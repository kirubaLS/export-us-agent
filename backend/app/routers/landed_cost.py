from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import schemas
from app.database import get_db
from app.services.landed_cost import apply_to_unit_price, get_or_compute

router = APIRouter(prefix="/landed-cost", tags=["landed-cost"])


@router.post("", response_model=schemas.LandedCostResponse)
def compute_landed_cost(payload: schemas.LandedCostRequest, db: Session = Depends(get_db)):
    estimate = get_or_compute(db, payload.hts10, payload.origin, payload.destination)
    applied = apply_to_unit_price(estimate, payload.unit_price)
    return schemas.LandedCostResponse(
        hts10=payload.hts10,
        origin=payload.origin,
        destination=payload.destination,
        unit_price=payload.unit_price,
        components=applied["components"],
        landed_total=applied["landed_total"],
        markup_pct=applied["markup_pct"],
        partial=applied["partial"],
        computed_at=datetime.utcnow(),
    )
