from typing import Dict, Any, List, Optional
import json
def get_wedding_by_expected_partner_email_query() -> str:
    """
    Returns a parameterized SQL query to find a wedding by the expected partner's email.
    This query is now safe from SQL injection.
    """
    return """
        SELECT 
            wedding_id, 
            wedding_name,
            wedding_date,
            wedding_location,
            wedding_tradition,
            wedding_style,
            details
        FROM weddings
        WHERE details->>'other_partner_email_expected' = :email
        LIMIT 1;
    """

def get_user_and_wedding_info_by_email_query() -> str:
    """
    Returns a parameterized SQL query to get user and wedding info by email.
    This query is now safe from SQL injection.
    """
    return """
        SELECT u.user_id, wm.wedding_id, wm.role, w.details AS wedding_details
        FROM users u
        LEFT JOIN wedding_members wm ON u.user_id = wm.user_id
        LEFT JOIN weddings w ON wm.wedding_id = w.wedding_id
        WHERE u.email = :email;
    """

def create_wedding_query() -> str:
    """
    Returns a parameterized SQL query to create a new wedding.
    This query is now safe from SQL injection.
    """
    return """
        INSERT INTO weddings (wedding_name, wedding_date, wedding_location, wedding_tradition, wedding_style, status, details)
        VALUES (:wedding_name, :wedding_date, :wedding_location, :wedding_tradition, :wedding_style, 'onboarding_in_progress', :details::jsonb)
        RETURNING wedding_id;
    """

def update_wedding_details_jsonb_query() -> str:
    """
    Returns a parameterized SQL query to update the details of a wedding.
    This query is now safe from SQL injection.
    """
    return """
        UPDATE weddings
        SET details = :details::jsonb,
            updated_at = NOW()
        WHERE wedding_id = :wedding_id
        RETURNING wedding_id;
    """

# This function is insecure due to dynamic path construction and has been removed.
# Its functionality should be replaced by fetching the JSONB, modifying it in Python,
# and writing it back using the updated `update_wedding_details_jsonb_query`.
# def update_wedding_details_jsonb_field_query(...)

def update_wedding_fields_query(update_keys: List[str]) -> str:
    """
    Returns a parameterized SQL query to update specific fields of a wedding.
    The list of keys to update must be validated by the caller.
    This query is now safe from SQL injection.
    """
    # Note: Column names are not typically parameterized in SQL. The caller
    # must ensure that the keys in `update_keys` are valid and sanitized
    # column names to prevent SQL injection. In this application, the keys
    # are derived from a Pydantic model, which provides a layer of safety.
    set_clauses = [f"{key} = :{key}" for key in update_keys]
    updates_str = ", ".join(set_clauses)
    return f"""
        UPDATE weddings
        SET {updates_str},
            updated_at = NOW()
        WHERE wedding_id = :wedding_id;
    """

def add_wedding_member_query() -> str:
    """
    Returns a parameterized SQL query to add a member to a wedding.
    This query is now safe from SQL injection.
    """
    return """
        INSERT INTO wedding_members (wedding_id, user_id, role)
        VALUES (:wedding_id, :user_id, :role)
        ON CONFLICT (wedding_id, user_id) DO UPDATE SET role = EXCLUDED.role
        RETURNING user_id;
    """


def update_wedding_status_query() -> str:
    """
    Returns a parameterized SQL query to update the status of a wedding.
    This query is now safe from SQL injection.
    """
    return """
        UPDATE weddings
        SET status = :status,
            updated_at = NOW()
        WHERE wedding_id = :wedding_id;
    """

def get_wedding_details_query() -> str:
    """
    Returns a parameterized SQL query to get the details of a wedding.
    This query is now safe from SQL injection.
    """
    return "SELECT * FROM weddings WHERE wedding_id = :wedding_id"

# Workflow Queries
def create_workflow_query() -> str:
    """
    Returns a parameterized SQL query to create or update a workflow.
    This query is now safe from SQL injection.
    """
    return """
        INSERT INTO workflows (wedding_id, workflow_name, status, context_summary)
        VALUES (:wedding_id, :workflow_name, :status, :context_summary::jsonb)
        ON CONFLICT (wedding_id, workflow_name) DO UPDATE SET
            status = EXCLUDED.status,
            context_summary = EXCLUDED.context_summary,
            updated_at = NOW()
        RETURNING workflow_id;
    """

def get_workflow_by_name_query() -> str:
    """
    Returns a parameterized SQL query to get a workflow by its name.
    This query is now safe from SQL injection.
    """
    return """
        SELECT workflow_id, status, context_summary
        FROM workflows
        WHERE wedding_id = :wedding_id AND workflow_name = :workflow_name
        LIMIT 1;
    """

def update_workflow_status_query() -> str:
    """
    Returns a parameterized SQL query to update the status of a workflow.
    This query is now safe from SQL injection.
    """
    return """
        UPDATE workflows
        SET status = :status,
            context_summary = :context_summary::jsonb,
            updated_at = NOW()
        WHERE workflow_id = :workflow_id;
    """

def get_workflows_by_wedding_id_query() -> str:
    """
    Returns a parameterized SQL query to get all workflows for a wedding.
    This query is now safe from SQL injection.
    """
    return """
        SELECT workflow_id, workflow_name, status, context_summary
        FROM workflows
        WHERE wedding_id = :wedding_id;
    """

# Task Feedback Queries
def create_task_feedback_query() -> str:
    """
    Returns a parameterized SQL query to create task feedback.
    This query is now safe from SQL injection.
    """
    return """
        INSERT INTO task_feedback (task_id, user_id, feedback_type, content)
        VALUES (:task_id, :user_id, :feedback_type, :content)
        RETURNING feedback_id;
    """

def get_task_feedback_query() -> str:
    """
    Returns a parameterized SQL query to get task feedback.
    This query is now safe from SQL injection.
    """
    return """
        SELECT feedback_id, user_id, feedback_type, content, created_at
        FROM task_feedback
        WHERE task_id = :task_id;
    """

# Task Approvals Queries
def create_task_approval_query() -> str:
    """
    Returns a parameterized SQL query to create a task approval.
    This query is now safe from SQL injection.
    """
    return """
        INSERT INTO task_approvals (task_id, approving_party, status, approved_by_user_id)
        VALUES (:task_id, :approving_party, :status, :approved_by_user_id)
        RETURNING approval_id;
    """

def get_task_approvals_query() -> str:
    """
    Returns a parameterized SQL query to get task approvals.
    This query is now safe from SQL injection.
    """
    return """
        SELECT approval_id, approving_party, status, approved_by_user_id, created_at
        FROM task_approvals
        WHERE task_id = :task_id;
    """
    
def create_task_query() -> str:
    """
    Returns a parameterized SQL query to create or update a task.
    This query is now safe from SQL injection.
    """
    return """
        INSERT INTO tasks (wedding_id, title, description, is_complete, due_date, priority, category, status, lead_party)
        VALUES (:wedding_id, :title, :description, :is_complete, :due_date, :priority, :category, :status, :lead_party)
        ON CONFLICT (wedding_id, title) DO UPDATE SET
            description = EXCLUDED.description,
            is_complete = EXCLUDED.is_complete,
            due_date = EXCLUDED.due_date,
            priority = EXCLUDED.priority,
            category = EXCLUDED.category,
            status = EXCLUDED.status,
            lead_party = EXCLUDED.lead_party,
            updated_at = NOW()
        RETURNING task_id;
    """

def get_tasks_by_wedding_id_query(filter_keys: Optional[List[str]] = None) -> str:
    """
    Returns a parameterized SQL query to get tasks for a wedding, with optional filters.
    The list of filter keys must be validated by the caller.
    This query is now safe from SQL injection.
    """
    where_clauses = ["wedding_id = :wedding_id"]
    if filter_keys:
        for key in filter_keys:
            where_clauses.append(f"{key} = :{key}")

    where_clause_str = " AND ".join(where_clauses)

    return f"""
        SELECT task_id, title, description, is_complete, due_date, priority, category, status, lead_party
        FROM tasks
        WHERE {where_clause_str};
    """

def update_task_status_query() -> str:
    """
    Returns a parameterized SQL query to update the status of a task.
    This query is now safe from SQL injection.
    """
    return """
        UPDATE tasks
        SET status = :new_status,
            updated_at = NOW()
        WHERE task_id = :task_id;
    """

def get_task_details_query() -> str:
    """
    Returns a parameterized SQL query to get the details of a task.
    This query is now safe from SQL injection.
    """
    return """
        SELECT task_id, wedding_id, title, description, is_complete, due_date, priority, category, status, lead_party
        FROM tasks
        WHERE task_id = :task_id;
    """

def create_budget_item_query(
    wedding_id: str,
    item_name: str,
    category: str,
    amount: float,
    vendor_name: Optional[str] = None,
    status: str = 'Pending',
    contribution_by: Optional[str] = None,
    item_id: Optional[str] = None
) -> str:
    # If item_id is not provided, the database should generate it (assuming UUID default)
    # If provided, include it in the insert statement
    item_id_clause = f"item_id, " if item_id else ""
    item_id_value = f"'{item_id}', " if item_id else ""

    return f"""
        INSERT INTO budget_items ({item_id_clause}wedding_id, item_name, category, amount, vendor_name, status, contribution_by)
        VALUES (
            {item_id_value}'{wedding_id}',
            '{item_name}',
            '{category}',
            {amount},
            {f"'{vendor_name}'" if vendor_name else 'NULL'},
            '{status}',
            {f"'{contribution_by}'" if contribution_by else 'NULL'}
        )
        ON CONFLICT (wedding_id, item_name, category) DO UPDATE SET
            amount = EXCLUDED.amount,
            vendor_name = EXCLUDED.vendor_name,
            status = EXCLUDED.status,
            contribution_by = EXCLUDED.contribution_by,
            updated_at = NOW()
        RETURNING item_id;
    """

def get_budget_items_by_wedding_id_query(wedding_id: str, filters: Dict[str, Any] = None) -> str:
    filter_clauses = [f"{k} = '{v}'" for k, v in filters.items()] if filters else []
    where_clause = f"AND {' AND '.join(filter_clauses)}" if filter_clauses else ""
    return f"""
        SELECT item_id, item_name, category, amount, vendor_name, status, contribution_by
        FROM budget_items
        WHERE wedding_id = '{wedding_id}' {where_clause};
    """

def update_budget_item_query(
    item_id: str,
    item_name: str = None,
    category: str = None,
    amount: float = None,
    vendor_name: str = None,
    status: str = None,
    contribution_by: str = None
) -> str:
    updates = []
    if item_name:
        updates.append(f"item_name = '{item_name}'")
    if category:
        updates.append(f"category = '{category}'")
    if amount:
        updates.append(f"amount = {amount}")
    if vendor_name:
        updates.append(f"vendor_name = '{vendor_name}'")
    if status:
        updates.append(f"status = '{status}'")
    if contribution_by:
        updates.append(f"contribution_by = '{contribution_by}'")

    updates_str = ", ".join(updates)

    return f"""
        UPDATE budget_items
        SET {updates_str},
            updated_at = NOW()
        WHERE item_id = '{item_id}';
    """

def get_budget_summary_query(wedding_id: str) -> str:
    """
    Queries and aggregates the budget_items table to provide a summary by category,
    including spent and a placeholder for budgeted.
    """
    return f"""
        SELECT
            category,
            SUM(amount) AS spent,
            0.0 AS budgeted -- Placeholder, assuming budgeted amount is not stored in budget_items table
        FROM budget_items
        WHERE wedding_id = '{wedding_id}'
        GROUP BY category;
    """

def create_mood_board_query(
    wedding_id: str,
    name: str = 'Wedding Mood Board',
    description: str = None,
    visibility: str = 'shared',
    owner_party: str = None
) -> str:
    return f"""
        INSERT INTO mood_boards (wedding_id, name, description, visibility, owner_party)
        VALUES (
            '{wedding_id}',
            '{name}',
            {f"'{description}'" if description else 'NULL'},
            '{visibility}',
            {f"'{owner_party}'" if owner_party else 'NULL'}
        )
        RETURNING mood_board_id;
    """

def get_mood_boards_by_wedding_id_query(wedding_id: str, filters: Dict[str, Any] = None) -> str:
    filter_clauses = [f"{k} = '{v}'" for k, v in filters.items()] if filters else []
    where_clause = f"AND {' AND '.join(filter_clauses)}" if filter_clauses else ""
    return f"""
        SELECT mood_board_id, name, description, visibility, owner_party
        FROM mood_boards
        WHERE wedding_id = '{wedding_id}' {where_clause};
    """

def create_mood_board_item_query(
    mood_board_id: str,
    image_url: str,
    note: str = None,
    category: str = 'Decorations'
) -> str:
    return f"""
        INSERT INTO mood_board_items (mood_board_id, image_url, note, category)
        VALUES (
            '{mood_board_id}',
            '{image_url}',
            {f"'{note}'" if note else 'NULL'},
            '{category}'
        )
        RETURNING item_id;
    """

def get_mood_board_items_query(mood_board_id: str) -> str:
    return f"""
        SELECT item_id, image_url, note, category
        FROM mood_board_items
        WHERE mood_board_id = '{mood_board_id}';
    """

def create_guest_query(
    wedding_id: str,
    guest_name: str,
    contact_info: str,
    relation: str = None,
    side: str = None,
    status: str = 'Pending',
    dietary_requirements: str = None
) -> str:
    return f"""
        INSERT INTO guest_list (wedding_id, guest_name, contact_info, relation, side, status, dietary_requirements)
        VALUES (
            '{wedding_id}',
            '{guest_name}',
            '{contact_info}',
            {f"'{relation}'" if relation else 'NULL'},
            {f"'{side}'" if side else 'NULL'},
            '{status}',
            {f"'{dietary_requirements}'" if dietary_requirements else 'NULL'}
        )
        RETURNING guest_id;
    """

def get_guest_list_by_wedding_id_query(wedding_id: str, filters: Dict[str, Any] = None) -> str:
    filter_clauses = [f"{k} = '{v}'" for k, v in filters.items()] if filters else []
    where_clause = f"AND {' AND '.join(filter_clauses)}" if filter_clauses else ""
    return f"""
        SELECT guest_id, guest_name, contact_info, relation, side, status, dietary_requirements
        FROM guest_list
        WHERE wedding_id = '{wedding_id}' {where_clause};
    """

def update_guest_status_query(guest_id: str, status: str) -> str:
    return f"""
        UPDATE guest_list
        SET status = '{status}',
            updated_at = NOW()
        WHERE guest_id = '{guest_id}';
    """

def create_timeline_event_query(
    wedding_id: str,
    event_name: str,
    event_date_time: str,
    location: str = None,
    description: str = None,
    visibility: str = 'shared',
    relevant_party: str = None
) -> str:
    return f"""
        INSERT INTO timeline_events (wedding_id, event_name, event_date_time, location, description, visibility, relevant_party)
        VALUES (
            '{wedding_id}',
            '{event_name}',
            '{event_date_time}',
            {f"'{location}'" if location else 'NULL'},
            {f"'{description}'" if description else 'NULL'},
            '{visibility}',
            {f"'{relevant_party}'" if relevant_party else 'NULL'}
        )
        RETURNING event_id;
    """

def get_timeline_events_by_wedding_id_query(wedding_id: str, filters: Dict[str, Any] = None) -> str:
    filter_clauses = [f"{k} = '{v}'" for k, v in filters.items()] if filters else []
    where_clause = f"AND {' AND '.join(filter_clauses)}" if filter_clauses else ""
    return f"""
        SELECT event_id, event_name, event_date_time, location, description, visibility, relevant_party
        FROM timeline_events
        WHERE wedding_id = '{wedding_id}' {where_clause}
        ORDER BY event_date_time;
    """

def create_chat_session_query(
    wedding_id: str,
    summary: Dict[str, Any] = None
) -> str:
    return f"""
        INSERT INTO chat_sessions (wedding_id, summary)
        VALUES (
            '{wedding_id}',
            {f"'{summary}'::jsonb" if summary else 'NULL'}
        )
        RETURNING session_id;
    """

def get_chat_sessions_by_wedding_id_query(wedding_id: str) -> str:
    return f"""
        SELECT session_id, summary, created_at, last_updated_at
        FROM chat_sessions
        WHERE wedding_id = '{wedding_id}'
        ORDER BY last_updated_at DESC;
    """

def update_chat_session_summary_query(session_id: str, summary: Dict[str, Any]) -> str:
    return f"""
        UPDATE chat_sessions
        SET summary = '{json.dumps(summary)}'::jsonb,
            last_updated_at = NOW()
        WHERE session_id = '{session_id}';
    """

def update_chat_session_adk_session_id_query(session_id: str, adk_session_id: str) -> str:
    return f"""
        UPDATE chat_sessions
        SET adk_session_id = '{adk_session_id}', last_updated_at = NOW()
        WHERE session_id = '{session_id}';
    """

def update_chat_session_final_summary_query(session_id: str, final_summary: str) -> str:
    return f"""
        UPDATE chat_sessions
        SET final_summary = $$ {final_summary} $$,
            last_updated_at = NOW(),
            updated_at = NOW()
        WHERE session_id = '{session_id}';
    """

def create_user_shortlisted_vendor_query(
    wedding_id: str,
    vendor_name: str,
    vendor_category: str,
    contact_info: str = None,
    status: str = 'contacted',
    booked_date: str = None,
    notes: str = None,
    linked_vendor_id: str = None,
    estimated_cost: float = None
) -> str:
    return f"""
        INSERT INTO user_shortlisted_vendors (wedding_id, vendor_name, vendor_category, contact_info, status, booked_date, notes, linked_vendor_id, estimated_cost)
        VALUES (
            '{wedding_id}',
            '{vendor_name}',
            '{vendor_category}',
            {f"'{contact_info}'" if contact_info else 'NULL'},
            '{status}',
            {f"'{booked_date}'" if booked_date else 'NULL'},
            {f"'{notes}'" if notes else 'NULL'},
            {f"'{linked_vendor_id}'" if linked_vendor_id else 'NULL'},
            {estimated_cost if estimated_cost else 'NULL'}
        )
        RETURNING user_vendor_id;
    """

def get_user_shortlisted_vendors_by_wedding_id_query(wedding_id: str, filters: Dict[str, Any] = None) -> str:
    filter_clauses = [f"{k} = '{v}'" for k, v in filters.items()] if filters else []
    where_clause = f"AND {' AND '.join(filter_clauses)}" if filter_clauses else ""
    return f"""
        SELECT user_vendor_id, vendor_name, vendor_category, contact_info, status, booked_date, notes, linked_vendor_id, estimated_cost
        FROM user_shortlisted_vendors
        WHERE wedding_id = '{wedding_id}' {where_clause};
    """

def update_user_shortlisted_vendor_query(
    user_vendor_id: str,
    vendor_name: str = None,
    vendor_category: str = None,
    contact_info: str = None,
    status: str = None,
    booked_date: str = None,
    notes: str = None,
    linked_vendor_id: str = None,
    estimated_cost: float = None
) -> str:
    updates = []
    if vendor_name:
        updates.append(f"vendor_name = '{vendor_name}'")
    if vendor_category:
        updates.append(f"vendor_category = '{vendor_category}'")
    if contact_info:
        updates.append(f"contact_info = '{contact_info}'")
    if status:
        updates.append(f"status = '{status}'")
    if booked_date:
        updates.append(f"booked_date = '{booked_date}'")
    if notes:
        updates.append(f"notes = '{notes}'")
    if linked_vendor_id:
        updates.append(f"linked_vendor_id = '{linked_vendor_id}'")
    if estimated_cost:
        updates.append(f"estimated_cost = {estimated_cost}")

    updates_str = ", ".join(updates)

    return f"""
        UPDATE user_shortlisted_vendors
        SET {updates_str},
            updated_at = NOW()
        WHERE user_vendor_id = '{user_vendor_id}';
    """

def search_vendors_query(category: str, city: str, budget_range: Dict[str, float] = None, style_keywords: List[str] = None) -> str:
    """
    Constructs a SQL query to search for vendors.
    """
    where_clauses = ["1 = 1"]
    if category:
        where_clauses.append(f"vendor_category = '{category}'")
    if city:
        where_clauses.append(f"(address->>'city') ILIKE '%{city}%'")
    if budget_range:
        if "min" in budget_range:
            where_clauses.append(f"pricing_range->>'min' >= '{budget_range['min']}'::float")
        if "max" in budget_range:
            where_clauses.append(f"pricing_range->>'max' <= '{budget_range['max']}'::float")
    if style_keywords:
        # Using pg_trgm for fuzzy matching on vendor_name and description, and a hypothetical style_tags in details
        keyword_clauses = []
        for keyword in style_keywords:
            keyword_clauses.append(f"vendor_name ILIKE '%{keyword}%'")
            keyword_clauses.append(f"description ILIKE '%{keyword}%'")
            # Assuming style_tags is a string field within the details JSONB
            keyword_clauses.append(f"(details->>'style_tags') ILIKE '%{keyword}%'")
        where_clauses.append(f"({' OR '.join(keyword_clauses)})")

    where_clause_str = " AND ".join(where_clauses)

    return f"""
        SELECT *
        FROM vendors
        WHERE {where_clause_str};
    """

def get_vendor_details_query(vendor_id: str) -> str:
    """
    Constructs a SQL query to get details for a specific vendor.
    """
    return f"""
        SELECT *
        FROM vendors
        WHERE vendor_id = '{vendor_id}';
    """

def add_to_shortlist_query(wedding_id: str, linked_vendor_id: str, vendor_name: str, vendor_category: str) -> str:
    """
    Constructs a SQL query to add a vendor to a user's shortlist.
    """
    return f"""
        INSERT INTO user_shortlisted_vendors (wedding_id, linked_vendor_id, vendor_name, vendor_category)
        VALUES ('{wedding_id}', '{linked_vendor_id}', '{vendor_name}', '{vendor_category}')
        RETURNING user_vendor_id;
    """

def create_booking_query(user_id: str, vendor_id: str, event_date: str, total_amount: float, advance_amount_due: float, paid_amount: float, booking_status: str = 'pending') -> str:
    """
    Constructs a SQL query to create a booking record.
    """
    # TODO plan on integrating with wedding_id instead of user_id
    return f"""
        INSERT INTO bookings (user_id, vendor_id, event_date, total_amount, advance_amount_due, paid_amount, booking_status)
        VALUES ('{user_id}', '{vendor_id}', '{event_date}', {total_amount}, {advance_amount_due}, {paid_amount}, '{booking_status}')
        RETURNING booking_id;
    """

def submit_review_query(booking_id: str, user_id: str, vendor_id: str, rating: float, comment: str) -> str:
    """
    Constructs a SQL query to submit a vendor review.
    """
    return f"""
        INSERT INTO reviews (booking_id, user_id, vendor_id, rating, comment)
        VALUES ('{booking_id}', '{user_id}', '{vendor_id}', {rating}, '{comment}')
        RETURNING review_id;
    """

def get_total_budget_query(wedding_id: str) -> str:
    """
    Retrieves the total allocated budget for a given wedding_id from the weddings table.
    Assumes budget is stored in the 'details' JSONB column under a 'total_budget' key.
    Defaults to 0 if not found.
    As of now return all wedding details not only budget
    """
    # TODO plan on how to get the budget for specific side , bride or groom
    return f"""
        SELECT details from weddings
        WHERE wedding_id = '{wedding_id}';
    """
def delete_budget_item_query(item_id: str, wedding_id: str) -> str:
   """
   Deletes a budget item by item_id and wedding_id.
   """
   return f"""
       DELETE FROM budget_items
       WHERE item_id = '{item_id}' AND wedding_id = '{wedding_id}'
       RETURNING item_id;
   """

# Image and Artifact Management Queries

def create_image_artifact_query(
    wedding_id: str,
    artifact_filename: str,
    supabase_url: str,
    generation_prompt: str = None,
    image_type: str = 'generated',
    metadata: str = None
) -> str:
    """
    Creates a record for an image artifact generated or uploaded for a wedding.
    """
    return f"""
        INSERT INTO image_artifacts (wedding_id, artifact_filename, supabase_url, generation_prompt, image_type, metadata)
        VALUES (
            '{wedding_id}',
            '{artifact_filename}',
            '{supabase_url}',
            {f"'{generation_prompt}'" if generation_prompt else 'NULL'},
            '{image_type}',
            {f"'{metadata}'" if metadata else 'NULL'}
        )
        RETURNING artifact_id;
    """

def get_image_artifacts_by_wedding_query(wedding_id: str, image_type: str = None) -> str:
    """
    Retrieves all image artifacts for a wedding, optionally filtered by type.
    """
    type_filter = f"AND image_type = '{image_type}'" if image_type else ""
    return f"""
        SELECT artifact_id, artifact_filename, supabase_url, generation_prompt, image_type, metadata, created_at
        FROM image_artifacts
        WHERE wedding_id = '{wedding_id}' {type_filter}
        ORDER BY created_at DESC;
    """

def update_mood_board_item_with_artifact_query(item_id: str, artifact_id: str) -> str:
    """
    Links a mood board item to an image artifact.
    """
    return f"""
        UPDATE mood_board_items
        SET artifact_id = '{artifact_id}',
            updated_at = NOW()
        WHERE item_id = '{item_id}'
        RETURNING item_id;
    """

def get_mood_board_items_with_artifacts_query(mood_board_id: str) -> str:
    """
    Retrieves mood board items along with their associated image artifacts.
    """
    return f"""
        SELECT 
            mbi.item_id, 
            mbi.image_url, 
            mbi.note, 
            mbi.category,
            mbi.created_at as item_created_at,
            ia.artifact_id,
            ia.artifact_filename,
            ia.generation_prompt,
            ia.image_type,
            ia.metadata as artifact_metadata
        FROM mood_board_items mbi
        LEFT JOIN image_artifacts ia ON mbi.artifact_id = ia.artifact_id
        WHERE mbi.mood_board_id = '{mood_board_id}'
        ORDER BY mbi.created_at DESC;
    """

def delete_mood_board_item_query(item_id: str) -> str:
    """
    Deletes a mood board item.
    """
    return f"""
        DELETE FROM mood_board_items
        WHERE item_id = '{item_id}'
        RETURNING item_id;
    """

def update_mood_board_item_query(item_id: str, note: str = None, category: str = None) -> str:
    """
    Updates a mood board item's note and/or category.
    """
    updates = []
    if note is not None:
        updates.append(f"note = '{note}'")
    if category is not None:
        updates.append(f"category = '{category}'")
    
    if not updates:
        return f"SELECT item_id FROM mood_board_items WHERE item_id = '{item_id}';"
    
    return f"""
        UPDATE mood_board_items
        SET {', '.join(updates)}, updated_at = NOW()
        WHERE item_id = '{item_id}'
        RETURNING item_id;
    """

def get_mood_board_stats_query(wedding_id: str) -> str:
    """
    Gets statistics about mood boards for a wedding.
    """
    return f"""
        SELECT 
            mb.mood_board_id,
            mb.name as mood_board_name,
            COUNT(mbi.item_id) as item_count,
            COUNT(CASE WHEN ia.image_type = 'generated' THEN 1 END) as generated_images,
            COUNT(CASE WHEN ia.image_type = 'uploaded' THEN 1 END) as uploaded_images,
            mb.created_at as board_created_at
        FROM mood_boards mb
        LEFT JOIN mood_board_items mbi ON mb.mood_board_id = mbi.mood_board_id
        LEFT JOIN image_artifacts ia ON mbi.artifact_id = ia.artifact_id
        WHERE mb.wedding_id = '{wedding_id}'
        GROUP BY mb.mood_board_id, mb.name, mb.created_at
        ORDER BY mb.created_at DESC;
    """

def get_latest_chat_session_id_by_wedding_id_query(wedding_id: str) -> str:
    """Get the most recent chat session_id for a wedding."""
    return f"""
        SELECT session_id
        FROM chat_sessions
        WHERE wedding_id = '{wedding_id}'
        ORDER BY last_updated_at DESC NULLS LAST, created_at DESC
        LIMIT 1;
    """


def get_recent_chat_messages_by_session_query(session_id: str, limit: int = 6) -> str:
    """Get recent chat messages for a session_id (schema: sender_type, content jsonb, timestamp).
    We extract text from content->>'text' for convenience.
    """
    return f"""
        SELECT sender_type, content->>'text' AS text, timestamp
        FROM chat_messages
        WHERE session_id = '{session_id}'
        ORDER BY timestamp DESC
        LIMIT {limit};
    """

# New: Chat message insert + session timestamp update (updated for actual schema)

def create_chat_message_query(
    session_id: str,
    sender_type: str,
    text: str,
    sender_name: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Insert chat message using actual schema. Stores text + optional metadata inside content jsonb.
    Table columns: (message_id uuid default, session_id uuid, sender_type varchar, sender_name varchar, content jsonb, timestamp timestamptz default now())
    """
    # Build content JSON
    payload: Dict[str, Any] = {"text": text}
    if metadata:
        payload["metadata"] = metadata
    import json as _json
    content_json = _json.dumps(payload).replace("'", "''")
    sender_name_val = sender_name or sender_type
    return f"""
        INSERT INTO chat_messages (session_id, sender_type, sender_name, content)
        VALUES ('{session_id}', '{sender_type}', '{sender_name_val}', '{content_json}'::jsonb)
        RETURNING message_id;
    """


def update_chat_session_last_updated_at_query(session_id: str) -> str:
    """
    Touches chat_sessions.last_updated_at to NOW(). Useful if triggers are absent.
    """
    return f"""
        UPDATE chat_sessions
        SET last_updated_at = NOW()
        WHERE session_id = '{session_id}';
    """