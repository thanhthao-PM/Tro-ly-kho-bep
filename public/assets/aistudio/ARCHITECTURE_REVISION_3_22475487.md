# Architecture Revision 3

> Converted from `revision345.docx`. Content order and tables are preserved; formatting is normalized to Markdown.



Part I: Phase 2 amendments (Revision 3)

Revision 2 sections not listed here are unchanged. All of Revision 3 is architecture only: no application code and none of the 16 agent files.

I.1 Decision register (updated)

| ID | Decision | Status |
| --- | --- | --- |
| D1 | React + TypeScript + Vite | ACCEPTED |
| D2 | PostgreSQL + SQLAlchemy 2.x + Alembic, explicit SELECT … FOR UPDATE | ACCEPTED |
| D3 | Modular monolith, FastAPI | ACCEPTED |
| D4 | Single account, single kitchen, no roles or permissions | ACCEPTED |
| D5 | kitchen_id on tenant tables, composite foreign keys where appropriate | ACCEPTED |
| D6 | Batch-cost snapshots for realized COGS; menu cost is an estimate | ACCEPTED |
| D7 | Accounting policy | OPEN: formulas are placeholders; all figures are labeled ACTUAL or ESTIMATE |
| D8 | Stock never negative; shortage Option C | ACCEPTED; resolution actions revised (D32) |
| D9 | Food-safety assumptions | OPEN: no invented expiry dates or safety rules |
| D10 | Never auto-invent expiry dates | ACCEPTED |
| D11 | Base units and explicit conversions | ACCEPTED |
| D12 | Soft delete for master data, ledger preserved | ACCEPTED |
| D13 | Provider-independent AI, deterministic calculations | ACCEPTED |
| D14, D16, D17 | Replenishment hints only; CSV/Excel first; folder-based role files | ACCEPTED |
| D15 | Supabase PostgreSQL; local Postgres for tests only | ACCEPTED (Supabase); ACCEPTED for tests, justified by your D20 local-first instruction |
| D18 | Antigravity conventions | OPEN: deferred until the architecture is final |
| D19 | Supabase Auth | ACCEPTED |
| D20 | Local backend execution and local testing first | ACCEPTED; production hosting OPEN |
| D21 | Synchronous SQLAlchemy 2.x + psycopg 3 | ACCEPTED |
| ~~D22~~ | ~~Permission matrix~~ | REMOVED |
| D23 | MVP dependencies (I.5); optional tools kept separate | ACCEPTED (required set); optional set PROPOSED |
| D24 | Rule-based provider is the default and fallback | ACCEPTED; choosing an external LLM provider OPEN, optional and replaceable |
| D25 | Replenishment formula from average consumption, usable stock and target coverage | ACCEPTED; parameter values OPEN (placeholders) |
| D26 | Supabase plan limits and backups | OPEN until verified |
| D27 | Account provisioning | REVISED: seed/bootstrap, no runtime provisioning. ACCEPTED |
| D28 | Account lifecycle | ACCEPTED as scoped in I.3: no registration, no email verification, deletion deferred |
| D4a | Browser session, JWT handling, CSP | PROPOSED (I.4) |
| D29 | idempotency_keys table | PROPOSED |
| D30 | DB trigger maintains batches.remaining_qty from the ledger | PROPOSED |
| D31 | SQLAlchemy models live centrally under backend/app/db/models/, owned by the Database Agent | PROPOSED |
| D32 | Shortage resolution actions (II.3 and I.6) | PROPOSED |
| D33 | FileStore interface; local disk in the MVP, Supabase Storage adapter optional later | PROPOSED |
| D34 | PyJWT for JWT verification | PROPOSED |

I.2 D27: Account flow (replaces section 3.1 runtime provisioning)

Runtime flow:

Login (Supabase Auth, frontend) → Bearer JWT → FastAPI verifies JWT

→ resolve existing kitchen (WHERE owner_user_id = sub) → application

No POST /me/provision and no onboarding screens.

A verified user with no kitchen row gets 403 KITCHEN_NOT_PROVISIONED. This is a setup error for the team, not something the user fixes.

get_current_kitchen returns an immutable (user_id, kitchen_id). Services never accept a kitchen_id from clients.

The user_profiles and kitchens rows come from the seed process below.

I.3 D28: Demo account runbook (PROPOSED procedure)

| Task | Procedure |
| --- | --- |
| Create the demo user | A team member creates one user in Supabase Auth (dashboard or Admin API) with email and password, already confirmed. Disable public sign-ups in the project's auth settings. Credentials live in the team's password manager, never in the repo. |
| Create profile and kitchen | seed_demo (a backend CLI command, run with the direct DB URL) takes DEMO_USER_ID, creates user_profiles, kitchens, kitchen_settings, and optionally demo data. It is idempotent. |
| Demo data | Seeded through the same InventoryService.receive and sales services as normal use, so the ledger is genuine. No hand-inserted ledger rows. |
| Password reset | Via Supabase Auth: the team sets a new password or sends a recovery email from the dashboard. No reset UI is built. |
| Reset data | reset_demo deletes all tenant data for the demo kitchen and re-runs the seed. Because the ledger is append-only (trigger blocks DELETE), reset uses TRUNCATE on tenant tables. It is guarded: it refuses to run unless ALLOW_DEMO_RESET=true and exactly one kitchen exists. |
| Reseed only | seed_demo --reseed-data rebuilds demo data without touching the account. |
| Maintenance | One named owner holds credentials. After a password change, rehearse login. Re-run the seed after every schema migration that adds required data. |
| Out of scope | Registration, email verification, account deletion, multi-user and production account lifecycle. |

I.4 D4a: Browser session, JWT handling and CSP (recommendation)

Session management (Supabase JS, no custom mechanism):

Use supabase-js defaults: persistSession and autoRefreshToken on. The session sits in browser storage, which I am stating from general supabase-js knowledge; verify it for the version you install.

The API client reads the current token from supabase.auth.getSession() per request and sends Authorization: Bearer. No code stores, copies or logs tokens.

On 401: refresh once, retry once, then redirect to login. Logout calls signOut() and clears the query cache.

The frontend holds only the public key and project URL. Service/secret keys and the DB password exist only in backend environment variables.

Trade-off: a token in browser storage is readable by any script that runs on the page, so XSS becomes the main risk. The alternative (httpOnly cookies via a server-side session layer) needs a backend-for-frontend component, which is not justified for a one-account demo. Revisit before production.

JWT verification in FastAPI:

Supabase publishes the public keys of asymmetric signing keys at a JWKS endpoint under the issuer URL, and that endpoint returns no keys if the project does not use asymmetric signing. Verify in the dashboard which signing method the project uses.

Preferred: asymmetric keys. Fetch and cache the JWKS, match kid, allow only the expected algorithm, check issuer, audience, exp and sub, and refresh the cache on an unknown kid (important for key rotation). Library: PyJWT (D34).

Supabase advises that for projects on a shared secret (HS256), user tokens should be verified by the Auth server. Local verification with the shared secret works but puts a token-minting secret on your API. If the project is HS256, either switch to asymmetric signing or call the Auth server for verification, and treat local shared-secret verification as a last resort.

Backend configuration: database URL, JWKS URL, issuer, audience. No role claims are read or trusted because no roles exist.

Content Security Policy (production build; send as an HTTP header from the static host):

default-src 'self';

script-src 'self';

style-src 'self';

img-src 'self' data: blob:;

font-src 'self';

connect-src 'self' https://<project-ref>.supabase.co https://<api-origin>;

object-src 'none'; base-uri 'self'; form-action 'self';

frame-ancestors 'none'; upgrade-insecure-requests

Self-host fonts. The demo's Google Fonts link would otherwise need extra allowances.

Vite's production build emits external scripts, so no inline script is needed. If a UI library forces inline styles, allow style-src 'unsafe-inline' for styles only and record why.

Roll out as Content-Security-Policy-Report-Only first, fix violations, then enforce. The Vite dev server needs a relaxed dev policy.

Also send X-Content-Type-Options: nosniff and Referrer-Policy: strict-origin-when-cross-origin.

Backend CORS: explicit origin allowlist, no credentials, allowed headers Authorization, Content-Type, Idempotency-Key.

Frontend rule: no dangerouslySetInnerHTML, and no innerHTML as in the demo.

I.5 D23: Dependency separation

Required for the MVP

| Layer | Dependency | Purpose |
| --- | --- | --- |
| Backend | FastAPI, Uvicorn, Pydantic, SQLAlchemy 2.x, psycopg 3, Alembic | Approved baseline |
| Backend | PyJWT (with crypto) | JWT verification (D34). Nothing in the baseline verifies JWTs |
| Backend | python-multipart | FastAPI file uploads |
| Backend | openpyxl | Read Excel sales reports (D16) |
| Backend | pytest, httpx | Tests |
| Frontend | React, TypeScript, Vite, Supabase JS (auth only), TanStack Query, openapi-typescript, Vitest + Testing Library | As approved |

Optional, kept separate (installed only when that feature is built)

| Group | Dependency | Note |
| --- | --- | --- |
| ocr extra | OpenCV, PaddleOCR (PaddlePaddle) | Heavy. Install only for the OCR slice and keep it out of the base install |
| Quality | import-linter, pip-audit, gitleaks, Playwright (smoke only) | Recommended, not required |
| External AI | One provider SDK, only if D24 selects one | Not needed for the default |
| Storage | Supabase Storage adapter | Not needed while files use local disk (D33) |

I.6 Corrections to Revision 2

Replenishment (D25). The approved formula excludes the "expiring soon" term I used earlier. The formula is in II.8.

Shortage resolution (D32). Revision 2 offered "correct or void the sale quantity". Correcting a sale after partial consumption needs a reversal flow that I would not build for the MVP. Replacement actions: CONSUME_FROM_STOCK, WRITE_OFF_ESTIMATED, WAIVE (with a required note, reported as unrecorded cost). Sale correction and voiding are deferred.

POST /me/provision removed (I.2). notification_reads keyed by kitchen stays.

Part II: Phase 3 deliverables

II.1 Final entity and relationship design

Conventions:

Tenant tables have id uuid PK default gen_random_uuid(), kitchen_id uuid NOT NULL, and UNIQUE (kitchen_id, id) so children can reference (kitchen_id, parent_id).

Quantities are numeric(14,3) in the ingredient's base unit. Unit costs are numeric(18,6) per base unit. Money totals are bigint VND.

Enumerations are text with CHECK constraints, not PostgreSQL enum types, so Alembic can change them simply.

Rounding rule for money totals is OPEN (D7). The placeholder is round-half-up, in one shared helper only.

Dates are date in the kitchen's timezone; audit timestamps are timestamptz.

II.1.1 Mermaid ERD

erDiagram

user_profiles ||--|| kitchens : owns

kitchens ||--|| kitchen_settings : configures

kitchens ||--o{ ingredients : has

kitchens ||--o{ dishes : has

kitchens ||--o{ documents : has

kitchens ||--o{ sales : has

kitchens ||--o{ audit_log : records

kitchens ||--o{ idempotency_keys : tracks

kitchens ||--o{ notification_reads : tracks

units ||--o{ ingredients : base_unit

units ||--o{ ingredient_unit_conversions : unit

ingredients ||--o{ ingredient_aliases : known_as

ingredients ||--o{ ingredient_unit_conversions : converts

ingredients ||--o{ batches : stocked_as

ingredients ||--o{ recipe_items : used_in

dishes ||--o{ recipe_items : composed_of

documents ||--o{ document_lines : contains

document_lines }o--o| ingredients : matches

document_lines }o--o| dishes : matches

document_lines ||--o| batches : creates

batches ||--o{ stock_movements : ledger

batches ||--o{ disposals : disposed

sales ||--o{ sale_lines : contains

dishes ||--o{ sale_lines : sold_as

documents ||--o{ sales : source

sale_lines ||--o{ stock_movements : consumes

sale_lines ||--o{ stock_shortages : short

ingredients ||--o{ stock_shortages : lacks

disposals ||--o{ stock_movements : posts

document_lines ||--o{ stock_movements : usage

stock_movements ||--o| stock_movements : reverses

user_profiles { uuid id PK }

kitchens { uuid id PK

uuid owner_user_id FK

text name

text timezone }

kitchen_settings { uuid kitchen_id PK }

units { text code PK

text dimension }

ingredients { uuid id PK

uuid kitchen_id FK

text base_unit_code FK

text name }

ingredient_aliases { uuid id PK

uuid ingredient_id FK }

ingredient_unit_conversions { uuid ingredient_id PK

text unit_code PK }

batches { uuid id PK

uuid ingredient_id FK

date expiry_date

numeric remaining_qty }

stock_movements { uuid id PK

uuid batch_id FK

text type

numeric qty_delta }

documents { uuid id PK

text kind

text status }

document_lines { uuid id PK

uuid document_id FK }

dishes { uuid id PK

text name }

recipe_items { uuid dish_id PK

uuid ingredient_id PK }

sales { uuid id PK

date business_date }

sale_lines { uuid id PK

uuid sale_id FK

uuid dish_id FK }

stock_shortages { uuid id PK

uuid sale_line_id FK

uuid ingredient_id FK }

disposals { uuid id PK

uuid batch_id FK

text type }

idempotency_keys { text key PK }

notification_reads { text notification_key PK }

audit_log { bigint id PK }

Every tenant table also carries kitchen_id; to keep the diagram readable only the root relationships are drawn. Cross-table references among tenant tables use composite foreign keys (kitchen_id, x_id).

II.2 Table definitions, constraints, indexes, ownership

Account and settings

| Table | Columns and constraints | Notes |
| --- | --- | --- |
| user_profiles | id uuid PK (= Supabase user id, no FK to auth.users), display_name text NOT NULL, created_at | Written by the seed process only |
| kitchens | id PK, owner_user_id uuid NOT NULL UNIQUE → user_profiles(id) RESTRICT, name text NOT NULL, timezone text NOT NULL default 'Asia/Ho_Chi_Minh', created_at | UNIQUE(owner_user_id) is the one-kitchen-per-user rule |
| kitchen_settings | kitchen_id PK → kitchens, expiry_warning_days smallint default 3 (0..30), target_coverage_days smallint default 3 (1..60), consumption_window_days smallint default 14 (7..90), min_history_days smallint default 7 (≥1), unusual_quantity_ratio numeric(6,2) default 2.0, backdate_limit_days smallint default 2 | All defaults are PLACEHOLDERS pending team decisions (D25, D9a) |

Catalog

| Table | Columns and constraints |
| --- | --- |
| units (global reference, not tenant-owned) | code text PK, label_vi text, dimension text CHECK IN (MASS, VOLUME, COUNT), factor_to_dimension_base numeric(18,6) > 0. Seed: g (1), kg (1000), ml (1), l (1000) and count units quả, hộp, bó, củ, bìa, gói, chai (1 each) |
| ingredients | kitchen_id, name, normalized_name (NFC, lowercase, trimmed), search_name (accent-stripped by the app, for search only), base_unit_code → units, default_location CHECK IN (FRIDGE, FREEZER, PANTRY), tracks_expiry boolean default true, min_stock_qty numeric(14,3) default 0 (≥0), expiry_warning_days smallint null, deleted_at, created_at, updated_at. Partial UNIQUE (kitchen_id, normalized_name) WHERE deleted_at IS NULL |
| ingredient_aliases | kitchen_id, ingredient_id (composite FK), alias, normalized_alias. UNIQUE (kitchen_id, normalized_alias). The service also rejects an alias equal to another ingredient's name |
| ingredient_unit_conversions | PK (kitchen_id, ingredient_id, unit_code), factor_to_base numeric(18,6) > 0 |

Conversion rule on entry: same unit as base → 1. Same MASS or VOLUME dimension → ratio of factor_to_dimension_base. Otherwise use ingredient_unit_conversions. Otherwise 422 UNIT_NOT_CONVERTIBLE. Base units cannot change once any batch or recipe references the ingredient.

Inventory

| Table | Columns and constraints |
| --- | --- |
| batches | kitchen_id, ingredient_id (composite FK), received_on date NOT NULL, expiry_date date NULL, initial_qty numeric(14,3) > 0, remaining_qty numeric(14,3) default 0 CHECK ≥ 0, unit_cost numeric(18,6) ≥ 0, location CHECK IN (…), source_document_line_id (composite FK, nullable), created_at. CHECK (expiry_date IS NULL OR expiry_date >= received_on). UNIQUE (kitchen_id, ingredient_id, id) |
| stock_movements | See below |

expiry_date is nullable at the database level. The service requires it when the ingredient tracks_expiry, so no expiry is ever invented (D10). Whether every ingredient must have one is OPEN (D9a).

stock_movements (the ledger):

Columns: kitchen_id, batch_id + ingredient_id (one composite FK (kitchen_id, ingredient_id, batch_id) so the ingredient always matches the batch), type, qty_delta numeric(14,3) CHECK <> 0, unit_cost_snapshot numeric(18,6) NOT NULL, value_vnd bigint NOT NULL (signed like qty_delta), occurred_on date NOT NULL, created_at timestamptz, actor_id → user_profiles, reason_code, note, and nullable composite FKs sale_line_id, disposal_id, document_line_id, plus reverses_movement_id (self FK, UNIQUE).

type ∈ RECEIPT, SALE_CONSUMPTION, USAGE_CONSUMPTION, DONATION, SELLOFF, WASTE, ADJUSTMENT_IN, ADJUSTMENT_OUT, REVERSAL.

Checks by type:

| Type | Sign of qty_delta | Required reference |
| --- | --- | --- |
| RECEIPT, ADJUSTMENT_IN | positive | ADJUSTMENT_* needs reason_code; RECEIPT has an optional document_line_id |
| SALE_CONSUMPTION | negative | sale_line_id |
| USAGE_CONSUMPTION | negative | document_line_id |
| DONATION, SELLOFF, WASTE | negative | disposal_id |
| ADJUSTMENT_OUT | negative | reason_code |
| REVERSAL | either | reverses_movement_id |

Append-only: a BEFORE UPDATE OR DELETE trigger raises an error. Corrections are REVERSAL rows.

Cache maintenance (D30): an AFTER INSERT trigger adds qty_delta to batches.remaining_qty. The CHECK (remaining_qty >= 0) then makes negative stock impossible even through a service bug; the service maps the violation to 409 INSUFFICIENT_STOCK. A batch is created with remaining_qty = 0 and its RECEIPT movement posts the initial quantity. The alternative is app-level updates inside InventoryService; the trigger is preferred because it removes the "forgot to update" failure mode.

Indexes: (kitchen_id, occurred_on, created_at), (batch_id), (kitchen_id, ingredient_id, occurred_on), (sale_line_id), (disposal_id).

Batch indexes:

FEFO: (kitchen_id, ingredient_id, expiry_date NULLS LAST, received_on, id) WHERE remaining_qty > 0.

Expiring list: (kitchen_id, expiry_date) WHERE remaining_qty > 0.

(kitchen_id, received_on).

Documents and idempotency

| Table | Columns and constraints |
| --- | --- |
| documents | kitchen_id, kind CHECK IN (IMPORT_INVOICE, SALES_REPORT, USAGE_SLIP), source_format CHECK IN (CSV, XLSX, IMAGE, PDF, MANUAL), status CHECK IN (DRAFT, CONFIRMED, CANCELLED), business_date date NOT NULL, file_sha256 text NULL, storage_key text NULL, ocr_status CHECK IN (NOT_APPLICABLE, PENDING, DONE, FAILED), created_by, created_at, confirmed_at. Partial UNIQUE (kitchen_id, kind, file_sha256) WHERE status <> 'CANCELLED' AND file_sha256 IS NOT NULL |
| document_lines | kitchen_id, document_id (composite FK), line_no int, raw_text, parsed_name, ingredient_id null, dish_id null, quantity numeric(14,3) null, unit_code → units null, unit_price_vnd numeric(18,2) null, line_total_vnd bigint null, expiry_date date null, confidence jsonb null, flags text[] default '{}', is_selected boolean default true. UNIQUE (document_id, line_no) |
| idempotency_keys (D29) | kitchen_id, key text, endpoint text, request_hash text, status_code, response_body jsonb, created_at. UNIQUE (kitchen_id, endpoint, key). Retention window is a placeholder (24 h) |

Menu, sales and shortages

| Table | Columns and constraints |
| --- | --- |
| dishes | kitchen_id, name, normalized_name, price_vnd bigint ≥ 0, deleted_at. Partial UNIQUE on (kitchen_id, normalized_name) WHERE deleted_at IS NULL |
| recipe_items | PK (kitchen_id, dish_id, ingredient_id) with composite FKs, quantity_base numeric(14,3) > 0 |
| sales | kitchen_id, business_date, source_document_id (composite FK, nullable), created_by, created_at |
| sale_lines | kitchen_id, sale_id, dish_id, dish_name_snapshot, quantity int > 0, unit_price_snapshot_vnd bigint, revenue_vnd bigint, cogs_vnd bigint default 0, consumption_status CHECK IN (FULL, PARTIAL), origin CHECK IN (NORMAL, REPURPOSE) |
| stock_shortages | kitchen_id, sale_line_id, ingredient_id, short_qty numeric(14,3) > 0, status CHECK IN (OPEN, RESOLVED), resolution CHECK IN (CONSUMED_FROM_STOCK, WRITTEN_OFF_ESTIMATED, WAIVED) NULL, estimated_unit_cost, estimated_cost_vnd, resolution_note, resolved_at, resolved_by. UNIQUE (sale_line_id, ingredient_id). Constraint: status='RESOLVED' ⇒ resolution and resolved_at present; WAIVED ⇒ resolution_note present. Partial index on (kitchen_id) WHERE status='OPEN' |

Recipe history is not versioned in the MVP. Sale lines snapshot name and price, and the ledger holds the cost truth.

Dispositions, notifications, audit

| Table | Columns and constraints |
| --- | --- |
| disposals | kitchen_id, batch_id (composite FK), type CHECK IN (DONATION, SELLOFF, WASTE), quantity > 0, occurred_on, reason_code CHECK IN (EXPIRED, SPOILED, OVERSTOCK, OTHER) NULL, note, counterparty_name, revenue_vnd bigint null, created_by. Checks: WASTE ⇒ reason present, and OTHER ⇒ note present; SELLOFF ⇒ revenue_vnd present; other types ⇒ revenue_vnd null |
| notification_reads | PK (kitchen_id, notification_key text), read_at. Alerts are computed on request; only read state is stored |
| audit_log | id bigserial PK, kitchen_id, actor_id, action, entity_type, entity_id, before jsonb, after jsonb, request_id, created_at. Append-only trigger |

Cooking an expiring batch into a dish is not a disposal. It creates a sale with origin = REPURPOSE that consumes the chosen batch first.

Data ownership rules

| Tables | Only writer | Readers |
| --- | --- | --- |
| user_profiles, kitchens, kitchen_settings | identity_access (seed) and catalog (settings) | all |
| units, ingredients, aliases, conversions | catalog | all (via service interfaces) |
| batches, stock_movements | inventory (through InventoryService only) | reporting, ai_assistant (read-only queries) |
| documents, document_lines, idempotency_keys | documents | sales, inventory via service calls |
| dishes, recipe_items | menu | all via service calls |
| sales, sale_lines, stock_shortages | sales | reporting |
| disposals | dispositions | reporting |
| notification_reads | notifications |  |
| audit_log | core audit helper |  |

Other modules never write another module's tables. They call the owner's service.

II.3 Alembic migration plan

Models are central (backend/app/db/models/, D31), so env.py imports one metadata object. Order respects foreign keys; each revision is its own reviewed PR.

| Rev | Content |
| --- | --- |
| 0001 | Naming convention, baseline, user_profiles, kitchens, kitchen_settings |
| 0002 | units (with seed), ingredients, aliases, conversions |
| 0003 | dishes, recipe_items |
| 0004 | documents, document_lines, idempotency_keys |
| 0005 | batches (indexes, checks) |
| 0006 | sales, sale_lines |
| 0007 | disposals |
| 0008 | stock_movements, its checks, append-only and cache triggers, deferred composite FKs |
| 0009 | stock_shortages |
| 0010 | notification_reads, audit_log (append-only trigger) |
| 0011 | RLS enabled on every table with no policies; revoke privileges from anon and authenticated, guarded with a role-exists check so local test databases work |

Rules:

Autogenerate, then review by hand. Triggers, partial indexes and checks use explicit op.execute or constructs reviewed against the model.

alembic upgrade head from an empty database must pass in CI, plus alembic check for drift. Trigger tests and constraint tests run against the migrated schema.

Production is forward-only. Downgrades exist for development.

units seed is reference data and lives in revision 0002. Demo data is never in migrations (see I.3).

Any migration that touches stock_movements or batches needs explicit sign-off from the Database and Backend owners.

II.4 API contracts (MVP)

Conventions:

Base /api/v1; JSON snake_case; dates YYYY-MM-DD.

Decimal = string ("2.500"), Money = integer VND, UUID = string.

All quantities in responses are in the ingredient's base unit with a unit code. Requests may give {quantity, unit} in any convertible unit.

Auth: Authorization: Bearer <JWT> on everything except GET /health.

Cross-kitchen access returns 404.

Idempotency-Key header is required on POST /documents/{id}/confirm, POST /batches, POST /batches/{id}/adjustments, POST /batches/{id}/disposals and POST /shortages/{id}/resolve. Same key and same request replays the stored response. Same key and a different request returns 422 IDEMPOTENCY_KEY_REUSED. A request still in flight returns 409 REQUEST_IN_PROGRESS.

Lists use cursor pagination: ?limit=50&cursor=… returns {items, next_cursor}.

Errors: {code, message, details?, request_id}.

| Status | Codes |
| --- | --- |
| 401 | UNAUTHENTICATED |
| 403 | KITCHEN_NOT_PROVISIONED |
| 404 | NOT_FOUND |
| 409 | DUPLICATE_NAME, DUPLICATE_DOCUMENT, DOCUMENT_ALREADY_CONFIRMED, INSUFFICIENT_STOCK, REQUEST_IN_PROGRESS, INGREDIENT_IN_USE |
| 413, 415 | FILE_TOO_LARGE, UNSUPPORTED_FILE |
| 422 | VALIDATION_ERROR, UNIT_NOT_CONVERTIBLE, DOCUMENT_NOT_READY, EXPIRY_REQUIRED, IDEMPOTENCY_KEY_REUSED |
| 429 | RATE_LIMITED |

II.4.1 Endpoint list

| ID | Method and path | Purpose |
| --- | --- | --- |
| H1 | GET /health | Liveness, no data, no auth |
| A1 | GET /me | User and kitchen |
| T1, T2 | GET /settings, PUT /settings | Thresholds and parameters |
| C1 | GET /units | Unit list |
| C2 | GET /ingredients | List (q, include_deleted) |
| C3 | POST /ingredients | Create |
| C4 | GET /ingredients/{id} | Detail |
| C5 | PATCH /ingredients/{id} | Update, aliases and conversions replace-style |
| C6 | DELETE /ingredients/{id} | Soft delete |
| I1 | GET /inventory/ingredients | Stock overview (K02–K06): q, location, received (all, today, 7d, date), sort (expiry, received, name) |
| I2 | GET /inventory/ingredients/{id}/batches | Batches of one ingredient (K07) |
| I3 | POST /batches | Manual receipt (creates batch and RECEIPT movement) |
| I4 | PATCH /batches/{id} | Metadata only: location, expiry_date, received_on. Audited |
| I5 | POST /batches/{id}/adjustments | Stocktake adjustment with reason |
| I6 | GET /inventory/summary | Item count, batch count, stock value, status counts (K01, K12) |
| I7 | GET /stock-movements | History (from, to, type, ingredient_id) |
| D1 | POST /documents | Upload (multipart) or manual (JSON) |
| D2, D3 | GET /documents, GET /documents/{id} | List and detail with lines |
| D4 | POST /documents/{id}/lines | Add a line |
| D5 | PATCH /documents/{id}/lines/{line_id} | Edit a line |
| D6 | DELETE /documents/{id}/lines/{line_id} | Remove a line |
| D7 | POST /documents/{id}/confirm | Apply the document |
| D8 | POST /documents/{id}/cancel | Cancel a draft |
| M1 | GET /dishes | List with estimates; sort=suitability supports TD13 |
| M2, M3 | POST /dishes, GET /dishes/{id} | Create, detail |
| M4 | PATCH /dishes/{id} | Update; recipe replaced as a whole |
| M5 | DELETE /dishes/{id} | Soft delete |
| S1, S2 | GET /sales, GET /sales/{id} | Sales and lines |
| S3 | GET /shortages | status=OPEN\|RESOLVED |
| S4 | POST /shortages/{id}/resolve | Resolve |
| P1 | GET /expiring-batches | Batches expired or within the warning window, with deterministic dish suggestions |
| P2 | POST /batches/{id}/disposals | DONATION, SELLOFF, WASTE, or COOK |
| N1 | GET /notifications | Computed alerts (state=unread\|all, date filters) |
| N2 | POST /notifications/read | Mark specific keys or all as read |
| R1 | GET /reports/summary | Period figures with labels |
| R2 | GET /reports/waste | Waste by reason and ingredient |
| R3 | GET /reports/dishes | Per-dish figures |
| R4 | GET /replenishment-suggestions | Deterministic formula result (II.8) |
| AI1 | POST /assistant/messages | Assistant question |

Registration, login, logout and password reset are Supabase Auth operations performed from the frontend, not FastAPI endpoints.

II.4.2 Shared schemas

type Qty = { quantity: Decimal; unit: string }          // base unit in responses

type Ingredient = {

id: UUID; name: string; base_unit: { code: string; dimension: "MASS"|"VOLUME"|"COUNT" };

default_location: "FRIDGE"|"FREEZER"|"PANTRY"; tracks_expiry: boolean;

min_stock_qty: Decimal; expiry_warning_days: number | null;

aliases: string[]; conversions: { unit: string; factor_to_base: Decimal }[];

deleted: boolean }

type Batch = {

id: UUID; ingredient_id: UUID; received_on: Date; expiry_date: Date | null;

initial_qty: Decimal; remaining_qty: Decimal; unit: string;

unit_cost: Decimal; value_vnd: Money; location: Location;

expiry_status: "EXPIRED"|"EXPIRES_SOON"|"OK"|"NO_EXPIRY"; days_to_expiry: number | null }

type Labeled<T> = { value: T; basis: "ACTUAL" | "ESTIMATE" }

II.4.3 Endpoint schemas

A1 GET /me → { user_id, display_name, kitchen: { id, name, timezone } }

T1/T2 body and response: { expiry_warning_days, target_coverage_days, consumption_window_days, min_history_days, unusual_quantity_ratio, backdate_limit_days } (all integers except the ratio, a decimal). Values are validated against the ranges in II.2.

C1 → { items: [{ code, label_vi, dimension }] }

C2 → { items: Ingredient[], next_cursor }

C3 request → { name, base_unit: "g", default_location, tracks_expiry?, min_stock_qty?, expiry_warning_days?, aliases?: string[], conversions?: [{unit, factor_to_base}] }; 201 Ingredient. Errors: DUPLICATE_NAME, VALIDATION_ERROR.

C4 → Ingredient. C5 request: any subset of the C3 fields except base_unit (rejected once the ingredient has batches or recipes). C6 → 204; 409 INGREDIENT_IN_USE if an active recipe uses it.

I1 → { items: [{ ingredient: {id, name}, total_remaining: Decimal, unit, location, batch_count, nearest_expiry: Date|null, expiry_status, last_received_on }], next_cursor }

I2 → { ingredient_id, total_remaining, unit, batches: Batch[] } (only batches with remaining_qty > 0 unless include_empty=true)

I3 request → { ingredient_id, quantity, unit?, unit_cost_vnd_per_unit: Decimal, received_on, expiry_date?: Date, location? }. Returns 201 Batch. Errors: EXPIRY_REQUIRED if the ingredient tracks expiry and none is given; UNIT_NOT_CONVERTIBLE.

I4 request → { location?, expiry_date?, received_on? } → Batch. Quantity and cost are not accepted here.

I5 request → { new_remaining_quantity: Decimal, unit?, reason_code: "COUNT_CORRECTION"|"LOSS"|"FOUND"|"OTHER", note? } → { batch: Batch, movement: { id, type, qty_delta, value_vnd } }. The service computes the delta and picks ADJUSTMENT_IN or ADJUSTMENT_OUT. Note required for OTHER.

I6 → { ingredient_count, batch_count, stock_value_vnd: Money, by_status: { expired, expires_soon, ok }, by_location: { FRIDGE, FREEZER, PANTRY } }

I7 → { items: [{ id, occurred_on, type, ingredient: {id, name}, batch_id, qty_delta, unit, value_vnd, reference: {kind, id} | null }], next_cursor }

D1

Upload: multipart kind, file (csv, xlsx, jpeg, png, pdf), optional business_date.

Manual: JSON { kind, source_format: "MANUAL", business_date }.

Response 201 Document.

Errors: DUPLICATE_DOCUMENT (same hash), UNSUPPORTED_FILE, FILE_TOO_LARGE. Size and page limits are team-set placeholders.

For CSV and Excel the draft is complete in the response. For image or PDF the response may have ocr_status: PENDING, polled with D3.

type Document = {

id: UUID; kind: "IMPORT_INVOICE"|"SALES_REPORT"|"USAGE_SLIP";

source_format: "CSV"|"XLSX"|"IMAGE"|"PDF"|"MANUAL";

status: "DRAFT"|"CONFIRMED"|"CANCELLED"; ocr_status: string;

business_date: Date; lines: DocumentLine[];

summary: { line_count: number; total_value_vnd: Money | null; blocking_issues: string[] } }

type DocumentLine = {

id: UUID; line_no: number; raw_text: string | null; is_selected: boolean;

ingredient: { id: UUID; name: string } | null; dish: { id: UUID; name: string } | null;

quantity: Decimal | null; unit: string | null; unit_price_vnd: string | null;

line_total_vnd: Money | null; expiry_date: Date | null;

confidence: Record<string, number> | null;

flags: ("UNMATCHED"|"LOW_CONFIDENCE"|"UNUSUAL_QUANTITY"|"TOTAL_MISMATCH"|"EXPIRY_MISSING")[] }

D4/D5 request → any of { ingredient_id, dish_id, quantity, unit, unit_price_vnd, expiry_date, is_selected, parsed_name }; response DocumentLine (flags recomputed server-side). D6 → 204. All three only on DRAFT documents.

D7 → no body. Preconditions, checked together with errors listed in details: every selected line is matched, has a positive quantity, a convertible unit, and for imports a unit price and (if the ingredient tracks expiry) an expiry date. Selected UNUSUAL_QUANTITY lines need the user to keep them selected, which counts as confirmation. Responses:

Import → { document_id, status: "CONFIRMED", batches_created: number, total_value_vnd: Money }.

Sales report → { document_id, status, sales_recorded: number, revenue_vnd: Money, consumption: { fully_covered_lines, partial_lines }, shortages: [{ id, ingredient, short_qty, unit, status }] }.

Usage slip → { document_id, status, lines_posted, shortages: [...] }.

Errors: DOCUMENT_ALREADY_CONFIRMED, DOCUMENT_NOT_READY (with line issues), EXPIRY_REQUIRED.

D8 → 204. Only DRAFT; the file hash is released for re-upload.

M1 → { items: [Dish], next_cursor } where

type Dish = { id; name; price_vnd: Money;

recipe: [{ ingredient_id, ingredient_name, quantity: Decimal, unit }];

cost_estimate_vnd: Labeled<Money>;           // basis: "ESTIMATE"

gross_margin_estimate: { amount_vnd: Money; percent: number; basis: "ESTIMATE" };

max_portions: number; missing_ingredients: string[];

uses_expiring_stock: boolean }

M2 request → { name, price_vnd, recipe: [{ ingredient_id, quantity, unit? }] } (≥ 1 item) → 201 Dish. M4 same fields, optional; recipe replaces the whole recipe. M5 → 204.

S1 → { items: [{ id, business_date, revenue_vnd, line_count, has_open_shortage }], next_cursor }. S2 → sale with lines: [{ id, dish_name, quantity, unit_price_vnd, revenue_vnd, cogs_vnd, consumption_status, origin }].

S3 → { items: [{ id, sale_line_id, business_date, dish_name, ingredient: {id, name}, short_qty, unit, status, resolution }], next_cursor }

S4 request → { action: "CONSUME_FROM_STOCK" | "WRITE_OFF_ESTIMATED" | "WAIVE", note? }. WAIVE requires note. Response { shortage, movements: [...] | [], estimated_cost_vnd: Labeled<Money> | null }. CONSUME_FROM_STOCK posts FEFO consumption for the full short_qty and returns 409 INSUFFICIENT_STOCK if the stock is still not there. WRITE_OFF_ESTIMATED uses the last known unit cost of that ingredient and labels it ESTIMATE; with no cost history it returns 422 VALIDATION_ERROR.

P1 → { as_of: Date, items: [{ batch: Batch, status: "EXPIRED"|"EXPIRES_SOON", suggested_dishes: [{ dish_id, name, portions_possible, gross_margin_estimate_vnd: Labeled<Money> }], available_actions: ["DONATION","SELLOFF","COOK","WASTE"] }] }. Expired batches only list WASTE (an expired batch cannot be consumed). suggested_dishes is a deterministic query over recipes and usable stock, not generated text.

P2 request

{ type: "DONATION" | "SELLOFF" | "WASTE" | "COOK",

quantity?: Decimal, unit?: string,           // not used for COOK

occurred_on?: Date, note?: string,

counterparty_name?: string,                  // DONATION, SELLOFF

revenue_vnd?: Money,                         // SELLOFF only, required

reason_code?: "EXPIRED"|"SPOILED"|"OVERSTOCK"|"OTHER",   // WASTE only, required

dish_id?: UUID, portions?: number }          // COOK only, required

Responses:

201 { disposal: {...}, movement: {...}, cost_vnd: Labeled<Money> } for DONATION, SELLOFF and WASTE.

For COOK: 201 { sale_id, sale_line: {...}, shortages: [...] }, consuming the chosen batch first, then FEFO for other ingredients.

Errors: INSUFFICIENT_STOCK, VALIDATION_ERROR. An expired batch accepts WASTE only.

N1 → { items: [{ key, kind: "EXPIRED"|"EXPIRING_SOON"|"LOW_STOCK"|"OPEN_SHORTAGE"|"MOVEMENT", severity: "CRITICAL"|"WARNING"|"INFO", date, title, detail, read: boolean, action: { kind, target_id } | null }], unread_count }. Keys are deterministic, for example EXPIRED:{batch_id}, EXPIRING:{batch_id}:{expiry_date}, LOW_STOCK:{ingredient_id}, SHORTAGE:{shortage_id}.
N2 request → { keys?: string[], all?: boolean } → { updated: number }.

R1 (?from&to)

{ period: { from, to },

revenue: { sales_vnd: Money, selloff_vnd: Money, total_vnd: Money },        // ACTUAL

cogs_vnd: Money, cogs_complete: boolean, open_shortage_count: number,        // ACTUAL

gross_profit_vnd: Money,

waste_cost_vnd: Money, donation_cost_vnd: Money,

adjustment_net_vnd: Money, unrecorded_cost: { waived_count: number, estimated_vnd: Money },

result_after_ingredient_loss: { amount_vnd: Money, policy_status: "PLACEHOLDER_PENDING_APPROVAL" },

portions_sold: number,

comparison: { previous_period: {...} | null, note: string } }

Components are always returned separately. The derived result is explicitly flagged as pending the accounting decision (D7). It covers ingredient cost only, so the labels say so. Figures involving open or estimated shortages carry cogs_complete=false or basis: "ESTIMATE".

R2 → { total_vnd, count, by_reason: [{ reason, cost_vnd, count }], by_ingredient: [{ ingredient, quantity, unit, cost_vnd, count }] }
R3 → { items: [{ dish, portions, revenue_vnd, cogs_vnd, gross_profit_vnd, margin_percent }] } (actual, from sale lines)

R4 → { as_of, parameters: { target_coverage_days, window_days, min_history_days }, items: [{ ingredient, usable_qty, unit, avg_daily_consumption: Decimal, days_of_cover: Decimal, suggested_order_qty: Decimal, basis: "ESTIMATE", assumptions: string[] }], insufficient_data: [{ ingredient, reason }] }

AI1 → see II.8.

II.5 Core data-flow diagrams

Request authentication and kitchen resolution

sequenceDiagram

participant B as Browser

participant SA as Supabase Auth

participant API as FastAPI

participant DB as Supabase PostgreSQL

B->>SA: signInWithPassword

SA-->>B: session (access token)

B->>API: request + Bearer token

API->>API: verify signature, issuer, audience, exp

API->>DB: SELECT id FROM kitchens WHERE owner_user_id = sub

DB-->>API: kitchen_id

API->>DB: business query scoped by kitchen_id

API-->>B: response (or 401 / 403 KITCHEN_NOT_PROVISIONED)

Invoice import (OCR or CSV)

sequenceDiagram

participant U as User

participant API as documents

participant OCR as OCR worker

participant INV as inventory

participant DB as PostgreSQL

U->>API: POST /documents (file)

API->>API: validate type/size, sha256, duplicate check

alt image or PDF

API->>OCR: bounded subprocess (timeout)

OCR-->>API: lines with confidence, no expiry invented

else CSV or XLSX

API->>API: deterministic parse

end

API->>DB: DRAFT document and lines

U->>API: review, edit, add expiry dates (D4-D6)

U->>API: POST /confirm (Idempotency-Key)

API->>INV: receive(lines) in one transaction

INV->>DB: batches + RECEIPT movements (trigger updates remaining_qty)

API-->>U: CONFIRMED

Sales report, FEFO and shortage (Option C)

sequenceDiagram

participant U as User

participant S as sales

participant INV as inventory

participant DB as PostgreSQL

U->>S: POST /documents/{id}/confirm

S->>DB: BEGIN; record sale and sale_lines (revenue always stored)

S->>INV: consume per ingredient, ascending ingredient id

INV->>DB: SELECT batches FOR UPDATE ORDER BY expiry, received, id

alt enough usable stock

INV->>DB: SALE_CONSUMPTION movements with cost snapshots

else not enough

INV->>DB: consume what exists; return short quantity

S->>DB: stock_shortages OPEN; sale_line PARTIAL

end

S->>DB: sale_line.cogs_vnd, document CONFIRMED, audit; COMMIT

S-->>U: totals, consumption summary, shortages

Expiring stock handling

flowchart TD

A[GET /expiring-batches] --> B{expiry status}

B -->|EXPIRES_SOON| C[Choose action]

B -->|EXPIRED| W[WASTE only]

C --> D[DONATION: disposal + movement]

C --> E[SELLOFF: disposal + movement + revenue]

C --> F[COOK: sale origin REPURPOSE, chosen batch first]

C --> W

D & E & F & W --> L[(append-only ledger + audit)]

Assistant question

sequenceDiagram

participant U as User

participant AS as AssistantService

participant P as LLMProvider (rule-based default)

participant T as Read-only tools

participant DB as PostgreSQL

U->>AS: POST /assistant/messages

AS->>P: plan(question, tool catalog)

P-->>AS: tool calls (no kitchen_id argument)

AS->>T: run with kitchen context from JWT

T->>DB: read-only queries

T-->>AS: typed facts with as_of

AS->>P: compose(question, facts)

P-->>AS: answer template with fact placeholders

AS->>AS: validate placeholders and numerals; render figures from facts

AS-->>U: answer, facts, recommendations, data_gaps, proposed_actions

II.6 Business rules referenced by the contracts

FEFO selection: batches with remaining_qty > 0 and (expiry_date >= today or expiry_date IS NULL), ordered by expiry_date NULLS LAST, received_on, id, locked FOR UPDATE. Ingredients are locked in ascending id order. A lock timeout returns a retryable error.

Sales consumption allocates each ingredient's pooled need across sale lines in line_no order.

Business date: occurred_on is the document's business_date, which cannot be in the future and not older than backdate_limit_days (placeholder). Eligibility uses current stock and today's usability. How back-dated reports should treat stock that was usable on the business date is OPEN (D9b); the placeholder rule avoids silent reinterpretation.

Expiry status: EXPIRED if expiry_date < today; EXPIRES_SOON if within expiry_warning_days (ingredient override or kitchen default); NO_EXPIRY when null. These are mechanical date comparisons. No safety rule beyond them is implied (D9).

Unusual quantity (placeholder): a received quantity above unusual_quantity_ratio times the largest single receipt of that ingredient in history gets the UNUSUAL_QUANTITY flag. With no history, no flag.

COGS and snapshots: each consumption row stores the batch's unit_cost_snapshot. COGS equals the sum of those values. Menu cost is ESTIMATE.

No claims beyond the data: every report field is labeled ACTUAL or ESTIMATE, and open shortages flip cogs_complete to false.

II.7 OCR contract (AI Agent)

Input: stored file reference and kind. Output:

type ExtractedDocument = {

engine: string; engine_version: string; page_count: number; image_quality: "OK"|"LOW"|"UNREADABLE";

lines: [{ raw_text: string,

fields: { name?: F<string>; quantity?: F<string>; unit?: F<string>;

unit_price?: F<string>; line_total?: F<string>; expiry_date?: F<string> } }] }

type F<T> = { value: T | null; confidence: number | null; status: "OK"|"LOW_CONFIDENCE"|"MISSING" }

OCR never creates ledger rows and never fills a missing value. A printed expiry date that is read is returned with status and still requires user confirmation.

Matching to ingredients uses exact normalized name or alias only. Otherwise the line is UNMATCHED.

Cross-check: quantity × unit price versus line total sets TOTAL_MISMATCH. The confidence threshold for LOW_CONFIDENCE is a team placeholder until a benchmark exists.

Failure or UNREADABLE produces a draft with no lines and an ocr_status: FAILED reason, and offers manual entry.

No accuracy figure is published before the evaluation set has run.

II.8 AI integration contracts

Provider interface (LLMProvider)

plan(input: { question: string; history: Turn[]; tools: ToolSpec[] }): { tool_calls: { tool: string; args: object }[] }

compose(input: { question: string; history: Turn[]; facts: Fact[] }): {

answer_template: string,                       // figures only as {{fact:ID}} placeholders

recommendations: { text: string; assumptions: string[]; basis: "VERIFIED_FACT"|"ESTIMATE" }[],

data_gaps: string[],

proposed_actions: { type: ActionType; target_id: UUID | null; label: string }[] }

Default RuleBasedProvider: keyword and intent mapping for the five spec questions: what to process first, stock of an ingredient, best-margin dish, most-wasted item, what can be cooked. It is deterministic, always available, and is the fallback. Selected by environment config (rule_based or external). No API key is needed for the default.

External provider (optional, replaceable, D24 OPEN): implements the same interface. Constraints: timeout, one retry, token budget, receives only aggregated facts (no images, emails, tokens, document contents). Any failure falls back to the rule-based provider.

Tools (read-only, scoped by the verified kitchen; tool arguments never contain kitchen_id or a user id)

| Tool | Arguments | Result |
| --- | --- | --- |
| get_stock | ingredient_ref: string (resolved by alias match; ambiguous returns a data_gap) | Total, per-batch quantity, expiry |
| list_expiring | within_days? | Batches with status |
| get_cookable_dishes | limit? | Dishes with max_portions, estimated margin |
| get_dish_margins | sort, limit | Estimated margins (ESTIMATE) and actual margins from sales (ACTUAL) |
| get_period_summary | from, to | Same fields as R1 |
| get_waste_summary | from, to | Same fields as R2 |
| get_replenishment_suggestions | none | Same fields as R4 |

Replenishment formula (D25, deterministic, parameters are placeholders):

usable_qty = sum of remaining_qty over batches that are not expired.

avg_daily_consumption = (sum of SALE_CONSUMPTION and USAGE_CONSUMPTION quantities over the last consumption_window_days) ÷ consumption_window_days. Waste, donations and sell-offs are not demand.

If the history available is shorter than min_history_days, the ingredient goes to insufficient_data and no suggestion is made.

days_of_cover = usable_qty ÷ avg_daily_consumption.

Suggest an order when days_of_cover < target_coverage_days or usable_qty < min_stock_qty.

suggested_order_qty = max(0, target_coverage_days × avg_daily_consumption − usable_qty, min_stock_qty − usable_qty), rounded up to the ingredient's base-unit step.

Always labeled ESTIMATE with the assumptions listed in the response.

AI1 request and response

// request

{ message: string /* ≤ 500 chars */, history?: { role: "user"|"assistant"; text: string }[] /* ≤ 10 */ }

// response

{ answer_text: string,                                  // figures already rendered by the backend

facts: { id: string; tool: string; label: string; value: string; unit?: string; as_of: string }[],

recommendations: { text: string; assumptions: string[]; basis: "VERIFIED_FACT"|"ESTIMATE" }[],

data_gaps: string[],

proposed_actions: { type: "OPEN_EXPIRING_BATCH"|"OPEN_SHORTAGE"|"OPEN_REPLENISHMENT"|"OPEN_DISH"; target_id: UUID | null; label: string }[],

provider: "rule_based" | "external", request_id: string }

The server is stateless: the client sends recent history, and no chat tables exist in the MVP.

Validation rules (backend, before anything reaches the user):

Every {{fact:ID}} placeholder must reference a returned fact.

Digits outside placeholders (other than list numbering) are rejected.

Recommendations must carry basis and assumptions.

Violations replace the answer with the rule-based output and log a request_id-tagged event.

proposed_actions are navigation hints into the ordinary confirm flows. The assistant has no write tools.

Text from invoices, ingredient names and user messages is treated as data, never as instructions.

Evaluation contract:

Datasets in backend/evals/: assistant Q&A with expected tools and numeric assertions; safety cases (fabricated figures, injected invoice text, attempts to name another kitchen); OCR field-level ground truth including digit confusions and ./, decimal separators.

Reports record pass/fail with evidence. Nothing is marked passed without a run.

II.9 Agent ownership boundaries and integration checkpoints

Repository layout is not finalized. These paths are PENDING logical paths (D31 included) until Phase 5.

| Agent | Owns | May read | Needs approval to touch |
| --- | --- | --- | --- |
| Database | backend/alembic/**, backend/app/db/models/**, seed and reset scripts, docs/03_DATABASE_DESIGN.md | everything | Any change to approved tables, triggers or constraints; destructive migrations |
| Backend | backend/app/modules/*/{api,schemas,service,repository}/** except ai_assistant and documents/ocr, backend/app/core/**, main.py, docs/04_API_CONTRACT.md (as drafter) | models, evals | API contract changes, anything in db/models, dependencies |
| AI | backend/app/modules/ai_assistant/**, backend/app/modules/documents/ocr/**, backend/evals/**, docs/05_AI_ARCHITECTURE.md | services it calls | Provider choice (D24), new tools, new tool arguments, any write capability |
| Frontend | frontend/** (generated API types are produced from OpenAPI, never hand-edited) | OpenAPI snapshot, docs | API shape changes, new dependencies, CSP changes |
| QA | backend/tests/{integration,contract,e2e}/**, frontend/tests/e2e/**, fixtures, eval runners, docs/09_TESTING_STRATEGY.md | everything | Changing production code to satisfy a test |

Unit tests live with the code's owner; QA owns cross-module, contract, concurrency and end-to-end tests.

Shared artifacts needing team approval to change: this Phase 3 document once approved, the committed OpenAPI snapshot, db/models, migrations, pyproject/package.json dependency lists, environment variable names.

Integration checkpoints

| CP | Gate | Producer → consumer | Exit criteria |
| --- | --- | --- | --- |
| 0 | Phase 3 approved | Team | Contracts frozen; open placeholders listed |
| 1 | Schema on dev | Database → Backend | Migrations 0001–0011 pass from empty; constraint and trigger tests pass |
| 2 | Identity and ledger slice | Backend + Database + QA | JWT verification, GET /me, POST /batches, FEFO, concurrent-consumption test (two requests, one batch, no negative stock), cross-kitchen 404 tests |
| 3 | OpenAPI snapshot | Backend → Frontend | Snapshot committed; TypeScript types generated; contract test in CI |
| 4 | Import flow | Backend, Frontend, QA | CSV import draft → review → confirm; duplicate and idempotency tests |
| 5 | Sales and shortages | Backend, Frontend, QA | Report confirm, partial consumption, shortage resolution, no double application |
| 6 | Expiring stock, notifications, reports | Backend, Frontend | P1/P2, N1/N2, R1–R4 with labels; cogs_complete behavior verified |
| 7 | AI tools and assistant | AI + Backend + QA | Rule-based provider passes the evaluation set; validation rejects fabricated figures |
| 8 | OCR draft pipeline | AI + Backend + QA | Benchmark executed on printed invoices; limits reported honestly |
| 9 | Demo rehearsal | All | reset_demo and reseed, full login-to-report run on the local backend |

Each handoff uses the report format from the master task: what changed, files, interfaces exposed, dependencies added, tests actually executed, limitations, and what the other agents must do.

Part III: Summary

Approved decisions: D1, D2, D3, D4, D5, D6, D8 (with D32 amendment proposed), D10, D11, D12, D13, D14, D15, D16, D17, D19, D20 (local-first), D21, D23 (required set), D24 (rule-based default), D25 (formula), D27 (seed/bootstrap), D28 (scope).

Remaining OPEN:

D7 accounting policy: formulas, rounding, direct usage in COGS, donation treatment, report naming.

D9 and sub-items D9a (is expiry mandatory for every ingredient) and D9b (back-dated stock eligibility), plus the shelf-life and storage-tip catalog.

D18 Antigravity conventions (deferred).

D20 production hosting.

D24 choice of any external LLM provider.

D26 Supabase plan limits, pausing and backups.

Placeholder parameter values: warning days, coverage days, window, minimum history, unusual-quantity ratio, back-date limit, upload limits, OCR confidence threshold.

Awaiting your approval (PROPOSED): D4a (session and CSP), D23 optional set, D29 (idempotency table), D30 (ledger trigger), D31 (central models), D32 (shortage resolution actions), D33 (FileStore), D34 (PyJWT), the demo runbook in I.3, and the entire Phase 3 design.

Documents modified or produced in this step:

Phase 2 Revision 3 amendments (Part I) with the updated decision register.

Phase 3 deliverables (Part II).

Nothing else was created. No application code, no migrations, and none of the 16 agent files.

Next recommended step: review Part II, especially the ledger triggers (D30), the shortage resolution actions (D32), the endpoint contracts, and the placeholder parameters. Reply with approvals or changes. After that I would produce Phase 4 (code standards, testing strategy, security checklist, Git workflow, Definition of Done). The Antigravity pilot for D18 should happen before Phase 5 generates the agent files.
