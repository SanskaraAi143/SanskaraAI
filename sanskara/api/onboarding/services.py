import json
from typing import Dict, Any, List, Optional
from datetime import date
from fastapi import HTTPException

from google.adk.models import LlmRequest
from google.adk.sessions import Session
from sanskara.sub_agents.setup_agent.agent import setup_agent
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types

from sanskara.helpers import execute_supabase_sql
import sanskara.db_queries as db_queries
from api.onboarding.models import CurrentUserOnboardingDetails, SecondPartnerDetails, WeddingDetails, PartnerOnboardingDetails,OnboardingSubmission, SecondPartnerSubmission
from logger import json_logger as logger # Import the custom JSON logger

async def _update_wedding_details(wedding_id: str,
                                  current_user_email: str,
                                  current_user_onboarding_details: CurrentUserOnboardingDetails = None,
                                  second_partner_details: SecondPartnerDetails = None,
                                  remove_other_partner_email_expected: bool = False):
    # Fetch existing wedding details to merge
    existing_wedding_query = await execute_supabase_sql(db_queries.get_wedding_details_query(wedding_id))
    if existing_wedding_query.get("status") == "error" or not existing_wedding_query.get("data"):
        logger.error(f"Failed to fetch existing wedding details for update: {existing_wedding_query.get('error')}")
        raise HTTPException(status_code=500, detail="Failed to fetch existing wedding details.")

    existing_details = existing_wedding_query["data"][0].get("details", {})
    logger.debug(f"_update_wedding_details: Initial existing_details: {existing_details}")

    partner_data = existing_details.get("partner_data", {})

    if current_user_onboarding_details:
        partner_data[current_user_email] = current_user_onboarding_details.model_dump()
        logger.debug(f"_update_wedding_details: Updated partner_data with current_user_onboarding_details: {partner_data}")
    elif second_partner_details:
        partner_data[current_user_email] = second_partner_details.model_dump()
        logger.debug(f"_update_wedding_details: Updated partner_data with second_partner_details: {partner_data}")

    existing_details["partner_data"] = partner_data

    if remove_other_partner_email_expected:
        if "other_partner_email_expected" in existing_details:
            del existing_details["other_partner_email_expected"]
            logger.debug(f"_update_wedding_details: Removed other_partner_email_expected.")

    logger.debug(f"_update_wedding_details: Final existing_details before DB update: {existing_details}")
    update_wedding_sql = db_queries.update_wedding_details_jsonb_query(
        wedding_id,
        json.dumps(existing_details)
    )
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
        logger.info(f"Both partners have submitted. Invoking SetupAgent for wedding_id: {wedding_id}.")
        
        session_service = InMemorySessionService()
        session = await session_service.create_session(
            app_name="sanskara_wedding_planner",
            user_id="setup-agent-trigger", # A dummy user ID for this trigger
            session_id=wedding_id,
        )
        # Populate session state with relevant data for SetupAgent
        session.state["wedding_id"] = wedding_id
        session.state["partner_data"] = updated_details["partner_data"]
        session.state["wedding_details"] = updated_details

        runner = Runner(
            app_name="sanskara_wedding_planner",
            agent=setup_agent,
            session_service=session_service,
        )

        user_message_content = types.Content(
            role="user",
            parts=[types.Part(text=f"Initialize wedding planning for wedding ID {wedding_id} with details: {json.dumps(updated_details)}. Both partners have completed onboarding.")]
        )

        final_response_text = "SetupAgent did not produce a final response."
        try:
            async for event in runner.run_async(user_id=session.user_id, session_id=session.id, new_message=user_message_content):
                if event.is_final_response():
                    if event.content and event.content.parts:
                        final_response_text = event.content.parts[0].text
                    elif event.actions and event.actions.escalate:
                        final_response_text = f"SetupAgent escalated: {event.error_message or 'No specific message.'}"
                    break
            
            logger.info(f"SetupAgent response for wedding_id {wedding_id}: {final_response_text}")

            # Assuming setup_agent completes successfully, update wedding status to 'active'
            update_status_sql = db_queries.update_wedding_status_query(wedding_id, 'active')
            agent_setup_response_db = await execute_supabase_sql(update_status_sql)
            if agent_setup_response_db.get("status") == "error":
                logger.error(f"Failed to update wedding status to 'active': {agent_setup_response_db.get('error')}")
                raise HTTPException(status_code=500, detail="Failed to update wedding status to 'active'.")
            logger.info(f"Wedding status updated to 'active' for wedding_id: {wedding_id}")
            
            return {"message": "Both partners submitted. SetupAgent triggered and wedding status active.", "wedding_id": str(wedding_id)}
        except Exception as e:
            logger.error(f"Error invoking SetupAgent for wedding_id {wedding_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error during SetupAgent invocation: {e}")
    else:
        return {"message": "Onboarding data updated. Waiting for other partner.", "wedding_id": str(wedding_id)}

async def _handle_first_partner_submission(user_id: str,
                                           wedding_details: WeddingDetails,
                                           current_user_onboarding_details: CurrentUserOnboardingDetails,
                                           partner_onboarding_details: PartnerOnboardingDetails):
    # Store other_partner_email_expected in the details JSONB
    initial_details = {
        "partner_data": {
            current_user_onboarding_details.email: current_user_onboarding_details.model_dump()
        },
        "partner_onboarding_details": partner_onboarding_details.model_dump(),
        "other_partner_email_expected": partner_onboarding_details.email
    }
    logger.debug(f"_handle_first_partner_submission: initial_details for new wedding: {initial_details}")

    create_wedding_sql = db_queries.create_wedding_query(
        wedding_details.wedding_name,
        wedding_details.wedding_date.isoformat(),
        wedding_details.wedding_location,
        wedding_details.wedding_tradition,
        json.dumps(initial_details), # Pass the complete initial JSONB
        wedding_details.wedding_style
    )
    logger.debug(f"_handle_first_partner_submission: create_wedding_sql: {create_wedding_sql}")
    create_result = await execute_supabase_sql(create_wedding_sql)
    if create_result.get("status") == "error" or not create_result.get("data"):
        logger.error(f"Failed to create new wedding: {create_result.get('error')}")
        raise HTTPException(status_code=500, detail="Failed to create new wedding.")

    wedding_id = create_result["data"][0]["wedding_id"]
    logger.info(f"New wedding created with ID: {wedding_id} for {current_user_onboarding_details.email}. Other partner expected: {partner_onboarding_details.email}")

    await _link_user_to_wedding(user_id, wedding_id, current_user_onboarding_details.role)

    # Update the user's entry to set wedding_id and remove old fields (handled by migration script, but API should not expect them)
    # This part is implicitly handled by the user's instruction that these are removed by migration.
    # The API just needs to ensure it doesn't send them.

    return {"message": "First partner data received. Waiting for other partner.", "wedding_id": str(wedding_id)}

async def _handle_second_partner_submission(user_id: str, wedding_id: str, second_partner_details: SecondPartnerDetails):
    # Verify that the wedding_id exists and that the second partner's email matches other_partner_email_expected
    find_wedding_sql = db_queries.get_wedding_details_query(wedding_id)
    wedding_query = await execute_supabase_sql(find_wedding_sql)
    existing_wedding_data = wedding_query.get("data")

    if not existing_wedding_data:
        logger.error(f"Wedding with ID {wedding_id} not found for second partner submission.")
        raise HTTPException(status_code=404, detail="Wedding not found.")

    existing_wedding = existing_wedding_data[0]
    wedding_details_jsonb = existing_wedding.get("details", {})
    logger.debug(f"_handle_second_partner_submission: Retrieved wedding_details_jsonb: {wedding_details_jsonb}")
    other_partner_email_expected = wedding_details_jsonb.get("other_partner_email_expected")
    logger.debug(f"_handle_second_partner_submission: Extracted other_partner_email_expected: {other_partner_email_expected}")

    if not other_partner_email_expected or other_partner_email_expected != second_partner_details.email:
        logger.error(f"Second partner email mismatch for wedding {wedding_id}. Expected {other_partner_email_expected}, got {second_partner_details.email}.")
        raise HTTPException(status_code=400, detail="Email does not match expected partner email for this wedding.")

    logger.info(f"Found existing wedding for second partner {second_partner_details.email}, wedding_id: {wedding_id}")

    # Update wedding details JSONB to mark second partner onboarding complete
    # and potentially remove other_partner_email_expected
    await _update_wedding_details(
        wedding_id,
        second_partner_details.email,
        second_partner_details=second_partner_details,
        remove_other_partner_email_expected=True # Mark onboarding complete
    )

    await _link_user_to_wedding(user_id, wedding_id, second_partner_details.role)

    # Update the second partner's users table entry to set their wedding_id.
    # This is handled by a migration script on the database, the API just needs to ensure it doesn't send them.

    return await _check_and_trigger_setup_agent(wedding_id, second_partner_details.email)

async def _update_existing_partner_details(user_id: str, wedding_id: str, user_email: str, user_role: str, submission: Any):
    logger.info(f"User {user_email} already associated with wedding_id: {wedding_id}. Updating details and wedding_members.")

    if isinstance(submission, OnboardingSubmission):
        current_user_onboarding_details = submission.current_user_onboarding_details
        partner_onboarding_details = submission.partner_onboarding_details
        
        logger.debug(f"_update_existing_partner_details (OnboardingSubmission): Processing update for user {user_email}.")
        logger.debug(f"_update_existing_partner_details (OnboardingSubmission): current_user_onboarding_details: {current_user_onboarding_details.model_dump()}")
        logger.debug(f"_update_existing_partner_details (OnboardingSubmission): partner_onboarding_details: {partner_onboarding_details.model_dump()}")

        # Update current user's partner data
        await execute_supabase_sql(db_queries.update_wedding_details_jsonb_field_query(
            wedding_id,
            ["partner_data", user_email],
            current_user_onboarding_details.model_dump()
        ))
        
        # Update partner onboarding details and expected email
        await execute_supabase_sql(db_queries.update_wedding_details_jsonb_field_query(
            wedding_id,
            ["partner_onboarding_details"],
            partner_onboarding_details.model_dump()
        ))
        await execute_supabase_sql(db_queries.update_wedding_details_jsonb_field_query(
            wedding_id,
            ["other_partner_email_expected"],
            partner_onboarding_details.email
        ))
    elif isinstance(submission, SecondPartnerSubmission):
        second_partner_details = submission.current_partner_details
        await _update_wedding_details(
            wedding_id,
            user_email,
            second_partner_details=second_partner_details
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid submission type for existing partner update.")

    await _add_user_to_wedding_members(user_id, wedding_id, user_role) # Ensure role is updated/inserted
    return await _check_and_trigger_setup_agent(wedding_id, user_email)