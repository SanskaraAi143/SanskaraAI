from typing import List, Dict, Any, Optional
from unittest import result
# Import the tool decorator

# Import astra_db from the new db.py
from sanskara.db import astra_db
import json
import asyncio
import logging


from typing import Union, List, Dict, Any, Optional  # Add Union to imports


def _static_ritual_fallback(query: str, limit: int = 3) -> List[Dict[str, Any]]:
    """Return a small, safe static fallback for common rituals when DB is unavailable."""
    q = (query or "").lower()
    catalog: Dict[str, Dict[str, Any]] = {
        "saptapadi": {
            "title": "Saptapadi (Seven Steps)",
            "description": "The couple takes seven steps together around the sacred fire, each step representing a vow for shared life, prosperity, strength, family, health, virtues, and friendship.",
            "region": "Pan-Indian (varies by tradition)",
        },
        "haldi": {
            "title": "Haldi (Turmeric Ceremony)",
            "description": "A cleansing and blessing ritual where family applies turmeric paste for auspiciousness, radiance, and protection before the wedding.",
            "region": "Widespread across regions",
        },
        "mehendi": {
            "title": "Mehendi (Henna)",
            "description": "Application of intricate henna designs symbolizing joy, beauty, and auspicious beginnings; often accompanied by music and family celebrations.",
            "region": "Widespread across regions",
        },
        "kanyadaan": {
            "title": "Kanyadaan",
            "description": "A blessing ceremony where the bride’s parents ceremonially offer blessings and support for the new journey; interpretations vary by community.",
            "region": "Common in many North and some South Indian traditions",
        },
        "baraat": {
            "title": "Baraat (Groom’s Procession)",
            "description": "The groom arrives in a festive procession with music and dance, welcomed by the bride’s family at the venue entrance.",
            "region": "Prominent in North Indian weddings",
        },
        "mangal": {
            "title": "Mangalsutra/Thali Tying",
            "description": "The tying of a sacred thread or necklace signifying the marital bond; names and forms vary by region.",
            "region": "South and West Indian traditions",
        },
        "talambralu": {
            "title": "Talambralu",
            "description": "The couple showers each other with rice or turmeric-rice, symbolizing prosperity, playfulness, and abundance.",
            "region": "Telugu weddings",
        },
    }

    # Simple match heuristic
    hits: List[Dict[str, Any]] = []
    for key, val in catalog.items():
        if key in q:
            hits.append(val)
    if not hits:
        # Provide a generic outline if no keyword matched
        hits = [
            {
                "title": "Common Wedding Rituals Overview",
                "description": "Typical ceremonies include engagement, haldi, mehendi, sangeet, the main wedding rituals (like saptapadi or mangalsutra tying), and reception. Specific names and sequences vary by community and region.",
                "region": "Varies by tradition",
            }
        ]
    # Annotate with fallback metadata
    for h in hits:
        h.update({
            "source": "static_fallback",
            "confidence": "low",
            "note": "Service temporarily unavailable; returning a concise cultural summary.",
        })
    return hits[: max(1, min(limit, len(hits)))]


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
        logging.info(info)
        ```
    """
    logging.info(f"query={query}")
    logging.debug(f"Attempting to retrieve ritual information for query: '{query}'")
    if not query or not isinstance(query, str):
        msg = "Invalid input: 'query' must be a non-empty string."
        logging.error(f"get_ritual_information: {msg}")
        return f"Error: {msg}"
    
    if not isinstance(limit, int) or limit <= 0:
        msg = "Invalid input: 'limit' must be a positive integer."
        logging.error(f"get_ritual_information: {msg}")
        return f"Error: {msg}"

    if astra_db is None:
        msg = "Astra DB client is not initialized. Check environment variables (ASTRA_API_TOKEN, ASTRA_API_ENDPOINT) and config."
        logging.error(f"get_ritual_information: {msg}")
        return f"Error: {msg}"

    # Retry with exponential backoff for transient errors (e.g., 5xx/connection)
    attempts = 0
    base_delay = 0.5
    last_exc: Optional[Exception] = None
    while attempts < 3:
        try:
            ritual_data_collection = astra_db.get_collection("ritual_data")
            # Build the find query
            find_query = {"$vectorize": query}
            results_cursor = ritual_data_collection.find(
                projection={"$vectorize": True, "content": True, "description": True},  # Request content and description
                sort=find_query,
                limit=limit,  # Use the provided limit
            )

            ritual_info: List[Dict[str, Any]] = []
            for doc in results_cursor:
                ritual_info.append(doc)

            if not ritual_info:
                logging.info(
                    f"get_ritual_information: No relevant ritual information found for query: '{query}'"
                )
                return []  # Return an empty list if no relevant results found
            return ritual_info
        except Exception as e:
            last_exc = e
            attempts += 1
            # Classify likely transient errors by message hints
            msg = str(e)
            is_transient = any(hint in msg for hint in [
                "503", "502", "504", "Service Unavailable", "Timeout", "temporarily", "connection", "reset by peer"
            ])
            logging.warning(
                {
                    "event": "ritual_info_retry",
                    "attempt": attempts,
                    "transient": is_transient,
                    "error": msg,
                }
            )
            if attempts >= 3 or not is_transient:
                break
            await asyncio.sleep(base_delay * (2 ** (attempts - 1)))

    # Fallback path when DB is unavailable or non-transient error occurred
    logging.error(
        f"get_ritual_information: falling back to static data for query '{query}' due to error: {last_exc}",
        exc_info=False,
    )
    return _static_ritual_fallback(query, limit)

if __name__ == "__main__":
    # Example usage of the get_ritual_information function
    import asyncio

    async def main():
        # Example 1: General query
        response1 = await get_ritual_information("kanyadhanam")
        logging.info("\n--- General Query ---")
        logging.info(response1)

     

    asyncio.run(main())