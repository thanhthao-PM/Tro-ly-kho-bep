# Architecture Revision 6.3: Frozen Core Baseline

**Project:** AI Kitchen Inventory Assistant (hackathon MVP)
**Status:**

- **Core architecture: FROZEN.**
- **D30a: PROPOSED / DISABLED.** It is gated by FU-1, the C2 policy tests, and the U2–U9 verifications.

**Scope:** Documentation only. This is Revision 6.2 with approved corrections C1–C6 applied. No code, SQL, migrations, tests, files, folders, skills, hooks, agent instructions or implementation plans were created or modified.

**Document composition.** This text consolidates Revision 6.2 with corrections C1–C6. As in Revisions 6 and 6.2, the contracts it builds on remain referenced by section and are unchanged: Revision 3 (ERD, tables, API contracts, AI contracts), Revision 4 (unit conversion 2.A, idempotency 2.C, cook endpoint 2.D, composite FK matrix 4.1, indexes 4.2), and Revision 5 (sign convention and formulas 2.1, R1 schema 2.3, replenishment table 2.4, expiry boundaries 2.6).

**Verification vocabulary**

- **Documented design:** specified here.
- **Proposed implementation:** the planned mechanism, not yet built.
- **Verified behavior:** shown by an executed test on the chosen PostgreSQL and Supabase setup. Nothing here is at this level.
- Statements marked _recalled_ describe PostgreSQL or Supabase behavior from general knowledge and must be tested before anyone relies on them.

---

## 1. Baseline carried unchanged

**Accepted decisions:** React + TypeScript + Vite; FastAPI modular monolith; Supabase PostgreSQL; SQLAlchemy 2.x (sync, psycopg 3); Alembic as sole schema authority; Supabase Auth; single account and single kitchen (seed and reset, no runtime provisioning); `kitchen_id` with composite FKs; actual batch-cost snapshots; stock never negative; ledger plus FEFO; shortage Option C; base units with conversion rules; provider-independent AI with the rule-based provider as default; replenishment formula (D25).

**Ledger sign convention (Revision 5, 2.1):** `qty_delta` and `value_vnd` are signed by direction with the same sign. Inflows are positive, outflows negative. A reversal has `qty_delta = −original.qty_delta`, `value_vnd = −original.value_vnd`, the same `unit_cost_snapshot` and the same references. Costs are reported as `−Σ value_vnd` per category. `CHECK (cogs_vnd >= 0)` stays.

---

## 2. Decision status: specified behavior versus OPEN policy

Some behavior is specified and will be implemented. The OPEN decisions concern whether the business or food-safety owner **approves** it as policy. Changing an approved value later touches one place, not the architecture.

| Topic                        | Specified now (implemented as written; placeholder where noted)                                                                                        | Where a change would land     | **Still OPEN**                                                                                                      |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| Movement attribution date    | Sale date; document date for usage; disposal date; otherwise movement date; reversals follow the original (3.3). Replenishment uses it unchanged (3.5) | `ledger_effective` definition | **D7:** whether accounting approves period matching by sale date                                                    |
| Profit and cost presentation | Both `excluding_estimates` and `including_estimates` figures, `ESTIMATE` labels, status-based `all_actual`                                             | R1/R3 composition             | **D7:** headline figure, usage slips in COGS, donation treatment, estimate presentation, rounding, report naming    |
| Expiry classification        | `EXPIRED` iff `expiry_date < today`; `EXPIRES_SOON` iff `0 ≤ days ≤ w` (Revision 5, 2.6); `OK`; `NO_EXPIRY`                                            | One classification function   | **D9:** whether these labels may serve as food-safety statements                                                    |
| Expired-stock handling       | Two-setting mechanism and `usable(batch)`, placeholder defaults (`false`, `{WASTE}`)                                                                   | Kitchen settings values       | **D9:** actual defaults and what may be done with expired stock                                                     |
| Expiry requirement           | Required when the ingredient tracks expiry                                                                                                             | `tracks_expiry` values        | **D9a:** which ingredients track expiry                                                                             |
| Other D9 items               |                                                                                                                                                        |                               | Safety buffers, opened-package shelf lives, shelf-life and storage-tip catalog, back-dated report eligibility (D9b) |

---

## 2A. Freeze criteria _(correction C3)_

> Core implementation proceeds on the working baseline D29, D30, D31, D32, D33, D34, D4a and the D23 optional set. At freeze they are adopted as the Core baseline and changed afterwards only through change control. D7, D9/D9a/D9b, D18, D20, D24, D26 and the placeholder parameters may remain OPEN. Unverified items U2–U9 gate D30a only. Items U1, U10, U12 and U13 are verified at the start of Core implementation, each with a documented fallback.

---

## 3. Architecture sections

### 3.1 D30: what the trigger-depth guard does and does not do

**The limitation.** `pg_trigger_depth()` reports how deeply triggers are nested. It does not say _which_ trigger is running. The guard on `batches` raises when `remaining_qty` changes at depth below 2. Any trigger, on any table, that issues an `UPDATE batches` runs at depth 2 and passes the guard. The movement trigger is therefore not authenticated by the guard, only indistinguishable from other trigger-initiated updates.

**What it is for.** It stops accidental or direct statements from application code, ad-hoc SQL and fixtures. It is **not** a security boundary.

**What protects the cache, strongest first**

| Layer                                                                                                                                                                                                                                                          | Protects against                                                                                      | Limits                                                                                                                                                                                                                                             |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Deferred consistency constraint trigger (on `batches` after insert or update, and on `stock_movements` after insert): at commit each touched batch must satisfy `remaining_qty = Σ qty_delta`, exactly one `RECEIPT` exists, and its `qty_delta = initial_qty` | Any path, including a rogue trigger, that leaves the cache inconsistent with the ledger cannot commit | Cannot catch an inconsistency the ledger itself agrees with (a forged but well-formed movement). Skipped if triggers are disabled (`session_replication_role = replica`, `DISABLE TRIGGER`), which needs privileges the runtime role must not have |
| Privileges (D30a): `app_runtime` has no `TRIGGER`, no `CREATE` on the schema, no `ALTER`, no `TRUNCATE`, no column privilege on `batches.remaining_qty`                                                                                                        | Runtime cannot define a rogue trigger or write the cache directly                                     | Exists only once D30a is adopted and verified                                                                                                                                                                                                      |
| Allowlist schema test: enumerate triggers and functions that reference `batches`; only the movement apply function may                                                                                                                                         | A rogue trigger added by a migration or script is caught in CI                                        | Heuristic text match; code review remains necessary                                                                                                                                                                                                |
| Trigger-depth guard                                                                                                                                                                                                                                            | Direct and accidental updates                                                                         | Not authentication                                                                                                                                                                                                                                 |

**Tests**

- **L1 (Core, limitation test):** create a test-only trigger on a scratch table whose function updates `batches.remaining_qty`. Assert that the guard does _not_ block it (documenting the limitation). Assert the transaction **fails at commit** through the consistency trigger. Assert that a paired change that keeps the cache equal to Σ is impossible without a ledger row.
- **L2 (Core):** a `DO` block and a plain function update are rejected by the guard. The test report states that these cover direct paths only.
- **L3 (Core, schema test):** the allowlist test above.
- **L4 (Stretch, as `app_runtime`):** `CREATE TRIGGER`, `CREATE FUNCTION`, `ALTER TABLE` and `UPDATE batches SET remaining_qty` fail with permission errors.

No new write architecture is introduced.

### 3.2 D30a: runtime role, cache function and policies (PROPOSED, DISABLED, unverified)

#### 3.2.1 The conflict and its resolution

A trigger function runs with the privileges of the user whose statement fired it. `app_runtime` cannot update `remaining_qty`, so the cache trigger would fail for it. **Resolution (proposed implementation):** the cache-maintenance function is `SECURITY DEFINER`.

#### 3.2.2 Ownership and execution identity

| Object                                                                                           | Owner                                                                                                                                                                                               |
| ------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| All tables, the `ledger_effective` view, schema `ledger_internal`                                | The migration owner. This is the single admin credential (`ADMIN_DATABASE_URL`); "migration owner" and "admin" are the same role.                                                                   |
| The cache function (one function, in `ledger_internal`, `SECURITY DEFINER`, fixed `search_path`) | **Core mode:** the migration owner. **D30a mode:** `ledger_owner`, after step 5(d) of 3.2.6.                                                                                                        |
| Triggers                                                                                         | No separate owner. The cache trigger belongs to `stock_movements` (after insert) and calls the function. The guard and consistency triggers on `batches` are separate `SECURITY INVOKER` functions. |

**Transfer procedure (step 5(d), in order):** (i) grant `CREATE` on `ledger_internal` to `ledger_owner`; (ii) transfer the function's ownership to `ledger_owner`; (iii) revoke that `CREATE`. Prerequisites to verify: the admin role is a member of `ledger_owner`, and `ledger_owner` has `CREATE` on the function's schema at the moment of transfer.

**Interim state:** between steps 3 and 5 the function runs as the migration owner. `app_runtime` holds no privileges until step 5, so the API is not started in D30a mode before step 6 passes.

**Lifecycle rule:** the cache function may only be changed with replace-in-place (which keeps the owner), by a role that is a member of `ledger_owner`. Drop-and-create is prohibited for it. Reconciliation (after every migration) and the catalog audit (owner = `ledger_owner`) detect any reversion.

**Execution identity (to verify):** the cache function runs as its owner. The `batches` guard trigger, when fired from inside the cache function, runs as `ledger_owner`; it reads no tables. The identity of the deferred consistency triggers at commit (session user versus the role current when the event was queued) is **unverified**. Required outcome: a real receipt and consumption executed as `app_runtime` commit successfully (T2 tests 1 and 2). If verification shows they run as `ledger_owner`, extending `ledger_owner` with `SELECT` on `stock_movements` would be needed. That would be a change requiring explicit approval and is **not proposed now**.

#### 3.2.3 Function specification

| Aspect                               | Specification                                                                                                                                                      |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Owner                                | See 3.2.2                                                                                                                                                          |
| Minimum privileges of `ledger_owner` | `SELECT` on `batches`; `UPDATE (remaining_qty)` on `batches`; nothing else. **No privilege is added to this list by this revision.**                               |
| `search_path`                        | Fixed in the function definition to `pg_catalog` only. Every object reference inside is schema-qualified                                                           |
| Location                             | Schema `ledger_internal`, not exposed through the Supabase API, created in migration 0009                                                                          |
| Execute privilege                    | `EXECUTE` revoked from `PUBLIC`, `anon`, `authenticated`. Trigger functions cannot be called directly in any case (return type `trigger`)                          |
| Parameters, dynamic SQL              | None. Reads only `NEW`; updates only the batch named by `NEW.batch_id` (matched on id, kitchen and ingredient) by adding `NEW.qty_delta`; zero rows updated raises |
| Escalation surface                   | The only way to change `remaining_qty` is to insert a ledger row, the intended path. No callable entry point, no search-path hijack, no dynamic SQL                |

All other triggers (validation, reversal rules, immutability, guards, deferred consistency, base-unit backstop) are `SECURITY INVOKER`.

#### 3.2.4 Privileges for `app_runtime`

**Rule: revoke first, then grant by column.** In PostgreSQL a table-level privilege covers all columns, and column grants add to it, so a surviving table-level grant would make a column list meaningless. For every restricted table the reconciliation step: (1) revokes all table-level privileges from `app_runtime` and `PUBLIC`; (2) grants only the permitted column or privilege set; (3) audits the result.

- **`batches`:** `INSERT` on `id, kitchen_id, ingredient_id, received_on, expiry_date, initial_qty, unit_cost, location, source_document_line_id, created_at` only (**`remaining_qty` excluded**, so it takes its default of 0). `UPDATE` on `location, expiry_date, received_on` only. `SELECT` on all columns. No `DELETE`, `TRUNCATE`, `TRIGGER` or `REFERENCES`.
- **`sale_lines`:** same pattern; `UPDATE` only on `cogs_vnd, consumption_status` (3.4).
- **Ledger and audit tables:** `SELECT` and `INSERT` only. **Other tenant tables:** ordinary DML, never `TRUNCATE` or `TRIGGER`.
- **Default privileges:** reconciliation verifies that no `ALTER DEFAULT PRIVILEGES` rule grants anything to `app_runtime` or `PUBLIC` on new tables.

**Privilege audit (catalog test, Stretch, required for D30a):** no table-level `INSERT` or `UPDATE` on `batches` or `sale_lines` for `app_runtime` or `PUBLIC`; no column privilege on `batches.remaining_qty` other than `SELECT`; no `UPDATE`, `DELETE` or `TRUNCATE` on `stock_movements` or `audit_log`.

#### 3.2.5 RLS policies

RLS is enabled on every table (migration 0011). Because RLS with no policies hides everything from non-owner roles, D30a adds explicit policies:

- **Tenant tables, `app_runtime`:** kitchen-scoped policy (see 3.3.2). _The explicit `USING` / `WITH CHECK` wording of these policies is follow-up issue FU-1 (section 9); the design is unchanged._
- **`units`:** see 3.3.3.
- **`ledger_owner` policies:**

| Policy name                   | Table     | Command  | Role           | `USING` | `WITH CHECK`                                         |
| ----------------------------- | --------- | -------- | -------------- | ------- | ---------------------------------------------------- |
| `ledger_owner_select_batches` | `batches` | `SELECT` | `ledger_owner` | `true`  | not applicable                                       |
| `ledger_owner_update_batches` | `batches` | `UPDATE` | `ledger_owner` | `true`  | `true` (written explicitly, not left to the default) |

- No other policy names `ledger_owner`: no `INSERT`, `DELETE` or `ALL` policy, and none on any other table. No policy is granted to `PUBLIC`. `FORCE ROW LEVEL SECURITY` is not used on any table (Core mode relies on the owner bypassing RLS).
- `ledger_owner` is not subject to the session kitchen setting. This is accepted because: it holds `UPDATE` on `remaining_qty` only (it cannot change `kitchen_id`, `ingredient_id` or any cost column); the cache function updates only the batch named by `NEW`, matched on id, kitchen and ingredient; and the commit-time consistency trigger rejects any resulting mismatch.
- Step 5(f) of 3.2.6, for `ledger_owner`, drops and recreates exactly these two policies by name. _(correction C5)_

#### 3.2.6 Bootstrap, migration and reconciliation order

Migration 0011 contains no role-specific statements: a conditional statement silently does nothing when a role does not exist yet. All role-specific work is one **idempotent reconciliation step** that fails loudly if a required role is missing.

- **Core mode (D30a not enabled):** no custom roles; migrations run as the owner role; only steps 2–4 apply.
- **D30a mode (PROPOSED, DISABLED):** the full sequence.

> _(correction C1)_ D30a must not be enabled (steps 1–6 not run; the API not started with `app_runtime`) until FU-1 is closed: every `app_runtime` policy documented with its command, `USING` and `WITH CHECK`, and the T2 policy tests pass. Core mode is independent of FU-1: it uses the owner role (RLS bypassed, `FORCE` not used), and no Core feature or Core test depends on `app_runtime` policies.
>
> Step 6's policy-coverage audit asserts the documented policy set exactly (name, table, command, roles, `USING`, `WITH CHECK`).
>
> FU-1 scope also covers: (a) tables without `kitchen_id` (`kitchens`, `user_profiles`); (b) the name and per-transaction setter of the session kitchen setting, mandatory in every runtime transaction; (c) T2 tests per command: allowed for the set kitchen, denied for another kitchen, denied when unset, and `WITH CHECK` rejecting cross-kitchen inserts and updates.

| Step | Action                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | Run by                  |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------- |
| 1    | Create roles `ledger_owner` (`NOLOGIN`) and `app_runtime` (`LOGIN`, password from the secret store). Neither is superuser, neither has `BYPASSRLS`, neither is a member of the other. Add the admin role (the migration owner) as a member of `ledger_owner`.                                                                                                                                                                                                                                                                                                                                                                    | Admin, outside Alembic  |
| 2    | Alembic 0001–0008 (tables and checks)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | Admin (migration owner) |
| 3    | Alembic 0009: schema `ledger_internal`; cache function (owned by the migration owner at this point, `SECURITY DEFINER`, fixed `search_path`); all triggers; deferred consistency triggers; base-unit trigger; `ledger_effective` (`security_invoker`)                                                                                                                                                                                                                                                                                                                                                                            | Admin (migration owner) |
| 4    | Alembic 0010–0011: remaining tables; RLS enabled on every table including `units`; revoke everything from `anon`, `authenticated`, `PUBLIC` on tables, the view and `ledger_internal`                                                                                                                                                                                                                                                                                                                                                                                                                                            | Admin (migration owner) |
| 5    | **Reconciliation** (idempotent; re-run after every migration and whenever a role is created later): (a) abort if either role is missing; (b) schema grants; (c) `ledger_owner`'s minimal table privileges (3.2.3); (d) transfer the cache function's ownership by the procedure in 3.2.2; (e) revoke-then-grant for `app_runtime` (3.2.4); (f) drop and recreate all named policies: the kitchen-scoped policies for tenant tables, the `units` read policy, and the two `ledger_owner` policies in 3.2.5; (g) grants on `ledger_effective` (3.3.4); (h) revoke `EXECUTE` on the function from `PUBLIC`, `anon`, `authenticated` | Admin                   |
| 6    | **Verification:** the privilege audit (3.2.4), a policy-coverage audit asserting every table in `public` has RLS enabled and a defined policy set for `app_runtime`, then the T2 tests. Any gap fails the deployment                                                                                                                                                                                                                                                                                                                                                                                                             | Admin and CI            |

A role created late cannot silently miss grants: step 5 applies everything, and step 6 fails the deployment on any gap, including for tables added by future migrations.

**Minimum schema privileges**

| Role           | `public`                              | `ledger_internal`                                                                                                      | Other schemas |
| -------------- | ------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- | ------------- |
| `ledger_owner` | `USAGE` (to resolve `public.batches`) | `USAGE`; `CREATE` only during the ownership transfer, then revoked                                                     | None          |
| `app_runtime`  | `USAGE`                               | None (the trigger function is not called directly; whether any schema privilege is needed to fire it is **to verify**) | None          |

#### 3.2.7 Required tests (T2, Stretch; D30a stays PROPOSED until all pass on the target environment, local Postgres and the Supabase dev project)

1. A real receipt (batch insert plus `RECEIPT` movement) as `app_runtime` succeeds and the cache shows the quantity.
2. Real consumption (FEFO, multi-batch) succeeds and the cache decreases; over-consumption fails and rolls back.
3. Direct update of `remaining_qty`, ledger `UPDATE`/`DELETE`, `TRUNCATE`, and insertion with a non-default `remaining_qty` all fail with permission errors.
4. Catalog test: the function has `prosecdef = true`, owner `ledger_owner`, a fixed `search_path`, and no execute grant to `PUBLIC`/API roles.
5. Reads through `ledger_effective` return only the kitchen set in the session (3.3).
6. The privilege audit (3.2.4).
7. A catalog test that `pg_policies` lists exactly the two `ledger_owner` policies in 3.2.5. An admin session that is a member of `ledger_owner` and assumes its role confirms that `INSERT` or `DELETE` on `batches`, `UPDATE` of any other column, and `SELECT` on any other tenant table all fail. A direct `UPDATE` of `remaining_qty` is blocked by the depth guard. _(correction C2, appended:)_ The catalog assertions are: (a) the set of policies in `pg_policies` whose roles contain `ledger_owner`, `public`, or any role `ledger_owner` is a member of equals exactly the two approved policies (name, table, command, permissive, `USING`, `WITH CHECK`); (b) no policy anywhere targets `public`; (c) `ledger_owner` has no role memberships (only the admin role is a member of it); (d) the privileges held by `ledger_owner`, across all tables and columns, equal exactly `SELECT` on `batches` and `UPDATE (remaining_qty)` on `batches`, plus the schema privileges in 3.2.6.

Whether the platform allows creating `ledger_owner`, transferring function ownership, and connecting as a custom role through the pooler is **unverified**. If it does not, Core mode (owner role) is unaffected.

### 3.3 `ledger_effective`: view, grants and isolation

#### 3.3.1 Definition and attribution

Read-only view, one row per movement: `category` (the movement's type, or the original's type for a `REVERSAL`), `attribution_date`, `kitchen_id`, references, signed values.

| Movement                                    | `attribution_date`        |
| ------------------------------------------- | ------------------------- |
| Has `sale_line_id`                          | `sales.business_date`     |
| `USAGE_CONSUMPTION` with `document_line_id` | `documents.business_date` |
| Disposal-linked                             | `disposals.occurred_on`   |
| All others                                  | `occurred_on`             |
| `REVERSAL`                                  | Same as its original      |

#### 3.3.2 Security design

- Created with **`security_invoker = true`**, so the caller's privileges and RLS apply to the base tables. Requires PostgreSQL 15 or later (_recalled_; verify the version of the Supabase project and the local test image). If lower, replace the view with a parameterized SQL function with default invoker semantics, same logic, same tests.
- On Supabase a view without `security_invoker` runs with its owner's rights and ignores the caller's RLS, and views in an exposed schema can be reachable through the Data API (_recalled_). The view is therefore also revoked from `anon` and `authenticated`.
- **Isolation for `app_runtime`:** base-table RLS policy on every tenant table: `kitchen_id` equals the kitchen id set in the session by the backend (`SET LOCAL` once per request transaction, from the verified kitchen resolution, never from request input). Unset means no rows (fail-closed).
- This is defense-in-depth against application bugs such as a forgotten filter. It is **not** a boundary against arbitrary SQL in the runtime session, which could set another kitchen id. Acceptable for a single-kitchen MVP.
- **Core tier (owner role, RLS bypassed):** isolation rests on kitchen-scoped repositories and composite FKs. The view carries `kitchen_id` and no service queries it without a kitchen filter.
- **Read-only:** `SELECT` is the only privilege granted on the view.

**Cross-kitchen tests on the view:** _Core:_ two-kitchen fixtures with overlapping data; every reporting, replenishment and assistant query returns only its own kitchen; a static test fails if a reporting repository method lacks a `kitchen_id` parameter. _T2 (Stretch):_ as `app_runtime` with kitchen A set, zero kitchen-B rows; with the setting unset, zero rows; `anon` and `authenticated` have no access.

#### 3.3.3 Shared `units` table

`units` has no `kitchen_id`. RLS is enabled (migration 0011). In D30a mode:

| Role                              | Access                                                                                                                                                                          |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `app_runtime`                     | `SELECT` privilege and one permissive `SELECT` policy (`USING (true)`). No `INSERT`, `UPDATE`, `DELETE` or `TRUNCATE` and no write policy. Units change only through migrations |
| `ledger_owner`                    | Nothing                                                                                                                                                                         |
| `anon`, `authenticated`, `PUBLIC` | Nothing                                                                                                                                                                         |

Foreign-key validation from `ingredients` and `ingredient_unit_conversions` to `units` is done by the database's internal referential checks, which as recalled from PostgreSQL's documentation do not go through row security, so creating an ingredient needs no extra privilege on `units`. **Verify** on the target version. **Tests (Stretch, T2):** `app_runtime` reads units; every write or `TRUNCATE` on `units` fails; creating an ingredient with a valid base unit works; a missing unit is rejected by the FK.

#### 3.3.4 Access to `ledger_effective`

- `GRANT SELECT ON ledger_effective TO app_runtime`; nothing else on the view.
- `anon`, `authenticated`, `PUBLIC`: no privilege on the view or on `ledger_internal`.
- Because the view is `security_invoker`, the caller needs `SELECT` on every underlying table (`stock_movements`, `sale_lines`, `sales`, `disposals`, `documents`, `document_lines`, and any other table in the final definition; the privilege audit enumerates them from the catalog), and each table's RLS applies to the caller. `app_runtime` already has `SELECT` on all tenant tables, so the kitchen-scoped policies apply.
- **Tests (T2, Stretch):** `app_runtime` can select from the view; `anon` and `authenticated` cannot; with kitchen A set, no kitchen-B rows; with the setting unset, no rows; writes against the view fail.

### 3.4 `sale_lines.cogs_vnd` and `consumption_status`: one authority

The ledger is the only source of truth. `cogs_vnd` and `consumption_status` are caches written by **one** function, `settle_sale_lines(line_ids)`, in the `sales` module.

- `cogs_vnd = −Σ value_vnd` over the line's effective movements with category `SALE_CONSUMPTION` (reversals net inside the category), or 0.
- `consumption_status`: `FULL` if never short; `PARTIAL` if any shortage is `OPEN`; `RESOLVED` if it has shortages and none is open.
- **When it runs:** at the end of every operation that inserts a movement referencing a sale line or changes one of its shortages (sales confirm, cook, all three shortage resolutions, the deferred reversal operation), in the **same transaction**. Under READ COMMITTED a reader sees the state before or after the commit, never an intermediate one.
- **Verification at commit:** a deferred constraint trigger on `sale_lines`, `stock_movements` and `stock_shortages` recomputes both values for touched lines and rejects the commit on mismatch.
- **Reports do not read the cache.** R1, R3 and replenishment compute from `ledger_effective`. The cache serves S1 and S2. `estimated_cogs_vnd` on a sale line is derived at read time from shortages, not stored.
- **Reconciliation tests (Core):** full consumption; partial; `CONSUME_FROM_STOCK`; `WRITE_OFF_ESTIMATED` (cogs unchanged, `RESOLVED`); `WAIVE`; two lines of one sale; reversal fixture reduces `cogs_vnd` and cannot make it negative; a wrong write fails at commit; a second connection during an open writer transaction sees only the old state.

### 3.5 Replenishment date basis

Both the historical window and consumption use **`ledger_effective.attribution_date`**.

- `history_start` = `MIN(attribution_date)` over the ingredient's effective ledger rows (any category). No effective rows → `NO_HISTORY`; the coverage rule is skipped and `MIN_STOCK_ONLY` may still apply.
- `history_start` later than yesterday → `observed_days = 0`, reason `NO_COMPLETE_DAYS`; no average computed.
- `window_end = yesterday`; `window_start = max(window_end − window_days + 1, history_start)`; `observed_days = max(0, window_end − window_start + 1)`.
- `consumption = −Σ qty_delta` over effective rows with category `SALE_CONSUMPTION` or `USAGE_CONSUMPTION` and `attribution_date` in the window.
- The classification table, formulas, rounding, `order_step` and RS1 schema from Revision 5, 2.4 are unchanged. `observation.from` is the window start actually used.
- A late-resolved shortage is attributed to the sale's date, so history may start earlier than the first receipt.
- With `expired_batches_consumable = true`, expired stock counts in `usable_qty` through the shared definition (3.7), lowering suggestions (D9 placeholder).
- **Tests (Core):** no rows; all rows today; one complete day; history shorter than `min_history_days`; longer than the window; late resolution extending `history_start`; reversal netting; `MIN_STOCK_ONLY` alongside `insufficient_data`; `avg = 0`.

### 3.6 `all_actual`, `has_open_shortages`, R1 and R3

Definitions use **shortage records and statuses** attributed to the period (through the sale line's `sales.business_date`, or the document's `business_date` for usage-slip shortages), never amounts.

| Flag                 | Definition                                                                                                                                            |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| `has_open_shortages` | At least one attributed shortage is `OPEN`                                                                                                            |
| `all_actual`         | No attributed shortage is `OPEN`, none has resolution `WRITTEN_OFF_ESTIMATED`, none has resolution `WAIVED`. `CONSUMED_FROM_STOCK` does not affect it |

A 0 VND estimated write-off still makes `all_actual` false. R1 carries `cogs_status` (`has_open_shortages`, `all_actual`) and `shortages` (`open_count`, `written_off_estimated_count`, `waived_count`); R3 rows carry the same two flags over that dish's lines. R1/R3 schemas are otherwise as in Revision 5, 2.3. The UI labels any estimate field or `including_estimates_vnd` figure as an estimate and shows an "incomplete costs" notice when `has_open_shortages` is true.

**Tests (Core):** open; positive estimated write-off; 0 VND estimated write-off; waived; consumed-from-stock only (stays true); resolution in another period; per-dish isolation in R3; a front-end test that estimate fields never render without their label.

### 3.7 Shared `usable(batch)` and the explicit COOK exception

`usable(batch)` = `remaining_qty > 0` and (`expiry_status ≠ EXPIRED` or `expired_batches_consumable = true`). It is the only definition used by automatic FEFO, menu `max_portions`, cookable-dish suggestions, cost estimates, replenishment `usable_qty` and the assistant's tools.

**The explicitly chosen COOK batch is the one exception, governed separately:**

- A non-expired explicit batch is always eligible (priority).
- An expired explicit batch is eligible only if `COOK` is in `expired_batch_actions`, regardless of `expired_batches_consumable`.
- Order for the cooked ingredient: (1) the explicit batch, up to the need; (2) any remainder through automatic FEFO over `usable(batch)` with the explicit batch **excluded by id**, so it is never counted twice.
- Other ingredients use automatic FEFO over `usable(batch)` only; an explicit expired batch never loosens the rules for other batches.
- M1 `max_portions` uses only `usable(batch)`. P1 `suggested_dishes` uses `portions_possible(dish, explicit_batch)`, shown only when `COOK` is permitted for that batch.

| Explicit batch | `COOK` in actions | `consumable` | Expected                                                                                |
| -------------- | ----------------- | ------------ | --------------------------------------------------------------------------------------- |
| Not expired    | any               | false        | Explicit first; rest from non-expired FEFO                                              |
| Not expired    | any               | true         | Explicit first; rest from FEFO including expired batches (expiry order)                 |
| Expired        | no                | false        | `409 ACTION_NOT_PERMITTED_FOR_EXPIRED_BATCH`                                            |
| Expired        | no                | true         | `409` (ordinary sales may still consume expired stock through FEFO)                     |
| Expired        | yes               | false        | Explicit first; rest from non-expired FEFO                                              |
| Expired        | yes               | true         | Explicit first; rest from FEFO including other expired batches, explicit excluded by id |

Plus: a dish that does not use the ingredient; a partial shortage; `max_portions` and replenishment ignoring expired batches when `consumable` is false and counting them when true. The `usable` consistency tests are Core; the COOK matrix is Stretch.

### 3.8 Base-unit immutability

**One predicate, `has_operational_data(ingredient)`,** identical in the API service and the database trigger. True when any exist for the ingredient: (1) a `batches` row (including empty); (2) a `stock_movements` row; (3) a `recipe_items` row (including rows of soft-deleted dishes); (4) a `document_lines` row whose document status is **not** `CANCELLED`; (5) a `stock_shortages` row; (6) an `ingredient_unit_conversions` row. It ignores `deleted_at` flags. Changing the base unit while true returns `409 BASE_UNIT_LOCKED`. The `BEFORE UPDATE` trigger fires only when the value differs, so no-op updates succeed. Cancelling the last non-cancelled document makes a change possible again.

**Concurrency lock protocol (service level):**

- The base-unit change first locks the ingredient row exclusively (`FOR UPDATE`), evaluates `has_operational_data`, then updates.
- Every operation that creates or changes operational data for an ingredient first locks that ingredient row in share mode (`FOR SHARE`) and reads `base_unit_code` under that lock before converting any quantity. Several ingredients are locked in ascending id order.
- Covered operations: manual receipt, import confirm, recipe create or update, document-line writes that set an ingredient, conversion-row writes, sale confirm and cook.
- If the data-creating transaction holds the share lock first, the base-unit change waits, sees the committed rows, and returns `409 BASE_UNIT_LOCKED`. If the change holds the lock first, the other operation waits and then uses the new base unit. A wait beyond the lock timeout returns `409 LOCK_TIMEOUT`.
- Lock order is compatible with FEFO (ingredient locks before batch locks; the change takes no batch locks) and with the idempotency claim (claim first).

**Residual risk.** The trigger backstop evaluates committed data only, so writers outside the lock protocol (direct SQL, seed or reset scripts, ad-hoc tools) can race a base-unit change. **Impact:** a row committed in the old base unit after the change would misstate its quantity. **Likelihood:** very low in a one-account demo. **Mitigation:** run seed, reset and manual SQL only when no base-unit change is in progress. A database-level alternative (carrying the base unit in every referencing key) is rejected as too complex for the MVP.

**Tests (Core):** the six conditions individually; cancelled-only draft line allowed; non-cancelled draft line rejected; soft-deleted dish recipe rejected; no-op allowed; a parity test running identical cases through the API and direct SQL; concurrency: (a) exclusive lock holder changes the unit while a second transaction creates a batch, which waits and converts with the new unit; (b) an uncommitted batch insert under the share lock makes the change wait and then fail with `BASE_UNIT_LOCKED`; (c) lock timeout returns `LOCK_TIMEOUT`.

---

## 4. API and database change summary (cumulative since Revision 5)

**API:** R1/R3 `all_actual` and `has_open_shortages` redefined (3.6); RS1 observation window based on attribution dates (3.5); S2 `estimated_cogs_vnd` derived at read time; no new endpoints.

**Database:** schema `ledger_internal` for trigger functions; cache function `SECURITY DEFINER` with fixed `search_path`; consistency triggers on `batches`, `stock_movements`, `sale_lines`, `stock_shortages`; `ledger_effective` with `security_invoker`, uniform attribution, read-only grants, revoked from API roles; base-unit trigger using the shared predicate; role-specific grants, policies and ownership handled by the reconciliation step, not by migration 0011.

## 5. Migration order

Unchanged from Revision 5 except: **0009** adds `ledger_internal`, the cache function, all triggers (including the new consistency triggers that reference `sale_lines` and `stock_shortages` from 0006 and 0008), the base-unit backstop and `ledger_effective`. **0011** is role-independent only (RLS on all tables including `units`, revokes from `anon`, `authenticated`, `PUBLIC`). Role-specific work follows 3.2.6.

## 6. Core / Stretch / Deferred scope

Feature tiers are unchanged (Revision 4, section 6).

| Tier                 | Tests                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Core DB**          | All nine movement types (signs, references, cache); reversal rules; L1–L3; consistency triggers; reconciliation queries; base-unit trigger; view read-only and cross-kitchen with two-kitchen fixtures; attribution-date rules. **_(correction C6)_ Catalog test:** every table in `public` has RLS enabled; every view is `security_invoker`; `anon`, `authenticated` and `PUBLIC` hold no privileges on tables, views or `ledger_internal`. Run it in CI after every migration. It needs no new tooling and closes review finding F7 for Core. |
| **Core integration** | Receipt; sale consumption (full, multi-batch, partial); negative-stock rollback; injected failure; concurrency; idempotency; unit conversion matrix; expiry boundaries; replenishment (3.5); COGS cache reconciliation (3.4); `all_actual` (3.6); `usable` consistency (3.7); base-unit parity and concurrency (3.8); shortages (`CONSUME_FROM_STOCK`, `WAIVE`)                                                                                                                                                                                  |
| **Stretch**          | T2 tests as `app_runtime` (3.2.7, including the privilege audit, the `ledger_owner` policy test, the `units` tests and the view-access tests) and L4; adjustment, waste, donation and sell-off workflows; COOK matrix; `WRITE_OFF_ESTIMATED`; R2/R3; notifications                                                                                                                                                                                                                                                                               |
| **Deferred**         | Usage-slip workflows; reversal and un-resolve workflows (movement-level reversal rules are Core DB tests); OCR; external LLM                                                                                                                                                                                                                                                                                                                                                                                                                     |

---

## 7. Remaining decisions

**OPEN:** D7 (policy approval items in section 2); D9, D9a, D9b (policy items); D18 (Antigravity conventions); D20 (production hosting); D24 (external LLM choice); D26 (Supabase plan limits, backups, custom-role and `session_replication_role` behavior); placeholder parameters (warning days, coverage days, window, minimum history, unusual-quantity ratio, back-date limit, upload limits, lock timeout, idempotency retention).

**PROPOSED:** D29 (idempotency), D30 (ledger triggers), **D30a** (runtime role, `SECURITY DEFINER` function, ownership, RLS policies; unverified), D32 (shortage resolution), D4a, D23 optional set, D31, D33, D34, the demo runbook.

## 8. Risks and assumptions

1. **Owner-role runtime in Core:** the API bypasses RLS until D30a is verified; isolation rests on application filters, composite FKs and commit-time triggers.
2. **Trigger limits:** the guard is not a boundary (3.1); disabled triggers or replica mode bypass everything.
3. **D30a feasibility unverified:** role creation, function ownership transfer, custom-role pooler login, `security_invoker`, execution identity of deferred triggers.
4. **RLS selector setting** protects against application bugs only, not SQL injection in the runtime session.
5. **Past-period COGS may change** after late shortage resolution; `has_open_shortages` and `all_actual` signal it.
6. **Estimates can be mislabeled** by a careless UI; the labeling test is the control.
7. **Expired-stock defaults** are placeholders; changing them alters `usable()` across features at once.
8. **Base-unit race** from writers outside the lock protocol (3.8).
9. **Scope pressure:** Core plus Core DB tests is large for 24 hours; cut Stretch first, never the ledger tests.
10. **Assumptions:** one kitchen, one account, `Asia/Ho_Chi_Minh`, VND, sales reports list dishes and portions, demo data created through real services, parameters are placeholders.

## 9. Follow-up issues (recorded, not implemented)

| ID       | Issue                                                                                                                                                                                                                                              | Status                                                                                                                                |
| -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| **FU-1** | The `app_runtime` kitchen-scoped RLS policies (3.3.2) state the kitchen condition but do not say explicitly which part is `USING` versus `WITH CHECK` for each command (`SELECT`, `INSERT`, `UPDATE`, `DELETE`). Specify it in the style of 3.2.5. | Open. The current design (kitchen condition, fail-closed when unset) is **unchanged** in this revision. **Gates D30a** (block below). |

> _(correction C1)_ D30a must not be enabled (steps 1–6 not run; the API not started with `app_runtime`) until FU-1 is closed: every `app_runtime` policy documented with its command, `USING` and `WITH CHECK`, and the T2 policy tests pass. Core mode is independent of FU-1: it uses the owner role (RLS bypassed, `FORCE` not used), and no Core feature or Core test depends on `app_runtime` policies.
>
> Step 6's policy-coverage audit asserts the documented policy set exactly (name, table, command, roles, `USING`, `WITH CHECK`).
>
> FU-1 scope also covers: (a) tables without `kitchen_id` (`kitchens`, `user_profiles`); (b) the name and per-transaction setter of the session kitchen setting, mandatory in every runtime transaction; (c) T2 tests per command: allowed for the set kitchen, denied for another kitchen, denied when unset, and `WITH CHECK` rejecting cross-kitchen inserts and updates.

## 10. Consistency audit (sections affected by Revision 6.2; unchanged in 6.3)

| Check                                                                                    | Status                      | Note                                                           |
| ---------------------------------------------------------------------------------------- | --------------------------- | -------------------------------------------------------------- |
| Function ownership stated once and consistently (3.2.2, 3.2.3, step 3, step 5(d), tests) | **PASS**                    | "Migration owner" and "admin" are one credential everywhere    |
| `ledger_owner` privileges unchanged                                                      | **PASS**                    | Still `SELECT` on `batches` and `UPDATE (remaining_qty)` only  |
| `ledger_owner` policies cover only what the function needs                               | **PASS** (design)           | `SELECT` and `UPDATE` on `batches`; matches the privilege list |
| Reconciliation step 5(d), 5(f) agree with 3.2.2 and 3.2.5                                | **PASS**                    | Step wording references them                                   |
| Deferred-trigger identity                                                                | **UNRESOLVED (unverified)** | Needs a real test; no privilege change proposed                |
| Ownership-transfer prerequisites                                                         | **UNRESOLVED (unverified)** | Needs a real test                                              |
| Core mode independent of D30a                                                            | **PASS**                    | Unchanged; stated explicitly in 3.2.6 and 9 (C1)               |

---

# Part B: Change log, Revision 6.2 → 6.3

| Correction       | Exact location in 6.3                                                         | Change                                                                                                                                                                                                                                             |
| ---------------- | ----------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **C1**           | 3.2.6, directly after the mode list; section 9, directly after the FU-1 table | Three-paragraph block added **verbatim** in both places (D30a gate; Core independence from FU-1; step 6 audit asserts the documented policy set exactly; FU-1 scope (a)–(c)). The FU-1 status cell gained the words "**Gates D30a** (block below)" |
| **C2**           | 3.2.7, test 7                                                                 | Catalog assertions (a)–(d) appended after the existing sentences, which are unchanged                                                                                                                                                              |
| **C3**           | New section **2A** (after section 2)                                          | Freeze criteria paragraph added verbatim; no renumbering of existing sections                                                                                                                                                                      |
| **C4**           | Part D, U1 row and new "Core-relevant" column                                 | U1 "needed before" changed to "Core migration 0009 (view); D30a"; U1, U10, U12, U13 marked Core-relevant                                                                                                                                           |
| **C5**           | 3.2.5, last bullet; Appendix 1, row 11                                        | "Step 5(f) of 3.2.6, for `ledger_owner`, drops and recreates exactly these two policies by name"; Appendix row 11 location changed to "Part D; section 9"                                                                                          |
| **C6**           | Section 6, Core DB row                                                        | Catalog test added as written in the review                                                                                                                                                                                                        |
| Title and status | Header, 3.2 heading                                                           | Revision 6.3; Core FROZEN; D30a PROPOSED / DISABLED. The 3.2 heading gained "DISABLED"                                                                                                                                                             |

**Not changed:** sections 1, 2, 3.1, 3.2.1–3.2.4, 3.3–3.8, 4, 5, 7, 8 and 10, the ledger formulas, schema definitions, workflows, migration order, scope tiers, privileges, policies, and every OPEN, PROPOSED and unverified status.

**Verification of this revision**

| Check                                                                     | Result                                                                                                                                                                                                                                                                                                          |
| ------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Only C1–C6 passages and the header or status wording changed              | Confirmed against the Revision 6.2 text                                                                                                                                                                                                                                                                         |
| No privilege, policy, schema, formula, workflow or migration-order change | Confirmed. C2 and C6 add tests; C1 adds a gate                                                                                                                                                                                                                                                                  |
| New text is consistent with existing text                                 | C1 matches 3.2.2's interim-state rule; C2(c) matches step 1 ("neither is a member of the other", admin member of `ledger_owner`); C2(d) matches 3.2.3 and the schema privileges in 3.2.6; C3 matches section 7 and Part D; C6 matches 0011's RLS and revoke scope; `ledger_internal` exists in Core mode (0009) |
| Cross-references valid                                                    | Section 2A, steps 5(f) and 6, 3.2.5, 3.2.6, Part D and section 9 all exist                                                                                                                                                                                                                                      |
| D30a still PROPOSED and gated by FU-1, C2 tests and U2–U9                 | Confirmed                                                                                                                                                                                                                                                                                                       |

**Observation for the team (not resolved, no document change).** The C6 test checks "every table in `public`". By Alembic's default its version table lives in `public`, and no document says where it lives or whether RLS applies to it. Before the test is written, the team decides whether to exclude that table explicitly or place it elsewhere. This does not block the freeze and changes no decision.

---

# Part C: Unchanged decisions

All decisions, scope tiers, migration order, Core mode and D30a PROPOSED status from Revision 6.2 are preserved. In particular:

- Accepted decisions in section 1; the ledger sign convention and formulas.
- The depth guard's status as a non-boundary; L1–L4.
- `SECURITY DEFINER` cache function with fixed `search_path`; `ledger_owner` privileges and the two approved policies (unchanged).
- `app_runtime` revoke-then-grant model; `batches` and `sale_lines` column privileges; `units` read-only policy.
- `ledger_effective` with `security_invoker`, attribution rules and grants.
- `settle_sale_lines` as the single cost-cache writer; status-based `all_actual`; shared `usable()` and the COOK rule; base-unit predicate and lock protocol.
- D7/D9 OPEN status with the specified-behavior split; all OPEN and PROPOSED items in section 7.

---

# Part D: Unverified assumptions

| #   | Assumption                                                                                                                                             | Needed before                    | Core-relevant |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------- | ------------- |
| U1  | PostgreSQL version supports `security_invoker` (15+) on the Supabase project and the test image                                                        | Core migration 0009 (view); D30a | **Yes**       |
| U2  | Custom roles can be created and used through the pooler                                                                                                | D30a                             |               |
| U3  | Ownership-transfer prerequisites: admin membership in `ledger_owner`; `ledger_owner` holds `CREATE` on `ledger_internal` at transfer; the revoke works | D30a                             |               |
| U4  | **Execution identity of deferred consistency triggers at commit** (session user versus role current when queued)                                       | D30a (T2 tests 1 and 2)          |               |
| U5  | The guard trigger fired from inside the cache function runs as `ledger_owner` and needs no table reads                                                 | D30a                             |               |
| U6  | `UPDATE` requires both a `SELECT` and an `UPDATE` policy; an omitted `WITH CHECK` falls back to `USING` (recalled)                                     | D30a policy tests                |               |
| U7  | Referential-integrity checks to `units` bypass RLS (recalled)                                                                                          | D30a, `units` tests              |               |
| U8  | Whether any schema privilege is needed to fire a trigger function in a schema the role cannot use                                                      | D30a                             |               |
| U9  | Whether roles can set `session_replication_role`                                                                                                       | D30a risk assessment             |               |
| U10 | `pg_trigger_depth()` values (1 for a direct statement, 2 for a trigger-initiated one)                                                                  | L1–L2 tests                      | **Yes**       |
| U11 | Supabase exposes views and tables in `public` through the Data API unless revoked or RLS blocks it (recalled)                                          | Security review                  |               |
| U12 | Token signing method (asymmetric or shared secret); supabase-js session storage default; public key variable name                                      | D4a, D34                         | **Yes**       |
| U13 | Pooler reachability from the demo network (IPv4/IPv6)                                                                                                  | D20                              | **Yes**       |
| U14 | Supabase plan limits, pausing, backups                                                                                                                 | D26                              |               |
| U15 | Antigravity folder name, frontmatter fields, extension parity, free-plan quotas                                                                        | D18                              |               |

No behavior has been verified; no implementation tests have been executed.

---

# Part E: Confirmation and final status

No implementation artifacts were created or modified. That covers repository files, code, SQL files, migrations, tests, folders, skills, hooks, agent instructions and implementation plans. Revision 6.3 exists only as text in this conversation. I did not start implementation planning.

**Final status**

- **Core architecture = FROZEN** (baseline per section 2A).
- **D30a = PROPOSED / DISABLED**, gated by FU-1, the C2 policy tests, and U2–U9 verification.

---

# Appendix 1: Prior change log, Revision 6.1 → 6.2 (history)

| #   | Location in 6.2                                | Replaces (6.1 / 6)                                                                   | Change                                                                                                                                                     |
| --- | ---------------------------------------------- | ------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | 3.2.2, ownership table                         | Rev 6 3.2 "Owner" row; Rev 6.1 §4 step 3 text "owned by the migration owner for now" | Ownership stated for all objects and both modes; trigger belongs to its table; guard and consistency triggers identified as `SECURITY INVOKER`             |
| 2   | 3.2.2, transfer procedure                      | Rev 6.1 §4 step 5(d)                                                                 | Three ordered sub-steps; prerequisites listed as to verify                                                                                                 |
| 3   | 3.2.2, interim state                           | none (new)                                                                           | API not started in D30a mode before step 6 passes                                                                                                          |
| 4   | 3.2.2, lifecycle rule                          | none (new)                                                                           | Replace-in-place only; drop-and-create prohibited                                                                                                          |
| 5   | 3.2.2, execution identity                      | none (new)                                                                           | Identity of deferred triggers declared unverified; required T2 outcome; possible `SELECT` extension recorded as needing explicit approval and not proposed |
| 6   | 3.2.6, step 1 and "Run by" column; steps 2–4   | Rev 6.1 §4 step 1 and table                                                          | "Admin (migration owner)" as one credential; membership wording                                                                                            |
| 7   | 3.2.6, steps 5(d) and 5(f)                     | Rev 6.1 §4 steps 5(d), 5(f)                                                          | Reference 3.2.2 and 3.2.5; policies named explicitly                                                                                                       |
| 8   | 3.2.5, `ledger_owner` policies                 | Rev 6 3.2 "RLS interaction"; Rev 6.1 §4 step 5(f) mention                            | Two named policies with `USING` and `WITH CHECK`; scope exclusions; rationale                                                                              |
| 9   | 3.2.7, test 7                                  | Rev 6.1 test list                                                                    | Added as approved                                                                                                                                          |
| 10  | 6, Stretch row                                 | Rev 6.1 §7                                                                           | Mentions the `ledger_owner` policy test                                                                                                                    |
| 11  | Part D; section 9 _(location corrected by C5)_ | none                                                                                 | Unverified assumptions extended; FU-1 recorded                                                                                                             |

**Merge-only (no content change):** Rev 6.1 §1 → section 2; §2 → 3.2.4; §3 → 3.3.3; §4 → 3.2.6; §5 → 3.3.4; §6 → 3.8.
