import os
from dotenv import load_dotenv

# Load environment variables from a .env file if it exists
load_dotenv()

# --- Application Constants ---
MODEL = os.getenv("MODEL", "gemini-1.5-flash")
VOICE_NAME = os.getenv("VOICE_NAME", "Puck")
SEND_SAMPLE_RATE = int(os.getenv("SEND_SAMPLE_RATE", 16000))
SYSTEM_INSTRUCTION = os.getenv("SYSTEM_INSTRUCTION", "You are the Sanskara AI Wedding Planner.")

# --- Database Configuration ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
# This is often the DB password. For production, consider a more secure secret management approach.
SUPABASE_ACCESS_TOKEN = os.getenv("SUPABASE_ACCESS_TOKEN")

# --- Database Connection URLs ---
# Default to a local SQLite database for session management
DEFAULT_SESSION_SERVICE_URI = "sqlite:///sessions.db"
DEFAULT_DATABASE_URL = "sqlite:///sanskara.db"

# Initialize URLs with default values
SESSION_SERVICE_URI = DEFAULT_SESSION_SERVICE_URI
DATABASE_URL = DEFAULT_DATABASE_URL

# Use Supabase PostgreSQL if all required environment variables are set
if SUPABASE_URL and SUPABASE_ACCESS_TOKEN:
    try:
        # Extract host from SUPABASE_URL (e.g., lylsxoupakajkuisjdfl.supabase.co)
        supabase_host = SUPABASE_URL.split('@')[-1]

        # Construct the PostgreSQL connection string
        # Format: postgresql://[user]:[password]@[host]:[port]/[database_name]
        # Supabase typically uses 'postgres' as the user and the database name.
        pg_url = f"postgresql://postgres:{SUPABASE_ACCESS_TOKEN}@{supabase_host}"

        # Assign the constructed URL to both session service and main database
        SESSION_SERVICE_URI = pg_url
        DATABASE_URL = pg_url

    except (IndexError, TypeError) as e:
        print(f"Error parsing SUPABASE_URL: {e}. Falling back to SQLite.")
        SESSION_SERVICE_URI = DEFAULT_SESSION_SERVICE_URI
        DATABASE_URL = DEFAULT_DATABASE_URL
else:
    print("Supabase environment variables not fully set. Falling back to SQLite.")

# --- AgentOps Configuration ---
AGENTOPS_API_KEY = os.getenv("AGENTOPS_API_KEY")

# --- Logging Configuration ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_TO_FILE = os.getenv("LOG_TO_FILE", "false").lower() == "true"
LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "app.log")

# --- CORS Origins ---
# "null" origin has been removed to prevent security vulnerabilities (CSRF).
# It's safer to explicitly list allowed origins.
CORS_ORIGINS = [
    "http://localhost",
    "http://localhost:8030",
    "http://127.0.0.1",
    "http://127.0.0.1:8030",
    "https://sanskaraai.com",
]

# --- Caching Configuration ---
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_CACHE_ENABLED = os.getenv("REDIS_CACHE_ENABLED", "false").lower() == "true"

# --- Feature Flags ---
DISABLE_SEMANTIC_RECALL = os.getenv("DISABLE_SEMANTIC_RECALL", "0") == "1"