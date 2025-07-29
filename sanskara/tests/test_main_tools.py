import pytest
from unittest.mock import AsyncMock, patch
import json
from sanskara.tools import (
    get_wedding_context,
    get_active_workflows,
    get_tasks_for_wedding,
    update_workflow_status,
    create_workflow,
    update_task_details,
    create_task,
    get_task_feedback,
    get_task_approvals,
)

# Mock the logger to prevent actual logging during tests
@pytest.fixture(autouse=True)
def mock_logger():
    with patch('sanskara.tools.logger') as mock_log:
        yield mock_log

@pytest.fixture
def mock_execute_supabase_sql():
    with patch('sanskara.tools.execute_supabase_sql', new_callable=AsyncMock) as mock_sql:
        yield mock_sql

@pytest.mark.asyncio
async def test_get_wedding_context_success(mock_execute_supabase_sql):
    # Mock successful response
    mock_execute_supabase_sql.return_value = {
        "status": "success",
        "data": [{"wedding_id": "123", "name": "Test Wedding", "status": "planning"}]
    }
    wedding_id = "123"
    result = await get_wedding_context(wedding_id)
    # Assert that execute_supabase_sql was called with the correct SQL and parameters
    mock_execute_supabase_sql.assert_called_once_with(
        "SELECT * FROM weddings WHERE wedding_id = :wedding_id;",
        {"wedding_id": wedding_id}
    )
    # Assert the expected output
    assert result == {"wedding_id": "123", "name": "Test Wedding", "status": "planning"}

@pytest.mark.asyncio
async def test_get_wedding_context_not_found(mock_execute_supabase_sql):
    # Mock no data found
    mock_execute_supabase_sql.return_value = {
        "status": "success",
        "data": []
    }
    wedding_id = "456"
    result = await get_wedding_context(wedding_id)
    # Assert that execute_supabase_sql was called with the correct SQL and parameters
    mock_execute_supabase_sql.assert_called_once_with(
        "SELECT * FROM weddings WHERE wedding_id = :wedding_id;",
        {"wedding_id": wedding_id}
    )
    # Assert an empty dictionary is returned when no data is found
    assert result == {}

@pytest.mark.asyncio
async def test_get_wedding_context_error(mock_execute_supabase_sql):
    # Mock an error from execute_supabase_sql
    mock_execute_supabase_sql.side_effect = Exception("Database error")
    wedding_id = "789"
    result = await get_wedding_context(wedding_id)
    # Assert that execute_supabase_sql was called
    mock_execute_supabase_sql.assert_called_once()
    # Assert an error dictionary is returned
    assert result == {"error": "Database error"}

@pytest.mark.asyncio
async def test_get_active_workflows_success(mock_execute_supabase_sql):
    # Mock successful response
    mock_execute_supabase_sql.return_value = {
        "status": "success",
        "data": [
            {"workflow_id": "w1", "name": "WF1", "status": "in_progress"},
            {"workflow_id": "w2", "name": "WF2", "status": "paused"}
        ]
    }
    wedding_id = "123"
    result = await get_active_workflows(wedding_id)
    # Assert that execute_supabase_sql was called with the correct SQL and parameters
    mock_execute_supabase_sql.assert_called_once_with(
        "SELECT * FROM workflows WHERE wedding_id = :wedding_id AND status IN ('in_progress', 'paused', 'awaiting_feedback');",
        {"wedding_id": wedding_id}
    )
    # Assert the expected output
    assert len(result) == 2 # Expected: 2 workflows
    assert result[0]["workflow_id"] == "w1" # Expected: First workflow ID is 'w1'

@pytest.mark.asyncio
async def test_get_active_workflows_no_workflows(mock_execute_supabase_sql):
    # Mock no data found
    mock_execute_supabase_sql.return_value = {
        "status": "success",
        "data": []
    }
    wedding_id = "456"
    result = await get_active_workflows(wedding_id)
    # Assert that execute_supabase_sql was called
    mock_execute_supabase_sql.assert_called_once()
    # Assert an empty list is returned
    assert result == []

@pytest.mark.asyncio
async def test_get_active_workflows_error(mock_execute_supabase_sql):
    # Mock an error from execute_supabase_sql
    mock_execute_supabase_sql.side_effect = Exception("Workflow DB error")
    wedding_id = "789"
    result = await get_active_workflows(wedding_id)
    # Assert that execute_supabase_sql was called
    mock_execute_supabase_sql.assert_called_once()
    # Assert an error dictionary is returned
    assert result == {"error": "Workflow DB error"}

@pytest.mark.asyncio
async def test_get_tasks_for_wedding_success_no_filters(mock_execute_supabase_sql):
    # Mock successful response
    mock_execute_supabase_sql.return_value = {
        "status": "success",
        "data": [
            {"task_id": "t1", "title": "Task 1", "status": "not_started"},
            {"task_id": "t2", "title": "Task 2", "status": "completed"}
        ]
    }
    wedding_id = "123"
    result = await get_tasks_for_wedding(wedding_id)
    # Assert that execute_supabase_sql was called with the correct SQL and parameters
    mock_execute_supabase_sql.assert_called_once_with(
        "SELECT * FROM tasks WHERE wedding_id = :wedding_id;",
        {"wedding_id": wedding_id}
    )
    # Assert the expected output
    assert len(result) == 2 # Expected: 2 tasks
    assert result[0]["task_id"] == "t1" # Expected: First task ID is 't1'

@pytest.mark.asyncio
async def test_get_tasks_for_wedding_success_with_status_filter(mock_execute_supabase_sql):
    # Mock successful response
    mock_execute_supabase_sql.return_value = {
        "status": "success",
        "data": [
            {"task_id": "t2", "title": "Task 2", "status": "completed"}
        ]
    }
    wedding_id = "123"
    status = "completed"
    result = await get_tasks_for_wedding(wedding_id, status=status)
    # Assert that execute_supabase_sql was called with the correct SQL and parameters
    mock_execute_supabase_sql.assert_called_once_with(
        "SELECT * FROM tasks WHERE wedding_id = :wedding_id AND status = :status;",
        {"wedding_id": wedding_id, "status": status}
    )
    # Assert the expected output
    assert len(result) == 1 # Expected: 1 task
    assert result[0]["status"] == "completed" # Expected: Task status is 'completed'

@pytest.mark.asyncio
async def test_get_tasks_for_wedding_success_with_lead_party_filter(mock_execute_supabase_sql):
    # Mock successful response
    mock_execute_supabase_sql.return_value = {
        "status": "success",
        "data": [
            {"task_id": "t1", "title": "Task 1", "lead_party": "bride_side"}
        ]
    }
    wedding_id = "123"
    lead_party = "bride_side"
    result = await get_tasks_for_wedding(wedding_id, lead_party=lead_party)
    # Assert that execute_supabase_sql was called with the correct SQL and parameters
    mock_execute_supabase_sql.assert_called_once_with(
        "SELECT * FROM tasks WHERE wedding_id = :wedding_id AND lead_party = :lead_party;",
        {"wedding_id": wedding_id, "lead_party": lead_party}
    )
    # Assert the expected output
    assert len(result) == 1 # Expected: 1 task
    assert result[0]["lead_party"] == "bride_side" # Expected: Task lead_party is 'bride_side'

@pytest.mark.asyncio
async def test_get_tasks_for_wedding_success_with_all_filters(mock_execute_supabase_sql):
    # Mock successful response
    mock_execute_supabase_sql.return_value = {
        "status": "success",
        "data": [
            {"task_id": "t1", "title": "Task 1", "status": "not_started", "lead_party": "couple"}
        ]
    }
    wedding_id = "123"
    status = "not_started"
    lead_party = "couple"
    result = await get_tasks_for_wedding(wedding_id, status=status, lead_party=lead_party)
    # Assert that execute_supabase_sql was called with the correct SQL and parameters
    mock_execute_supabase_sql.assert_called_once_with(
        "SELECT * FROM tasks WHERE wedding_id = :wedding_id AND status = :status AND lead_party = :lead_party;",
        {"wedding_id": wedding_id, "status": status, "lead_party": lead_party}
    )
    # Assert the expected output
    assert len(result) == 1 # Expected: 1 task
    assert result[0]["status"] == "not_started" # Expected: Task status is 'not_started'
    assert result[0]["lead_party"] == "couple" # Expected: Task lead_party is 'couple'

@pytest.mark.asyncio
async def test_get_tasks_for_wedding_no_tasks(mock_execute_supabase_sql):
    # Mock no data found
    mock_execute_supabase_sql.return_value = {
        "status": "success",
        "data": []
    }
    wedding_id = "456"
    result = await get_tasks_for_wedding(wedding_id)
    # Assert that execute_supabase_sql was called
    mock_execute_supabase_sql.assert_called_once()
    # Assert an empty list is returned
    assert result == []

@pytest.mark.asyncio
async def test_get_tasks_for_wedding_error(mock_execute_supabase_sql):
    # Mock an error from execute_supabase_sql
    mock_execute_supabase_sql.side_effect = Exception("Task DB error")
    wedding_id = "789"
    result = await get_tasks_for_wedding(wedding_id)
    # Assert that execute_supabase_sql was called
    mock_execute_supabase_sql.assert_called_once()
    # Assert an error dictionary is returned
    assert result == {"error": "Task DB error"}

@pytest.mark.asyncio
async def test_update_workflow_status_success_no_context(mock_execute_supabase_sql):
    # Mock successful response
    mock_execute_supabase_sql.return_value = {
        "status": "success",
        "data": [{"workflow_id": "w1", "status": "completed"}]
    }
    workflow_id = "w1"
    new_status = "completed"
    result = await update_workflow_status(workflow_id, new_status)
    # Assert that execute_supabase_sql was called with the correct SQL and parameters
    mock_execute_supabase_sql.assert_called_once()
    sql_arg = mock_execute_supabase_sql.call_args[0][0]
    params_arg = mock_execute_supabase_sql.call_args[0][1]
    assert "UPDATE workflows SET status = :new_status, updated_at = NOW() WHERE workflow_id = :workflow_id RETURNING *;" in sql_arg # Expected: SQL contains update statement without context_summary
    assert params_arg["new_status"] == new_status # Expected: new_status parameter is correct
    assert params_arg["workflow_id"] == workflow_id # Expected: workflow_id parameter is correct
    # Assert the expected output
    assert result == {"status": "success", "data": [{"workflow_id": "w1", "status": "completed"}]} # Expected: Success status and data

@pytest.mark.asyncio
async def test_update_workflow_status_success_with_context(mock_execute_supabase_sql):
    # Mock successful response
    mock_execute_supabase_sql.return_value = {
        "status": "success",
        "data": [{"workflow_id": "w1", "status": "paused", "context_summary": {"key": "value"}}]
    }
    workflow_id = "w1"
    new_status = "paused"
    context_summary = {"key": "value"}
    result = await update_workflow_status(workflow_id, new_status, context_summary)
    # Assert that execute_supabase_sql was called with the correct SQL and parameters
    mock_execute_supabase_sql.assert_called_once()
    sql_arg = mock_execute_supabase_sql.call_args[0][0]
    params_arg = mock_execute_supabase_sql.call_args[0][1]
    assert "UPDATE workflows SET status = :new_status, updated_at = NOW(), context_summary = :context_summary WHERE workflow_id = :workflow_id RETURNING *;" in sql_arg # Expected: SQL contains update statement with context_summary
    assert params_arg["new_status"] == new_status # Expected: new_status parameter is correct
    assert params_arg["workflow_id"] == workflow_id # Expected: workflow_id parameter is correct
    assert json.loads(params_arg["context_summary"]) == context_summary # Expected: context_summary parameter is correct and JSON parsed
    # Assert the expected output
    assert result == {"status": "success", "data": [{"workflow_id": "w1", "status": "paused", "context_summary": {"key": "value"}}]} # Expected: Success status and data

@pytest.mark.asyncio
async def test_update_workflow_status_failure(mock_execute_supabase_sql):
    # Mock a failed response from execute_supabase_sql
    mock_execute_supabase_sql.return_value = {
        "status": "error",
        "error": "Workflow not found"
    }
    workflow_id = "nonexistent"
    new_status = "completed"
    result = await update_workflow_status(workflow_id, new_status)
    # Assert that execute_supabase_sql was called
    mock_execute_supabase_sql.assert_called_once()
    # Assert an error dictionary is returned
    assert result == {"status": "error", "message": "Workflow not found"} # Expected: Error status and message

@pytest.mark.asyncio
async def test_update_workflow_status_exception(mock_execute_supabase_sql):
    # Mock an exception during execution
    mock_execute_supabase_sql.side_effect = Exception("Network error")
    workflow_id = "w1"
    new_status = "completed"
    result = await update_workflow_status(workflow_id, new_status)
    # Assert that execute_supabase_sql was called
    mock_execute_supabase_sql.assert_called_once()
    # Assert an error dictionary with the exception message is returned
    assert result == {"status": "error", "message": "Network error"} # Expected: Error status and network error message

@pytest.mark.asyncio
async def test_create_workflow_success_no_context(mock_execute_supabase_sql):
    # Mock successful response
    mock_execute_supabase_sql.return_value = {
        "status": "success",
        "data": [{"workflow_id": "new_w", "wedding_id": "w_id", "workflow_name": "WF Name", "status": "not_started"}]
    }
    wedding_id = "w_id"
    workflow_name = "WF Name"
    result = await create_workflow(wedding_id, workflow_name)
    # Assert that execute_supabase_sql was called with the correct SQL and parameters
    mock_execute_supabase_sql.assert_called_once()
    sql_arg = mock_execute_supabase_sql.call_args[0][0]
    params_arg = mock_execute_supabase_sql.call_args[0][1]
    assert "INSERT INTO workflows (wedding_id, workflow_name, status, context_summary)" in sql_arg # Expected: SQL contains insert statement
    assert params_arg["wedding_id"] == wedding_id # Expected: wedding_id parameter is correct
    assert params_arg["workflow_name"] == workflow_name # Expected: workflow_name parameter is correct
    assert params_arg["status"] == "not_started" # Expected: status parameter is 'not_started'
    assert params_arg["context_summary"] is None # Expected: context_summary parameter is None
    # Assert the expected output
    assert result["status"] == "success" # Expected: Success status
    assert result["data"]["workflow_id"] == "new_w" # Expected: new workflow ID is returned

@pytest.mark.asyncio
async def test_create_workflow_success_with_context(mock_execute_supabase_sql):
    # Mock successful response
    mock_execute_supabase_sql.return_value = {
        "status": "success",
        "data": [{"workflow_id": "new_w_ctx", "wedding_id": "w_id_ctx", "workflow_name": "WF Name Ctx", "status": "in_progress", "context_summary": {"foo": "bar"}}]
    }
    wedding_id = "w_id_ctx"
    workflow_name = "WF Name Ctx"
    status = "in_progress"
    context_summary = {"foo": "bar"}
    result = await create_workflow(wedding_id, workflow_name, status=status, context_summary=context_summary)
    # Assert that execute_supabase_sql was called with the correct SQL and parameters
    mock_execute_supabase_sql.assert_called_once()
    sql_arg = mock_execute_supabase_sql.call_args[0][0]
    params_arg = mock_execute_supabase_sql.call_args[0][1]
    assert "INSERT INTO workflows (wedding_id, workflow_name, status, context_summary)" in sql_arg # Expected: SQL contains insert statement
    assert params_arg["wedding_id"] == wedding_id # Expected: wedding_id parameter is correct
    assert params_arg["workflow_name"] == workflow_name # Expected: workflow_name parameter is correct
    assert params_arg["status"] == status # Expected: status parameter is 'in_progress'
    assert json.loads(params_arg["context_summary"]) == context_summary # Expected: context_summary parameter is correct and JSON parsed
    # Assert the expected output
    assert result["status"] == "success" # Expected: Success status
    assert result["data"]["workflow_id"] == "new_w_ctx" # Expected: new workflow ID is returned
    assert result["data"]["status"] == status # Expected: status in returned data is correct

@pytest.mark.asyncio
async def test_create_workflow_failure(mock_execute_supabase_sql):
    # Mock a failed response from execute_supabase_sql
    mock_execute_supabase_sql.return_value = {
        "status": "error",
        "error": "Duplicate workflow"
    }
    wedding_id = "w_id_fail"
    workflow_name = "WF Name Fail"
    result = await create_workflow(wedding_id, workflow_name)
    # Assert that execute_supabase_sql was called
    mock_execute_supabase_sql.assert_called_once()
    # Assert an error dictionary is returned
    assert result == {"status": "error", "message": "Duplicate workflow"} # Expected: Error status and message

@pytest.mark.asyncio
async def test_create_workflow_exception(mock_execute_supabase_sql):
    # Mock an exception during execution
    mock_execute_supabase_sql.side_effect = Exception("DB connection lost")
    wedding_id = "w_id_exc"
    workflow_name = "WF Name Exc"
    result = await create_workflow(wedding_id, workflow_name)
    # Assert that execute_supabase_sql was called
    mock_execute_supabase_sql.assert_called_once()
    # Assert an error dictionary with the exception message is returned
    assert result == {"status": "error", "message": "DB connection lost"} # Expected: Error status and DB connection lost message

@pytest.mark.asyncio
async def test_update_task_details_success(mock_execute_supabase_sql):
    # Mock successful response
    mock_execute_supabase_sql.return_value = {
        "status": "success",
        "data": [{"task_id": "t1", "status": "completed", "priority": "high"}]
    }
    task_id = "t1"
    updates = {"status": "completed", "priority": "high"}
    result = await update_task_details(task_id, updates)
    # Assert that execute_supabase_sql was called with the correct SQL and parameters
    mock_execute_supabase_sql.assert_called_once()
    sql_arg = mock_execute_supabase_sql.call_args[0][0]
    params_arg = mock_execute_supabase_sql.call_args[0][1]
    assert "UPDATE tasks SET status = :status, priority = :priority, updated_at = NOW() WHERE task_id = :task_id RETURNING *;" in sql_arg # Expected: SQL contains update statement with status and priority
    assert params_arg["task_id"] == task_id # Expected: task_id parameter is correct
    assert params_arg["status"] == "completed" # Expected: status parameter is 'completed'
    assert params_arg["priority"] == "high" # Expected: priority parameter is 'high'
    # Assert the expected output
    assert result == {"status": "success", "data": [{"task_id": "t1", "status": "completed", "priority": "high"}]} # Expected: Success status and updated data

@pytest.mark.asyncio
async def test_update_task_details_no_updates(mock_execute_supabase_sql):
    task_id = "t1"
    updates = {}
    result = await update_task_details(task_id, updates)
    # Assert that execute_supabase_sql was not called
    mock_execute_supabase_sql.assert_not_called()
    # Assert an error message for no updates provided
    assert result == {"status": "error", "message": "No updates provided."} # Expected: Error message for no updates

@pytest.mark.asyncio
async def test_update_task_details_failure(mock_execute_supabase_sql):
    # Mock a failed response from execute_supabase_sql
    mock_execute_supabase_sql.return_value = {
        "status": "error",
        "error": "Task not found"
    }
    task_id = "nonexistent"
    updates = {"status": "completed"}
    result = await update_task_details(task_id, updates)
    # Assert that execute_supabase_sql was called
    mock_execute_supabase_sql.assert_called_once()
    # Assert an error dictionary is returned
    assert result == {"status": "error", "message": "Task not found"} # Expected: Error status and message

@pytest.mark.asyncio
async def test_update_task_details_exception(mock_execute_supabase_sql):
    # Mock an exception during execution
    mock_execute_supabase_sql.side_effect = Exception("Invalid column")
    task_id = "t1"
    updates = {"invalid_col": "value"}
    result = await update_task_details(task_id, updates)
    # Assert that execute_supabase_sql was called
    mock_execute_supabase_sql.assert_called_once()
    # Assert an error dictionary with the exception message is returned
    assert result == {"status": "error", "message": "Invalid column"} # Expected: Error status and invalid column message

@pytest.mark.asyncio
async def test_create_task_success_minimal_args(mock_execute_supabase_sql):
    # Mock successful response
    mock_execute_supabase_sql.return_value = {
        "status": "success",
        "data": [{"task_id": "new_task_id", "wedding_id": "w_id", "title": "New Task", "is_complete": False}]
    }
    wedding_id = "w_id"
    title = "New Task"
    result = await create_task(wedding_id, title)
    # Assert that execute_supabase_sql was called with the correct SQL and parameters
    mock_execute_supabase_sql.assert_called_once()
    sql_arg = mock_execute_supabase_sql.call_args[0][0]
    params_arg = mock_execute_supabase_sql.call_args[0][1]
    assert "INSERT INTO tasks (wedding_id, title, description, is_complete, due_date, priority, category, status, lead_party)" in sql_arg # Expected: SQL contains insert statement
    assert params_arg["wedding_id"] == wedding_id # Expected: wedding_id parameter is correct
    assert params_arg["title"] == title # Expected: title parameter is correct
    assert params_arg["description"] is None # Expected: description is None
    assert params_arg["is_complete"] is False # Expected: is_complete is False
    assert params_arg["priority"] == "medium" # Expected: priority is 'medium'
    assert params_arg["status"] == "No Status" # Expected: status is 'No Status'
    # Assert the expected output
    assert result["status"] == "success" # Expected: Success status
    assert result["data"]["task_id"] == "new_task_id" # Expected: new task ID is returned

@pytest.mark.asyncio
async def test_create_task_success_all_args(mock_execute_supabase_sql):
    # Mock successful response
    mock_execute_supabase_sql.return_value = {
        "status": "success",
        "data": [{"task_id": "new_task_full", "wedding_id": "w_id_full", "title": "Full Task", "description": "Desc", "is_complete": True, "due_date": "2025-01-01", "priority": "high", "category": "Planning", "status": "Pending Review", "lead_party": "couple"}]
    }
    wedding_id = "w_id_full"
    title = "Full Task"
    description = "Desc"
    is_complete = True
    due_date = "2025-01-01"
    priority = "high"
    category = "Planning"
    status = "Pending Review"
    lead_party = "couple"
    result = await create_task(wedding_id, title, description, is_complete, due_date, priority, category, status, lead_party)
    # Assert that execute_supabase_sql was called with the correct SQL and parameters
    mock_execute_supabase_sql.assert_called_once()
    params_arg = mock_execute_supabase_sql.call_args[0][1]
    assert params_arg["wedding_id"] == wedding_id # Expected: wedding_id parameter is correct
    assert params_arg["title"] == title # Expected: title parameter is correct
    assert params_arg["description"] == description # Expected: description parameter is correct
    assert params_arg["is_complete"] == is_complete # Expected: is_complete parameter is correct
    assert params_arg["due_date"] == due_date # Expected: due_date parameter is correct
    assert params_arg["priority"] == priority # Expected: priority parameter is correct
    assert params_arg["category"] == category # Expected: category parameter is correct
    assert params_arg["status"] == status # Expected: status parameter is correct
    assert params_arg["lead_party"] == lead_party # Expected: lead_party parameter is correct
    # Assert the expected output
    assert result["status"] == "success" # Expected: Success status
    assert result["data"]["task_id"] == "new_task_full" # Expected: new task ID is returned

@pytest.mark.asyncio
async def test_create_task_failure(mock_execute_supabase_sql):
    # Mock a failed response from execute_supabase_sql
    mock_execute_supabase_sql.return_value = {
        "status": "error",
        "error": "Invalid wedding ID"
    }
    wedding_id = "invalid_w_id"
    title = "Failing Task"
    result = await create_task(wedding_id, title)
    # Assert that execute_supabase_sql was called
    mock_execute_supabase_sql.assert_called_once()
    # Assert an error dictionary is returned
    assert result == {"status": "error", "message": "Invalid wedding ID"} # Expected: Error status and message

@pytest.mark.asyncio
async def test_create_task_exception(mock_execute_supabase_sql):
    # Mock an exception during execution
    mock_execute_supabase_sql.side_effect = Exception("DB write error")
    wedding_id = "w_id_exc"
    title = "Task with Exception"
    result = await create_task(wedding_id, title)
    # Assert that execute_supabase_sql was called
    mock_execute_supabase_sql.assert_called_once()
    # Assert an error dictionary with the exception message is returned
    assert result == {"status": "error", "message": "DB write error"} # Expected: Error status and DB write error message

@pytest.mark.asyncio
async def test_get_task_feedback_success(mock_execute_supabase_sql):
    # Mock successful response
    mock_execute_supabase_sql.return_value = {
        "status": "success",
        "data": [
            {"feedback_id": "f1", "task_id": "t1", "comment": "Good job!"},
            {"feedback_id": "f2", "task_id": "t1", "comment": "Needs revision"}
        ]
    }
    task_id = "t1"
    result = await get_task_feedback(task_id)
    # Assert that execute_supabase_sql was called with the correct SQL and parameters
    mock_execute_supabase_sql.assert_called_once_with(
        "SELECT * FROM task_feedback WHERE task_id = :task_id ORDER BY created_at DESC;",
        {"task_id": task_id}
    )
    # Assert the expected output
    assert len(result) == 2 # Expected: 2 feedback entries
    assert result[0]["feedback_id"] == "f1" # Expected: First feedback ID is 'f1'

@pytest.mark.asyncio
async def test_get_task_feedback_no_feedback(mock_execute_supabase_sql):
    # Mock no data found
    mock_execute_supabase_sql.return_value = {
        "status": "success",
        "data": []
    }
    task_id = "t2"
    result = await get_task_feedback(task_id)
    # Assert that execute_supabase_sql was called
    mock_execute_supabase_sql.assert_called_once()
    # Assert an empty list is returned
    assert result == []

@pytest.mark.asyncio
async def test_get_task_feedback_error(mock_execute_supabase_sql):
    # Mock an error from execute_supabase_sql
    mock_execute_supabase_sql.side_effect = Exception("Feedback DB error")
    task_id = "t3"
    result = await get_task_feedback(task_id)
    # Assert that execute_supabase_sql was called
    mock_execute_supabase_sql.assert_called_once()
    # Assert an error dictionary is returned
    assert result == {"error": "Feedback DB error"}

@pytest.mark.asyncio
async def test_get_task_approvals_success(mock_execute_supabase_sql):
    # Mock successful response
    mock_execute_supabase_sql.return_value = {
        "status": "success",
        "data": [
            {"approval_id": "a1", "task_id": "t1", "approved_by": "User A"},
            {"approval_id": "a2", "task_id": "t1", "approved_by": "User B"}
        ]
    }
    task_id = "t1"
    result = await get_task_approvals(task_id)
    # Assert that execute_supabase_sql was called with the correct SQL and parameters
    mock_execute_supabase_sql.assert_called_once_with(
        "SELECT * FROM task_approvals WHERE task_id = :task_id ORDER BY created_at DESC;",
        {"task_id": task_id}
    )
    # Assert the expected output
    assert len(result) == 2 # Expected: 2 approval entries
    assert result[0]["approval_id"] == "a1" # Expected: First approval ID is 'a1'

@pytest.mark.asyncio
async def test_get_task_approvals_no_approvals(mock_execute_supabase_sql):
    # Mock no data found
    mock_execute_supabase_sql.return_value = {
        "status": "success",
        "data": []
    }
    task_id = "t2"
    result = await get_task_approvals(task_id)
    # Assert that execute_supabase_sql was called
    mock_execute_supabase_sql.assert_called_once()
    # Assert an empty list is returned
    assert result == []

@pytest.mark.asyncio
async def test_get_task_approvals_error(mock_execute_supabase_sql):
    # Mock an error from execute_supabase_sql
    mock_execute_supabase_sql.side_effect = Exception("Approval DB error")
    task_id = "t3"
    result = await get_task_approvals(task_id)
    # Assert that execute_supabase_sql was called
    mock_execute_supabase_sql.assert_called_once()
    # Assert an error dictionary is returned
    assert result == {"error": "Approval DB error"}