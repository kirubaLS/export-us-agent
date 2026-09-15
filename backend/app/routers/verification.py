from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models
from app.database import get_db

router = APIRouter(prefix="/vendors/{vendor_id}/verification", tags=["verification"])

_TIER_ORDER = [
    models.VerificationTier.listed,
    models.VerificationTier.claimed,
    models.VerificationTier.verified,
    models.VerificationTier.trade_proven,
    models.VerificationTier.audited,
]


def _recompute_tier(db: Session, vendor: models.Vendor) -> None:
    """Table 22: badges are derived from current non-expired verifications,
    never set by hand."""
    now = datetime.utcnow()
    checks = {
        v.check_type
        for v in vendor.verifications
        if v.result == "pass" and (v.expires_at is None or v.expires_at > now)
    }

    if vendor.claim_state == models.ClaimState.claimed and {"iec", "gstin", "mca"} <= checks:
        vendor.verification_tier = models.VerificationTier.verified
    elif vendor.claim_state == models.ClaimState.claimed:
        vendor.verification_tier = models.VerificationTier.claimed
    else:
        vendor.verification_tier = models.VerificationTier.listed

    if "shipment_corroborated" in checks and vendor.verification_tier == models.VerificationTier.verified:
        vendor.verification_tier = models.VerificationTier.trade_proven

    if "audit" in checks and vendor.verification_tier == models.VerificationTier.trade_proven:
        vendor.verification_tier = models.VerificationTier.audited


@router.post("/run-check")
def run_check(vendor_id: str, check_type: str, db: Session = Depends(get_db)):
    """Stub KYB call standing in for the HyperVerge/Signzy/Karza bundle
    (Section 3.2, Appendix B). Real integration swaps the fixed 'pass'
    for the provider's response; the append-only Verification row and
    tier-recompute logic either side of it stay the same.

    A vendor failing a sanctions screen is suspended automatically, not
    flagged for review (Section 6.4) — enforced here rather than left to
    an operator to notice.
    """
    vendor = db.get(models.Vendor, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    result = "fail" if check_type == "sanctions" and vendor.legal_name.upper().startswith("BLOCKED") else "pass"

    verification = models.Verification(
        vendor_id=vendor_id,
        check_type=check_type,
        source="stub-kyb-provider",
        result=result,
        expires_at=datetime.utcnow() + timedelta(days=180),
    )
    db.add(verification)
    db.flush()

    if check_type == "sanctions" and result == "fail":
        vendor.claim_state = models.ClaimState.unclaimed
        vendor.verification_tier = models.VerificationTier.listed
        db.commit()
        return {"vendor_id": vendor_id, "check_type": check_type, "result": result, "action": "suspended"}

    db.refresh(vendor)
    _recompute_tier(db, vendor)
    db.commit()
    return {"vendor_id": vendor_id, "check_type": check_type, "result": result, "verification_tier": vendor.verification_tier.value}


@router.get("")
def list_checks(vendor_id: str, db: Session = Depends(get_db)):
    vendor = db.get(models.Vendor, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return [
        {
            "id": v.id,
            "check_type": v.check_type,
            "result": v.result,
            "checked_at": v.checked_at,
            "expires_at": v.expires_at,
        }
        for v in vendor.verifications
    ]
