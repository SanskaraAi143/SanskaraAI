# Ritual Search Agent Utility (Astra DB)
from astrapy import DataAPIClient
from typing import List, Dict, Any
import os
import dotenv
dotenv.load_dotenv()  # Load environment variables from .env file

ASTRA_API_TOKEN = os.environ.get("ASTRA_API_TOKEN")
ASTRA_API_ENDPOINT = os.environ.get("ASTRA_API_ENDPOINT")

client = DataAPIClient(ASTRA_API_TOKEN)
db = client.get_database_by_api_endpoint(ASTRA_API_ENDPOINT)


def search_rituals(question: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Search rituals in Astra DB using vector search for a given question.
    Returns top_k most relevant documents.
    """
    ritual_data = db.get_collection("ritual_data")
    result = ritual_data.find(
        projection={"$vectorize": True},
        sort={"$vectorize": question},
    )
    contexts = []
    for doc in result:
        if len(contexts) >= top_k:
            break
        contexts.append(doc)
    return contexts

# Example usage (for testing):
if __name__ == "__main__":
    results = search_rituals("Describe the Haldi ceremony")
    for ritual in results:
        print(ritual)
