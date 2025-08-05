from google.adk.tools import ToolContext
from typing import Dict, Any, List
from google.genai import types
from google.adk.agents.callback_context import CallbackContext
import json
from logger import json_logger as logger # Import the custom JSON logger
# Import execute_supabase_sql from the shared libraries
from sanskara.helpers import execute_supabase_sql,get_current_datetime

async def bulk_create_workflows(tool_context: ToolContext, wedding_id: str, workflows_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Bulk inserts workflow data into the 'workflows' table.
    The LLM is responsible for generating the workflows_data.
    """
    with logger.contextualize(tool_name="bulk_create_workflows", wedding_id=wedding_id, num_workflows=len(workflows_data)):
        logger.debug(f"Entering bulk_create_workflows tool with wedding_id: {wedding_id} and {len(workflows_data)} workflows.")
        if not wedding_id or not workflows_data:
            logger.error("wedding_id and workflows_data are required for bulk_create_workflows.")
            return {"status": "error", "message": "wedding_id and workflows_data are required."}

        insert_values = []
        for workflow in workflows_data:
            workflow_name = workflow.get("name", "Unnamed Workflow").replace("'", "''")
            workflow_status = workflow.get("description", "not_started")
            insert_values.append(f"('{workflow_name}', '{workflow_status}', '{wedding_id}')")

        sql = f"""
        INSERT INTO workflows (workflow_name, status, wedding_id)
        VALUES {", ".join(insert_values)};
        """
        logger.debug(f"Executing SQL for bulk_create_workflows: {sql}")
        try:
            result = await execute_supabase_sql(sql)
            if result.get("status") == "success":
                logger.info(f"Successfully created {len(workflows_data)} workflows for wedding {wedding_id}.")
                return {"status": "success", "message": f"Successfully created {len(workflows_data)} workflows."}
            else:
                logger.error(f"Failed to create workflows for wedding {wedding_id}: {result.get('error')}")
                return {"status": "error", "message": f"Failed to create workflows: {result.get('error')}"}
        except Exception as e:
            logger.error(f"Unexpected error in bulk_create_workflows for wedding {wedding_id}: {e}", exc_info=True)
            return {"status": "error", "message": "An unexpected error occurred during workflow creation."}

async def bulk_create_tasks(tool_context: ToolContext, wedding_id: str, tasks_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Bulk inserts task data into the 'tasks' table.
    The LLM is responsible for generating the tasks_data, including due_date, lead_party, etc.
    """
    with logger.contextualize(tool_name="bulk_create_tasks", wedding_id=wedding_id, num_tasks=len(tasks_data)):
        logger.debug(f"Entering bulk_create_tasks tool with wedding_id: {wedding_id} and {len(tasks_data)} tasks.")
        if not wedding_id or not tasks_data:
            logger.error("wedding_id and tasks_data are required for bulk_create_tasks.")
            return {"status": "error", "message": "wedding_id and tasks_data are required."}

        insert_values = []
        for task in tasks_data:
            title = task.get("title", "Unnamed Task").replace("'", "''")
            description = task.get("description", "").replace("'", "''")
            is_complete = task.get("is_complete", False)
            due_date = task.get("due_date", None)
            priority = task.get("priority", "medium")
            category = task.get("category", "Uncategorized").replace("'", "''")
            status = task.get("status", "not_started")
            lead_party = task.get("lead_party", "couple").replace("'", "''")

            # Handle None values and format properly
            due_date_str = f"'{due_date}'" if due_date else "NULL"
            
            insert_values.append(
                f"('{title}', '{description}', {is_complete}, {due_date_str}, '{priority}', '{category}', '{status}', '{lead_party}', '{wedding_id}')"
            )
        
        sql = f"""
        INSERT INTO tasks (title, description, is_complete, due_date, priority, category, status, lead_party, wedding_id)
        VALUES {", ".join(insert_values)};
        """
        logger.debug(f"Executing SQL for bulk_create_tasks: {sql}")
        try:
            result = await execute_supabase_sql(sql)

            if result.get("status") == "success":
                logger.info(f"Successfully created {len(tasks_data)} tasks for wedding {wedding_id}.")
                return {"status": "success", "message": f"Successfully created {len(tasks_data)} tasks."}
            else:
                logger.error(f"Failed to create tasks for wedding {wedding_id}: {result.get('error')}")
                return {"status": "error", "message": f"Failed to create tasks: {result.get('error')}"}
        except Exception as e:
            logger.error(f"Unexpected error in bulk_create_tasks for wedding {wedding_id}: {e}", exc_info=True)
            return {"status": "error", "message": "An unexpected error occurred during task creation."}

async def populate_initial_budget(tool_context: ToolContext, wedding_id: str, budget_details: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Populates initial budget items in the 'budget_items' table.
    The LLM is responsible for generating the budget_details.
    """
    with logger.contextualize(tool_name="populate_initial_budget", wedding_id=wedding_id, num_budget_items=len(budget_details)):
        logger.debug(f"Entering populate_initial_budget tool with wedding_id: {wedding_id} and {len(budget_details)} budget items.")
        if not wedding_id:
            logger.error("wedding_id is required for populate_initial_budget.")
            return {"status": "error", "message": "wedding_id is required."}
        if not budget_details:
            logger.info("No budget items to populate.")
            return {"status": "success", "message": "No budget items to populate."}

        insert_values = []
        for budget in budget_details:
            item_name = budget.get("item_name", "Unnamed Item").replace("'", "''")
            amount = budget.get("amount", 0)
            category = budget.get("category", "Uncategorized").replace("'", "''")
            status = budget.get("status", "pending")
            contribution_by = budget.get("contribution_by", "couple").replace("'", "''")

            insert_values.append(f"('{item_name}', {amount}, '{status}', '{wedding_id}', '{contribution_by}', '{category}')")

        if not insert_values:
            logger.info("No budget items to populate.")
            return {"status": "success", "message": "No budget items to populate."}

        sql = f"""
        INSERT INTO budget_items (item_name, amount, status, wedding_id, contribution_by, category)
        VALUES {", ".join(insert_values)};
        """
        logger.debug(f"Executing SQL for populate_initial_budget: {sql}")
        try:
            result = await execute_supabase_sql(sql)

            if result.get("status") == "success":
                logger.info(f"Successfully populated {len(budget_details)} budget items for wedding {wedding_id}.")
                return {"status": "success", "message": "Successfully populated initial budget."}
            else:
                logger.error(f"Failed to populate initial budget for wedding {wedding_id}: {result.get('error')}")
                return {"status": "error", "message": f"Failed to populate initial budget: {result.get('error')}"}
        except Exception as e:
            logger.error(f"Unexpected error in populate_initial_budget for wedding {wedding_id}: {e}", exc_info=True)
            return {"status": "error", "message": "An unexpected error occurred during budget population."}


# check if the wedding status is 'active' and if the wedding_id is valid
async def setup_agent_before_agent_callback(callback_context:CallbackContext) -> bool:
    """
    Callback to check if the wedding is active before running the agent.
    This is a placeholder for actual logic that would check the wedding status.
    """
    wedding_id = callback_context.state.get("wedding_id")
    with logger.contextualize(tool_name="setup_agent_before_agent_callback", wedding_id=wedding_id):
        logger.debug(f"Entering setup_agent_before_agent_callback for wedding_id: {wedding_id}.")
        sql_query = """
            SELECT status FROM weddings WHERE wedding_id = :wedding_id;
        """
        params = {"wedding_id": wedding_id}
        logger.debug(f"Executing SQL to check wedding status: {sql_query} with params: {params}")
        try:
            result = await execute_supabase_sql(sql_query, params)
            if result.get("status") == "success" and result.get("data"):
                wedding_status = result["data"][0].get("status")
                is_active = wedding_status == "active"
                logger.info(f"Wedding {wedding_id} status is '{wedding_status}'. Is active: {is_active}")
                return is_active
            else:
                logger.warning(f"Wedding {wedding_id} not found or error occurred during status check. Result: {result}")
                return False  # Wedding not found or error occurred
        except Exception as e:
            logger.error(f"Unexpected error in setup_agent_before_agent_callback for wedding {wedding_id}: {e}", exc_info=True)
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