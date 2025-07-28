import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import CORS_ORIGINS

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