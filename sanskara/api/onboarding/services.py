import json
import logging
from typing import Dict, Any, List, Optional
from datetime import date
from fastapi import HTTPException

from sanskara.helpers import execute_supabase_sql
import sanskara.db_queries as db_queries
from api.onboarding.models import PartnerDetails, SecondPartnerDetails
from tests.test_setup_agent_invocation import run_setup_agent_test # TODO: Remove test import

logger = logging.getLogger(__name__)

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
    find_wedding_sql = db_queries.get_wedding_by_expected_partner_email_query(email)
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