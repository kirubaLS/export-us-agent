from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import auth, enquiries, landed_cost, listings, moderation, vendors, verification

app = FastAPI(
    title="India-USA Trade Marketplace API",
    description="Corridor A (India to USA) B2B marketplace: verified vendor "
    "profiles, tiered pricing, automatic tariff classification and landed-cost "
    "estimation, gated buyer-vendor enquiries.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(vendors.router)
app.include_router(listings.router)
app.include_router(landed_cost.router)
app.include_router(enquiries.router)
app.include_router(moderation.router)
app.include_router(verification.router)


@app.on_event("startup")
def on_startup():
    # Dev convenience only — production schema changes go through Alembic
    # migrations (backend/alembic/), never create_all.
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok"}
