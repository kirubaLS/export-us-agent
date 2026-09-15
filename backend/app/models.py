import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def uid() -> str:
    return str(uuid.uuid4())


class ClaimState(str, enum.Enum):
    unclaimed = "unclaimed"
    pending = "pending"
    claimed = "claimed"


class VerificationTier(str, enum.Enum):
    listed = "listed"
    claimed = "claimed"
    verified = "verified"
    trade_proven = "trade_proven"
    audited = "audited"


class ListingState(str, enum.Enum):
    draft = "draft"
    pending = "pending"
    live = "live"
    suspended = "suspended"


class Incoterm(str, enum.Enum):
    EXW = "EXW"
    FOB = "FOB"
    CIF = "CIF"
    DDP = "DDP"


class PriceDisclosure(str, enum.Enum):
    published = "published"
    indicative = "indicative"
    on_request = "on_request"


class EnquiryStatus(str, enum.Enum):
    new = "new"
    contact_released = "contact_released"
    responded = "responded"
    closed = "closed"


class Corridor(str, enum.Enum):
    india_to_usa = "india_to_usa"
    usa_to_india = "usa_to_india"


class Vendor(Base):
    """One row per legal entity. Public-vs-gated split lives at the
    listing/enquiry layer, not here -- a Vendor row itself holds only
    factual, registry-sourced data plus consent state (Section 5, 10.2)."""

    __tablename__ = "vendors"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    legal_name: Mapped[str] = mapped_column(String, nullable=False)
    trade_name: Mapped[str | None] = mapped_column(String)
    country: Mapped[str] = mapped_column(String, default="IN")
    state: Mapped[str | None] = mapped_column(String)
    city: Mapped[str | None] = mapped_column(String)

    # Registry identifiers (Section 3.2, Appendix A)
    iec: Mapped[str | None] = mapped_column(String, index=True)
    gstin: Mapped[str | None] = mapped_column(String, index=True)
    cin: Mapped[str | None] = mapped_column(String)
    udyam: Mapped[str | None] = mapped_column(String)

    claim_state: Mapped[ClaimState] = mapped_column(
        Enum(ClaimState), default=ClaimState.unclaimed
    )
    verification_tier: Mapped[VerificationTier] = mapped_column(
        Enum(VerificationTier), default=VerificationTier.listed
    )

    # Computed/denormalized, shown publicly (Table 19, Table 35)
    response_rate: Mapped[float | None] = mapped_column(Numeric(5, 2))
    median_response_hours: Mapped[float | None] = mapped_column(Numeric(8, 2))

    # DPDP consent basis for any contact disclosure (Section 10.2)
    consent_record_id: Mapped[str | None] = mapped_column(
        ForeignKey("consent_records.id")
    )

    # Contact fields -- personal/sensitive, never selected into public
    # responses. See app/schemas.py VendorPublic vs VendorInternal.
    contact_name: Mapped[str | None] = mapped_column(String)
    contact_email: Mapped[str | None] = mapped_column(String)
    contact_phone: Mapped[str | None] = mapped_column(String)
    contact_public_opt_in: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    verifications: Mapped[list["Verification"]] = relationship(back_populates="vendor")
    listings: Mapped[list["Listing"]] = relationship(back_populates="vendor")
    shipment_signals: Mapped[list["ShipmentSignal"]] = relationship(
        back_populates="vendor"
    )


class Verification(Base):
    """Append-only. Never updated in place -- a re-check inserts a new
    row and the vendor's tier is *derived* from the latest non-expired
    result per check_type (Table 22)."""

    __tablename__ = "verifications"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    vendor_id: Mapped[str] = mapped_column(ForeignKey("vendors.id"), nullable=False)
    check_type: Mapped[str] = mapped_column(String, nullable=False)  # iec|gstin|mca|udyam|sanctions
    source: Mapped[str] = mapped_column(String, nullable=False)
    result: Mapped[str] = mapped_column(String, nullable=False)  # pass|fail|expired
    evidence_url: Mapped[str | None] = mapped_column(String)
    checked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)

    vendor: Mapped[Vendor] = relationship(back_populates="verifications")


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    vendor_id: Mapped[str] = mapped_column(ForeignKey("vendors.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    specs: Mapped[dict] = mapped_column(JSON, default=dict)

    # AI-assigned tariff classification, moderated (Section 9.1)
    hts10: Mapped[str | None] = mapped_column(String, index=True)
    hts_confidence: Mapped[float | None] = mapped_column(Numeric(4, 3))
    hts_reasoning: Mapped[str | None] = mapped_column(Text)

    taxonomy_path: Mapped[str | None] = mapped_column(String)  # human browse taxonomy
    moq: Mapped[int | None] = mapped_column(Integer)
    lead_time_days: Mapped[int | None] = mapped_column(Integer)
    capacity_per_month: Mapped[int | None] = mapped_column(Integer)
    certifications: Mapped[list] = mapped_column(JSON, default=list)
    images: Mapped[list] = mapped_column(JSON, default=list)

    state: Mapped[ListingState] = mapped_column(Enum(ListingState), default=ListingState.draft)
    embedding: Mapped[list | None] = mapped_column(JSON)  # pgvector in prod; JSON fallback

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    vendor: Mapped[Vendor] = relationship(back_populates="listings")
    price_tiers: Mapped[list["PriceTier"]] = relationship(
        back_populates="listing", cascade="all, delete-orphan"
    )


class PriceTier(Base):
    """Many per listing -- never a single price field (Section 4, Table 13/14).
    A listing without a PriceTier row must still resolve to a derived
    category range at read time (see services/pricing.py); it is never
    rendered as an empty price (Table 15)."""

    __tablename__ = "price_tiers"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    listing_id: Mapped[str] = mapped_column(ForeignKey("listings.id"), nullable=False)
    qty_min: Mapped[int] = mapped_column(Integer, nullable=False)
    qty_max: Mapped[int | None] = mapped_column(Integer)
    price_low: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)
    price_high: Mapped[float | None] = mapped_column(Numeric(14, 4))
    currency: Mapped[str] = mapped_column(String, default="USD")
    incoterm: Mapped[Incoterm] = mapped_column(Enum(Incoterm), default=Incoterm.FOB)
    port: Mapped[str | None] = mapped_column(String)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime)
    disclosure: Mapped[PriceDisclosure] = mapped_column(
        Enum(PriceDisclosure), default=PriceDisclosure.indicative
    )

    listing: Mapped[Listing] = relationship(back_populates="price_tiers")


class LandedCostEstimate(Base):
    """Cached by (hts10, origin, destination) -- the expensive duty-research
    half of the Export-to-Entry Agent is shared across every listing under
    the same classification (Section 4.3, 9.2)."""

    __tablename__ = "landed_cost_estimates"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    hts10: Mapped[str] = mapped_column(String, nullable=False, index=True)
    origin: Mapped[str] = mapped_column(String, default="IN")
    destination: Mapped[str] = mapped_column(String, nullable=False)
    components: Mapped[dict] = mapped_column(JSON, nullable=False)  # duty/freight/fees breakdown
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    partial: Mapped[bool] = mapped_column(Boolean, default=False)


class ShipmentSignal(Base):
    """Derived from trade data -- powers the trade-proven badge and the
    supply-acquisition prospect ranking (Section 3.1, Table 22)."""

    __tablename__ = "shipment_signals"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    vendor_id: Mapped[str] = mapped_column(ForeignKey("vendors.id"), nullable=False)
    hts6: Mapped[str] = mapped_column(String, nullable=False)
    destination: Mapped[str] = mapped_column(String, nullable=False)
    period: Mapped[str] = mapped_column(String, nullable=False)  # e.g. "2026-Q2"
    shipment_count: Mapped[int] = mapped_column(Integer, default=0)
    value_band: Mapped[str | None] = mapped_column(String)

    vendor: Mapped[Vendor] = relationship(back_populates="shipment_signals")


class Buyer(Base):
    __tablename__ = "buyers"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    company_name: Mapped[str] = mapped_column(String, nullable=False)
    contact_name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    phone: Mapped[str | None] = mapped_column(String)
    country: Mapped[str] = mapped_column(String, default="US")
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Enquiry(Base):
    """THE monetisable event (Appendix A). contact_released_at is set the
    moment gated contact details are disclosed to this buyer for this
    vendor -- that timestamp plus the buyer identity is the DPDP
    disclosure record (Section 10.2)."""

    __tablename__ = "enquiries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    buyer_id: Mapped[str] = mapped_column(ForeignKey("buyers.id"), nullable=False)
    vendor_id: Mapped[str] = mapped_column(ForeignKey("vendors.id"), nullable=False)
    listing_id: Mapped[str | None] = mapped_column(ForeignKey("listings.id"))
    qty: Mapped[int | None] = mapped_column(Integer)
    destination: Mapped[str | None] = mapped_column(String)
    specification: Mapped[str | None] = mapped_column(Text)
    status: Mapped[EnquiryStatus] = mapped_column(
        Enum(EnquiryStatus), default=EnquiryStatus.new
    )
    contact_released_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MessageThread(Base):
    __tablename__ = "message_threads"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    enquiry_id: Mapped[str] = mapped_column(ForeignKey("enquiries.id"), nullable=False)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    thread_id: Mapped[str] = mapped_column(ForeignKey("message_threads.id"), nullable=False)
    sender_type: Mapped[str] = mapped_column(String, nullable=False)  # buyer|vendor
    sender_id: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    attachments: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ConsentRecord(Base):
    __tablename__ = "consent_records"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    subject_type: Mapped[str] = mapped_column(String, nullable=False)  # vendor|buyer
    subject_id: Mapped[str] = mapped_column(String, nullable=False)
    purpose: Mapped[str] = mapped_column(String, nullable=False)
    granted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime)


class ModerationQueueItem(Base):
    __tablename__ = "moderation_queue"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    listing_id: Mapped[str] = mapped_column(ForeignKey("listings.id"), nullable=False)
    reason: Mapped[str] = mapped_column(String, nullable=False)
    flags: Mapped[dict] = mapped_column(JSON, default=dict)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    listing: Mapped["Listing"] = relationship()


class ClaimRequest(Base):
    __tablename__ = "claim_requests"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    vendor_id: Mapped[str] = mapped_column(ForeignKey("vendors.id"), nullable=False)
    claimant_email: Mapped[str] = mapped_column(String, nullable=False)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String, default="pending")  # pending|approved|rejected
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
