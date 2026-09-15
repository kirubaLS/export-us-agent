"""Section 4.3 / 9.2 — the landed-cost layer.

Every listing's price is shown twice: what the vendor charges, and what it
costs the buyer at their own door. The expensive part (duty research) is
cached by (hts10, origin, destination) — origin is always India for
Corridor A, so a few thousand distinct classifications cover the whole
catalogue (Section 4.3, Table 27). Freight and brokerage are estimates and
are labelled as such; the duty line is sourced and dated.
"""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app import models
from app.services.duty_rates import lookup_duty_rate

CACHE_TTL = timedelta(days=7)

# Rough, published-looking per-unit freight/fee estimates. Real
# implementation swaps this for the Freightos integration in Phase 3
# (Table 26 / Appendix B).
_ESTIMATED_FREIGHT_PCT_OF_UNIT = 0.09
_ESTIMATED_INSURANCE_PCT_OF_UNIT = 0.01
_ESTIMATED_FEDERAL_FEES_PCT = 0.005
_ESTIMATED_BROKERAGE_PCT = 0.013


def get_or_compute(db: Session, hts10: str, origin: str, destination: str) -> models.LandedCostEstimate:
    cached = (
        db.query(models.LandedCostEstimate)
        .filter_by(hts10=hts10, origin=origin, destination=destination)
        .order_by(models.LandedCostEstimate.computed_at.desc())
        .first()
    )
    if cached and (datetime.utcnow() - cached.computed_at) < CACHE_TTL:
        return cached

    rate = lookup_duty_rate(hts10, origin)
    partial = rate is None
    components = {
        "duty": None
        if rate is None
        else {
            "pct": rate["ad_valorem_pct"],
            "source": rate["source"],
            "as_of": rate["as_of"],
            "sourced": True,
        },
        "freight_pct": _ESTIMATED_FREIGHT_PCT_OF_UNIT,
        "insurance_pct": _ESTIMATED_INSURANCE_PCT_OF_UNIT,
        "federal_fees_pct": _ESTIMATED_FEDERAL_FEES_PCT,
        "brokerage_pct": _ESTIMATED_BROKERAGE_PCT,
    }

    estimate = models.LandedCostEstimate(
        hts10=hts10,
        origin=origin,
        destination=destination,
        components=components,
        partial=partial,
    )
    db.add(estimate)
    db.commit()
    db.refresh(estimate)
    return estimate


def apply_to_unit_price(estimate: models.LandedCostEstimate, unit_price: float) -> dict:
    """Turns the cached percentage components into an itemised, dollar
    breakdown for one specific listing's price (Table 16)."""
    c = estimate.components
    lines = []

    freight = unit_price * c["freight_pct"]
    lines.append({"label": "Ocean freight", "amount": round(freight, 4), "note": "estimated, 20ft container", "sourced": False})

    insurance = unit_price * c["insurance_pct"]
    lines.append({"label": "Insurance", "amount": round(insurance, 4), "note": "estimated", "sourced": False})

    if c["duty"] is not None:
        duty = unit_price * (c["duty"]["pct"] / 100.0)
        lines.append(
            {
                "label": "Duty",
                "amount": round(duty, 4),
                "note": f"HTS {estimate.hts10}, {estimate.origin} origin — {c['duty']['source']} (as of {c['duty']['as_of']})",
                "sourced": True,
            }
        )
    else:
        duty = 0.0
        lines.append({"label": "Duty", "amount": 0.0, "note": "rate not available for this classification — treat as incomplete", "sourced": False})

    fees = unit_price * c["federal_fees_pct"]
    lines.append({"label": "Federal fees", "amount": round(fees, 4), "note": "processing and harbour fees, estimated", "sourced": False})

    brokerage = unit_price * c["brokerage_pct"]
    lines.append({"label": "Brokerage", "amount": round(brokerage, 4), "note": "estimated", "sourced": False})

    landed_total = round(unit_price + freight + insurance + duty + fees + brokerage, 4)
    markup_pct = round(((landed_total / unit_price) - 1) * 100, 1) if unit_price else 0.0

    return {
        "components": lines,
        "landed_total": landed_total,
        "markup_pct": markup_pct,
        "partial": estimate.partial,
    }
