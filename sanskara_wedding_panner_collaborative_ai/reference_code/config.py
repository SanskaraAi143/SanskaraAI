# Utility for loading environment variables and credentials
from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from .env file
#load_dotenv("FutureBackend/.env")  # Load environment variables from .env file

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
ASTRA_DB_ID = os.getenv("ASTRA_DB_ID")
ASTRA_DB_REGION = os.getenv("ASTRA_DB_REGION")
ASTRA_DB_APPLICATION_TOKEN = os.getenv("ASTRA_DB_APPLICATION_TOKEN")

# Add more as needed for Google ADK, etc.

# Astra DB and Supabase connection utilities
from typing import Optional # Import Optional
from astrapy import DataAPIClient
from supabase import create_client, Client

# Astra DB setup
ASTRA_API_TOKEN = os.getenv("ASTRA_API_TOKEN")
ASTRA_API_ENDPOINT = os.getenv("ASTRA_API_ENDPOINT")

print(f"ASTRA_API_ENDPOINT in config: {ASTRA_API_ENDPOINT}") # More specific print

astra_client = None
astra_db = None

if ASTRA_API_TOKEN and ASTRA_API_ENDPOINT:
    try:
        astra_client = DataAPIClient(ASTRA_API_TOKEN)
        astra_db = astra_client.get_database_by_api_endpoint(ASTRA_API_ENDPOINT)
        print("AstraDB client initialized.")
    except Exception as e:
        print(f"Error initializing AstraDB client: {e}. astra_db will be None.")
else:
    print("ASTRA_API_TOKEN or ASTRA_API_ENDPOINT not found. AstraDB client not initialized.")


# Supabase setup (using correct URL and key, no DATABASE_URL needed)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Optional[Client] = None # Initialize as None

if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("Supabase client initialized.")
    except Exception as e:
        print(f"Error initializing Supabase client: {e}. supabase client will be None.")
else:
    print("SUPABASE_URL or SUPABASE_KEY not found. Supabase client not initialized.")

# ToolContext for ADK tools (if needed)
# tool_context = ToolContext()  # Removed: requires invocation_context, not needed for connection setup

# Add more utility functions as needed for CRUD, search, etc.
# Example: def get_user(user_id): ...
# Example: def search_rituals(query): ...
