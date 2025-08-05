from fastapi import APIRouter, HTTPException
from api.onboarding.models import OnboardingSubmission, SecondPartnerSubmission, CurrentUserOnboardingDetails, WeddingDetails, PartnerOnboardingDetails
from sanskara.helpers import execute_supabase_sql
import sanskara.db_queries as db_queries
from api.onboarding.services import (
    _update_existing_partner_details,
    _handle_first_partner_submission,
    _handle_second_partner_submission
)
from logger import json_logger as logger # Import the custom JSON logger

onboarding_router = APIRouter()

@onboarding_router.post("/submit")
async def submit_onboarding_data(submission: OnboardingSubmission | SecondPartnerSubmission):
    logger.info(f"Received onboarding submission.")

    user_email = None
    user_role = None
    wedding_id = None

    if isinstance(submission, OnboardingSubmission):
        user_email = submission.current_user_onboarding_details.email
        user_role = submission.current_user_onboarding_details.role
    elif isinstance(submission, SecondPartnerSubmission):
        user_email = submission.current_partner_details.email
        user_role = submission.current_partner_details.role
        wedding_id = submission.wedding_id

    if not user_email:
        logger.warning("Onboarding submission failed: User email not provided.")
        raise HTTPException(status_code=400, detail="User email is required for onboarding.")

    user_query_result = await execute_supabase_sql(db_queries.get_user_and_wedding_info_by_email_query(user_email))
    existing_user_data = user_query_result.get("data")

    user_id = None
    existing_wedding_id = None
    existing_role = None

    if existing_user_data:
        user_id = existing_user_data[0].get("user_id")
        existing_wedding_id = existing_user_data[0].get("wedding_id")
        existing_role = existing_user_data[0].get("role")

    if not user_id:
        logger.error(f"Onboarding failed: User with email {user_email} not found in the users table. User must sign up first.")
        raise HTTPException(status_code=404, detail="User not found. Please ensure you have signed up before onboarding.")

    if existing_wedding_id and wedding_id and existing_wedding_id != wedding_id:
        logger.warning(f"Onboarding conflict: User {user_email} is already associated with wedding {existing_wedding_id}, but attempted to link to {wedding_id}.")
        raise HTTPException(status_code=400, detail="You are already associated with a different wedding. Please contact support if you believe this is an error.")
    elif existing_wedding_id:
        # User exists and is already linked to a wedding via wedding_members
        # This branch handles re-submission by an already onboarded user
        return await _update_existing_partner_details(user_id, existing_wedding_id, user_email, user_role, submission)
    elif isinstance(submission, OnboardingSubmission):
        # First partner submission (new wedding creation)
        if submission.current_user_onboarding_details.email == submission.partner_onboarding_details.email:
            logger.warning(f"Onboarding submission failed: Current user ({user_email}) and partner have the same email address.")
            raise HTTPException(status_code=400, detail="You and your partner cannot have the same email address. Please provide unique emails.")
        return await _handle_first_partner_submission(user_id, submission.wedding_details, submission.current_user_onboarding_details, submission.partner_onboarding_details)
    elif isinstance(submission, SecondPartnerSubmission):
        # Second partner submission (joining existing wedding)
        return await _handle_second_partner_submission(user_id, submission.wedding_id, submission.current_partner_details)
    else:
        logger.error(f"Onboarding submission failed: Invalid submission type or missing information for user {user_email}.")
        raise HTTPException(status_code=400, detail="Invalid submission. Please check the provided information.")

@onboarding_router.get("/partner-details")
async def get_partner_details(email: str):
    logger.info(f"Received request for partner details for email: {email}")

    # Search for a wedding where this email is the expected other partner
    find_wedding_sql = db_queries.get_wedding_by_expected_partner_email_query(email)
    wedding_query = await execute_supabase_sql(find_wedding_sql)
    wedding_data = wedding_query.get("data")

    if not wedding_data:
        logger.info(f"Partner details request for {email}: No wedding found where this email is an expected partner.")
        raise HTTPException(status_code=404, detail="No wedding found where this email is listed as an expected partner. Please ensure the first partner has completed their onboarding.")

    wedding_record = wedding_data[0]
    wedding_id = wedding_record["wedding_id"]
    wedding_details = wedding_record["details"]
    other_partner_email_expected = wedding_details.get("other_partner_email_expected")

    first_partner_info = {}
    if wedding_details.get("partner_data"):
        for p_email, p_details in wedding_details["partner_data"].items():
            if p_email != other_partner_email_expected:
                first_partner_info = p_details
                break

    # Extract wedding table fields
    wedding_name = wedding_record.get("wedding_name") or f"{first_partner_info.get('name', 'Partner')}'s Wedding Plan"
    wedding_date = wedding_record.get("wedding_date")
    wedding_location = wedding_record.get("wedding_location")
    wedding_tradition = wedding_record.get("wedding_tradition")
    wedding_style = wedding_record.get("wedding_style")

    return {
        "wedding_id": str(wedding_id),
        "wedding_name": wedding_name,
        "wedding_date": str(wedding_date) if wedding_date else None,
        "wedding_location": wedding_location,
        "wedding_tradition": wedding_tradition,
        "wedding_style": wedding_style,
        "first_partner_name": first_partner_info.get("name", "N/A"),
        "first_partner_details": first_partner_info,
        "partner_data": wedding_details.get("partner_data", {}),
        "partner_onboarding_details": wedding_details.get("partner_onboarding_details", {}),
        "other_partner_email_expected": other_partner_email_expected
    }