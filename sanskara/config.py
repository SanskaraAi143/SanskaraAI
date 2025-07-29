import os

# Application Constants
MODEL = "gemini-1.5-flash"
VOICE_NAME = "Puck"
SEND_SAMPLE_RATE = 16000
SYSTEM_INSTRUCTION = "You are the Sanskara AI Wedding Planner."

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///sessions.db")

# AgentOps Configuration
AGENTOPS_API_KEY = os.getenv("AGENTOPS_API_KEY")

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_TO_FILE = os.getenv("LOG_TO_FILE", "false").lower() == "true"
LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "app.log")

# CORS Origins
CORS_ORIGINS = [
    "http://localhost",
    "http://localhost:8030",
    "http://127.0.0.1",
    "http://127.0.0.1:8030",
    "https://sanskaraai.com",
    "null",
]