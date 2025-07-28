import pytest
from unittest.mock import patch, MagicMock
from sanskara.sub_agents.ritual_and_cultural_agent.tools import search_rituals
from sanskara.db import astra_db

# DummyInvocationContext is no longer directly used by ToolContext, but might be useful for other mocks.
# For now, keeping it here.
class DummyInvocationContext:
    def __init__(self):
        self.state = {}
        self.llm_request = MagicMock()
        self.llm_request.context = {}

# Test for uninitialized Astra DB will be removed or adapted as it relies on mocking environment
# @pytest.mark.asyncio
# async def test_search_rituals_astra_db_not_initialized():
#     """
#     Test search_rituals when astra_db is not initialized.
#     This test uses a patch to simulate the uninitialized state.
#     """
#     with patch('sanskara.db.astra_db', None):
#         tool_context = ToolContext(invocation_context=DummyInvocationContext())
#         response = await search_rituals("some question", tool_context)
#         assert response["status"] == "error"
#         assert "Astra DB client is not initialized." in response["error"]

@pytest.mark.asyncio
async def test_search_rituals_invalid_input_question():
    """
    Test search_rituals with invalid question input.
    """
    # No tool_context argument anymore
    response = await search_rituals("", limit=1)
    assert response["status"] == "error"
    assert "Invalid input: 'question' must be a non-empty string." in response["error"]

    response = await search_rituals(123, limit=1)
    assert response["status"] == "error"
    assert "Invalid input: 'question' must be a non-empty string." in response["error"]

@pytest.mark.asyncio
async def test_search_rituals_invalid_input_limit():
    """
    Test search_rituals with invalid limit input.
    """
    # No tool_context argument anymore
    response = await search_rituals("some question", limit=0)
    assert response["status"] == "error"
    assert "Invalid input: 'limit' must be a positive integer." in response["error"]

    response = await search_rituals("some question", limit="abc")
    assert response["status"] == "error"
    assert "Invalid input: 'limit' must be a positive integer." in response["error"]

@pytest.mark.asyncio
async def test_search_rituals_success():
    """
    Test successful search_rituals call with a real Astra DB.
    This requires ASTRA_API_TOKEN and ASTRA_API_ENDPOINT to be set in the environment.
    It also assumes there is data in the 'ritual_data' collection that can be found.
    """
    if astra_db is None:
        pytest.skip("Astra DB client not initialized. Set ASTRA_API_TOKEN and ASTRA_API_ENDPOINT environment variables.")

    # No tool_context argument anymore
    question = "What is snathakam?"
    limit = 1

    response = await search_rituals(question, limit)

    assert response["status"] == "success"
    print(f"Found {len(response['data'])} rituals matching the query. response: {response}")
    assert len(response["data"]) > 0

@pytest.mark.asyncio
async def test_search_rituals_no_results():
    """
    Test search_rituals when no results are found (real DB).
    """
    if astra_db is None:
        pytest.skip("Astra DB client not initialized. Set ASTRA_API_TOKEN and ASTRA_API_ENDPOINT environment variables.")

    # No tool_context argument anymore
    question = "A very unique string that should not exist in the database for sure."
    limit = 1

    response = await search_rituals(question, limit)

    assert response["status"] == "success"
    assert len(response["data"]) == 0
    assert "No rituals found matching the query." in response["message"]

@pytest.mark.skip(reason="Simulating a real Astra DB error without mocking is complex and environment-dependent.")
@pytest.mark.asyncio
async def test_search_rituals_astra_db_error():
    """
    Test search_rituals when a real Astra DB error occurs.
    This test is harder to simulate without mocking the underlying astrapy client directly.
    For a true "real" test, you might need to temporarily misconfigure the DB connection
    or use a specialized test harness provided by astrapy for error simulation.
    For now, this test will remain as a placeholder and be skipped.
    """
    pass