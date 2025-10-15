from fastapi import APIRouter, WebSocket
from api.vendor_onboarding.service import websocket_endpoint

vendor_onboarding_router = APIRouter()

@vendor_onboarding_router.websocket("/onboard")
async def vendor_onboard_ws(websocket: WebSocket):
    await websocket_endpoint(websocket)