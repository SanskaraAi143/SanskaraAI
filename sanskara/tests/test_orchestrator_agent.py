import asyncio
import json
import asyncio
import json
import pytest
import uuid
from logger import logger

from google.adk.agents import LlmAgent
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types

# Import the orchestrator_agent and its tools
from sanskara.agent import orchestrator_agent
from sanskara.tools import (
    get_wedding_details,
    get_budget_summary,
    get_overdue_tasks,
    get_upcoming_deadlines,
    get_shortlisted_vendors,
    get_task_and_workflow_summary,
)

# Import execute_supabase_sql for actual calls
from sanskara.helpers import execute_supabase_sql

# NOTE: The mock_execute_supabase_sql fixture is removed as per user's request.
# These tests will now attempt to make actual Supabase calls.
# Ensure your .env is configured with valid Supabase credentials for these tests to pass.

@pytest.mark.asyncio
async def test_orchestrator_agent_instantiation():
    """
    Tests that the OrchestratorAgent can be instantiated.
    """
    assert isinstance(orchestrator_agent, LlmAgent)
    assert orchestrator_agent.name == "OrchestratorAgent", f"Expected agent name to be 'OrchestratorAgent', got {orchestrator_agent.name}"
    #print the agent's description for verification

@pytest.mark.asyncio
async def test_orchestrator_agent_new_tools_execution():
    """
    Tests that the new granular database tools can execute correctly.
    """
    test_wedding_id = str(uuid.uuid4())

    # --- Setup: Create a test wedding ---
    create_wedding_sql = """
        INSERT INTO weddings (wedding_id, wedding_name, status)
        VALUES (:wedding_id, :wedding_name, :status)
        RETURNING *;
    """
    create_wedding_params = {
        "wedding_id": test_wedding_id,
        "wedding_name": "Test Wedding for New Tools",
        "status": "active"
    }
    await execute_supabase_sql(create_wedding_sql, create_wedding_params)

    try:
        # Test get_wedding_details
        details = await get_wedding_details(test_wedding_id)
        assert details is not None
        assert details.get("wedding_id") == test_wedding_id
        assert details.get("wedding_name") == "Test Wedding for New Tools"

        # Test get_budget_summary (assuming no budget items yet)
        budget = await get_budget_summary(test_wedding_id)
        assert budget is not None
        assert budget.get("total_budget") == 0

        # --- Setup: Create a test task ---
        create_task_sql = """
            INSERT INTO tasks (task_id, wedding_id, title, due_date, is_complete)
            VALUES (:task_id, :wedding_id, :title, :due_date, :is_complete)
        """
        await execute_supabase_sql(create_task_sql, {
            "task_id": str(uuid.uuid4()),
            "wedding_id": test_wedding_id,
            "title": "Overdue Test Task",
            "due_date": "2022-01-01",
            "is_complete": False
        })

        # Test get_overdue_tasks
        overdue_tasks = await get_overdue_tasks(test_wedding_id)
        assert isinstance(overdue_tasks, list)
        assert len(overdue_tasks) >= 1
        assert any(t["title"] == "Overdue Test Task" for t in overdue_tasks)

    finally:
        # --- Teardown: Clean up test data ---
        delete_wedding_sql = "DELETE FROM weddings WHERE wedding_id = :wedding_id;"
        await execute_supabase_sql(delete_wedding_sql, {"wedding_id": test_wedding_id})

@pytest.mark.asyncio
async def test_orchestrator_agent_basic_response():
    """
    Tests that the OrchestratorAgent can process a simple message and return a response.
    This test will make an actual LLM call.
    """
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name="sanskara_wedding_planner",
        user_id="test-user",
    )
    orchestrator_agent.model= "gemini-2.5-flash"  # Ensure the model is set for the test
    runner = Runner(
        app_name="sanskara_wedding_planner",
        agent=orchestrator_agent,
        session_service=session_service,
    )

    # Simulate a user message that the OrchestratorAgent should respond to
    user_message_content = types.Content(
        role="user",
        parts=[types.Part(text="Hello, Sanskara AI!")]
    )

    final_response_text = None
    async for event in runner.run_async(user_id=session.user_id, session_id=session.id, new_message=user_message_content):
        if event.is_final_response():
            if event.content and event.content.parts:
                final_response_text = event.content.parts[0].text
            break
    
    # We expect the OrchestratorAgent to respond with its default behavior or acknowledge the greeting.
    assert final_response_text is not None , f"Expected a response from the agent, but got None. Event: {event}"
    assert isinstance(final_response_text, str)
    assert len(final_response_text) > 0 # Ensure some response is generated
    logger.info(f"OrchestratorAgent response: {final_response_text}")

    # Further assertions can be added based on expected LLM output, e.g.:
    # assert "Hello" in final_response_text or "Hi" in final_response_text