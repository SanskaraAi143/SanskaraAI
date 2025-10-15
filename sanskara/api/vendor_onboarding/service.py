import asyncio
import json
import base64
import os
import traceback
import logging
import uuid
from dotenv import load_dotenv
from starlette.websockets import WebSocketState

try:
    from logging_setup import setup_logging
except ImportError:
    from logging_setup import setup_logging

load_dotenv()

from google.adk.agents import LiveRequestQueue
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.sessions import DatabaseSessionService
from google.genai import types
from fastapi import WebSocket, WebSocketDisconnect
from sanskara.sub_agents.form_filling_agent.agent import get_form_filling_agent
from config import VOICE_NAME, SEND_SAMPLE_RATE, SESSION_SERVICE_URI
from sanskara.adk_artifacts import artifact_service # Keep this if artifact_service is still needed elsewhere, otherwise remove

session_service = DatabaseSessionService(db_url=SESSION_SERVICE_URI)

async def websocket_endpoint(websocket: WebSocket, user_type: str = "vendor"): # Added user_type as query parameter
    setup_logging()
    logging.getLogger().setLevel(logging.DEBUG)
    await websocket.accept()
    logging.info(f"New WebSocket connection for form-filling from {websocket.client.host}:{websocket.client.port} for user_type={user_type}")

    user_id = str(uuid.uuid4()) # In a real app, this would come from authentication
    logging.info(f"Generated temporary user_id for form-filling session: {user_id}")

    # Dynamically get the agent based on user_type
    agent_instance = get_form_filling_agent(user_type)

    try:
        await _run_session(websocket, user_id, agent_instance)
    except WebSocketDisconnect:
        logging.info("WebSocket disconnected for form-filling.")
    except Exception as e:
        logging.error(f"Unhandled error in form-filling WebSocket endpoint: {e}")
        logging.error(traceback.format_exc())
    finally:
        logging.info("WebSocket connection closed for form-filling.")

async def _run_session(websocket: WebSocket, user_id: str, agent_instance: Agent): # Added agent_instance parameter
    adk_session = await session_service.create_session(app_name="sanskara_form_filling", user_id=user_id)

    runner = Runner(
        app_name="sanskara_form_filling",
        agent=agent_instance,
        session_service=session_service,
        # As per the latest design, artifact_service is not used for file processing via agent
        # However, if other agents or parts of the system use it, it can remain.
        # For this specific flow, it's not directly integrated with the form_filling_agent.
        # If it's truly not used at all, it can be removed from the import and Runner init.
        artifact_service=artifact_service,
    )

    live_request_queue = LiveRequestQueue()

    _Modality = getattr(types, "Modality", None)
    _response_modalities = [getattr(_Modality, "AUDIO")] if _Modality and hasattr(_Modality, "AUDIO") else None

    run_config = RunConfig(
        streaming_mode=StreamingMode.BIDI,
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=VOICE_NAME)
            )
        ),
        response_modalities=_response_modalities,
        output_audio_transcription=types.AudioTranscriptionConfig(),
        input_audio_transcription=types.AudioTranscriptionConfig(),
    )

    audio_queue = asyncio.Queue()

    async def handle_websocket_messages():
        async for raw in websocket.iter_text():
            try:
                message = json.loads(raw)
                if message.get("type") == "audio":
                    audio_bytes = base64.b64decode(message.get("data", ""))
                    await audio_queue.put(audio_bytes)
            except Exception as e:
                logging.error(f"Error processing incoming message: {e}")

    async def process_and_send_audio_to_adk():
        while True:
            data = await audio_queue.get()
            if data is None:
                break
            live_request_queue.send_realtime(
                types.Blob(data=data, mime_type=f"audio/pcm;rate={SEND_SAMPLE_RATE}")
            )
            audio_queue.task_done()

    async def receive_and_process_responses_from_adk():
        interrupted = False
        async for event in runner.run_live(
            session=adk_session,
            live_request_queue=live_request_queue,
            run_config=run_config,
        ):
            if event.interrupted and not interrupted:
                if websocket.client_state == WebSocketState.CONNECTED:
                    logging.info("🤐 INTERRUPTION DETECTED")
                    await websocket.send_json(
                        {
                            "type": "interrupted",
                            "data": "Response interrupted by user input",
                        }
                    )
                interrupted = True

            if event.content and event.content.parts:
                for part in event.content.parts:
                    if websocket.client_state != WebSocketState.CONNECTED:
                        logging.info("WebSocket disconnected during content processing, stopping.")
                        break
                    if hasattr(part, "inline_data") and part.inline_data:
                        try:
                            mime = getattr(part.inline_data, "mime_type", "")
                            b64_data = base64.b64encode(part.inline_data.data).decode("utf-8")
                            await websocket.send_json({"type": "audio", "data": b64_data, "mime": mime})
                        except Exception as e:
                            logging.error(f"Failed to forward inline_data: {e}")
                    if hasattr(part, "text") and part.text:
                        await websocket.send_json({"type": "text", "data": part.text})

            if event.turn_complete:
                if websocket.client_state != WebSocketState.CONNECTED:
                    logging.info("WebSocket disconnected before turn complete.")
                elif not interrupted:
                    logging.info("✅ Gemini done talking")
                    await websocket.send_json({"type": "turn_complete"})
                interrupted = False

    logging.info("Starting TaskGroup for live form-filling session.")
    async with asyncio.TaskGroup() as tg:
        tg.create_task(handle_websocket_messages())
        tg.create_task(process_and_send_audio_to_adk())
        tg.create_task(receive_and_process_responses_from_adk())