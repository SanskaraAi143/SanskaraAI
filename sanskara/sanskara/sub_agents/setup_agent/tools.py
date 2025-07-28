import datetime
from google.adk.tools import ToolContext
from typing import Dict, Any, List
from google.genai import types 
from google.adk.agents.callback_context import CallbackContext
import json
# Import execute_supabase_sql from the shared libraries
from ...helpers import execute_supabase_sql
def get_current_datetime() -> Dict[str, Any]:
    """
    Returns the current UTC date and time in ISO 8601 format.
    """
    current_utc_datetime = datetime.datetime.now(datetime.timezone.utc)
    return {"current_datetime_utc": current_utc_datetime.isoformat()}

async def bulk_create_workflows(tool_context: ToolContext, wedding_id: str, workflows_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Bulk inserts workflow data into the 'workflows' table.
    The LLM is responsible for generating the workflows_data.
    """
    with open("logs/bulk_create.log", "a") as log_file:
        log_file.write(f"Bulk create workflows called with wedding_id: {len(workflows_data)} and workflows_data: {workflows_data}\n")
    #return {"status" : "success", "message": f"This is a placeholder for bulk_create_workflows. {workflows_data}"}
    if not wedding_id or not workflows_data:
        return {"status": "error", "message": "wedding_id and workflows_data are required."}

    insert_values = []
    for workflow in workflows_data:
        workflow_name = workflow.get("workflow_name", "Unnamed Workflow")
        workflow_status = workflow.get("status", "not_started")
        context_summary = workflow.get("context_summary", {})
        insert_values.append(f"('{workflow_name}', '{workflow_status}', '{wedding_id}', '{json.dumps(context_summary)}')")

    sql = f"""
    INSERT INTO workflows (workflow_name, status, wedding_id)
    VALUES {", ".join(insert_values)};
    """
    with open("logs/bulk_create.sql", "a") as log_file:
        log_file.write(f"SQL for bulk_create_workflows: {sql}\n")
    result = await execute_supabase_sql(sql)

    if result.get("status") == "success":
        return {"status": "success", "message": f"Successfully created {len(workflows_data)} workflows."}
    else:
        return {"status": "error", "message": f"Failed to create workflows: {result.get('error')}"}

async def bulk_create_tasks(tool_context: ToolContext, wedding_id: str, tasks_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Bulk inserts task data into the 'tasks' table.
    The LLM is responsible for generating the tasks_data, including due_date, lead_party, etc.
    """
    with open("logs/bulk_create.log", "a") as log_file:
        log_file.write(f"Bulk create tasks called with wedding_id: {len(tasks_data)} {wedding_id} and tasks_data: {tasks_data}\n")
    #return {"status" : "success", "message": f"This is a placeholder for bulk_create_tasks. {tasks_data}"}
    if not wedding_id or not tasks_data:
        return {"status": "error", "message": "wedding_id and tasks_data are required."}

    insert_values = []
    params = []
    for idx, task in enumerate(tasks_data):
        title = task.get("title", "Unnamed Task")
        description = task.get("description", "")
        is_complete = task.get("is_complete", False)
        due_date = task.get("due_date", None)
        priority = task.get("priority", "medium")
        category = task.get("category", "Uncategorized")
        status = task.get("status", "not_started")
        lead_party = task.get("lead_party", "couple")

        insert_values.append(
            f"(:title{idx}, :description{idx}, :is_complete{idx}, :due_date{idx}, :priority{idx}, :category{idx}, :status{idx}, :lead_party{idx}, :wedding_id{idx})"
        )
        params.extend([
            (f"title{idx}", title),
            (f"description{idx}", description),
            (f"is_complete{idx}", is_complete),
            (f"due_date{idx}", due_date),
            (f"priority{idx}", priority),
            (f"category{idx}", category),
            (f"status{idx}", status),
            (f"lead_party{idx}", lead_party),
            (f"wedding_id{idx}", wedding_id),
        ])
    
    sql = f"""
    INSERT INTO tasks (title, description, is_complete, due_date, priority, category, status, lead_party, wedding_id)
    VALUES {", ".join(insert_values)};
    """
    param_dict = dict(params)
    with open("logs/bulk_create.sql", "a") as log_file:
        log_file.write(f"SQL for bulk_create_tasks: {sql}\n")
        log_file.write(f"Params: {param_dict}\n")

    result = await execute_supabase_sql(sql, param_dict)

    if result.get("status") == "success":
        return {"status": "success", "message": f"Successfully created {len(tasks_data)} tasks."}
    else:
        return {"status": "error", "message": f"Failed to create tasks: {result.get('error')}"}

async def populate_initial_budget(tool_context: ToolContext, wedding_id: str, budget_details: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Populates initial budget items in the 'budget_items' table.
    The LLM is responsible for generating the budget_details.
    """
    with open("logs/populate_budget.log", "a") as log_file:
        log_file.write(f"Populate initial budget called with wedding_id: {len(budget_details)} {wedding_id} and budget_details: {budget_details}\n")
    #return {"status" : "success", "message": f"This is a placeholder for populate_initial_budget. {budget_details}"}
    if not wedding_id or not budget_details:
        return {"status": "error", "message": "wedding_id and budget_details are required."}

    insert_values = []
    for budget in budget_details:
        item_name = budget.get("item_name", "Unnamed Item").replace("'", "''")
        amount = budget.get("amount", 0)
        category = budget.get("category", "Uncategorized").replace("'", "''")
        status = budget.get("status", "pending")
        contribution_by = budget.get("contribution_by", "couple").replace("'", "''")

        insert_values.append(f"('{item_name}', {amount}, '{status}', '{wedding_id}', '{contribution_by}', '{category}')")
    if not insert_values:
        return {"status": "success", "message": "No budget items to populate."}

    sql = f"""
    INSERT INTO budget_items (item_name, amount, status, wedding_id, contribution_by, category)
    VALUES {", ".join(insert_values)};
    """

    with open("logs/populate_budget.sql", "a") as log_file:
        log_file.write(f"SQL for populate_initial_budget: {sql}\n")
    result = await execute_supabase_sql(sql)

    if result.get("status") == "success":
        return {"status": "success", "message": "Successfully populated initial budget."}
    else:
        return {"status": "error", "message": f"Failed to populate initial budget: {result.get('error')}"}



# check if the wedding status is 'active' and if the wedding_id is valid
async def setup_agent_before_agent_callback(wedding_id: str) -> bool:
    """
    Callback to check if the wedding is active before running the agent.
    This is a placeholder for actual logic that would check the wedding status.
    """
    sql_query = """
        SELECT status FROM weddings WHERE wedding_id = :wedding_id;
    """
    params = {"wedding_id": wedding_id}
    result = await execute_supabase_sql(sql_query, params)
    if result.get("status") == "success" and result.get("data"):
        wedding_status = result["data"][0].get("status")
        return wedding_status == "active"
    else:
        return False  # Wedding not found or error occurred