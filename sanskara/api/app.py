from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import CORS_ORIGINS, DATABASE_URL, AGENTOPS_API_KEY
from pydantic import BaseModel
from typing import Dict
import asyncio
import sqlite3
from sanskara.db import astra_db
from sanskara.helpers import _supabase_mcp_toolset, _supabase_tools, execute_supabase_sql
from logger import json_logger as logger # Import the custom JSON logger
from google.adk.cli.fast_api import get_fast_api_app
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp
import uuid
import os

# Get the directory where main.py is located
AGENT_DIR = "./"
# Example session service URI (e.g., SQLite)
SESSION_SERVICE_URI = "sqlite:///./sessions.db"

# Set web=True if you intend to serve a web interface, False otherwise
SERVE_WEB_INTERFACE = True

app = get_fast_api_app(agents_dir=AGENT_DIR,session_service_uri=SESSION_SERVICE_URI,web=SERVE_WEB_INTERFACE)
app.title = "Sanskara AI"

@app.on_event("startup")
async def startup_event():
    logger.info("Application startup event.")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutdown event.")

# Custom middleware to add request context to logger
class ProcessRequestMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        # Attempt to get wedding_id and user_id from headers or query parameters
        wedding_id = request.headers.get("x-wedding-id") or request.query_params.get("wedding_id")
        user_id = request.headers.get("x-user-id") or request.query_params.get("user_id")

        with logger.contextualize(request_id=request_id, wedding_id=wedding_id, user_id=user_id):
            response = await call_next(request)
        return response

app.add_middleware(ProcessRequestMiddleware)

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
    logger.debug("Checking AstraDB health.")
    try:
        if astra_db:
            # Perform a simple, non-destructive operation to verify connection
            # For Astrapy, you might try to list collections or get a collection by name
            # without actually creating or inserting data.
            # This example assumes a 'test_collection' exists or can be safely accessed.
            # A more robust check might involve a small read from a known collection.
            _ = astra_db.list_collection_names()
            logger.info("AstraDB health check successful.")
            return HealthCheckResult(status="ok", message="AstraDB connection successful")
        else:
            logger.warning("AstraDB client not initialized.")
            return HealthCheckResult(status="degraded", message="AstraDB client not initialized")
    except Exception as e:
        logger.error(f"AstraDB health check failed: {e}", exc_info=True)
        return HealthCheckResult(status="unavailable", message=f"AstraDB connection failed: {e}")

async def check_local_db_health() -> HealthCheckResult:
    logger.debug("Checking local database health.")
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(DATABASE_URL.replace("sqlite:///", ""))
        cursor = conn.cursor()
        # Execute a simple query to check connectivity
        cursor.execute("SELECT 1")
        conn.close()
        logger.info("Local database health check successful.")
        return HealthCheckResult(status="ok", message="Local session database connection successful")
    except Exception as e:
        logger.error(f"Local session database health check failed: {e}", exc_info=True)
        return HealthCheckResult(status="unavailable", message=f"Local session database connection failed: {e}")

async def check_agentops_health() -> HealthCheckResult:
    logger.debug("Checking AgentOps health.")
    try:
        if AGENTOPS_API_KEY:
            # In a real scenario, you might make a small, non-authenticated API call
            # to AgentOps to verify connectivity. For simplicity, we'll check key presence.
            logger.info("AgentOps health check successful.")
            return HealthCheckResult(status="ok", message="AgentOps API key is configured")
        else:
            logger.warning("AgentOps API key not found.")
            return HealthCheckResult(status="degraded", message="AgentOps API key not found")
    except Exception as e:
        logger.error(f"AgentOps health check failed: {e}", exc_info=True)
        return HealthCheckResult(status="unavailable", message=f"AgentOps health check failed: {e}")

async def check_supabase_db_health() -> HealthCheckResult:
    logger.debug("Checking Supabase health.")
    try:
        # Check MCP toolset availability first
        if not ("execute_sql" in _supabase_tools):
            logger.error("Supabase MCP toolset or 'execute_sql' tool not available.")
            return HealthCheckResult(status="degraded", message="Supabase MCP toolset or execute_sql tool not available")

        # Then, perform a simple query to check database connectivity via MCP
        response = await execute_supabase_sql(sql="SELECT 1;")
        if response and response.get("status") == "success":
            logger.info("Supabase health check successful.")
            return HealthCheckResult(status="ok", message="Supabase database and MCP toolset available")
        else:
            logger.warning(f"Supabase query failed via MCP: {response.get('error', 'Unknown error')}")
            return HealthCheckResult(status="degraded", message=f"Supabase query failed via MCP: {response.get('error', 'Unknown error')}")
    except Exception as e:
        logger.error(f"Supabase health check failed: {e}", exc_info=True)
        return HealthCheckResult(status="unavailable", message=f"Supabase health check failed: {e}")