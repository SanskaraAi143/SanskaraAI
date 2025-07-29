import asyncio
import json
import websockets
import traceback
from websockets.exceptions import ConnectionClosed
from websockets.server import ServerConnection
from logger import json_logger as logger # Import the custom JSON logger

# Constants
PROJECT_ID = "sanskaraAI"
LOCATION = "us-central1"
MODEL = "gemini-1.5-flash"
VOICE_NAME = "Puck"
SEND_SAMPLE_RATE = 16000

SYSTEM_INSTRUCTION = "You are the Sanskara AI Wedding Planner."

class BaseWebSocketServer:
    def __init__(self, host="0.0.0.0", port=8765):
        self.host = host
        self.port = port
        self.active_clients = {}

    async def start(self):
        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
        async with websockets.serve(self.handle_client, self.host, self.port):
            await asyncio.Future()

    async def handle_client(self, websocket: ServerConnection, path):
        logger.info(f"New client connected: {websocket} , 'path': {path}")
        client_id = id(websocket)
        logger.info(f"New client connected: {client_id}")
        await websocket.send(json.dumps({"type": "ready"}))
        try:
            await self.process_audio(websocket, client_id)
        except ConnectionClosed:
            logger.info(f"Client disconnected: {client_id}")
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
            logger.error(traceback.format_exc())
        finally:
            if client_id in self.active_clients:
                del self.active_clients[client_id]

    async def process_audio(self, websocket, client_id):
        raise NotImplementedError("Subclasses must implement process_audio")
