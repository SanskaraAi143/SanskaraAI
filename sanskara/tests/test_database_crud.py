import asyncio
import pytest
import uuid
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Optional
import logging # Import the custom JSON logger

# --- IMPORTANT: Replace this placeholder with your actual execute_supabase_sql function ---
# Example: from sanskara.shared_libraries.helpers import execute_supabase_sql
# If running from sanskara/tests, and helpers is in sanskara/sanskara/shared_libraries
#from sanskara.shared_libraries.helpers import execute_supabase_sql
from sanskara.helpers import execute_supabase_sql
# --- User Data for Testing (from your provided context) ---
TEST_USER_ID = "fca04215-2af3-4a4e-bcfa-c27a4f54474c"
TEST_SUPABASE_AUTH_UID = "4b73666f-3333-4838-a4ce-ce7eb1328543"
TEST_USER_EMAIL = "kpuneeth714@gmail.com"

# --- Test Case Implementations ---

@pytest.mark.asyncio
async def test_weddings_crud():
    logging.info("\n--- Running Weddings CRUD Test ---")
    wedding_id = str(uuid.uuid4())
    wedding_name = f"Test Wedding {datetime.now().strftime('%Y%m%d%H%M%S')}"
    initial_status = "onboarding_in_progress"
    updated_status = "active"
    updated_name = f"Updated Test Wedding {datetime.now().strftime('%Y%m%d%H%M%S')}"
    test_passed = True

    try:
        # 1. Insert Test
        logging.info(f"Attempting to insert wedding: {wedding_name}")
        insert_sql = """
            INSERT INTO weddings (wedding_id, wedding_name, status)
            VALUES (:wedding_id, :wedding_name, :status)
            RETURNING *;
        """
        insert_params = {
            "wedding_id": wedding_id,
            "wedding_name": wedding_name,
            "status": initial_status
        }
        insert_result = await execute_supabase_sql(insert_sql, insert_params)
        if insert_result.get("error") or not insert_result.get("data"):
            logging.error(f"Insert wedding failed: {insert_result.get('error', 'No data returned')}")
            test_passed = False
            return False # Exit early if insert fails
        inserted_wedding = insert_result["data"][0]
        if inserted_wedding.get("wedding_id") != wedding_id or inserted_wedding.get("wedding_name") != wedding_name:
            logging.error(f"Insert wedding verification failed. Expected ID {wedding_id}, got {inserted_wedding.get('wedding_id')}. Expected name {wedding_name}, got {inserted_wedding.get('wedding_name')}")
            test_passed = False
        else:
            logging.info(f"Successfully inserted wedding: {inserted_wedding}")

        # 2. Read Test
        if test_passed:
            logging.info(f"Attempting to read wedding with ID: {wedding_id}")
            read_sql = "SELECT * FROM weddings WHERE wedding_id = :wedding_id;"
            read_params = {"wedding_id": wedding_id}
            read_result = await execute_supabase_sql(read_sql, read_params)
            if read_result.get("error") or not read_result.get("data"):
                logging.error(f"Read wedding failed: {read_result.get('error', 'No data returned')}")
                test_passed = False
            else:
                read_wedding = read_result["data"][0]
                if read_wedding.get("wedding_name") != wedding_name:
                    logging.error(f"Read wedding verification failed. Expected name {wedding_name}, got {read_wedding.get('wedding_name')}")
                    test_passed = False
                else:
                    logging.info(f"Successfully read wedding: {read_wedding}")

        # 3. Update Test
        if test_passed:
            logging.info(f"Attempting to update wedding with ID: {wedding_id}")
            update_sql = """
                UPDATE weddings
                SET wedding_name = :updated_name, status = :updated_status
                WHERE wedding_id = :wedding_id
                RETURNING *;
            """
            update_params = {
                "wedding_id": wedding_id,
                "updated_name": updated_name,
                "updated_status": updated_status
            }
            update_result = await execute_supabase_sql(update_sql, update_params)
            if update_result.get("error") or not update_result.get("data"):
                logging.error(f"Update wedding failed: {update_result.get('error', 'No data returned')}")
                test_passed = False
            else:
                updated_wedding = update_result["data"][0]
                if updated_wedding.get("wedding_name") != updated_name or updated_wedding.get("status") != updated_status:
                    logging.error(f"Update wedding verification failed. Expected name {updated_name}, status {updated_status}. Got {updated_wedding.get('wedding_name')}, {updated_wedding.get('status')}")
                    test_passed = False
                else:
                    logging.info(f"Successfully updated wedding: {updated_wedding}")

    finally:
        # Cleanup: Delete the created wedding
        logging.info(f"Cleanup: Attempting to delete wedding {wedding_id}")
        delete_sql = "DELETE FROM weddings WHERE wedding_id = :wedding_id RETURNING wedding_id;"
        delete_params = {"wedding_id": wedding_id}
        delete_result = await execute_supabase_sql(delete_sql, delete_params)
        if delete_result.get("error") or not delete_result.get("data"):
            logging.error(f"Cleanup failed: Could not delete wedding {wedding_id}: {delete_result.get('error', 'No data returned')}")
            test_passed = False # Mark as failed if cleanup fails, as it affects future runs
        else:
            logging.info(f"Successfully deleted wedding {wedding_id} during cleanup.")
            # Verify deletion
            read_after_delete_sql = "SELECT * FROM weddings WHERE wedding_id = :wedding_id;"
            read_after_delete_params = {"wedding_id": "deleted_id"} # Use a dummy ID to simulate not found
            read_after_delete_result = await execute_supabase_sql(read_after_delete_sql, read_after_delete_params)
            if read_after_delete_result.get("data"):
                logging.error(f"Wedding {wedding_id} still found after deletion verification.")
                test_passed = False
            else:
                logging.info(f"Wedding {wedding_id} successfully verified as deleted.")

    if test_passed:
        logging.info("--- Weddings CRUD Test Passed ---")
    else:
        logging.error("--- Weddings CRUD Test FAILED ---")
    return test_passed

@pytest.mark.asyncio
async def test_wedding_members_crud():
    logging.info("\n--- Running Wedding Members CRUD Test ---")
    wedding_id = str(uuid.uuid4())
    member_role = "bride"
    test_passed = True

    try:
        # Setup: Insert a wedding first
        insert_wedding_sql = """
            INSERT INTO weddings (wedding_id, wedding_name, status)
            VALUES (:wedding_id, :wedding_name, :status)
            RETURNING wedding_id;
        """
        insert_wedding_params = {
            "wedding_id": wedding_id,
            "wedding_name": f"Member Test Wedding {datetime.now().strftime('%Y%m%d%H%M%S')}",
            "status": "active"
        }
        wedding_insert_result = await execute_supabase_sql(insert_wedding_sql, insert_wedding_params)
        if wedding_insert_result.get("error") or not wedding_insert_result.get("data"):
            logging.error(f"Setup failed: Could not insert wedding for wedding_members test: {wedding_insert_result.get('error', 'No data returned')}")
            test_passed = False
            return False # Exit early if setup fails
        logging.info(f"Setup: Inserted wedding {wedding_id} for wedding_members test.")

        # 1. Insert Test
        logging.info(f"Attempting to insert wedding member: User {TEST_USER_ID} to Wedding {wedding_id}")
        insert_sql = """
            INSERT INTO wedding_members (wedding_id, user_id, role)
            VALUES (:wedding_id, :user_id, :role)
            RETURNING *;
        """
        insert_params = {
            "wedding_id": wedding_id,
            "user_id": TEST_USER_ID,
            "role": member_role
        }
        insert_result = await execute_supabase_sql(insert_sql, insert_params)
        if insert_result.get("error") or not insert_result.get("data"):
            logging.error(f"Insert wedding member failed: {insert_result.get('error', 'No data returned')}")
            test_passed = False
        else:
            inserted_member = insert_result["data"][0]
            if inserted_member.get("wedding_id") != wedding_id or inserted_member.get("user_id") != TEST_USER_ID:
                logging.error(f"Insert wedding member verification failed. Expected wedding_id {wedding_id}, user_id {TEST_USER_ID}. Got {inserted_member.get('wedding_id')}, {inserted_member.get('user_id')}")
                test_passed = False
            else:
                logging.info(f"Successfully inserted wedding member: {inserted_member}")

        # 2. Read Test
        if test_passed:
            logging.info(f"Attempting to read wedding member: User {TEST_USER_ID} from Wedding {wedding_id}")
            read_sql = "SELECT * FROM wedding_members WHERE wedding_id = :wedding_id AND user_id = :user_id;"
            read_params = {
                "wedding_id": wedding_id,
                "user_id": TEST_USER_ID
            }
            read_result = await execute_supabase_sql(read_sql, read_params)
            if read_result.get("error") or not read_result.get("data"):
                logging.error(f"Read wedding member failed: {read_result.get('error', 'No data returned')}")
                test_passed = False
            else:
                read_member = read_result["data"][0]
                if read_member.get("role") != member_role:
                    logging.error(f"Read wedding member verification failed. Expected role {member_role}, got {read_member.get('role')}")
                    test_passed = False
                else:
                    logging.info(f"Successfully read wedding member: {read_member}")

        # 3. Negative Test (Duplicate Insert)
        if test_passed:
            logging.info("Attempting duplicate insert for wedding member (expected to fail)...")
            duplicate_insert_sql = """
                INSERT INTO wedding_members (wedding_id, user_id, role)
                VALUES (:wedding_id, :user_id, :role);
            """
            duplicate_insert_params = {
                "wedding_id": wedding_id,
                "user_id": TEST_USER_ID,
                "role": "groom" # Different role, but same PK (wedding_id, user_id)
            }
            duplicate_insert_result = await execute_supabase_sql(duplicate_insert_sql, duplicate_insert_params)
            if not duplicate_insert_result.get("error"):
                logging.error("Duplicate insert unexpectedly succeeded for wedding member.")
                test_passed = False
            else:
                logging.info(f"Duplicate insert failed as expected: {duplicate_insert_result['error']}")

    finally:
        # Cleanup: Delete the created wedding member
        logging.info(f"Cleanup: Attempting to delete wedding member (User {TEST_USER_ID} from Wedding {wedding_id})")
        delete_sql = "DELETE FROM wedding_members WHERE wedding_id = :wedding_id AND user_id = :user_id RETURNING wedding_id, user_id;"
        delete_params = {
            "wedding_id": wedding_id,
            "user_id": TEST_USER_ID
        }
        delete_result = await execute_supabase_sql(delete_sql, delete_params)
        if delete_result.get("error") or not delete_result.get("data"):
            logging.error(f"Cleanup failed: Could not delete wedding member: {delete_result.get('error', 'No data returned')}")
            test_passed = False
        else:
            logging.info(f"Successfully deleted wedding member during cleanup.")
            # Verify deletion
            read_after_delete_sql = "SELECT * FROM wedding_members WHERE wedding_id = :wedding_id AND user_id = :user_id;"
            read_after_delete_params = {"wedding_id": "deleted_id", "user_id": "deleted_id"} # Use dummy IDs to simulate not found
            read_after_delete_result = await execute_supabase_sql(read_after_delete_sql, read_after_delete_params)
            if read_after_delete_result.get("data"):
                logging.error(f"Wedding member (User {TEST_USER_ID} in Wedding {wedding_id}) still found after deletion verification.")
                test_passed = False
            else:
                logging.info(f"Wedding member (User {TEST_USER_ID} in Wedding {wedding_id}) successfully verified as deleted.")

        # Cleanup: Delete the created wedding
        cleanup_wedding_sql = "DELETE FROM weddings WHERE wedding_id = :wedding_id;"
        await execute_supabase_sql(cleanup_wedding_sql, {"wedding_id": wedding_id})
        logging.info(f"Cleanup: Deleted wedding {wedding_id}.")

    if test_passed:
        logging.info("--- Wedding Members CRUD Test Passed ---")
    else:
        logging.error("--- Wedding Members CRUD Test FAILED ---")
    return test_passed

@pytest.mark.asyncio
async def test_tasks_crud():
    logging.info("\n--- Running Tasks CRUD Test ---")
    wedding_id = str(uuid.uuid4())
    task_id = str(uuid.uuid4())
    task_title = f"Plan Ceremony {datetime.now().strftime('%Y%m%d%H%M%S')}"
    initial_status = "To Do"
    updated_status = "In Progress"
    updated_title = f"Finalize Ceremony Details {datetime.now().strftime('%Y%m%d%H%M%S')}"
    due_date = (date.today() + timedelta(days=30)).isoformat()
    lead_party = "bride_side"
    test_passed = True

    try:
        # Setup: Insert a wedding first
        insert_wedding_sql = """
            INSERT INTO weddings (wedding_id, wedding_name, status)
            VALUES (:wedding_id, :wedding_name, :status)
            RETURNING wedding_id;
        """
        insert_wedding_params = {
            "wedding_id": wedding_id,
            "wedding_name": f"Task Test Wedding {datetime.now().strftime('%Y%m%d%H%M%S')}",
            "status": "active"
        }
        wedding_insert_result = await execute_supabase_sql(insert_wedding_sql, insert_wedding_params)
        if wedding_insert_result.get("error") or not wedding_insert_result.get("data"):
            logging.error(f"Setup failed: Could not insert wedding for tasks test: {wedding_insert_result.get('error', 'No data returned')}")
            test_passed = False
            return False # Exit early if setup fails
        logging.info(f"Setup: Inserted wedding {wedding_id} for tasks test.")

        # 1. Insert Test
        logging.info(f"Attempting to insert task: {task_title} for Wedding {wedding_id}")
        insert_sql = """
            INSERT INTO tasks (task_id, wedding_id, title, description, due_date, status, priority, category, is_complete, lead_party)
            VALUES (:task_id, :wedding_id, :title, :description, :due_date, :status, :priority, :category, :is_complete, :lead_party)
            RETURNING *;
        """
        insert_params = {
            "task_id": task_id,
            "wedding_id": wedding_id,
            "title": task_title,
            "description": "Research and book ceremony venue.",
            "due_date": due_date,
            "status": initial_status,
            "priority": "medium",
            "category": "Ceremony",
            "is_complete": False,
            "lead_party": lead_party
        }
        insert_result = await execute_supabase_sql(insert_sql, insert_params)
        if insert_result.get("error") or not insert_result.get("data"):
            logging.error(f"Insert task failed: {insert_result.get('error', 'No data returned')}")
            test_passed = False
        else:
            inserted_task = insert_result["data"][0]
            if inserted_task.get("task_id") != task_id or inserted_task.get("wedding_id") != wedding_id:
                logging.error(f"Insert task verification failed. Expected ID {task_id}, wedding_id {wedding_id}. Got {inserted_task.get('task_id')}, {inserted_task.get('wedding_id')}")
                test_passed = False
            else:
                logging.info(f"Successfully inserted task: {inserted_task}")

        # 2. Read Test
        if test_passed:
            logging.info(f"Attempting to read task with ID: {task_id}")
            read_sql = "SELECT * FROM tasks WHERE task_id = :task_id;"
            read_params = {"task_id": task_id}
            read_result = await execute_supabase_sql(read_sql, read_params)
            if read_result.get("error") or not read_result.get("data"):
                logging.error(f"Read task failed: {read_result.get('error', 'No data returned')}")
                test_passed = False
            else:
                read_task = read_result["data"][0]
                if read_task.get("title") != task_title:
                    logging.error(f"Read task verification failed. Expected title {task_title}, got {read_task.get('title')}")
                    test_passed = False
                else:
                    logging.info(f"Successfully read task: {read_task}")

        # 3. Update Test
        if test_passed:
            logging.info(f"Attempting to update task with ID: {task_id}")
            update_sql = """
                UPDATE tasks
                SET title = :updated_title, status = :updated_status
                WHERE task_id = :task_id
                RETURNING *;
            """
            update_params = {
                "task_id": task_id,
                "updated_title": updated_title,
                "updated_status": updated_status
            }
            update_result = await execute_supabase_sql(update_sql, update_params)
            if update_result.get("error") or not update_result.get("data"):
                logging.error(f"Update task failed: {update_result.get('error', 'No data returned')}")
                test_passed = False
            else:
                updated_task = update_result["data"][0]
                if updated_task.get("title") != updated_title or updated_task.get("status") != updated_status:
                    logging.error(f"Update task verification failed. Expected title {updated_title}, status {updated_status}. Got {updated_task.get('title')}, {updated_task.get('status')}")
                    test_passed = False
                else:
                    logging.info(f"Successfully updated task: {updated_task}")

        # 4. Negative Test (Invalid Foreign Key)
        if test_passed:
            logging.info("Attempting to insert task with non-existent wedding_id (expected to fail)...")
            invalid_wedding_id = str(uuid.uuid4()) # Ensure this ID does not exist
            invalid_insert_sql = """
                INSERT INTO tasks (task_id, wedding_id, title, description, due_date, status, lead_party)
                VALUES (:task_id, :wedding_id, :title, :description, :due_date, :status, :lead_party);
            """
            invalid_insert_params = {
                "task_id": str(uuid.uuid4()),
                "wedding_id": invalid_wedding_id,
                "title": "Invalid Task",
                "description": "Should fail",
                "due_date": date.today().isoformat(),
                "status": "To Do",
                "lead_party": "couple"
            }
            invalid_insert_result = await execute_supabase_sql(invalid_insert_sql, invalid_insert_params)
            if not invalid_insert_result.get("error"):
                logging.error("Invalid foreign key insert unexpectedly succeeded for tasks.")
                test_passed = False
            else:
                logging.info(f"Invalid foreign key insert failed as expected: {invalid_insert_result['error']}")

    finally:
        # Cleanup: Delete the created task
        logging.info(f"Cleanup: Attempting to delete task {task_id}")
        delete_sql = "DELETE FROM tasks WHERE task_id = :task_id RETURNING task_id;"
        delete_params = {"task_id": task_id}
        delete_result = await execute_supabase_sql(delete_sql, delete_params)
        if delete_result.get("error") or not delete_result.get("data"):
            logging.error(f"Cleanup failed: Could not delete task {task_id}: {delete_result.get('error', 'No data returned')}")
            test_passed = False
        else:
            logging.info(f"Successfully deleted task {task_id} during cleanup.")
            # Verify deletion
            read_after_delete_sql = "SELECT * FROM tasks WHERE task_id = :task_id;"
            read_after_delete_params = {"task_id": "deleted_id"} # Use dummy ID to simulate not found
            read_after_delete_result = await execute_supabase_sql(read_after_delete_sql, read_after_delete_params)
            if read_after_delete_result.get("data"):
                logging.error(f"Task {task_id} still found after deletion verification.")
                test_passed = False
            else:
                logging.info(f"Task {task_id} successfully verified as deleted.")

        # Cleanup: Delete the created wedding
        cleanup_wedding_sql = "DELETE FROM weddings WHERE wedding_id = :wedding_id;"
        await execute_supabase_sql(cleanup_wedding_sql, {"wedding_id": wedding_id})
        logging.info(f"Cleanup: Deleted wedding {wedding_id}.")

    if test_passed:
        logging.info("--- Tasks CRUD Test Passed ---")
    else:
        logging.error("--- Tasks CRUD Test FAILED ---")
    return test_passed

# @pytest.mark.asyncio
# async def run_all_db_tests():
#     logging.info("Starting all database CRUD tests...")
#     results = {
#         "weddings_crud": await test_weddings_crud(),
#         "wedding_members_crud": await test_wedding_members_crud(),
#         "tasks_crud": await test_tasks_crud()
#     }
#     logging.info("\n--- All Database CRUD Tests Summary ---")
#     for test_name, passed in results.items():
#         logging.info(f"{test_name}: {'PASSED' if passed else 'FAILED'}")
#     logging.info("--- End of Summary ---")
#     return all(results.values())

