import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import CORS_ORIGINS, DATABASE_URL, AGENTOPS_API_KEY
from pydantic import BaseModel
from typing import Dict
import asyncio
import sqlite3
from sanskara.db import astra_db
from sanskara.helpers import _supabase_mcp_toolset, _supabase_tools, execute_supabase_sql

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Sanskara AI Wedding Planner")

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Placeholder for router inclusion, will be updated later
# from .onboarding.routes import onboarding_router
# app.include_router(onboarding_router, prefix="/onboarding", tags=["Onboarding"])

class HealthCheckResult(BaseModel):
    status: str
    message: str = None

class OverallHealthStatus(BaseModel):
    status: str
    checks: Dict[str, HealthCheckResult]

@app.get("/health", response_model=OverallHealthStatus, tags=["Health"])
async def health_check():
    application_status = HealthCheckResult(status="ok", message="Application is running")

    astra_db_status, local_db_status, agentops_status, supabase_status = await asyncio.gather(
        check_astra_db_health(),
        check_local_db_health(),
        check_agentops_health(),
        check_supabase_db_health()
    )

    all_checks = {
        "application": application_status,
        "astra_db": astra_db_status,
        "local_db": local_db_status,
        "agentops": agentops_status,
        "supabase": supabase_status,
    }

    overall_status = "ok"
    if any(check.status == "unavailable" for check in all_checks.values()):
        overall_status = "unavailable"
    elif any(check.status == "degraded" for check in all_checks.values()):
        overall_status = "degraded"

    return OverallHealthStatus(
        status=overall_status,
        checks=all_checks
    )

async def check_astra_db_health() -> HealthCheckResult:
    try:
        if astra_db:
            # Perform a simple, non-destructive operation to verify connection
            # For Astrapy, you might try to list collections or get a collection by name
            # without actually creating or inserting data.
            # This example assumes a 'test_collection' exists or can be safely accessed.
            # A more robust check might involve a small read from a known collection.
            _ = astra_db.list_collection_names()
            return HealthCheckResult(status="ok", message="AstraDB connection successful")
        else:
            return HealthCheckResult(status="degraded", message="AstraDB client not initialized")
    except Exception as e:
        logger.error(f"AstraDB health check failed: {e}")
        return HealthCheckResult(status="unavailable", message=f"AstraDB connection failed: {e}")

async def check_local_db_health() -> HealthCheckResult:
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(DATABASE_URL.replace("sqlite:///", ""))
        cursor = conn.cursor()
        # Execute a simple query to check connectivity
        cursor.execute("SELECT 1")
        conn.close()
        return HealthCheckResult(status="ok", message="Local session database connection successful")
    except Exception as e:
        logger.error(f"Local session database health check failed: {e}")
        return HealthCheckResult(status="unavailable", message=f"Local session database connection failed: {e}")

async def check_agentops_health() -> HealthCheckResult:
    try:
        if AGENTOPS_API_KEY:
            # In a real scenario, you might make a small, non-authenticated API call
            # to AgentOps to verify connectivity. For simplicity, we'll check key presence.
            return HealthCheckResult(status="ok", message="AgentOps API key is configured")
        else:
            return HealthCheckResult(status="degraded", message="AgentOps API key not found")
    except Exception as e:
        logger.error(f"AgentOps health check failed: {e}")
        return HealthCheckResult(status="unavailable", message=f"AgentOps health check failed: {e}")

async def check_supabase_db_health() -> HealthCheckResult:
    try:
        # Check MCP toolset availability first
        if not ("execute_sql" in _supabase_tools):
            logger.error("Supabase MCP toolset or 'execute_sql' tool not available.")
            return HealthCheckResult(status="degraded", message="Supabase MCP toolset or execute_sql tool not available")

        # Then, perform a simple query to check database connectivity via MCP
        response = await execute_supabase_sql(sql="SELECT 1;")
        if response and response.get("status") == "success":
            return HealthCheckResult(status="ok", message="Supabase database and MCP toolset available")
        else:
            return HealthCheckResult(status="degraded", message=f"Supabase query failed via MCP: {response.get('error', 'Unknown error')}")
    except Exception as e:
        logger.error(f"Supabase health check failed: {e}")
        return HealthCheckResult(status="unavailable", message=f"Supabase health check failed: {e}")