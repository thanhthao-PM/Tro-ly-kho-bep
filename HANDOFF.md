# HANDOFF

## State
Phase 1 verified on Windows. MVP code written (migrations 0001-0012, models, services, API, rule-based AI, frontend, seed, tests) but
NOTHING beyond Phase 1 has run against PostgreSQL, SQLAlchemy, FastAPI business routes or the Vite build.

## Rules
Rev 6.3 > Rev 5/4/3 (cumulative) > plan > docx > demo. Do not touch auth/JWT code. Never overwrite backend/.env or frontend/.env.local.
No migration on the real Supabase project; use a scratch database. D30a stays disabled (API connects as owner role).

## Resume checklist (in order; stop and report at the first failure with the exact message)
1. `cd backend; python -m pytest -q`  (expect only skips for tests/db)
2. `alembic upgrade head --sql > ..\migration_preview.sql` (review), then `alembic upgrade head` against the SCRATCH DB
3. `$env:TEST_DATABASE_URL="..."; python -m pytest tests\db -q`  <- first real check of 0009/0012 triggers and the service flow
4. `python -m app.scripts.seed_demo --user-id <supabase user uuid>` on the demo DB
5. `uvicorn app.main:app --reload --port 8000`, open /docs
6. `cd frontend; npm install; npm run build; npm run dev`, log in, walk the flow in README section 5

## Likely fix areas on first run
0009/0012 plpgsql syntax; ORM insert order (no FK metadata, explicit flushes); settle_sale_lines vs deferred trigger; TypeScript strictness in pages; commit-time trigger errors mapped in app/main.py.
