import json
import os
import asyncio
import dotenv
import ast
import re
import datetime
from typing import Optional, Any, Tuple, Dict
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters,StdioConnectionParams
import logging # Import the custom JSON logger

dotenv_paths = [
    os.path.join(os.path.dirname(__file__), '..', '.env'),
    os.path.join(os.path.dirname(__file__), '.env'),
    os.path.abspath('.env')
]

dotenv_loaded = False
for path in dotenv_paths:
    if os.path.exists(path) and dotenv.load_dotenv(dotenv_path=path):
        logging.info(f"helpers.py: Loaded .env from: {path}")
        dotenv_loaded = True
        break

if not dotenv_loaded:
    if dotenv.load_dotenv():
        logging.info("helpers.py: Loaded .env from current directory or parent.")
    else:
        logging.warning("helpers.py: .env file not found. Critical environment variables might be missing.")


SUPABASE_ACCESS_TOKEN = os.getenv("SUPABASE_ACCESS_TOKEN")
SUPABASE_PROJECT_ID = os.getenv("SUPABASE_PROJECT_ID", "lylsxoupakajkuisjdfl")

_supabase_mcp_toolset: Optional[MCPToolset] = None
_supabase_tools: Optional[Dict[str, Any]] = None
_mcp_session: Optional[MCPToolset] = None

async def init_supabase_mcp() -> Tuple[Optional[MCPToolset], Optional[Dict[str, Any]]]:
    global _mcp_session, _supabase_mcp_toolset, _supabase_tools

    if _supabase_mcp_toolset and _supabase_tools:
        logging.debug("init_supabase_mcp: Supabase MCP toolset already initialized. Reusing existing session.")
        return _supabase_mcp_toolset, _supabase_tools

    logging.info("init_supabase_mcp: Attempting to initialize Supabase MCP toolset.")
    if not SUPABASE_ACCESS_TOKEN:
        logging.error("init_supabase_mcp: SUPABASE_ACCESS_TOKEN environment variable is not set.")
        raise ValueError("SUPABASE_ACCESS_TOKEN environment variable is not set.")

    try:
        # Check if an MCP session exists and is active before trying to close it.
        # This prevents errors if init_supabase_mcp is called multiple times without a successful init first.
        if _mcp_session is not None and not _mcp_session.is_closed:
            logging.info("init_supabase_mcp: Closing existing MCP session before re-initialization.")
            await _mcp_session.close()
            _mcp_session = None

        connection_params = StdioServerParameters(
            command='/usr/bin/npx',
            args=["-y", "@supabase/mcp-server-supabase@latest", "--access-token", SUPABASE_ACCESS_TOKEN],
        )
        mcp = MCPToolset(
            connection_params=StdioConnectionParams(server_params=connection_params, timeout=20),
            tool_filter=["execute_sql"]
        )
        _mcp_session = mcp  # Assign the new MCPToolset instance to _mcp_session
        tools = await mcp.get_tools()
        if not tools or "execute_sql" not in [tool.name for tool in tools]:
            logging.error("init_supabase_mcp: 'execute_sql' tool not found after MCP server connection.")
            raise RuntimeError("'execute_sql' tool not found in Supabase MCP server.")

        _supabase_mcp_toolset = mcp
        _supabase_tools = {tool.name: tool for tool in tools}
        logging.info("init_supabase_mcp: Supabase MCP toolset initialized successfully with 'execute_sql' tool.")

    except Exception as e:
        logging.exception(f"init_supabase_mcp: Failed to initialize Supabase MCP toolset: {e}")
        _supabase_mcp_toolset = None
        _supabase_tools = None
        _mcp_session = None  # Ensure _mcp_session is also cleared on failure
        raise RuntimeError(f"Failed to initialize Supabase MCP toolset: {e}") from e

    return _supabase_mcp_toolset, _supabase_tools

def sql_quote_value(val: Any) -> str:
    if val is None:
        return 'NULL'
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, (dict, list)):
        val_str = json.dumps(val).replace("'", "''")
        return f"'{val_str}'"
    val_str = str(val).replace("'", "''")
    return f"'{val_str}'"


import time

async def execute_supabase_sql(sql: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    start_time = time.perf_counter()
    logging.debug(f"execute_supabase_sql: Received SQL: {sql}, Params: {params}")
    try:
        mcp_set, tools_map = await init_supabase_mcp()
        if not mcp_set or not tools_map:
            end_time = time.perf_counter()
            duration = (end_time - start_time) * 1000
            logging.error(f"execute_supabase_sql: Supabase MCP toolset not available. Duration: {duration:.2f}ms")
            return {"status": "error", "error": "Supabase MCP toolset not available."}

        sql_tool = tools_map.get("execute_sql")
        if not sql_tool:
            end_time = time.perf_counter()
            duration = (end_time - start_time) * 1000
            logging.error(f"execute_supabase_sql: Supabase MCP 'execute_sql' tool not found. Duration: {duration:.2f}ms")
            return {"status": "error", "error": "Supabase MCP 'execute_sql' tool not found."}

        final_sql = sql
        if params:
            for k, v in params.items():
                placeholder = f":{k}"
                if placeholder not in final_sql:
                    logging.warning(f"execute_supabase_sql: Parameter key '{k}' as placeholder '{placeholder}' not found in SQL query. SQL: {sql}")
                final_sql = final_sql.replace(placeholder, sql_quote_value(v))

        mcp_args = {"query": final_sql, "project_id": SUPABASE_PROJECT_ID}
        logging.info(f"execute_supabase_sql: Executing with MCP args: {mcp_args}")

        mcp_result = await sql_tool.run_async(args=mcp_args, tool_context=None)
        logging.debug(f"execute_supabase_sql: Raw result from MCP: {mcp_result}")
        end_time = time.perf_counter()
        duration = (end_time - start_time) * 1000

        if hasattr(mcp_result, "error_message") and mcp_result.error_message:
            logging.error(f"execute_supabase_sql: MCP tool returned an error: {mcp_result.error_message}")
            return {"status": "error", "error": str(mcp_result.error_message)}
        
        if hasattr(mcp_result, "content") and mcp_result.content and hasattr(mcp_result.content[0], "text"):
            text_response = mcp_result.content[0].text

            try:
                extracted_data = extract_untrusted_json(text_response)
                # Detect error envelope returned as JSON
                try:
                    text_json = json.loads(text_response.strip('"')) if isinstance(text_response, str) else None
                except Exception:
                    text_json = None
                if isinstance(text_json, dict) and text_json.get("error"):
                    logging.error(f"execute_supabase_sql: Database returned error: {text_json['error']}")
                    return {"status": "error", "error": text_json["error"]}

                if extracted_data is not None:
                    logging.info(f"execute_supabase_sql: Query executed successfully. Duration: {duration:.2f}ms. SQL: {sql[:50]}...")
                    if isinstance(extracted_data, list):
                        return {"status": "success", "data": extracted_data}
                    else:
                        return {"status": "success", "data": [extracted_data]}
                else:
                    logging.info(f"execute_supabase_sql: Query executed successfully (no rows). Duration: {duration:.2f}ms. SQL: {sql[:50]}...")
                    return {"status": "success", "data": []}
            except json.JSONDecodeError:
                logging.error(f"execute_supabase_sql: Failed to parse MCP response as JSON. Response text: {text_response}")
                return {"status": "error", "error": "Failed to parse database response.", "details": text_response}

        logging.error(f"execute_supabase_sql: No content or unexpected format in MCP response: {mcp_result}")
        return {"status": "error", "error": "No content or unexpected format in database response."}

    except ValueError as ve:
        logging.error(f"execute_supabase_sql: Initialization error: {ve}")
        return {"status": "error", "error": str(ve)}
    except RuntimeError as rte:
        logging.error(f"execute_supabase_sql: Runtime error during MCP interaction: {rte}")
        return {"status": "error", "error": str(rte)}
    except Exception as e:
        logging.exception(f"execute_supabase_sql: Unexpected error executing SQL '{sql[:100]}...': {e}")
        return {"status": "error", "error": "An unexpected error occurred during SQL execution."}

def extract_untrusted_json(text_data: str) -> Optional[Any]:
    logging.debug(f"extract_untrusted_json: Extracting JSON from text: {text_data}...")

    # --- NEW STEP: Un-escape the input string if it's enclosed in quotes ---
    if text_data.startswith('"') and text_data.endswith('"'):
        try:
            # json.loads() will un-escape the newlines, quotes, etc.
            text_data = json.loads(text_data)
        except json.JSONDecodeError as e:
            logging.warning(f"extract_untrusted_json: Failed to un-escape JSON string. Error: {e}")
            return None
    
    # Now, the text_data string contains actual newlines and un-escaped quotes.
    # Your robust regex from before will work on this un-escaped string.
    pattern = r'<untrusted-data-.*?>\s*(\[.*\])\s*</untrusted-data-.*?>'

    match = re.search(pattern, text_data, re.DOTALL)

    if match:
        json_str = match.group(1).strip()
        
        try:
            # Return the parsed JSON
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logging.warning(f"extract_untrusted_json: JSON parsing failed for extracted string: '{json_str}'. Error: {e}")
            return None
    else:
        logging.debug(f"extract_untrusted_json: No JSON array or object found in text.")
        return None

def get_current_datetime() -> Dict[str, Any]:
    """
    Returns the current UTC date and time in ISO 8601 format.
    """
    logging.info(f"tool_name='get_current_datetime'")
    logging.debug("Entering get_current_datetime tool.")
    current_utc_datetime = datetime.datetime.now(datetime.timezone.utc)
    result = {"current_datetime_utc": current_utc_datetime.isoformat()}
    logging.debug(f"Exiting get_current_datetime tool. Result: {result}")
    return result


# async def main():
#     result = await execute_supabase_sql("SELECT * FROM users where email = 'kpuneeth714@gmail.com';")
# #     print(f"Result: {result}")

# asyncio.run(main())