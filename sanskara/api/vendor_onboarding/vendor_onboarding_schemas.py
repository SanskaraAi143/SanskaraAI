from pydantic import BaseModel, Field
from typing import List, Optional, Dict

# Reusable model for min/max pricing
class PricingRange(BaseModel):
    min: Optional[str] = None
    max: Optional[str] = None

class HallSeatingCapacity(BaseModel):
    theatre: Optional[int] = None
    roundTable: Optional[int] = None
    floating: Optional[int] = None

class HallDiningArrangement(BaseModel):
    has_separate_dining: Optional[bool] = None
    diningCapacity: Optional[int] = None

class HallStage(BaseModel):
    is_available: Optional[bool] = None
    dimensions: Optional[str] = None

class HallDanceFloor(BaseModel):
    is_available: Optional[bool] = None
    size: Optional[str] = None

class HallDetails(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None
    otherType: Optional[str] = None
    seatingCapacity: Optional[HallSeatingCapacity] = None
    diningArrangement: Optional[HallDiningArrangement] = None
    area_sq_ft: Optional[float] = None # Use a numerical type and clarify units
    airConditioning: Optional[str] = None
    stage: Optional[HallStage] = None
    danceFloor: Optional[HallDanceFloor] = None
    ambience: Optional[str] = None

class RentalCharges(BaseModel):
    weekday: Optional[float] = None
    weekend: Optional[float] = None
    festival: Optional[float] = None

class CateringPricing(BaseModel):
    vegStandard: Optional[PricingRange] = None
    vegDeluxe: Optional[PricingRange] = None
    nonVegStandard: Optional[PricingRange] = None
    nonVegDeluxe: Optional[PricingRange] = None

class OutsideCaterersDetails(BaseModel):
    tieUps: Optional[str] = None
    is_royalty_fee: Optional[bool] = None
    has_kitchen_access: Optional[bool] = None

class AlcoholCorkageFee(BaseModel):
    is_applicable: Optional[bool] = None
    amount: Optional[str] = None

class DecorPackages(BaseModel):
    priceRange: Optional[PricingRange] = None
    themes: Optional[str] = None

class ParkingDetails(BaseModel):
    cars: Optional[int] = None
    twoWheelers: Optional[int] = None
    is_valet_available: Optional[bool] = None
    valetCost: Optional[str] = None

class RoomDetails(BaseModel):
    total: Optional[int] = None
    ac: Optional[int] = None
    nonAc: Optional[int] = None
    is_complimentary: Optional[bool] = None
    extraCharges: Optional[str] = None
    amenities: Optional[List[str]] = Field(default_factory=list)

class PowerBackupDetails(BaseModel):
    capacity: Optional[str] = None # Can keep as string if units vary
    duration_hours: Optional[float] = None # Using float to support fractions of an hour

class AudioVisualDetails(BaseModel):
    has_sound_system: Optional[bool] = None
    is_sound_system_included: Optional[bool] = None
    has_projector: Optional[bool] = None
    is_projector_included: Optional[bool] = None
    djServices: Optional[str] = None
    djCost: Optional[str] = None

class WashroomDetails(BaseModel):
    number: Optional[int] = None
    description: Optional[str] = None

class AccessibilityDetails(BaseModel):
    has_wheelchair_access: Optional[bool] = None
    has_elevator: Optional[bool] = None

class EventStaffingDetails(BaseModel):
    staffCount: Optional[int] = None
    services: Optional[str] = None

class VendorOnboardingForm(BaseModel):
    # Basic Information
    venueName: Optional[str] = None
    fullAddress: Optional[str] = None
    contactPersonName: Optional[str] = None
    directPhoneNumbers: Optional[str] = None
    emailAddress: Optional[str] = None
    websiteLinks: Optional[str] = None
    yearsInOperation: Optional[int] = None
    
    # Hall Details
    halls: Optional[List[HallDetails]] = Field(default_factory=list)
    
    # Pricing & Packages
    is_rental_included_in_catering: Optional[bool] = None
    rentalCharges: Optional[RentalCharges] = None
    rentalDuration: Optional[List[str]] = Field(default_factory=list)
    hourlyRate: Optional[float] = None
    basicRentalIncludes: Optional[List[str]] = Field(default_factory=list)
    
    # Catering
    cateringOptions: Optional[str] = None
    outsideCaterersDetails: Optional[OutsideCaterersDetails] = None
    pricing: Optional[CateringPricing] = None
    cuisineSpecialties: Optional[List[str]] = Field(default_factory=list)
    menuCustomization: Optional[str] = None
    
    # Alcohol Policy
    is_alcohol_allowed: Optional[bool] = None
    has_in_house_bar: Optional[bool] = None
    is_permit_required: Optional[bool] = None
    corkageFee: Optional[AlcoholCorkageFee] = None
    
    # Decoration
    decorationOptions: Optional[str] = None
    outsideDecoratorRestrictions: Optional[str] = None
    is_basic_decor_included: Optional[bool] = None
    basicDecorDetails: Optional[str] = None
    decorPackages: Optional[DecorPackages] = None
    is_decor_customization: Optional[bool] = None
    popularThemes: Optional[str] = None
    
    # Taxes & Payment
    is_gst_applied: Optional[bool] = None
    gstPercentage: Optional[float] = None
    otherCharges: Optional[str] = None
    advanceBooking: Optional[str] = None
    paymentTerms: Optional[str] = None
    cancellationPolicy: Optional[str] = None
    paymentModes: Optional[List[str]] = Field(default_factory=list)
    
    # Amenities
    parking: Optional[ParkingDetails] = None
    rooms: Optional[RoomDetails] = None
    powerBackup: Optional[PowerBackupDetails] = None
    audioVisual: Optional[AudioVisualDetails] = None
    washrooms: Optional[WashroomDetails] = None
    accessibility: Optional[AccessibilityDetails] = None
    eventStaffing: Optional[EventStaffingDetails] = None
    is_wifi_available: Optional[bool] = None
    
    # Ritual & Cultural
    fireRitual: Optional[str] = None
    mandapSetup: Optional[str] = None
    
    # AI & Operational
    bookingSystem: Optional[str] = None
    is_integrate_with_app: Optional[bool] = None
    uniqueFeatures: Optional[str] = None
    idealClientProfile: Optional[str] = None
    flexibilityLevel: Optional[str] = None
    aiSuggestions: Optional[str] = None
    preferredLeadMode: Optional[str] = None
    venueRules: Optional[str] = None

