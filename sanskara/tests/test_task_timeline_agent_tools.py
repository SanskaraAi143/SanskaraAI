import pytest
from unittest.mock import patch, MagicMock
from sanskara.sub_agents.task_and_timeline_agent.tools import (
    get_tasks,
    update_task_status,
    submit_task_feedback,
    approve_task_final_choice,
    create_timeline_event,
)
from sanskara.db import astra_db
from sanskara.db_queries import (
    get_tasks_by_wedding_id_query,
    update_task_status_query,
    create_task_feedback_query,
    create_task_approval_query,
    create_timeline_event_query,
)

# Mock the astra_db client
@pytest.fixture(autouse=True)
def mock_astra_db():
    with patch('sanskara.db.astra_db', new_callable=MagicMock) as mock_db:
        yield mock_db

@pytest.fixture(autouse=True)
def mock_logger():
    with patch('sanskara.sub_agents.task_and_timeline_agent.tools.logger', autospec=True) as mock_log:
        yield mock_log

# Test cases for get_tasks
def test_get_tasks_success(mock_astra_db, mock_logger):
    """
    Test successful retrieval of tasks with valid wedding_id.
    """
    mock_astra_db.collection.return_value.find.return_value = [
        {"task_id": "task1", "title": "Book Venue", "status": "pending_review", "due_date": "2025-08-01"},
        {"task_id": "task2", "title": "Send Invitations", "status": "completed", "due_date": "2025-07-15"},
    ]
    
    tasks = get_tasks("wedding123")
    assert isinstance(tasks, list), "Expected a list of tasks" # Assert that the return type is a list
    assert len(tasks) == 2, "Expected two tasks" # Assert that two tasks are returned
    assert tasks[0]["task_id"] == "task1", "Expected task1 as the first task_id" # Assert the ID of the first task
    mock_logger.debug.assert_called_with("Entering get_tasks tool for wedding_id: wedding123 with filters: None.") # Assert that debug logging was called
    mock_logger.info.assert_called_with("Successfully retrieved 2 tasks for wedding wedding123.") # Assert that info logging was called

def test_get_tasks_with_filters(mock_astra_db, mock_logger):
    """
    Test successful retrieval of tasks with filters.
    """
    mock_astra_db.collection.return_value.find.return_value = [
        {"task_id": "task1", "title": "Book Venue", "status": "pending_review", "due_date": "2025-08-01"},
    ]
    filters = {"status": "pending_review"}
    tasks = get_tasks("wedding123", filters)
    assert len(tasks) == 1, "Expected one task with filters" # Assert that one task is returned
    assert tasks[0]["status"] == "pending_review", "Expected task with pending_review status" # Assert the status of the returned task
    mock_logger.debug.assert_called_with(f"Entering get_tasks tool for wedding_id: wedding123 with filters: {filters}.") # Assert that debug logging was called with filters

def test_get_tasks_astra_db_not_initialized(mock_astra_db, mock_logger):
    """
    Test get_tasks when astra_db is not initialized.
    """
    mock_astra_db.collection.return_value = None # Simulate astra_db not being initialized
    with patch('sanskara.db.astra_db', None):
        tasks = get_tasks("wedding123")
        assert tasks == [], "Expected an empty list when astra_db is not initialized" # Assert an empty list is returned
        mock_logger.error.assert_called_with("AstraDB client not initialized for get_tasks.") # Assert that error logging was called

def test_get_tasks_exception_handling(mock_astra_db, mock_logger):
    """
    Test exception handling in get_tasks.
    """
    mock_astra_db.collection.side_effect = Exception("DB connection error") # Simulate a database connection error
    tasks = get_tasks("wedding123")
    assert tasks == [], "Expected an empty list on exception" # Assert an empty list is returned
    mock_logger.error.assert_called_with("Error in get_tasks for wedding wedding123: DB connection error", exc_info=True) # Assert that error logging was called with exception info

# Test cases for update_task_status
def test_update_task_status_success(mock_astra_db, mock_logger):
    """
    Test successful update of task status.
    """
    mock_astra_db.collection.return_value.update_one.return_value.modified_count = 1 # Simulate successful update
    result = update_task_status("task1", "completed")
    assert result == {"status": "success"}, "Expected success status" # Assert the return value is success
    mock_logger.debug.assert_called_with("Entering update_task_status tool for task_id: task1 with new_status: completed.") # Assert debug logging
    mock_logger.info.assert_called_with("Successfully updated task task1 to status: completed.") # Assert info logging

def test_update_task_status_astra_db_not_initialized(mock_astra_db, mock_logger):
    """
    Test update_task_status when astra_db is not initialized.
    """
    mock_astra_db.collection.return_value = None # Simulate astra_db not being initialized
    with patch('sanskara.db.astra_db', None):
        result = update_task_status("task1", "completed")
        assert result == {"status": "failure", "message": "Database client not initialized."}, "Expected database client not initialized message" # Assert failure message
        mock_logger.error.assert_called_with("AstraDB client not initialized for update_task_status.") # Assert error logging

def test_update_task_status_exception_handling(mock_astra_db, mock_logger):
    """
    Test exception handling in update_task_status.
    """
    mock_astra_db.collection.side_effect = Exception("DB update error") # Simulate a database update error
    result = update_task_status("task1", "completed")
    assert result == {"status": "failure", "message": "An unexpected error occurred during task status update."}, "Expected unexpected error message" # Assert failure message
    mock_logger.error.assert_called_with("Error in update_task_status for task task1: DB update error", exc_info=True) # Assert error logging with exception info

# Test cases for submit_task_feedback
def test_submit_task_feedback_success(mock_astra_db, mock_logger):
    """
    Test successful submission of task feedback.
    """
    mock_astra_db.collection.return_value.insert_one.return_value.inserted_id = "feedback123" # Simulate successful insertion
    result = submit_task_feedback("task1", "user1", None, "Great work!")
    assert result == {"feedback_id": "feedback123"}, "Expected feedback ID" # Assert feedback ID is returned
    mock_logger.debug.assert_called_with("Entering submit_task_feedback tool for task_id: task1, user_id: user1, comment: Great work!...") # Assert debug logging
    mock_logger.info.assert_called_with("Successfully submitted feedback for task task1. Feedback ID: feedback123") # Assert info logging

def test_submit_task_feedback_with_related_entity(mock_astra_db, mock_logger):
    """
    Test successful submission of task feedback with a related entity.
    """
    mock_astra_db.collection.return_value.insert_one.return_value.inserted_id = "feedback456" # Simulate successful insertion
    result = submit_task_feedback("task1", "user1", "vendor123", "Good vendor.")
    assert result == {"feedback_id": "feedback456"}, "Expected feedback ID" # Assert feedback ID is returned
    mock_logger.debug.assert_called_with("Entering submit_task_feedback tool for task_id: task1, user_id: user1, comment: Good vendor....") # Assert debug logging

def test_submit_task_feedback_astra_db_not_initialized(mock_astra_db, mock_logger):
    """
    Test submit_task_feedback when astra_db is not initialized.
    """
    mock_astra_db.collection.return_value = None # Simulate astra_db not being initialized
    with patch('sanskara.db.astra_db', None):
        result = submit_task_feedback("task1", "user1", None, "Comment")
        assert result == {"status": "failure", "message": "Database client not initialized."}, "Expected database client not initialized message" # Assert failure message
        mock_logger.error.assert_called_with("AstraDB client not initialized for submit_task_feedback.") # Assert error logging

def test_submit_task_feedback_exception_handling(mock_astra_db, mock_logger):
    """
    Test exception handling in submit_task_feedback.
    """
    mock_astra_db.collection.side_effect = Exception("DB insert error") # Simulate a database insert error
    result = submit_task_feedback("task1", "user1", None, "Comment")
    assert result == {"status": "failure", "message": "An unexpected error occurred during feedback submission."}, "Expected unexpected error message" # Assert failure message
    mock_logger.error.assert_called_with("Error in submit_task_feedback for task task1: DB insert error", exc_info=True) # Assert error logging with exception info

# Test cases for approve_task_final_choice
def test_approve_task_final_choice_success(mock_astra_db, mock_logger):
    """
    Test successful approval of a task's final choice.
    """
    mock_astra_db.collection.return_value.insert_one.return_value.inserted_id = "approval123" # Simulate successful insertion
    result = approve_task_final_choice("task1", "user1")
    assert result == {"status": "success", "is_fully_approved": True}, "Expected success and fully approved" # Assert success and fully approved
    mock_logger.debug.assert_called_with("Entering approve_task_final_choice tool for task_id: task1, user_id: user1.") # Assert debug logging
    mock_logger.info.assert_called_with("Successfully recorded final approval for task task1 by user user1.") # Assert info logging

def test_approve_task_final_choice_astra_db_not_initialized(mock_astra_db, mock_logger):
    """
    Test approve_task_final_choice when astra_db is not initialized.
    """
    mock_astra_db.collection.return_value = None # Simulate astra_db not being initialized
    with patch('sanskara.db.astra_db', None):
        result = approve_task_final_choice("task1", "user1")
        assert result == {"status": "failure", "message": "Database client not initialized."}, "Expected database client not initialized message" # Assert failure message
        mock_logger.error.assert_called_with("AstraDB client not initialized for approve_task_final_choice.") # Assert error logging

def test_approve_task_final_choice_exception_handling(mock_astra_db, mock_logger):
    """
    Test exception handling in approve_task_final_choice.
    """
    mock_astra_db.collection.side_effect = Exception("DB approval error") # Simulate a database approval error
    result = approve_task_final_choice("task1", "user1")
    assert result == {"status": "failure", "message": "An unexpected error occurred during task approval."}, "Expected unexpected error message" # Assert failure message
    mock_logger.error.assert_called_with("Error in approve_task_final_choice for task task1: DB approval error", exc_info=True) # Assert error logging with exception info

# Test cases for create_timeline_event
def test_create_timeline_event_success(mock_astra_db, mock_logger):
    """
    Test successful creation of a timeline event.
    """
    mock_astra_db.collection.return_value.insert_one.return_value.inserted_id = "event123" # Simulate successful insertion
    result = create_timeline_event("wedding123", "Wedding Day", "2025-12-25T14:00:00Z", "Venue Hall")
    assert result == {"event_id": "event123"}, "Expected event ID" # Assert event ID is returned
    mock_logger.debug.assert_called_with("Entering create_timeline_event tool for wedding_id: wedding123, event_name: Wedding Day.") # Assert debug logging
    mock_logger.info.assert_called_with("Successfully created timeline event 'Wedding Day' for wedding wedding123. Event ID: event123") # Assert info logging

def test_create_timeline_event_no_location(mock_astra_db, mock_logger):
    """
    Test successful creation of a timeline event without a location.
    """
    mock_astra_db.collection.return_value.insert_one.return_value.inserted_id = "event456" # Simulate successful insertion
    result = create_timeline_event("wedding123", "Engagement Party", "2025-06-01T18:00:00Z")
    assert result == {"event_id": "event456"}, "Expected event ID" # Assert event ID is returned
    mock_logger.debug.assert_called_with("Entering create_timeline_event tool for wedding_id: wedding123, event_name: Engagement Party.") # Assert debug logging

def test_create_timeline_event_astra_db_not_initialized(mock_astra_db, mock_logger):
    """
    Test create_timeline_event when astra_db is not initialized.
    """
    mock_astra_db.collection.return_value = None # Simulate astra_db not being initialized
    with patch('sanskara.db.astra_db', None):
        result = create_timeline_event("wedding123", "Event", "2025-01-01T00:00:00Z")
        assert result == {"status": "failure", "message": "Database client not initialized."}, "Expected database client not initialized message" # Assert failure message
        mock_logger.error.assert_called_with("AstraDB client not initialized for create_timeline_event.") # Assert error logging

def test_create_timeline_event_exception_handling(mock_astra_db, mock_logger):
    """
    Test exception handling in create_timeline_event.
    """
    mock_astra_db.collection.side_effect = Exception("DB event error") # Simulate a database event error
    result = create_timeline_event("wedding123", "Event", "2025-01-01T00:00:00Z")
    assert result == {"status": "failure", "message": "An unexpected error occurred during timeline event creation."}, "Expected unexpected error message" # Assert failure message
    mock_logger.error.assert_called_with("Error in create_timeline_event for wedding wedding123: DB event error", exc_info=True) # Assert error logging with exception info