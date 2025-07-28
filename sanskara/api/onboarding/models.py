from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import date

class TeamworkPlan(BaseModel):
    """Defines the structure for the teamwork and responsibilities section."""
    venue_decor: str
    catering: str
    guest_list: str
    sangeet_entertainment: str

class PartnerDetails(BaseModel):
    """
    Represents the detailed information collected from the partner filling out the form.
    This corresponds to the 'current_partner_details' object in the payload.
    """
    # --- Step 1: Core Foundation ---
    name: str
    email: str
    phone: Optional[str] = None
    role: str  # "Bride" or "Groom"
    partner_name: str
    partner_email: str
    wedding_city: str
    wedding_date: date

    # --- Step 2: Vision & Vibe ---
    wedding_style: Optional[str] = None
    other_style: Optional[str] = None
    color_theme: Optional[str] = None
    attire_main: Optional[str] = None
    attire_other: Optional[str] = None

    # --- Step 3: Cultural Heartbeat ---
    cultural_background: str
    ceremonies: List[str] = []
    custom_instructions: Optional[str] = None

    # --- Step 4: Teamwork Plan ---
    teamwork_plan: TeamworkPlan

    # --- Step 5: Budget & Priorities ---
    guest_estimate: Optional[str] = None
    guest_split: Optional[str] = None
    budget_range: Optional[str] = None
    budget_flexibility: str
    priorities: List[str] = []

# MODEL 2: For the SECOND partner's submission (new and streamlined)
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
    current_partner_email: str
    other_partner_email: Optional[str] = None # Provided by the first partner
    current_partner_details: PartnerDetails

class SecondPartnerSubmission(BaseModel):
    current_partner_email: str
    current_partner_details: SecondPartnerDetails