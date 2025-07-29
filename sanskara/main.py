import uvicorn
from dotenv import load_dotenv
import os

from logger import json_logger as logger # Import the custom JSON logger
from api.app import app
from api.onboarding.routes import onboarding_router
from api.weddings.routes import weddings_router
from agent_websocket.service import websocket_endpoint

load_dotenv()

logger.info("Application starting up...") # Log application startup

# Include routers
app.include_router(onboarding_router, prefix="/onboarding", tags=["Onboarding"])
app.include_router(weddings_router, prefix="/weddings", tags=["Weddings"])

# Register WebSocket endpoint
app.websocket("/ws")(websocket_endpoint)

if __name__ == "__main__":
    with logger.contextualize(agent_name="OrchestratorAgent"):
        uvicorn.run(app, host="0.0.0.0", port=8765)
