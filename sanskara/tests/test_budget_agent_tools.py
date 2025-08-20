import unittest
from unittest.mock import AsyncMock, patch
import datetime

# Assuming these are the functions to be tested
from sanskara.sub_agents.budget_and_expense_agent.tools import add_expense, get_total_budget, get_budget_summary

class TestBudgetAgentTools(unittest.IsolatedAsyncioTestCase):

    @patch('sanskara.sub_agents.budget_and_expense_agent.tools.execute_supabase_sql')
    @patch('sanskara.sub_agents.budget_and_expense_agent.tools.create_budget_item_query')
    async def test_add_expense_success(self, mock_create_query, mock_execute_sql):
        # Mock the SQL query generation
        mock_create_query.return_value = "INSERT INTO budget_items ..."

        # Mock the Supabase execution result for success
        mock_execute_sql.return_value = {"status": "success", "data": [{"item_id": "test_item_id_123"}]}

        wedding_id = "test_wedding_id"
        item_name = "test_item"
        category = "test_category"
        amount = 100.0

        result = await add_expense(wedding_id, item_name, category, amount)

        # Assertions
        mock_create_query.assert_called_once_with(wedding_id, item_name, category, amount, None, contribution_by=None)
        # Expected: create_budget_item_query should be called with the provided arguments.
        # Actual: mock_create_query.call_args[0] contains the arguments used in the call.

        mock_execute_sql.assert_called_once()
        # Expected: execute_supabase_sql should be called exactly once.
        # Actual: mock_execute_sql.call_count should be 1.

        self.assertEqual(result["status"], "success")
        # Expected: The status of the result should be "success".
        # Actual: result["status"] is the actual status returned.

        self.assertEqual(result["item_id"], "test_item_id_123")
        # Expected: The item_id in the result should match the mocked item_id.
        # Actual: result["item_id"] is the actual item_id returned.

    @patch('sanskara.sub_agents.budget_and_expense_agent.tools.execute_supabase_sql')
    @patch('sanskara.sub_agents.budget_and_expense_agent.tools.create_budget_item_query')
    async def test_add_expense_failure(self, mock_create_query, mock_execute_sql):
        # Mock the SQL query generation
        mock_create_query.return_value = "INSERT INTO budget_items ..."

        # Mock the Supabase execution result for failure
        mock_execute_sql.return_value = {"status": "error", "error": "Database error"}

        wedding_id = "test_wedding_id"
        item_name = "test_item"
        category = "test_category"
        amount = 100.0

        result = await add_expense(wedding_id, item_name, category, amount)

        # Assertions
        mock_create_query.assert_called_once_with(wedding_id, item_name, category, amount, None, contribution_by=None)
        # Expected: create_budget_item_query should be called with the provided arguments.
        # Actual: mock_create_query.call_args[0] contains the arguments used in the call.

        mock_execute_sql.assert_called_once()
        # Expected: execute_supabase_sql should be called exactly once.
        # Actual: mock_execute_sql.call_count should be 1.

        self.assertEqual(result["status"], "error")
        # Expected: The status of the result should be "error".
        # Actual: result["status"] is the actual status returned.

        self.assertIn("Database error", result["message"])
        # Expected: The error message should contain "Database error".
        # Actual: result["message"] is the actual error message returned.

    @patch('sanskara.sub_agents.budget_and_expense_agent.tools.execute_supabase_sql')
    @patch('sanskara.sub_agents.budget_and_expense_agent.tools.get_budget_summary_query')
    async def test_get_budget_summary_success(self, mock_get_summary_query, mock_execute_sql):
        # Mock the SQL query generation
        mock_get_summary_query.return_value = "SELECT category, SUM(amount) FROM budget_items GROUP BY category ..."

        # Mock the Supabase execution result for success
        mock_execute_sql.return_value = {"status": "success", "data": [{"category": "Food", "total_amount": 500}, {"category": "Decor", "total_amount": 300}]}

        wedding_id = "test_wedding_id"

        result = await get_budget_summary(wedding_id)

        # Assertions
        mock_get_summary_query.assert_called_once_with(wedding_id)
        # Expected: get_budget_summary_query should be called with the wedding_id.
        # Actual: mock_get_summary_query.call_args[0] contains the arguments used in the call.

        mock_execute_sql.assert_called_once()
        # Expected: execute_supabase_sql should be called exactly once.
        # Actual: mock_execute_sql.call_count should be 1.

        self.assertEqual(result["status"], "success")
        # Expected: The status of the result should be "success".
        # Actual: result["status"] is the actual status returned.

        self.assertIsInstance(result["budget_summary"], list)
        # Expected: budget_summary should be a list.
        # Actual: type(result["budget_summary"]) is the actual type.

        self.assertEqual(len(result["budget_summary"]), 2)
        # Expected: The length of budget_summary should be 2.
        # Actual: len(result["budget_summary"]) is the actual length.

        self.assertEqual(result["budget_summary"][0]["category"], "Food")
        # Expected: The first item's category should be "Food".
        # Actual: result["budget_summary"][0]["category"] is the actual category.

    @patch('sanskara.sub_agents.budget_and_expense_agent.tools.execute_supabase_sql')
    @patch('sanskara.sub_agents.budget_and_expense_agent.tools.get_budget_summary_query')
    async def test_get_budget_summary_failure(self, mock_get_summary_query, mock_execute_sql):
        # Mock the SQL query generation
        mock_get_summary_query.return_value = "SELECT category, SUM(amount) FROM budget_items GROUP BY category ..."

        # Mock the Supabase execution result for failure
        mock_execute_sql.return_value = {"status": "error", "error": "Network error"}

        wedding_id = "test_wedding_id"

        result = await get_budget_summary(wedding_id)

        # Assertions
        mock_get_summary_query.assert_called_once_with(wedding_id)
        # Expected: get_budget_summary_query should be called with the wedding_id.
        # Actual: mock_get_summary_query.call_args[0] contains the arguments used in the call.

        mock_execute_sql.assert_called_once()
        # Expected: execute_supabase_sql should be called exactly once.
        # Actual: mock_execute_sql.call_count should be 1.

        self.assertEqual(result["status"], "error")
        # Expected: The status of the result should be "error".
        # Actual: result["status"] is the actual status returned.

        self.assertIn("Network error", result["message"])
        # Expected: The error message should contain "Network error".
        # Actual: result["message"] is the actual error message returned.