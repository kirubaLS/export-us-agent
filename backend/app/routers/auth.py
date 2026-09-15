from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=schemas.Token)
def register(payload: schemas.BuyerRegister, db: Session = Depends(get_db)):
    if db.query(models.Buyer).filter(models.Buyer.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")

    buyer = models.Buyer(
        company_name=payload.company_name,
        contact_name=payload.contact_name,
        email=payload.email,
        phone=payload.phone,
        country=payload.country,
        hashed_password=hash_password(payload.password),
    )
    db.add(buyer)
    db.commit()
    db.refresh(buyer)
    return schemas.Token(access_token=create_access_token(buyer.id))


@router.post("/login", response_model=schemas.Token)
def login(payload: schemas.BuyerLogin, db: Session = Depends(get_db)):
    buyer = db.query(models.Buyer).filter(models.Buyer.email == payload.email).first()
    if not buyer or not verify_password(payload.password, buyer.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return schemas.Token(access_token=create_access_token(buyer.id))
