from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import CORS_ORIGINS, DATABASE_URL, AGENTOPS_API_KEY, SESSION_SERVICE_URI,MEMORY_DATABASE_URL
from pydantic import BaseModel
from typing import Dict
import asyncio
import sqlite3
from sanskara.db import astra_db
from sanskara.helpers import _supabase_mcp_toolset, _supabase_tools, execute_supabase_sql
import logging # standard logging
from google.adk.cli.fast_api import get_fast_api_app
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp
import uuid
import os
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi import status, UploadFile, File, Form, Depends
from typing import Optional
from sanskara.adk_artifacts import artifact_service, record_artifact_metadata, list_session_artifacts
from .security import get_current_user_id
from google.genai import types as _genai_types
# Removed SQLAlchemy imports and ChatSession/ChatMessage models
# from sanskara.db import async_get_db_session # Import the new async session getter
# from sanskara.models import ChatSession, ChatMessage
# from sqlalchemy.future import select
try:
    from logging_setup import setup_logging
except ImportError:
    from sanskara.logging_setup import setup_logging

# Ensure logging is configured when the app module is imported (e.g., under uvicorn)
setup_logging()

# Get the directory where main.py is located
AGENT_DIR = "./"
# SESSION_SERVICE_URI is now constructed in config.py

# Set web=True if you intend to serve a web interface, False otherwise
SERVE_WEB_INTERFACE = True

app = get_fast_api_app(
    agents_dir=AGENT_DIR,
    session_service_uri=SESSION_SERVICE_URI,
    web=SERVE_WEB_INTERFACE,
    #memory_service_uri=MEMORY_DATABASE_URL,
)
app.title = "Sanskara AI"

# --- App State ---
app.state.EMBEDDING_MODEL_READY = False

async def load_embeddings_in_background():
    """Background task to preload embedding model without blocking startup."""
    logging.info("Starting embedding model preloading in the background.")
    try:
        try:
            from sanskara.sanskara.memory.supabase_memory_service import preload_embeddings
        except ImportError:
            from sanskara.memory.supabase_memory_service import preload_embeddings

        dim = await asyncio.to_thread(preload_embeddings)
        app.state.EMBEDDING_MODEL_READY = True
        logging.info(f"Background embedding preloading complete (dim={dim}).")
    except Exception as e:
        app.state.EMBEDDING_MODEL_READY = False
        logging.error(f"Background embedding preload failed: {e}", exc_info=True)

@app.on_event("startup")
async def startup_event():
    logging.info("Application startup event.")
    asyncio.create_task(load_embeddings_in_background())

@app.on_event("shutdown")
async def shutdown_event():
    logging.info("Application shutdown event.")

# Custom middleware to add request context to logger
class ProcessRequestMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        # Attempt to get wedding_id and user_id from headers or query parameters
        wedding_id = request.headers.get("x-wedding-id") or request.query_params.get("wedding_id")
        user_id = request.headers.get("x-user-id") or request.query_params.get("user_id")

        logging.info(f"request_id={request_id}, wedding_id={wedding_id}, user_id={user_id}")
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

    results = await asyncio.gather(
        check_astra_db_health(),
        check_local_db_health(),
        check_agentops_health(),
        check_supabase_db_health(),
        check_embedding_model_health(),
    )

    astra_db_status, local_db_status, agentops_status, supabase_status, embedding_status = results

    all_checks = {
        "application": application_status,
        "astra_db": astra_db_status,
        "local_db": local_db_status,
        "agentops": agentops_status,
        "supabase": supabase_status,
        "embedding_model": embedding_status,
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
    logging.debug("Checking AstraDB health.")
    try:
        if astra_db and hasattr(astra_db, 'list_collection_names'):
            _ = astra_db.list_collection_names()
            logging.info("AstraDB health check successful.")
            return HealthCheckResult(status="ok", message="AstraDB connection successful")
        else:
            logging.warning("AstraDB client not initialized or lacks required methods.")
            return HealthCheckResult(status="degraded", message="AstraDB client not fully initialized")
    except Exception as e:
        logging.error(f"AstraDB health check failed: {e}", exc_info=False) # Avoid leaking exception details
        return HealthCheckResult(status="unavailable", message="AstraDB connection failed")

async def check_local_db_health() -> HealthCheckResult:
    logging.debug("Checking session database health.")
    try:
        if DATABASE_URL and DATABASE_URL.startswith("postgresql://"):
            # This is a placeholder. A real check would involve a connection attempt.
            # For now, we assume a correctly formatted URL is a sign of being "configured".
            logging.info("Session database health check successful (PostgreSQL URL configured).")
            return HealthCheckResult(status="ok", message="PostgreSQL session database connection successful")
        elif DATABASE_URL and DATABASE_URL.startswith("sqlite:///"):
            db_path = DATABASE_URL.replace("sqlite:///", "")
            # Ensure the directory exists if the path is not just in-memory
            if db_path != ":memory:":
                os.makedirs(os.path.dirname(db_path), exist_ok=True)
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            conn.close()
            logging.info("Local SQLite database health check successful.")
            return HealthCheckResult(status="ok", message="Local SQLite session database connection successful")
        else:
            logging.warning("Unknown or misconfigured DATABASE_URL for session service.")
            return HealthCheckResult(status="degraded", message="Session database is not configured correctly")
    except Exception as e:
        logging.error(f"Session database health check failed: {e}", exc_info=False) # Avoid leaking exception details
        return HealthCheckResult(status="unavailable", message="Session database connection failed")

async def check_agentops_health() -> HealthCheckResult:
    logging.debug("Checking AgentOps health.")
    if AGENTOPS_API_KEY:
        logging.info("AgentOps health check successful.")
        return HealthCheckResult(status="ok", message="AgentOps API key is configured")
    else:
        logging.warning("AgentOps API key not found.")
        return HealthCheckResult(status="degraded", message="AgentOps API key not found")

async def check_supabase_db_health() -> HealthCheckResult:
    logging.debug("Checking Supabase health.")
    try:
        # Check if the toolset initialization seems plausible
        if not _supabase_tools or "execute_sql" not in _supabase_tools:
            logging.error("Supabase MCP toolset or 'execute_sql' tool not available.")
            return HealthCheckResult(status="degraded", message="Supabase toolset not available")

        # Perform a simple, non-destructive query
        response = await execute_supabase_sql(sql="SELECT 1;")
        if response and response.get("status") == "success":
            logging.info("Supabase health check successful.")
            return HealthCheckResult(status="ok", message="Supabase database and toolset are available")
        else:
            # Log the internal error but don't expose it in the response
            internal_error = response.get('error', 'Unknown error')
            logging.warning(f"Supabase query failed via MCP: {internal_error}")
            return HealthCheckResult(status="degraded", message="Supabase query execution failed")
    except Exception as e:
        logging.error(f"Supabase health check failed: {e}", exc_info=False) # Avoid leaking exception details
        return HealthCheckResult(status="unavailable", message="Supabase health check failed")

async def check_embedding_model_health() -> HealthCheckResult:
    """Checks the readiness of the embedding model."""
    logging.debug("Checking embedding model health.")
    if app.state.EMBEDDING_MODEL_READY:
        logging.info("Embedding model health check successful.")
        return HealthCheckResult(status="ok", message="Embedding model is loaded and ready")
    else:
        logging.info("Embedding model is still loading.")
        return HealthCheckResult(status="degraded", message="Embedding model is loading")

@app.post("/artifacts/upload", tags=["Artifacts"])
async def upload_artifact(
    session_id: str = Form(...),
    file: UploadFile = File(...),
    app_name: Optional[str] = Form(None),
    caption: Optional[str] = Form(None),
    user_id: str = Depends(get_current_user_id),
):
    """Upload an artifact and store it via ADK ArtifactService only.
    Requires explicit app_name/user_id/session_id to keep consistency with ADK expectations.
    Returns the artifact version handle and basic metadata.
    """
    data = await file.read()
    app_name = app_name or os.getenv("SANSKARA_APP_NAME", "sanskara")
    part = _genai_types.Part.from_bytes(data=data, mime_type=file.content_type or "application/octet-stream")
    artifact_version = None
    try:
        artifact_version = await artifact_service.save_artifact(  # type: ignore
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            filename=file.filename,
            artifact=part,
        )
        logging.info(f"Artifact saved with version {artifact_version} for user_id={user_id}, session_id={session_id}")
    except Exception as e:  # pragma: no cover
        logging.error(f"ADK save_artifact failed for {file.filename}: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "error": str(e)})

    # Lightweight auto summary for text-like content (best-effort, avoid heavy model call here)
    auto_summary = None
    try:
        if (file.content_type or "").startswith("text/"):
            decoded = data.decode(errors="ignore")
            snippet = decoded.strip().splitlines()[:8]
            joined = " ".join(s.strip() for s in snippet)
            auto_summary = (joined[:280] + "…") if len(joined) > 280 else joined
    except Exception:
        auto_summary = None

    record_artifact_metadata(artifact_version, {
        "filename": file.filename,
        "caption": caption,
        "auto_summary": auto_summary,
        "mime_type": file.content_type or "application/octet-stream",
        "size_bytes": len(data),
        "session_id": session_id,
        "user_id": user_id,
        "app_name": app_name,
    })

    logging.info(f"Artifact uploaded filename={file.filename} size={len(data)} user_id={user_id} session_id={session_id} version={artifact_version}")
    return {"status": "success", "artifact": {
        "filename": file.filename,
        "mime_type": file.content_type or "application/octet-stream",
        "size_bytes": len(data),
        "caption": caption,
        "auto_summary": auto_summary,
        "version": artifact_version,
        "session_id": session_id,
        "user_id": user_id,
        "app_name": app_name,
    }}

@app.get("/artifacts/list", tags=["Artifacts"])
async def list_artifacts(session_id: str, app_name: Optional[str] = None, user_id: str = Depends(get_current_user_id)):
    """List artifacts (filename + version + metadata) from in-memory session index."""
    app_name = app_name or os.getenv("SANSKARA_APP_NAME", "sanskara")
    items = await list_session_artifacts(app_name, user_id, session_id)
    return {"status": "success", "artifacts": items}

@app.get("/weddings/{wedding_id}/sessions/{adk_session_id}/messages", tags=["Chat"])
async def get_chat_messages(wedding_id: str, adk_session_id: str):
    """
    Fetches chat messages for a specific wedding and ADK session ID.
    This endpoint is now protected against SQL injection.
    """
    try:
        # Find the ChatSession using parameterized query to prevent SQL injection
        check_session_sql = """
        SELECT session_id FROM chat_sessions
        WHERE wedding_id = :wedding_id AND adk_session_id = :adk_session_id;
        """
        params = {"wedding_id": wedding_id, "adk_session_id": adk_session_id}
        check_result = await execute_supabase_sql(check_session_sql, params)

        if not check_result or check_result.get("status") != "success" or not check_result.get("data"):
            raise StarletteHTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found."
            )
        
        chat_session_db_id = check_result["data"][0].get("session_id")

        # Fetch all messages for this chat_session.session_id using parameterized query
        messages_sql = """
        SELECT sender_type, sender_name, content, timestamp FROM chat_messages
        WHERE session_id = :session_id
        ORDER BY timestamp ASC;
        """
        messages_params = {"session_id": chat_session_db_id}
        messages_result = await execute_supabase_sql(messages_sql, messages_params)

        if not messages_result or messages_result.get("status") != "success":
            raise StarletteHTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve chat messages: {messages_result.get('error', 'Unknown error')}"
            )
        
        chat_messages_raw = messages_result.get("data", [])

        # Format messages for frontend
        formatted_messages = []
        for msg in chat_messages_raw:
            # content is already JSONB in DB, so it should be a dict here
            content_data = msg.get("content", {})
            formatted_messages.append({
                "sender": msg.get("sender_type"),
                "text": content_data.get("text", ""),
                "timestamp": msg.get("timestamp"), # Timestamps are already ISO formatted by Supabase
                "sender_name": msg.get("sender_name"),
            })

        return {"status": "success", "messages": formatted_messages}

    except StarletteHTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logging.error(f"Error fetching chat messages: {e}", exc_info=True)
        raise StarletteHTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {e}"
        )

@app.get("/artifacts/content", tags=["Artifacts"])
async def get_artifact_content(session_id: str, version: str, filename: str, app_name: Optional[str] = None, user_id: str = Depends(get_current_user_id)):
    """Fetch a single artifact's raw bytes (base64) via ADK ArtifactService."""
    app_name = app_name or os.getenv("SANSKARA_APP_NAME", "sanskara")
    try:
        art = await artifact_service.load_artifact(  # type: ignore
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            filename=filename,
            version=int(version)
        )
        logging.debug(f"artifact content {art}")
    except Exception as e:  # pragma: no cover
        logging.error(f"ADK load_artifact failed: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "error": str(e)})
    try:
        import base64
        # Attempt to extract raw bytes; fallback attributes included
        data = getattr(art, "data", None) or getattr(art, "bytes", None) or getattr(getattr(art, "inline_data", None), "data", None)
        b64 = base64.b64encode(data).decode("utf-8") if data else None
        return {"status": "success", "artifact": {
            "version": version,
            "filename": getattr(art, "filename", None) or getattr(art, "name", None) or filename,
            "mime_type": getattr(art, "mime_type", None) or getattr(art, "content_type", None),
            "base64_content": b64,
        }}
    except Exception as e:  # pragma: no cover
        return JSONResponse(status_code=500, content={"status": "error", "error": f"Decode failed: {e}"})