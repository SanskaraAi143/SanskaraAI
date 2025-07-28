import uvicorn
from dotenv import load_dotenv
import logging
import os

from api.app import app
from api.onboarding.routes import onboarding_router
from agent_websocket.service import websocket_endpoint

load_dotenv()

# Configure logging for main.py (if needed, otherwise app.py will handle it)
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Include routers
app.include_router(onboarding_router, prefix="/onboarding", tags=["Onboarding"])

# Register WebSocket endpoint
app.websocket("/ws")(websocket_endpoint)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8765)
