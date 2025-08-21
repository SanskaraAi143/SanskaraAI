from google.adk.tools import ToolContext
from typing import Dict, Any, List
from google.genai import types
from google.adk.agents.callback_context import CallbackContext
import json
import logging # Import the custom JSON logger
# Import execute_supabase_sql from the shared libraries
from sanskara.helpers import execute_supabase_sql,get_current_datetime

async def bulk_create_workflows(tool_context: ToolContext, wedding_id: str, workflows_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Bulk inserts workflow data into the 'workflows' table.
    The LLM is responsible for generating the workflows_data.
    """
    logging.info(f"tool_name='bulk_create_workflows', wedding_id={wedding_id}, num_workflows={len(workflows_data)}")
    logging.debug(f"Entering bulk_create_workflows tool with wedding_id: {wedding_id} and {len(workflows_data)} workflows.")
    if not wedding_id or not workflows_data:
        logging.error("wedding_id and workflows_data are required for bulk_create_workflows.")
        return {"status": "error", "message": "wedding_id and workflows_data are required."}

    insert_values = []
    for workflow in workflows_data:
        name = (workflow.get("name") or "Unnamed Workflow").replace("'", "''")
        status = (workflow.get("status") or "not_started").replace("'", "''")
        # Allow LLM to pass description/context; store into context_summary JSONB
        context = workflow.get("context_summary") or {}
        if not context and workflow.get("description"):
            context = {"description": workflow.get("description")}
        context_json = json.dumps(context).replace("'", "''") if context else None
        context_val = f"'{context_json}'::jsonb" if context_json else "NULL"
        insert_values.append(f"('{wedding_id}', '{name}', '{status}', {context_val})")

    sql = f"""
    INSERT INTO workflows (wedding_id, workflow_name, status, context_summary)
    VALUES {", ".join(insert_values)}
    """
    logging.debug(f"Executing SQL for bulk_create_workflows: {sql}")
    try:
        result = await execute_supabase_sql(sql)
        if result.get("status") == "success":
            logging.info(f"Successfully created {len(workflows_data)} workflows for wedding {wedding_id}.")
            return {"status": "success", "message": f"Successfully created {len(workflows_data)} workflows."}
        else:
            logging.error(f"Failed to create workflows for wedding {wedding_id}: {result.get('error')}")
            return {"status": "error", "message": f"Failed to create workflows: {result.get('error')}"}
    except Exception as e:
        logging.error(f"Unexpected error in bulk_create_workflows for wedding {wedding_id}: {e}", exc_info=True)
        return {"status": "error", "message": "An unexpected error occurred during workflow creation."}

async def bulk_create_tasks(tool_context: ToolContext, wedding_id: str, tasks_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Bulk inserts task data into the 'tasks' table.
    The LLM is responsible for generating the tasks_data, including due_date, lead_party, etc.
    """
    logging.info(f"tool_name='bulk_create_tasks', wedding_id={wedding_id}, num_tasks={len(tasks_data)}")
    logging.debug(f"Entering bulk_create_tasks tool with wedding_id: {wedding_id} and {len(tasks_data)} tasks.")
    if not wedding_id or not tasks_data:
        logging.error("wedding_id and tasks_data are required for bulk_create_tasks.")
        return {"status": "error", "message": "wedding_id and tasks_data are required."}

    insert_values = []
    for task in tasks_data:
        title = (task.get("title") or "Unnamed Task").replace("'", "''")
        description = (task.get("description") or "").replace("'", "''")
        is_complete = bool(task.get("is_complete", False))
        due_date = task.get("due_date")
        priority = (task.get("priority") or "medium").replace("'", "''")
        category = (task.get("category") or "Uncategorized").replace("'", "''")
        status = (task.get("status") or "No Status").replace("'", "''")
        lead_party = (task.get("lead_party") or "couple").replace("'", "''")

        # Handle None values and format properly
        due_date_str = f"'{due_date}'" if due_date else "NULL"

        insert_values.append(
            f"('{wedding_id}', '{title}', '{description}', {is_complete}, {due_date_str}, '{priority}', '{category}', '{status}', '{lead_party}')"
        )

    sql = f"""
    INSERT INTO tasks (wedding_id, title, description, is_complete, due_date, priority, category, status, lead_party)
    VALUES {", ".join(insert_values)}
    """
    logging.debug(f"Executing SQL for bulk_create_tasks: {sql}")
    try:
        result = await execute_supabase_sql(sql)

        if result.get("status") == "success":
            logging.info(f"Successfully created {len(tasks_data)} tasks for wedding {wedding_id}.")
            return {"status": "success", "message": f"Successfully created {len(tasks_data)} tasks."}
        else:
            logging.error(f"Failed to create tasks for wedding {wedding_id}: {result.get('error')}")
            return {"status": "error", "message": f"Failed to create tasks: {result.get('error')}"}
    except Exception as e:
        logging.error(f"Unexpected error in bulk_create_tasks for wedding {wedding_id}: {e}", exc_info=True)
        return {"status": "error", "message": "An unexpected error occurred during task creation."}

async def populate_initial_budget(tool_context: ToolContext, wedding_id: str, budget_details: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Populates initial budget items in the 'budget_items' table.
    The LLM is responsible for generating the budget_details.
    """
    logging.info(f"tool_name='populate_initial_budget', wedding_id={wedding_id}, num_budget_items={len(budget_details)}")
    logging.debug(f"Entering populate_initial_budget tool with wedding_id: {wedding_id} and {len(budget_details)} budget items.")
    if not wedding_id:
        logging.error("wedding_id is required for populate_initial_budget.")
        return {"status": "error", "message": "wedding_id is required."}
    if not budget_details:
        logging.info("No budget items to populate.")
        return {"status": "success", "message": "No budget items to populate."}

    insert_values = []
    for budget in budget_details:
        item_name = (budget.get("item_name") or "Unnamed Item").replace("'", "''")
        amount = float(budget.get("amount", 0))
        category = (budget.get("category") or "Uncategorized").replace("'", "''")
        status = (budget.get("status") or "Pending").replace("'", "''")
        contribution_by_raw = (budget.get("contribution_by") or "couple").lower()
        # Map 'couple' -> 'shared' to align with schema convention
        contribution_by = 'shared' if contribution_by_raw == 'couple' else contribution_by_raw
        contribution_by = contribution_by.replace("'", "''")

        insert_values.append(f"('{wedding_id}', '{item_name}', '{category}', {amount}, NULL, '{status}', '{contribution_by}')")

    if not insert_values:
        logging.info("No budget items to populate.")
        return {"status": "success", "message": "No budget items to populate."}

    sql = f"""
    INSERT INTO budget_items (wedding_id, item_name, category, amount, vendor_name, status, contribution_by)
    VALUES {", ".join(insert_values)}
    """
    logging.debug(f"Executing SQL for populate_initial_budget: {sql}")
    try:
        result = await execute_supabase_sql(sql)

        if result.get("status") == "success":
            logging.info(f"Successfully populated {len(budget_details)} budget items for wedding {wedding_id}.")
            return {"status": "success", "message": "Successfully populated initial budget."}
        else:
            logging.error(f"Failed to populate initial budget for wedding {wedding_id}: {result.get('error')}")
            return {"status": "error", "message": f"Failed to populate initial budget: {result.get('error')}"}
    except Exception as e:
        logging.error(f"Unexpected error in populate_initial_budget for wedding {wedding_id}: {e}", exc_info=True)
        return {"status": "error", "message": "An unexpected error occurred during budget population."}


# check if the wedding status is 'active' and if the wedding_id is valid
async def setup_agent_before_agent_callback(callback_context:CallbackContext) -> bool:
    """
    Callback to check if the wedding is active before running the agent.
    This is a placeholder for actual logic that would check the wedding status.
    """
    wedding_id = callback_context.state.get("wedding_id")
    logging.info(f"tool_name='setup_agent_before_agent_callback', wedding_id={wedding_id}")
    logging.debug(f"Entering setup_agent_before_agent_callback for wedding_id: {wedding_id}.")
    sql_query = """
        SELECT status FROM weddings WHERE wedding_id = :wedding_id;
    """
    params = {"wedding_id": wedding_id}
    logging.debug(f"Executing SQL to check wedding status: {sql_query} with params: {params}")
    try:
        result = await execute_supabase_sql(sql_query, params)
        if result.get("status") == "success" and result.get("data"):
            wedding_status = result["data"][0].get("status")
            is_active = wedding_status == "active"
            logging.info(f"Wedding {wedding_id} status is '{wedding_status}'. Is active: {is_active}")
            return is_active
        else:
            logging.warning(f"Wedding {wedding_id} not found or error occurred during status check. Result: {result}")
            return False  # Wedding not found or error occurred
    except Exception as e:
        logging.error(f"Unexpected error in setup_agent_before_agent_callback for wedding {wedding_id}: {e}", exc_info=True)
        return False
        
if __name__ == "__main__":
    # This is just a placeholder to avoid errors when importing this module
    # in other parts of the application.
    # test the workflows function 
    workflows_data = [
        {
            "name": "Test Workflow 1",
            "description": "This is a test workflow"
        },
        {
            "name": "Test Workflow 2",
            "description": "This is another test workflow"
        }
    ]
    wedding_id = "test_wedding_id"
    # Call the function to test it
    async def test_bulk_create_workflows():
        result = await bulk_create_workflows(None, wedding_id, workflows_data)
        print(result)
    import asyncio
    asyncio.run(test_bulk_create_workflows())
    #PYTHONPATH=/home/puneeth/programmes/Sanskara_AI/SanskaraAI/sanskara python sanskara/sub_agents/setup_agent/tools.py