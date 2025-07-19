import asyncio
import json
import base64
import logging
import os
import traceback

from google.adk.agents import LiveRequestQueue
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.sessions import DatabaseSessionService
from google.genai import types
from google.adk.tools import google_search
from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any,List
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import date

load_dotenv()

from common import (
    BaseWebSocketServer,
    logger,
    MODEL,
    VOICE_NAME,
    SEND_SAMPLE_RATE,
    SYSTEM_INSTRUCTION,
)

app = FastAPI(title="Sanskara AI Wedding Planner")
onboarding_router = APIRouter()

from shared_libraries.helpers import execute_supabase_sql
from shared_libraries import db_queries
from typing import Optional

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
    # This function is now a wrapper for _add_user_to_wedding_members
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

# --- ADD THIS CORS MIDDLEWARE SECTION ---

# Define the origins that are allowed to make requests to your API.
# Using ["*"] is the most permissive. For production, you might want to restrict this
# to the actual domain of your frontend (e.g., "http://your-frontend-domain.com").
origins = [
    "http://localhost",
    "http://localhost:8080", # Add other ports if you use them
    "http://127.0.0.1",
    "http://127.0.0.1:8080",
    "null", # Important for requests from `file:///` URLs (opening the HTML file directly)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods, including POST, GET, and OPTIONS
    allow_headers=["*"],  # Allows all headers
)

class MultimodalADKServer(BaseWebSocketServer):
    def __init__(self, host="0.0.0.0", port=8765):
        super().__init__(host, port)

        self.agent = Agent(
            name="sanskara_wedding_planner",
            model=MODEL,
            instruction=SYSTEM_INSTRUCTION,
            tools=[google_search],
        )

        self.session_service = DatabaseSessionService(db_url=os.getenv("DATABASE_URL", "sqlite:///sessions.db"))

    async def process_audio(self, websocket, client_id):
        self.active_clients[client_id] = websocket

        session = await self.session_service.create_session(
            app_name="multimodal_assistant",
            user_id=f"user_{client_id}",
            session_id=f"session_{client_id}",
        )
        
        runner = Runner(
            app_name="multimodal_assistant",
            agent=self.agent,
            session_service=self.session_service,
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
            response_modalities=["AUDIO"],
            output_audio_transcription=types.AudioTranscriptionConfig(),
            input_audio_transcription=types.AudioTranscriptionConfig(),
        )

        audio_queue = asyncio.Queue()
        text_queue = asyncio.Queue()

        async with asyncio.TaskGroup() as tg:
            async def handle_websocket_messages():
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        if data.get("type") == "audio":
                            audio_bytes = base64.b64decode(data.get("data", ""))
                            await audio_queue.put(audio_bytes)
                        elif data.get("type") == "end":
                            logger.info("Received end signal from client")
                        elif data.get("type") == "text":
                            logger.info(f"Received text: {data.get('data')}")
                            await text_queue.put({"data": data.get("data")})
                    except json.JSONDecodeError:
                        logger.error("Invalid JSON message received")
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")

            async def process_and_send_audio():
                while True:
                    data = await audio_queue.get()
                    live_request_queue.send_realtime(
                        types.Blob(
                            data=data,
                            mime_type=f"audio/pcm;rate={SEND_SAMPLE_RATE}",
                        )
                    )
                    audio_queue.task_done()

            async def handle_text_messages(session):
                while True:
                    text_data = await text_queue.get()
                    text_content = text_data.get("data", "")
                    if text_content:
                        # Process the message using the agent and session
                        agent_response = await self.agent.process_message(session, text_content)
                        await websocket.send(json.dumps({"type": "text", "data": agent_response}))
                    text_queue.task_done()

            async def receive_and_process_responses():
                async for event in runner.run_live(
                    session=session,
                    live_request_queue=live_request_queue,
                    run_config=run_config,
                ):
                    if event.content and event.content.parts:
                        for part in event.content.parts:
                            if hasattr(part, "inline_data") and part.inline_data:
                                b64_audio = base64.b64encode(part.inline_data.data).decode("utf-8")
                                await websocket.send(json.dumps({"type": "audio", "data": b64_audio}))

                            if hasattr(part, "text") and part.text:
                                await websocket.send(json.dumps({"type": "text", "data": part.text}))

            tg.create_task(handle_websocket_messages(), name="MessageHandler")
            tg.create_task(process_and_send_audio(), name="AudioProcessor")
            tg.create_task(handle_text_messages(), name="TextHandler")
            tg.create_task(receive_and_process_responses(), name="ResponseHandler")


import uvicorn

@app.on_event("startup")
async def startup_event():
    server = MultimodalADKServer()
    asyncio.create_task(server.start())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
