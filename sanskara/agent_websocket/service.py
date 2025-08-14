import asyncio
import json
import base64
import os
import traceback
import re
from urllib.parse import urlparse, parse_qs
from logger import json_logger as logger # Import the custom JSON logger

from google.adk.agents import LiveRequestQueue
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.sessions import DatabaseSessionService
from google.adk.artifacts import InMemoryArtifactService
from google.genai import types
from fastapi import WebSocket, WebSocketDisconnect

from sanskara.agent import root_agent
from sanskara.tools import get_wedding_context, get_active_workflows, get_tasks_for_wedding
from sanskara.helpers import execute_supabase_sql
from config import VOICE_NAME, SEND_SAMPLE_RATE, SESSION_SERVICE_URI
from sanskara.adk_artifacts import artifact_service


# Initialize session service, artifact service, and agent once for the application
session_service = DatabaseSessionService(db_url=SESSION_SERVICE_URI)
# artifact_service = InMemoryArtifactService()  # replaced by shared singleton
agent_instance = root_agent # Use the RootAgent as the main agent

async def websocket_endpoint(websocket: WebSocket):
    """
    Handles incoming WebSocket connections for the multimodal ADK.
    The user_id is expected as a query parameter in the WebSocket URL.
    Example: ws://localhost:8000/ws?user_id=your_user_id
    """
    await websocket.accept()
    logger.info(f"New WebSocket connection accepted from {websocket.client.host}:{websocket.client.port}")

    # Extract user_id from query parameters
    query_params = websocket.query_params
    user_id = query_params.get("user_id", "default_user_id") # Get user_id from query params

    logger.info(f"Client connected with user_id: {user_id}")
    
    # Create session for the ADK runner
    session = await session_service.create_session(
        app_name="sanskara",
        user_id=user_id,
    )
    # Send the ADK session identifier to the client for future artifact & tool calls
    try:
        logger.info(f"Session object repr: {session}")
        try:
            logger.info(f"Session dir: {dir(session)}")
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
            logger.warning("Generated synthetic session handle (none provided by ADK)")
        session.state["adk_session_id"] = session_handle
        session.state.setdefault("recent_artifacts", [])  # prevent KeyError in prompt templating
        await websocket.send_json({"type": "session", "session_id": session_handle})
        logger.info(f"Sent session id to client: {session_handle}")
    except Exception as e:
        logger.error(f"Failed to emit session id to client: {e}")

    # Always send ready after session announcement
    try:
        await websocket.send_json({"type": "ready"})
    except Exception as e:
        logger.error(f"Failed to send ready message: {e}")

    # Fetch wedding_id from user_id and prime context
    wedding_id = None
    try:
        user_wedding_query_sql = f"SELECT wedding_id FROM wedding_members WHERE user_id = '{user_id}';"
        user_wedding_result = await execute_supabase_sql(user_wedding_query_sql)

        if user_wedding_result and user_wedding_result.get("status") == "success" and user_wedding_result.get("data"):
            wedding_id = user_wedding_result["data"][0].get("wedding_id")

        if not wedding_id:
            logger.warning(f"No wedding_id found for user_id {user_id}. Cannot prime context.")
            await websocket.send_json({"type": "error", "data": "No wedding found for your user ID. Please complete onboarding."})
        else:
            # # Fetch wedding details, tasks, and workflows
            # wedding_details = await get_wedding_context(wedding_id)
            # active_workflows = await get_active_workflows(wedding_id)
            # all_tasks = await get_tasks_for_wedding(wedding_id)
            
            # Update session state with the fetched context
            session.state.update({
                "current_wedding_id": wedding_id,
                "current_user_id": user_id,
                
            })
            logger.info(f"Initial context primed for user {user_id}, wedding {wedding_id}: {session.state}")
    except Exception as e:
        logger.error(f"Error priming context for user {user_id}: {e}")
        logger.error(traceback.format_exc())
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
                            logger.info("Received end signal from client")
                            # Optionally, signal end to the live_request_queue or close queues
                        elif message.get("type") == "text":
                            logger.info(f"Received text: {message.get('data')}")
                            await text_queue.put({"data": message.get("data")})
                    except json.JSONDecodeError:
                        logger.error("Invalid JSON message received")
                    except Exception as e:
                        logger.error(f"Error processing incoming message: {e}")

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

                    logger.info(f"Processing video frame from {video_mode}")

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
                                            logger.info({
                                                "event": "ws_inline_artifact",
                                                "filename": fname,
                                                "mime_type": getattr(getattr(art, "inline_data", None), "mime_type", None),
                                            })
                                        else:
                                            logger.warning(f"Artifact not found for filename={fname} user={user_id} session={session_id}")
                                    except Exception as e:
                                        logger.error(f"load_artifact failed for {fname}: {e}")

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
                            logger.error(f"Error processing text with agent: {e}")
                            await websocket.send_json({"type": "error", "data": f"Agent error: {e}"})
                    text_queue.task_done()

            async def receive_and_process_responses_from_adk():
                # Track user and model outputs between turn completion events
                input_texts = []
                output_texts = []
                current_session_id = None

                # Flag to track if we've seen an interruption in the current turn
                interrupted = False

                # Process responses from the agent
                async for event in runner.run_live(
                    session=session,
                    live_request_queue=live_request_queue,
                    run_config=run_config,
                ):
                    # Check for turn completion or interruption using string matching
                    # This is a fallback approach until a proper API exists
                    event_str = str(event)

                    # If there's a session resumption update, store the session ID
                    if hasattr(event, 'session_resumption_update') and event.session_resumption_update:
                        update = event.session_resumption_update
                        if update.resumable and update.new_handle:
                            current_session_id = update.new_handle
                            logger.info(f"New SESSION: {current_session_id}")
                            # Send session ID to client
                            session_id_msg = json.dumps({
                                "type": "session_id", 
                                "data": current_session_id
                            })
                            await websocket.send(session_id_msg)

                    # Handle content
                    if event.content and event.content.parts:
                        for part in event.content.parts:
                            # Process audio content
                            if hasattr(part, "inline_data") and part.inline_data:
                                try:
                                    mime = getattr(part.inline_data, "mime_type", None) or ""
                                    b64_data = base64.b64encode(part.inline_data.data).decode("utf-8")
                                    if mime.startswith("audio/"):
                                        await websocket.send_json({"type": "audio", "data": b64_data, "mime": mime})
                                    elif mime.startswith("image/"):
                                        await websocket.send_json({"type": "image", "data": b64_data, "mime": mime})
                                    else:
                                        await websocket.send_json({"type": "blob", "data": b64_data, "mime": mime})
                                except Exception as e:
                                    logger.error(f"Failed to forward inline_data: {e}")

                            # Process text content
                            if hasattr(part, "text") and part.text:
                                # Check if this is user or model text based on content role
                                if hasattr(event.content, "role") and event.content.role == "user":
                                    # User text shouldn't be sent to the client
                                    input_texts.append(part.text)
                                    
                                else:
                                    # From the logs, we can see the duplicated text issue happens because
                                    # we get streaming chunks with "partial=True" followed by a final consolidated
                                    # response with "partial=None" containing the complete text

                                    # Check in the event string for the partial flag
                                    # Only process messages with "partial=True"
                                    if "partial=True" in event_str:
                                        await websocket.send_json({"type": "text", "data": part.text})
                                        output_texts.append(part.text)
                                    # Skip messages with "partial=None" to avoid duplication
                    # Check for interruption
                    if event.interrupted and not interrupted:
                        logger.info("🤐 INTERRUPTION DETECTED")
                        await websocket.send_json({
                            "type": "interrupted",
                            "data": "Response interrupted by user input"
                        })
                        interrupted = True
                    
                    # Check for turn completion
                    if event.turn_complete:
                        # Only send turn_complete if there was no interruption
                        if not interrupted:
                            logger.info("✅ Gemini done talking")
                            await websocket.send_json({
                                "type": "turn_complete",
                                "session_id": current_session_id
                            })

                        # Log collected transcriptions for debugging
                        if input_texts:
                            # Get unique texts to prevent duplication
                            unique_texts = list(dict.fromkeys(input_texts))
                            logger.info(f"Input transcription: {' '.join(unique_texts)}")
                            # send transcription to client as user_input
                            # unique_texts = list(dict.fromkeys(input_texts))
                            # logger.info(f"Input transcription: {' '.join(unique_texts)}")
                            # await websocket.send(json.dumps({
                            #     "type": "user_input",
                            #     "data": " ".join(unique_texts)
                            # }))
                        if output_texts:
                            # Get unique texts to prevent duplication
                            unique_texts = list(dict.fromkeys(output_texts))
                            logger.info(f"Output transcription: {' '.join(unique_texts)}")

                        # Reset for next turn
                        input_texts = []
                        output_texts = []
                        interrupted = False

            # Create tasks within the TaskGroup
            tg.create_task(handle_websocket_messages(), name="WebSocketMessageReceiver")
            tg.create_task(process_and_send_audio_to_adk(), name="ADKAudioSender")
            tg.create_task(handle_text_messages_with_agent(), name="AgentTextProcessor")
            tg.create_task(process_and_send_video(), name="ADKVideoSender") # Added video processing task
            tg.create_task(receive_and_process_responses_from_adk(), name="ADKResponseSender")

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user_id: {user_id}")
    except Exception as e:
        logger.error(f"Unhandled error in WebSocket endpoint for user_id {user_id}: {e}")
        logger.error(traceback.format_exc())
    finally:
        # Clean up resources if necessary
        # For example, if you stored the websocket in a manager, remove it here
        logger.info(f"WebSocket connection closed for user_id: {user_id}")