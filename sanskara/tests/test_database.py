import pytest
from logger import logger
import os
from unittest.mock import AsyncMock, MagicMock, patch
from sanskara.helpers import  init_supabase_mcp, execute_supabase_sql, _supabase_mcp_toolset, _supabase_tools,extract_untrusted_json

import dotenv # Added import

# Mock environment variables for testing
@pytest.fixture(autouse=True)
def mock_env_vars():
    with patch.dict(os.environ, {"SUPABASE_ACCESS_TOKEN": "mock_token", "SUPABASE_PROJECT_ID": "mock_project_id"}):
        yield

# Reset the global variables before each test
@pytest.fixture(autouse=True)
def reset_supabase_globals():
    global _supabase_mcp_toolset, _supabase_tools
    _supabase_mcp_toolset = None
    _supabase_tools = None
    yield


@pytest.mark.asyncio
async def test_execute_supabase_sql_real_connection():
    # This test requires actual SUPABASE_ACCESS_TOKEN and SUPABASE_PROJECT_ID
    # to be set in the environment for a live Supabase instance.
    # It will attempt to connect and execute a simple query.
    try:
        result = await execute_supabase_sql("SELECT COUNT(*) FROM users;")
        logger.info(f"Real connection test result: {result}")
        assert "status" not in result or result["status"] == "success"
        assert isinstance(result, dict)  and "count" in result['data'][0] 
    except Exception as e:
        pytest.fail(f"Real Supabase connection test failed: {e}")
