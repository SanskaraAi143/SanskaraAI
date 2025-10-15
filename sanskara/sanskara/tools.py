import json
from typing import Optional, Dict, Any, List
from google.genai import types
from google.adk.models import LlmResponse, LlmRequest
from sanskara.adk_artifacts import artifact_service, get_artifact_metadata, find_session_artifacts_by_filenames, list_all_session_artifacts, get_latest_session_for_user
import os, base64
from google.adk.tools.tool_context import ToolContext

from sanskara.helpers import execute_supabase_sql
import logging # Import the custom JSON logger
from sanskara.context_models import WorkflowContextSummary # Import the new model

# Restrict exported symbols so deprecated names (e.g. list_artifacts_for_current_session) are NOT auto-exposed
__all__ = [
    "get_wedding_context",
    "get_active_workflows",
    "get_tasks_for_wedding",
    "update_workflow_status",
    "create_workflow",
    "upsert_workflow",
    "update_task_details",
    "create_task",
    "upsert_task",
    "get_task_feedback",
    "add_task_feedback",
    "get_task_approvals",
    "set_task_approval",
    "get_complete_wedding_context",
    "resolve_artifact_filenames",
    "load_artifact_content",
    "list_user_artifacts",
    "list_user_files_py",
    # Intentionally excluding deprecated wrappers
]

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
        logging.error(f"Error fetching wedding context for {wedding_id}: {e}")
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
        logging.error(f"Error fetching active workflows for {wedding_id}: {e}")
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
        logging.error(f"Error fetching tasks for {wedding_id}: {e}")
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
        try:
            # Validate and serialize the context_summary using the Pydantic model
            validated_summary = WorkflowContextSummary(**context_summary)
            sql += ", context_summary = :context_summary"
            params["context_summary"] = validated_summary.model_dump_json() # Use model_dump_json for Pydantic v2
        except Exception as e:
            logging.error(f"Invalid context_summary for workflow {workflow_id}: {e}")
            return {"status": "error", "message": f"Invalid context_summary: {e}"}
    sql += " WHERE workflow_id = :workflow_id RETURNING *;"
    
    try:
        result = await execute_supabase_sql(sql, params)
        if result and result.get("status") == "success":
            return {"status": "success", "data": result.get("data")}
        else:
            return {"status": "error", "message": result.get("error", "Unknown error during workflow status update")}
    except Exception as e:
        logging.error(f"Error updating workflow {workflow_id} status to {new_status}: {e}")
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
    # Validate and serialize the context_summary using the Pydantic model
    serialized_context_summary = None
    if context_summary is not None:
        try:
            validated_summary = WorkflowContextSummary(**context_summary)
            serialized_context_summary = validated_summary.model_dump_json()
        except Exception as e:
            logging.error(f"Invalid context_summary for new workflow {workflow_name}: {e}")
            return {"status": "error", "message": f"Invalid context_summary: {e}"}

    sql = """
        INSERT INTO workflows (wedding_id, workflow_name, status, context_summary)
        VALUES (:wedding_id, :workflow_name, :status, :context_summary)
        RETURNING *;
    """
    params = {
        "wedding_id": wedding_id,
        "workflow_name": workflow_name,
        "status": status,
        "context_summary": serialized_context_summary
    }
    
    try:
        result = await execute_supabase_sql(sql, params)
        if result and result.get("status") == "success" and result.get("data"):
            return {"status": "success", "data": result["data"][0]}
        else:
            return {"status": "error", "message": result.get("error", "Unknown error during workflow creation")}
    except Exception as e:
        logging.error(f"Error creating workflow {workflow_name} for wedding {wedding_id}: {e}")
        return {"status": "error", "message": str(e)}

async def upsert_workflow(
    wedding_id: str,
    workflow_name: str,
    status: str = 'not_started',
    context_summary: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Creates a new workflow or updates an existing one if a workflow with the same
    wedding_id and workflow_name already exists.

    Args:
        wedding_id: The UUID of the wedding this workflow belongs to.
        workflow_name: The name of the workflow (e.g., 'CoreVendorBookingWorkflow').
        status: The initial status of the workflow (default: 'not_started').
        context_summary: Optional. A JSONB object for initial context.

    Returns:
        A dictionary containing the created/updated workflow's data or an error.
    """
    # First, try to find an existing workflow
    sql_select = "SELECT workflow_id FROM workflows WHERE wedding_id = :wedding_id AND workflow_name = :workflow_name;"
    params_select = {"wedding_id": wedding_id, "workflow_name": workflow_name}
    
    try:
        result_select = await execute_supabase_sql(sql_select, params_select)
        
        if result_select and result_select.get("status") == "success" and result_select.get("data"):
            # Workflow exists, update it
            existing_workflow_id = result_select["data"][0]["workflow_id"]
            logging.info(f"Workflow '{workflow_name}' already exists for wedding {wedding_id}. Updating.")
            return await update_workflow_status(existing_workflow_id, status, context_summary)
        else:
            # Workflow does not exist, create a new one
            logging.info(f"Workflow '{workflow_name}' does not exist for wedding {wedding_id}. Creating new.")
            return await create_workflow(wedding_id, workflow_name, status, context_summary)
            
    except Exception as e:
        logging.error(f"Error in upsert_workflow for {workflow_name} (wedding {wedding_id}): {e}")
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
        logging.error(f"Error updating task {task_id} with updates {updates}: {e}")
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
        logging.error(f"Error creating task {title} for wedding {wedding_id}: {e}")
        return {"status": "error", "message": str(e)}
    

async def upsert_task(
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
    Creates a new task or updates an existing one if a task with the same
    wedding_id and title already exists.

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
        A dictionary containing the created/updated task's data or an error.
    """
    # First, try to find an existing task
    sql_select = "SELECT task_id FROM tasks WHERE wedding_id = :wedding_id AND title = :title;"
    params_select = {"wedding_id": wedding_id, "title": title}
    
    try:
        result_select = await execute_supabase_sql(sql_select, params_select)
        
        if result_select and result_select.get("status") == "success" and result_select.get("data"):
            # Task exists, update it
            existing_task_id = result_select["data"][0]["task_id"]
            logging.info(f"Task '{title}' already exists for wedding {wedding_id}. Updating.")
            updates = {
                "description": description,
                "is_complete": is_complete,
                "due_date": due_date,
                "priority": priority,
                "category": category,
                "status": status,
                "lead_party": lead_party
            }
            # Filter out None values from updates to avoid overwriting with None if not provided
            updates = {k: v for k, v in updates.items() if v is not None}
            return await update_task_details(existing_task_id, updates)
        else:
            # Task does not exist, create a new one
            logging.info(f"Task '{title}' does not exist for wedding {wedding_id}. Creating new.")
            return await create_task(
                wedding_id, title, description, is_complete, due_date,
                priority, category, status, lead_party
            )
            
    except Exception as e:
        logging.error(f"Error in upsert_task for {title} (wedding {wedding_id}): {e}")
        return {"status": "error", "message": str(e)}

async def get_task_feedback(task_id: str) -> List[Dict[str, Any]]:
    """
    Retrieves all feedback entries for a specific task.

    Args:
        task_id: The UUID of the task.

    Returns:
        A list of dictionaries, each representing a feedback entry.
    """
    sql = "SELECT * FROM task_feedback WHERE task_id = :task_id ORDER BY created_at DESC;"
    params = {"task_id": task_id}
    try:
        result = await execute_supabase_sql(sql, params)
        if result and result.get("status") == "success" and result.get("data"):
            return result["data"]
        else:
            return []
    except Exception as e:
        logging.error(f"Error fetching task feedback for {task_id}: {e}")
        return {"error": str(e)}

async def add_task_feedback(
    task_id: str,
    user_id: str,
    content: str,
    feedback_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Inserts a feedback entry for a task into task_feedback.

    Args:
        task_id: Task identifier.
        user_id: Authoring user id.
        content: Feedback text/content.
        feedback_type: Optional tag (e.g., 'comment', 'like', 'concern').

    Returns:
        {status, data|message}
    """
    sql = (
        """
        INSERT INTO task_feedback (task_id, user_id, feedback_type, content)
        VALUES (:task_id, :user_id, :feedback_type, :content)
        RETURNING *;
        """
    )
    params = {
        "task_id": task_id,
        "user_id": user_id,
        "feedback_type": feedback_type,
        "content": content,
    }
    try:
        result = await execute_supabase_sql(sql, params)
        if result and result.get("status") == "success":
            return {"status": "success", "data": result.get("data")}
        else:
            return {"status": "error", "message": result.get("error", "Unknown error adding feedback")}
    except Exception as e:
        logging.error(f"Error adding task feedback for {task_id}: {e}")
        return {"status": "error", "message": str(e)}

async def get_task_approvals(task_id: str) -> List[Dict[str, Any]]:
    """
    Retrieves all approval entries for a specific task.

    Args:
        task_id: The UUID of the task.

    Returns:
        A list of dictionaries, each representing an approval entry.
    """
    sql = "SELECT * FROM task_approvals WHERE task_id = :task_id ORDER BY created_at DESC;"
    params = {"task_id": task_id}
    try:
        result = await execute_supabase_sql(sql, params)
        if result and result.get("status") == "success" and result.get("data"):
            return result["data"]
        else:
            return []
    except Exception as e:
        logging.error(f"Error fetching task approvals for {task_id}: {e}")
        return {"error": str(e)}

async def set_task_approval(
    task_id: str,
    approving_party: str,
    status: str,
    approved_by_user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Inserts an approval record (e.g., 'approved'/'rejected') into task_approvals.

    Args:
        task_id: Task identifier.
        approving_party: e.g., 'bride', 'groom', 'couple', 'parent'.
        status: 'approved' | 'rejected' | 'needs_changes' | custom states.
        approved_by_user_id: Optional explicit user id performing approval.

    Returns:
        {status, data|message}
    """
    sql = (
        """
        INSERT INTO task_approvals (task_id, approving_party, status, approved_by_user_id)
        VALUES (:task_id, :approving_party, :status, :approved_by_user_id)
        RETURNING *;
        """
    )
    params = {
        "task_id": task_id,
        "approving_party": approving_party,
        "status": status,
        "approved_by_user_id": approved_by_user_id,
    }
    try:
        result = await execute_supabase_sql(sql, params)
        if result and result.get("status") == "success":
            return {"status": "success", "data": result.get("data")}
        else:
            return {"status": "error", "message": result.get("error", "Unknown error setting approval")}
    except Exception as e:
        logging.error(f"Error setting task approval for {task_id}: {e}")
        return {"status": "error", "message": str(e)}


async def get_complete_wedding_context(wedding_id: str) -> Dict[str, Any]:
    """
    Retrieves all wedding context data in a single optimized query using joins.
    This replaces multiple separate calls to get_wedding_context, get_active_workflows, 
    get_tasks_for_wedding, get_task_feedback, and get_task_approvals.

    Args:
        wedding_id: The UUID of the wedding.

    Returns:
        A dictionary containing:
        - wedding_data: Wedding details
        - active_workflows: List of active workflows
        - all_tasks: List of tasks with feedback and approvals
    """
    sql = """
    WITH wedding_info AS (
        SELECT * FROM weddings WHERE wedding_id = :wedding_id
    ),
    active_workflows_data AS (
        SELECT * FROM workflows 
        WHERE wedding_id = :wedding_id 
        AND status IN ('in_progress', 'paused', 'awaiting_feedback')
    ),
    tasks_with_details AS (
        SELECT 
            t.*,
            COALESCE(
                json_agg(
                    DISTINCT jsonb_build_object(
                        'feedback_id', tf.feedback_id,
                        'user_id', tf.user_id,
                        'feedback_type', tf.feedback_type,
                        'content', tf.content,
                        'created_at', tf.created_at
                    )
                ) FILTER (WHERE tf.feedback_id IS NOT NULL), 
                '[]'::json
            ) AS feedback,
            COALESCE(
                json_agg(
                    DISTINCT jsonb_build_object(
                        'approval_id', ta.approval_id,
                        'approving_party', ta.approving_party,
                        'status', ta.status,
                        'approved_by_user_id', ta.approved_by_user_id,
                        'created_at', ta.created_at,
                        'updated_at', ta.updated_at
                    )
                ) FILTER (WHERE ta.approval_id IS NOT NULL), 
                '[]'::json
            ) AS approvals
        FROM tasks t
        LEFT JOIN task_feedback tf ON t.task_id = tf.task_id
        LEFT JOIN task_approvals ta ON t.task_id = ta.task_id
        WHERE t.wedding_id = :wedding_id
        GROUP BY t.task_id, t.wedding_id, t.title, t.description, t.is_complete, 
                 t.due_date, t.priority, t.category, t.status, t.lead_party, 
                 t.created_at, t.updated_at
    )
    SELECT 
        (SELECT row_to_json(wedding_info) FROM wedding_info) as wedding_data,
        (SELECT COALESCE(json_agg(active_workflows_data), '[]'::json) FROM active_workflows_data) as active_workflows,
        (SELECT COALESCE(json_agg(tasks_with_details), '[]'::json) FROM tasks_with_details) as all_tasks;
    """
    
    params = {"wedding_id": wedding_id}
    
    try:
        result = await execute_supabase_sql(sql, params)
        if result and result.get("status") == "success" and result.get("data"):
            data = result["data"][0]
            return {
                "wedding_data": data.get("wedding_data", {}),
                "active_workflows": data.get("active_workflows", []),
                "all_tasks": data.get("all_tasks", [])
            }
        else:
            logging.warning(f"No data found for wedding_id: {wedding_id}")
            return {
                "wedding_data": {},
                "active_workflows": [],
                "all_tasks": []
            }
    except Exception as e:
        logging.error(f"Error fetching complete wedding context for {wedding_id}: {e}")
        return {
            "error": str(e),
            "wedding_data": {},
            "active_workflows": [],
            "all_tasks": []
        }

async def resolve_artifact_filenames(filenames: List[str], session_id: str, user_id: str, app_name: Optional[str] = None, alternate_user_ids: Optional[List[str]] = None, alternate_session_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """Resolve user-visible filenames to internal artifact versions and metadata for the current session.
    Enhanced: detects swapped arguments (user_id passed as name, session_id passed as user UUID) and auto-recovers.
    """
    app_name = app_name or os.getenv("SANSKARA_APP_NAME", "sanskara")
    try:
        clean_names = [f.strip() for f in filenames if f and f.strip()]
        logging.debug({
            "event": "resolve_artifact_filenames:start",
            "input_filenames": filenames,
            "clean_filenames": clean_names,
            "app_name": app_name,
            "user_id": user_id,
            "session_id": session_id,
        })
        if not clean_names:
            return {"status": "success", "resolved": [], "note": "no_valid_filenames"}
        matches = find_session_artifacts_by_filenames(app_name, user_id, session_id, clean_names)  # primary
        attempted = [(user_id, session_id, "primary")]
        index_snapshot = list_all_session_artifacts(app_name)
        existing_users = {x['user_id'] for x in index_snapshot}
        existing_sessions = {x['session_id'] for x in index_snapshot}
        # If no matches, attempt fallback heuristics
        if not matches:
            import re
            uuid_re = re.compile(r"^[0-9a-fA-F-]{30,36}$")
            # Heuristic 1: Swapped values (session_id actually user_uuid, user_id is display/email/name)
            if uuid_re.match(session_id) and user_id not in existing_users and session_id in existing_users:
                derived_user = session_id
                # Try latest session for that user first
                latest_sess = get_latest_session_for_user(app_name, derived_user)
                if latest_sess:
                    m = find_session_artifacts_by_filenames(app_name, derived_user, latest_sess, clean_names)
                    attempted.append((derived_user, latest_sess, "swap_latest_session"))
                    if m:
                        matches = m
                        user_id = derived_user
                        session_id = latest_sess
                # If still none, brute force that user's sessions from snapshot
                if not matches:
                    user_sessions = {x['session_id'] for x in index_snapshot if x['user_id'] == derived_user}
                    for s in list(user_sessions)[:5]:
                        m = find_session_artifacts_by_filenames(app_name, derived_user, s, clean_names)
                        attempted.append((derived_user, s, "swap_scan"))
                        if m:
                            matches = m
                            user_id = derived_user
                            session_id = s
                            break
            # Heuristic 2: Try alternate provided lists
            if not matches:
                alt_users = alternate_user_ids or []
                alt_sessions = alternate_session_ids or []
                if not alt_users:
                    # include all existing users (bounded)
                    alt_users = list(existing_users)[:6]
                if not alt_sessions:
                    alt_sessions = list(existing_sessions)[:6]
                for au in alt_users:
                    for asess in alt_sessions:
                        if (au, asess, "alt") in attempted:
                            continue
                        m = find_session_artifacts_by_filenames(app_name, au, asess, clean_names)
                        attempted.append((au, asess, "alt"))
                        if m:
                            matches = m
                            user_id = au
                            session_id = asess
                            break
                    if matches:
                        break
        logging.debug({
            "event": "resolve_artifact_filenames:result",
            "requested": clean_names,
            "resolved_count": len(matches),
            "resolved_filenames": [m.get("filename") for m in matches],
            "final_user_id": user_id,
            "final_session_id": session_id,
            "attempts": attempted,
        })
        if not matches:
            logging.debug({
                "event": "resolve_artifact_filenames:empty_final",
                "available_index_size": len(index_snapshot),
                "users_indexed": list(existing_users),
                "sessions_indexed": list(existing_sessions),
            })
        return {"status": "success", "resolved": matches, "final_user_id": user_id, "final_session_id": session_id}
    except Exception as e:
        logging.error(f"resolve_artifact_filenames failed: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}

async def load_artifact_content(filename: str , tool_context: ToolContext) -> Dict[str, Any]:
    logging.debug({
        "event": "load_artifact_content:start",
        "filename" : filename,
    })
    try:
        art = await tool_context.load_artifact(filename)
    except Exception as e:
        logging.error(f"load_artifact_content load failed: {e}")
        return {"status": "error", "error": f"load_failed: {e}"}
    return {
        "status": "success",
        "filename": filename,
        "mime_type": art.inline_data.mime_type,
        "data": art.inline_data.data
    }

# --- Artifact Tools Reimplementation (explicit user_id & session_id like working curl endpoints) ---
async def list_user_artifacts(user_id: str, session_id: str, app_name: Optional[str] = None, limit: int = 25) -> Dict[str, Any]:
    """List artifacts for a given user & session (explicit identifiers required, mirrors /artifacts/list).
    Returns: {status, artifacts:[{filename, version, mime_type, caption, auto_summary}]}

    IMPORTANT:
    - This replaces the deprecated list_artifacts_for_current_session.
    - Always pass explicit user_id and session_id taken from state (e.g. db_chat_session_id / current_user_id).
    - Never guess IDs; if unavailable, ask user to perform an action that provides them (or request re-upload).
    """
    app = app_name or os.getenv("SANSKARA_APP_NAME", "sanskara")
    try:
        from sanskara.adk_artifacts import list_session_artifacts
        items = await list_session_artifacts(app, user_id, session_id)[:limit]
        return {"status": "success", "artifacts": items, "user_id": user_id, "session_id": session_id}
    except Exception as e:
        logging.error(f"list_user_artifacts failed: {e}")
        return {"status": "error", "error": str(e)}

# Removed deprecated list_artifacts_for_current_session to prevent the model from auto-calling it.
# If calls appear in logs, they come from cached prompt memory; reinforce prompt to ONLY use list_user_artifacts.

# Keep resolve_artifacts stub for backward compatibility but ensure it clearly directs usage.
async def resolve_artifacts(filenames: List[str]) -> Dict[str, Any]:  # legacy name
    return {"status": "error", "error": "deprecated_use_list_user_artifacts_then_load_artifact_content"}

async def list_user_files_py(tool_context: ToolContext) -> str:  # ToolContext typed indirectly to avoid import cycles
    """List available artifact filenames for the current session via ADK ToolContext.

    Returns a human-readable bullet list or a short status string.
    This is the preferred lightweight listing tool for the orchestrator.
    For programmatic version metadata use list_user_artifacts(user_id, session_id).
    """
    try:
        available_files = await tool_context.list_artifacts()
        logging.debug({
            "event": "list_user_files_py",
            "available_files_count": len(available_files),
            "available_files": available_files,
        })
         # If no files, return a simple message
         # If files, format them as a bullet list
         # This is for human-readable output in orchestrator responses
         # Not intended for programmatic use (use list_user_artifacts instead)
         # This is a tool for the orchestrator to quickly check available files
         # without needing to know user_id/session_id explicitly.
        if not available_files:
            return "You have no saved artifacts."
        file_list_str = "\n".join([f"- {fname}" for fname in available_files])
        return f"Here are your available artifacts:\n{file_list_str}"
    except ValueError as e:
        logging.error(f"list_user_files_py ValueError: {e}")
        return "Error: Could not list artifacts (service not configured)."
    except Exception as e:
        logging.error(f"list_user_files_py unexpected error: {e}", exc_info=True)
        return "Error: An unexpected issue occurred while listing artifacts."

if __name__ == "__main__":
    # Example usage
    import asyncio
    wedding_id = "9ce1a9c6-9c47-47e7-97cc-e4e222d0d90c"
    
    async def main():
        context = await get_complete_wedding_context(wedding_id)
        print("-------------------------------")
        print(json.dumps(context, indent=2))
        print("-------------------------------")
    
    asyncio.run(main())
