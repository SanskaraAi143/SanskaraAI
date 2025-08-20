import json
import logging
from typing import List, Dict, Any, Optional
from google.adk.tools import ToolContext # For type hinting context

from ..shared_libraries.helpers import execute_supabase_sql # Relative import

# Configure logging for this module
logger = logging.getLogger(__name__)

async def get_user_id(email: str, tool_context: ToolContext) -> Dict[str, Any]:
    """
    Retrieves the user_id for a given email from the users table.

    Args:
        email (str): The user's email address. Must be a non-empty string.
        tool_context (ToolContext): The ADK ToolContext for state management.

    Returns:
        Dict[str, Any]:
            On success: `{"status": "success", "data": {"user_id": "uuid-string"}}`
            On failure: `{"status": "error", "error": "Error message"}`
            If user not found: `{"status": "error", "error": "User not found."}` (or similar)

    Error Handling:
        - Returns an error dict if email is invalid.
        - Returns an error dict if the database query fails or returns an unexpected format.
        - Logs errors using the standard logger.

    Dependencies:
        - `execute_supabase_sql` from `shared_libraries.helpers`.

    Example Usage:
        ```python
        user_info = await get_user_id("test@example.com", tool_context)
        if user_info["status"] == "success":
            user_id = user_info["data"]["user_id"]
            print(f"User ID: {user_id}")
        else:
            print(f"Error: {user_info['error']}")
        ```
    """
    if not email or not isinstance(email, str):
        logger.error("get_user_id: Invalid email provided.")
        return {"status": "error", "error": "Invalid email provided. Email must be a non-empty string."}

    # Check cache first
    cached_user_id = tool_context.state.get(f"user_id_by_email:{email}")
    if cached_user_id:
        logger.info(f"get_user_id: Returning cached user_id for email: {email}")
        return {"status": "success", "data": {"user_id": cached_user_id}}

    logger.info(f"get_user_id: Attempting to get user_id for email: {email}")
    sql = "SELECT user_id FROM users WHERE email = :email LIMIT 1;"

    try:
        result = await execute_supabase_sql(sql, {"email": email})
        logger.info(f"get_user_id: SQL executed for email {email}. Result: {result}")
        if isinstance(result, dict) and "error" in result: # Error from execute_supabase_sql
            logger.error(f"get_user_id: Database error for email {email}: {result['error']}")
            return {"status": "error", "error": result['error']}

        user_data = None
        if isinstance(result, list) and result:
            user_data = result[0]
        elif isinstance(result, dict) and result.get("rows") and result["rows"]: # Should be covered by list case with MCP
            user_data = result["rows"][0]
        elif isinstance(result, dict) and "user_id" in result: # Direct dict if MCP returns single object
             user_data = result

        if user_data and "user_id" in user_data:
            user_id = user_data["user_id"]
            tool_context.state[f"user_id_by_email:{email}"] = user_id # Cache the result
            logger.info(f"get_user_id: Successfully found user_id for email {email}. Cached.")
            return {"status": "success", "data": {"user_id": user_id}}
        else:
            logger.warning(f"get_user_id: User not found for email {email}. Result: {result}")
            return {"status": "error", "error": "User not found."}

    except Exception as e:
        logger.exception(f"get_user_id: Unexpected error for email {email}: {e}")
        return {"status": "error", "error": f"An unexpected error occurred: {str(e)}"}


async def get_user_data(user_id: str, tool_context: ToolContext) -> Dict[str, Any]:
    """
    Retrieves all user data for a given user_id from the users table.

    Args:
        user_id (str): The user's UUID. Must be a non-empty string.
        tool_context (ToolContext): The ADK ToolContext for state management.

    Returns:
        Dict[str, Any>:
            On success: `{"status": "success", "data": {"user_id": ..., "email": ..., ...}}`
            On failure: `{"status": "error", "error": "Error message"}`
            If user not found: `{"status": "error", "error": "User data not found."}`

    Error Handling:
        - Returns an error dict if user_id is invalid.
        - Returns an error dict if the database query fails or returns an unexpected format.
        - Logs errors.

    Dependencies:
        - `execute_supabase_sql` from `shared_libraries.helpers`.

    Example Usage:
        ```python
        user_details = await get_user_data("some-uuid-string", tool_context)
        if user_details["status"] == "success":
            print(f"User data: {user_details['data']}")
        else:
            print(f"Error: {user_details['error']}")
        ```
    """
    if not user_id or not isinstance(user_id, str):
        logger.error("get_user_data: Invalid user_id provided.")
        return {"status": "error", "error": "Invalid user_id provided. User ID must be a non-empty string."}

    # Check cache first
    cached_user_data = tool_context.state.get(f"user_data:{user_id}")
    if cached_user_data:
        logger.info(f"get_user_data: Returning cached user data for user_id: {user_id}")
        return {"status": "success", "data": cached_user_data}

    logger.info(f"get_user_data: Attempting to get data for user_id: {user_id}")
    sql = "SELECT * FROM users WHERE user_id = :user_id LIMIT 1;"

    try:
        result = await execute_supabase_sql(sql, {"user_id": user_id})

        if isinstance(result, dict) and "error" in result:
            logger.error(f"get_user_data: Database error for user_id {user_id}: {result['error']}")
            return {"status": "error", "error": result['error']}

        user_data_dict = None
        if isinstance(result, list) and result:
            user_data_dict = result[0]
        elif isinstance(result, dict) and result.get("rows") and result["rows"]:
             user_data_dict = result["rows"][0]
        elif isinstance(result, dict) and "user_id" in result and result.get("user_id") == user_id:
            user_data_dict = result

        if user_data_dict:
            tool_context.state[f"user_data:{user_id}"] = user_data_dict # Cache the result
            logger.info(f"get_user_data: Successfully retrieved data for user_id {user_id}. Cached.")
            return {"status": "success", "data": user_data_dict}
        else:
            logger.warning(f"get_user_data: User data not found for user_id {user_id}. Result: {result}")
            return {"status": "error", "error": "User data not found."}

    except Exception as e:
        logger.exception(f"get_user_data: Unexpected error for user_id {user_id}: {e}")
        return {"status": "error", "error": f"An unexpected error occurred: {str(e)}"}


async def update_user_data(user_id: str, data: Dict[str, Any], tool_context: ToolContext) -> Dict[str, Any]:
    """
    Updates user data for a given user_id.
    Specific columns are updated directly; other fields are merged into the 'preferences' JSONB column.
    The 'user_type' column is intentionally not updatable by this function.

    Args:
        user_id (str): The user's UUID. Must be a non-empty string.
        data (Dict[str, Any]): A dictionary of fields to update.
                               Keys matching allowed columns update those columns.
                               Other keys are added/updated within the 'preferences' field.
        tool_context (ToolContext): The ADK ToolContext for state management.

    Returns:
        Dict[str, Any>:
            On success: `{"status": "success", "data": {updated_user_data_dict}}`
            On failure: `{"status": "error", "error": "Error message"}`

    Error Handling:
        - Returns an error dict if user_id or data is invalid.
        - Returns an error dict if no valid fields for update are provided.
        - Returns an error dict if database update fails.
        - Logs errors.

    Dependencies:
        - `get_user_data` (for merging preferences).
        - `execute_supabase_sql` from `shared_libraries.helpers`.

    Example Usage:
        ```python
        update_payload = {"display_name": "New Name", "custom_pref": "value1"}
        response = await update_user_data("some-uuid", update_payload, tool_context)
        if response["status"] == "success":
            print("User updated:", response["data"])
        else:
            print("Update error:", response["error"])
        ```
    """
    if not user_id or not isinstance(user_id, str):
        logger.error("update_user_data: Invalid user_id provided.")
        return {"status": "error", "error": "Invalid user_id. Must be a non-empty string."}
    if not data or not isinstance(data, dict):
        logger.error(f"update_user_data: Invalid or empty data provided for user_id {user_id}.")
        return {"status": "error", "error": "Invalid or empty data payload. Must be a non-empty dictionary."}

    logger.info(f"update_user_data: Attempting to update data for user_id: {user_id} with payload: {data}")

    USERS_TABLE_COLUMNS = {
        "user_id", "supabase_auth_uid", "email", "display_name", "created_at", "updated_at",
        "wedding_date", "wedding_location", "wedding_tradition", "preferences"
    }

    fields_to_set = {}
    preferences_to_merge = data.get("preferences", {})
    if not isinstance(preferences_to_merge, dict): # Ensure it's a dict if provided
        logger.warning(f"update_user_data: 'preferences' field in payload for user {user_id} is not a dict, ignoring.")
        preferences_to_merge = {}

    for key, value in data.items():
        if key == "preferences":
            continue
        if key in USERS_TABLE_COLUMNS:
            fields_to_set[key] = value
        elif key == "user_type":
             logger.warning(f"update_user_data: Attempt to update 'user_type' for user {user_id} was ignored.")
        else: # Field not in main columns (excluding user_type) goes to preferences
            preferences_to_merge[key] = value

    try:
        if preferences_to_merge:
            # Pass context to get_user_data for potential caching benefits
            current_user_response = await get_user_data(user_id, tool_context)
            if current_user_response["status"] == "success":
                current_prefs = current_user_response["data"].get("preferences", {})
                if not isinstance(current_prefs, dict):
                    current_prefs = {} # Default to empty if malformed or None
                current_prefs.update(preferences_to_merge)
                fields_to_set["preferences"] = current_prefs
            else: # Failed to get current user data, potentially error out or proceed with caution
                logger.warning(f"update_user_data: Could not fetch current preferences for user {user_id} due to: {current_user_response.get('error')}. Merging with empty preferences.")
                fields_to_set["preferences"] = preferences_to_merge # Use only new preferences

        if not fields_to_set:
            logger.warning(f"update_user_data: No valid fields to update for user_id {user_id} after processing payload.")
            return {"status": "error", "error": "No valid fields provided for update after processing."}

        if "preferences" in fields_to_set and isinstance(fields_to_set["preferences"], dict):
            fields_to_set["preferences"] = json.dumps(fields_to_set["preferences"])

        set_clause_parts = []
        update_params = {}
        # Use specific param names to avoid issues with SQL keywords or special chars in keys
        for i, (k, v) in enumerate(fields_to_set.items()):
            param_name = f"val{i}"
            set_clause_parts.append(f"{k} = :{param_name}") # k should be from USERS_TABLE_COLUMNS, thus safe
            update_params[param_name] = v

        set_clause = ", ".join(set_clause_parts)
        sql = f"UPDATE users SET {set_clause} WHERE user_id = :user_id_param RETURNING *;"
        final_params = {**update_params, "user_id_param": user_id} # Ensure user_id key for param is unique

        result = await execute_supabase_sql(sql, final_params)

        if isinstance(result, dict) and "error" in result:
            logger.error(f"update_user_data: Database error for user_id {user_id}: {result['error']}")
            return {"status": "error", "error": result['error']}

        updated_data = None
        if isinstance(result, list) and result:
            updated_data = result[0]
        elif isinstance(result, dict) and result.get("rows") and result["rows"]:
            updated_data = result["rows"][0]
        elif isinstance(result, dict) and "user_id" in result:
            updated_data = result

        if updated_data:
            # Invalidate cache after update
            if f"user_data:{user_id}" in tool_context.state:
                del tool_context.state[f"user_data:{user_id}"]
            if f"user_id_by_email:{updated_data.get('email')}" in tool_context.state:
                del tool_context.state[f"user_id_by_email:{updated_data.get('email')}"]

            logger.info(f"update_user_data: Successfully updated data for user_id {user_id}. Cache invalidated.")
            return {"status": "success", "data": updated_data}
        else:
            logger.error(f"update_user_data: Update failed for user_id {user_id}. DB Result: {result}")
            return {"status": "error", "error": "Update failed or did not return updated data."}

    except Exception as e:
        logger.exception(f"update_user_data: Unexpected error for user_id {user_id}: {e}")
        return {"status": "error", "error": f"An unexpected error occurred: {str(e)}"}


async def get_user_activities(user_id: str, tool_context: ToolContext) -> Dict[str, Any]:
    """
    Retrieves all user activities (chat messages) for a given user, ordered by timestamp.

    Args:
        user_id (str): The user's UUID. Must be a non-empty string.
        tool_context (ToolContext): The ADK ToolContext for state management.

    Returns:
        Dict[str, Any>:
            On success: `{"status": "success", "data": [activity_dict_1, activity_dict_2, ...]}`
            On failure: `{"status": "error", "error": "Error message"}`
            If no activities: `{"status": "success", "data": []}`

    Error Handling:
        - Returns an error dict if user_id is invalid.
        - Returns an error dict if the database query fails.
        - Logs errors.

    Dependencies:
        - `execute_supabase_sql` from `shared_libraries.helpers`.

    Example Usage:
        ```python
        activities_response = await get_user_activities("some-uuid", tool_context)
        if activities_response["status"] == "success":
            for activity in activities_response["data"]:
                print(activity)
        else:
            print(f"Error fetching activities: {activities_response['error']}")
        ```
    """
    if not user_id or not isinstance(user_id, str):
        logger.error("get_user_activities: Invalid user_id provided.")
        return {"status": "error", "error": "Invalid user_id. Must be a non-empty string."}

    # Activities are dynamic and usually not cached in session state
    logger.info(f"get_user_activities: Fetching activities for user_id: {user_id}")
    sql = """
        SELECT cm.*
        FROM chat_sessions cs
        JOIN chat_messages cm ON cs.session_id = cm.session_id
        WHERE cs.user_id = :user_id
        ORDER BY cm.timestamp DESC;
    """
    try:
        result = await execute_supabase_sql(sql, {"user_id": user_id})

        if isinstance(result, dict) and "error" in result:
            logger.error(f"get_user_activities: Database error for user_id {user_id}: {result['error']}")
            return {"status": "error", "error": result['error']}

        if isinstance(result, list):
            logger.info(f"get_user_activities: Successfully retrieved {len(result)} activities for user_id {user_id}.")
            return {"status": "success", "data": result}
        else: # Should ideally not happen if execute_supabase_sql is consistent for SELECTs
            logger.warning(f"get_user_activities: Unexpected result format for user_id {user_id}. Result: {result}")
            return {"status": "error", "error": "Could not fetch user activities or unexpected format."}

    except Exception as e:
        logger.exception(f"get_user_activities: Unexpected error for user_id {user_id}: {e}")
        return {"status": "error", "error": f"An unexpected error occurred: {str(e)}"}