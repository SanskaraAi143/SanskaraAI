from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import date

class TeamworkPlan(BaseModel):
    """Defines the structure for the teamwork and responsibilities section."""
    venue_decor: str
    catering: str
    guest_list: str
    sangeet_entertainment: str

class WeddingDetails(BaseModel):
    wedding_name: str
    wedding_date: date
    wedding_location: Optional[str] = None
    wedding_tradition: Optional[str] = None
    wedding_style: Optional[str] = None

class CurrentUserOnboardingDetails(BaseModel):
    """
    Represents the detailed information collected from the current user filling out the form.
    This corresponds to the 'current_user_onboarding_details' object in the payload.
    """
    name: str
    email: str
    phone: Optional[str] = None
    role: str  # "Bride" or "Groom"
    cultural_background: str
    ceremonies: List[str] = []
    custom_instructions: Optional[str] = None
    teamwork_plan: TeamworkPlan
    guest_estimate: Optional[str] = None
    guest_split: Optional[str] = None
    budget_range: Optional[str] = None
    budget_flexibility: str
    priorities: List[str] = []

class PartnerOnboardingDetails(BaseModel):
    """
    Represents the initial contact information for the second partner, provided by the first partner.
    """
    name: str
    email: str

class SecondPartnerDetails(BaseModel):
    """The focused details provided ONLY by the second partner."""
    name: str
    email: str
    role: str
    cultural_background: str
    ceremonies: List[str] = []
    budget_range: Optional[str] = None
    priorities: List[str] = []
    teamwork_agreement: bool # The crucial consensus flag

class OnboardingSubmission(BaseModel):
    wedding_details: WeddingDetails
    current_user_onboarding_details: CurrentUserOnboardingDetails
    partner_onboarding_details: PartnerOnboardingDetails

class SecondPartnerSubmission(BaseModel):
    wedding_id: str
    current_partner_details: SecondPartnerDetails