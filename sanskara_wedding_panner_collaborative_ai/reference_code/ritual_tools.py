import logging
from typing import List, Dict, Any, Optional
from google.adk.tools import ToolContext # For type hinting context

# Import astra_db from the config location
from ..config import astra_db # Relative import
import json

# Configure logging for this module
logger = logging.getLogger(__name__)

async def search_rituals(question: str, tool_context: ToolContext, limit: int = 3):
    """
    Searches for rituals in Astra DB using vector search based on a question.

    Args:
        question (str): The user's query or question about rituals. Must be a non-empty string.
        limit (int): The maximum number of relevant documents to return. Defaults to 3. Must be positive.
        tool_context (ToolContext): The ADK ToolContext for state management.

    Returns:
        Dict[str, Any]:
            On success: `{"status": "success", "data": [document_1, document_2, ...]}` (list of documents)
            On failure: `{"status": "error", "error": "Error message"}`
            If AstraDB client not initialized: `{"status": "error", "error": "Astra DB client not initialized."}`
            If no rituals found: `{"status": "success", "data": [], "message": "No rituals found matching the query."}`

    Error Handling:
        - Validates `question` (non-empty string) and `limit` (positive integer).
        - Checks if `astra_db` client from config is initialized.
        - Catches exceptions during database interaction and returns a standardized error dict.
        - Logs errors and important actions.

    Dependencies:
        - `astra_db` client from `multi_agent_orchestrator.multi_agent_orchestrator.config`.
        - `astrapy` library for AstraDB interaction.

    Example Usage:
        ```python
        response = await search_rituals("Tell me about the Haldi ceremony.", limit=5, context=context)
        if response["status"] == "success":
            if response["data"]:
                for ritual_doc in response["data"]:
                    print(ritual_doc.get("name", "Unnamed Ritual")) # Assuming docs have a 'name' field
            else:
                print(response.get("message", "No rituals found."))
        else:
            print(f"Error searching rituals: {response['error']}")
        ```
    """
    if tool_context is None:
        logger.warning("search_rituals: ToolContext not provided. Caching will not be used.")

    cache_key = f"search_rituals:{question}:{limit}"
    if tool_context and cache_key in tool_context.state:
        logger.info(f"search_rituals: Returning cached data for question: '{question}', limit: {limit}")
        return {"status": "success", "data": tool_context.state[cache_key]}

    if not question or not isinstance(question, str):
        msg = "Invalid input: 'question' must be a non-empty string."
        logger.error(f"search_rituals: {msg}")
        return {"status": "error", "error": msg}
    if not isinstance(limit, int) or limit <= 0:
        msg = "Invalid input: 'limit' must be a positive integer."
        logger.error(f"search_rituals: {msg}")
        return {"status": "error", "error": msg}

    logger.info(f"search_rituals: Searching for rituals related to: '{question}', limit: {limit}")

    if astra_db is None:
        msg = "Astra DB client is not initialized. Check environment variables (ASTRA_API_TOKEN, ASTRA_API_ENDPOINT) and config."
        logger.error(f"search_rituals: {msg}")
        return {"status": "error", "error": msg}

    try:
        # Assuming 'ritual_data' is the correct collection name
        ritual_data_collection = astra_db.get_collection("ritual_data")

        # The query structure for DataStax AstraPy for vector search.
        # The `sort={"$vectorize": question}` implies the database handles vectorizing the query string.
        # `projection={"$vectorize": True}` was in the original; its exact utility here might
        # be to return the query vector or related metadata, which isn't typically the main data.
        # If documents have a text field that was vectorized (e.g., 'description_vector'),
        # the query might look different in some AstraPy versions or setups.
        # For now, sticking to the provided logic for the find call.
        results_cursor = ritual_data_collection.find(
            sort={"$vectorize": question},
            limit=limit
            # projection={"$vectorize": True} # Original had this. If not needed for result docs, can omit.
                                            # If you need specific fields, project them: e.g., {"name": 1, "description": 1}
        )

        # Standard AstraPy response structure is a dict, with actual documents often under data['documents']
        documents = []
        if results_cursor and isinstance(results_cursor, dict) and "data" in results_cursor:
            documents = results_cursor.get("data", {}).get("documents", [])

        if results_cursor and isinstance(results_cursor, dict) and results_cursor.get("errors"):
            # Handle specific Astra DB errors if provided in a structured way
            error_detail = results_cursor["errors"]
            logger.error(f"search_rituals: Astra DB query failed: {error_detail}")
            return {"status": "error", "error": f"Astra DB query failed: {error_detail}"}

        if not documents:
            logger.info(f"search_rituals: No rituals found for query: '{question}'")
            return {"status": "success", "data": [], "message": "No rituals found matching the query."}

        if tool_context:
            tool_context.state[cache_key] = documents # Cache the result
        logger.info(f"search_rituals: Successfully retrieved {len(documents)} ritual(s) for query: '{question}'. Cached: {bool(tool_context)}")
        return {"status": "success", "data": documents}

    except Exception as e:
        logger.exception(f"search_rituals: Unexpected error for query '{question}': {e}")
        # Mask potentially sensitive details from the raw exception in the return
        return {"status": "error", "error": "An unexpected error occurred during ritual search."}

# Keep the __main__ block for direct testing if desired, but ensure it uses the new signature
if __name__ == '__main__':
    import asyncio
    # This example requires .env to be in the parent of the parent of this file (project root)
    # and GOOGLE_API_KEY to be set if other parts of config are used by other imports.
    # For this specific tool, ASTRA_API_TOKEN and ASTRA_API_ENDPOINT are key.
    from dotenv import load_dotenv
    import os

    # Load .env from project root (two levels up from tools directory)
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    load_dotenv(dotenv_path=dotenv_path)
    print(f"Attempted to load .env from: {dotenv_path}")
    print(f"ASTRA_API_TOKEN set: {bool(os.getenv('ASTRA_API_TOKEN'))}")
    print(f"ASTRA_API_ENDPOINT set: {bool(os.getenv('ASTRA_API_ENDPOINT'))}")


    async def test_search():
        print("\nTesting ritual search tool...")

        test_question_valid = "What is Kanyadaan?"
        print(f"\nSearching for: '{test_question_valid}'")
        response_valid = await search_rituals(test_question_valid, limit=2, tool_context=ToolContext())
        print(f"Response: {json.dumps(response_valid, indent=2)}")

        test_question_empty = ""
        print(f"\nSearching for empty question: '{test_question_empty}'")
        response_empty = await search_rituals(test_question_empty, tool_context=ToolContext())
        print(f"Response: {json.dumps(response_empty, indent=2)}")

        test_question_no_results = "Tell me about alien wedding customs on Mars"
        print(f"\nSearching for: '{test_question_no_results}'")
        response_no_results = await search_rituals(test_question_no_results, context=ToolContext())
        print(f"Response: {json.dumps(response_no_results, indent=2)}")


    if astra_db: # Only run test if db client initialized
        asyncio.run(test_search())
    else:
        print("\nSkipping search_rituals test as AstraDB client is not initialized (check .env and config).")