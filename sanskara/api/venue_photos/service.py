import base64
import mimetypes
import os
import logging
from typing import List, Dict, Any, Optional, Tuple
import requests
from config import GOOGLE_MAPS_API_KEY

logger = logging.getLogger(__name__)

def download_image_as_data_uri(url: str, frontend_origin: str = "http://localhost:8030") -> str:
    """
    Downloads an image from a URL and converts it to a Base64 Data URI.
    Includes an IMPORTANT Referer header for Google Places API.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36",
        "Referer": frontend_origin
    }
    
    try:
        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status()

        content_type = response.headers.get("Content-Type")
        if not content_type:
            content_type, _ = mimetypes.guess_type(url)
            if not content_type:
                content_type = "application/octet-stream"

        image_data = response.content
        base64_encoded_data = base64.b64encode(image_data).decode('utf-8')
        return f"data:{content_type};base64,{base64_encoded_data}"

    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading image from {url}: {e}")
        raise ValueError(f"Failed to download image from URL: {url}") from e
    except Exception as e:
        logger.exception(f"An unexpected error occurred while downloading image from {url}")
        raise

async def get_venue_photos_data_uris(
    place_id: str, 
    max_width: int = 800, 
    max_height: int = 600,
    frontend_origin: str = "http://localhost:8030" # Default for Referer header
) -> Tuple[bool, Optional[List[Dict[str, str]]], Optional[str]]:
    """
    Fetches venue photos from Google Places API, downloads them, and converts them
    to Base64 Data URIs.
    """
    if not GOOGLE_MAPS_API_KEY:
        return False, None, "Google Maps API key not configured."

    # Step 1: Get Place Details to retrieve photo references
    place_details_url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=photo&key={GOOGLE_MAPS_API_KEY}"
    
    try:
        details_response = requests.get(place_details_url)
        details_response.raise_for_status()
        details_data = details_response.json()

        if details_data.get("status") != "OK":
            error_msg = details_data.get("error_message", "Failed to get place details")
            logger.error(f"Google Places API error for place_id {place_id}: {error_msg}")
            return False, None, error_msg

        photos_data = details_data["result"].get("photos", [])
        
        venue_photos_data_uris = []
        for photo in photos_data[:4]: # Limit to first 4 photos
            photo_reference = photo["photo_reference"]
            # Construct the photo URL
            photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth={max_width}&maxheight={max_height}&photoreference={photo_reference}&key={GOOGLE_MAPS_API_KEY}"
            
            # Download and convert to data URI
            try:
                data_uri = download_image_as_data_uri(photo_url, frontend_origin) 
                venue_photos_data_uris.append({"data_uri": data_uri})
            except ValueError as e:
                logger.warning(f"Could not convert photo {photo_reference} to data URI: {e}")
                # Continue to next photo if one fails
            except Exception as e:
                logger.exception(f"Unexpected error processing photo {photo_reference}")
                # Continue to next photo if one fails

        return True, venue_photos_data_uris, None

    except requests.exceptions.RequestException as e:
        logger.error(f"Backend failed to fetch place details for place_id {place_id}: {e}")
        return False, None, f"Failed to fetch place details: {e}"
    except Exception as e:
        logger.exception(f"An unexpected error occurred while fetching venue photos for place_id {place_id}")
        return False, None, f"An unexpected error occurred: {e}"