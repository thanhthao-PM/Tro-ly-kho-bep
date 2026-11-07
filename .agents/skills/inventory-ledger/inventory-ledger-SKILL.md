---
name: inventory-ledger
description: Applies the Kitchen Assistant inventory ledger, batch, expiry, FEFO, stock and costing rules. Use when changing or reviewing inventory, stock movements, batch consumption, unit conversion, expiry handling, shortages or ledger data.
---

# Inventory Ledger

## 1. Purpose

Protect the Kitchen Assistant inventory model. Treat the ledger as the source of truth; do not replace it with a manually maintained total-stock calculation.

## 2. Activate when

- Creating or reviewing receipt, sale-consumption, cook or shortage-related inventory behavior.
- Working with batches, expiry dates, FEFO, usable stock, stock caches or cost snapshots.
- Reviewing unit conversions, base-unit changes, ledger constraints or reconciliation.
- Investigating stock mismatch, negative-stock rejection or ledger integrity failures.

## 3. Do NOT activate when

- The task is limited to UI styling, unrelated API plumbing or general documentation.
- The user asks for a feature whose business rules are not in the approved sources. In that case, identify the missing contract and stop before inventing behavior.

## 4. Required documents

Read only the relevant sections first:

1. `docs/architecture/architecture-revision-6.3.md` — frozen source of truth.
2. `docs/architecture/ARCHITECTURE_REVISION_5.md` — cumulative ledger, API and database contracts; verify this path in the repository.
3. `docs/implementation/implementation-plan.md` — implementation sequence and Core Mode constraints.
4. `PROJECT_CONTEXT.md` — required by project handoff; its repository path/content was not available at Skill authoring time.
5. Revision 3 and Revision 4 source documents — referenced by later revisions but not supplied. If a task depends on their detailed contracts, mark the contract `NOT SPECIFIED` and request the source.

## 5. Core rules

- Architecture Revision 6.3 is **FROZEN**. Never edit it to make implementation easier. OPEN decisions remain OPEN.
- Core Mode is the baseline. D30a is **PROPOSED / DISABLED**. Do not create or activate `app_runtime` / `ledger_owner`, transfer function ownership, or add D30a policies.
- Ledger-first: the stock movement ledger is authoritative. `batches.remaining_qty` is a derived/cache value guarded by database logic; do not update it as an independent source of truth.
- Preserve all nine documented movement types, their sign/reference rules, cost snapshots, reversal validation and database-side consistency safeguards. Do not invent or rename movement types.
- Preserve the non-negative stock invariant. A transaction that would create negative stock must fail and roll back atomically.
- Preserve batch-level expiry and FEFO. Use the single documented `usable(batch)` definition consistently; do not create a second definition for reports, replenishment or assistant tools.
- Expiry boundaries are kitchen-local: `EXPIRED` when expiry is before today; `EXPIRES_SOON` includes today and the configured warning-day upper boundary; null expiry is `NO_EXPIRY`. Do not invent the configurable warning value.
- Explicit handling of an expired batch is governed separately by `expired_batch_actions`. A COOK action on an expired batch requires the documented `COOK` permission. Do not treat this as permission to consume expired stock automatically in ordinary FEFO.
- Costing must use the applicable batch cost snapshots and signed ledger values. Preserve the distinction between signed `stock_movements.value_vnd` and positive remaining `batches.stock_value_vnd`. Do not recompute historical cost from current ingredient prices.
- Base-unit changes are locked once operational data exists, including empty batches and the other documented reference categories. Do not implement historical rebasing as a shortcut.
- Keep kitchen isolation: all tenant-scoped repository reads/writes must use the authenticated `kitchen_id`; preserve composite foreign keys and cross-kitchen protections.
- Do not invent formulas, columns, API routes, movement types, status values or accounting policies. If not in the source, write `NOT SPECIFIED`.

## 6. Recommended procedure

1. Identify the exact operation and its approved contract; locate the corresponding schema, trigger, service and tests.
2. Trace the write path from domain action through service transaction to ledger movement and database guards.
3. Confirm batch selection uses the shared `usable(batch)` rule and FEFO ordering.
4. Confirm quantities and units are normalized according to the approved base-unit/conversion contract.
5. Confirm cost snapshots and signed values are preserved; do not silently use current prices for historical movements.
6. Check rollback, idempotency and concurrency implications before changing transaction boundaries.
7. Add or update tests at the correct tier. Never move a Core invariant into Stretch to avoid implementing it.
8. Report any dependency on missing Revision 3/4 contracts or OPEN decisions.

## 7. Validation checklist

- [ ] Ledger is still the source of truth; no independent stock-total write path was added.
- [ ] Movement type, sign, reference and cost-snapshot rules match the source.
- [ ] No path can commit negative stock.
- [ ] FEFO and every consumer use the shared `usable(batch)` definition.
- [ ] Expiry boundary and explicit expired-batch action rules are preserved.
- [ ] Base-unit immutability and conversion constraints are preserved.
- [ ] Tenant reads/writes are scoped by authenticated `kitchen_id`.
- [ ] Database triggers, composite FKs and reconciliation checks remain intact.
- [ ] Relevant Core DB and Core Integration tests are retained and executed where possible.
- [ ] No D30a, new movement type, formula or schema rule was introduced without approval.

## 8. Common mistakes

- Treating `remaining_qty` as the primary stock record.
- Selecting batches by receipt date instead of the documented FEFO rule.
- Using different usable-stock logic in reporting and consumption.
- Recalculating historical COGS from current prices.
- Allowing a client or request body to choose another kitchen's `kitchen_id`.
- Changing base units after operational data exists.
- Treating D30a or Stretch workflows as Core.
- Assuming an absent contract from a class name or UI mock-up.

## 9. Expected handoff

Provide: changed files; movement/transaction path; source sections relied on; tests run with command, exit status and evidence; tests not run; migration impact; and unresolved contracts/decisions. Do not claim correctness without fresh evidence.
