import os
import dotenv

# Load environment variables from .env file
dotenv.load_dotenv()

# Application Constants
MODEL = "gemini-1.5-flash"
VOICE_NAME = "Puck"
SEND_SAMPLE_RATE = 16000
SYSTEM_INSTRUCTION = "You are the Sanskara AI Wedding Planner."

# Database Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_ACCESS_TOKEN = os.getenv("SUPABASE_ACCESS_TOKEN") # This is often the DB password

# Construct the Supabase PostgreSQL connection string for ADK's DatabaseSessionService
# Format: postgresql://[user]:[password]@[host]:[port]/[database_name]
# Supabase typically uses 'postgres' as the user and 'postgres' as the database name.
# The host is derived from SUPABASE_URL.
MEMORY_DATABASE_URL=None
if SUPABASE_URL and SUPABASE_ACCESS_TOKEN:
    # Extract host from SUPABASE_URL (e.g., lylsxoupakajkuisjdfl.supabase.co)
    supabase_host = SUPABASE_URL.replace("https://", "").split("/")[0]
    MEMORY_DATABASE_URL = f"postgresql://postgres:{SUPABASE_ACCESS_TOKEN}@{supabase_host}:5432/postgres"
else:
    # Fallback to SQLite if Supabase details are not fully provided
    pass

# ADK's SESSION_SERVICE_URI expects a SQLAlchemy compatible URL.
# We will use the constructed DATABASE_URL directly for it.
SESSION_SERVICE_URI = "sqlite:///sessions.db"
DATABASE_URL = MEMORY_DATABASE_URL
# Google AI Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
# Google Maps Configuration
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY") # Using VITE prefix as per user's example
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
    "http://localhost:8080",
    "https://sanskaraai.com",
    "null",
]