import uvicorn
from dotenv import load_dotenv
import os
from arize.otel import register

# Load env first so we can read ARIZE_* variables
load_dotenv()

ARIZE_SPACE_ID = os.getenv("ARIZE_SPACE_ID")
ARIZE_API_KEY = os.getenv("ARIZE_API_KEY")
ARIZE_PROJECT_NAME = os.getenv("ARIZE_PROJECT_NAME", "SanskaraAI")

tracer_provider = None
if ARIZE_SPACE_ID and ARIZE_API_KEY:
    try:
        tracer_provider = register(
            space_id=ARIZE_SPACE_ID,
            api_key=ARIZE_API_KEY,
            project_name=ARIZE_PROJECT_NAME,
        )
    except Exception as e:  # pragma: no cover
        # Fallback: continue without tracing if registration fails
        from logger import json_logger as _tmp_logger
        _tmp_logger.warning(f"Arize tracing disabled (registration failed): {e}")
else:
    from logger import json_logger as _tmp_logger
    _tmp_logger.warning("Arize tracing disabled (ARIZE_SPACE_ID / ARIZE_API_KEY not set)")

# Import and configure the automatic instrumentor from OpenInference
from openinference.instrumentation.google_adk import GoogleADKInstrumentor

# Finish automatic instrumentation
GoogleADKInstrumentor().instrument(tracer_provider=tracer_provider)
import nest_asyncio
nest_asyncio.apply()


from logger import json_logger as logger # Import the custom JSON logger
from api.app import app
from api.onboarding.routes import onboarding_router
from api.weddings.routes import weddings_router
from agent_websocket.service import websocket_endpoint

import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
# AGENTOPS_API_KEY = os.getenv("AGENTOPS_API_KEY")
# agentops.init(
#     api_key=AGENTOPS_API_KEY,
#     default_tags=['google adk']
# )

logger.info("Application starting up...") # Log application startup

# Include routers
app.include_router(onboarding_router, prefix="/onboarding", tags=["Onboarding"])
app.include_router(weddings_router, prefix="/weddings", tags=["Weddings"])

# Register WebSocket endpoint
app.websocket("/ws")(websocket_endpoint)

if __name__ == "__main__":
    with logger.contextualize(agent_name="OrchestratorAgent"):
        uvicorn.run(app, host="0.0.0.0", port=8765)
