from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.security import get_current_buyer

router = APIRouter(prefix="/enquiries", tags=["enquiries"])


@router.post("", response_model=schemas.EnquiryOut, status_code=201)
def create_enquiry(
    payload: schemas.EnquiryCreate,
    db: Session = Depends(get_db),
    buyer: models.Buyer = Depends(get_current_buyer),
):
    """Section 5 — the gate itself. Contact is never returned from this
    call; a registered buyer must submit a real enquiry, which is the
    monetisable event (Appendix A) and the DPDP disclosure trigger."""
    vendor = db.get(models.Vendor, payload.vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    enquiry = models.Enquiry(buyer_id=buyer.id, **payload.model_dump())
    db.add(enquiry)
    db.commit()
    db.refresh(enquiry)
    return enquiry


@router.post("/{enquiry_id}/release-contact", response_model=schemas.VendorContactReleased)
def release_contact(
    enquiry_id: str,
    db: Session = Depends(get_db),
    buyer: models.Buyer = Depends(get_current_buyer),
):
    """The only path by which contact details ever leave the platform.
    Requires: an authenticated buyer, an enquiry they themselves filed,
    and a vendor who has consented to disclosure (claim_state == claimed).
    Sets contact_released_at, which together with buyer.id *is* the DPDP
    consent/disclosure record referenced in Section 10.2."""
    enquiry = db.get(models.Enquiry, enquiry_id)
    if not enquiry or enquiry.buyer_id != buyer.id:
        raise HTTPException(status_code=404, detail="Enquiry not found")

    vendor = db.get(models.Vendor, enquiry.vendor_id)
    if vendor.claim_state == models.ClaimState.unclaimed:
        raise HTTPException(
            status_code=409,
            detail="This vendor has not claimed their profile and has not consented to contact disclosure yet",
        )

    enquiry.status = models.EnquiryStatus.contact_released
    enquiry.contact_released_at = datetime.utcnow()
    db.commit()

    return schemas.VendorContactReleased(
        contact_name=vendor.contact_name,
        contact_email=vendor.contact_email,
        contact_phone=vendor.contact_phone,
    )


@router.get("/mine", response_model=list[schemas.EnquiryOut])
def my_enquiries(db: Session = Depends(get_db), buyer: models.Buyer = Depends(get_current_buyer)):
    return db.query(models.Enquiry).filter(models.Enquiry.buyer_id == buyer.id).all()


@router.get("/vendor/{vendor_id}", response_model=list[schemas.EnquiryOut])
def vendor_inbox(vendor_id: str, db: Session = Depends(get_db)):
    """Table 19 vendor 'lead inbox' screen. Real deployments would scope
    this to an authenticated vendor-user session; omitted here to keep the
    auth surface to one role (buyer) for the MVP."""
    return db.query(models.Enquiry).filter(models.Enquiry.vendor_id == vendor_id).all()
