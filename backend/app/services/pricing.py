"""Section 4: 'A single price is a lie in export trade.'

This module owns the one rule that must never be violated anywhere in the
codebase: a listing is never rendered with no price information (Table 15).
If a listing has no PriceTier of its own, callers must fall back to
`derived_range_for_classification`, which looks at *other* verified
listings sharing the same HTS10 and reports a labelled estimate.
"""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models


def derived_range_for_classification(db: Session, hts10: str, exclude_listing_id: str | None = None):
    """A category-level price band derived from comparable listings.
    Returned as an explicitly-labelled estimate, never attributed to the
    vendor being displayed (Table 14, 'Quote on request' row)."""
    query = (
        db.query(
            func.min(models.PriceTier.price_low),
            func.max(func.coalesce(models.PriceTier.price_high, models.PriceTier.price_low)),
            models.PriceTier.currency,
        )
        .join(models.Listing, models.Listing.id == models.PriceTier.listing_id)
        .filter(models.Listing.hts10 == hts10, models.Listing.state == models.ListingState.live)
    )
    if exclude_listing_id:
        query = query.filter(models.Listing.id != exclude_listing_id)

    row = query.first()
    if not row or row[0] is None:
        return None

    low, high, currency = row
    return {
        "price_low": float(low),
        "price_high": float(high),
        "currency": currency or "USD",
        "disclosure": "derived_estimate",
        "label": "Estimate from comparable listings in this classification — not this vendor's price.",
    }


def ensure_never_empty(db: Session, listing: models.Listing) -> list[dict]:
    """Returns price info to render: the listing's own tiers if present,
    otherwise a derived range, otherwise an explicit 'insufficient data'
    marker (still not a blank)."""
    if listing.price_tiers:
        return [
            {
                "source": "vendor",
                "qty_min": t.qty_min,
                "qty_max": t.qty_max,
                "price_low": float(t.price_low),
                "price_high": float(t.price_high) if t.price_high else None,
                "currency": t.currency,
                "incoterm": t.incoterm.value if hasattr(t.incoterm, "value") else t.incoterm,
                "disclosure": t.disclosure.value if hasattr(t.disclosure, "value") else t.disclosure,
            }
            for t in listing.price_tiers
        ]

    if listing.hts10:
        derived = derived_range_for_classification(db, listing.hts10, exclude_listing_id=listing.id)
        if derived:
            return [{"source": "derived", **derived}]

    return [
        {
            "source": "insufficient_data",
            "label": "Not enough comparable listings yet — request a quote.",
        }
    ]
