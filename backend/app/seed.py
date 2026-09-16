"""Seeds a handful of realistic vendors/listings so the search and
landed-cost endpoints return real results instead of an empty catalogue.
Mirrors the claim-your-profile pipeline (Section 3.6) end to end: an
unclaimed stub vendor, a claim approval, KYB checks, a published listing
with price tiers. Run with: `python -m app.seed`.

Idempotent-ish: re-running adds a second batch rather than erroring, so
it's safe to run against a dev database more than once, but it's a
development convenience, not a fixture for automated tests.
"""

from app.database import Base, SessionLocal, engine
from app.routers.verification import _recompute_tier
from app import models

SEED_VENDORS = [
    {
        "vendor": {
            "legal_name": "Khurja Ceramics Exports Pvt Ltd",
            "city": "Khurja",
            "state": "Uttar Pradesh",
            "iec": "IEC0001",
            "gstin": "GSTIN0001",
        },
        "listings": [
            {
                "title": "Stoneware Ceramic Mug 350ml, Glazed",
                "description": "Food-grade stoneware ceramic mug, glazed finish, dishwasher and microwave safe. Private label available.",
                "specs": {"materials": "ceramic", "capacity_ml": 350},
                "moq": 2000,
                "lead_time_days": 35,
                "certifications": ["FDA food-contact compliant"],
                "price_tiers": [
                    {"qty_min": 2000, "qty_max": 9999, "price_low": 1.10, "price_high": 1.35, "incoterm": "FOB", "disclosure": "indicative"},
                    {"qty_min": 10000, "qty_max": None, "price_low": 0.92, "price_high": 1.05, "incoterm": "FOB", "disclosure": "indicative"},
                ],
            },
        ],
    },
    {
        "vendor": {
            "legal_name": "Tirupur Cotton Garments LLP",
            "city": "Tirupur",
            "state": "Tamil Nadu",
            "iec": "IEC0002",
            "gstin": "GSTIN0002",
        },
        "listings": [
            {
                "title": "100% Cotton Crew Neck T-Shirt, Private Label",
                "description": "Cotton knit t-shirt, 180 GSM combed cotton, custom labelling and packaging available for private brands.",
                "specs": {"materials": "cotton", "gsm": 180},
                "moq": 5000,
                "lead_time_days": 45,
                "certifications": ["OEKO-TEX Standard 100"],
                "price_tiers": [
                    {"qty_min": 5000, "qty_max": None, "price_low": 2.40, "price_high": 3.10, "incoterm": "FOB", "disclosure": "indicative"},
                ],
            },
        ],
    },
    {
        "vendor": {
            "legal_name": "Jodhpur Wooden Furniture Co",
            "city": "Jodhpur",
            "state": "Rajasthan",
            "iec": "IEC0003",
            "gstin": "GSTIN0003",
        },
        "listings": [
            {
                "title": "Solid Sheesham Wood Dining Chair",
                "description": "Handcrafted solid sheesham (Indian rosewood) dining chair, natural finish, knock-down packaging for freight efficiency.",
                "specs": {"materials": "wooden", "wood": "sheesham"},
                "moq": 100,
                "lead_time_days": 60,
                "certifications": [],
                "price_tiers": [],  # deliberately empty -> exercises the derived-range fallback
            },
        ],
    },
]


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for entry in SEED_VENDORS:
            vendor = models.Vendor(**entry["vendor"])
            db.add(vendor)
            db.flush()

            # Claim + consent, same as the API-driven flow in vendors.py
            consent = models.ConsentRecord(
                subject_type="vendor",
                subject_id=vendor.id,
                purpose="publish_business_details+contact_disclosure_on_enquiry",
            )
            db.add(consent)
            db.flush()
            vendor.claim_state = models.ClaimState.claimed
            vendor.contact_name = "Export Manager"
            vendor.contact_email = f"exports@{vendor.legal_name.lower().split()[0]}.example.com"
            vendor.contact_phone = "+91-90000-00000"
            vendor.consent_record_id = consent.id

            for check_type in ("iec", "gstin", "mca"):
                db.add(
                    models.Verification(
                        vendor_id=vendor.id,
                        check_type=check_type,
                        source="seed-fixture",
                        result="pass",
                    )
                )
            db.flush()
            db.refresh(vendor)
            _recompute_tier(db, vendor)

            for listing_data in entry["listings"]:
                price_tiers = listing_data.pop("price_tiers")
                listing = models.Listing(vendor_id=vendor.id, **listing_data)
                db.add(listing)
                db.flush()

                from app.services.classification import classify

                result = classify(listing.title, listing.description, listing.specs.get("materials"))
                listing.hts10 = result["hts10"]
                listing.hts_confidence = result["confidence"]
                listing.hts_reasoning = result["reasoning"]
                listing.state = models.ListingState.live  # seed data skips the moderation queue

                for tier in price_tiers:
                    db.add(models.PriceTier(listing_id=listing.id, **tier))

            db.commit()
            print(f"Seeded vendor: {vendor.legal_name} ({vendor.verification_tier.value})")
    finally:
        db.close()


if __name__ == "__main__":
    run()
