from fastapi import APIRouter, HTTPException, status
from api.image_generation.schemas import GenerateVisualizationRequest, GenerateVisualizationResponse
from api.image_generation.service import generate_composite_image
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/generate-visualization", response_model=GenerateVisualizationResponse, tags=["Image Generation"])
async def generate_visualization_endpoint(request: GenerateVisualizationRequest):
    """
    Generates a photorealistic composite image by placing a user's photo (wearing a specific outfit)
    into a venue photo, guided by custom instructions.
    """
    logger.info(f"Received generate-visualization request for venue: {request.venueName}")
    
    success, image_data_uri, error_message = await generate_composite_image(
        venue_name=request.venueName,
        specific_area_data_uri=request.specificArea,
        user_photo_data_uri=request.userPhotoDataUri,
        outfit_photo_data_uri=request.outfitPhotoDataUri,
        custom_instructions=request.customInstructions
    )

    if success:
        logger.info("Image generation successful.")
        return GenerateVisualizationResponse(success=True, image=image_data_uri)
    else:
        logger.error(f"Image generation failed: {error_message}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_message
        )