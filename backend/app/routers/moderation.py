from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app import models
from app.database import get_db

router = APIRouter(prefix="/moderation", tags=["moderation"])


@router.get("/queue")
def get_queue(db: Session = Depends(get_db)):
    items = (
        db.query(models.ModerationQueueItem)
        .options(joinedload(models.ModerationQueueItem.listing))
        .filter_by(resolved=False)
        .all()
    )
    return [
        {
            "id": i.id,
            "listing_id": i.listing_id,
            "listing_title": i.listing.title,
            "reason": i.reason,
            "flags": i.flags,
            "created_at": i.created_at,
        }
        for i in items
    ]


@router.get("/claims")
def get_pending_claims(db: Session = Depends(get_db)):
    claims = db.query(models.ClaimRequest).filter_by(status="pending").all()
    return [
        {"id": c.id, "vendor_id": c.vendor_id, "claimant_email": c.claimant_email, "created_at": c.created_at}
        for c in claims
    ]
