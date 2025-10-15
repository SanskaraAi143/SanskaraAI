from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class StaffGenericAttributes(BaseModel):
    food_options: Optional[str] = None # Could be JSON string or text
    pricing_details: Optional[str] = None
    service_type: Optional[str] = None
    # Add other dynamic attributes as they appear in frontend's genericAttributes

class StaffOnboardingForm(BaseModel):
    name: Optional[str] = None # Combined name from frontend
    role: Optional[str] = None
    portfolioTitle: Optional[str] = None
    portfolioDescription: Optional[str] = None
    portfolioType: Optional[str] = None
    genericAttributes: Optional[StaffGenericAttributes] = Field(default_factory=StaffGenericAttributes)
    # imageUrls and videoUrls are handled separately by TaggedImageUploader,
    # so they are not part of the direct GenAI extraction schema for form fields.
    # If GenAI needs to extract tags or info about images/videos,
    # a separate model would be needed or these fields would be structured differently.