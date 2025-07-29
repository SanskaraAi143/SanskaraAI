from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import date

class WeddingDetailsResponse(BaseModel):
    wedding_id: str
    wedding_name: str
    wedding_date: date
    wedding_location: Optional[str] = None
    wedding_tradition: Optional[str] = None
    wedding_style: Optional[str] = None
    status: str
    details: Dict[str, Any]
    created_at: str
    updated_at: str

class WeddingUpdate(BaseModel):
    wedding_name: Optional[str] = None
    wedding_date: Optional[date] = None
    wedding_location: Optional[str] = None
    wedding_tradition: Optional[str] = None
    wedding_style: Optional[str] = None
    status: Optional[str] = None
    details: Optional[Dict[str, Any]] = None