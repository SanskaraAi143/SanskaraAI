import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone
import json

# Assuming ToolContext and CallbackContext are defined or mocked elsewhere,
# or we can create simple mock classes for them if they are not complex objects.
# For now, let's assume simple mock classes.
class MockToolContext:
    pass

class MockCallbackContext:
    pass

# Import the tools to be tested
from sanskara.sub_agents.setup_agent.tools import (
    get_current_datetime,
    bulk_create_workflows,
    bulk_create_tasks,
    populate_initial_budget,
    setup_agent_before_agent_callback,
)

@pytest.fixture
def mock_execute_supabase_sql():
    """Fixture to mock execute_supabase_sql for tests."""
    with patch("sanskara.sub_agents.setup_agent.tools.execute_supabase_sql", new_callable=AsyncMock) as mock:
        yield mock

@pytest.fixture
def mock_tool_context():
    """Fixture for a mock ToolContext."""
    return MockToolContext()

@pytest.fixture
def mock_callback_context():
    """Fixture for a mock CallbackContext."""
    return MockCallbackContext()


class TestSetupAgentTools:

    def test_get_current_datetime(self):
        """
        Test case for get_current_datetime tool.
        Ensures the function returns the current UTC datetime in ISO 8601 format.
        """
        result = get_current_datetime()
        # Assert that 'current_datetime_utc' key exists in the result
        assert "current_datetime_utc" in result, "Result should contain 'current_datetime_utc' key."
        
        # Assert that the returned datetime string is a valid ISO 8601 format
        try:
            # Attempt to parse the datetime string to verify its format
            datetime.fromisoformat(result["current_datetime_utc"])
            is_valid_format = True
        except ValueError:
            is_valid_format = False
        assert is_valid_format, "The returned datetime string should be in ISO 8601 format."

        # Assert that the datetime is close to the current UTC time (allowing for slight execution time differences)
        current_utc = datetime.now(timezone.utc)
        returned_datetime = datetime.fromisoformat(result["current_datetime_utc"]).replace(tzinfo=timezone.utc)
        time_difference = abs((current_utc - returned_datetime).total_seconds())
        assert time_difference < 5, f"Returned datetime {returned_datetime} should be close to current UTC time {current_utc}. Difference: {time_difference} seconds."

    @pytest.mark.asyncio
    async def test_bulk_create_workflows_success(self, mock_execute_supabase_sql, mock_tool_context):
        """
        Test case for successful bulk_create_workflows execution.
        Mocks execute_supabase_sql to return a success status.
        """
        mock_execute_supabase_sql.return_value = {"status": "success", "data": []}
        wedding_id = "test_wedding_id_1"
        workflows_data = [
            {"workflow_name": "Workflow 1", "status": "active", "context_summary": {"key": "value"}},
            {"workflow_name": "Workflow 2", "status": "pending"},
        ]
        
        result = await bulk_create_workflows(mock_tool_context, wedding_id, workflows_data)
        
        # Assert the function returns a success status
        assert result["status"] == "success", "Expected 'success' status for successful workflow creation."
        # Assert the success message
        assert result["message"] == f"Successfully created {len(workflows_data)} workflows.", "Expected success message for workflow creation."
        
        # Assert execute_supabase_sql was called once
        mock_execute_supabase_sql.assert_called_once()
        
        # Assert the SQL query and parameters passed to execute_supabase_sql
        args, kwargs = mock_execute_supabase_sql.call_args
        sql_query = args[0]
        params = args[1]

        # Assert SQL contains INSERT INTO workflows and VALUES
        assert "INSERT INTO workflows" in sql_query, "SQL query should contain 'INSERT INTO workflows'."
        assert "VALUES" in sql_query, "SQL query should contain 'VALUES' clause."
        
        # Assert that the SQL uses parameterized queries
        assert "%(workflow_name_0)s" in sql_query, "SQL query should use parameterized query for workflow_name_0."
        assert "%(workflow_status_0)s" in sql_query, "SQL query should use parameterized query for workflow_status_0."
        assert "%(wedding_id_0)s" in sql_query, "SQL query should use parameterized query for wedding_id_0."
        assert "%(context_summary_0)s" in sql_query, "SQL query should use parameterized query for context_summary_0."

        # Assert correct parameters are passed for each workflow
        assert params["workflow_name_0"] == "Workflow 1", "Parameter for workflow_name_0 should be 'Workflow 1'."
        assert params["workflow_status_0"] == "active", "Parameter for workflow_status_0 should be 'active'."
        assert params["wedding_id_0"] == wedding_id, "Parameter for wedding_id_0 should match the provided wedding_id."
        assert json.loads(params["context_summary_0"]) == {"key": "value"}, "Parameter for context_summary_0 should be the JSON string of the context."

        assert params["workflow_name_1"] == "Workflow 2", "Parameter for workflow_name_1 should be 'Workflow 2'."
        assert params["workflow_status_1"] == "pending", "Parameter for workflow_status_1 should be 'pending'."
        assert params["wedding_id_1"] == wedding_id, "Parameter for wedding_id_1 should match the provided wedding_id."
        assert json.loads(params["context_summary_1"]) == {}, "Parameter for context_summary_1 should be an empty JSON object."

    @pytest.mark.asyncio
    async def test_bulk_create_workflows_empty_data(self, mock_tool_context):
        """
        Test case for bulk_create_workflows with empty workflow data.
        Ensures proper error handling when workflows_data is empty.
        """
        wedding_id = "test_wedding_id_2"
        workflows_data = []
        
        result = await bulk_create_workflows(mock_tool_context, wedding_id, workflows_data)
        
        # Assert the function returns an error status
        assert result["status"] == "error", "Expected 'error' status for empty workflow data."
        # Assert the error message
        assert result["message"] == "wedding_id and workflows_data are required.", "Expected specific error message for missing data."

    @pytest.mark.asyncio
    async def test_bulk_create_workflows_missing_wedding_id(self, mock_tool_context):
        """
        Test case for bulk_create_workflows with missing wedding_id.
        Ensures proper error handling when wedding_id is missing.
        """
        wedding_id = ""
        workflows_data = [{"workflow_name": "Workflow 1"}]
        
        result = await bulk_create_workflows(mock_tool_context, wedding_id, workflows_data)
        
        # Assert the function returns an error status
        assert result["status"] == "error", "Expected 'error' status for missing wedding_id."
        # Assert the error message
        assert result["message"] == "wedding_id and workflows_data are required.", "Expected specific error message for missing wedding_id."

    @pytest.mark.asyncio
    async def test_bulk_create_workflows_supabase_error(self, mock_execute_supabase_sql, mock_tool_context):
        """
        Test case for bulk_create_workflows when execute_supabase_sql returns an error.
        Ensures proper error handling and message propagation.
        """
        mock_execute_supabase_sql.return_value = {"status": "error", "error": "Database connection failed."}
        wedding_id = "test_wedding_id_3"
        workflows_data = [{"workflow_name": "Workflow 1"}]
        
        result = await bulk_create_workflows(mock_tool_context, wedding_id, workflows_data)
        
        # Assert the function returns an error status
        assert result["status"] == "error", "Expected 'error' status when execute_supabase_sql fails."
        # Assert the error message contains the Supabase error
        assert "Failed to create workflows: Database connection failed." in result["message"], "Expected specific error message from Supabase."

    @pytest.mark.asyncio
    async def test_bulk_create_workflows_exception(self, mock_execute_supabase_sql, mock_tool_context):
        """
        Test case for bulk_create_workflows when an unexpected exception occurs.
        Ensures graceful error handling.
        """
        mock_execute_supabase_sql.side_effect = Exception("Unexpected database error")
        wedding_id = "test_wedding_id_4"
        workflows_data = [{"workflow_name": "Workflow 1"}]
        
        result = await bulk_create_workflows(mock_tool_context, wedding_id, workflows_data)
        
        # Assert the function returns an error status
        assert result["status"] == "error", "Expected 'error' status for unexpected exceptions."
        # Assert a general error message is returned
        assert result["message"] == "An unexpected error occurred during workflow creation.", "Expected general error message for unexpected exceptions."

    @pytest.mark.asyncio
    async def test_bulk_create_tasks_success(self, mock_execute_supabase_sql, mock_tool_context):
        """
        Test case for successful bulk_create_tasks execution.
        Mocks execute_supabase_sql to return a success status.
        """
        mock_execute_supabase_sql.return_value = {"status": "success", "data": []}
        wedding_id = "test_wedding_id_5"
        tasks_data = [
            {"title": "Task 1", "description": "Desc 1", "is_complete": False, "due_date": "2025-12-31", "priority": "high"},
            {"title": "Task 2", "description": "Desc 2", "is_complete": True, "category": "Planning"},
        ]

        result = await bulk_create_tasks(mock_tool_context, wedding_id, tasks_data)

        # Assert the function returns a success status
        assert result["status"] == "success", "Expected 'success' status for successful task creation."
        # Assert the success message
        assert result["message"] == f"Successfully created {len(tasks_data)} tasks.", "Expected success message for task creation."

        # Assert execute_supabase_sql was called once
        mock_execute_supabase_sql.assert_called_once()

        # Assert the SQL query and parameters passed to execute_supabase_sql
        args, kwargs = mock_execute_supabase_sql.call_args
        sql_query = args[0]
        params = args[1]

        # Assert SQL contains INSERT INTO tasks and VALUES
        assert "INSERT INTO tasks" in sql_query, "SQL query should contain 'INSERT INTO tasks'."
        assert "VALUES" in sql_query, "SQL query should contain 'VALUES' clause."

        # Assert that the SQL uses parameterized queries
        assert ":title0" in sql_query, "SQL query should use parameterized query for title0."
        assert ":description0" in sql_query, "SQL query should use parameterized query for description0."
        assert ":wedding_id0" in sql_query, "SQL query should use parameterized query for wedding_id0."

        # Assert correct parameters are passed for each task
        assert params["title0"] == "Task 1", "Parameter for title0 should be 'Task 1'."
        assert params["description0"] == "Desc 1", "Parameter for description0 should be 'Desc 1'."
        assert params["is_complete0"] is False, "Parameter for is_complete0 should be False."
        assert params["due_date0"] == "2025-12-31", "Parameter for due_date0 should be '2025-12-31'."
        assert params["priority0"] == "high", "Parameter for priority0 should be 'high'."
        assert params["category0"] == "Uncategorized", "Parameter for category0 should be 'Uncategorized' (default)."
        assert params["status0"] == "not_started", "Parameter for status0 should be 'not_started' (default)."
        assert params["lead_party0"] == "couple", "Parameter for lead_party0 should be 'couple' (default)."
        assert params["wedding_id0"] == wedding_id, "Parameter for wedding_id0 should match the provided wedding_id."

        assert params["title1"] == "Task 2", "Parameter for title1 should be 'Task 2'."
        assert params["description1"] == "Desc 2", "Parameter for description1 should be 'Desc 2'."
        assert params["is_complete1"] is True, "Parameter for is_complete1 should be True."
        assert params["due_date1"] is None, "Parameter for due_date1 should be None (default)."
        assert params["priority1"] == "medium", "Parameter for priority1 should be 'medium' (default)."
        assert params["category1"] == "Planning", "Parameter for category1 should be 'Planning'."
        assert params["status1"] == "not_started", "Parameter for status1 should be 'not_started' (default)."
        assert params["lead_party1"] == "couple", "Parameter for lead_party1 should be 'couple' (default)."
        assert params["wedding_id1"] == wedding_id, "Parameter for wedding_id1 should match the provided wedding_id."

    @pytest.mark.asyncio
    async def test_bulk_create_tasks_empty_data(self, mock_tool_context):
        """
        Test case for bulk_create_tasks with empty task data.
        Ensures proper error handling when tasks_data is empty.
        """
        wedding_id = "test_wedding_id_6"
        tasks_data = []

        result = await bulk_create_tasks(mock_tool_context, wedding_id, tasks_data)

        # Assert the function returns an error status
        assert result["status"] == "error", "Expected 'error' status for empty task data."
        # Assert the error message
        assert result["message"] == "wedding_id and tasks_data are required.", "Expected specific error message for missing data."

    @pytest.mark.asyncio
    async def test_bulk_create_tasks_missing_wedding_id(self, mock_tool_context):
        """
        Test case for bulk_create_tasks with missing wedding_id.
        Ensures proper error handling when wedding_id is missing.
        """
        wedding_id = ""
        tasks_data = [{"title": "Task 1"}]

        result = await bulk_create_tasks(mock_tool_context, wedding_id, tasks_data)

        # Assert the function returns an error status
        assert result["status"] == "error", "Expected 'error' status for missing wedding_id."
        # Assert the error message
        assert result["message"] == "wedding_id and tasks_data are required.", "Expected specific error message for missing wedding_id."

    @pytest.mark.asyncio
    async def test_bulk_create_tasks_supabase_error(self, mock_execute_supabase_sql, mock_tool_context):
        """
        Test case for bulk_create_tasks when execute_supabase_sql returns an error.
        Ensures proper error handling and message propagation.
        """
        mock_execute_supabase_sql.return_value = {"status": "error", "error": "Database write failed."}
        wedding_id = "test_wedding_id_7"
        tasks_data = [{"title": "Task 1"}]

        result = await bulk_create_tasks(mock_tool_context, wedding_id, tasks_data)

        # Assert the function returns an error status
        assert result["status"] == "error", "Expected 'error' status when execute_supabase_sql fails."
        # Assert the error message contains the Supabase error
        assert "Failed to create tasks: Database write failed." in result["message"], "Expected specific error message from Supabase."

    @pytest.mark.asyncio
    async def test_bulk_create_tasks_exception(self, mock_execute_supabase_sql, mock_tool_context):
        """
        Test case for bulk_create_tasks when an unexpected exception occurs.
        Ensures graceful error handling.
        """
        mock_execute_supabase_sql.side_effect = Exception("Network error")
        wedding_id = "test_wedding_id_8"
        tasks_data = [{"title": "Task 1"}]

        result = await bulk_create_tasks(mock_tool_context, wedding_id, tasks_data)

        # Assert the function returns an error status
        assert result["status"] == "error", "Expected 'error' status for unexpected exceptions."
        # Assert a general error message is returned
        assert result["message"] == "An unexpected error occurred during task creation.", "Expected general error message for unexpected exceptions."

    @pytest.mark.asyncio
    async def test_populate_initial_budget_success(self, mock_execute_supabase_sql, mock_tool_context):
        """
        Test case for successful populate_initial_budget execution.
        Mocks execute_supabase_sql to return a success status.
        """
        mock_execute_supabase_sql.return_value = {"status": "success", "data": []}
        wedding_id = "test_wedding_id_9"
        budget_details = [
            {"item_name": "Venue", "amount": 10000, "category": "Major", "status": "paid", "contribution_by": "couple"},
            {"item_name": "Catering", "amount": 5000, "category": "Food"},
        ]

        result = await populate_initial_budget(mock_tool_context, wedding_id, budget_details)

        # Assert the function returns a success status
        assert result["status"] == "success", "Expected 'success' status for successful budget population."
        # Assert the success message
        assert result["message"] == "Successfully populated initial budget.", "Expected success message for budget population."

        # Assert execute_supabase_sql was called once
        mock_execute_supabase_sql.assert_called_once()

        # Assert the SQL query and parameters passed to execute_supabase_sql
        args, kwargs = mock_execute_supabase_sql.call_args
        sql_query = args[0]
        params = args[1]

        # Assert SQL contains INSERT INTO budget_items and VALUES
        assert "INSERT INTO budget_items" in sql_query, "SQL query should contain 'INSERT INTO budget_items'."
        assert "VALUES" in sql_query, "SQL query should contain 'VALUES' clause."

        # Assert that the SQL uses parameterized queries
        assert "%(item_name_0)s" in sql_query, "SQL query should use parameterized query for item_name_0."
        assert "%(amount_0)s" in sql_query, "SQL query should use parameterized query for amount_0."
        assert "%(wedding_id_0)s" in sql_query, "SQL query should use parameterized query for wedding_id_0."

        # Assert correct parameters are passed for each budget item
        assert params["item_name_0"] == "Venue", "Parameter for item_name_0 should be 'Venue'."
        assert params["amount_0"] == 10000, "Parameter for amount_0 should be 10000."
        assert params["status_0"] == "paid", "Parameter for status_0 should be 'paid'."
        assert params["wedding_id_0"] == wedding_id, "Parameter for wedding_id_0 should match the provided wedding_id."
        assert params["contribution_by_0"] == "couple", "Parameter for contribution_by_0 should be 'couple'."
        assert params["category_0"] == "Major", "Parameter for category_0 should be 'Major'."

        assert params["item_name_1"] == "Catering", "Parameter for item_name_1 should be 'Catering'."
        assert params["amount_1"] == 5000, "Parameter for amount_1 should be 5000."
        assert params["status_1"] == "pending", "Parameter for status_1 should be 'pending' (default)."
        assert params["wedding_id_1"] == wedding_id, "Parameter for wedding_id_1 should match the provided wedding_id."
        assert params["contribution_by_1"] == "couple", "Parameter for contribution_by_1 should be 'couple' (default)."
        assert params["category_1"] == "Food", "Parameter for category_1 should be 'Food'."

    @pytest.mark.asyncio
    async def test_populate_initial_budget_empty_data(self, mock_tool_context):
        """
        Test case for populate_initial_budget with empty budget data.
        Ensures proper error handling when budget_details is empty.
        """
        wedding_id = "test_wedding_id_10"
        budget_details = []

        result = await populate_initial_budget(mock_tool_context, wedding_id, budget_details)

        # Assert the function returns a success status (as per current implementation, it returns success if no items to populate)
        assert result["status"] == "success", f"Expected 'success' status for empty budget data, got {result['status']}."
        # Assert the message for no budget items
        assert result["message"] == "No budget items to populate.", f"Expected specific message for no budget items, got {result['message']}."

    @pytest.mark.asyncio
    async def test_populate_initial_budget_missing_wedding_id(self, mock_tool_context):
        """
        Test case for populate_initial_budget with missing wedding_id.
        Ensures proper error handling when wedding_id is missing.
        """
        wedding_id = ""
        budget_details = [{"item_name": "Venue", "amount": 1000}]

        result = await populate_initial_budget(mock_tool_context, wedding_id, budget_details)

        # Assert the function returns an error status
        assert result["status"] == "error", "Expected 'error' status for missing wedding_id."
        # Assert the error message
        assert result["message"] == "wedding_id and budget_details are required.", "Expected specific error message for missing wedding_id."

    @pytest.mark.asyncio
    async def test_populate_initial_budget_supabase_error(self, mock_execute_supabase_sql, mock_tool_context):
        """
        Test case for populate_initial_budget when execute_supabase_sql returns an error.
        Ensures proper error handling and message propagation.
        """
        mock_execute_supabase_sql.return_value = {"status": "error", "error": "Database budget insert failed."}
        wedding_id = "test_wedding_id_11"
        budget_details = [{"item_name": "Venue", "amount": 1000}]

        result = await populate_initial_budget(mock_tool_context, wedding_id, budget_details)

        # Assert the function returns an error status
        assert result["status"] == "error", "Expected 'error' status when execute_supabase_sql fails."
        # Assert the error message contains the Supabase error
        assert "Failed to populate initial budget: Database budget insert failed." in result["message"], "Expected specific error message from Supabase."

    @pytest.mark.asyncio
    async def test_populate_initial_budget_exception(self, mock_execute_supabase_sql, mock_tool_context):
        """
        Test case for populate_initial_budget when an unexpected exception occurs.
        Ensures graceful error handling.
        """
        mock_execute_supabase_sql.side_effect = Exception("Connection refused")
        wedding_id = "test_wedding_id_12"
        budget_details = [{"item_name": "Venue", "amount": 1000}]

        result = await populate_initial_budget(mock_tool_context, wedding_id, budget_details)

        # Assert the function returns an error status
        assert result["status"] == "error", "Expected 'error' status for unexpected exceptions."
        # Assert a general error message is returned
        assert result["message"] == "An unexpected error occurred during budget population.", "Expected general error message for unexpected exceptions."

    @pytest.mark.asyncio
    async def test_setup_agent_before_agent_callback_active(self, mock_execute_supabase_sql):
        """
        Test case for setup_agent_before_agent_callback when wedding status is 'active'.
        """
        mock_execute_supabase_sql.return_value = {"status": "success", "data": [{"status": "active"}]}
        wedding_id = "active_wedding_id"
        
        result = await setup_agent_before_agent_callback(wedding_id)
        
        # Assert the callback returns True for an active wedding
        assert result is True, "Expected True for an active wedding."
        
        # Assert execute_supabase_sql was called once
        mock_execute_supabase_sql.assert_called_once()
        args, kwargs = mock_execute_supabase_sql.call_args
        sql_query = args[0]
        params = args[1]
        
        # Assert SQL query and parameters are correct
        assert "SELECT status FROM weddings WHERE wedding_id = :wedding_id;" in sql_query, "SQL query should select status from weddings table."
        assert params["wedding_id"] == wedding_id, "Parameter for wedding_id should match the provided wedding_id."

    @pytest.mark.asyncio
    async def test_setup_agent_before_agent_callback_inactive(self, mock_execute_supabase_sql):
        """
        Test case for setup_agent_before_agent_callback when wedding status is 'inactive'.
        """
        mock_execute_supabase_sql.return_value = {"status": "success", "data": [{"status": "inactive"}]}
        wedding_id = "inactive_wedding_id"
        
        result = await setup_agent_before_agent_callback(wedding_id)
        
        # Assert the callback returns False for an inactive wedding
        assert result is False, "Expected False for an inactive wedding."
        
        mock_execute_supabase_sql.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_agent_before_agent_callback_not_found(self, mock_execute_supabase_sql):
        """
        Test case for setup_agent_before_agent_callback when wedding ID is not found.
        """
        mock_execute_supabase_sql.return_value = {"status": "success", "data": []}
        wedding_id = "non_existent_wedding_id"
        
        result = await setup_agent_before_agent_callback(wedding_id)
        
        # Assert the callback returns False for a non-existent wedding
        assert result is False, "Expected False when wedding ID is not found."
        
        mock_execute_supabase_sql.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_agent_before_agent_callback_supabase_error(self, mock_execute_supabase_sql):
        """
        Test case for setup_agent_before_agent_callback when execute_supabase_sql returns an error.
        """
        mock_execute_supabase_sql.return_value = {"status": "error", "error": "Query failed."}
        wedding_id = "error_wedding_id"
        
        result = await setup_agent_before_agent_callback(wedding_id)
        
        # Assert the callback returns False when Supabase query fails
        assert result is False, "Expected False when Supabase query fails."
        
        mock_execute_supabase_sql.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_agent_before_agent_callback_exception(self, mock_execute_supabase_sql):
        """
        Test case for setup_agent_before_agent_callback when an unexpected exception occurs.
        """
        mock_execute_supabase_sql.side_effect = Exception("Database is down")
        wedding_id = "exception_wedding_id"
        
        result = await setup_agent_before_agent_callback(wedding_id)
        
        # Assert the callback returns False for an unexpected exception
        assert result is False, "Expected False for an unexpected exception."
        
        mock_execute_supabase_sql.assert_called_once()