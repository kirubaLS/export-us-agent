# India ⇄ USA Trade Marketplace — Phase 1 MVP

A two-sided B2B marketplace connecting verified Indian exporters with US
buyers, built from the research blueprint in `docs/ARCHITECTURE.md`. Core
bet: not another directory — every listing carries an automatically
classified tariff code and a sourced, dated landed-cost estimate, and
vendor contact details are gated behind a real buyer enquiry rather than
published openly.

See `docs/ARCHITECTURE.md` for the system design write-up and how each
piece maps back to the blueprint sections.

## Backend (FastAPI + PostgreSQL)

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # set DATABASE_URL, JWT_SECRET
uvicorn app.main:app --reload
```

API docs at `http://localhost:8000/docs`.

To populate the catalogue with sample verified vendors and listings so
search and landed-cost have real data to return:

```bash
python -m app.seed
```

Key endpoints:
- `POST /vendors` — publish an unclaimed, registry-sourced stub profile
- `POST /vendors/{id}/claim` / `POST /vendors/claims/{id}/approve` — claim-your-profile flow
- `POST /vendors/{id}/verification/run-check` — KYB checks, derives `verification_tier`
- `POST /listings`, `POST /listings/{id}/price-tiers`, `POST /listings/{id}/publish`
- `GET /listings/search`, `GET /listings/{id}` — public read paths, price never blank
- `POST /landed-cost` — sourced duty + estimated freight/fees breakdown
- `POST /auth/register` / `POST /auth/login` — buyer accounts
- `POST /enquiries`, `POST /enquiries/{id}/release-contact` — the gate

## Frontend (React + Vite + TypeScript)

```bash
cd frontend
npm install
npm run dev
```

Pages: buyer search, listing detail with landed-cost calculator and
gated enquiry panel, buyer registration, vendor onboarding (profile →
listing → price tiers → publish), and an operations console for
moderation and claim approval.

## Tests / verification run so far

The backend has been smoke-tested end-to-end against SQLite (vendor
creation → listing → classification → publish → search → landed cost →
buyer registration → enquiry → gated-contact 409 before claim, 200 after
→ verification tier recompute → moderation queue). The frontend has been
type-checked and production-built. Neither has automated test suites yet
— see "Next steps".

## Next steps toward Phase 1 exit criteria (blueprint §12, Table 33)

- Point `DATABASE_URL` at a real Postgres instance and add Alembic
  migrations (`backend/alembic/` is not yet scaffolded).
- Replace the fixture `duty_rates.py` and keyword `classification.py`
  with real integrations (HTS/duty data source, LLM classifier).
- Add pytest coverage for the gating logic in `enquiries.py` and the
  never-empty-price logic in `pricing.py` — these are the two rules the
  blueprint treats as non-negotiable and are the highest-value tests to
  write first.
- Wire WhatsApp/email notifications, restricted-party screening, and a
  vendor-role auth audience before onboarding real vendors.
