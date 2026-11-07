# PHASE2_READINESS (corrected)

CORRECTION: Revisions 3, 4 and 5 ARE in the project documents. Earlier versions of this file wrongly said they
were missing and marked the schema BLOCKED. That was my error; this file replaces it.

Legend: DONE-UNVERIFIED = code written, not executed against PostgreSQL | NOT STARTED | NEEDS DECISION.

## Database (Rev 3 II.2, Rev 4 s2.A/2.B/2.F/3/4.1/4.2/5, Rev 5 s2, Rev 6.3 s3, plan s3)
| Item | Status |
|---|---|
| Migrations 0001-0011 (tables, composite FKs, checks, indexes, seed units) | DONE-UNVERIFIED |
| Ledger triggers (cache, depth guard, deferred consistency, movement validation, append-only, TRUNCATE guard), base-unit backstop, sale-line cache check | DONE-UNVERIFIED (0009) |
| `ledger_effective` (security_invoker) | DONE-UNVERIFIED (0009) |
| RLS enabled on all public tables incl. alembic_version, revokes from PUBLIC/anon/authenticated | DONE-UNVERIFIED (0011) |
| Static migration tests | PASS in sandbox (6 cases, stub alembic); pytest on Windows NOT RUN |
| DB integrity tests (`tests/db`, 15 tests) | WRITTEN, NOT RUN (need migrated scratch DB) |
| SQLAlchemy models | NOT STARTED |
| `alembic upgrade --sql` review, then real upgrade | NOT RUN, needs your approval |

## Choices made where the documents were silent or inconsistent (flag for review)
1. units CHECK rewritten with explicit `IS NOT NULL` for MASS/VOLUME: Rev 4's literal expression lets NULL factors pass.
2. Migration order follows Rev 4 s5 (kitchen_settings in 0001; shortages 0008 before movements 0009; notification_reads+audit_log in 0010), not the plan's own grouping.
3. alembic_version stays in `public` and gets RLS + revokes in 0011, so C6 needs NO exclusion (Option A, no bootstrap script).
4. Reversal trigger COPIES the original's sale_line/disposal/document_line/shortage ids (Rev 5 wording) and validates qty, snapshot cost, value, batch.
5. TRUNCATE guard covers every public table except alembic_version (Rev 5: "every ledger and tenant table"). The reset script must disable the listed `no_truncate_*` triggers (Rev 5 runbook).
6. sale_lines cache check (6.3 s3.4) is implemented as a deferred trigger on sale_lines, stock_movements, stock_shortages; the writer `settle_sale_lines` is Python service code (not started).
7. Anon/authenticated revokes are guarded by role existence (local DBs); custom roles/policies/D30a intentionally absent.
8. Enum-like columns use text + CHECK; `label_vi` for units is my wording (not specified).

## Remaining decisions / unverified
- U1 PostgreSQL >= 15 for security_invoker (Supabase reports 17.11: OK in principle), U10 `pg_trigger_depth()` values: both verified only by tests/db when run.
- OPEN placeholders (D7, D9...) unchanged; no business policy invented.

## Next, in order
Run migration SQL review -> approve -> migrate a scratch DB -> run tests/db -> models -> repositories/services (FEFO, units, idempotency, settle_sale_lines) -> API (Rev 3 II.4) -> frontend -> rule-based AI. OCR is Deferred in 6.3.

---
# Review 1 (code reading of 0001-0011 against Rev 3/4/5/6.3 and the delivered tests)

Method: static reading + sandbox lint only. NOTHING here was checked by PostgreSQL. "No error found" means "none found by reading", not "valid SQL".
Classes: ERROR (violates a stated invariant), GAP (invariant implied by the docs, not enforced), RISK (could bite, not wrong), DECISION (docs silent, you choose).

## 1. disposals <-> stock_movements
Evidence: `validate_movement` (0009) checks only the cost snapshot and reversal rules; `ck_sm_refs` only requires `disposal_id IS NOT NULL` for DONATION/SELLOFF/WASTE. No trigger or FK compares the movement with the disposal row.
| Question | Enforced now? | Consequence |
|---|---|---|
| movement.batch_id = disposals.batch_id | NO | a WASTE movement could drain batch B while the disposal says batch A |
| movement.type = disposals.type | NO | a DONATION disposal could carry a WASTE movement; Rev 5 reports cost per category from movements, disposal revenue from `disposals`, so SELLOFF revenue/cost could split |
| -qty_delta = disposals.quantity | NO | quantity and ledger can diverge; Rev 5 "disposal cost = -sum(value_vnd) with that disposal_id" would not equal quantity x cost |
| one movement per disposal | NO | Rev 3 P2 response is `{disposal, movement}` (singular); ER uses 1:N only because reversals share the id |
Class: **GAP (R1)**, medium. The cache/ledger invariant (C-series) still holds; the disposal-to-ledger link does not.
Proposed fix: `alembic/proposed/0012_review_fixes_PROPOSED.py` (NOT in versions/, not applied): extra checks in `validate_movement` + partial unique index `uq_sm_one_disposal_movement`. Tests: `tests/db/test_proposed_0012_db.py` (runs only if you set PROPOSED_0012_APPLIED=1).
DECISION D-R1: confirm 1 disposal = exactly 1 original movement. Not coded: the reverse direction (a disposal with no movement at commit). It would need one more deferred trigger; say if you want it.

Same class, **GAP (R2)**: a movement with `shortage_id` is not checked against the shortage (ingredient, sale/document line). Rev 4 s2.F says the movement "references ... shortage_id" for traceability. Included in the same proposed 0012. DECISION D-R2: accept.

## 2. Constraints, composite FKs, triggers vs Rev 3/4/5/6.3
Compared: every table/column/check/index in Rev 3 II.2, Rev 4 s2.A/B/D/E/F, s3, s4.1, s4.2, s5, Rev 5 s2.1/2.2/2.5/4.1, Rev 6.3 s3.1-3.8 and the C6 test. Composite-FK matrix (Rev 4 4.1): all 20 rows present. Index list (Rev 4 4.2 + Rev 3): all present. Value/sign/reference CHECKs, receipt uniqueness, reversal uniqueness, deferred consistency, depth guard, append-only, TRUNCATE guard, base-unit backstop, `ledger_effective` columns and attribution table: present.
Findings:
| # | Class | Finding |
|---|---|---|
| 2.1 | GAP (low) | Rev 4 s3 says only location, expiry_date, received_on may change on a batch; the guard rejects id, kitchen, ingredient, initial_qty, unit_cost (as Rev 5 lists) but not source_document_line_id / created_at. DECISION: add them? (not in proposed file) |
| 2.2 | GAP (low) | stock_shortages: status OPEN with a non-null resolution is allowed; docs only require RESOLVED => resolution. Domain code ignores resolution while open. DECISION: add `resolution IS NULL OR status='RESOLVED'`? |
| 2.3 | RISK | Not enforceable in DB with the documented schema: a SALE_CONSUMPTION movement's ingredient belonging to the sold dish's recipe (recipes are unversioned). Stays a service rule. |
| 2.4 | RISK | New tables in later migrations get Supabase default grants to anon/authenticated (0011 only revokes existing objects; plan forbids ALTER DEFAULT PRIVILEGES in Core). The C6 test catches it; each future migration must revoke. |
| 2.5 | RISK (U1, U10) | `security_invoker` needs PG15+ (Supabase 17.11 reported); depth values 1/2 are assumed. Both are verified only when tests/db runs. |
| 2.6 | NOTE | No ERROR (definite violation of a stated rule) was found in 0001-0011 by reading. SQL syntax is unverified. |
Missing tests required by 6.3 s3.1 (L1, L2, L3): were not in the first package. Added in `tests/db/test_guard_limits_db.py`, not run.

## 3. Reversal, deferred triggers, remaining_qty cache, sale_lines cache
Traced by hand:
- Reversal: needs original in same kitchen+batch, not a reversal, exact negation of qty and value, same snapshot cost; refs copied; `uq_sm_reverses` blocks double reversal; reversing a consumed receipt fails on `remaining_qty >= 0`. Reversal row passes `ck_sm_*` (type REVERSAL skips sign/ref rules). Attribution of a reversal = its original's (view uses original's type/occurred_on; sale/disposal/doc links are copied). Matches Rev 5 2.1 and 6.3 3.3.
- Cache: `trg_sm_apply` (AFTER INSERT, SECURITY DEFINER, `search_path=pg_catalog`, every object schema-qualified) updates the batch at trigger depth 2, so the guard allows it; a direct statement is depth 1 and fails. Deferred `check_batch_consistency` (batches insert/update, movements insert) re-checks sum, exactly one RECEIPT, RECEIPT qty = initial_qty at commit. Matches 6.3 3.1.
- sale_lines: `check_sale_line_cache` (sale_lines, movements, shortages) recomputes cogs = -sum(value_vnd) of SALE_CONSUMPTION incl. reversals, and FULL/PARTIAL/RESOLVED from shortage status; mismatch aborts commit. Consequence by design: any movement/shortage change on a sale line must be followed by `settle_sale_lines` in the same transaction (service not written yet).
- RISK: row-level deferred triggers recompute aggregates per row; fine for demo volumes, would need a statement-level rewrite for bulk loads.
- RISK: reset script must disable the `no_truncate_*` triggers (Rev 5 runbook) and re-enable them; `alembic_version` is excluded from the guard.
- Test caveat: tests use `SET CONSTRAINTS ALL IMMEDIATE`, which also makes later statements in the same transaction check immediately; fine for the tests as written.

## 4. Downgrade and rollback
- Upgrade atomicity: PostgreSQL DDL is transactional and env.py uses one transaction for the whole run, so a failure in any migration should roll everything back (assumed from PostgreSQL/Alembic behaviour, not tested). Side effect: after a failure at 0009 you re-run 0001-0008 too. DECISION (optional): `transaction_per_migration=True` in env.py trades that for partial states; not changed.
- Downgrade order, read through: 0011 -> 0010 -> 0009 -> ... -> 0001 respects FKs (children dropped before parents; truncate triggers dropped before `DROP SCHEMA ledger_internal CASCADE`; view before table).
- ERROR-class? No. But **RISK (high if misused)**: downgrades DROP TABLE, including the ledger, and the append-only trigger does not stop DROP. Development scratch DB only, never the real project.
- **RISK**: 0011 downgrade disables RLS but does NOT restore the grants it revoked (they cannot be reconstructed safely). So 0011 is not fully reversible. DECISION: accept (recommended) or document a manual re-grant.
- Downgrade not run anywhere.

## 5. env.py offline mode vs current Alembic config
Read against `alembic.ini` (script_location = alembic, prepend_sys_path = ., no sqlalchemy.url, no fileConfig call) and Alembic's documented offline pattern (`context.configure(url=..., literal_binds=True, dialect_opts=...)`): compatible; revisions are plain modules with `revision`/`down_revision`; filenames fine; run from `backend/`.
Findings: (a) RISK low: offline mode still needs `MIGRATION_DATABASE_URL` set (it only needs a dialect, not a connection). Fallback to a dummy `postgresql+psycopg://` URL when empty would remove the need to read a secret for a preview. Not changed (you asked not to modify existing code); say if you want it. (b) NOTE: SQL statements contain no percent signs and no colon-name tokens (checked by test), so text() and literal rendering should not mangle them. (c) `alembic downgrade 0011:0010 --sql` needs a revision range. (d) Not run: `alembic upgrade head --sql` has not been executed by me (Alembic is not installed in my sandbox).

## Review decisions needed from you
D-R1 (1 disposal = 1 movement; adopt proposed 0012?), D-R2 (shortage match), 2.1, 2.2, `transaction_per_migration`, 0011 downgrade grants, offline dummy URL.
Models stay NOT STARTED until database tests run and pass on a scratch database.


---
# Stage 2 implementation status (MVP build session)

Legend: CREATED = code written. Nothing below that touches SQLAlchemy, FastAPI, PostgreSQL or the frontend toolchain was
EXECUTED in the build sandbox (those libraries/DB/network are absent there). What WAS executed: py_compile on all
backend files, a coarse undefined-name lint, and 70 pure-logic test cases (domain rules, units, FEFO, replenishment,
AI planner/validator, migration static checks).

| Area | Status |
|---|---|
| Review 1 fixes (disposal/shortage vs movement, one movement per disposal, both directions; batch guard; shortage status/resolution) | Migration `0012_review_fixes.py` in versions/ (official). CREATED, SQL UNVERIFIED |
| Future-migration privilege rule | Enforced by a static test: any migration after 0011 that creates a table must ENABLE RLS and REVOKE |
| SQLAlchemy models (20 tables) | CREATED. Column parity with migrations: 0 mismatches by regex check; `tests/test_models_parity.py` needs SQLAlchemy (Windows) |
| Services: catalog, inventory (receipt, FEFO, disposals, overview, expiring, movements), sales (menu, sale, shortages, settle_sale_lines, manual sales-report documents), reporting (R1, RS1), idempotency (Rev 4 2.C), audit | CREATED, NOT EXECUTED |
| API (/api/v1): settings, units, ingredients, inventory, batches (+disposals), expiring-batches, dishes, documents, sales, shortages, reports/summary, replenishment-suggestions, assistant | CREATED, NOT EXECUTED; unauthenticated access returns 401 (test written, not run here) |
| AI: provider-independent core, rule-based provider, 7 read-only tools, output validator, deterministic fallback, audit of queries | CREATED; core logic tests PASS (5 cases); tools NOT EXECUTED |
| Frontend: login, Dashboard, Kho, Bán hàng, Báo cáo, Trợ lý AI | CREATED, `npm run build` NOT RUN, no lockfile |
| Seed: `python -m app.scripts.seed_demo --user-id <uuid>` (real services, idempotent) | CREATED, NOT RUN |
| DB tests: `tests/db` (ledger, guards L1-L3, review fixes, full service flow) | CREATED, NOT RUN (need migrated scratch DB) |

## Decisions I made (documented, not asked)
1. Review 1: all findings adopted via a NEW migration 0012 instead of editing 0009, so a database that already ran 0001-0011 can still upgrade.
2. Sales entry follows Rev 3 D1/D4/D7: manual SALES_REPORT document, lines (dish, portions), confirm. `IMPORT_INVOICE`, CSV/Excel upload, usage slips -> 501 NOT_IMPLEMENTED (receipts use POST /batches, I3).
3. API commits explicitly in each handler so deferred ledger triggers fail inside the request (a failure becomes a 409, not a silent post-response error).
4. Models declare no ForeignKey/relationship objects (composite keys, mapper config could not be executed). Services flush parents before children explicitly; queries use explicit joins.
5. Cursor pagination encodes an integer offset (simple, documented deviation from an opaque cursor).
6. Money rounding = half-up (D7 placeholder, one helper); expiry/replenishment parameters come from kitchen_settings placeholders.
7. Usage consumption is not part of COGS in R1 (D7 open; usage slips are Deferred).

## Requested by the master prompt but NOT implemented, with reason
- Suppliers / purchase orders: no table or contract in Rev 3/4/5/6.3 (Rev 4 lists "supplier and purchase orders" as Deferred). Not invented.
- User roles / permission management: Rev 3 D4 = single account, no roles. Settings screen is read-only.
- OCR: Deferred in 6.3.
- Pending-purchase and safety-stock inputs to recommendations: only `min_stock_qty` and the Rev 5 formula exist.
- Adjustments, COOK, WRITE_OFF_ESTIMATED, notifications, R2/R3, CSV import: Stretch in 6.3, not built.
- External LLM provider: D24 open; the provider interface exists, only the rule-based provider is implemented.

## Highest risks for the first real run
`0009` and `0012` SQL never ran in PostgreSQL; ORM/service code never imported with SQLAlchemy. Expect first-run fixes. Start with `tests/db` on a scratch database, then the service-flow test, then the seed.
