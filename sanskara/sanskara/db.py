import os
from typing import Optional
from dotenv import load_dotenv
from astrapy import DataAPIClient
import logging # Import the custom JSON logger

# Load environment variables from .env file
load_dotenv()

# Astra DB setup
ASTRA_API_TOKEN = os.getenv("ASTRA_API_TOKEN")
ASTRA_API_ENDPOINT = os.getenv("ASTRA_API_ENDPOINT")

logging.info(f"ASTRA_API_ENDPOINT in config: {ASTRA_API_ENDPOINT}")

astra_client = None
astra_db = None

if ASTRA_API_TOKEN and ASTRA_API_ENDPOINT:
    try:
        astra_client = DataAPIClient(ASTRA_API_TOKEN)
        astra_db = astra_client.get_database_by_api_endpoint(ASTRA_API_ENDPOINT)
        logging.info("AstraDB client initialized.")
    except Exception as e:
        logging.error(f"Error initializing AstraDB client: {e}. astra_db will be None.")
else:
    logging.warning("ASTRA_API_TOKEN or ASTRA_API_ENDPOINT not found. AstraDB client not initialized.")