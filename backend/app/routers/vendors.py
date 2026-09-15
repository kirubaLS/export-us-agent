from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/vendors", tags=["vendors"])


@router.post("", response_model=schemas.VendorPublic, status_code=201)
def create_stub_vendor(payload: schemas.VendorCreate, db: Session = Depends(get_db)):
    """Publishes an unclaimed, registry-sourced stub page (Section 3.6,
    Table 11 STEP 3). No contact details are accepted here by design."""
    vendor = models.Vendor(**payload.model_dump())
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor


@router.get("", response_model=list[schemas.VendorPublic])
def list_vendors(city: str | None = None, verification_tier: str | None = None, db: Session = Depends(get_db)):
    q = db.query(models.Vendor)
    if city:
        q = q.filter(models.Vendor.city == city)
    if verification_tier:
        q = q.filter(models.Vendor.verification_tier == verification_tier)
    return q.limit(100).all()


@router.get("/{vendor_id}", response_model=schemas.VendorPublic)
def get_vendor(vendor_id: str, db: Session = Depends(get_db)):
    vendor = db.get(models.Vendor, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor


@router.post("/{vendor_id}/claim", status_code=202)
def claim_vendor(vendor_id: str, payload: schemas.VendorClaim, db: Session = Depends(get_db)):
    """Section 3.6 STEP 5 — vendor claims control, accepts terms and
    records DPDP consent *before* any contact field becomes gate-releasable
    (Section 10.2). This endpoint records a ClaimRequest for operator
    review; approval flips claim_state and writes the ConsentRecord."""
    vendor = db.get(models.Vendor, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    if not (payload.consent_publish_details and payload.consent_contact_disclosure):
        raise HTTPException(status_code=400, detail="Both consent flags are required to claim a profile")

    claim = models.ClaimRequest(
        vendor_id=vendor_id,
        claimant_email=payload.claimant_email,
        evidence={
            "contact_name": payload.contact_name,
            "contact_email": payload.contact_email,
            "contact_phone": payload.contact_phone,
        },
    )
    db.add(claim)
    vendor.claim_state = models.ClaimState.pending
    db.commit()
    return {"claim_request_id": claim.id, "status": "pending_review"}


@router.post("/claims/{claim_id}/approve", status_code=200)
def approve_claim(claim_id: str, db: Session = Depends(get_db)):
    """Operator action (Table 19 'Operations' role). Writes the consent
    record and only then copies contact details onto the vendor row —
    they remain gated at the API layer regardless (schemas.VendorPublic)."""
    claim = db.get(models.ClaimRequest, claim_id)
    if not claim or claim.status != "pending":
        raise HTTPException(status_code=404, detail="No pending claim with that id")

    vendor = db.get(models.Vendor, claim.vendor_id)
    consent = models.ConsentRecord(
        subject_type="vendor",
        subject_id=vendor.id,
        purpose="publish_business_details+contact_disclosure_on_enquiry",
    )
    db.add(consent)
    db.flush()

    vendor.claim_state = models.ClaimState.claimed
    vendor.contact_name = claim.evidence.get("contact_name")
    vendor.contact_email = claim.evidence.get("contact_email")
    vendor.contact_phone = claim.evidence.get("contact_phone")
    vendor.consent_record_id = consent.id
    claim.status = "approved"
    db.commit()
    return {"vendor_id": vendor.id, "claim_state": vendor.claim_state.value}
