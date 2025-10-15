from fastapi import APIRouter, HTTPException, status, Query
from api.venue_photos.schemas import VenuePhotosResponse
from api.venue_photos.service import get_venue_photos_data_uris
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/venue-photos", response_model=VenuePhotosResponse, tags=["Venue Photos"])
async def get_venue_photos_endpoint(
    place_id: str = Query(..., description="The Google Place ID of the venue."),
    max_width: int = Query(800, description="Maximum width of the photo."),
    max_height: int = Query(600, description="Maximum height of the photo."),
    frontend_origin: str = Query("http://localhost:8030", description="Origin of the frontend for Referer header.")
):
    """
    Retrieves venue photos from Google Places API, converts them to Base64 Data URIs,
    and returns them.
    """
    logger.info(f"Received request for venue photos for place_id: {place_id}")
    
    success, photos, error_message = await get_venue_photos_data_uris(
        place_id=place_id,
        max_width=max_width,
        max_height=max_height,
        frontend_origin=frontend_origin
    )

    if success:
        logger.info(f"Successfully retrieved {len(photos) if photos else 0} venue photos for place_id: {place_id}")
        return VenuePhotosResponse(success=True, photos=photos)
    else:
        logger.error(f"Failed to retrieve venue photos for place_id {place_id}: {error_message}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_message
        )