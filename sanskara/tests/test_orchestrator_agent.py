import asyncio
import json
import asyncio
import json
import pytest
import uuid
import logging

from google.adk.agents import LlmAgent
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types

# Import the orchestrator_agent and its tools
from sanskara.agent import orchestrator_agent
from sanskara.tools import (
    get_wedding_context,
    get_active_workflows,
    get_tasks_for_wedding,
    update_workflow_status,
    create_workflow,
    update_task_details,
    create_task
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
async def test_orchestrator_agent_tools_registration_and_execution():
    """
    Tests that the direct database tools are correctly registered with the OrchestratorAgent
    and can execute (make actual Supabase calls).
    """
  
    # Generate unique IDs for testing to avoid conflicts with existing data
    test_wedding_id = str(uuid.uuid4())
    test_workflow_id = str(uuid.uuid4())
    test_task_id = str(uuid.uuid4())

    # --- Test create_wedding (prerequisite for other tests) ---
    # We need a wedding entry to test workflows and tasks related to it.
    # This is a simplified direct SQL execution for test setup/teardown.
    # In a real app, this would be part of a setup_agent or similar.
    create_wedding_sql = """
        INSERT INTO weddings (wedding_id, wedding_name, status)
        VALUES (:wedding_id, :wedding_name, :status)
        RETURNING *;
    """
    create_wedding_params = {
        "wedding_id": test_wedding_id,
        "wedding_name": "Test Wedding for Orchestrator",
        "status": "active"
    }
    await execute_supabase_sql(create_wedding_sql, create_wedding_params)

    try:
        # Test get_wedding_context
        result = await get_wedding_context(test_wedding_id)
        assert result is not None
        assert result.get("wedding_id") == test_wedding_id
        assert result.get("wedding_name") == "Test Wedding for Orchestrator"

        # Test create_workflow
        result = await create_workflow(test_wedding_id, "Test Workflow", "in_progress")
        assert result["status"] == "success"
        assert result["data"]["workflow_name"] == "Test Workflow"
        created_workflow_id = result["data"]["workflow_id"]

        # Test get_active_workflows
        result = await get_active_workflows(test_wedding_id)
        assert len(result) >= 1
        assert any(wf["workflow_id"] == created_workflow_id for wf in result)

        # Test update_workflow_status
        result = await update_workflow_status(created_workflow_id, "completed")
        assert result["status"] == "success"
        assert result["data"][0]["status"] == "completed"

        # Test create_task
        result = await create_task(test_wedding_id, "Test Task", description="This is a test task.")
        assert result["status"] == "success"
        assert result["data"]["title"] == "Test Task"
        created_task_id = result["data"]["task_id"]

        # Test get_tasks_for_wedding
        result = await get_tasks_for_wedding(test_wedding_id, status="No Status")
        assert len(result) >= 1
        assert any(task["task_id"] == created_task_id for task in result)

        # Test update_task_details
        result = await update_task_details(created_task_id, {"status": "completed", "is_complete": True})
        assert result["status"] == "success"
        assert result["data"][0]["status"] == "completed"
        assert result["data"][0]["is_complete"] is True

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
    logging.info(f"OrchestratorAgent response: {final_response_text}")

    # Further assertions can be added based on expected LLM output, e.g.:
    # assert "Hello" in final_response_text or "Hi" in final_response_text