import asyncio
import json
import base64
import os
import traceback
from urllib.parse import urlparse, parse_qs
from logger import json_logger as logger # Import the custom JSON logger

from google.adk.agents import LiveRequestQueue
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.sessions import DatabaseSessionService
from google.genai import types
from fastapi import WebSocket, WebSocketDisconnect

from sanskara.agent import orchestrator_agent
from sanskara.tools import get_wedding_context, get_active_workflows, get_tasks_for_wedding
from sanskara.helpers import execute_supabase_sql
from config import VOICE_NAME, SEND_SAMPLE_RATE, DATABASE_URL

# logger = logging.getLogger(__name__) # Replaced with json_logger import

# Initialize session service and agent once for the application
session_service = DatabaseSessionService(db_url=DATABASE_URL)
agent_instance = orchestrator_agent # Use the OrchestratorAgent as the main agent

async def websocket_endpoint(websocket: WebSocket):
    """
    Handles incoming WebSocket connections for the multimodal ADK.
    The user_id is expected as a query parameter in the WebSocket URL.
    Example: ws://localhost:8000/ws?user_id=your_user_id
    """
    await websocket.accept()
    logger.info(f"New WebSocket connection accepted from {websocket.client.host}:{websocket.client.port}")
    logger.debug(f"WebSocket client details: host={websocket.client.host}, port={websocket.client.port}")
    logger.debug(f"WebSocket client details: host={websocket.client.host}, port={websocket.client.port}")

    # Extract user_id from query parameters
    query_params = websocket.query_params
    user_id = query_params.get("user_id", "default_user_id") # Get user_id from query params

    logger.info(f"Client connected with user_id: {user_id}")
    await websocket.send_json({"type": "ready"})
    logger.debug(f"WebSocket session created for user_id: {user_id}")
    logger.debug(f"WebSocket session created for user_id: {user_id}")
    orchestrator_agent.model= "gemini-2.0-flash-live-001"
    # Create session for the ADK runner
    session = await session_service.create_session(
        app_name="multimodal_assistant",
        user_id=user_id,
    )

    # Fetch wedding_id and user_role from user_id and prime context
    wedding_id = None
    user_role = None
    try:
        user_wedding_query_sql = f"SELECT wedding_id, role FROM wedding_members WHERE user_id = '{user_id}';"
        user_wedding_result = await execute_supabase_sql(user_wedding_query_sql)

        if user_wedding_result and user_wedding_result.get("status") == "success" and user_wedding_result.get("data"):
            wedding_id = user_wedding_result["data"][0].get("wedding_id")
            user_role = user_wedding_result["data"][0].get("role")

        if not wedding_id:
            logger.warning(f"No wedding_id found for user_id {user_id}. Cannot prime context.")
            await websocket.send_json({"type": "error", "data": "No wedding found for your user ID. Please complete onboarding."})
        else:
            # The context priming for the agent itself is handled by the before_agent_callback
            # We still need to store these in session.state for the callback to pick them up
            session.state.update({
                "wedding_id": wedding_id,
                "user_id": user_id,
                "user_role": user_role
            })
            logger.info(f"Session state updated for user {user_id}, wedding {wedding_id}: User Role: {user_role}")
            # Bind context to logger for this session
            logger.bind(wedding_id=wedding_id, user_id=user_id).info("Context primed for WebSocket session.")
    except Exception as e:
        logger.error(f"Error priming context for user {user_id}: {e}", exc_info=True)
        await websocket.send_json({"type": "error", "data": f"Server error priming context: {e}"})
        await websocket.close()
        return # Exit the handler if context priming fails

    runner = Runner(
        app_name="multimodal_assistant",
        agent=agent_instance,
        session_service=session_service,
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
                logger.debug("Starting WebSocket message handler.")
                async for message in websocket.iter_json(): # Use iter_json for convenience
                    try:
                        message_type = message.get("type")
                        logger.debug(f"Received WebSocket message type: {message_type}")
                        if message_type == "audio":
                            audio_bytes = base64.b64decode(message.get("data", ""))
                            await audio_queue.put(audio_bytes)
                            logger.debug("Audio data put into queue.")
                        elif message_type == "video":
                            # Decode base64 video frame
                            video_bytes = base64.b64decode(message.get("data", ""))
                            # Get video mode metadata if available
                            video_mode = message.get("mode", "webcam")  # Default to webcam if not specified
                            # Put video frame in queue for processing with metadata
                            await video_queue.put({
                                "data": video_bytes,
                                "mode": video_mode
                            })
                            logger.debug(f"Video data ({video_mode}) put into queue.")
                        elif message_type == "end":
                            logger.info("Received end signal from client.")
                            # Optionally, signal end to the live_request_queue or close queues
                        elif message_type == "text":
                            text_data = message.get('data')
                            logger.info(f"Received text: {text_data}")
                            await text_queue.put({"data": text_data})
                            logger.debug("Text data put into queue.")
                        else:
                            logger.warning(f"Unknown WebSocket message type received: {message_type}")
                    except json.JSONDecodeError:
                        logger.error("Invalid JSON message received.", exc_info=True)
                    except Exception as e:
                        logger.error(f"Error processing incoming message: {e}", exc_info=True)

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

                    logger.debug(f"Processing video frame from {video_mode}.")

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
                            #agent_response = await agent_instance.process_message(session, text_content)
                            live_request_queue.send_content(
                                types.Content(
                                    role="user",
                                    parts=[types.Part(text=text_content)]
                                )
                            )
                            #await websocket.send_json({"type": "text", "data": agent_response})
                        except Exception as e:
                            logger.error(f"Error processing text with agent: {e}", exc_info=True)
                            await websocket.send_json({"type": "error", "data": f"Agent error: {e}"})
                    text_queue.task_done()
                logger.debug("Text message handler finished.")

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
                            logger.info(f"New ADK Session started: {current_session_id}")
                            # Send session ID to client
                            session_id_msg = json.dumps({
                                "type": "session_id",
                                "data": current_session_id
                            })
                            await websocket.send(session_id_msg)
                            logger.debug(f"Sent session ID to client: {current_session_id}")

                    # Handle content
                    if event.content and event.content.parts:
                        for part in event.content.parts:
                            # Process audio content
                            if hasattr(part, "inline_data") and part.inline_data:
                                b64_audio = base64.b64encode(part.inline_data.data).decode("utf-8")
                                await websocket.send_json({"type": "audio", "data": b64_audio})
                                logger.debug("Sent audio data to client.")
                                logger.debug("Sent audio data to client.")

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
                                        logger.debug(f"Sent partial text to client: {part.text}")
                                    # Skip messages with "partial=None" to avoid duplication
                    # Check for interruption
                    if event.interrupted and not interrupted:
                        logger.info("🤐 INTERRUPTION DETECTED - Response interrupted by user input.")
                        await websocket.send_json({
                            "type": "interrupted",
                            "data": "Response interrupted by user input"
                        })
                        interrupted = True
                        logger.debug("Interruption signal sent to client.")
                    
                    # Check for turn completion
                    if event.turn_complete:
                        # Only send turn_complete if there was no interruption
                        if not interrupted:
                            logger.info("✅ Gemini done talking - Turn complete.")
                            await websocket.send_json({
                                "type": "turn_complete",
                                "session_id": current_session_id
                            })
                            logger.debug(f"Turn complete signal sent to client for session: {current_session_id}")

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
                        logger.debug("Received and processed responses from ADK.")
                        logger.debug("Received and processed responses from ADK.")

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
        logger.error(f"Unhandled error in WebSocket endpoint for user_id {user_id}: {e}", exc_info=True)
    finally:
        # Clean up resources if necessary
        # For example, if you stored the websocket in a manager, remove it here
        logger.info(f"WebSocket connection closed for user_id: {user_id}.")