from typing import List, Dict, Any, Optional
from unittest import result
 # Import the tool decorator

# Import astra_db from the new db.py
from sanskara.db import astra_db
import json
from logger import json_logger as logger


from typing import Union, List, Dict, Any, Optional # Add Union to imports

async def get_ritual_information(query: str, limit: int = 3) -> Union[str, List[Dict[str, Any]]]:
    """
    Retrieves information about rituals from a knowledge base.
    This tool is designed to search for and provide details on various wedding traditions and customs.

    Args:
        query (str): The user's query or question about rituals (e.g., "significance of saptapadi").
                     Must be a non-empty string.
        limit (int): The maximum number of results to return (default: 3).
                     Must be a positive integer.

    Returns:
        Union[str, List[Dict[str, Any]]]: A list of dictionaries containing the retrieved ritual information.
             Returns a string error message if the query fails or input is invalid.
             Returns an empty list if no relevant information is found.

    Error Handling:
        - Validates `query` (non-empty string).
        - Validates `limit` (positive integer).
        - Checks if `astra_db` client from config is initialized.
        - Catches exceptions during database interaction and returns a standardized error message.
        - Logs errors and important actions.

    Dependencies:
        - `astra_db` client from `sanskara.db`.
        - `astrapy` library for AstraDB interaction.

    Example Usage:
        ```python
        # Example 1: Search for general ritual information
        info = await get_ritual_information("What is the significance of the Haldi ceremony?")
        logger.info(info)
        ```
    """
    with logger.contextualize(query=query):
        logger.debug(f"Attempting to retrieve ritual information for query: '{query}'")
        if not query or not isinstance(query, str):
            msg = "Invalid input: 'query' must be a non-empty string."
            logger.error(f"get_ritual_information: {msg}")
            return f"Error: {msg}"
        
        if not isinstance(limit, int) or limit <= 0:
            msg = "Invalid input: 'limit' must be a positive integer."
            logger.error(f"get_ritual_information: {msg}")
            return f"Error: {msg}"

        if astra_db is None:
            msg = "Astra DB client is not initialized. Check environment variables (ASTRA_API_TOKEN, ASTRA_API_ENDPOINT) and config."
            logger.error(f"get_ritual_information: {msg}")
            return f"Error: {msg}"

        try:
            ritual_data_collection = astra_db.get_collection("ritual_data")
            
            # Build the find query
            find_query = {"$vectorize": query}
            results_cursor = ritual_data_collection.find(
                projection={"$vectorize": True, "content": True, "description": True}, # Request content and description
                sort=find_query,
                limit=limit # Use the provided limit
            )
           
            ritual_info = []
            for doc in results_cursor:
                    ritual_info.append(doc)

            if not ritual_info:
                logger.info(f"get_ritual_information: No relevant ritual information found for query: '{query}'")
                return [] # Return an empty list if no relevant results found
            return ritual_info

        except Exception as e:
            logger.error(f"get_ritual_information: Unexpected error for query '{query}': {e}", exc_info=True)
            return "An unexpected error occurred during ritual information retrieval."

if __name__ == "__main__":
    # Example usage of the get_ritual_information function
    import asyncio

    async def main():
        # Example 1: General query
        response1 = await get_ritual_information("kanyadhanam")
        logger.info("\n--- General Query ---")
        logger.info(response1)

     

    asyncio.run(main())