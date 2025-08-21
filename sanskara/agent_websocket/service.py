import asyncio
import json
import base64
import os
import traceback
import re
from urllib.parse import urlparse, parse_qs
import logging
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
from sanskara.tools import get_wedding_context, get_active_workflows, get_tasks_for_wedding
from sanskara.helpers import execute_supabase_sql
from config import VOICE_NAME, SEND_SAMPLE_RATE, SESSION_SERVICE_URI
from sanskara.adk_artifacts import artifact_service


# Initialize session service, artifact service, and agent once for the application
session_service = DatabaseSessionService(db_url=SESSION_SERVICE_URI)
# artifact_service = InMemoryArtifactService()  # replaced by shared singleton
agent_instance = root_agent # Use the RootAgent as the main agent

# Reconnection settings for upstream Gemini Live session
MAX_RECONNECT_ATTEMPTS = 3
BASE_RECONNECT_DELAY = 0.75  # seconds

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
    await websocket.accept()
    logging.info(f"New WebSocket connection accepted from {websocket.client.host}:{websocket.client.port}")

    # Extract user_id from query parameters
    query_params = websocket.query_params
    user_id = query_params.get("user_id", "default_user_id") # Get user_id from query params

    logging.info(f"Client connected with user_id: {user_id}")
    
    # Create session for the ADK runner
    session = await session_service.create_session(
        app_name="sanskara",
        user_id=user_id,
    )
    # Send the ADK session identifier to the client for future artifact & tool calls
    try:
        logging.info(f"Session object repr: {session}")
        try:
            logging.info(f"Session dir: {dir(session)}")
        except Exception:
            pass
        session_handle = (
            getattr(session, "session_id", None)
            or getattr(session, "handle", None)
            or getattr(session, "id", None)
        )
        if not session_handle:
            import uuid as _uuid
            session_handle = f"sess-{_uuid.uuid4().hex[:8]}"
            logging.warning("Generated synthetic session handle (none provided by ADK)")
        session.state["adk_session_id"] = session_handle
        session.state.setdefault("recent_artifacts", [])  # prevent KeyError in prompt templating
        await websocket.send_json({"type": "session", "session_id": session_handle})
        logging.info(f"Sent session id to client: {session_handle}")
    except Exception as e:
        logging.error(f"Failed to emit session id to client: {e}")

    # Always send ready after session announcement
    try:
        await websocket.send_json({"type": "ready"})
    except Exception as e:
        logging.error(f"Failed to send ready message: {e}")

    # Fetch wedding_id from user_id and prime context
    wedding_id = None
    try:
        user_wedding_query_sql = f"SELECT wedding_id FROM wedding_members WHERE user_id = '{user_id}';"
        user_wedding_result = await execute_supabase_sql(user_wedding_query_sql)

        if user_wedding_result and user_wedding_result.get("status") == "success" and user_wedding_result.get("data"):
            wedding_id = user_wedding_result["data"][0].get("wedding_id")

        if not wedding_id:
            logging.warning(f"No wedding_id found for user_id {user_id}. Cannot prime context.")
            await websocket.send_json({"type": "error", "data": "No wedding found for your user ID. Please complete onboarding."})
        else:
            # Seed state with safe defaults so prompt templating never fails
            try:
                defaults = _safe_defaults()
            except Exception:
                defaults = {}
            # Include V2 additions and nested structures referenced in prompt
            defaults.update({
                "workflow_saves": [],
                "collab_status": {"bride_side": {}, "groom_side": {}, "couple": {}},
                "bookings": [],
                "thread_hint": {},
                "semantic_memory": {"facts": []},
            })

            session.state.update(defaults)
            session.state.update({
                "current_wedding_id": wedding_id,
                "current_user_id": user_id,
            })

            # Optionally enrich with baseline context from DB (non-fatal if it fails)
            try:
                baseline = await assemble_baseline_context(wedding_id, user_id, user_role=None)
                if isinstance(baseline, dict):
                    session.state.update(baseline)
            except Exception as e:
                logging.debug(f"assemble_baseline_context failed during priming: {e}")

            logging.info(f"Initial context primed for user {user_id}, wedding {wedding_id}: {session.state}")
    except Exception as e:
        logging.error(f"Error priming context for user {user_id}: {e}")
        logging.error(traceback.format_exc())
        await websocket.send_json({"type": "error", "data": f"Server error priming context: {e}"})
        await websocket.close()
        return # Exit the handler if context priming fails

    runner = Runner(
        app_name="sanskara",
        agent=agent_instance,
        session_service=session_service,
        artifact_service=artifact_service,
    )

    live_request_queue = LiveRequestQueue()

    run_config = RunConfig(
        streaming_mode=StreamingMode.BIDI,
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=VOICE_NAME
                )
            )
        ),
        response_modalities=["TEXT"],
        output_audio_transcription=types.AudioTranscriptionConfig(),
        input_audio_transcription=types.AudioTranscriptionConfig(),
    )

    audio_queue = asyncio.Queue()
    video_queue = asyncio.Queue()
    text_queue = asyncio.Queue()

    try:
        async with asyncio.TaskGroup() as tg:
            async def handle_websocket_messages():
                """Receives messages from the WebSocket and puts them into queues."""
                async for message in websocket.iter_json(): # Use iter_json for convenience
                    try:
                        if message.get("type") == "audio":
                            audio_bytes = base64.b64decode(message.get("data", ""))
                            await audio_queue.put(audio_bytes)
                        elif message.get("type") == "video":
                            # Decode base64 video frame
                            video_bytes = base64.b64decode(message.get("data", ""))
                            # Get video mode metadata if available
                            video_mode = message.get("mode", "webcam")  # Default to webcam if not specified
                            # Put video frame in queue for processing with metadata
                            await video_queue.put({
                                "data": video_bytes,
                                "mode": video_mode
                            })
                        elif message.get("type") == "end":
                            logging.info("Received end signal from client")
                            # Optionally, signal end to the live_request_queue or close queues
                        elif message.get("type") == "text":
                            logging.info(f"Received text: {message.get('data')}")
                            await text_queue.put({"data": message.get("data")})
                    except json.JSONDecodeError:
                        logging.error("Invalid JSON message received")
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

            async def handle_text_messages_with_agent():
                """Takes text from queue, processes with agent, sends response to client."""
                while True:
                    text_data = await text_queue.get()
                    if text_data is None: # Sentinel for ending the queue
                        break
                    text_content = text_data.get("data", "")
                    if text_content:
                        try:
                            # Parse [FILES: ...] style references and attach artifacts (images/blobs) to the user message
                            # Example: "Please compare [FILES: img1.png, img2.jpg]"
                            app_name = os.getenv("SANSKARA_APP_NAME", "sanskara")
                            session_id = (
                                session.state.get("adk_session_id")
                                or getattr(session, "session_id", None)
                                or getattr(session, "handle", None)
                                or getattr(session, "id", None)
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
                            if filenames and session_id and user_id:
                                for fname in filenames:
                                    try:
                                        art = await artifact_service.load_artifact(  # type: ignore
                                            app_name=app_name,
                                            user_id=user_id,
                                            session_id=session_id,
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
                                            logging.warning(f"Artifact not found for filename={fname} user={user_id} session={session_id}")
                                    except Exception as e:
                                        logging.error(f"load_artifact failed for {fname}: {e}")

                            # Clean the [FILES: ...] markers from user text
                            cleaned_text = re.sub(r"\[(FILES?|files?):\s*[^\]]+\]", "", text_content).strip() if text_content else text_content

                            user_parts: list[types.Part] = []
                            if cleaned_text:
                                user_parts.append(types.Part(text=cleaned_text))
                            # Append any artifacts we successfully loaded
                            if artifact_parts:
                                user_parts.extend(artifact_parts)
                            # Fallback: if no parts produced, ensure we still send original text
                            if not user_parts:
                                user_parts = [types.Part(text=text_content)]

                            live_request_queue.send_content(
                                types.Content(
                                    role="user",
                                    parts=user_parts,
                                )
                            )
                            #await websocket.send_json({"type": "text", "data": agent_response})
                        except Exception as e:
                            logging.error(f"Error processing text with agent: {e}")
                            await websocket.send_json({"type": "error", "data": f"Agent error: {e}"})
                    text_queue.task_done()

            async def receive_and_process_responses_from_adk():
                """Stream responses from Gemini via ADK with reconnection on transient closures.

                Reuses the same ADK session and live_request_queue when possible.
                Notifies the client on reconnect and on final failure.
                """
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
                            session=session,
                            live_request_queue=live_request_queue,
                            run_config=run_config,
                        ):
                            event_str = str(event)

                            # Handle session resumption updates
                            if hasattr(event, 'session_resumption_update') and event.session_resumption_update:
                                update = event.session_resumption_update
                                if update.resumable and update.new_handle:
                                    current_session_id = update.new_handle
                                    logging.info(f"New SESSION: {current_session_id}")
                                    try:
                                        await websocket.send_json({
                                            "type": "session_id",
                                            "data": current_session_id,
                                        })
                                    except Exception as e:
                                        logging.debug(f"Failed to notify client of session_id: {e}")

                            # Forward content
                            if event.content and event.content.parts:
                                for part in event.content.parts:
                                    if hasattr(part, "inline_data") and part.inline_data:
                                        try:
                                            mime = getattr(part.inline_data, "mime_type", None) or ""
                                            b64_data = base64.b64encode(part.inline_data.data).decode("utf-8")
                                            payload_type = (
                                                "audio" if mime.startswith("audio/") else
                                                "image" if mime.startswith("image/") else
                                                "blob"
                                            )
                                            await websocket.send_json({"type": payload_type, "data": b64_data, "mime": mime})
                                        except Exception as e:
                                            logging.error(f"Failed to forward inline_data: {e}")

                                    if hasattr(part, "text") and part.text:
                                        if hasattr(event.content, "role") and event.content.role == "user":
                                            input_texts.append(part.text)
                                        else:
                                            if "partial=True" in event_str:
                                                await websocket.send_json({"type": "text", "data": part.text})
                                                output_texts.append(part.text)

                            if event.interrupted and not interrupted:
                                logging.info("🤐 INTERRUPTION DETECTED")
                                await websocket.send_json({
                                    "type": "interrupted",
                                    "data": "Response interrupted by user input",
                                })
                                interrupted = True

                            if event.turn_complete:
                                if not interrupted:
                                    logging.info("✅ Gemini done talking")
                                    await websocket.send_json({
                                        "type": "turn_complete",
                                        "session_id": current_session_id,
                                    })
                                if input_texts:
                                    unique_texts = list(dict.fromkeys(input_texts))
                                    logging.info(f"Input transcription: {' '.join(unique_texts)}")
                                if output_texts:
                                    unique_texts = list(dict.fromkeys(output_texts))
                                    logging.info(f"Output transcription: {' '.join(unique_texts)}")
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
                                await websocket.send_json({
                                    "type": "error",
                                    "data": "Connection to AI service closed. Please send your message again.",
                                })
                            except Exception:
                                pass
                            break  # exit the receiver loop; TaskGroup will unwind

                        # backoff and try again with same session/live_request_queue
                        attempts += 1
                        delay = BASE_RECONNECT_DELAY * (2 ** (attempts - 1))
                        try:
                            await websocket.send_json({
                                "type": "reconnecting",
                                "data": {"attempt": attempts, "retry_in": delay},
                            })
                        except Exception:
                            pass
                        await asyncio.sleep(delay)
                        # loop continues and re-enters run_live

            # Create tasks within the TaskGroup
            tg.create_task(handle_websocket_messages(), name="WebSocketMessageReceiver")
            tg.create_task(process_and_send_audio_to_adk(), name="ADKAudioSender")
            tg.create_task(handle_text_messages_with_agent(), name="AgentTextProcessor")
            tg.create_task(process_and_send_video(), name="ADKVideoSender") # Added video processing task
            tg.create_task(receive_and_process_responses_from_adk(), name="ADKResponseSender")

    except WebSocketDisconnect:
        logging.info(f"WebSocket disconnected for user_id: {user_id}")
    except Exception as e:
        logging.error(f"Unhandled error in WebSocket endpoint for user_id {user_id}: {e}")
        logging.error(traceback.format_exc())
    finally:
        # Clean up resources if necessary
        # For example, if you stored the websocket in a manager, remove it here
        logging.info(f"WebSocket connection closed for user_id: {user_id}")