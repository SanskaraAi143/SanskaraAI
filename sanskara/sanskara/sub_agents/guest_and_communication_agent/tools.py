import os
from typing import Optional
from google.adk.tools import agent_tool
import logging # Import the custom JSON logger
import json
import asyncio
from sanskara.helpers import execute_supabase_sql
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from twilio.rest import Client as TwilioClient
import re


# Initialize SendGrid client using environment variable
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")

# Initialize Twilio client using environment variables
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
TWILIO_MESSAGING_SERVICE_SID = os.getenv("TWILIO_MESSAGING_SERVICE_SID")  # optional (preferred with Content API)

twilio_client: Optional[TwilioClient] = None
if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# TODO Implement endpoint for listening and sending messages to whatsapp and email

async def add_guest(wedding_id: str, guest_name: str, side: str, contact_info: str) -> str:
    """
    Adds a new guest to the wedding guest list.
    Args:
        wedding_id: The ID of the wedding to which the guest is being added.
        guest_name: The name of the guest.
        side: The side of the wedding (e.g., "bride", "groom", "common").
        contact_info: The contact information of the guest (e.g., email, phone number).
    Returns:
        A message indicating the success or failure of the operation.
    """
    logging.info(f"wedding_id={wedding_id}, guest_name={guest_name}, side={side}")
    logging.debug(f"Attempting to add guest: {guest_name} for wedding {wedding_id}")
    try:
        sql_query = """
        INSERT INTO guest_list (wedding_id, guest_name, side, contact_info, status)
        VALUES (:wedding_id, :guest_name, :side, :contact_info, :status)
        RETURNING guest_id;
        """
        params = {
            "wedding_id": wedding_id,
            "guest_name": guest_name,
            "side": side,
            "contact_info": contact_info,
            "status": "pending"
        }
        result = await execute_supabase_sql(sql_query, params)

        if result.get("status") == "success" and result.get("data"):
            guest_id = result["data"][0]['guest_id']
            logging.info(f"Guest '{guest_name}' added successfully with ID: {guest_id}")
            return f"Guest '{guest_name}' added successfully with ID: {guest_id}"
        else:
            error_message = result.get("error", "Unknown error")
            logging.error(f"Error adding guest: {guest_name}. Error: {error_message}")
            return f"Error adding guest: {error_message}"
    except Exception as e:
        logging.error(f"Error adding guest: {guest_name}. Error: {e}", exc_info=True)
        return f"Error adding guest: {e}"


async def update_guest_rsvp(guest_id: str, rsvp_status: str) -> str:
    """
    Updates the RSVP status of a guest.
    Args:
        guest_id: The ID of the guest to update.
        rsvp_status: The new RSVP status (e.g., "accepted", "declined", "pending").
    Returns:
        A message indicating the success or failure of the operation.
    """
    logging.info(f"guest_id={guest_id}, rsvp_status={rsvp_status}")
    logging.debug(f"Attempting to update RSVP status for guest_id: {guest_id} to {rsvp_status}")
    try:
        sql_query = """
        UPDATE guest_list
        SET status = :status
        WHERE guest_id = :guest_id
        RETURNING guest_id;
        """
        params = {
            "status": rsvp_status,
            "guest_id": guest_id
        }
        result = await execute_supabase_sql(sql_query, params)

        if result.get("status") == "success" and result.get("data"):
            logging.info(f"Guest '{guest_id}' RSVP status updated to '{rsvp_status}' successfully.")
            return f"Guest '{guest_id}' RSVP status updated to '{rsvp_status}' successfully."
        else:
            error_message = result.get("error", "Unknown error")
            if "0 rows" in error_message: # Specific error message for no rows updated
                logging.warning(f"Guest with ID '{guest_id}' not found for RSVP update.")
                return f"Guest with ID '{guest_id}' not found."
            logging.error(f"Error updating guest RSVP status for guest_id: {guest_id}. Error: {error_message}")
            return f"Error updating guest RSVP status: {error_message}"
    except Exception as e:
        logging.error(f"Error updating guest RSVP status for guest_id: {guest_id}. Error: {e}", exc_info=True)
        return f"Error updating guest RSVP status: {e}"


async def send_email(recipient_email: str, subject: str, body: str) -> str:
    """
    Sends an email to the specified recipient using SendGrid.
    
    Args:
        recipient_email (str): Recipient email address.
        subject (str): Email subject.
        body (str): The text content of the email.
        
    Returns:
        str: Success or error message.
    """
    logging.info(f"recipient_email={recipient_email}, subject={subject}")
    logging.debug(f"Sending email to {recipient_email}")
    if not SENDGRID_API_KEY:
        logging.error("SENDGRID_API_KEY must be set in environment variables.")
        return "Error sending email: SENDGRID_API_KEY not configured."
    try:
        message = Mail(
            from_email=("admin@sanskaraai.com", "Wedding Planner"),
            to_emails=recipient_email,
            subject=subject,
            plain_text_content=body
        )
        sendgrid_client = SendGridAPIClient(SENDGRID_API_KEY)
        response = sendgrid_client.send(message)
        if 200 <= response.status_code < 300:
            logging.info(f"Email sent successfully to {recipient_email}")
            return f"Email sent to {recipient_email} successfully."
        else:
            logging.error(f"SendGrid returned error status: {response.status_code}")
            return f"Error sending email: {response.status_code}"
    except Exception as e:
        logging.error(f"Exception when sending email: {e}", exc_info=True)
        return f"Error sending email: {e}"


async def send_whatsapp_message(phone_number: str, template_name: str, params: dict, body_text: Optional[str] = None) -> str:
    """
    Sends a WhatsApp message using Twilio.

    Two modes:
    1. Content Template mode (Twilio Content API): when template_name looks like a Content SID (starts with 'HX').
       -> Uses content_sid + (optional) content_variables.
    2. Plain Body mode: if no valid Content SID OR body_text provided -> sends simple text body.

    Args:
        phone_number: Destination in E.164 (e.g. +91XXXXXXXXXX)
        template_name: Either Content SID (HX...) or a logical label (ignored for plain body).
        params: Template variables (for Content SID) or key/value pairs used to build a fallback body.
        body_text: Optional explicit body override for plain body mode.

    Returns: status string.
    """
    logging.info(f"phone_number={phone_number}, template={template_name}")
    logging.debug(f"Preparing WhatsApp message to {phone_number}")

    if not twilio_client:
        logging.warning("Twilio client not initialized (missing SID / token).")
        return "Twilio credentials not configured."
    if not (TWILIO_WHATSAPP_NUMBER or TWILIO_MESSAGING_SERVICE_SID):
        logging.warning("No TWILIO_WHATSAPP_NUMBER or TWILIO_MESSAGING_SERVICE_SID configured.")
        return "Twilio WhatsApp sender not configured."

        # Decide mode
        is_content_sid = bool(re.match(r"^HX[0-9a-fA-F]{8,}$", template_name or ""))
        use_content_api = is_content_sid and body_text is None

        try:
            if use_content_api:
                payload_kwargs = {
                    "to": f"whatsapp:{phone_number}",
                    "content_sid": template_name,
                    "content_variables": json.dumps(params or {}) if params else None,
                }
                # Prefer messaging service if provided
                if TWILIO_MESSAGING_SERVICE_SID:
                    payload_kwargs["messaging_service_sid"] = TWILIO_MESSAGING_SERVICE_SID
                else:
                    payload_kwargs["from_"] = f"whatsapp:{TWILIO_WHATSAPP_NUMBER}"

                logging.debug(f"Sending via Content API mode (content_sid={template_name})")
                # Remove None keys
                payload_kwargs = {k: v for k, v in payload_kwargs.items() if v is not None}
                message = twilio_client.messages.create(**payload_kwargs)
            else:
                # Plain body fallback
                if not body_text:
                    # Construct a simple body from params
                    if params:
                        ordered = " | ".join(f"{k}: {v}" for k, v in params.items())
                    else:
                        ordered = "Hello from Sanskara AI"
                    body_text = f"{template_name}: {ordered}" if not is_content_sid else ordered
                send_kwargs = {
                    "to": f"whatsapp:{phone_number}",
                    "body": body_text
                }
                if TWILIO_MESSAGING_SERVICE_SID:
                    send_kwargs["messaging_service_sid"] = TWILIO_MESSAGING_SERVICE_SID
                else:
                    send_kwargs["from_"] = f"whatsapp:{TWILIO_WHATSAPP_NUMBER}"

                logging.debug(f"Sending plain body WhatsApp message (len={len(body_text)})")
                message = twilio_client.messages.create(**send_kwargs)

            logging.info(f"WhatsApp message sent, SID: {message.sid}")
            mode = "content" if use_content_api else "plain"
            return f"WhatsApp ({mode}) message sent to {phone_number} SID: {message.sid}"
        except Exception as e:
            # Enhanced Twilio error introspection
            status = getattr(e, 'status', None)
            code = getattr(e, 'code', None)
            more_info = getattr(e, 'more_info', None)
            logging.error(
                f"Exception sending WhatsApp message: status={status} code={code} more_info={more_info} error={e}",
                exc_info=True
            )
            return f"Error sending WhatsApp message: {e} (code={code})"


async def delete_guest(guest_identifier: str) -> str:
    """
    Deletes a guest record from the database by marking their status as 'deleted'.
    Args:
        guest_identifier: The unique identifier of the guest (e.g., guest_id or email).
    Returns:
        A message indicating the success or failure of the deletion operation.
    """
    logging.info(f"guest_identifier={guest_identifier}")
    logging.debug(f"Attempting to delete guest with identifier: {guest_identifier}")
    try:
        sql_query = """
        UPDATE guest_list
        SET status = 'deleted'
        WHERE guest_id = :guest_identifier OR contact_info = :guest_identifier
        RETURNING guest_id;
        """
        params = {
            "guest_identifier": guest_identifier
        }
        result = await execute_supabase_sql(sql_query, params)

        if result.get("status") == "success" and result.get("data"):
            deleted_guest_id = result["data"][0]['guest_id']
            logging.info(f"Guest '{deleted_guest_id}' marked as deleted successfully.")
            return f"Guest '{deleted_guest_id}' marked as deleted successfully."
        else:
            error_message = result.get("error", "Unknown error")
            if "0 rows" in error_message:
                logging.warning(f"Guest with identifier '{guest_identifier}' not found for deletion.")
                return f"Guest with identifier '{guest_identifier}' not found."
            logging.error(f"Error deleting guest with identifier: {guest_identifier}. Error: {error_message}")
            return f"Error deleting guest: {error_message}"
    except Exception as e:
        logging.error(f"Error deleting guest with identifier: {guest_identifier}. Error: {e}", exc_info=True)
        return f"Error deleting guest: {e}"


if __name__ == "__main__":
    # Note: For these tests to run successfully, ensure the following environment variables are set:
    # - SUPABASE_URL (for execute_supabase_sql)
    # - SUPABASE_KEY (for execute_supabase_sql)
    # - TWILIO_ACCOUNT_SID (for send_whatsapp_message)
    # - TWILIO_AUTH_TOKEN (for send_whatsapp_message)
    # - TWILIO_PHONE_NUMBER (for send_whatsapp_message)

    print("=== Testing Guest and Communication Agent Tools (Real Dependencies) ===")

    # Define some sample data for testing.
    # IMPORTANT: Replace these with actual IDs/data from your Supabase setup for real testing.
    # If running against a live database, ensure you have proper cleanup or test data isolation.
    test_wedding_id = "236571a1-db81-4980-be99-f7ec3273881c"
    test_guest_name = "Real Test Guest"
    test_guest_contact = "real.test.guest@example.com"
    # test_guest_id is intentionally left as a placeholder for a known existing guest
    # for testing update/delete of pre-existing records.
    test_guest_id_existing = "116e269d-baa0-4318-aaaa-6467ab9a1155" # Replace with a real guest_id from your DB if needed for specific tests
    test_email_recipient = "kpuneeth714@gmail.com" # Replace with a real email to observe simulation
    test_whatsapp_number = "+917674051127" # Replace with a real WhatsApp enabled number for actual sending
    test_whatsapp_template_id = "your_approved_template_id" # Replace with your actual approved Twilio template ID

    async def run_real_tests():
        added_guest_id: Optional[str] = None
        
        # # Test add_guest - Success Scenario
        # print("\n--- Testing add_guest (Success) ---")
        # try:
        #     result_add_guest = await add_guest(
        #         wedding_id=test_wedding_id,
        #         guest_name=test_guest_name,
        #         side="common",
        #         contact_info=test_guest_contact
        #     )
        #     print(f"Add Guest Result: {result_add_guest}")
        #     if "Guest '" in result_add_guest and "' added successfully with ID:" in result_add_guest:
        #         try:
        #             added_guest_id = result_add_guest.split("ID: ")[1].strip()
        #             print(f"Successfully added guest with ID: {added_guest_id}")
        #         except IndexError:
        #             print("Could not parse guest ID from add_guest result.")
        #     else:
        #         print("Add guest operation did not indicate success or returned no ID.")
        # except Exception as e:
        #     logging.error(f"Error during add_guest test: {e}", exc_info=True)

        # # Test update_guest_rsvp - Success Scenario (using newly added guest if available)
        # print("\n--- Testing update_guest_rsvp (Success) ---")
        # guest_id_for_update_success = added_guest_id if added_guest_id else test_guest_id_existing
        # if guest_id_for_update_success and guest_id_for_update_success != "116e269d-baa0-4318-aaaa-6467ab9a1155": # Avoid using the placeholder
        #     try:
        #         print(f"Attempting to update RSVP for guest ID: {guest_id_for_update_success}")
        #         result_update_rsvp = await update_guest_rsvp(
        #             guest_id=guest_id_for_update_success,
        #             rsvp_status="accepted"
        #         )
        #         print(f"Update RSVP Result (Success): {result_update_rsvp}")
        #     except Exception as e:
        #         logging.error(f"Error during update_guest_rsvp success test: {e}", exc_info=True)
        # else:
        #     print("Skipping update_guest_rsvp success test: No valid 'guest_id' to update. Please ensure add_guest succeeds or set 'test_guest_id_existing' to an existing ID.")

        # # Test update_guest_rsvp - Not Found Scenario
        # print("\n--- Testing update_guest_rsvp (Not Found) ---")
        # try:
        #     non_existent_guest_id = "00000000-0000-0000-0000-000000000000"
        #     print(f"Attempting to update RSVP for non-existent guest ID: {non_existent_guest_id}")
        #     result_update_rsvp_not_found = await update_guest_rsvp(
        #         guest_id=non_existent_guest_id,
        #         rsvp_status="accepted"
        #     )
        #     print(f"Update RSVP Result (Not Found): {result_update_rsvp_not_found}")
        # except Exception as e:
        #     logging.error(f"Error during update_guest_rsvp not found test: {e}", exc_info=True)

        # Test send_email - Simulated Success Scenario
        # print("\n--- Testing send_email (Simulated Success) ---")
        # try:
        #     result_send_email = await send_email(
        #         recipient_email=test_email_recipient,
        #         subject="Test Email from Sanskara (Simulated)",
        #         body="This is a test email sent from the guest and communication agent. This function simulates success."
        #     )
        #     print(f"Send Email Result: {result_send_email}")
        #     if "successfully" in result_send_email:
        #         print("Email simulation reported success as expected.")
        #     else:
        #         print("Email simulation did not report success as expected.")
        # except Exception as e:
        #     logging.error(f"Error during send_email test: {e}", exc_info=True)

        # Test send_whatsapp_message - Success Scenario (requires valid Twilio setup)
        print("\n--- Testing send_whatsapp_message (Success) ---")
        print("Note: This test requires TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER to be set in environment variables.")
        print("Also, 'test_whatsapp_number' must be a WhatsApp-enabled number and 'test_whatsapp_template_id' a valid approved template.")
        try:
            result_whatsapp = await send_whatsapp_message(
                phone_number=test_whatsapp_number,
                template_name=test_whatsapp_template_id,
                params={"1": "Test User", "2": "Wedding Date"} # Adjust params based on your template
            )
            print(f"Send WhatsApp Result: {result_whatsapp}")
        except Exception as e:
            logging.error(f"Error during send_whatsapp_message test: {e}", exc_info=True)
            
        # # Test send_whatsapp_message - Missing Credentials Scenario
        # print("\n--- Testing send_whatsapp_message (Missing Credentials) ---")
        # # Temporarily unset Twilio env vars to test the error handling
        # original_sid = os.getenv("TWILIO_ACCOUNT_SID")
        # original_token = os.getenv("TWILIO_AUTH_TOKEN")
        # original_phone = os.getenv("TWILIO_PHONE_NUMBER")
        
        # os.environ.pop("TWILIO_ACCOUNT_SID", None)
        # os.environ.pop("TWILIO_AUTH_TOKEN", None)
        # os.environ.pop("TWILIO_PHONE_NUMBER", None)
        
        # try:
        #     result_whatsapp_no_creds = send_whatsapp_message(
        #         phone_number=test_whatsapp_number,
        #         message_template_id=test_whatsapp_template_id,
        #         params={"1": "Test User", "2": "Wedding Date"}
        #     )
        #     print(f"Send WhatsApp Result (No Credentials): {result_whatsapp_no_creds}")
        #     if "Twilio credentials not configured" in result_whatsapp_no_creds:
        #         print("Successfully caught missing Twilio credentials.")
        #     else:
        #         print("Did not catch missing Twilio credentials as expected.")
        # except Exception as e:
        #     logging.error(f"Error during send_whatsapp_message no credentials test: {e}", exc_info=True)
        # finally:
        #     # Restore original Twilio env vars
        #     if original_sid: os.environ["TWILIO_ACCOUNT_SID"] = original_sid
        #     if original_token: os.environ["TWILIO_AUTH_TOKEN"] = original_token
        #     if original_phone: os.environ["TWILIO_PHONE_NUMBER"] = original_phone


    #     # Test delete_guest - Success Scenario (using newly added guest if available)
    #     print("\n--- Testing delete_guest (Success) ---")
    #     guest_identifier_for_delete_success = added_guest_id if added_guest_id else test_guest_id_existing
    #     if guest_identifier_for_delete_success and guest_identifier_for_delete_success != "116e269d-baa0-4318-aaaa-6467ab9a1155": # Avoid using the placeholder
    #         try:
    #             print(f"Attempting to delete guest with identifier: {guest_identifier_for_delete_success}")
    #             result_delete_guest = await delete_guest(guest_identifier=guest_identifier_for_delete_success)
    #             print(f"Delete Guest Result (Success): {result_delete_guest}")
    #         except Exception as e:
    #             logging.error(f"Error during delete_guest success test: {e}", exc_info=True)
    #     else:
    #         print("Skipping delete_guest success test: No valid 'guest_id' to delete. Please ensure add_guest succeeds or set 'test_guest_id_existing' to an existing ID.")

    #     # Test delete_guest - Not Found Scenario
    #     print("\n--- Testing delete_guest (Not Found) ---")
    #     try:
    #         non_existent_guest_identifier = "non.existent@example.com" # Can be ID or email
    #         print(f"Attempting to delete non-existent guest with identifier: {non_existent_guest_identifier}")
    #         result_delete_guest_not_found = await delete_guest(guest_identifier=non_existent_guest_identifier)
    #         print(f"Delete Guest Result (Not Found): {result_delete_guest_not_found}")
    #     except Exception as e:
    #         logging.error(f"Error during delete_guest not found test: {e}", exc_info=True)

    #     print("\n=== Guest and Communication Agent Tests Completed ===")

    try:
        asyncio.run(run_real_tests())
    except Exception as e:
        logging.error(f"An error occurred during guest and communication agent testing: {e}", exc_info=True)
    finally:
        logging.info("Guest and Communication Agent tests script finished.")