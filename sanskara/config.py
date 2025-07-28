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

# CORS Origins
CORS_ORIGINS = [
    "http://localhost",
    "http://localhost:8080",
    "http://127.0.0.1",
    "http://127.0.0.1:8030",
    "https://sanskaraai.com",
    "null",
]