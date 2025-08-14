import json
import os
import asyncio
import dotenv
import ast
import re
import logging # Import standard logging
from typing import Optional, Any, Tuple, Dict
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters

# Configure logging for this module
logger = logging.getLogger(__name__)

# Load .env from the project root (two levels up from shared_libraries)
# This ensures environment variables are loaded when this module is imported.
# It's important if other modules (like config.py) also call load_dotenv(),
# dotenv usually handles multiple calls gracefully (doesn't overwrite existing env vars by default).
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
if dotenv.load_dotenv(dotenv_path=dotenv_path):
    logger.info(f"helpers.py: Loaded .env from: {dotenv_path}")
else:
    # Fallback if .env is in current dir (e.g. if script run from root)
    if dotenv.load_dotenv():
        logger.info("helpers.py: Loaded .env from current directory or parent.")
    else:
        logger.warning("helpers.py: .env file not found. Critical environment variables might be missing.")


SUPABASE_ACCESS_TOKEN = os.getenv("SUPABASE_ACCESS_TOKEN")
SUPABASE_PROJECT_ID = os.getenv("SUPABASE_PROJECT_ID", "lylsxoupakajkuisjdfl") # Default if not set

# Global MCPToolset instance for Supabase
_supabase_mcp_toolset: Optional[MCPToolset] = None
_supabase_tools: Optional[Dict[str, Any]] = None # Using Any for ADK tool type flexibility

async def init_supabase_mcp() -> Tuple[Optional[MCPToolset], Optional[Dict[str, Any]]]:
    """
    Initializes the Supabase MCP (Multi-Capability Peripheral) toolset if not already initialized.
    This toolset allows interaction with Supabase, primarily for executing SQL queries.

    The function uses global variables `_supabase_mcp_toolset` and `_supabase_tools`
    to cache the initialized toolset and tools, preventing re-initialization on subsequent calls.

    Raises:
        ValueError: If the `SUPABASE_ACCESS_TOKEN` environment variable is not set,
                    as it's crucial for connecting to the Supabase MCP server.
        RuntimeError: If the MCP server command fails or the 'execute_sql' tool is not found.

    Returns:
        Tuple[Optional[MCPToolset], Optional[Dict[str, Any]]]:
            A tuple containing the initialized MCPToolset instance and a dictionary of its tools.
            Returns (None, None) or raises an exception if initialization fails.

    Side Effects:
        - Modifies global `_supabase_mcp_toolset` and `_supabase_tools`.
        - May print to stdout/stderr if the MCP server process does.
        - Logs information about initialization status or errors.
    """
    global _supabase_mcp_toolset, _supabase_tools
    if _supabase_mcp_toolset is None:
        logger.info("init_supabase_mcp: Attempting to initialize Supabase MCP toolset.")
        if not SUPABASE_ACCESS_TOKEN:
            logger.error("init_supabase_mcp: SUPABASE_ACCESS_TOKEN environment variable is not set.")
            raise ValueError("SUPABASE_ACCESS_TOKEN environment variable is not set.")

        try:
            mcp = MCPToolset(
                connection_params=StdioServerParameters(
                    command='/usr/bin/npx', # Consider making command/args configurable if needed
                    args=["-y", "@supabase/mcp-server-supabase@latest", "--access-token", SUPABASE_ACCESS_TOKEN],
                ),
                tool_filter=["execute_sql"] # Only interested in the SQL execution tool
            )

            tools = await mcp.get_tools()
            if not tools or "execute_sql" not in [tool.name for tool in tools]:
                logger.error("init_supabase_mcp: 'execute_sql' tool not found after MCP server connection.")
                raise RuntimeError("'execute_sql' tool not found in Supabase MCP server.")

            _supabase_mcp_toolset = mcp
            _supabase_tools = {tool.name: tool for tool in tools}
            logger.info("init_supabase_mcp: Supabase MCP toolset initialized successfully with 'execute_sql' tool.")

        except Exception as e:
            logger.exception(f"init_supabase_mcp: Failed to initialize Supabase MCP toolset: {e}")
            # Reset globals to allow retry if applicable, or ensure they remain None
            _supabase_mcp_toolset = None
            _supabase_tools = None
            raise RuntimeError(f"Failed to initialize Supabase MCP toolset: {e}") from e

    return _supabase_mcp_toolset, _supabase_tools


def sql_quote_value(val: Any) -> str:
    """
    Safely quotes and formats a Python value for inlining into an SQL string.
    Handles None, numbers, strings, dictionaries, and lists.

    Args:
        val (Any): The Python value to be quoted.
                   - None becomes 'NULL'.
                   - Numbers (int, float) are converted to string.
                   - Strings are enclosed in single quotes, with internal single quotes escaped ('').
                   - Dictionaries and lists are JSON serialized, then treated as strings (quoted and escaped).

    Returns:
        str: The SQL-safe string representation of the value.

    Example:
        ```python
        sql_quote_value(None)  # "NULL"
        sql_quote_value(123)   # "123"
        sql_quote_value("O'Malley") # "'O''Malley'"
        sql_quote_value({"key": "value"}) # "'{\"key\": \"value\"}'" (or similar JSON string)
        ```
    """
    if val is None:
        return 'NULL'
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, (dict, list)):
        # JSON dump, then escape single quotes within the JSON string for SQL compatibility
        val_str = json.dumps(val).replace("'", "''")
        return f"'{val_str}'"
    # Default to string, escape single quotes
    val_str = str(val).replace("'", "''")
    return f"'{val_str}'"


async def execute_supabase_sql(sql: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Executes a given SQL query against the Supabase database via the MCP server.
    Handles parameter inlining (use with caution, prefer parameterized queries if MCP tool supports them directly).

    Args:
        sql (str): The SQL query string. Placeholders should match keys in `params` (e.g., ":key_name").
        params (Optional[Dict[str, Any]]): A dictionary of parameters to be inlined into the SQL query
                                           by replacing placeholders. Values are quoted using `sql_quote_value`.

    Returns:
        Dict[str, Any]:
            On success: A dictionary representing the parsed JSON result from the query (often a list of rows).
                        Example: `{"status": "success", "data": [{"col1": "val1"}, {"col1": "val2"}]}`
            On failure or error: `{"status": "error", "error": "Error message", "details": "Optional details"}`

    Error Handling:
        - Raises ValueError or RuntimeError from `init_supabase_mcp` if MCP setup fails.
        - Returns an error dictionary if `execute_sql` tool is missing or if the MCP call itself fails.
        - Returns an error dictionary if the result from MCP cannot be parsed as JSON.
        - Logs errors and debug information.

    Note on Parameterization:
        This function currently inlines parameters into the SQL string. This is done because the
        underlying MCP `execute_sql` tool might not directly support parameterized queries in all setups.
        Be extremely cautious if constructing SQL with user-provided keys in `params`.
        Ideally, use this for predefined queries where `params` keys are controlled.
    """
    logger.debug(f"execute_supabase_sql: Received SQL: {sql}, Params: {params}")
    try:
        # Ensure MCP is initialized. This will raise if critical env vars are missing.
        mcp_set, tools_map = await init_supabase_mcp()
        if not mcp_set or not tools_map: # Should be caught by init_supabase_mcp's raise
             return {"status": "error", "error": "Supabase MCP toolset not available."}

        sql_tool = tools_map.get("execute_sql")
        if not sql_tool: # Should also be caught by init_supabase_mcp
            return {"status": "error", "error": "Supabase MCP 'execute_sql' tool not found."}

        final_sql = sql
        if params:
            for k, v in params.items():
                # Ensure placeholder format is consistent, e.g., always :key
                placeholder = f":{k}"
                if placeholder not in final_sql:
                    logger.warning(f"execute_supabase_sql: Parameter key '{k}' as placeholder '{placeholder}' not found in SQL query. SQL: {sql}")
                    # Decide if this is an error or just a warning. For now, warning.
                final_sql = final_sql.replace(placeholder, sql_quote_value(v))

        mcp_args = {"query": final_sql, "project_id": SUPABASE_PROJECT_ID}
        logger.debug(f"execute_supabase_sql: Executing with MCP args: {mcp_args}")

        mcp_result = await sql_tool.run_async(args=mcp_args, tool_context=None)
        logger.debug(f"execute_supabase_sql: Raw result from MCP: {mcp_result}")

        if hasattr(mcp_result, "content") and mcp_result.content and hasattr(mcp_result.content[0], "text"):
            text_response = mcp_result.content[0].text

            # Attempt to parse as JSON directly first
            try:
                extracted_data = extract_untrusted_json(text_response)
                if extracted_data is not None:
                    return extracted_data[0]
            except json.JSONDecodeError:
                # If direct JSON load fails, try extracting JSON-like string if it's embedded
                # If still no valid JSON, and it's not an obvious error structure from MCP itself:
                logger.error(f"execute_supabase_sql: Failed to parse MCP response as JSON. Response text: {text_response}")
                return {"status": "error", "error": "Failed to parse database response.", "details": text_response}

        # Handle cases where MCP result might indicate an error more directly
        if hasattr(mcp_result, "error_message") and mcp_result.error_message:
            logger.error(f"execute_supabase_sql: MCP tool returned an error: {mcp_result.error_message}")
            return {"status": "error", "error": mcp_result.error_message}

        logger.error(f"execute_supabase_sql: No content or unexpected format in MCP response: {mcp_result}")
        return {"status": "error", "error": "No content or unexpected format in database response."}

    except ValueError as ve: # Catch specific errors from init_supabase_mcp
        logger.error(f"execute_supabase_sql: Initialization error: {ve}")
        return {"status": "error", "error": str(ve)}
    except RuntimeError as rte: # Catch specific errors from init_supabase_mcp
        logger.error(f"execute_supabase_sql: Runtime error during MCP interaction: {rte}")
        return {"status": "error", "error": str(rte)}
    except Exception as e:
        logger.exception(f"execute_supabase_sql: Unexpected error executing SQL '{sql[:100]}...': {e}")
        # Mask potentially sensitive details from raw exception string
        return {"status": "error", "error": "An unexpected error occurred during SQL execution."}


def extract_untrusted_json(text_data: str) -> Optional[Any]:
    """
    Extracts and parses the first valid JSON array or object found within a larger text string.
    This is useful when the desired JSON is embedded within logs or other text.
    Handles escaped double quotes within the JSON string.

    Args:
        text_data (str): The string potentially containing an embedded JSON structure.

    Returns:
        Optional[Any]: The parsed JSON data (list or dict) if found and valid, otherwise None.

    Example:
        ```python
        log_line = "Some prefix text [[{"key": "value"}]] and some suffix."
        json_data = extract_untrusted_json(log_line)
        # json_data would be [{'key': 'value'}]
        ```
    """
    if not isinstance(text_data, str):
        logger.warning(f"extract_untrusted_json: Input was not a string, type: {type(text_data)}")
        return None

    # Use a non-greedy regex to find the smallest JSON object or array
    # This helps in cases where multiple JSON structures might be present or
    # where the JSON is embedded with other text.
    match = re.search(r"({.*?})|(\[.*?\])", text_data, re.DOTALL)
    if match:
        json_str = match.group(0).strip()

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"extract_untrusted_json: JSON parsing failed for extracted string: '{json_str}'. Error: {e}")
            return None
    logger.debug(f"extract_untrusted_json: No JSON array or object found in text: {text_data[:100]}...")
    return None



if __name__ == "__main__":
    # Example usage for helpers.py (for direct testing of these functions)
    logging.basicConfig(level=logging.DEBUG) # Enable debug logging for test

    async def test_helpers():
        logger.info("Testing helper functions...")

        # Test init_supabase_mcp (requires SUPABASE_ACCESS_TOKEN in .env)
        if SUPABASE_ACCESS_TOKEN:
            logger.info("\n--- Testing init_supabase_mcp ---")
            try:
                mcp_set, tools_map = await init_supabase_mcp()
                if mcp_set and tools_map:
                    logger.info(f"Supabase MCP initialized. Found tools: {list(tools_map.keys())}")

                    logger.info("\n--- Testing execute_supabase_sql (SELECT 1) ---")
                    # Requires SUPABASE_PROJECT_ID to be set or uses default
                    select_result = await execute_supabase_sql("SELECT 1 as testval;", {})
                    logger.info(f"SELECT 1 Result: {json.dumps(select_result, indent=2)}")
                    assert select_result.get("status") == "success"
                    assert isinstance(select_result.get("data"), list)
                    assert select_result["data"][0].get("testval") in [1, "1"] # Varies by DB/driver

                else:
                    logger.error("Supabase MCP initialization failed to return expected objects in test.")
            except Exception as e:
                logger.error(f"Error during MCP initialization/execution test: {e}")
        else:
            logger.warning("Skipping init_supabase_mcp and execute_supabase_sql tests: SUPABASE_ACCESS_TOKEN not set.")

        # Test sql_quote_value
        logger.info("\n--- Testing sql_quote_value ---")
        logger.info(f"None -> {sql_quote_value(None)}")
        logger.info(f"123 -> {sql_quote_value(123)}")
        logger.info(f"O'Malley -> {sql_quote_value("O'Malley")}")
        logger.info(f"[1, \"test\"] -> {sql_quote_value([1, "test"])}")
        logger.info(f"{{'key': 'val with \\'quote\\''}} -> {sql_quote_value({'key': "val with 'quote'"})}")

        # Test extract_untrusted_json
        logger.info("\n--- Testing extract_untrusted_json ---")
        test_str1 = "Some log [{\"id\": 1, \"name\": \"Test\"}] more log"
        logger.info(f"'{test_str1}' -> {extract_untrusted_json(test_str1)}")
        test_str2 = "{\"error\": \"Something went wrong\"} but also other stuff"
        logger.info(f"'{test_str2}' -> {extract_untrusted_json(test_str2)}")
        test_str3 = "No json here"
        logger.info(f"'{test_str3}' -> {extract_untrusted_json(test_str3)}")
        test_str4 = "Embedded: {\\\"key\\\": \\\"value with esc \\\\\\\"quotes\\\\\\\"\\\"}" # Escaped quotes
        logger.info(f"'{test_str4}' -> {extract_untrusted_json(test_str4)}")


    asyncio.run(test_helpers())
