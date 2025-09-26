import json
from typing import Dict, Any, List, Optional
import asyncio
from sanskara.helpers import execute_supabase_sql
from sanskara.db_queries import (
    get_tasks_by_wedding_id_query,
    update_task_status_query,
    create_task_feedback_query,
    create_task_approval_query,
    create_timeline_event_query,
)
import logging # Import the custom JSON logger

async def get_tasks(wedding_id: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Fetches a list of tasks for a wedding, with optional filters.
    """
    logging.info(f"tool_name='get_tasks', wedding_id={wedding_id}, filters={filters}")
    logging.debug(f"Entering get_tasks tool for wedding_id: {wedding_id} with filters: {filters}.")
    try:
        filter_keys = list(filters.keys()) if filters else None
        query = get_tasks_by_wedding_id_query(filter_keys)
        params = {"wedding_id": wedding_id, **(filters or {})}
        result = await execute_supabase_sql(query, params)
        
        if result.get("status") == "success" and result.get("data"):
            tasks = result["data"]
            logging.info(f"Successfully retrieved {len(tasks)} tasks for wedding {wedding_id}.")
            return tasks
        logging.info(f"No tasks found for wedding {wedding_id}.")
        return []
    except Exception as e:
        logging.error(f"Error in get_tasks for wedding {wedding_id}: {e}", exc_info=True)
        return []

async def update_task_status(task_id: str, new_status: str) -> Dict[str, Any]:
    """
    Updates the status of a specific task.
    """
    logging.info(f"tool_name='update_task_status', task_id={task_id}, new_status={new_status}")
    logging.debug(f"Entering update_task_status tool for task_id: {task_id} with new_status: {new_status}.")
    try:
        query = update_task_status_query()
        params = {"task_id": task_id, "new_status": new_status}
        result = await execute_supabase_sql(query, params)
        if result.get("status") == "success":
            logging.info(f"Successfully updated task {task_id} to status: {new_status}.")
            return {"status": "success"}
        logging.error(f"Failed to update task {task_id} status to {new_status}. Result: {result}")
        return {"status": "failure", "message": result.get("message", "Failed to update task status.")}
    except Exception as e:
        logging.error(f"Error in update_task_status for task {task_id}: {e}", exc_info=True)
        return {"status": "failure", "message": "An unexpected error occurred during task status update."}

async def submit_task_feedback(task_id: str, user_id: str, related_entity_id: Optional[str], comment: str) -> Dict[str, Any]:
    """
    Writes feedback for a task (e.g., a comment on a shortlisted vendor) to the `task_feedback` table.
    """
    logging.info(f"tool_name='submit_task_feedback', task_id={task_id}, user_id={user_id}, related_entity_id={related_entity_id}")
    logging.debug(f"Entering submit_task_feedback tool for task_id: {task_id}, user_id: {user_id}, comment: {comment[:50]}...")
    try:
        feedback_content = f"Comment: {comment}"
        if related_entity_id:
            feedback_content += f" (Related Entity: {related_entity_id})"
            
        query = create_task_feedback_query()
        params = {
            "task_id": task_id,
            "user_id": user_id,
            "feedback_type": "comment",
            "content": feedback_content
        }
        result = await execute_supabase_sql(query, params)
        if result.get("status") == "success" and result.get("data"):
            feedback_id = result["data"][0].get("feedback_id") # Assuming feedback_id is returned
            logging.info(f"Successfully submitted feedback for task {task_id}. Feedback ID: {feedback_id}")
            return {"feedback_id": feedback_id}
        logging.error(f"Failed to submit feedback for task {task_id}. Result: {result}")
        return {"status": "failure", "message": result.get("message", "Failed to submit feedback.")}
    except Exception as e:
        logging.error(f"Error in submit_task_feedback for task {task_id}: {e}", exc_info=True)
        return {"status": "failure", "message": "An unexpected error occurred during feedback submission."}

async def approve_task_final_choice(task_id: str, user_id: str) -> Dict[str, Any]:
    """
    Records a final approval for a task, creating a row in the `task_approvals` table.
    """
    logging.info(f"tool_name='approve_task_final_choice', task_id={task_id}, user_id={user_id}")
    logging.debug(f"Entering approve_task_final_choice tool for task_id: {task_id}, user_id: {user_id}.")
    try:
        approving_party = "user"
        status = "approved"
        query = create_task_approval_query()
        params = {
            "task_id": task_id,
            "approving_party": approving_party,
            "status": status,
            "approved_by_user_id": user_id
        }
        result = await execute_supabase_sql(query, params)
        if result.get("status") == "success":
            # Assuming the approval query also handles the logic for is_fully_approved or we fetch it separately
            is_fully_approved = True # This would depend on your SQL query's return or another query
            logging.info(f"Successfully recorded final approval for task {task_id} by user {user_id}.")
            return {"status": "success", "is_fully_approved": is_fully_approved}
        logging.error(f"Failed to record approval for task {task_id}. Result: {result}")
        return {"status": "failure", "message": result.get("message", "Failed to approve task.")}
    except Exception as e:
        logging.error(f"Error in approve_task_final_choice for task {task_id}: {e}", exc_info=True)
        return {"status": "failure", "message": "An unexpected error occurred during task approval."}

async def create_timeline_event(wedding_id: str, event_name: str, event_date_time: str, location: Optional[str] = None) -> Dict[str, Any]:
    """
    Adds a new event to the detailed wedding timeline in the `timeline_events` table.
    """
    logging.info(f"tool_name='create_timeline_event', wedding_id={wedding_id}, event_name={event_name}")
    logging.debug(f"Entering create_timeline_event tool for wedding_id: {wedding_id}, event_name: {event_name}.")
    try:
        query = create_timeline_event_query(wedding_id, event_name, event_date_time, location)
        result = await execute_supabase_sql(query)
        if result.get("status") == "success" and result.get("data"):
            event_id = result["data"][0].get("event_id") # Assuming event_id is returned
            logging.info(f"Successfully created timeline event '{event_name}' for wedding {wedding_id}. Event ID: {event_id}")
            return {"event_id": event_id}
        logging.error(f"Failed to create timeline event '{event_name}' for wedding {wedding_id}. Result: {result}")
        return {"status": "failure", "message": result.get("message", "Failed to create timeline event.")}
    except Exception as e:
        logging.error(f"Error in create_timeline_event for wedding {wedding_id}: {e}", exc_info=True)
        return {"status": "failure", "message": "An unexpected error occurred during timeline event creation."}

if __name__ == "__main__":
    async def test_functions():
        print("=== Starting Task and Timeline Agent Supabase Tests ===")

        # Define common test data
        # Ensure these IDs exist in your Supabase DB for successful testing
        test_wedding_id = "236571a1-db81-4980-be99-f7ec3273881c"
        test_task_id = "08fc7772-2d07-421b-bb13-ae0d6d2b1453"
        test_user_id = "fca04215-2af3-4a4e-bcfa-c27a4f54474c"
        test_event_date_time = "2025-09-01T10:00:00Z"

        # Test get_tasks
        print("\n--- Testing get_tasks ---")
        tasks_result = await get_tasks(test_wedding_id)
        print(f"get_tasks result: {tasks_result}")
        assert isinstance(tasks_result, list), "get_tasks should return a list"
        if tasks_result:
            print(f"Retrieved {len(tasks_result)} tasks.")
        else:
            print("No tasks found for the given wedding ID. This might be expected if the DB is empty.")

        # Test update_task_status
        print("\n--- Testing update_task_status ---")
        # Ensure test_task_id exists and can be updated
        update_status_result = await update_task_status(test_task_id, "completed")
        print(f"update_task_status result: {update_status_result}")
        assert update_status_result.get("status") == "success", "update_task_status failed"

        # Test submit_task_feedback
        print("\n--- Testing submit_task_feedback ---")
        feedback_result = await submit_task_feedback(test_task_id, test_user_id, None, "This is a test comment from Supabase.")
        print(f"submit_task_feedback result: {feedback_result}")
        assert feedback_result.get("feedback_id") is not None, "submit_task_feedback failed"

        feedback_with_entity_result = await submit_task_feedback(test_task_id, test_user_id, "entity123", "Another comment for an entity from Supabase.")
        print(f"submit_task_feedback with related_entity_id result: {feedback_with_entity_result}")
        assert feedback_with_entity_result.get("feedback_id") is not None, "submit_task_feedback with related_entity_id failed"

        # Test approve_task_final_choice
        print("\n--- Testing approve_task_final_choice ---")
        approve_result = await approve_task_final_choice(test_task_id, test_user_id)
        print(f"approve_task_final_choice result: {approve_result}")
        assert approve_result.get("status") == "success", "approve_task_final_choice failed"

        # Test create_timeline_event
        print("\n--- Testing create_timeline_event ---")
        timeline_event_result = await create_timeline_event(test_wedding_id, "Supabase Test Event", test_event_date_time)
        print(f"create_timeline_event result: {timeline_event_result}")
        assert timeline_event_result.get("event_id") is not None, "create_timeline_event failed"

        timeline_event_with_location_result = await create_timeline_event(test_wedding_id, "Supabase Test Event with Location", test_event_date_time, "Virtual Location")
        print(f"create_timeline_event with location result: {timeline_event_with_location_result}")
        assert timeline_event_with_location_result.get("event_id") is not None, "create_timeline_event with location failed"

        print("\n=== All Task and Timeline Agent Supabase Tests Completed ===")

    import asyncio
    asyncio.run(test_functions())