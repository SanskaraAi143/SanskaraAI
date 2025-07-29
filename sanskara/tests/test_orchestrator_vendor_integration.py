import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from sanskara.agent import orchestrator_agent
from google.adk.agents import Agent
from google.adk.models.llm_response import LlmResponse
from google.genai import types # Import types
from google.adk.models import LlmRequest # Import LlmRequest
from google.adk.agents.callback_context import CallbackContext # Import CallbackContext

# Mock the entire vendor_management_agent for integration tests
@pytest.fixture
def mock_vendor_management_agent():
    with patch('sanskara.sub_agents.vendor_management_agent.agent.vendor_management_agent', spec=Agent) as mock_agent:
        # Mock the execute method of the vendor_management_agent
        # This will be called by the AgentTool
        mock_agent.execute = AsyncMock(return_value=LlmResponse(
            content=types.Content(parts=[types.Part(text="Mocked Vendor Management Agent Response with vendors: Mock Photo Co.")]),
            custom_metadata={"vendors": [{"vendor_id": "v1", "name": "Mock Photo Co."}]}
        ))
        yield mock_agent

# Test OrchestratorAgent invoking search_vendors through VendorManagementAgent
@pytest.mark.asyncio
async def test_orchestrator_calls_search_vendors(mock_vendor_management_agent):
    # Simulate a user message that should trigger the vendor search
    user_message = "Find me a photographer in New York"

    # Call the orchestrator_agent with the user message
    # We need to simulate the ADK request structure
    mock_llm_request = LlmRequest(contents=[types.Content(parts=[types.Part(text=user_message)])])
    mock_callback_context = MagicMock() # Mock the callback context if needed
    
    # Mock the session.state directly since _handle_message doesn't take callback_context directly
    mock_session = MagicMock()
    mock_session.state = mock_callback_context._invocation_context.session.state
    response = await orchestrator_agent._handle_message(
        session=mock_session,
        llm_request=mock_llm_request
    )

    # Assert that the vendor_management_agent's execute method was called
    mock_vendor_management_agent.execute.assert_called_once()

    # You might need more specific assertions here depending on how the OrchestratorAgent
    # constructs the request to the VendorManagementAgent.
    # For now, we'll just check if it was called.
    # In a real scenario, you'd inspect mock_vendor_management_agent.execute.call_args
    # to ensure the correct arguments were passed to the sub-agent.
    assert "Mocked Vendor Management Agent Response" in response.content.parts[0].text
    assert response.custom_metadata == {"vendors": [{"vendor_id": "v1", "name": "Mock Photo Co."}]}

# Add more integration tests for other vendor management tools
# Example for add_to_shortlist:
@pytest.mark.asyncio
async def test_orchestrator_calls_add_to_shortlist(mock_vendor_management_agent):
    user_message = "Shortlist vendor V1 for user U1, it's Photo Pro, a photographer"

    mock_llm_request = LlmRequest(contents=[types.Content(parts=[types.Part(text=user_message)])])
    mock_callback_context = MagicMock() # Mock the callback context if needed

    mock_vendor_management_agent.execute.return_value = LlmResponse(
        content=types.Content(parts=[types.Part(text="Vendor V1 added to shortlist.")]),
        custom_metadata={"status": "success", "user_vendor_id": "uv123"}
    )

    # Mock the session.state directly since _handle_message doesn't take callback_context directly
    mock_session = MagicMock()
    mock_session.state = mock_callback_context._invocation_context.session.state
    response = await orchestrator_agent._handle_message(
        session=mock_session,
        llm_request=mock_llm_request
    )

    mock_vendor_management_agent.execute.assert_called_once()
    assert "Vendor V1 added to shortlist." in response.content.parts[0].text
    assert response.custom_metadata == {"status": "success", "user_vendor_id": "uv123"}

# Example for get_vendor_details:
@pytest.mark.asyncio
async def test_orchestrator_calls_get_vendor_details(mock_vendor_management_agent):
    user_message = "Tell me more about vendor V2"

    mock_llm_request = LlmRequest(contents=[types.Content(parts=[types.Part(text=user_message)])])
    mock_callback_context = MagicMock() # Mock the callback context if needed

    mock_vendor_management_agent.execute.return_value = LlmResponse(
        content=types.Content(parts=[types.Part(text="Details for Vendor V2: Name: Cake Bakery, Location: NYC")]),
        custom_metadata={"vendor_id": "V2", "name": "Cake Bakery", "location": "NYC"}
    )

    # Mock the session.state directly since _handle_message doesn't take callback_context directly
    mock_session = MagicMock()
    mock_session.state = mock_callback_context._invocation_context.session.state
    response = await orchestrator_agent._handle_message(
        session=mock_session,
        llm_request=mock_llm_request
    )

    mock_vendor_management_agent.execute.assert_called_once()
    assert "Details for Vendor V2: Name: Cake Bakery, Location: NYC" in response.content.parts[0].text
    assert response.custom_metadata == {"vendor_id": "V2", "name": "Cake Bakery", "location": "NYC"}

# Example for create_booking:
@pytest.mark.asyncio
async def test_orchestrator_calls_create_booking(mock_vendor_management_agent):
    user_message = "Book vendor V3 for wedding W1 on 2025-12-25 for $5000"

    mock_llm_request = LlmRequest(contents=[types.Content(parts=[types.Part(text=user_message)])])
    mock_callback_context = MagicMock() # Mock the callback context if needed

    mock_vendor_management_agent.execute.return_value = LlmResponse(
        content=types.Content(parts=[types.Part(text="Booking created with ID B123")]),
        custom_metadata={"booking_id": "B123"}
    )

    # Mock the session.state directly since _handle_message doesn't take callback_context directly
    mock_session = MagicMock()
    mock_session.state = mock_callback_context._invocation_context.session.state
    response = await orchestrator_agent._handle_message(
        session=mock_session,
        llm_request=mock_llm_request
    )

    mock_vendor_management_agent.execute.assert_called_once()
    assert "Booking created with ID B123" in response.content.parts[0].text
    assert response.custom_metadata == {"booking_id": "B123"}

# Example for submit_review:
@pytest.mark.asyncio
async def test_orchestrator_calls_submit_review(mock_vendor_management_agent):
    user_message = "Submit a review for booking B456: 4 stars, great service"

    mock_llm_request = LlmRequest(contents=[types.Content(parts=[types.Part(text=user_message)])])
    mock_callback_context = MagicMock() # Mock the callback context if needed

    mock_vendor_management_agent.execute.return_value = LlmResponse(
        content=types.Content(parts=[types.Part(text="Review submitted with ID R789")]),
        custom_metadata={"review_id": "R789"}
    )

    # Mock the session.state directly since _handle_message doesn't take callback_context directly
    mock_session = MagicMock()
    mock_session.state = mock_callback_context._invocation_context.session.state
    response = await orchestrator_agent._handle_message(
        session=mock_session,
        llm_request=mock_llm_request
    )

    mock_vendor_management_agent.execute.assert_called_once()
    assert "Review submitted with ID R789" in response.content.parts[0].text
    assert response.custom_metadata == {"review_id": "R789"}