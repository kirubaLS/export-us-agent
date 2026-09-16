from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.database import get_db
from app.services import semantic_search
from app.services.classification import classify
from app.services.pricing import ensure_never_empty

router = APIRouter(prefix="/listings", tags=["listings"])


@router.post("", status_code=201)
def create_listing(payload: schemas.ListingCreate, db: Session = Depends(get_db)):
    vendor = db.get(models.Vendor, payload.vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    listing = models.Listing(**payload.model_dump())
    db.add(listing)
    db.flush()

    result = classify(payload.title, payload.description, payload.specs.get("materials"))
    listing.hts10 = result["hts10"]
    listing.hts_confidence = result["confidence"]
    listing.hts_reasoning = result["reasoning"]

    if result["requires_moderation"]:
        db.add(
            models.ModerationQueueItem(
                listing_id=listing.id,
                reason="low_confidence_classification",
                flags={"confidence": result["confidence"]},
            )
        )
        listing.state = models.ListingState.pending
    else:
        listing.state = models.ListingState.pending  # every new listing still needs a human pass

    db.commit()
    db.refresh(listing)
    return {"listing_id": listing.id, "hts10": listing.hts10, "state": listing.state.value}


@router.post("/{listing_id}/price-tiers", status_code=201)
def add_price_tier(listing_id: str, payload: schemas.PriceTierCreate, db: Session = Depends(get_db)):
    listing = db.get(models.Listing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    tier = models.PriceTier(listing_id=listing_id, **payload.model_dump())
    db.add(tier)
    db.commit()
    db.refresh(tier)
    return {"price_tier_id": tier.id}


@router.post("/{listing_id}/publish", status_code=200)
def publish_listing(listing_id: str, db: Session = Depends(get_db)):
    """Operator moderation approval gate (Section 9.5) — a listing never
    goes live without this, regardless of classification confidence."""
    listing = db.get(models.Listing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    listing.state = models.ListingState.live
    db.query(models.ModerationQueueItem).filter_by(listing_id=listing_id, resolved=False).update(
        {"resolved": True}
    )
    db.commit()
    return {"listing_id": listing.id, "state": listing.state.value}


@router.get("/search")
def search_listings(
    q: str | None = None,
    hts10: str | None = None,
    category: str | None = None,
    db: Session = Depends(get_db),
):
    """Section 9.3 — a relevance-ranked search over the live catalogue.
    Filters (hts10, category) narrow the candidate set in SQL; free-text
    `q` then ranks that set with TF-IDF cosine similarity
    (services/semantic_search.py) rather than an ILIKE substring match,
    so results with more/rarer matching terms surface first instead of
    in an arbitrary row order. This is the Phase-1 bridge described in
    that module's docstring, not the Phase-2 embeddings pipeline."""
    query = (
        db.query(models.Listing)
        .options(joinedload(models.Listing.vendor), joinedload(models.Listing.price_tiers))
        .filter(models.Listing.state == models.ListingState.live)
    )
    if hts10:
        query = query.filter(models.Listing.hts10 == hts10)
    if category:
        query = query.filter(models.Listing.taxonomy_path.ilike(f"%{category}%"))

    candidates = query.limit(500).all()

    if q:
        ranked = semantic_search.rank(q, candidates)
        by_id = {l.id: l for l in candidates}
        listings = [by_id[listing_id] for listing_id, _score in ranked[:50]]
    else:
        listings = sorted(candidates, key=lambda l: l.created_at, reverse=True)[:50]

    return [
        {
            "id": l.id,
            "title": l.title,
            "vendor": {"id": l.vendor.id, "legal_name": l.vendor.legal_name, "verification_tier": l.vendor.verification_tier.value, "city": l.vendor.city},
            "hts10": l.hts10,
            "taxonomy_path": l.taxonomy_path,
            "price": ensure_never_empty(db, l),
        }
        for l in listings
    ]


@router.get("/{listing_id}")
def get_listing(listing_id: str, db: Session = Depends(get_db)):
    listing = (
        db.query(models.Listing)
        .options(joinedload(models.Listing.vendor), joinedload(models.Listing.price_tiers))
        .filter(models.Listing.id == listing_id)
        .first()
    )
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    return {
        "id": listing.id,
        "title": listing.title,
        "description": listing.description,
        "specs": listing.specs,
        "hts10": listing.hts10,
        "taxonomy_path": listing.taxonomy_path,
        "moq": listing.moq,
        "lead_time_days": listing.lead_time_days,
        "certifications": listing.certifications,
        "images": listing.images,
        "vendor": schemas.VendorPublic.model_validate(listing.vendor),
        "price": ensure_never_empty(db, listing),
    }
