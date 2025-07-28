import asyncio
import json
import base64
import logging
import os
import traceback
from urllib.parse import urlparse, parse_qs
import agentops


from google.adk.agents import LiveRequestQueue
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.sessions import DatabaseSessionService
from google.genai import types
from sanskara.agent import root_agent
from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from fastapi.middleware.cors import CORSMiddleware
from datetime import date

# Assuming these are available from sanskara.common or defined here if common.py is no longer used for these
# If common.py is still used, ensure these are correctly imported from it.
# For this refactor, I'll assume they are available directly or through your existing imports.
# from sanskara.common import logger, MODEL, VOICE_NAME, SEND_SAMPLE_RATE, SYSTEM_INSTRUCTION
logger = logging.getLogger() # Use the existing logger
MODEL = "gemini-1.5-flash" # Placeholder, ensure this comes from your common config
VOICE_NAME = "Puck" # Placeholder
SEND_SAMPLE_RATE = 16000 # Placeholder
SYSTEM_INSTRUCTION = "You are the Sanskara AI Wedding Planner." # Placeholder


# Import test function and context tools
from tests.test_setup_agent_invocation import run_setup_agent_test
from sanskara.tools import get_wedding_context, get_active_workflows, get_tasks_for_wedding
from sanskara.helpers import execute_supabase_sql
import sanskara.db_queries as db_queries

load_dotenv()

app = FastAPI(title="Sanskara AI Wedding Planner")
onboarding_router = APIRouter()

# --- Pydantic Models (as in your original file) ---
class TeamworkPlan(BaseModel):
    """Defines the structure for the teamwork and responsibilities section."""
    venue_decor: str
    catering: str
    guest_list: str
    sangeet_entertainment: str

class PartnerDetails(BaseModel):
    """
    Represents the detailed information collected from the partner filling out the form.
    This corresponds to the 'current_partner_details' object in the payload.
    """
    # --- Step 1: Core Foundation ---
    name: str
    email: str
    phone: Optional[str] = None
    role: str  # "Bride" or "Groom"
    partner_name: str
    partner_email: str
    wedding_city: str
    wedding_date: date

    # --- Step 2: Vision & Vibe ---
    wedding_style: Optional[str] = None
    other_style: Optional[str] = None
    color_theme: Optional[str] = None
    attire_main: Optional[str] = None
    attire_other: Optional[str] = None

    # --- Step 3: Cultural Heartbeat ---
    cultural_background: str
    ceremonies: List[str] = []
    custom_instructions: Optional[str] = None

    # --- Step 4: Teamwork Plan ---
    teamwork_plan: TeamworkPlan

    # --- Step 5: Budget & Priorities ---
    guest_estimate: Optional[str] = None
    guest_split: Optional[str] = None
    budget_range: Optional[str] = None
    budget_flexibility: str
    priorities: List[str] = []

# MODEL 2: For the SECOND partner's submission (new and streamlined)
class SecondPartnerDetails(BaseModel):
    """The focused details provided ONLY by the second partner."""
    name: str
    email: str
    role: str
    cultural_background: str
    ceremonies: List[str] = []
    budget_range: Optional[str] = None
    priorities: List[str] = []
    teamwork_agreement: bool # The crucial consensus flag

class OnboardingSubmission(BaseModel):
    current_partner_email: str
    other_partner_email: Optional[str] = None # Provided by the first partner
    current_partner_details: PartnerDetails

class SecondPartnerSubmission(BaseModel):
    current_partner_email: str
    current_partner_details: SecondPartnerDetails

# --- Helper Functions (as in your original file) ---
async def _update_wedding_details(wedding_id: str, current_partner_email: str, current_partner_details_json: str):
    update_wedding_sql = db_queries.update_wedding_details_query(wedding_id, current_partner_email, current_partner_details_json)
    update_result = await execute_supabase_sql(update_wedding_sql)
    if update_result.get("status") == "error":
        logger.error(f"Failed to update wedding details: {update_result.get('error')}")
        raise HTTPException(status_code=500, detail="Failed to update wedding details.")
    return update_result

async def _add_user_to_wedding_members(user_id: str, wedding_id: str, role: str):
    add_member_sql = db_queries.add_wedding_member_query(user_id, wedding_id, role)
    add_member_result = await execute_supabase_sql(add_member_sql)
    if add_member_result.get("status") == "error":
        logger.error(f"Failed to add user {user_id} to wedding {wedding_id} with role {role}: {add_member_result.get('error')}")
        raise HTTPException(status_code=500, detail="Failed to add user to wedding members.")
    return add_member_result

async def _link_user_to_wedding(user_id: str, wedding_id: str, role: str):
    return await _add_user_to_wedding_members(user_id, wedding_id, role)

async def _check_and_trigger_setup_agent(wedding_id: str, current_partner_email: str) -> dict:
    logger.debug(f"Attempting to fetch updated wedding details for wedding_id: {wedding_id}")
    updated_wedding_details_query = await execute_supabase_sql(db_queries.get_wedding_details_query(wedding_id))
    logger.debug(f"Result of fetching updated wedding details: {updated_wedding_details_query}")
    updated_details = updated_wedding_details_query.get("data")[0].get("details", {})

    expected_other_email = updated_details.get("other_partner_email_expected")
    if updated_details.get("partner_data") and \
       current_partner_email in updated_details["partner_data"] and \
       expected_other_email and \
       expected_other_email in updated_details["partner_data"]:
        logger.info(f"Both partners have submitted for wedding_id: {wedding_id}. Triggering SetupAgent.")
        update_status_sql = db_queries.update_wedding_status_query(wedding_id, 'onboarding_complete')
        await execute_supabase_sql(update_status_sql)
        # TODO: Trigger SetupAgent here
        if run_setup_agent_test(updated_details, wedding_id):  # Placeholder for actual agent invocation
            logger.info(f"SetupAgent successfully triggered for wedding_id: {wedding_id}")
            # update the wedding status to 'active'
            update_status_sql = db_queries.update_wedding_status_query(wedding_id, 'active')
            agent_setup_respone = await execute_supabase_sql(update_status_sql)
            if agent_setup_respone.get("status") == "error":
                logger.error(f"Failed to update wedding status to 'active': {agent_setup_respone.get('error')}")
                raise HTTPException(status_code=500, detail="Failed to update wedding status to 'active'.")
            logger.info(f"Wedding status updated to 'active' for wedding_id: {wedding_id}")
        return {"message": "Both partners submitted. SetupAgent triggered (placeholder).", "wedding_id": str(wedding_id)}
    else:
        return {"message": "Onboarding data updated. Waiting for other partner.", "wedding_id": str(wedding_id)}

async def _handle_first_partner_submission(email: str, details_json: str, other_partner_email: str):
    create_wedding_sql = db_queries.create_wedding_query(email, details_json, other_partner_email)
    create_result = await execute_supabase_sql(create_wedding_sql)
    if create_result.get("status") == "error" or not create_result.get("data"):
        logger.error(f"Failed to create new wedding: {create_result.get('error')}")
        raise HTTPException(status_code=500, detail="Failed to create new wedding.")

    wedding_id = create_result["data"][0]["wedding_id"]
    logger.info(f"New wedding created with ID: {wedding_id} for {email}. Other partner expected: {other_partner_email}")

    # We need the user_id from the users table to link to wedding_members
    user_query = await execute_supabase_sql(db_queries.get_user_and_wedding_info_by_email_query(email))
    user_data = user_query.get("data")
    if not user_data:
        logger.error(f"User with email {email} not found after wedding creation.")
        raise HTTPException(status_code=500, detail="User not found after wedding creation.")
    user_id = user_data[0]["user_id"]

    # The role for the first partner is extracted from PartnerDetails
    first_partner_details_obj = PartnerDetails.model_validate(json.loads(details_json))
    role = first_partner_details_obj.role

    await _link_user_to_wedding(user_id, wedding_id, role)

    return {"message": "First partner data received. Waiting for other partner.", "wedding_id": str(wedding_id)}

async def _handle_second_partner_submission(email: str, details_json: str):
    find_wedding_sql = db_queries.find_wedding_by_other_partner_email_query(email)
    wedding_query = await execute_supabase_sql(find_wedding_sql)
    existing_wedding = wedding_query.get("data")
    print(existing_wedding)

    if existing_wedding:
        wedding_id = existing_wedding[0]["wedding_id"]
        logger.info(f"Found existing wedding for second partner {email}, wedding_id: {wedding_id}")

        await _update_wedding_details(wedding_id, email, details_json)

        # We need the user_id from the users table to link to wedding_members
        user_query = await execute_supabase_sql(db_queries.get_user_and_wedding_info_by_email_query(email))
        user_data = user_query.get("data")
        if not user_data:
            logger.error(f"User with email {email} not found for second partner submission.")
            raise HTTPException(status_code=500, detail="User not found for second partner submission.")
        user_id = user_data[0]["user_id"]

        # The role for the second partner is extracted from SecondPartnerDetails
        second_partner_details_obj = SecondPartnerDetails.model_validate(json.loads(details_json))
        role = second_partner_details_obj.role

        await _link_user_to_wedding(user_id, wedding_id, role)

        return await _check_and_trigger_setup_agent(wedding_id, email)

    else:
        logger.error(f"Second partner {email} submitted, but no matching wedding found where they are the expected other partner.")
        raise HTTPException(status_code=404, detail="No matching wedding found for this partner's email. Please ensure the first partner has initiated the wedding setup or that your email is correct.")

async def _update_existing_partner_details(email: str, details_json: str, wedding_id: str, user_id: str, role: str):
    logger.info(f"Current partner {email} already associated with wedding_id: {wedding_id}. Updating details and wedding_members.")
    await _update_wedding_details(wedding_id, email, details_json)
    await _add_user_to_wedding_members(user_id, wedding_id, role) # Ensure role is updated/inserted
    return await _check_and_trigger_setup_agent(wedding_id, email)

@onboarding_router.post("/submit")
async def submit_onboarding_data(submission: OnboardingSubmission | SecondPartnerSubmission):
    logger.info(f"Received onboarding submission from {submission.current_partner_email}")

    current_partner_email = submission.current_partner_email
    other_partner_email = None
    if type(submission) is OnboardingSubmission:
        other_partner_email = submission.other_partner_email

    current_partner_details_json = submission.current_partner_details.model_dump_json()

    # Extract role from the submission details
    current_partner_role = submission.current_partner_details.role

    user_query_result = await execute_supabase_sql(db_queries.get_user_and_wedding_info_by_email_query(current_partner_email))
    existing_user_data = user_query_result.get("data")

    user_id = None
    existing_wedding_id = None
    existing_role = None

    if existing_user_data:
        user_id = existing_user_data[0].get("user_id")
        existing_wedding_id = existing_user_data[0].get("wedding_id") # This will now come from wedding_members join
        existing_role = existing_user_data[0].get("role")

    if not user_id:
        logger.error(f"User with email {current_partner_email} not found in the users table.")
        raise HTTPException(status_code=404, detail=f"User with email {current_partner_email} not found. Please ensure you have signed up.")

    if existing_wedding_id:
        # User exists and is already linked to a wedding via wedding_members
        return await _update_existing_partner_details(current_partner_email, current_partner_details_json, existing_wedding_id, user_id, current_partner_role)
    elif other_partner_email:
        # First partner submission
        return await _handle_first_partner_submission(current_partner_email, current_partner_details_json, other_partner_email)
    else:
        # Second partner submission
        return await _handle_second_partner_submission(current_partner_email, current_partner_details_json)

@onboarding_router.get("/partner-details")
async def get_partner_details(email: str):
    logger.info(f"Received request for partner details for email: {email}")

    # Search for a wedding where this email is the expected other partner
    find_wedding_sql = db_queries.get_wedding_by_expected_partner_email_query(email)
    wedding_query = await execute_supabase_sql(find_wedding_sql)
    wedding_data = wedding_query.get("data")

    if not wedding_data:
        raise HTTPException(status_code=404, detail="No wedding found associated with this email as an expected partner.")

    wedding_id = wedding_data[0]["wedding_id"]
    wedding_details = wedding_data[0]["details"]
    partner_data = wedding_details.get("partner_data", {})
    other_partner_email_expected = wedding_details.get("other_partner_email_expected")

    first_partner_email = None
    # Determine who the first partner was (the one who provided other_partner_email_expected)
    for p_email, p_details in partner_data.items():
        if p_email != other_partner_email_expected:
            first_partner_email = p_email
            break

    first_partner_info = {}
    if first_partner_email and first_partner_email in partner_data:
        first_partner_info = partner_data[first_partner_email]

    # Placeholder for proposed plan/responsibilities
    proposed_plan = {
        "message": "Proposed plan and responsibilities will be generated by the SetupAgent after both partners onboard.",
        "example_responsibility": "Budget management",
        "example_task": "Venue selection"
    }

    return {
        "wedding_id": str(wedding_id),
        "first_partner_name": first_partner_info.get("name", "N/A"),
        "first_partner_details": first_partner_info,
        "wedding_details": wedding_details,
        "proposed_plan_responsibilities": proposed_plan
    }

app.include_router(onboarding_router, prefix="/onboarding", tags=["Onboarding"])

# --- CORS MIDDLEWARE ---
origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://127.0.0.1",
    "http://127.0.0.1:8080",
    "https://sanskaraai.com",
    "null",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- FastAPI WebSocket Endpoint ---
# Initialize session service and agent once for the application
session_service = DatabaseSessionService(db_url=os.getenv("DATABASE_URL", "sqlite:///sessions.db"))
agent_instance = root_agent # Use the RootAgent as the main agent

@app.websocket("/ws")
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
    await websocket.send_json({"type": "ready"})

    # Create session for the ADK runner
    session = await session_service.create_session(
        app_name="multimodal_assistant",
        user_id=user_id,
    )

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
            # Fetch wedding details, tasks, and workflows
            wedding_details = await get_wedding_context(wedding_id)
            active_workflows = await get_active_workflows(wedding_id)
            all_tasks = await get_tasks_for_wedding(wedding_id)
            # wedding_id = "123"
            # wedding_details = {"wedding_id": wedding_id, "details": "Sample wedding details"}  # Placeholder
            # active_workflows = [{"workflow_id": "1", "status": "active"}]
            # all_tasks = [{"task_id": "1", "description": "Sample task"}]
            
            # Update session state with the fetched context
            session.state.update({
                "current_wedding_id": wedding_id,
                "current_user_id": user_id,
                "wedding_details": wedding_details,
                "active_workflows": active_workflows,
                "all_tasks": all_tasks
            })

            logger.info(f"Initial context primed for user {user_id}, wedding {wedding_id}: "
                        f"Details: {bool(wedding_details)}, "
                        f"Workflows: {len(active_workflows)}, "
                        f"Tasks: {len(all_tasks)}")
    except Exception as e:
        logger.error(f"Error priming context for user {user_id}: {e}")
        logger.error(traceback.format_exc())
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
                            #agent_response = await agent_instance.process_message(session, text_content)
                            live_request_queue.send_content(
                                types.Content(
                                    role="user",
                                    parts=[types.Part(text=text_content)]
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
                                b64_audio = base64.b64encode(part.inline_data.data).decode("utf-8")
                                await websocket.send_json({"type": "audio", "data": b64_audio})

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

import uvicorn
# --- Main entry point for Uvicorn ---
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8765)
