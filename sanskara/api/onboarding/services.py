import json
from typing import Dict, Any, List, Optional
from datetime import date
from fastapi import HTTPException, BackgroundTasks

from google.adk.models import LlmRequest
from google.adk.sessions import Session
from sanskara.sub_agents.setup_agent.agent import setup_agent
from google.adk.sessions import DatabaseSessionService
from google.adk.runners import Runner
from google.genai import types
from config import SESSION_SERVICE_URI # Import SESSION_SERVICE_URI

from sanskara.helpers import execute_supabase_sql
import sanskara.db_queries as db_queries
from api.onboarding.models import CurrentUserOnboardingDetails, SecondPartnerDetails, WeddingDetails, PartnerOnboardingDetails,OnboardingSubmission, SecondPartnerSubmission
import logging # Import the custom JSON logger

async def _update_wedding_details(wedding_id: str,
                                  current_user_email: str,
                                  current_user_onboarding_details: CurrentUserOnboardingDetails = None,
                                  second_partner_details: SecondPartnerDetails = None,
                                  remove_other_partner_email_expected: bool = False):
    # Fetch existing wedding details to merge
    existing_wedding_query = await execute_supabase_sql(
        db_queries.get_wedding_details_query(),
        {"wedding_id": wedding_id}
    )
    if existing_wedding_query.get("status") == "error" or not existing_wedding_query.get("data"):
        error_message = existing_wedding_query.get('error', 'Unknown error')
        logging.error(f"Failed to fetch existing wedding details for update (wedding_id: {wedding_id}): {error_message}")
        raise HTTPException(status_code=500, detail="Could not retrieve wedding details. Please try again.")

    existing_details = existing_wedding_query["data"][0].get("details", {})
    logging.debug(f"_update_wedding_details: Initial existing_details: {existing_details}")

    partner_data = existing_details.get("partner_data", {})

    if current_user_onboarding_details:
        partner_data[current_user_email] = current_user_onboarding_details.model_dump()
        logging.debug(f"_update_wedding_details: Updated partner_data with current_user_onboarding_details: {partner_data}")
    elif second_partner_details:
        partner_data[current_user_email] = second_partner_details.model_dump()
        logging.debug(f"_update_wedding_details: Updated partner_data with second_partner_details: {partner_data}")

    existing_details["partner_data"] = partner_data

    if remove_other_partner_email_expected:
        if "other_partner_email_expected" in existing_details:
            del existing_details["other_partner_email_expected"]
            logging.debug(f"_update_wedding_details: Removed other_partner_email_expected.")

    logging.debug(f"_update_wedding_details: Final existing_details before DB update: {existing_details}")
    update_wedding_sql = db_queries.update_wedding_details_jsonb_query()
    params = {
        "wedding_id": wedding_id,
        "details": json.dumps(existing_details)
    }
    update_result = await execute_supabase_sql(update_wedding_sql, params)
    if update_result.get("status") == "error":
        error_message = update_result.get('error', 'Unknown error')
        logging.error(f"Failed to update wedding details (wedding_id: {wedding_id}): {error_message}")
        raise HTTPException(status_code=500, detail="Failed to update wedding details during onboarding. Please try again.")
    return update_result

async def _add_user_to_wedding_members(user_id: str, wedding_id: str, role: str):
    add_member_sql = db_queries.add_wedding_member_query()
    params = {"user_id": user_id, "wedding_id": wedding_id, "role": role}
    add_member_result = await execute_supabase_sql(add_member_sql, params)
    if add_member_result.get("status") == "error":
        error_message = add_member_result.get('error', 'Unknown error')
        logging.error(f"Failed to add user {user_id} to wedding {wedding_id} with role {role}: {error_message}")
        raise HTTPException(status_code=500, detail="Failed to link user to wedding. Please try again.")
    return add_member_result

async def _link_user_to_wedding(user_id: str, wedding_id: str, role: str):
    return await _add_user_to_wedding_members(user_id, wedding_id, role)

async def run_setup_agent_in_background(wedding_id: str, updated_details: Dict[str, Any]):
    """This function is executed in the background to avoid blocking the API response."""
    logging.info(f"Background task started: Invoking SetupAgent for wedding_id: {wedding_id}.")

    session_service = DatabaseSessionService(db_url=SESSION_SERVICE_URI)
    session = await session_service.create_session(
        app_name="sanskara",
        user_id="setup-agent-trigger",
    )
    session.state.update({
        "wedding_id": wedding_id,
        "partner_data": updated_details.get("partner_data", {}),
        "wedding_details": updated_details,
    })

    runner = Runner(
        app_name="sanskara",
        agent=setup_agent,
        session_service=session_service,
    )

    user_message_content = types.Content(
        role="user",
        parts=[types.Part(text=f"Initialize wedding planning for wedding ID {wedding_id} with details: {json.dumps(updated_details)}. Both partners have completed onboarding.")]
    )

    try:
        final_response_text = "SetupAgent did not produce a final response."
        async for event in runner.run_async(user_id=session.user_id, session_id=session.id, new_message=user_message_content):
            if event.is_final_response():
                if event.content and event.content.parts:
                    final_response_text = event.content.parts[0].text
                elif event.actions and event.actions.escalate:
                    final_response_text = f"SetupAgent escalated: {event.error_message or 'No specific message.'}"
                break
        
        logging.info(f"SetupAgent background run finished for wedding {wedding_id}. Response: {final_response_text}")

        update_status_sql = db_queries.update_wedding_status_query()
        await execute_supabase_sql(update_status_sql, {"wedding_id": wedding_id, "status": 'active'})
        logging.info(f"Wedding status updated to 'active' for wedding_id: {wedding_id}")

    except Exception as e:
        logging.error(f"Error in background SetupAgent invocation for wedding {wedding_id}: {e}", exc_info=True)
        # Optionally, update wedding status to 'setup_failed' to indicate an issue
        update_status_sql = db_queries.update_wedding_status_query()
        await execute_supabase_sql(update_status_sql, {"wedding_id": wedding_id, "status": 'setup_failed'})

async def _check_and_trigger_setup_agent(wedding_id: str, current_partner_email: str, background_tasks: BackgroundTasks) -> dict:
    updated_wedding_details_query = await execute_supabase_sql(
        db_queries.get_wedding_details_query(), {"wedding_id": wedding_id}
    )
    if not updated_wedding_details_query.get("data"):
        return {"message": "Wedding not found, cannot trigger agent."} # Should not happen

    updated_details = updated_wedding_details_query["data"][0].get("details", {})
    expected_other_email = updated_details.get("partner_onboarding_details", {}).get('email')

    if (updated_details.get("partner_data") and
            current_partner_email in updated_details["partner_data"] and
            expected_other_email and
            expected_other_email in updated_details["partner_data"]):

        logging.info(f"Both partners have submitted for wedding {wedding_id}. Scheduling SetupAgent to run in background.")
        update_status_sql = db_queries.update_wedding_status_query()
        await execute_supabase_sql(update_status_sql, {"wedding_id": wedding_id, "status": 'onboarding_complete'})

        background_tasks.add_task(run_setup_agent_in_background, wedding_id, updated_details)

        return {"message": "Both partners submitted. Wedding setup is being initialized in the background.", "wedding_id": str(wedding_id)}
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
    logging.debug(f"_handle_first_partner_submission: initial_details for new wedding: {initial_details}")

    create_wedding_sql = db_queries.create_wedding_query()
    params = {
        "wedding_name": wedding_details.wedding_name,
        "wedding_date": wedding_details.wedding_date.isoformat() if wedding_details.wedding_date else None,
        "wedding_location": wedding_details.wedding_location,
        "wedding_tradition": wedding_details.wedding_tradition,
        "wedding_style": wedding_details.wedding_style,
        "details": json.dumps(initial_details)
    }
    logging.debug(f"_handle_first_partner_submission: creating wedding with params: {params}")
    create_result = await execute_supabase_sql(create_wedding_sql, params)
    if create_result.get("status") == "error" or not create_result.get("data"):
        error_message = create_result.get('error', 'Unknown error')
        logging.error(f"Failed to create new wedding: {error_message}")
        raise HTTPException(status_code=500, detail="Failed to create your wedding plan. Please try again.")

    wedding_id = create_result["data"][0]["wedding_id"]
    logging.info(f"New wedding created with ID: {wedding_id} for {current_user_onboarding_details.email}. Other partner expected: {partner_onboarding_details.email}")

    await _link_user_to_wedding(user_id, wedding_id, current_user_onboarding_details.role)

    # Update the user's entry to set wedding_id and remove old fields (handled by migration script, but API should not expect them)
    # This part is implicitly handled by the user's instruction that these are removed by migration.
    # The API just needs to ensure it doesn't send them.

    return {"message": "First partner data received. Waiting for other partner.", "wedding_id": str(wedding_id)}

async def _handle_second_partner_submission(user_id: str, wedding_id: str, second_partner_details: SecondPartnerDetails, background_tasks: BackgroundTasks):
    # Verify that the wedding_id exists and that the second partner's email matches other_partner_email_expected
    find_wedding_sql = db_queries.get_wedding_details_query()
    wedding_query = await execute_supabase_sql(find_wedding_sql, {"wedding_id": wedding_id})
    existing_wedding_data = wedding_query.get("data")

    if not existing_wedding_data:
        logging.error(f"Second partner submission failed: Wedding with ID {wedding_id} not found.")
        raise HTTPException(status_code=404, detail="The wedding you are trying to join was not found. Please check the wedding ID.")

    existing_wedding = existing_wedding_data[0]
    wedding_details_jsonb = existing_wedding.get("details", {})
    logging.debug(f"_handle_second_partner_submission: Retrieved wedding_details_jsonb: {wedding_details_jsonb}")
    other_partner_email_expected = wedding_details_jsonb.get("other_partner_email_expected")
    logging.debug(f"_handle_second_partner_submission: Extracted other_partner_email_expected: {other_partner_email_expected}")

    if not other_partner_email_expected or other_partner_email_expected != second_partner_details.email:
        logging.warning(f"Second partner submission failed: Email mismatch for wedding {wedding_id}. Expected {other_partner_email_expected}, got {second_partner_details.email}.")
        raise HTTPException(status_code=400, detail="The email you provided does not match the expected partner email for this wedding. Please verify your email or contact the first partner.")

    logging.info(f"Found existing wedding for second partner {second_partner_details.email}, wedding_id: {wedding_id}")

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

    return await _check_and_trigger_setup_agent(wedding_id, second_partner_details.email, background_tasks)

async def _update_existing_partner_details(user_id: str, wedding_id: str, user_email: str, user_role: str, submission: Any, background_tasks: BackgroundTasks):
    logging.info(f"User {user_email} already associated with wedding_id: {wedding_id}. Updating details and wedding_members.")

    if isinstance(submission, OnboardingSubmission):
        current_user_onboarding_details = submission.current_user_onboarding_details
        partner_onboarding_details = submission.partner_onboarding_details
        
        logging.debug(f"_update_existing_partner_details (OnboardingSubmission): Processing update for user {user_email}.")
        
        # Securely update JSONB by fetching, modifying, and writing back
        wedding_details_query = db_queries.get_wedding_details_query()
        wedding_details_result = await execute_supabase_sql(wedding_details_query, {"wedding_id": wedding_id})
        if wedding_details_result.get("status") == "error" or not wedding_details_result.get("data"):
            raise HTTPException(status_code=404, detail="Wedding not found for update.")

        existing_details = wedding_details_result["data"][0].get("details", {})

        partner_data = existing_details.get("partner_data", {})
        partner_data[user_email] = current_user_onboarding_details.model_dump()
        existing_details["partner_data"] = partner_data
        existing_details["partner_onboarding_details"] = partner_onboarding_details.model_dump()
        existing_details["other_partner_email_expected"] = partner_onboarding_details.email

        update_sql = db_queries.update_wedding_details_jsonb_query()
        update_params = {
            "wedding_id": wedding_id,
            "details": json.dumps(existing_details)
        }
        update_result = await execute_supabase_sql(update_sql, update_params)
        if update_result.get("status") == "error":
            logging.error(f"Failed to update wedding details for existing partner: {update_result.get('error')}")
            raise HTTPException(status_code=500, detail="Failed to update wedding details.")

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
    return await _check_and_trigger_setup_agent(wedding_id, user_email, background_tasks)