---
name: backend-module
description: Implements and reviews Kitchen Assistant FastAPI backend modules using the approved modular-monolith, SQLAlchemy and Supabase boundaries. Use for routers, services, repositories, schemas, authentication, validation, transactions or API integration.
---

# Backend Module

## 1. Purpose

Implement backend behavior without drifting from the frozen architecture or inventing API contracts.

## 2. Activate when

- Creating or modifying FastAPI routers, dependencies, services, repositories or request/response schemas.
- Working with SQLAlchemy 2.x synchronous sessions, psycopg 3, Supabase PostgreSQL/Auth, transaction handling or API errors.
- Reviewing kitchen-scoped data access, authentication, validation or backend integration.

## 3. Do NOT activate when

- The task is exclusively frontend presentation, database schema design or ledger business-rule design; use the corresponding Skill.
- The requested endpoint/schema is not documented. Do not create a plausible substitute.

## 4. Required documents

- `docs/architecture/architecture-revision-6.3.md` — frozen architecture and API/database contracts.
- `docs/implementation/implementation-plan.md` — implementation phases, runtime configuration and module layout.
- `docs/architecture/ARCHITECTURE_REVISION_5.md` — cumulative API and database contract; verify repository path.
- `PROJECT_CONTEXT.md` — required but unavailable during authoring; locate before implementation.
- Revision 3/4 source contracts — not supplied. Do not infer their details from Revision 5/6.3 summaries.

## 5. Core rules

- Stack: FastAPI modular monolith; SQLAlchemy 2.x **synchronous**; psycopg 3; Supabase PostgreSQL and Supabase Auth. Alembic is the sole schema authority.
- Do not add frameworks, async database access, dependencies, service boundaries or deployment components without approval.
- Keep responsibilities separated: router handles HTTP mapping/dependencies; service owns use-case orchestration and transaction boundaries; repository owns persistence queries; schemas validate/serialize API data. Match the existing repository conventions if they differ; do not force a new layout.
- API routes, request/response fields, status codes, error codes and idempotency behavior must come from approved contracts. Missing details are `NOT SPECIFIED`.
- Supabase Auth is selected. JWT verification algorithm/key discovery and claim mapping must follow verified project configuration. U12 is not proven merely because verification code exists; do not assume HS256, RS256, ES256 or JWKS configuration.
- Derive kitchen context from the authenticated identity/profile flow. Never trust a client-supplied `kitchen_id` as authorization. Every tenant-scoped repository operation must filter by the authenticated kitchen and preserve composite-FK references.
- Core Mode uses the documented owner/admin connection arrangement. D30a remains **PROPOSED / DISABLED**; do not create custom runtime roles, transfer ownership or introduce `app_runtime` policies.
- The implementation plan describes Supabase Transaction Pooler for runtime and Session Pooler/direct Port 5432 for migrations; psycopg 3 server-side prepared statements are disabled with `prepare_threshold=None` for Transaction Pooler and require environment verification. Do not hardcode secrets or assume connectivity has been verified.
- Run Alembic migrations through the approved deployment/CI step. Never run `alembic upgrade head` during FastAPI startup. Never perform ad-hoc schema changes.
- Preserve atomic transactions, rollback, concurrency locks and idempotency contracts for inventory operations. Never catch a database integrity failure and continue as if the operation succeeded.
- Validate input at the boundary, but keep business invariants in the domain/service and database layers where specified. Do not duplicate business rules with subtly different semantics.
- D20 conflict: Revision 6.3 lists production hosting as OPEN; the Implementation Plan states Firebase Hosting + Cloud Run. Record this discrepancy and follow the owner's explicit decision; do not resolve it inside backend code.

## 6. Recommended procedure

1. Inspect existing module structure and root instructions before editing.
2. Find the endpoint and schema contract in the authoritative architecture sources.
3. Trace authentication → kitchen context → router → service → repository → transaction/database constraints.
4. Check whether the operation is Core, Stretch or Deferred.
5. Implement the smallest change consistent with existing conventions.
6. Add validation and error mapping only where specified; label missing behavior `NOT SPECIFIED`.
7. Test transaction rollback, tenant isolation and relevant failure paths, not only the happy path.
8. Inspect the diff for accidental schema changes, secrets, dependency changes and contract drift.

## 7. Validation checklist

- [ ] Existing repository conventions were inspected and preserved.
- [ ] No endpoint or API field was invented.
- [ ] Authenticated kitchen context is enforced in every tenant-scoped query.
- [ ] Supabase Auth/JWT assumptions are verified, not guessed.
- [ ] SQLAlchemy usage remains synchronous and uses psycopg 3.
- [ ] Transaction, rollback, idempotency and concurrency behavior match the contract.
- [ ] Alembic remains the only schema authority; no migration runs at app startup.
- [ ] Core Mode remains active; D30a remains disabled.
- [ ] Error responses do not hide integrity failures or leak secrets.
- [ ] Tests and build claims have fresh evidence.

## 8. Common mistakes

- Inventing REST endpoints or response schemas from UI labels.
- Treating RLS as the sole tenant-isolation boundary in Core Mode.
- Accepting `kitchen_id` from request payloads for authorization.
- Assuming JWT signing algorithm/claims before U12 verification.
- Using async SQLAlchemy or adding a new ORM.
- Running migrations at startup or applying SQL outside Alembic.
- Introducing `app_runtime` / `ledger_owner` before D30a gates pass.
- Returning success after a failed or rolled-back transaction.

## 9. Expected handoff

List changed backend files, contract references, transaction/auth/tenant implications, migrations (if any), test commands and evidence, unverified environment assumptions, and unresolved API details.
