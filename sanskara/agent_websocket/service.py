import asyncio
import json
import base64
import os
import traceback
import re
from urllib.parse import urlparse, parse_qs
import logging
import uuid as _uuid # Moved import to top level
try:
    # Prefer running from sanskara/ working directory
    from logging_setup import setup_logging
except ImportError:  # Fallback when imported as a package
    from sanskara.logging_setup import setup_logging

from google.adk.agents import LiveRequestQueue
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.sessions import DatabaseSessionService
from google.adk.artifacts import InMemoryArtifactService
from google.genai import types
from fastapi import WebSocket, WebSocketDisconnect
from sanskara.agent import root_agent
from sanskara.context_service import _safe_defaults, assemble_baseline_context
from sanskara.tools import get_wedding_context, get_active_workflows, get_tasks_for_wedding, get_complete_wedding_context
from sanskara.semantic_recall import warmup_semantic_memory
from sanskara.helpers import execute_supabase_sql
from config import VOICE_NAME, SEND_SAMPLE_RATE, SESSION_SERVICE_URI
from sanskara.adk_artifacts import artifact_service
# Removed SQLAlchemy imports and ChatSession/ChatMessage models
# from sanskara.db import async_get_db_session # Corrected import
# from typing import Optional

# Initialize session service, artifact service, and agent once for the application
session_service = DatabaseSessionService(db_url=SESSION_SERVICE_URI)
# artifact_service = InMemoryArtifactService()  # replaced by shared singleton
agent_instance = root_agent # Use the RootAgent as the main agent

# Reconnection settings for upstream Gemini Live session
MAX_RECONNECT_ATTEMPTS = 3
BASE_RECONNECT_DELAY = 0.75  # seconds

# Cache whether chat_sessions has a user_id column (varies across environments)
_CHAT_SESSIONS_HAS_USER_ID: bool | None = None

async def _detect_chat_sessions_has_user_id() -> bool:
    global _CHAT_SESSIONS_HAS_USER_ID
    if _CHAT_SESSIONS_HAS_USER_ID is not None:
        return _CHAT_SESSIONS_HAS_USER_ID
    try:
        sql = (
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = 'chat_sessions' "
            "AND column_name = 'user_id' LIMIT 1;"
        )
        res = await execute_supabase_sql(sql)
        has_col = bool(res and res.get("status") == "success" and res.get("data"))
        _CHAT_SESSIONS_HAS_USER_ID = has_col
        if not has_col:
            logging.info("chat_sessions.user_id not found; falling back to wedding-only session scoping.")
        return has_col
    except Exception as e:
        logging.debug(f"Failed to detect chat_sessions.user_id column: {e}")
        _CHAT_SESSIONS_HAS_USER_ID = False
        return False

def _is_transient_ws_error(err: Exception) -> bool:
    """Classify whether a websocket error is likely transient and worth retrying."""
    try:
        msg = str(err) if err else ""
        # Common transient hints from upstream (service timeouts / 5xx / transport issues)
        hints = [
            "1011",  # internal error (includes deadline expired)
            "Deadline expired",
            "Service Unavailable",
            "temporarily",
            "timeout",
            "Timeout",
            "connection",
            "reset by peer",
            "abnormal closure",
            "1006",  # abnormal closure
            "502",
            "503",
            "504",
        ]
        return any(h.lower() in msg.lower() for h in hints)
    except Exception:
        return False

async def websocket_endpoint(websocket: WebSocket):
    # Ensure logging is configured if this module is loaded directly (e.g., tests)
    setup_logging()
    """
    Handles incoming WebSocket connections for the multimodal ADK.
    The user_id is expected as a query parameter in the WebSocket URL.
    Example: ws://localhost:8000/ws?user_id=your_user_id
    """
    logging.getLogger().setLevel(logging.DEBUG) # Explicitly set logging level to DEBUG
    await websocket.accept()
    logging.info(f"New WebSocket connection accepted from {websocket.client.host}:{websocket.client.port}")

    # Extract user_id and optional session identifiers from query parameters
    query_params = websocket.query_params
    user_id = query_params.get("user_id", "default_user_id")
    # Allow clients to pass an ADK session id (alias: session_id) and/or DB chat session id
    requested_adk_session_id = query_params.get("adk_session_id") or query_params.get("session_id")
    requested_chat_session_id = query_params.get("chat_session_id")

    logging.info(f"Client connected with user_id: {user_id}")

    # Fetch wedding_id from user_id early
    wedding_id = None
    user_wedding_query_sql = f"SELECT wedding_id FROM wedding_members WHERE user_id = '{user_id}';"
    user_wedding_result = await execute_supabase_sql(user_wedding_query_sql)

    if user_wedding_result and user_wedding_result.get("status") == "success" and user_wedding_result.get("data"):
        wedding_id = user_wedding_result["data"][0].get("wedding_id")

    if not wedding_id:
        logging.warning(f"No wedding_id found for user_id {user_id}. Cannot prime context.")
        await websocket.send_json({"type": "error", "data": "No wedding found for your user ID. Please complete onboarding."})
        await websocket.close()
        return

    logging.debug(f"Attempting to establish session for user_id: {user_id}, wedding_id: {wedding_id}") # Added debug log

    # adk_session, session_handle, and chat_session_db_id will be managed by _run_session
    # and its inner functions using nonlocal.
    adk_session = None
    session_handle = None
    chat_session_db_id = None

    async def _ensure_chat_session_id(wedding_id: str, adk_session_id: str | None, user_id: str) -> str | None:
        """Ensure there is a chat_sessions row for a wedding.
        If adk_session_id is provided, prefer linking/looking up by it; else use most recent by wedding.
        Returns session_id. Safe to call repeatedly.
        """
        try:
            has_user_id = await _detect_chat_sessions_has_user_id()
            # 1) Try by adk_session_id if provided
            if adk_session_id:
                if has_user_id:
                    by_adk_sql = f"""
                    SELECT session_id FROM chat_sessions
                    WHERE adk_session_id = '{adk_session_id}' AND user_id = '{user_id}'
                    ORDER BY last_updated_at DESC LIMIT 1;
                    """
                else:
                    by_adk_sql = f"""
                    SELECT session_id FROM chat_sessions
                    WHERE adk_session_id = '{adk_session_id}'
                    ORDER BY last_updated_at DESC LIMIT 1;
                    """
                res2 = await execute_supabase_sql(by_adk_sql)
                if res2 and res2.get("status") == "success" and res2.get("data"):
                    return res2["data"][0].get("session_id")

            # 2) Try latest by wedding_id and user_id
            if has_user_id:
                select_sql = f"""
                SELECT session_id FROM chat_sessions
                WHERE wedding_id = '{wedding_id}' AND user_id = '{user_id}'
                ORDER BY last_updated_at DESC LIMIT 1;
                """
            else:
                select_sql = f"""
                SELECT session_id FROM chat_sessions
                WHERE wedding_id = '{wedding_id}'
                ORDER BY last_updated_at DESC LIMIT 1;
                """
            res = await execute_supabase_sql(select_sql)
            if res and res.get("status") == "success" and res.get("data"):
                sid = res["data"][0].get("session_id")
                # If session exists but not linked to adk_session_id, set it
                if adk_session_id:
                    try:
                        if has_user_id:
                            update_sql = f"""
                            UPDATE chat_sessions SET adk_session_id = '{adk_session_id}', last_updated_at = NOW()
                            WHERE session_id = '{sid}' AND user_id = '{user_id}';
                            """
                        else:
                            update_sql = f"""
                            UPDATE chat_sessions SET adk_session_id = '{adk_session_id}', last_updated_at = NOW()
                            WHERE session_id = '{sid}';
                            """
                        await execute_supabase_sql(update_sql)
                    except Exception:
                        pass
                return sid

            # 3) Otherwise insert a fresh session
            new_sid = str(_uuid.uuid4())
            if has_user_id:
                insert_sql = f"""
                INSERT INTO chat_sessions (session_id, wedding_id, adk_session_id, user_id)
                VALUES ('{new_sid}', '{wedding_id}', '{adk_session_id or ''}', '{user_id}')
                RETURNING session_id;
                """
            else:
                insert_sql = f"""
                INSERT INTO chat_sessions (session_id, wedding_id, adk_session_id)
                VALUES ('{new_sid}', '{wedding_id}', '{adk_session_id or ''}')
                RETURNING session_id;
                """
            ins = await execute_supabase_sql(insert_sql)
            if ins and ins.get("status") == "success" and ins.get("data"):
                return ins["data"][0].get("session_id")
        except Exception as e:
            logging.error(f"_ensure_chat_session_id failed: {e}")
        return None

    # Initial setup for ADK session and chat history
    initial_adk_session_id = requested_adk_session_id or None
    initial_chat_session_db_id = requested_chat_session_id or None

    # Try to retrieve existing ChatSession from my DB based on wedding_id and user_id
    has_user_id_col = await _detect_chat_sessions_has_user_id()
    if has_user_id_col:
        check_chat_session_sql = f"""
        SELECT session_id, adk_session_id FROM chat_sessions
        WHERE wedding_id = '{wedding_id}' AND user_id = '{user_id}'
        ORDER BY last_updated_at DESC LIMIT 1;
        """
    else:
        check_chat_session_sql = f"""
        SELECT session_id, adk_session_id FROM chat_sessions
        WHERE wedding_id = '{wedding_id}'
        ORDER BY last_updated_at DESC LIMIT 1;
        """
    existing_chat_session_result = await execute_supabase_sql(check_chat_session_sql)
    logging.debug(f"Raw result of check existing chat session for user {user_id} in wedding {wedding_id}: {existing_chat_session_result}")

    if (not initial_chat_session_db_id) and existing_chat_session_result and existing_chat_session_result.get("status") == "success" and existing_chat_session_result.get("data"):
        initial_chat_session_db_id = existing_chat_session_result["data"][0].get("session_id")
        initial_adk_session_id = initial_adk_session_id or existing_chat_session_result["data"][0].get("adk_session_id")
        logging.info(f"Found existing ChatSession in DB: {initial_chat_session_db_id} with ADK session ID: {initial_adk_session_id}. Will attempt to use this ADK session.")

    # If we have an existing ADK session id, send it now; otherwise wait for session_resumption_update
    if initial_adk_session_id:
        await websocket.send_json({"type": "session_id", "data": initial_adk_session_id})
        logging.info(f"Sent initial session id to client: {initial_adk_session_id}")
    else:
        logging.info("No existing ADK session id; will send on session_resumption_update")
    # If a DB chat session id is known, announce it as well
    if initial_chat_session_db_id:
        try:
            await websocket.send_json({"type": "session_id", "data": initial_chat_session_db_id})
        except Exception:
            pass
    await websocket.send_json({"type": "ready"}) # Always send ready after session announcement

    # Seed state with safe defaults so prompt templating never fails
    defaults = _safe_defaults()
    # Include V2 additions and nested structures referenced in prompt
    defaults.update({
        "workflow_saves": [],
        "collab_status": {"bride_side": {}, "groom_side": {}, "couple": {}},
        "bookings": [],
        "thread_hint": {},
        "semantic_memory": {"facts": []},
    })
    # adk_session.state will be populated inside _run_session once the session object is available.

    # This log will be moved to _run_session after adk_session is established.
    # logging.info(f"Initial context primed for user {user_id}, wedding {wedding_id}: {adk_session.state}")

    async def _run_session(initial_adk_session_id: str | None, initial_chat_session_db_id: str | None):
        nonlocal adk_session, session_handle, chat_session_db_id # Declare as nonlocal to modify outer scope variables

        # Set initial values for adk_session and chat_session_db_id from arguments
        # adk_session will be updated by runner.run_live with the actual session object
        # For ADK, if we try to create a session with an existing ID, it will load it.
        # If initial_adk_session_id is None, it will create a new one.
        # Create or resume ADK session. If a session with this id already exists in the DB,
        # avoid UNIQUE constraint errors by falling back to a fresh session without specifying id.
        try:
            if initial_adk_session_id:
                adk_session = await session_service.create_session(
                    app_name="sanskara", user_id=user_id, session_id=initial_adk_session_id
                )
            else:
                adk_session = await session_service.create_session(
                    app_name="sanskara", user_id=user_id
                )
        except Exception as e:
            # If the backing store complains about unique constraint, open a new session without id
            if "UNIQUE constraint failed" in str(e):
                logging.info(
                    f"Existing ADK session detected for id={initial_adk_session_id}; creating a fresh session without explicit id."
                )
                adk_session = await session_service.create_session(
                    app_name="sanskara", user_id=user_id
                )
            else:
                raise
        session_handle = getattr(adk_session, "session_id", None) or getattr(adk_session, "handle", None) or getattr(adk_session, "id", None)
        chat_session_db_id = initial_chat_session_db_id

        # Initial context priming (moved from websocket_endpoint)
        adk_session.state.update(defaults)  # Use the defaults defined in outer scope
        adk_session.state.update({
            "current_wedding_id": wedding_id,
            "current_user_id": user_id,
        })

        # Ensure we carry forward existing chat_session id into state for preloading
        if initial_chat_session_db_id and not adk_session.state.get("chat_session_db_id"):
            adk_session.state["chat_session_db_id"] = initial_chat_session_db_id
            try:
                await websocket.send_json({"type": "chat_session_id", "data": initial_chat_session_db_id})
            except Exception:
                pass

        # Parallelize initial baseline context + conversation summary loads + semantic warmup
        async def _load_baseline():
            try:
                baseline = await assemble_baseline_context(wedding_id, user_id, user_role=None)
                if isinstance(baseline, dict):
                    adk_session.state.update(baseline)
            except Exception as e:
                logging.debug(f"assemble_baseline_context failed during priming: {e}")

        async def _load_conv_bits():
            try:
                # 1) Conversation summary (latest for this wedding)
                has_user_id_col = await _detect_chat_sessions_has_user_id()
                if has_user_id_col:
                    summary_sql = f"""
                    SELECT summary FROM chat_sessions
                    WHERE wedding_id = '{wedding_id}' AND user_id = '{user_id}'
                    ORDER BY last_updated_at DESC
                    LIMIT 1;
                    """
                else:
                    summary_sql = f"""
                    SELECT summary FROM chat_sessions
                    WHERE wedding_id = '{wedding_id}'
                    ORDER BY last_updated_at DESC
                    LIMIT 1;
                    """
                summary_res = await execute_supabase_sql(summary_sql)
                if summary_res and summary_res.get("status") == "success" and summary_res.get("data"):
                    adk_session.state["conversation_summary"] = summary_res["data"][0].get("summary") or ""
                else:
                    adk_session.state.setdefault("conversation_summary", "")

                # 2) Recent messages (by session if known; else by latest session for wedding)
                session_for_msgs = adk_session.state.get("chat_session_db_id")
                if not session_for_msgs:
                    latest_session_sql = f"""
                    SELECT session_id FROM chat_sessions
                    WHERE wedding_id = '{wedding_id}'
                    ORDER BY last_updated_at DESC
                    LIMIT 1;
                    """
                    latest_session_res = await execute_supabase_sql(latest_session_sql)
                    if latest_session_res and latest_session_res.get("status") == "success" and latest_session_res.get("data"):
                        session_for_msgs = latest_session_res["data"][0].get("session_id")
                if session_for_msgs:
                    load_msgs_sql = f"""
                    SELECT sender_type, sender_name, content, timestamp FROM chat_messages
                    WHERE session_id = '{session_for_msgs}'
                    ORDER BY timestamp DESC
                    LIMIT 12;
                    """
                    messages_result = await execute_supabase_sql(load_msgs_sql)
                    if messages_result and messages_result.get("status") == "success":
                        adk_session.state["recent_messages"] = list(reversed(messages_result.get("data", [])))
            except Exception as e:
                logging.debug(f"_load_conv_bits failed: {e}")

        async def _warmup_semantic():
            try:
                await warmup_semantic_memory()
            except Exception as e:
                logging.debug(f"semantic warmup failed: {e}")

        try:
            await asyncio.gather(_load_baseline(), _load_conv_bits(), _warmup_semantic())
        except Exception:
            pass

        # Optionally pre-load conversation summary and recent messages for continuity
        try:
            # 1) Conversation summary (latest for this wedding)
            has_user_id_col = await _detect_chat_sessions_has_user_id()
            if has_user_id_col:
                summary_sql = f"""
                SELECT summary FROM chat_sessions
                WHERE wedding_id = '{wedding_id}' AND user_id = '{user_id}'
                ORDER BY last_updated_at DESC
                LIMIT 1;
                """
            else:
                summary_sql = f"""
                SELECT summary FROM chat_sessions
                WHERE wedding_id = '{wedding_id}'
                ORDER BY last_updated_at DESC
                LIMIT 1;
                """
            summary_res = await execute_supabase_sql(summary_sql)
            if summary_res and summary_res.get("status") == "success" and summary_res.get("data"):
                adk_session.state["conversation_summary"] = summary_res["data"][0].get("summary") or ""
            else:
                adk_session.state.setdefault("conversation_summary", "")

            # 2) Recent messages (by session if known; else by latest session for wedding)
            session_for_msgs = adk_session.state.get("chat_session_db_id")
            if not session_for_msgs:
                # fallback to latest session id for wedding
                latest_session_sql = f"""
                SELECT session_id FROM chat_sessions
                WHERE wedding_id = '{wedding_id}'
                ORDER BY last_updated_at DESC
                LIMIT 1;
                """
                latest_session_res = await execute_supabase_sql(latest_session_sql)
                if latest_session_res and latest_session_res.get("status") == "success" and latest_session_res.get("data"):
                    session_for_msgs = latest_session_res["data"][0].get("session_id")
            if session_for_msgs:
                load_msgs_sql = f"""
                SELECT sender_type, sender_name, content, timestamp FROM chat_messages
                WHERE session_id = '{session_for_msgs}'
                ORDER BY timestamp DESC
                LIMIT 12;
                """
                messages_result = await execute_supabase_sql(load_msgs_sql)
                if messages_result and messages_result.get("status") == "success":
                    adk_session.state["recent_messages"] = list(reversed(messages_result.get("data", [])))
                else:
                    logging.debug(f"Failed to load recent messages: {messages_result.get('error', 'Unknown error')}")
        except Exception as e:
            logging.debug(f"Failed to preload recent messages: {e}")

    # Optionally enrich with semantic memory summaries (session_final_summary entries)
        # Do this in the background so we don't block the user's first turn.
        async def _bg_semantic_memory_load():
            try:
                try:
                    from sanskara.semantic_recall import semantic_search_facts  # type: ignore
                except Exception:
                    from sanskara.sanskara.semantic_recall import semantic_search_facts  # type: ignore
                mem = await semantic_search_facts(
                    wedding_id=wedding_id,
                    session_id=adk_session.state.get("chat_session_db_id"),
                    query="session_final_summary",
                    top_k=5,
                )
                if isinstance(mem, dict) and mem.get("facts"):
                    adk_session.state.setdefault("semantic_memory", {})
                    adk_session.state["semantic_memory"]["facts"] = mem.get("facts")
            except Exception as e:
                logging.debug(f"semantic_memory preload failed: {e}")

        try:
            asyncio.create_task(_bg_semantic_memory_load())
        except Exception:
            # Fallback to inline load if task creation fails (unlikely)
            await _bg_semantic_memory_load()

        # Background enrichment with full context (non-blocking, timeout-guarded)
        async def _bg_enrich_context():
            try:
                ctx = await asyncio.wait_for(get_complete_wedding_context(wedding_id), timeout=4.0)
                if isinstance(ctx, dict):
                    # Minimal merge: wedding_data/active_workflows/all_tasks and workflows alias
                    for k in ("wedding_data", "active_workflows", "all_tasks"):
                        if k in ctx and ctx[k] is not None:
                            adk_session.state[k] = ctx[k]
                    # Keep prompt alias in sync
                    if ctx.get("active_workflows"):
                        adk_session.state["workflows"] = ctx.get("active_workflows")
            except Exception as e:
                logging.debug(f"_bg_enrich_context failed: {e}")

        try:
            asyncio.create_task(_bg_enrich_context())
        except Exception:
            pass

        logging.info(f"Initial context primed for user {user_id}, wedding {wedding_id}: {adk_session.state}")  # Use adk_session.state

        runner = Runner(
            app_name="sanskara",
            agent=agent_instance,
            session_service=session_service,
            artifact_service=artifact_service,
        )

        live_request_queue = LiveRequestQueue()

        # Resolve TEXT modality enum safely to avoid Pydantic warnings
        _Modality = getattr(types, "Modality", None)
        _response_modalities = [getattr(_Modality, "TEXT")] if _Modality and hasattr(_Modality, "TEXT") else None

        run_config = RunConfig(
            streaming_mode=StreamingMode.BIDI,
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=VOICE_NAME
                    )
                )
            ),
            response_modalities=_response_modalities,
            output_audio_transcription=types.AudioTranscriptionConfig(),
            input_audio_transcription=types.AudioTranscriptionConfig(),
        )

        audio_queue = asyncio.Queue()
        video_queue = asyncio.Queue()
        text_queue = asyncio.Queue()

        # Define handlers and processing coroutines
        async def handle_websocket_messages():
            """Receives messages from the WebSocket and puts them into queues.
            Accepts plain text or JSON objects with a 'type' field.
            """
            async for raw in websocket.iter_text():
                try:
                    message = None
                    try:
                        message = json.loads(raw)
                    except Exception:
                        message = raw  # treat as plain text

                    # JSON object path
                    if isinstance(message, dict):
                        mtype = message.get("type")
                        if mtype == "audio":
                            audio_bytes = base64.b64decode(message.get("data", ""))
                            await audio_queue.put(audio_bytes)
                        elif mtype == "video":
                            video_bytes = base64.b64decode(message.get("data", ""))
                            video_mode = message.get("mode", "webcam")
                            await video_queue.put({
                                "data": video_bytes,
                                "mode": video_mode
                            })
                        elif mtype == "end":
                            logging.info("Received end signal from client")
                        elif mtype == "text" or (mtype is None and message.get("data")):
                            text_val = message.get("data")
                            logging.info(f"Received text: {text_val}")
                            await text_queue.put({"data": text_val})
                        else:
                            logging.debug(f"Unhandled message shape: {message}")
                    else:
                        # Plain text path
                        text_val = str(message)
                        logging.info(f"Received text: {text_val}")
                        await text_queue.put({"data": text_val})
                except Exception as e:
                    logging.error(f"Error processing incoming message: {e}")

        async def process_and_send_audio_to_adk():
            """Takes audio from queue and sends to ADK's live_request_queue."""
            while True:
                data = await audio_queue.get()
                if data is None: # Sentinel for ending the queue
                    break
                live_request_queue.send_realtime(
                    types.Blob(
                        data=data,
                        mime_type=f"audio/pcm;rate={SEND_SAMPLE_RATE}",
                    )
                )
                audio_queue.task_done()
        # Task to process and send video frames to Gemini via ADK
        async def process_and_send_video():
            while True:
                video_data = await video_queue.get()

                # Extract video bytes and mode from queue item
                video_bytes = video_data.get("data")
                video_mode = video_data.get("mode", "webcam")

                logging.info(f"Processing video frame from {video_mode}")

                # Send the video frame to Gemini through ADK
                live_request_queue.send_realtime(
                    types.Blob(
                        data=video_bytes,
                        mime_type="image/jpeg",
                    )
                )

                video_queue.task_done()

        async def handle_text_messages_with_agent(): # Removed db_session param; look up dynamically
            """Takes text from queue, processes with agent, sends response to client, and persists messages."""
            while True:
                text_data = await text_queue.get()
                if text_data is None:  # Sentinel for ending the queue
                    break
                text_content = text_data.get("data", "")
                if not text_content:
                    text_queue.task_done()
                    continue
                try:
                    # Ensure chat session linkage exists before persisting
                    if not adk_session.state.get("chat_session_db_id"):
                        ensured = await _ensure_chat_session_id(
                            wedding_id, adk_session.state.get("adk_session_id"), user_id
                        )
                        adk_session.state["chat_session_db_id"] = ensured

                    # Persist user message
                    if adk_session.state.get("chat_session_db_id"):
                        content_json = json.dumps({"text": text_content})
                        # Escape single quotes for safe SQL literal embedding
                        content_json_sql = content_json.replace("'", "''")
                        insert_sql = f"""
                        WITH ins AS (
                          INSERT INTO chat_messages (session_id, sender_type, sender_name, content)
                          VALUES ('{adk_session.state.get('chat_session_db_id')}', 'user', 'User', '{content_json_sql}'::jsonb)
                          RETURNING message_id, session_id
                        )
                        UPDATE chat_sessions cs
                          SET last_updated_at = NOW()
                        FROM ins
                        WHERE cs.session_id = ins.session_id
                        RETURNING ins.message_id;
                        """
                        insert_result = await execute_supabase_sql(insert_sql)
                        if insert_result and insert_result.get("status") == "success" and insert_result.get("data"):
                            logging.info(f"Persisted user message: {insert_result['data'][0].get('message_id')}")
                        else:
                            logging.error(f"Failed to persist user message: {insert_result.get('error', 'Unknown error')}")
                    else:
                        logging.warning("Cannot persist user message: chat_session_db_id is missing.")

                    # Parse [FILES: ...] markers
                    app_name = os.getenv("SANSKARA_APP_NAME", "sanskara")
                    adk_session_id_for_artifacts = (
                        adk_session.state.get("adk_session_id")
                        or getattr(adk_session, "session_id", None)
                        or getattr(adk_session, "handle", None)
                        or getattr(adk_session, "id", None)
                    )
                    filenames: list[str] = []
                    try:
                        matches = re.findall(r"\[(FILES?|files?):\s*([^\]]+)\]", text_content)
                        for _label, inner in matches:
                            parts = re.split(r"[,;]", inner)
                            filenames.extend([p.strip() for p in parts if p and p.strip()])
                    except Exception:
                        pass

                    artifact_parts: list[types.Part] = []
                    if filenames and adk_session_id_for_artifacts and user_id:
                        for fname in filenames:
                            try:
                                art = await artifact_service.load_artifact(  # type: ignore
                                    app_name=app_name,
                                    user_id=user_id,
                                    session_id=adk_session_id_for_artifacts,
                                    filename=fname,
                                )
                                if art is not None:
                                    artifact_parts.append(art)
                                    logging.info({
                                        "event": "ws_inline_artifact",
                                        "filename": fname,
                                        "mime_type": getattr(getattr(art, "inline_data", None), "mime_type", None),
                                    })
                                else:
                                    logging.warning(f"Artifact not found for filename={fname} user={user_id} session={adk_session_id_for_artifacts}")
                            except Exception as e:
                                logging.error(f"load_artifact failed for {fname}: {e}")

                    # Clean [FILES: ...] markers
                    cleaned_text = re.sub(r"\[(FILES?|files?):\s*[^\]]+\]", "", text_content).strip() if text_content else text_content

                    user_parts: list[types.Part] = []
                    if cleaned_text:
                        user_parts.append(types.Part(text=cleaned_text))
                    if artifact_parts:
                        user_parts.extend(artifact_parts)
                    if not user_parts:
                        user_parts = [types.Part(text=text_content)]

                    live_request_queue.send_content(
                        types.Content(
                            role="user",
                            parts=user_parts,
                        )
                    )
                except Exception as e:
                    logging.error(f"Error processing text with agent: {e}")
                    await websocket.send_json({"type": "error", "data": f"Agent error: {e}"})
                text_queue.task_done()

        async def receive_and_process_responses_from_adk():  # Removed db_session param; look up dynamically
            """Stream responses from Gemini via ADK with reconnection on transient closures.

            Reuses the same ADK session and live_request_queue when possible.
            Notifies the client on reconnect and on final failure.
            """
            nonlocal adk_session, session_handle, chat_session_db_id
            current_session_id = None
            attempts = 0

            # Keep running until we exhaust retries or the outer TaskGroup cancels us
            while True:
                # Track user and model outputs between turn completion events
                input_texts = []
                output_texts = []
                interrupted = False

                try:
                    async for event in runner.run_live(
                        session=adk_session,  # Use adk_session
                        live_request_queue=live_request_queue,
                        run_config=run_config,
                    ):
                        # Update adk_session object from the event (it will be the actual session object)
                        if hasattr(event, "session") and event.session:
                            adk_session = event.session

                        event_str = str(event)

                        # Handle session resumption updates
                        if hasattr(event, "session_resumption_update") and event.session_resumption_update:
                            update = event.session_resumption_update
                            if update.resumable and update.new_handle:
                                current_session_id = update.new_handle
                                session_handle = current_session_id
                                logging.info(f"ADK established new/resumed session: {current_session_id}")
                                try:
                                    await websocket.send_json({
                                        "type": "session_id",
                                        "data": current_session_id,
                                    })
                                except Exception as e:
                                    logging.debug(f"Failed to notify client of session_id: {e}")

                                # Ensure chat_session_db_id is linked/created after ADK session is established
                                if adk_session and adk_session.state.get("chat_session_db_id") is None:
                                    ensured_chat_session_db_id = await _ensure_chat_session_id(
                                        wedding_id, session_handle, user_id  # Pass user_id
                                    )
                                    if ensured_chat_session_db_id:
                                        adk_session.state["chat_session_db_id"] = ensured_chat_session_db_id
                                        chat_session_db_id = ensured_chat_session_db_id
                                        logging.info(
                                            f"Linked ADK session {session_handle} to DB chat session {chat_session_db_id}"
                                        )
                                        try:
                                            await websocket.send_json({"type": "session_id", "data": chat_session_db_id})
                                        except Exception:
                                            pass
                                    else:
                                        logging.warning(
                                            "Could not establish DB chat session linkage after ADK session established. Messages might not be persisted."
                                        )

                                # Send a one-time welcome trigger so the user sees activity without sending first
                                try:
                                    if not adk_session.state.get("welcomed", False):
                                        adk_session.state["welcomed"] = True
                                        live_request_queue.send_content(
                                            types.Content(
                                                role="user",
                                                parts=[
                                                    types.Part(
                                                        text="Say a brief, friendly welcome as Sanskara AI and offer help with wedding planning."
                                                    )
                                                ],
                                            )
                                        )
                                        logging.info("Sent one-time welcome trigger to ADK")
                                except Exception as e:
                                    logging.debug(f"Failed to send welcome trigger: {e}")

                        # Forward content
                        if event.content and event.content.parts:
                            for part in event.content.parts:
                                if hasattr(part, "inline_data") and part.inline_data:
                                    try:
                                        mime = getattr(part.inline_data, "mime_type", None) or ""
                                        b64_data = base64.b64encode(part.inline_data.data).decode("utf-8")
                                        payload_type = (
                                            "audio"
                                            if mime.startswith("audio/")
                                            else "image"
                                            if mime.startswith("image/")
                                            else "blob"
                                        )
                                        await websocket.send_json(
                                            {"type": payload_type, "data": b64_data, "mime": mime}
                                        )
                                    except Exception as e:
                                        logging.error(f"Failed to forward inline_data: {e}")

                                if hasattr(part, "text") and part.text:
                                    if hasattr(event.content, "role") and event.content.role == "user":
                                        input_texts.append(part.text)
                                    else:
                                        if "partial=True" in event_str:
                                            await websocket.send_json(
                                                {"type": "text", "data": part.text}
                                            )
                                            output_texts.append(part.text)

                        if event.interrupted and not interrupted:
                            logging.info("🤐 INTERRUPTION DETECTED")
                            await websocket.send_json(
                                {
                                    "type": "interrupted",
                                    "data": "Response interrupted by user input",
                                }
                            )
                            interrupted = True

                        if event.turn_complete:
                            if not interrupted:
                                logging.info("✅ Gemini done talking")
                                await websocket.send_json({
                                    "type": "turn_complete",
                                    "session_id": current_session_id,
                                })
                            # Persist a single assistant message combining parts for this turn
                            try:
                                if output_texts:
                                    combined = "\n".join(list(dict.fromkeys(output_texts)))
                                    if not adk_session.state.get("chat_session_db_id"):
                                        ensured = await _ensure_chat_session_id(
                                            wedding_id, adk_session.state.get("adk_session_id"), user_id
                                        )
                                        adk_session.state["chat_session_db_id"] = ensured
                                        if ensured:
                                            try:
                                                await websocket.send_json({"type": "chat_session_id", "data": ensured})
                                            except Exception:
                                                pass
                                    if adk_session.state.get("chat_session_db_id"):
                                        content_json = json.dumps({"text": combined})
                                        # Escape single quotes for safe SQL literal embedding
                                        content_json_sql = content_json.replace("'", "''")
                                        insert_sql = f"""
                                            WITH ins AS (
                                                INSERT INTO chat_messages (session_id, sender_type, sender_name, content)
                                                VALUES ('{adk_session.state.get('chat_session_db_id')}', 'assistant', 'Sanskara AI', '{content_json_sql}'::jsonb)
                                                RETURNING message_id, session_id
                                            )
                                            UPDATE chat_sessions cs
                                                SET last_updated_at = NOW()
                                            FROM ins
                                            WHERE cs.session_id = ins.session_id
                                            RETURNING ins.message_id;
                                        """
                                        await execute_supabase_sql(insert_sql)
                                    else:
                                        logging.warning(
                                            "Cannot persist assistant message: chat_session_db_id is missing."
                                        )
                            except Exception as e:
                                logging.error(
                                    f"Failed to persist assistant message on turn_complete: {e}"
                                )

                            if input_texts:
                                unique_texts = list(dict.fromkeys(input_texts))
                                logging.info(
                                    f"Input transcription: {' '.join(unique_texts)}"
                                )
                            if output_texts:
                                unique_texts = list(dict.fromkeys(output_texts))
                                logging.info(
                                    f"Output transcription: {' '.join(unique_texts)}"
                                )
                            # reset per turn
                            input_texts = []
                            output_texts = []
                            interrupted = False

                        # If the async for exits normally, reset attempts and continue listening
                        attempts = 0
                        continue

                except Exception as e:
                    # Handle transient upstream closure and try to resume
                    is_transient = _is_transient_ws_error(e)
                    logging.error(
                        {
                            "event": "adk_receive_error",
                            "transient": is_transient,
                            "attempts": attempts,
                            "error": str(e),
                        }
                    )
                    if not is_transient or attempts >= MAX_RECONNECT_ATTEMPTS:
                        try:
                            await websocket.send_json(
                                {
                                    "type": "error",
                                    "data": "Connection to AI service closed. Please send your message again.",
                                }
                            )
                        except Exception:
                            pass
                        break  # exit the receiver loop; TaskGroup will unwind

                    # backoff and try again with same session/live_request_queue
                    attempts += 1
                    delay = BASE_RECONNECT_DELAY * (2 ** (attempts - 1))
                    try:
                        await websocket.send_json(
                            {"type": "reconnecting", "data": {"attempt": attempts, "retry_in": delay}}
                        )
                    except Exception:
                        pass
                    await asyncio.sleep(delay)
                    # loop continues and re-enters run_live

        # Start concurrent pipelines (websocket ingest, audio/video forwarding, text handling, and ADK response streaming)
        logging.info("Starting TaskGroup for live session pipelines")
        async with asyncio.TaskGroup() as tg:
            tg.create_task(handle_websocket_messages(), name="WebSocketMessageReceiver")
            tg.create_task(process_and_send_audio_to_adk(), name="ADKAudioSender")
            tg.create_task(handle_text_messages_with_agent(), name="AgentTextProcessor")
            tg.create_task(process_and_send_video(), name="ADKVideoSender")
            tg.create_task(receive_and_process_responses_from_adk(), name="ADKResponseSender")

    try:
        # Run the live session (queues + streaming)
        await _run_session(initial_adk_session_id, initial_chat_session_db_id)
    except WebSocketDisconnect:
        logging.info(f"WebSocket disconnected for user_id: {user_id}")
    except Exception as e:
        logging.error(f"Unhandled error in WebSocket endpoint for user_id {user_id}: {e}")
        logging.error(traceback.format_exc())
    finally:
        # No db_session_context to exit, as we are not using SQLAlchemy session context manager here.
        # All database operations are direct via execute_supabase_sql.
        logging.info(f"WebSocket connection closed for user_id: {user_id}")