import datetime
import subprocess
import tempfile
import os

from typing import Dict, Any, List, Optional
from uuid import UUID, uuid4
import logging # Import the custom JSON logger

# Import execute_supabase_sql from the shared helpers
from sanskara.helpers import execute_supabase_sql
from sanskara.db_queries import (
    create_budget_item_query,
    get_budget_items_by_wedding_id_query,
    get_budget_summary_query
)
from sanskara.db_queries import (
    get_total_budget_query,
    delete_budget_item_query,
    update_budget_item_query,
    get_budget_items_by_wedding_id_query as get_all_expenses_query
)



async def get_total_budget(wedding_id: str) -> Dict[str, Any]:
    """
    Retrieves the total allocated budget for a given wedding_id.
    """
    logging.info(f"wedding_id={wedding_id}")
    logging.debug(f"Attempting to get total budget for wedding {wedding_id}")
    sql = get_total_budget_query(wedding_id)
    result = await execute_supabase_sql(sql)
    if result.get("status") == "success" and result.get("data"):
        total_budget = result["data"]
        logging.info(f"Successfully retrieved total budget for wedding {wedding_id}: {total_budget}")
        return {"status": "success", "total_budget": total_budget}
    else:
        logging.error(f"Failed to retrieve total budget for wedding {wedding_id}. Error: {result.get('error')}", exc_info=True)
        return {"status": "error", "message": f"Failed to retrieve total budget: {result.get('error')}"}

async def get_budget_summary(wedding_id: str) -> Dict[str, Any]:
    """
    Retrieves a summary of expenses by category for a given wedding_id.
    """
    logging.info(f"wedding_id={wedding_id}")
    logging.debug(f"Attempting to get budget summary for wedding {wedding_id}")
    sql = get_budget_summary_query(wedding_id)
    result = await execute_supabase_sql(sql)
    if result.get("status") == "success":
        summary = result.get("data", [])
        logging.info(f"Successfully retrieved budget summary for wedding {wedding_id}: {summary}")
        return {"status": "success", "budget_summary": summary}
    else:
        logging.error(f"Failed to retrieve budget summary for wedding {wedding_id}. Error: {result.get('error')}", exc_info=True)
        return {"status": "error", "message": f"Failed to retrieve budget summary: {result.get('error')}"}


async def update_expense(expense_id: str, wedding_id: str, item_name: Optional[str] = None, category: Optional[str] = None, amount: Optional[float] = None, vendor_name: Optional[str] = None, status: Optional[str] = None, contribution_by: Optional[str] = None) -> Dict[str, Any]:
    """
    Updates an existing expense identified by expense_id for a specific wedding_id. Only provided fields should be updated.
    """
    logging.info(f"expense_id={expense_id}, wedding_id={wedding_id}")
    logging.debug(f"Attempting to update expense {expense_id} for wedding {wedding_id}")
    sql = update_budget_item_query(
        item_id=expense_id,
        item_name=item_name,
        category=category,
        amount=amount,
        vendor_name=vendor_name,
        status=status,
        contribution_by=contribution_by
    )
    result = await execute_supabase_sql(sql)
    if result.get("status") == "success":
        logging.info(f"Successfully updated expense: {expense_id}")
        return {"status": "success", "expense_id": expense_id}
    else:
        logging.error(f"Failed to update expense: {expense_id}. Error: {result.get('error')}", exc_info=True)
        return {"status": "error", "message": f"Failed to update expense: {result.get('error')}"}

async def delete_expense(expense_id: str, wedding_id: str) -> Dict[str, Any]:
    """
    Deletes an expense identified by expense_id for a specific wedding_id.
    """
    logging.info(f"expense_id={expense_id}, wedding_id={wedding_id}")
    logging.debug(f"Attempting to delete expense {expense_id} for wedding {wedding_id}")
    sql = delete_budget_item_query(expense_id, wedding_id)
    result = await execute_supabase_sql(sql)
    if result.get("status") == "success":
        logging.info(f"Successfully deleted expense: {expense_id}")
        return {"status": "success", "expense_id": expense_id}
    else:
        logging.error(f"Failed to delete expense: {expense_id}. Error: {result.get('error')}", exc_info=True)
        return {"status": "error", "message": f"Failed to delete expense: {result.get('error')}"}

async def get_all_expenses(wedding_id: str) -> Dict[str, Any]:
    """
    Retrieves a list of all expenses for a given wedding_id.
    """
    logging.info(f"wedding_id={wedding_id}")
    logging.debug(f"Attempting to get all expenses for wedding {wedding_id}")
    sql = get_all_expenses_query(wedding_id)
    result = await execute_supabase_sql(sql)
    if result.get("status") == "success":
        expenses = result.get("data", [])
        logging.info(f"Successfully retrieved {len(expenses)} expenses for wedding {wedding_id}")
        return {"status": "success", "expenses": expenses}
    else:
        logging.error(f"Failed to retrieve all expenses for wedding {wedding_id}. Error: {result.get('error')}", exc_info=True)
        return {"status": "error", "message": f"Failed to retrieve expenses: {result.get('error')}"}

async def add_expense(
    wedding_id: str,
    item_name: str,
    category: str,
    amount: float,
    vendor_name: Optional[str] = None,
    contribution_by: Optional[str] = None
) -> Dict[str, Any]:
    """
    Adds a new expense item for a specific wedding_id.
    """
    logging.info(f"wedding_id={wedding_id}, item_name={item_name}")
    logging.debug(f"Attempting to add expense '{item_name}' for wedding {wedding_id}")
    item_id = str(uuid4()) # Generate a new UUID for the item
    sql = create_budget_item_query(
        item_id=item_id,
        wedding_id=wedding_id,
        item_name=item_name,
        category=category,
        amount=amount,
        vendor_name=vendor_name,
        contribution_by=contribution_by
    )
    result = await execute_supabase_sql(sql)
    if result.get("status") == "success":
        logging.info(f"Successfully added expense: {item_name} with ID {item_id}")
        return {"status": "success", "item_id": item_id}
    else:
        logging.error(f"Failed to add expense: {item_name}. Error: {result.get('error')}", exc_info=True)
        return {"status": "error", "message": f"Failed to add expense: {result.get('error')}"}


async def upsert_budget_item(
    wedding_id: str,
    item_name: str,
    category: str,
    amount: float,
    vendor_name: Optional[str] = None,
    contribution_by: Optional[str] = None,
    status: Optional[str] = None # Allow updating status through upsert
) -> Dict[str, Any]:
    """
    Creates a new budget item or updates an existing one if a budget item with the same
    wedding_id, item_name, and category already exists.

    Args:
        wedding_id: The UUID of the wedding this item belongs to.
        item_name: The name of the budget item.
        category: The category of the budget item.
        amount: The estimated or actual amount.
        vendor_name: Optional. The name of the associated vendor.
        contribution_by: Optional. Who is contributing to this expense.
        status: Optional. The status of the budget item (e.g., 'Pending', 'Booked', 'Paid').

    Returns:
        A dictionary indicating success or failure.
    """
    logging.info(f"wedding_id={wedding_id}, item_name={item_name}, category={category}")
    logging.debug(f"Attempting to upsert budget item '{item_name}' (category: {category}) for wedding {wedding_id}")
    
    # First, try to find an existing budget item
    sql_select = """
        SELECT item_id FROM budget_items
        WHERE wedding_id = :wedding_id AND item_name = :item_name AND category = :category;
    """
    params_select = {
        "wedding_id": wedding_id,
        "item_name": item_name,
        "category": category
    }
    
    try:
        result_select = await execute_supabase_sql(sql_select, params_select)
        
        if result_select and result_select.get("status") == "success" and result_select.get("data"):
            # Item exists, update it
            existing_item_id = result_select["data"][0]["item_id"]
            logging.info(f"Budget item '{item_name}' (category: {category}) already exists for wedding {wedding_id}. Updating.")
            
            updates = {
                "item_name": item_name, # Include item_name and category in updates to ensure they are set if only amount changes
                "category": category,
                "amount": amount,
                "vendor_name": vendor_name,
                "contribution_by": contribution_by,
                "status": status
            }
            # Filter out None values from updates to avoid overwriting with None if not provided
            updates = {k: v for k, v in updates.items() if v is not None}

            return await update_expense(
                expense_id=existing_item_id,
                wedding_id=wedding_id, # wedding_id is needed by update_expense (though not used in query)
                **updates # Pass filtered updates directly
            )
        else:
            # Item does not exist, create a new one
            logging.info(f"Budget item '{item_name}' (category: {category}) does not exist for wedding {wedding_id}. Creating new.")
            return await add_expense(
                wedding_id=wedding_id,
                item_name=item_name,
                category=category,
                amount=amount,
                vendor_name=vendor_name,
                contribution_by=contribution_by
            )
            
    except Exception as e:
        logging.error(f"Error in upsert_budget_item for {item_name} (wedding {wedding_id}): {e}", exc_info=True)
        return {"status": "error", "message": str(e)}

async def code_execution_tool(code: str, language: str) -> Dict[str, Any]:
    """
    Executes arbitrary code in a specified language within a simulated environment.
    Supports Python execution by writing to a temporary file and running it.
    For other languages, it indicates that execution is not fully supported.
    Captures and returns stdout/stderr.
    """
    logging.info(f"language={language}")
    logging.info(f"Attempting to execute code in {language}...")
    if language.lower() == "python":
        try:
            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".py") as temp_file:
                temp_file.write(code)
                temp_file_path = temp_file.name
            
            process = subprocess.run(
                ["python", temp_file_path],
                capture_output=True,
                text=True,
                check=False
            )
            
            os.remove(temp_file_path) # Clean up the temporary file

            if process.returncode == 0:
                logging.info("Code executed successfully.")
                return {"status": "success", "stdout": process.stdout, "stderr": process.stderr}
            else:
                logging.error(f"Code execution failed with errors: {process.stderr}")
                return {"status": "error", "stdout": process.stdout, "stderr": process.stderr}
        except Exception as e:
            logging.error(f"An unexpected error occurred during Python code execution: {e}", exc_info=True)
            return {"status": "error", "message": f"An unexpected error occurred: {e}"}
    else:
        message = f"Code execution for language '{language}' is not fully supported in this simulated environment."
        logging.warning(message)
        return {"status": "error", "message": message, "stdout": "", "stderr": ""}

if __name__ == "__main__":
    import asyncio
    from uuid import uuid4

    async def run_tests():
        # # Use dummy UUIDs for testing
        wedding_id = "9ce1a9c6-9c47-47e7-97cc-e4e222d0d90c"
        # user_id = str(uuid4())
        
        # print("--- Running Tests for Budget and Expense Agent Tools ---")

        # # Test add_expense
        # print("\nTesting add_expense...")
        # expense_id_1 = str(uuid4())
        # result_add_1 = await add_expense(
        #     wedding_id=wedding_id,
        #     item_name="Wedding Cake",
        #     category="Food & Beverage",
        #     amount=500.0,
        #     vendor_name="Sweet Delights Bakery",
        #     contribution_by="Parents"
        # )
        # print(f"add_expense result 1: {result_add_1}")
        # if result_add_1["status"] == "success":
        #     expense_id_1 = result_add_1["item_id"]
        #     print(f"Successfully added expense with ID: {expense_id_1}")
        # else:
        #     print(f"Failed to add expense 1: {result_add_1['message']}")
        #     return # Stop if initial add fails

        # expense_id_2 = str(uuid4())
        # result_add_2 = await add_expense(
        #     wedding_id=wedding_id,
        #     item_name="Photography Package",
        #     category="Photography",
        #     amount=2500.0,
        #     vendor_name="Eternal Memories Photography",
        #     contribution_by="Self"
        # )
        # print(f"add_expense result 2: {result_add_2}")
        # if result_add_2["status"] == "success":
        #     expense_id_2 = result_add_2["item_id"]
        #     print(f"Successfully added expense with ID: {expense_id_2}")
        # else:
        #     print(f"Failed to add expense 2: {result_add_2['message']}")
        #     return # Stop if initial add fails

        # # Test get_all_expenses
        # print("\nTesting get_all_expenses...")
        # result_get_all = await get_all_expenses(wedding_id)
        # print(f"get_all_expenses result: {result_get_all}")
        # if result_get_all["status"] == "success":
        #     print(f"Retrieved {len(result_get_all['expenses'])} expenses.")
        # else:
        #     print(f"Failed to get all expenses: {result_get_all['message']}")

        # # Test get_budget
        # print("\nTesting get_budget...")
        # result_get_budget = await get_budget(wedding_id)
        # print(f"get_budget result: {result_get_budget}")
        # if result_get_budget["status"] == "success":
        #     print(f"Total budget for wedding {wedding_id}: {result_get_budget}")
        # else:
        #     print(f"Failed to get budget: {result_get_budget['message']}")

        # # Test update_expense
        # print(f"\nTesting update_expense for ID: {expense_id_1}...")
        # result_update = await update_expense(
        #     expense_id=expense_id_1,
        #     wedding_id=wedding_id,
        #     amount=550.0,
        #     item_name="Updated Wedding Cake"
        # )
        # print(f"update_expense result: {result_update}")
        # if result_update["status"] == "success":
        #     print(f"Successfully updated expense: {expense_id_1}")
        # else:
        #     print(f"Failed to update expense: {result_update['message']}")

        # # Test get_all_expenses again to confirm update
        # print("\nTesting get_all_expenses after update...")
        # result_get_all_after_update = await get_all_expenses(wedding_id)
        # print(f"get_all_expenses after update result: {result_get_all_after_update}")

        # # Test delete_expense
        # print(f"\nTesting delete_expense for ID: {expense_id_1}...")
        # result_delete = await delete_expense(expense_id=expense_id_1, wedding_id=wedding_id)
        # print(f"delete_expense result: {result_delete}")
        # if result_delete["status"] == "success":
        #     print(f"Successfully deleted expense: {expense_id_1}")
        # else:
        #     print(f"Failed to delete expense: {result_delete['message']}")

        # # Test get_all_expenses after delete
        # print("\nTesting get_all_expenses after delete...")
        # result_get_all_after_delete = await get_all_expenses(wedding_id)
        # print(f"get_all_expenses after delete result: {result_get_all_after_delete}")

        # # Test code_execution_tool (Python)
        # print("\nTesting code_execution_tool (Python)...")
        # python_code = "print('Hello, World from Python!'); import sys; print('Error output', file=sys.stderr)"
        # result_code_python = await code_execution_tool(code=python_code, language="python")
        # print(f"code_execution_tool (Python) result: {result_code_python}")
        # if result_code_python["status"] == "success":
        #     print("Python code executed successfully.")
        # else:
        #     print(f"Python code execution failed: {result_code_python.get('stderr', result_code_python.get('message'))}")

        # # Test code_execution_tool (Unsupported Language)
        # print("\nTesting code_execution_tool (Unsupported Language)...")
        # unsupported_code = "console.log('Hello, World from JS!');"
        # result_code_unsupported = await code_execution_tool(code=unsupported_code, language="javascript")
        # print(f"code_execution_tool (Unsupported Language) result: {result_code_unsupported}")
        # if result_code_unsupported["status"] == "error" and "not fully supported" in result_code_unsupported["message"]:
        #     print("Unsupported language test passed.")
        # else:
        #     print("Unsupported language test failed.")

        # print("\n--- All Budget and Expense Agent Tests Completed ---")

    asyncio.run(run_tests())