from pydantic import BaseModel, Field
from typing import Optional

class GenerateVisualizationRequest(BaseModel):
    venueName: str
    specificArea: str = Field(..., description="Data URI of the venue photo")
    userPhotoDataUri: str = Field(..., description="Data URI of the user's photo")
    outfitPhotoDataUri: str = Field(..., description="Data URI of the outfit photo")
    customInstructions: Optional[str] = Field(None, description="Optional user instructions for fitting or placement")

class GenerateVisualizationResponse(BaseModel):
    success: bool
    image: Optional[str] = None
    error: Optional[str] = None