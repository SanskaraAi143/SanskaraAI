import json
import logging
from typing import Optional, Dict, Any, List
from google.genai import types 
from google.adk.models import LlmResponse, LlmRequest
from google.adk.agents.callback_context import CallbackContext

from .helpers import execute_supabase_sql

logger = logging.getLogger(__name__)

async def get_wedding_context(wedding_id: str) -> dict:
    """
    Retrieves the high-level context of a specific wedding from the 'weddings' table.
    This includes general wedding details, status, and any aggregated onboarding data summary.

    Args:
        wedding_id: The UUID of the wedding.

    Returns:
        A dictionary containing the wedding context, or an empty dictionary if not found.
    """
    sql = "SELECT * FROM weddings WHERE wedding_id = :wedding_id;"
    params = {"wedding_id": wedding_id}
    try:
        result = await execute_supabase_sql(sql, params)
        if result and result.get("status") == "success" and result.get("data"):
            return result["data"][0]
        else:
            return {}
    except Exception as e:
        logger.error(f"Error fetching wedding context for {wedding_id}: {e}")
        return {"error": str(e)}

async def get_active_workflows(wedding_id: str) -> List[Dict[str, Any]]:
    """
    Retrieves all active or paused workflows associated with a specific wedding from the 'workflows' table.

    Args:
        wedding_id: The UUID of the wedding.

    Returns:
        A list of dictionaries, each representing an active or paused workflow.
    """
    sql = "SELECT * FROM workflows WHERE wedding_id = :wedding_id AND status IN ('in_progress', 'paused', 'awaiting_feedback');"
    params = {"wedding_id": wedding_id}
    try:
        result = await execute_supabase_sql(sql, params)
        if result and result.get("status") == "success" and result.get("data"):
            return result["data"]
        else:
            return []
    except Exception as e:
        logger.error(f"Error fetching active workflows for {wedding_id}: {e}")
        return {"error": str(e)}

async def get_tasks_for_wedding(wedding_id: str, status: Optional[str] = None, lead_party: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieves tasks for a specific wedding, with optional filters for status and lead party.

    Args:
        wedding_id: The UUID of the wedding.
        status: Optional. Filter tasks by their status (e.g., 'not_started', 'pending_review', 'completed').
        lead_party: Optional. Filter tasks by the responsible party ('bride_side', 'groom_side', 'couple').

    Returns:
        A list of dictionaries, each representing a task.
    """
    sql = "SELECT * FROM tasks WHERE wedding_id = :wedding_id"
    params = {"wedding_id": wedding_id}
    if status:
        sql += " AND status = :status"
        params["status"] = status
    if lead_party:
        sql += " AND lead_party = :lead_party"
        params["lead_party"] = lead_party
    
    sql += ";"
    
    try:
        result = await execute_supabase_sql(sql, params)
        if result and result.get("status") == "success" and result.get("data"):
            return result["data"]
        else:
            return []
    except Exception as e:
        logger.error(f"Error fetching tasks for {wedding_id}: {e}")
        return {"error": str(e)}

async def update_workflow_status(workflow_id: str, new_status: str, context_summary: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Updates the status and optionally the context summary of a workflow.

    Args:
        workflow_id: The UUID of the workflow to update.
        new_status: The new status for the workflow (e.g., 'completed', 'paused', 'in_progress').
        context_summary: Optional. A JSONB object to update the context_summary column.

    Returns:
        A dictionary indicating success or failure.
    """
    sql = "UPDATE workflows SET status = :new_status, updated_at = NOW()"
    params = {"new_status": new_status, "workflow_id": workflow_id}
    if context_summary is not None:
        sql += ", context_summary = :context_summary"
        params["context_summary"] = json.dumps(context_summary) # Supabase expects JSON string for JSONB
    sql += " WHERE workflow_id = :workflow_id RETURNING *;"
    
    try:
        result = await execute_supabase_sql(sql, params)
        if result and result.get("status") == "success":
            return {"status": "success", "data": result.get("data")}
        else:
            return {"status": "error", "message": result.get("error", "Unknown error during workflow status update")}
    except Exception as e:
        logger.error(f"Error updating workflow {workflow_id} status to {new_status}: {e}")
        return {"status": "error", "message": str(e)}

async def create_workflow(
    wedding_id: str,
    workflow_name: str,
    status: str = 'not_started',
    context_summary: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Creates a new workflow entry in the 'workflows' table.

    Args:
        wedding_id: The UUID of the wedding this workflow belongs to.
        workflow_name: The name of the workflow (e.g., 'CoreVendorBookingWorkflow').
        status: The initial status of the workflow (default: 'not_started').
        context_summary: Optional. A JSONB object for initial context.

    Returns:
        A dictionary containing the created workflow's data or an error.
    """
    sql = """
        INSERT INTO workflows (wedding_id, workflow_name, status, context_summary)
        VALUES (:wedding_id, :workflow_name, :status, :context_summary)
        RETURNING *;
    """
    params = {
        "wedding_id": wedding_id,
        "workflow_name": workflow_name,
        "status": status,
        "context_summary": json.dumps(context_summary) if context_summary is not None else None
    }
    
    try:
        result = await execute_supabase_sql(sql, params)
        if result and result.get("status") == "success" and result.get("data"):
            return {"status": "success", "data": result["data"][0]}
        else:
            return {"status": "error", "message": result.get("error", "Unknown error during workflow creation")}
    except Exception as e:
        logger.error(f"Error creating workflow {workflow_name} for wedding {wedding_id}: {e}")
        return {"status": "error", "message": str(e)}

async def update_task_details(task_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Updates details of an existing task in the 'tasks' table.

    Args:
        task_id: The UUID of the task to update.
        updates: A dictionary of columns and their new values (e.g., {"status": "completed", "due_date": "2024-12-31"}).

    Returns:
        A dictionary indicating success or failure.
    """
    if not updates:
        return {"status": "error", "message": "No updates provided."}

    set_clauses = []
    params = {"task_id": task_id}
    for key, value in updates.items():
        set_clauses.append(f"{key} = :{key}")
        params[key] = value
    
    sql = f"UPDATE tasks SET {', '.join(set_clauses)}, updated_at = NOW() WHERE task_id = :task_id RETURNING *;"
    
    try:
        result = await execute_supabase_sql(sql, params)
        if result and result.get("status") == "success":
            return {"status": "success", "data": result.get("data")}
        else:
            return {"status": "error", "message": result.get("error", "Unknown error during task update")}
    except Exception as e:
        logger.error(f"Error updating task {task_id} with updates {updates}: {e}")
        return {"status": "error", "message": str(e)}

async def create_task(
    wedding_id: str,
    title: str,
    description: Optional[str] = None,
    is_complete: bool = False,
    due_date: Optional[str] = None, # Assuming YYYY-MM-DD format
    priority: str = 'medium',
    category: Optional[str] = None,
    status: str = 'No Status',
    lead_party: Optional[str] = None
) -> Dict[str, Any]:
    """
    Creates a new task entry in the 'tasks' table.

    Args:
        wedding_id: The UUID of the wedding this task belongs to.
        title: The title of the task.
        description: Optional. A detailed description of the task.
        is_complete: Whether the task is completed (default: False).
        due_date: Optional. The due date of the task in YYYY-MM-DD format.
        priority: The priority of the task (default: 'medium').
        category: Optional. The category of the task.
        status: The status of the task (default: 'No Status').
        lead_party: Optional. The responsible party ('bride_side', 'groom_side', 'couple').

    Returns:
        A dictionary containing the created task's data or an error.
    """
    sql = """
        INSERT INTO tasks (wedding_id, title, description, is_complete, due_date, priority, category, status, lead_party)
        VALUES (:wedding_id, :title, :description, :is_complete, :due_date, :priority, :category, :status, :lead_party)
        RETURNING *;
    """
    params = {
        "wedding_id": wedding_id,
        "title": title,
        "description": description,
        "is_complete": is_complete,
        "due_date": due_date,
        "priority": priority,
        "category": category,
        "status": status,
        "lead_party": lead_party
    }
    
    try:
        result = await execute_supabase_sql(sql, params)
        if result and result.get("status") == "success" and result.get("data"):
            return {"status": "success", "data": result["data"][0]}
        else:
            return {"status": "error", "message": result.get("error", "Unknown error during task creation")}
    except Exception as e:
        logger.error(f"Error creating task {title} for wedding {wedding_id}: {e}")
        return {"status": "error", "message": str(e)}
    

# before_agent_callback function to handle context add for wedding details
# def orchestrator_agent_before_agent_callback(callback_context :CallbackContext , llm_request : LlmRequest) -> Optional[LlmResponse]:
#     """
#     Callback to add wedding context to the LLM request before invoking the agent.
#     This ensures the agent has access to the wedding details for processing.
#
#     Args:
#         callback_context: The context for the callback, containing session and user information.
#         llm_request: The original LLM request being processed.
#
#     Returns:
#         An updated LlmResponse with the wedding context added, or None if no context is available.
#     """
#     wedding_id = callback_context.get("wedding_id")
#     if not wedding_id:
#         logger.warning("No wedding_id found in callback context.")
#         return None
#
#     # Fetch wedding context
#     wedding_context = get_wedding_context(wedding_id)
#
#     if not wedding_context:
#         logger.warning(f"No context found for wedding_id {wedding_id}.")
#         return None
#
#     # Add wedding context to the LLM request
#     llm_request.context["wedding_context"] = wedding_context
#     return llm_request