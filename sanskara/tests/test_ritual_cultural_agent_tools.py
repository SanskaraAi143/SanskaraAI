import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio
import json
from sanskara.sub_agents.ritual_and_cultural_agent.tools import get_ritual_information
from sanskara.db import astra_db as original_astra_db

@pytest.fixture(autouse=True)
def mock_astra_db():
    """
    Fixture to mock the astra_db client for each test.
    Ensures a clean mock for astra_db in every test function.
    """
    with patch('sanskara.db.astra_db', new_callable=MagicMock) as mock_db:
        yield mock_db

@pytest.fixture
def mock_ritual_data_collection(mock_astra_db):
    """
    Fixture to mock the 'ritual_data' collection and its methods.
    """
    mock_collection = MagicMock()
    mock_astra_db.get_collection.return_value = mock_collection
    return mock_collection

@pytest.mark.asyncio
async def test_get_ritual_information_success(mock_ritual_data_collection):
    """
    Test case for successful retrieval of ritual information.
    Covers a successful execution path with valid input.
    """
    # Mock the find method to return a successful result
    mock_ritual_data_collection.find.return_value = {
        "data": {
            "documents": [
                {"content": "The Haldi ceremony is a pre-wedding ritual."}
            ]
        }
    }
    
    query = "What is the significance of the Haldi ceremony?"
    result = await get_ritual_information(query)
    
    # Assert the expected output
    expected_result = "The Haldi ceremony is a pre-wedding ritual."
    assert result == expected_result, f"Expected: '{expected_result}', Actual: '{result}'"
    
    # Assert that get_collection and find were called correctly
    mock_ritual_data_collection.find.assert_called_once()
    find_query_arg = mock_ritual_data_collection.find.call_args[0][0]
    assert "$vectorize" in find_query_arg, f"Expected '$vectorize' in query, Actual: '{find_query_arg}'"
    assert find_query_arg["$vectorize"] == query, f"Expected query '{query}', Actual: '{find_query_arg['$vectorize']}'"
    assert "limit" in mock_ritual_data_collection.find.call_args[1], f"Expected 'limit' in find arguments"
    assert mock_ritual_data_collection.find.call_args[1]["limit"] == 1, f"Expected limit 1, Actual: '{mock_ritual_data_collection.find.call_args[1]['limit']}'"

@pytest.mark.asyncio
async def test_get_ritual_information_with_culture_filter(mock_ritual_data_collection):
    """
    Test case for successful retrieval of ritual information with a culture filter.
    Covers a successful execution path with valid input and a culture filter.
    """
    # Mock the find method to return a successful result for a specific culture
    mock_ritual_data_collection.find.return_value = {
        "data": {
            "documents": [
                {"content": "The Anand Karaj is the Sikh marriage ceremony."}
            ]
        }
    }
    
    query = "Describe the Anand Karaj ceremony"
    culture_filter = "Punjabi"
    result = await get_ritual_information(query, culture_filter)
    
    # Assert the expected output
    expected_result = "The Anand Karaj is the Sikh marriage ceremony."
    assert result == expected_result, f"Expected: '{expected_result}', Actual: '{result}'"
    
    # Assert that get_collection and find were called correctly with the filter
    mock_ritual_data_collection.find.assert_called_once()
    find_query_arg = mock_ritual_data_collection.find.call_args[0][0]
    assert "$vectorize" in find_query_arg, f"Expected '$vectorize' in query, Actual: '{find_query_arg}'"
    assert find_query_arg["$vectorize"] == query, f"Expected query '{query}', Actual: '{find_query_arg['$vectorize']}'"
    assert "culture" in find_query_arg, f"Expected 'culture' in query, Actual: '{find_query_arg}'"
    assert find_query_arg["culture"] == culture_filter, f"Expected culture filter '{culture_filter}', Actual: '{find_query_arg['culture']}'"

@pytest.mark.asyncio
async def test_get_ritual_information_empty_query():
    """
    Test case for an empty query input.
    Covers an edge case with invalid input.
    """
    result = await get_ritual_information("")
    expected_result = "Error: Invalid input: 'query' must be a non-empty string."
    assert result == expected_result, f"Expected: '{expected_result}', Actual: '{result}'"

@pytest.mark.asyncio
async def test_get_ritual_information_astra_db_not_initialized():
    """
    Test case when astra_db client is not initialized.
    Covers an edge case where a dependency is not met.
    """
    # Temporarily set astra_db to None to simulate not initialized
    with patch('sanskara.db.astra_db', None):
        result = await get_ritual_information("Some query")
        expected_result = "Error: Astra DB client is not initialized. Check environment variables (ASTRA_API_TOKEN, ASTRA_API_ENDPOINT) and config."
        assert result == expected_result, f"Expected: '{expected_result}', Actual: '{result}'"

@pytest.mark.asyncio
async def test_get_ritual_information_no_results(mock_ritual_data_collection):
    """
    Test case when no ritual information is found for the query.
    Covers a scenario where no results are returned from the database.
    """
    # Mock the find method to return no documents
    mock_ritual_data_collection.find.return_value = {
        "data": {
            "documents": []
        }
    }
    
    query = "Non-existent ritual"
    result = await get_ritual_information(query)
    expected_result = "No information found for your query. Please try a different query or culture filter."
    assert result == expected_result, f"Expected: '{expected_result}', Actual: '{result}'"
    
    # Assert that find was called
    mock_ritual_data_collection.find.assert_called_once()

@pytest.mark.asyncio
async def test_get_ritual_information_astra_db_query_failure(mock_ritual_data_collection):
    """
    Test case for when the Astra DB query itself returns an error.
    Covers error handling during database interaction.
    """
    # Mock the find method to return an error from Astra DB
    mock_ritual_data_collection.find.return_value = {
        "errors": [{"message": "Internal database error."}]
    }
    
    query = "Query causing error"
    result = await get_ritual_information(query)
    expected_result = "Error: Astra DB query failed: [{'message': 'Internal database error.'}]"
    assert result == expected_result, f"Expected: '{expected_result}', Actual: '{result}'"
    
    # Assert that find was called
    mock_ritual_data_collection.find.assert_called_once()

@pytest.mark.asyncio
async def test_get_ritual_information_general_exception(mock_ritual_data_collection):
    """
    Test case for a general unexpected exception during execution.
    Covers robust error handling.
    """
    # Mock the find method to raise an arbitrary exception
    mock_ritual_data_collection.find.side_effect = Exception("Simulated network error")
    
    query = "Query with network issue"
    result = await get_ritual_information(query)
    expected_result = "An unexpected error occurred during ritual information retrieval."
    assert result == expected_result, f"Expected: '{expected_result}', Actual: '{result}'"
    
    # Assert that find was called
    mock_ritual_data_collection.find.assert_called_once()

@pytest.mark.asyncio
async def test_get_ritual_information_document_structure_variation(mock_ritual_data_collection):
    """
    Test case to ensure the function handles variations in document structure (description field).
    """
    mock_ritual_data_collection.find.return_value = {
        "data": {
            "documents": [
                {"description": "A description of a ritual."}
            ]
        }
    }
    query = "test query"
    result = await get_ritual_information(query)
    expected_result = "A description of a ritual."
    assert result == expected_result, f"Expected: '{expected_result}', Actual: '{result}'"

@pytest.mark.asyncio
async def test_get_ritual_information_document_structure_json_fallback(mock_ritual_data_collection):
    """
    Test case to ensure the function falls back to JSON dump if content/description are missing.
    """
    mock_ritual_data_collection.find.return_value = {
        "data": {
            "documents": [
                {"id": "123", "name": "Ritual X"}
            ]
        }
    }
    query = "test query"
    result = await get_ritual_information(query)
    # The result should be a JSON string of the document
    expected_document_json = json.dumps({"id": "123", "name": "Ritual X"}, indent=2)
    assert result == expected_document_json, f"Expected: '{expected_document_json}', Actual: '{result}'"