from pydantic import BaseModel, Field
from typing import List, Optional

class VenuePhoto(BaseModel):
    data_uri: str = Field(..., description="Base64 Data URI of the venue photo")

class VenuePhotosResponse(BaseModel):
    success: bool
    photos: Optional[List[VenuePhoto]] = None
    error: Optional[str] = None