from typing import Dict, Any

def get_wedding_by_expected_partner_email_query(email: str) -> str:
    return f"""
        SELECT wedding_id, details
        FROM weddings
        WHERE details @> '{{"other_partner_email_expected":"{email}"}}'::jsonb
        LIMIT 1;
    """

def get_user_and_wedding_info_by_email_query(email: str) -> str:
    return f"""
        SELECT u.user_id, wm.wedding_id, wm.role
        FROM users u
        LEFT JOIN wedding_members wm ON u.user_id = wm.user_id
        WHERE u.email = '{email}';
    """

def create_wedding_query(current_partner_email: str, details_json: str, other_partner_email: str) -> str:
    return f"""
        INSERT INTO weddings (wedding_name, status, details)
        VALUES (
            'New Wedding',
            'onboarding_in_progress',
            '{{
                "partner_data": {{ "{current_partner_email}": {details_json} }},
                "other_partner_email_expected": "{other_partner_email}"
            }}'::jsonb
        )
        RETURNING wedding_id;
    """

def update_wedding_details_query(wedding_id: str, current_partner_email: str, details_json: str) -> str:
    return f"""
        UPDATE weddings
        SET details = jsonb_set(COALESCE(details, '{{}}'::jsonb), '{{partner_data, "{current_partner_email}"}}', '{details_json}'::jsonb, true),
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

def find_wedding_by_other_partner_email_query(email: str) -> str:
    return f"""
        SELECT wedding_id, details
        FROM weddings
        WHERE details @> '{{"other_partner_email_expected":"{email}"}}'::jsonb
        LIMIT 1;
    """

def update_wedding_status_query(wedding_id: str, status: str) -> str:
    return f"""
        UPDATE weddings
        SET status = '{status}',
            updated_at = NOW()
        WHERE wedding_id = '{wedding_id}';
    """

def get_wedding_details_query(wedding_id: str) -> str:
    return f"SELECT details FROM weddings WHERE wedding_id = '{wedding_id}'"
