import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import os
import json
import asyncio

# Adjust the import path for the tools
# Assuming the tests directory is a sibling of sanskara/sanskara
# So, from sanskara.sub_agents.guest_and_communication_agent import tools
# This might need adjustment based on the actual project structure and how pytest discovers modules.
from sanskara.sub_agents.guest_and_communication_agent import tools


# Mock the logger to prevent actual logging during tests
@pytest.fixture(autouse=True)
def mock_logger():
    with patch('sanskara.sub_agents.guest_and_communication_agent.tools.logger') as mock_log:
        mock_log.contextualize.return_value.__enter__.return_value = mock_log
        yield mock_log

@pytest.mark.asyncio
async def test_add_guest_success():
    """
    Test case for successful guest addition.
    Mocks execute_supabase_sql to return a success status with guest_id.
    """
    mock_execute_supabase_sql = AsyncMock(return_value={"status": "success", "data": [{"guest_id": "test-guest-id"}]})
    with patch('sanskara.sub_agents.guest_and_communication_agent.tools.execute_supabase_sql', new=mock_execute_supabase_sql):
        wedding_id = "test-wedding-id"
        guest_name = "John Doe"
        side = "bride"
        contact_info = "john.doe@example.com"
        
        result = await tools.add_guest(wedding_id, guest_name, side, contact_info)
        
        # Assert execute_supabase_sql was called with the correct SQL query and parameters
        mock_execute_supabase_sql.assert_called_once()
        called_args, called_kwargs = mock_execute_supabase_sql.call_args
        
        expected_sql_query_part = "INSERT INTO guest_list"
        assert expected_sql_query_part in called_args[0], "Expected SQL query not found in call arguments" # Assert that the expected SQL query part is present
        
        expected_params = {
            "wedding_id": wedding_id,
            "guest_name": guest_name,
            "side": side,
            "contact_info": contact_info,
            "status": "pending"
        }
        assert called_args[1] == expected_params, "Expected parameters do not match actual parameters" # Assert that the expected parameters match the actual parameters
        
        # Assert the expected return message
        assert result == "Guest 'John Doe' added successfully with ID: test-guest-id", "Expected success message not returned" # Assert that the success message is returned

@pytest.mark.asyncio
async def test_add_guest_db_error():
    """
    Test case for database error during guest addition.
    Mocks execute_supabase_sql to return an error status.
    """
    mock_execute_supabase_sql = AsyncMock(return_value={"status": "error", "error": "Database connection failed"})
    with patch('sanskara.sub_agents.guest_and_communication_agent.tools.execute_supabase_sql', new=mock_execute_supabase_sql):
        result = await tools.add_guest("w1", "Jane Doe", "groom", "jane.doe@example.com")
        # Assert the expected error message
        assert result == "Error adding guest: Database connection failed", "Expected database error message not returned" # Assert that the database error message is returned

@pytest.mark.asyncio
async def test_add_guest_exception():
    """
    Test case for an unexpected exception during guest addition.
    Mocks execute_supabase_sql to raise an exception.
    """
    mock_execute_supabase_sql = AsyncMock(side_effect=Exception("Network issue"))
    with patch('sanskara.sub_agents.guest_and_communication_agent.tools.execute_supabase_sql', new=mock_execute_supabase_sql):
        result = await tools.add_guest("w1", "Alice", "common", "alice@example.com")
        # Assert the expected exception message
        assert "Error adding guest: Network issue" in result, "Expected exception message not found in result" # Assert that the exception message is part of the result

@pytest.mark.asyncio
async def test_update_guest_rsvp_success():
    """
    Test case for successful RSVP status update.
    Mocks execute_supabase_sql to return a success status with guest_id.
    """
    mock_execute_supabase_sql = AsyncMock(return_value={"status": "success", "data": [{"guest_id": "guest-123"}]})
    with patch('sanskara.sub_agents.guest_and_communication_agent.tools.execute_supabase_sql', new=mock_execute_supabase_sql):
        guest_id = "guest-123"
        rsvp_status = "accepted"
        
        result = await tools.update_guest_rsvp(guest_id, rsvp_status)
        
        # Assert execute_supabase_sql was called with the correct SQL query and parameters
        mock_execute_supabase_sql.assert_called_once()
        called_args, called_kwargs = mock_execute_supabase_sql.call_args
        
        expected_sql_query_part = "UPDATE guest_list"
        assert expected_sql_query_part in called_args[0], "Expected SQL query not found in call arguments" # Assert that the expected SQL query part is present
        
        expected_params = {
            "status": rsvp_status,
            "guest_id": guest_id
        }
        assert called_args[1] == expected_params, "Expected parameters do not match actual parameters" # Assert that the expected parameters match the actual parameters
        
        # Assert the expected return message
        assert result == f"Guest '{guest_id}' RSVP status updated to '{rsvp_status}' successfully.", "Expected success message not returned" # Assert that the success message is returned

@pytest.mark.asyncio
async def test_update_guest_rsvp_not_found():
    """
    Test case for updating RSVP status of a guest not found.
    Mocks execute_supabase_sql to return an error indicating "0 rows".
    """
    mock_execute_supabase_sql = AsyncMock(return_value={"status": "error", "error": "0 rows updated"})
    with patch('sanskara.sub_agents.guest_and_communication_agent.tools.execute_supabase_sql', new=mock_execute_supabase_sql):
        result = await tools.update_guest_rsvp("non-existent-guest", "declined")
        # Assert the expected guest not found message
        assert result == "Guest with ID 'non-existent-guest' not found.", "Expected guest not found message not returned" # Assert that the guest not found message is returned

@pytest.mark.asyncio
async def test_update_guest_rsvp_db_error():
    """
    Test case for database error during RSVP status update.
    Mocks execute_supabase_sql to return a generic error status.
    """
    mock_execute_supabase_sql = AsyncMock(return_value={"status": "error", "error": "Permission denied"})
    with patch('sanskara.sub_agents.guest_and_communication_agent.tools.execute_supabase_sql', new=mock_execute_supabase_sql):
        result = await tools.update_guest_rsvp("guest-456", "accepted")
        # Assert the expected error message
        assert result == "Error updating guest RSVP status: Permission denied", "Expected database error message not returned" # Assert that the database error message is returned

@pytest.mark.asyncio
async def test_update_guest_rsvp_exception():
    """
    Test case for an unexpected exception during RSVP status update.
    Mocks execute_supabase_sql to raise an exception.
    """
    mock_execute_supabase_sql = AsyncMock(side_effect=ValueError("Invalid status"))
    with patch('sanskara.sub_agents.guest_and_communication_agent.tools.execute_supabase_sql', new=mock_execute_supabase_sql):
        result = await tools.update_guest_rsvp("guest-789", "invalid")
        # Assert the expected exception message
        assert "Error updating guest RSVP status: Invalid status" in result, "Expected exception message not found in result" # Assert that the exception message is part of the result

def test_send_email_success():
    """
    Test case for successful email simulation.
    Since send_email is a placeholder, it always returns a success message.
    """
    recipient_email = "test@example.com"
    subject = "Test Subject"
    body = "Test Body"
    
    result = tools.send_email(recipient_email, subject, body)
    
    # Assert the expected hardcoded success message
    assert result == f"Email sent to {recipient_email} with subject '{subject}' successfully.", "Expected email success message not returned" # Assert that the email success message is returned

def test_send_whatsapp_message_success():
    """
    Test case for successful WhatsApp message sending.
    Mocks os.getenv for Twilio credentials and twilio.rest.Client.
    """
    with patch.dict(os.environ, {
        "TWILIO_ACCOUNT_SID": "AC_test_sid",
        "TWILIO_AUTH_TOKEN": "test_auth_token",
        "TWILIO_PHONE_NUMBER": "+15017122661"
    }), patch('sanskara.sub_agents.guest_and_communication_agent.tools.Client') as MockTwilioClient:
        
        mock_messages_create = MockTwilioClient.return_value.messages.create
        mock_messages_create.return_value.sid = "SM_test_sid"
        
        phone_number = "+12345678900"
        message_template_id = "template_123"
        params = {"name": "Test User"}
        
        result = tools.send_whatsapp_message(phone_number, message_template_id, params)
        
        # Assert Twilio client and messages.create were called with correct arguments
        MockTwilioClient.assert_called_once_with("AC_test_sid", "test_auth_token")
        mock_messages_create.assert_called_once_with(
            from_="whatsapp:+15017122661",
            to="whatsapp:+12345678900",
            content_sid=message_template_id,
            content_variables=json.dumps(params)
        )
        
        # Assert the expected return message
        assert result == f"WhatsApp message sent to {phone_number} with SID: SM_test_sid", "Expected WhatsApp success message not returned" # Assert that the WhatsApp success message is returned

def test_send_whatsapp_message_missing_credentials():
    """
    Test case for missing Twilio credentials.
    Mocks os.getenv to return None for credentials.
    """
    with patch.dict(os.environ, {}, clear=True): # Clear environment variables for this test
        result = tools.send_whatsapp_message("+12345678900", "template_123", {})
        # Assert the expected warning message
        assert result == "Twilio credentials not configured. Please set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER in the environment.", "Expected missing credentials message not returned" # Assert that the missing credentials message is returned

def test_send_whatsapp_message_twilio_error():
    """
    Test case for Twilio API error during WhatsApp message sending.
    Mocks twilio.rest.Client to raise an exception.
    """
    with patch.dict(os.environ, {
        "TWILIO_ACCOUNT_SID": "AC_test_sid",
        "TWILIO_AUTH_TOKEN": "test_auth_token",
        "TWILIO_PHONE_NUMBER": "+15017122661"
    }), patch('sanskara.sub_agents.guest_and_communication_agent.tools.Client') as MockTwilioClient:
        
        MockTwilioClient.return_value.messages.create.side_effect = Exception("Twilio API error")
        
        result = tools.send_whatsapp_message("+12345678900", "template_123", {})
        
        # Assert the expected error message
        assert "Error sending WhatsApp message: Twilio API error" in result, "Expected Twilio API error message not found in result" # Assert that the Twilio API error message is part of the result