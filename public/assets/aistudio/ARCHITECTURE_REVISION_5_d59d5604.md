# Architecture Revision 5

> Converted from `revision345.docx`. Revision 4 sections not amended by Revision 5 remain carried forward as stated in the source.



Architecture Revision 5

This is architecture documentation only. I created no code, migrations, repository files, agent instructions, skills, hooks or folders, and Phase 4 has not started. Every Revision 4 section not listed below is carried over unchanged. That includes 2.A (unit conversion), 2.C (idempotency), 2.D (cook), sections 4.1 and 4.2 (composite keys, indexes), Revision 3 sections II.4 and II.8 except where amended here, and the Revision 4 scope table apart from the test tiers in section 3 below.

1. Change log from Revision 4

| ID | Change | Affects |
| --- | --- | --- |
| A | D30 no longer uses custom settings (app.*). The ledger guard uses trigger depth. TRUNCATE is blocked unconditionally. A deferred consistency trigger, cost-snapshot validation and privilege layers are added. | DB, tests, reset runbook |
| B | Reversal sign rules made explicit and enforced by trigger. | DB |
| C | One sign convention and the formulas for actual COGS, disposal cost and adjustments; COGS cannot go negative. A read-only ledger_effective view is proposed. | DB, reports |
| D | Replenishment contradictions removed. Zero-observation-day case specified. Consumption aggregation defined for signed and reversed rows. | API, tests |
| E | Base-unit immutability invariant added (service check, plus a small database backstop). | Service, DB, tests |
| F | Sell-off revenue and cost reported together, separate from ordinary sales. | API (R1) |
| G | cogs_complete removed and replaced by two explicit flags. | API (R1, R3) |
| H | Exact EXPIRES_SOON boundaries; interaction of the two expired-stock settings; one shared definition of usable stock. | DB, API, tests |
| I | Test tiers separated from feature tiers (section 3). | Scope |
| J | Audit findings and fixes (section 4), including the Batch.value_vnd name clash. | API |

2. Corrected sections

2.1 Ledger sign convention and formulas (C, B)

Convention. qty_delta and value_vnd in stock_movements are signed by direction and always carry the same sign: value_vnd ≈ qty_delta × unit_cost_snapshot. Inflows are positive, outflows negative. Reports convert to positive cost amounts with an explicit formula and never sum raw signed values into a "cost".

| Type | qty_delta | value_vnd | Report meaning |
| --- | --- | --- | --- |
| RECEIPT | + | + | Inventory in |
| SALE_CONSUMPTION | − | − | Cost = −value_vnd (sales COGS) |
| USAGE_CONSUMPTION | − | − | Cost = −value_vnd (usage; D7 decides whether it joins COGS) |
| DONATION, SELLOFF, WASTE | − | − | Cost = −value_vnd |
| ADJUSTMENT_IN | + | + | Gain = +value_vnd |
| ADJUSTMENT_OUT | − | − | Loss = −value_vnd |
| REVERSAL of X | −X.qty_delta | −X.value_vnd | Counts in X's category; nets X out |

Reversal rules (enforced by the BEFORE INSERT trigger): reversal.qty_delta = −original.qty_delta; reversal.unit_cost_snapshot = original.unit_cost_snapshot; reversal.value_vnd = −original.value_vnd. The reversal copies the original's reference columns (sale_line_id, disposal_id, document_line_id, shortage_id). The original must be in the same kitchen and batch and must not itself be a REVERSAL.

Value constraints on every movement:

CHECK (value_vnd = 0 OR sign(value_vnd) = sign(qty_delta)).

CHECK (abs(value_vnd − qty_delta × unit_cost_snapshot) < 1). This bounds forged values without hard-coding the rounding rule, so D7 stays open.

The trigger also requires unit_cost_snapshot = batches.unit_cost for the movement's batch (batch cost is immutable). A snapshot cannot be forged through direct SQL.

Effective-ledger view (technical decision, no approval needed). A read-only view ledger_effective exposes, for each movement: category (the movement's type, or the original's type for a REVERSAL), attribution_date, the reference ids, and the signed values. Reports, replenishment and the assistant's tools all read from it, so the netting rule lives in one place.

attribution_date:

sale-linked movements: sales.business_date (original and reversal alike);

disposal-linked: disposals.occurred_on;

document_line-linked usage and everything else: occurred_on of the movement, or of the original for a reversal.

Formulas

For a period P (all sums over ledger_effective rows with attribution_date ∈ P; reversals are included through their category):

| Quantity | Formula |
| --- | --- |
| Actual sales COGS | −Σ value_vnd where category = SALE_CONSUMPTION |
| Sell-off cost | −Σ value_vnd where category = SELLOFF |
| Waste cost | −Σ value_vnd where category = WASTE |
| Donation cost | −Σ value_vnd where category = DONATION |
| Adjustment net (gain positive) | +Σ value_vnd where category ∈ {ADJUSTMENT_IN, ADJUSTMENT_OUT} |
| sale_lines.cogs_vnd | −Σ value_vnd over that line's movements with category SALE_CONSUMPTION |
| Disposal cost (one disposal) | −Σ value_vnd over movements with that disposal_id |
| Stock value | Σ remaining_qty × unit_cost over batches |

Why COGS cannot go negative. Each reversal exactly negates one distinct original (unique reverses_movement_id), shares its references and therefore its attribution date, and an original and its reversal always land in the same period. Within any period the sum of those signed values is ≤ 0, so −Σ value_vnd ≥ 0. sale_lines.cogs_vnd also carries CHECK (cogs_vnd >= 0). Adjustments are excluded from this guarantee by design, because corrections there can be gains or losses.

2.2 D30 revised: trigger security (A)

Problem accepted. A session that can run SQL can also set custom GUC values, so app.ledger_apply and app.allow_demo_reset are removed. No guard depends on a session setting.

Mechanisms evaluated

| Mechanism | Verdict |
| --- | --- |
| Custom settings (app.*) | Rejected. Any client can set them. |
| Trigger-depth validation (pg_trigger_depth()) | Selected primary guard. A direct client UPDATE fires the guard at depth 1. The same update issued from inside the movement trigger fires it at depth 2. Requires no setting and works for any role. |
| Restricted functions (post_movement() as the only write path, with INSERT revoked on the ledger) | Deferred hardening. Strongest, but it moves business logic into SQL and adds work. |
| Database privileges (non-owner runtime role) | Recommended layer, stretch tier (see below). Prevents the bypasses that triggers cannot. |

Final design

| Safeguard | Implementation |
| --- | --- |
| Cache maintenance | AFTER INSERT trigger on stock_movements adds qty_delta to the matching batch (match on id, kitchen_id, ingredient_id; zero rows updated raises). |
| remaining_qty guard | BEFORE UPDATE trigger on batches raises if remaining_qty changes and pg_trigger_depth() < 2. A direct statement, a DO block or a function wrapper does not raise the depth. |
| Other batch immutables | Same trigger rejects changes to id, kitchen_id, ingredient_id, initial_qty, unit_cost. |
| Direct batch insert | BEFORE INSERT trigger requires remaining_qty = 0. |
| Ledger consistency at commit | A deferred constraint trigger on batches and on stock_movements re-checks, for every touched batch at commit: remaining_qty = Σ qty_delta, exactly one RECEIPT and its qty_delta = initial_qty. A bypass that leaves the cache inconsistent cannot commit. |
| Movement validation | BEFORE INSERT trigger: unit_cost_snapshot = batch.unit_cost; reversal rules from 2.1; type-specific sign and reference checks. |
| Non-negative stock | CHECK (remaining_qty >= 0); mapped to INSUFFICIENT_STOCK. |
| Immutability | BEFORE UPDATE OR DELETE triggers on stock_movements and audit_log always raise. |
| TRUNCATE | A BEFORE TRUNCATE trigger on every ledger and tenant table always raises. No override setting exists (see the reset runbook below). |
| Rollback guarantees, ORM refresh | Unchanged from Revision 4. |

Limitations, stated plainly

Triggers do not protect against a role that can ALTER TABLE … DISABLE TRIGGER, DROP TRIGGER, or change replication-role settings. Whether the Supabase postgres role may set session_replication_role (which disables ordinary triggers when set to replica) must be verified. Do not assume.

A direct INSERT into stock_movements that is well-formed (correct signs, references, cost snapshot) is indistinguishable from a service insert. The database guarantees ledger consistency, not business correctness such as FEFO order or the expired-stock policy. Those stay in the services.

If the MVP's runtime role is the table owner (the default postgres connection), only the trigger layer applies. That is a documented residual risk, not a claim of immunity.

Privilege layer (stretch, PROPOSED). A runtime role app_runtime, created by a bootstrap script outside Alembic (so no password lives in a migration), is not the owner and has no TRIGGER, TRUNCATE, ALTER or CREATE privilege. It has:

SELECT and INSERT on the ledger and audit tables;

no UPDATE or DELETE on them;

UPDATE (location, expiry_date, received_on) only on batches.

The grants migration is conditional on the role existing, so local databases work without it. The pooler username format for a custom role must be verified. Migrations and the reset script use a separate owner credential (ADMIN_DATABASE_URL) that the API process never reads.

Test matrix for A

Tier T1: runs as the default/owner role (Core):

| # | Test | Expected |
| --- | --- | --- |
| 1 | SET app.ledger_apply='on' then UPDATE batches SET remaining_qty=… | rejected |
| 2 | SET app.allow_demo_reset='on' then TRUNCATE stock_movements (and each other protected table, with CASCADE) | rejected |
| 3 | The same updates inside a DO block and a plain function | rejected (depth stays below 2) |
| 4 | Insert a movement, then UPDATE remaining_qty to compensate in the same transaction | rejected |
| 5 | Direct INSERT into batches with remaining_qty > 0 | rejected |
| 6 | Batch inserted without a receipt, or with a mismatched receipt, at commit | rejected |
| 7 | Movement with forged unit_cost_snapshot or value_vnd outside tolerance | rejected |
| 8 | Legitimate movement insert updates the cache | passes |
| 9 | Direct UPDATE/DELETE of movements and audit rows | rejected |

Tier T2: runs as app_runtime (Stretch, required if the role is adopted): UPDATE remaining_qty, UPDATE/DELETE on ledger, TRUNCATE, ALTER TABLE, DISABLE TRIGGER, CREATE TRIGGER, and SET session_replication_role all return permission errors. The session_replication_role result is recorded as a verification finding.

Trigger versus application-level updates. The comparison table from Revision 4 stands. This revision adds one qualification to the recommendation: the trigger approach is only as strong as the roles around it (limitations 1 and 3). D30 stays PROPOSED, with the privilege layer as a separate PROPOSED item (D30a).

Reset runbook (replaces the earlier ALLOW_DEMO_RESET database setting). reset_demo runs under ADMIN_DATABASE_URL, outside the API process:

Refuse unless the script process has ALLOW_DEMO_RESET=true, ENVIRONMENT is not production, and exactly one kitchen exists. These are script-level safeguards, not database-level ones.

One transaction: ALTER TABLE … DISABLE TRIGGER for the explicit list of no_truncate triggers, one TRUNCATE over the explicit list of tenant tables (every table with kitchen_id except kitchens and kitchen_settings; user_profiles and units are untouched), re-enable the triggers.

Verify in pg_trigger that every trigger is enabled; abort the run if not.

Re-run seed_demo --reseed-data.

Alternative considered: rebuild the schema through downgrade and upgrade. It is cleaner but brittle for a hackathon, so it is not chosen. Residual risk: anyone holding the admin URL can truncate. That is accepted for a demo and keeps the admin URL out of the runtime environment.

2.3 Sell-off accounting and R1 / R3 (F, G)

Rules. Ordinary sales and sell-offs are separate sections of the report. Sell-off revenue comes from disposals.revenue_vnd. Its cost is −Σ value_vnd of SELLOFF movements (actual, real batches, net of reversals). Revenue never appears in gross profit without its cost.

cogs_complete is removed. Two precise flags replace it:

| Flag | Definition |
| --- | --- |
| has_open_shortages | At least one OPEN shortage on a sale line attributed to the period. When true, costs are understated. |
| all_actual | has_open_shortages = false and cogs.estimated_vnd = 0 and waived_count = 0. True only when every cost is an established actual cost. |

They are not equivalent: a period with only a WRITE_OFF_ESTIMATED shortage has has_open_shortages = false but all_actual = false.

Revised R1 response (replaces the Revision 4 version):

{ period: { from, to },

sales: {

revenue_vnd: Money,                                   // ACTUAL

cogs: { actual_vnd: Money, estimated_vnd: Money },    // actual = SALE_CONSUMPTION; estimated = WRITE_OFF_ESTIMATED shortages (ESTIMATE)

gross_profit: { excluding_estimates_vnd: Money, including_estimates_vnd: Money },

portions_sold: number },

selloff: {

revenue_vnd: Money, cost_vnd: Money /* ACTUAL */, margin_vnd: Money },   // margin may be negative

totals: {

revenue_vnd: Money,                                   // sales + selloff

gross_profit: { excluding_estimates_vnd: Money, including_estimates_vnd: Money } },

waste_cost_vnd: Money, donation_cost_vnd: Money,        // ACTUAL, positive costs

adjustment_net_vnd: Money,                              // signed, gain positive

shortages: { open_count, written_off_estimated_count, waived_count },

unrecorded_cost: { indicative_estimate_vnd: Money | null /* ESTIMATE, memo only */, ingredients_without_cost: number },

cogs_status: { has_open_shortages: boolean, all_actual: boolean },

result_after_ingredient_loss: {

excluding_estimates_vnd: Money, including_estimates_vnd: Money,

policy_status: "PLACEHOLDER_PENDING_D7" },

comparison: { previous_period: {...} | null, note: string } }

Formulas (placeholders under D7):

sales.gross_profit.excluding = sales.revenue − cogs.actual; including also subtracts cogs.estimated.

selloff.margin = selloff.revenue − selloff.cost.

totals.gross_profit = sales.gross_profit + selloff.margin (both variants).

result = totals.gross_profit − waste_cost − donation_cost + adjustment_net.

R3 rows: { dish, portions, revenue_vnd, cogs_actual_vnd, cogs_estimated_vnd, gross_profit: {excluding_estimates_vnd, including_estimates_vnd}, has_open_shortages, all_actual }.

UI contract: only *actual* fields may be labeled "actual". Any figure derived from including_estimates_vnd or an ESTIMATE field must display its label. When has_open_shortages is true the view must say costs are incomplete. A frontend test asserts that estimate fields never render without their label.

2.4 Replenishment revised (D, D25 formula unchanged)

Definitions (all decimal arithmetic):

usable(batch) is the single shared definition (see 2.6): remaining > 0 and not EXPIRED, unless expired_batches_consumable is true. Replenishment, FEFO, menu max_portions, estimates and the assistant's cookable-dishes tool all use it.

consumption(ingredient, window) = −Σ qty_delta over ledger_effective rows with category SALE_CONSUMPTION or USAGE_CONSUMPTION and attribution_date inside the window. Consumption quantities are negative, so the minus sign makes the total positive; a reversal's positive quantity subtracts from its original's period.

window_end = yesterday; history_start = earliest occurred_on of any movement of the ingredient.

window_start = max(window_end − window_days + 1, history_start).

observed_days = max(0, window_end − window_start + 1). It is 0 when history_start > window_end (for example everything happened today), and the ingredient has no history at all if it has no movement.

No average is computed unless observed_days ≥ min_history_days (the setting is ≥ 1). The denominator is always observed_days, never the configured window.

Classification (each ingredient is evaluated by both rules independently):

| Condition | items | insufficient_data | no_recent_consumption |
| --- | --- | --- | --- |
| Coverage rule not evaluable (observed_days < min_history_days) | Only if usable_qty < min_stock_qty and min_stock_qty > 0: item with rule: MIN_STOCK_ONLY | Yes, with reason HISTORY_TOO_SHORT (1 ≤ observed < min), NO_COMPLETE_DAYS (observed = 0 with movements), or NO_HISTORY | No |
| Evaluable, average > 0, days_of_cover < target_coverage_days | Item, rule: COVERAGE (or BOTH if also under minimum) | No | No |
| Evaluable, average = 0 | Item only if under minimum (MIN_STOCK_ONLY) | No | Yes if no rule triggered |
| Evaluable, sufficient cover, above minimum | No | No | No |

An ingredient can therefore appear in both items and insufficient_data: the first is the suggestion, the second is the caveat that its coverage rule was skipped. no_recent_consumption never overlaps the other two. This replaces the contradictory Revision 4 wording.

Quantities:

Coverage: raw = max(0, target_coverage_days × avg_daily − usable_qty); days_of_cover = usable_qty ÷ avg_daily (null when avg_daily = 0).

Minimum: raw = max(0, min_stock_qty − usable_qty).

raw_order_qty = the larger of the applicable raws. suggested_order_qty = ceil(raw ÷ step) × step, where step is ingredients.order_step or 0.001 when null.

Revised RS1 item and lists:

items: [{ ingredient, usable_qty, unit,

observation: { from: Date, to: Date, observed_days: number } | null,

consumption_total: Decimal | null, avg_daily_consumption: Decimal | null,

days_of_cover: Decimal | null,

rule: "COVERAGE" | "MIN_STOCK_ONLY" | "BOTH",

raw_order_qty: Decimal, order_step: Decimal | null, suggested_order_qty: Decimal,

basis: "ESTIMATE", assumptions: string[] }],

insufficient_data: [{ ingredient, reason: "HISTORY_TOO_SHORT" | "NO_COMPLETE_DAYS" | "NO_HISTORY",

observed_days: number, coverage_rule_skipped: true }],

no_recent_consumption: [{ ingredient, usable_qty, unit }]

Limitations stay as listed in Revision 4 (stock-outs, unmet demand, weekday patterns). The notification LOW_STOCK uses the same classification.

2.5 Base-unit immutability (E)

Invariant (service level, MVP). A PATCH /ingredients/{id} that changes base_unit returns 409 BASE_UNIT_LOCKED if the ingredient has any related operational data:

any batch (including empty ones) or any stock movement;

any recipe_items row (including rows of soft-deleted dishes);

any document_lines row on a non-cancelled document;

any stock_shortages row;

any ingredient_unit_conversions row.

The repository exposes one has_operational_data(ingredient_id) check. Re-basing historical data is not implemented. The workaround is to create a new ingredient and soft-delete the old one.

Database backstop. A BEFORE UPDATE OF base_unit_code trigger on ingredients raises if any of those tables references the ingredient, so direct SQL cannot change it either. (This replaces reliance on the conversion-table foreign key alone, which covered only conversions.)

Tests (Core): change succeeds for an ingredient with no data; rejected after a receipt (even when fully consumed), with only a recipe, with a draft document line, with a confirmed line, with a shortage, with a conversion row; no-op update to the same unit succeeds; soft-deleted ingredient with history stays locked; direct SQL update with data present is rejected by the trigger.

2.6 Expiry boundaries and policy interaction (H)

Let d = expiry_date − today in whole days (kitchen-local dates) and w = the ingredient's expiry_warning_days or the kitchen default (0 to 30).

| d | Status | Example with w = 3 |
| --- | --- | --- |
| < 0 | EXPIRED | yesterday (d = −1) |
| 0 ≤ d ≤ w | EXPIRES_SOON | today (0), tomorrow (1), exactly w days away (3) |
| > w | OK | d = 4 |
| null | NO_EXPIRY |  |

The upper bound is inclusive. With w = 0 only today is EXPIRES_SOON. days_to_expiry = d. expiry_date < today is EXPIRED, unchanged.

How the two expired-stock settings interact (both are placeholders under D9 and remain independent):

expired_batches_consumable controls only automatic FEFO eligibility for sales consumption and shortage CONSUME_FROM_STOCK, including the "other ingredients" part of a cook. It is part of the shared usable(batch) definition.

expired_batch_actions controls only explicit user actions on a specific expired batch: WASTE, DONATION, SELLOFF, COOK.

COOK from an expired batch requires COOK in expired_batch_actions, regardless of the other setting. If COOK is permitted but expired_batches_consumable is false, the chosen expired batch is consumed first and the rest of that ingredient comes from non-expired batches through FEFO.

If expired_batches_consumable is true, FEFO treats expired batches in expiry order (they come first), independent of the action list. The settings endpoint returns a policy_warnings entry when consumable is true but COOK is not listed, because that combination is unusual.

'WASTE' must always be in expired_batch_actions (new CHECK). This is record-keeping, not safety policy: otherwise expired stock could only leave the ledger through an adjustment.

3. MVP scope and test tiers (I)

Integrity safeguards are not removed to save time. They live in the schema, which is built in one pass. The test tiers decide what must be proven.

| Tier | What it covers | Contents |
| --- | --- | --- |
| Core DB invariants (schema must exist) | Built in migrations 0001–0011 | All CHECKs and composite FKs; movement apply trigger; depth guard; deferred consistency trigger; cost-snapshot and reversal validation; immutability and TRUNCATE triggers; base-unit backstop; partial uniques; RLS; ledger_effective view |
| Core DB tests (no feature needed) | Executed with SQL fixtures | One parametrized test over all nine movement types: sign, reference checks and cache application. Reversal rules (valid, double reversal, reversal of a reversal, mismatched fields, consumed receipt). T1 bypass tests. Reconciliation queries. These cost little and need no deferred business workflow. |
| Core integration tests (Core features) | API and services | RECEIPT via import and manual batch; SALE_CONSUMPTION (full, multi-batch, partial with shortage); negative-stock rollback; injected failure leaves no rows; two concurrent transactions on one batch; idempotency (replay, reuse, in-progress, rollback leaves no CLAIMED row); unit conversion matrix; expiry boundaries; replenishment table in 2.4; COGS sign and netting; cross-kitchen 404; shortage CONSUME_FROM_STOCK and WAIVE; base-unit immutability |
| Stretch tests | Stretch features | ADJUSTMENT_IN/OUT workflows; WASTE, DONATION, SELLOFF workflows and sell-off reporting; COOK; WRITE_OFF_ESTIMATED; R2/R3; T2 privilege tests if app_runtime is adopted; notifications |
| Deferred tests | Deferred features | USAGE_CONSUMPTION through usage slips; reversal and shortage-un-resolve workflows; OCR; external LLM provider |

The Revision 4 feature table (Core, Stretch, Deferred) is unchanged. The only change is that movement types without an MVP workflow are covered by DB-level fixtures, not by feature implementation.

4. Consistency audit of Revision 4

| # | Finding | Resolution | Agreement |
| --- | --- | --- | --- |
| 1 | D30 depended on custom settings | Removed (2.2) | Sections 2.2, tests T1, reset runbook |
| 2 | Reversal value_vnd ambiguous | 2.1 | Constraints, trigger, formulas |
| 3 | Cost formulas ignored sign; COGS could be negative | 2.1 formulas, CHECK cogs_vnd >= 0 | Report formulas, R1 |
| 4 | Replenishment contradiction; zero observed days; signed aggregation | 2.4 | Table, RS1 schema, tests |
| 5 | Base-unit change not blocked for operational data | 2.5 | Service, trigger, tests |
| 6 | Sell-off revenue without its cost in R1 | 2.3 | R1 schema, formulas |
| 7 | cogs_complete ambiguous | Replaced by has_open_shortages and all_actual | R1, R3, UI contract |
| 8 | EXPIRES_SOON boundaries unspecified; settings interaction unclear; usable stock differed between replenishment and FEFO | 2.6 and shared usable() | FEFO, estimates, RS1, assistant tools |
| 9 | Batch.value_vnd clashed with the ledger's signed value_vnd | Renamed Batch.stock_value_vnd (positive, remaining × unit_cost) | Batch schema; I6 already used stock_value_vnd |
| 10 | Replenishment used a different date basis than COGS | One attribution_date via ledger_effective | 2.1, 2.4 |
| 11 | I7 returns value_vnd | Stays signed; documented as signed ledger value, with a category field added | I7 schema |
| 12 | The app.allow_demo_reset guard in migration 0009 and the I.3 runbook | Replaced (2.2) | Runbook, migration 0009 |
| 13 | Deprecated names | cogs_complete, app.ledger_apply, app.allow_demo_reset, P2 COOK, /me/provision, kitchen_members removed | All references searched in this revision |

Checked and unchanged: composite foreign key matrix (4.1) and indexes (4.2); idempotency protocol and retry table (2.C); cook endpoint (2.D); core/stretch/deferred feature table; migration ordering apart from the additions below.

Not claimed as resolved: D7 and D9 stay open. The ledger sign convention is consistent across 2.1, 2.2, 2.3 and 2.4, but every example in Part II of Revision 3 that shows a ledger value_vnd is a signed value unless a field name says cost.

4.1 Migration order impact

The order from Revision 4 stands. Content changes only:

0001: kitchen_settings gains the check that 'WASTE' is in expired_batch_actions.

0002: ingredients base-unit backstop trigger created after the referencing tables exist, so it is added in 0009.

0006: sale_lines gains CHECK (cogs_vnd >= 0).

0009: stock_movements, all triggers from 2.2 (no GUC), the value CHECKs from 2.1, the base-unit backstop, BEFORE TRUNCATE triggers on tenant tables, and ledger_effective.

0011: unchanged, plus the conditional app_runtime grants.

5. API and database change summary (Revision 4 → 5)

API

R1 restructured (sales, selloff, totals, cogs_status); R3 rows updated; cogs_complete removed everywhere.

RS1: observation and avg_daily_consumption nullable, rule includes MIN_STOCK_ONLY for insufficient history, new NO_COMPLETE_DAYS reason, coverage_rule_skipped field.

Batch.value_vnd renamed stock_value_vnd; I7 items gain category.

New error 409 BASE_UNIT_LOCKED.

T1/T2 reject an expired_batch_actions list without WASTE, and return policy_warnings.

Database

Removed: all use of app.* settings; the conditional TRUNCATE guard.

Added: unconditional BEFORE TRUNCATE triggers; depth-based batches guard; deferred consistency trigger on batches and stock_movements; direct-insert guard on batches; unit_cost_snapshot equals batch cost; value sign and tolerance CHECKs; reversal trigger now includes value negation and reference copying; base-unit backstop trigger; CHECK (cogs_vnd >= 0); CHECK that expired_batch_actions includes WASTE; ledger_effective view.

Operational: ADMIN_DATABASE_URL (owner, never in the API environment) separate from DATABASE_URL.

6. Decisions

6.1 Remaining OPEN

D7 (accounting policy: attribution rule, estimate treatment, headline profit figure, rounding, usage in COGS, donation treatment, report naming); D9, D9a, D9b (food-safety assumptions, expiry boundary convention, whether every ingredient needs an expiry date, back-dated reports, shelf-life catalog, and the expired-stock defaults); D18 (Antigravity conventions); D20 (production hosting); D24 (external LLM choice); D26 (Supabase plan limits, backups, and whether postgres or a custom role may change replication-role settings); placeholder parameter values as listed in Revision 4.

6.2 Remaining PROPOSED

D29 (idempotency), D30 (ledger triggers, revised), D30a (app_runtime role, new), D32 (shortage resolution), D4a, D23 optional set, D31, D33, D34 (with the Revision 4 implementation conditions), and the demo runbook as revised in 2.2.

Technical decisions made here without further approval: the ledger_effective view, the depth guard, the consistency trigger, the base-unit backstop trigger, value tolerance checks, the replenishment classification table, and the exact expiry boundaries.

7. Risks and assumptions still unresolved

Owner-role runtime. Until D30a is adopted and verified on Supabase, the API runs with table-owner rights and trigger safeguards only (2.2, limitations 1 and 3).

pg_trigger_depth() behavior is a well-known pattern, but the Core DB tests (section 3) are what prove it for the chosen Postgres version. Run them on both local Postgres and the Supabase dev project.

Past-period COGS can still change when shortages are resolved late, through attribution to the sale date. has_open_shortages signals it; it does not prevent it.

Estimates may be mislabeled by a careless UI. The labeling contract and its frontend test are the control.

Custom-role pooler support and username format unverified (D26).

Scope pressure. The Core tier plus the Core DB tests is still a lot for 24 hours. If time runs short, cut Stretch features first, and never the T1 tests or the ledger constraints.

Assumptions unchanged: one kitchen, one account, VND only, Asia/Ho_Chi_Minh, sales reports list dishes and portions, demo data created through real services, parameters are placeholders.

I have not started Phase 4 and will wait for your review of Revision 5.
