import json
import os
import asyncio
import dotenv
import ast
import re
import logging
from typing import Optional, Any, Tuple, Dict
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters,StdioConnectionParams

logger = logging.getLogger(__name__)

dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env') # Updated path
if dotenv.load_dotenv(dotenv_path=dotenv_path):
    logger.info(f"helpers.py: Loaded .env from: {dotenv_path}")
else:
    if dotenv.load_dotenv():
        logger.info("helpers.py: Loaded .env from current directory or parent.")
    else:
        logger.warning("helpers.py: .env file not found. Critical environment variables might be missing.")


SUPABASE_ACCESS_TOKEN = os.getenv("SUPABASE_ACCESS_TOKEN")
SUPABASE_PROJECT_ID = os.getenv("SUPABASE_PROJECT_ID", "lylsxoupakajkuisjdfl")

_supabase_mcp_toolset: Optional[MCPToolset] = None
_supabase_tools: Optional[Dict[str, Any]] = None
_mcp_session: Optional[MCPToolset] = None

async def init_supabase_mcp() -> Tuple[Optional[MCPToolset], Optional[Dict[str, Any]]]:
    global _mcp_session, _supabase_mcp_toolset, _supabase_tools

    if _mcp_session is not None:
        logger.info("init_supabase_mcp: Closing existing MCP session.")
        await _mcp_session.close()
        _mcp_session = None # Clear the reference after closing

    logger.info("init_supabase_mcp: Attempting to initialize Supabase MCP toolset.")
    if not SUPABASE_ACCESS_TOKEN:
        logger.error("init_supabase_mcp: SUPABASE_ACCESS_TOKEN environment variable is not set.")
        raise ValueError("SUPABASE_ACCESS_TOKEN environment variable is not set.")

    try:
        connection_params=StdioServerParameters(
                command='/usr/bin/npx',
                args=["-y", "@supabase/mcp-server-supabase@latest", "--access-token", SUPABASE_ACCESS_TOKEN],
            )
        mcp= MCPToolset(
            connection_params=StdioConnectionParams(server_params=connection_params,timeout=20),tool_filter=["execute_sql"]
        )
        _mcp_session = mcp # Assign the new MCPToolset instance to _mcp_session
        tools = await mcp.get_tools()
        if not tools or "execute_sql" not in [tool.name for tool in tools]:
            logger.error("init_supabase_mcp: 'execute_sql' tool not found after MCP server connection.")
            raise RuntimeError("'execute_sql' tool not found in Supabase MCP server.")

        _supabase_mcp_toolset = mcp
        _supabase_tools = {tool.name: tool for tool in tools}
        logger.info("init_supabase_mcp: Supabase MCP toolset initialized successfully with 'execute_sql' tool.")

    except Exception as e:
        logger.exception(f"init_supabase_mcp: Failed to initialize Supabase MCP toolset: {e}")
        _supabase_mcp_toolset = None
        _supabase_tools = None
        _mcp_session = None # Ensure _mcp_session is also cleared on failure
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


async def execute_supabase_sql(sql: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    logger.debug(f"execute_supabase_sql: Received SQL: {sql}, Params: {params}")
    try:
        mcp_set, tools_map = await init_supabase_mcp()
        if not mcp_set or not tools_map:
             return {"status": "error", "error": "Supabase MCP toolset not available."}

        sql_tool = tools_map.get("execute_sql")
        if not sql_tool:
            return {"status": "error", "error": "Supabase MCP 'execute_sql' tool not found."}

        final_sql = sql
        if params:
            for k, v in params.items():
                placeholder = f":{k}"
                if placeholder not in final_sql:
                    logger.warning(f"execute_supabase_sql: Parameter key '{k}' as placeholder '{placeholder}' not found in SQL query. SQL: {sql}")
                final_sql = final_sql.replace(placeholder, sql_quote_value(v))

        mcp_args = {"query": final_sql, "project_id": SUPABASE_PROJECT_ID}
        logger.info(f"execute_supabase_sql: Executing with MCP args: {mcp_args}")

        mcp_result = await sql_tool.run_async(args=mcp_args, tool_context=None)
        logger.debug(f"execute_supabase_sql: Raw result from MCP: {mcp_result}")

        if hasattr(mcp_result, "error_message") and mcp_result.error_message:
            logger.error(f"execute_supabase_sql: MCP tool returned an error: {mcp_result.error_message}")
            return {"status": "error", "error": str(mcp_result.error_message)}
        
        if hasattr(mcp_result, "content") and mcp_result.content and hasattr(mcp_result.content[0], "text"):
            text_response = mcp_result.content[0].text

            try:
                extracted_data = extract_untrusted_json(text_response)
                if extracted_data is not None:
                    if isinstance(extracted_data, list):
                        return {"status": "success", "data": extracted_data}
                    else:
                        return {"status": "success", "data": [extracted_data]}
                else:
                    return {"status": "success", "data": []}
            except json.JSONDecodeError:
                logger.error(f"execute_supabase_sql: Failed to parse MCP response as JSON. Response text: {text_response}")
                return {"status": "error", "error": "Failed to parse database response.", "details": text_response}

        logger.error(f"execute_supabase_sql: No content or unexpected format in MCP response: {mcp_result}")
        return {"status": "error", "error": "No content or unexpected format in database response."}

    except ValueError as ve:
        logger.error(f"execute_supabase_sql: Initialization error: {ve}")
        return {"status": "error", "error": str(ve)}
    except RuntimeError as rte:
        logger.error(f"execute_supabase_sql: Runtime error during MCP interaction: {rte}")
        return {"status": "error", "error": str(rte)}
    except Exception as e:
        logger.exception(f"execute_supabase_sql: Unexpected error executing SQL '{sql[:100]}...': {e}")
        return {"status": "error", "error": "An unexpected error occurred during SQL execution."}

def extract_untrusted_json(text_data: str) -> Optional[Any]:
    print(f"extract_untrusted_json: Extracting JSON from text: {text_data}...")

    # --- NEW STEP: Un-escape the input string if it's enclosed in quotes ---
    if text_data.startswith('"') and text_data.endswith('"'):
        try:
            # json.loads() will un-escape the newlines, quotes, etc.
            text_data = json.loads(text_data)
        except json.JSONDecodeError as e:
            logger.warning(f"extract_untrusted_json: Failed to un-escape JSON string. Error: {e}")
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
            logger.warning(f"extract_untrusted_json: JSON parsing failed for extracted string: '{json_str}'. Error: {e}")
            return None
    else:
        logger.debug(f"extract_untrusted_json: No JSON array or object found in text.")
        return None

# async def main():
#     result = await execute_supabase_sql("SELECT * FROM users where email = 'kpuneeth714@gmail.com';")
# #     print(f"Result: {result}")

# asyncio.run(main())