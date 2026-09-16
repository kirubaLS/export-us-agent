# System design — India ⇄ USA Trade Marketplace (Corridor A, Phase 1)

This implements the Phase 1 MVP scope from the research blueprint
(`Contents`, §12, Table 33): vendor onboarding with verification, a
listing editor with quantity-tiered pricing, server-queryable search,
gated enquiries, automatic tariff classification, and landed-cost
estimation. Reverse corridor (USA→India), payments, Typesense, and
hosted-embedding search and Typesense are deliberately out of scope here — they are
Phase 2+ per the blueprint's own sequencing rule (§7.2: "do not build the
reverse corridor in parallel"; "do not add a search service on day one").

## Why this shape

The blueprint's central architectural claim (§1.5, §9) is that the
defensible product isn't the catalogue — anyone can build a directory —
it's the number a buyer can't get anywhere else: a sourced, dated landed
cost per listing. Two consequences drove the design:

1. **The duty-research cache is a first-class object, not a side effect.**
   `LandedCostEstimate` is keyed by `(hts10, origin, destination)`, not by
   listing. Every listing under the same ten-digit classification shares
   one row (`app/services/landed_cost.py`). This is what makes the
   economics work at catalogue scale (§4.3): a few thousand distinct
   classifications can cover tens of thousands of listings.

2. **Gated contact disclosure is enforced in the data layer, not the UI.**
   `schemas.VendorPublic` structurally cannot carry a contact field —
   there is no `contact_email` attribute on it at all, so a router author
   can't accidentally leak one by forgetting a redaction step. The only
   code path that can return `contact_name`/`contact_email`/`contact_phone`
   is `POST /enquiries/{id}/release-contact`, which requires an
   authenticated buyer, an enquiry that buyer filed, and a vendor whose
   `claim_state` shows consent was captured (`app/routers/enquiries.py`).
   `contact_released_at` on that row *is* the DPDP disclosure record
   (§10.2) — it doesn't need a separate audit table because the enquiry
   itself is append-only and timestamped.

## Data model

`backend/app/models.py` implements Appendix A directly: `Vendor`,
`Verification` (append-only), `Listing`, `PriceTier` (many-per-listing,
never a single price field — §4), `LandedCostEstimate`, `ShipmentSignal`,
`Enquiry`, `Message`/`MessageThread`, `ConsentRecord`,
`ModerationQueueItem`, `ClaimRequest`. The one deviation from the
appendix: `Vendor` carries `contact_*` columns directly rather than a
separate contacts table, because DPDP consent attaches to the vendor
entity as a whole (one `consent_record_id`), and the schema layer, not a
second table, is what actually keeps them from leaking.

## The "never render an empty price" rule (Table 15)

This is enforced in exactly one place, `app/services/pricing.py`, and
every read path (`GET /listings/{id}`, `GET /listings/search`) calls
through it:

1. If the listing has its own `PriceTier` rows, show them.
2. Otherwise, derive a range from other **live** listings sharing the
   same `hts10`, explicitly labelled as an estimate attributed to the
   classification, not the vendor (§4.2 "Quote on request" tier).
3. Otherwise, an explicit "insufficient data" marker — still not a blank.

## Classification and landed cost as a pipeline, not a monolith

`app/services/classification.py` and `app/services/duty_rates.py` are
built as swappable stubs with the same contract the real Export-to-Entry
Agent would need: return `None`/low-confidence rather than guess, and
route anything under `MODERATION_CONFIDENCE_THRESHOLD` to
`ModerationQueueItem` (§9.1, §9.5). Wiring in a real LLM-based classifier
or a licensed HTS/duty data source later means replacing the body of
`classify()` and `lookup_duty_rate()` — no caller changes, because the
router and the caching layer only depend on the function contracts, not
their internals.

## Verification tiers are derived state, never set by hand (Table 22)

`app/routers/verification.py` recomputes `vendor.verification_tier` from
the *current, non-expired* `Verification` rows every time a check runs.
A sanctions-screen failure short-circuits straight to suspension in the
same request — not a flag for a human to notice later (§6.4, §10.5).

## Stack choices vs. the blueprint's §7

| Layer | Blueprint recommendation | What's implemented |
|---|---|---|
| Backend | Python/FastAPI | FastAPI, sync SQLAlchemy 2.0 ORM |
| Database | Postgres, managed; pgvector later | SQLAlchemy models portable to Postgres; smoke-tested against SQLite for zero-dependency local dev; `LandedCostEstimate`/`Listing.embedding` columns are JSON now, swap to `pgvector`'s `Vector` type when semantic search (Phase 2) lands |
| Search | Postgres full-text first | SQL filters (hts10, category) narrow candidates, then `services/semantic_search.py` ranks free-text `q` by TF-IDF cosine similarity — closer to relevance-ranked search than ILIKE, with no external service or API key to fail at deploy time; swap its internals for a real embeddings pipeline (or move filtering to `to_tsvector`) when the catalogue is real, migrate to Typesense only in Phase 2 |
| Auth | Managed IdP | Minimal JWT + bcrypt for the MVP; buyer-only (§7.1 "buy this rather than build it" — noted as a deliberate simplification to keep the reference implementation dependency-free, not a recommendation to keep it in production) |
| Frontend | React, moving to SSR | React + Vite SPA here; the router/page split (`Search`, `ListingDetail`, `VendorOnboarding`, `Moderation`) maps directly onto the SSR page boundaries the blueprint calls for in §7.2 ("listing and category pages must be server-rendered") — moving to Next.js/Remix only changes the render target, not the component boundaries |
| Payments | Deferred to Phase 4 | Not implemented — no code path touches money |

## What's intentionally not built here

- Reverse corridor, RFQ multi-vendor routing, semantic matching,
  WhatsApp notifications, restricted-party screening integration,
  freight-rate API, Typesense migration — all explicitly Phase 2+ in the
  blueprint's own roadmap (§12, Table 33) and would be premature before
  Phase 0's cold-start (200 hand-onboarded vendors) has actually run.
- A vendor-role auth surface — the inbox endpoint
  (`GET /enquiries/vendor/{vendor_id}`) is unauthenticated in this
  reference implementation and is called out as such in its docstring;
  production needs a second JWT audience for vendor users before this
  ships.
