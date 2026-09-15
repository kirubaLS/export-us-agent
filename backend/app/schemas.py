from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

# ---------------------------------------------------------------------------
# The Public/Internal split below is the load-bearing part of this file.
# It enforces Section 5's disclosure model in the type system rather than
# leaving it to a router author to remember: VendorPublic can never carry a
# contact field, no matter which endpoint constructs it.
# ---------------------------------------------------------------------------


class PriceTierOut(BaseModel):
    id: str
    qty_min: int
    qty_max: int | None
    price_low: float
    price_high: float | None
    currency: str
    incoterm: str
    port: str | None
    valid_until: datetime | None
    disclosure: str

    class Config:
        from_attributes = True


class VendorPublic(BaseModel):
    """Section 5.1 'Public — indexed' layer. No contact fields, ever."""

    id: str
    legal_name: str
    trade_name: str | None
    city: str | None
    state: str | None
    verification_tier: str
    claim_state: str
    response_rate: float | None
    median_response_hours: float | None

    class Config:
        from_attributes = True


class VendorContactReleased(BaseModel):
    """Section 5.1 'Released on enquiry' layer. Only ever returned by
    enquiries.release_contact, after the gate has actually been passed."""

    contact_name: str | None
    contact_email: str | None
    contact_phone: str | None


class ListingPublic(BaseModel):
    id: str
    vendor: VendorPublic
    title: str
    description: str
    specs: dict
    hts10: str | None
    taxonomy_path: str | None
    moq: int | None
    lead_time_days: int | None
    certifications: list
    images: list
    price_tiers: list[PriceTierOut]

    class Config:
        from_attributes = True


class ListingCreate(BaseModel):
    vendor_id: str
    title: str
    description: str
    specs: dict = Field(default_factory=dict)
    moq: int | None = None
    lead_time_days: int | None = None
    capacity_per_month: int | None = None
    certifications: list[str] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)


class PriceTierCreate(BaseModel):
    qty_min: int
    qty_max: int | None = None
    price_low: float
    price_high: float | None = None
    currency: str = "USD"
    incoterm: str = "FOB"
    port: str | None = None
    valid_until: datetime | None = None
    disclosure: str = "indicative"


class VendorCreate(BaseModel):
    legal_name: str
    trade_name: str | None = None
    country: str = "IN"
    state: str | None = None
    city: str | None = None
    iec: str | None = None
    gstin: str | None = None
    cin: str | None = None
    udyam: str | None = None


class VendorClaim(BaseModel):
    claimant_email: EmailStr
    contact_name: str
    contact_email: EmailStr
    contact_phone: str
    consent_publish_details: bool
    consent_contact_disclosure: bool


class BuyerRegister(BaseModel):
    company_name: str
    contact_name: str
    email: EmailStr
    phone: str | None = None
    country: str = "US"
    password: str


class BuyerLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class EnquiryCreate(BaseModel):
    vendor_id: str
    listing_id: str | None = None
    qty: int | None = None
    destination: str | None = None
    specification: str | None = None


class EnquiryOut(BaseModel):
    id: str
    vendor_id: str
    listing_id: str | None
    qty: int | None
    destination: str | None
    specification: str | None
    status: str
    contact_released_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class LandedCostRequest(BaseModel):
    hts10: str
    destination: str
    unit_price: float
    currency: str = "USD"
    origin: str = "IN"


class LandedCostComponent(BaseModel):
    label: str
    amount: float
    note: str
    sourced: bool


class LandedCostResponse(BaseModel):
    hts10: str
    origin: str
    destination: str
    unit_price: float
    components: list[LandedCostComponent]
    landed_total: float
    markup_pct: float
    partial: bool
    computed_at: datetime
    disclaimer: str = "Advisory only — not a binding classification ruling."


class ClassificationRequest(BaseModel):
    title: str
    description: str
    materials: str | None = None


class ClassificationResponse(BaseModel):
    hts10: str
    confidence: float
    reasoning: str
    requires_moderation: bool
