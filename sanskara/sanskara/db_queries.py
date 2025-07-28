from typing import Dict, Any, List

def get_wedding_by_expected_partner_email_query(email: str) -> str:
    return f"""
        SELECT wedding_id, details
        FROM weddings
        WHERE details @> '{{"other_partner_email_expected":"{email}"}}'::jsonb
        LIMIT 1;
    """

def get_user_and_wedding_info_by_email_query(email: str) -> str:
    return f"""
        SELECT u.user_id, wm.wedding_id, wm.role, w.details AS wedding_details
        FROM users u
        LEFT JOIN wedding_members wm ON u.user_id = wm.user_id
        LEFT JOIN weddings w ON wm.wedding_id = w.wedding_id
        WHERE u.email = '{email}';
    """

def create_wedding_query(current_partner_email: str, details_json: str, other_partner_email: str) -> str:
    return f"""
        INSERT INTO weddings (wedding_name, status, details)
        VALUES (
            'Unnamed Wedding',
            'onboarding_in_progress',
            '{{ "partner_data": {{ "{current_partner_email}": {details_json} }}, "other_partner_email_expected": "{other_partner_email}" }}'::jsonb
        )
        RETURNING wedding_id;
    """

def update_wedding_details_query(
    wedding_id: str,
    current_partner_email: str,
    details_json: str,
    wedding_name: str = None,
    wedding_date: str = None
) -> str:
    updates = [
        f"details = jsonb_set(COALESCE(details, '{{}}'::jsonb), '{{partner_data, \"{current_partner_email}\"}}', '{details_json}'::jsonb, true)"
    ]
    if wedding_name:
        updates.append(f"wedding_name = '{wedding_name}'")
    if wedding_date:
        updates.append(f"wedding_date = '{wedding_date}'")

    updates_str = ", ".join(updates)

    return f"""
        UPDATE weddings
        SET {updates_str},
            updated_at = NOW()
        WHERE wedding_id = '{wedding_id}'
        RETURNING wedding_id;
    """

def add_wedding_member_query(user_id: str, wedding_id: str, role: str) -> str:
    return f"""
        INSERT INTO wedding_members (wedding_id, user_id, role)
        VALUES ('{wedding_id}', '{user_id}', '{role}')
        ON CONFLICT (wedding_id, user_id) DO UPDATE SET role = EXCLUDED.role
        RETURNING user_id;
    """


def update_wedding_status_query(wedding_id: str, status: str) -> str:
    return f"""
        UPDATE weddings
        SET status = '{status}',
            updated_at = NOW()
        WHERE wedding_id = '{wedding_id}';
    """

def get_wedding_details_query(wedding_id: str) -> str:
    return f"SELECT * FROM weddings WHERE wedding_id = '{wedding_id}'"

# Workflow Queries
def create_workflow_query(wedding_id: str, workflow_name: str, status: str, context_summary: Dict[str, Any]) -> str:
    return f"""
        INSERT INTO workflows (wedding_id, workflow_name, status, context_summary)
        VALUES ('{wedding_id}', '{workflow_name}', '{status}', '{context_summary}'::jsonb)
        RETURNING workflow_id;
    """

def get_workflow_by_name_query(wedding_id: str, workflow_name: str) -> str:
    return f"""
        SELECT workflow_id, status, context_summary
        FROM workflows
        WHERE wedding_id = '{wedding_id}' AND workflow_name = '{workflow_name}'
        LIMIT 1;
    """

def update_workflow_status_query(workflow_id: str, status: str, context_summary: Dict[str, Any]) -> str:
    return f"""
        UPDATE workflows
        SET status = '{status}',
            context_summary = '{context_summary}'::jsonb,
            updated_at = NOW()
        WHERE workflow_id = '{workflow_id}';
    """

def get_workflows_by_wedding_id_query(wedding_id: str) -> str:
    return f"""
        SELECT workflow_id, workflow_name, status, context_summary
        FROM workflows
        WHERE wedding_id = '{wedding_id}';
    """

# Task Feedback Queries
def create_task_feedback_query(task_id: str, user_id: str, feedback_type: str, content: str) -> str:
    return f"""
        INSERT INTO task_feedback (task_id, user_id, feedback_type, content)
        VALUES ('{task_id}', '{user_id}', '{feedback_type}', '{content}')
        RETURNING feedback_id;
    """

def get_task_feedback_query(task_id: str) -> str:
    return f"""
        SELECT feedback_id, user_id, feedback_type, content, created_at
        FROM task_feedback
        WHERE task_id = '{task_id}';
    """

# Task Approvals Queries
def create_task_approval_query(task_id: str, approving_party: str, status: str, approved_by_user_id: str) -> str:
    return f"""
        INSERT INTO task_approvals (task_id, approving_party, status, approved_by_user_id)
        VALUES ('{task_id}', '{approving_party}', '{status}', '{approved_by_user_id}')
        RETURNING approval_id;
    """

def get_task_approvals_query(task_id: str) -> str:
    return f"""
        SELECT approval_id, approving_party, status, approved_by_user_id, created_at
        FROM task_approvals
        WHERE task_id = '{task_id}';
    """
    
def create_task_query(
    wedding_id: str,
    title: str,
    description: str = None,
    is_complete: bool = False,
    due_date: str = None,
    priority: str = 'medium',
    category: str = None,
    status: str = 'not_started',
    lead_party: str = None
) -> str:
    return f"""
        INSERT INTO tasks (wedding_id, title, description, is_complete, due_date, priority, category, status, lead_party)
        VALUES (
            '{wedding_id}',
            '{title}',
            {f"'{description}'" if description else 'NULL'},
            {is_complete},
            {f"'{due_date}'" if due_date else 'NULL'},
            '{priority}',
            {f"'{category}'" if category else 'NULL'},
            '{status}',
            {f"'{lead_party}'" if lead_party else 'NULL'}
        )
        RETURNING task_id;
    """

def get_tasks_by_wedding_id_query(wedding_id: str, filters: Dict[str, Any] = None) -> str:
    filter_clauses = [f"{k} = '{v}'" for k, v in filters.items()] if filters else []
    where_clause = f"AND {' AND '.join(filter_clauses)}" if filter_clauses else ""
    return f"""
        SELECT task_id, title, description, is_complete, due_date, priority, category, status, lead_party
        FROM tasks
        WHERE wedding_id = '{wedding_id}' {where_clause};
    """

def update_task_status_query(task_id: str, new_status: str) -> str:
    return f"""
        UPDATE tasks
        SET status = '{new_status}',
            updated_at = NOW()
        WHERE task_id = '{task_id}';
    """

def get_task_details_query(task_id: str) -> str:
    return f"""
        SELECT task_id, wedding_id, title, description, is_complete, due_date, priority, category, status, lead_party
        FROM tasks
        WHERE task_id = '{task_id}';
    """

def create_budget_item_query(
    wedding_id: str,
    item_name: str,
    category: str,
    amount: float,
    vendor_name: str = None,
    status: str = 'Pending',
    contribution_by: str = None
) -> str:
    return f"""
        INSERT INTO budget_items (wedding_id, item_name, category, amount, vendor_name, status, contribution_by)
        VALUES (
            '{wedding_id}',
            '{item_name}',
            '{category}',
            {amount},
            {f"'{vendor_name}'" if vendor_name else 'NULL'},
            '{status}',
            {f"'{contribution_by}'" if contribution_by else 'NULL'}
        )
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
        SET summary = '{summary}'::jsonb,
            last_updated_at = NOW()
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
        # Assuming a 'city' column exists in the vendors table or similar
        where_clauses.append(f"city = '{city}'")
    if budget_range:
        if "min" in budget_range:
            where_clauses.append(f"estimated_cost >= {budget_range['min']}")
        if "max" in budget_range:
            where_clauses.append(f"estimated_cost <= {budget_range['max']}")
    if style_keywords:
        # Assuming style_keywords can be matched against a 'style' or 'tags' column
        # This is a simplified example; a real implementation might use array intersection or full-text search
        for keyword in style_keywords:
            where_clauses.append(f"style_tags ILIKE '%{keyword}%'")

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

def add_to_shortlist_query(wedding_id: str, user_id: str, vendor_id: str, vendor_name: str, vendor_category: str) -> str:
    """
    Constructs a SQL query to add a vendor to a user's shortlist.
    """
    return f"""
        INSERT INTO user_shortlisted_vendors (wedding_id, vendor_id, vendor_name, vendor_category)
        VALUES ('{wedding_id}', '{vendor_id}', '{vendor_name}', '{vendor_category}')
        RETURNING user_vendor_id;
    """

def create_booking_query(wedding_id: str, user_id: str, vendor_id: str, event_date: str, final_amount: float) -> str:
    """
    Constructs a SQL query to create a booking record.
    """
    return f"""
        INSERT INTO bookings (wedding_id, user_id, vendor_id, event_date, final_amount)
        VALUES ('{wedding_id}', '{user_id}', '{vendor_id}', '{event_date}', {final_amount})
        RETURNING booking_id;
    """

def submit_review_query(booking_id: str, user_id: str, rating: float, comment: str) -> str:
    """
    Constructs a SQL query to submit a vendor review.
    """
    return f"""
        INSERT INTO reviews (booking_id, user_id, rating, comment)
        VALUES ('{booking_id}', '{user_id}', {rating}, '{comment}')
        RETURNING review_id;
    """