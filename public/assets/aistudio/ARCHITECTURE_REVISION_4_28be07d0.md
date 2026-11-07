# Architecture Revision 4

> Converted from `revision345.docx`. Revision 3 sections not amended by Revision 4 remain carried forward as stated in the source.



Revision 4: focused corrections to Phase 3

This revision is architecture only. There is no application code, no migrations, no repository files, no Phase 4, and none of the 16 agent files. Revision 3 sections not mentioned here stay as written.

1. Change log from Revision 3

| # | Change | Affects |
| --- | --- | --- |
| A | COUNT units no longer auto-convert. MASS and VOLUME convert within their own dimension only. | DB, API, tests |
| B | Mechanical expiry classification is separated from expired-stock policy. The policy is a small, isolated, configurable placeholder pending D9. | DB, API |
| C | Idempotency protocol rewritten: the claim and the business effects commit in one transaction, so no abandoned in-progress state exists. | DB, API |
| D | COOK moved out of disposals to POST /batches/{id}/cook, owned by sales. | API, DB, flows |
| E | Replenishment edge cases specified. ingredients.order_step added. | DB, API |
| F | Shortage resolution accounting specified for all three actions. sale_lines and stock_shortages revised. | DB, API |
| G | D30 safeguards specified (receipt, consumption, adjustment, reversal, direct-update guards, test matrix). D30 stays PROPOSED. | DB |
| H | Consistency review: 21 findings fixed (section 4). | DB, API |
| I | MVP / deferred classification added (section 6). | Scope |

2. Corrections

2.A Unit conversion rules

Constraint on units:

CHECK ( (dimension IN ('MASS','VOLUME') AND factor_to_dimension_base > 0)

OR (dimension = 'COUNT'            AND factor_to_dimension_base IS NULL) )

Seeded values: g 1, kg 1000, ml 1, l 1000; the count units (quả, hộp, bó, củ, bìa, gói, chai) have NULL.

Conversion algorithm convert(ingredient, qty, from_unit):

from_unit equals the ingredient's base unit → qty.

Both units are MASS, or both are VOLUME → qty × factor(from) ÷ factor(base).

Otherwise look up ingredient_unit_conversions for (ingredient, from_unit) → qty × factor_to_base.

Otherwise 422 UNIT_NOT_CONVERTIBLE with details: {from, to}.

Consequences: hộp → quả, bó → chai and every other COUNT-to-different-COUNT conversion need an ingredient-specific row. MASS ↔ VOLUME (density) also needs one. COUNT never converts to MASS or VOLUME automatically.

Database-level protection for ingredient_unit_conversions:

Add column base_unit_code. Composite FK (kitchen_id, ingredient_id, base_unit_code) → ingredients (requires UNIQUE (kitchen_id, id, base_unit_code) on ingredients). This also stops the base unit changing while conversions exist.

CHECK (unit_code <> base_unit_code).

Service validation: reject a conversion row whose unit has the same MASS/VOLUME dimension as the base (it would contradict step 2).

Tests: a conversion matrix covering identical unit, kg↔g, l↔ml, kg→ml (rejected without density), hộp→quả (rejected without row, accepted with row), bó→chai (rejected), and unit-change after data exists (rejected).

2.B Expired-stock policy

Two separate concepts:

| Concept | Nature | Rule |
| --- | --- | --- |
| expiry_status | Mechanical date comparison | EXPIRED if expiry_date < today (kitchen timezone); EXPIRES_SOON if within expiry_warning_days; OK; NO_EXPIRY if null. That an item expiring today is not yet EXPIRED is a classification convention recorded under D9a. |
| Expired-stock policy | Policy, pending D9 | What the system permits for an EXPIRED batch. Not a food-safety statement. |

Isolated policy (PROPOSED): one ExpiredStockPolicy component, backed by two kitchen settings. Nothing else in the code decides what may be done with expired stock.

| Setting | Type | Placeholder default |
| --- | --- | --- |
| expired_batches_consumable | boolean | false (FEFO skips expired batches for sales and usage) |
| expired_batch_actions | text[] ⊆ {WASTE,DONATION,SELLOFF,COOK} | {WASTE} |

The defaults are the most restrictive setting for usage actions, so the system never lets expired stock be used or passed on without an explicit team decision. They are marked PLACEHOLDER_PENDING_D9 wherever they surface. The team may change them without code changes once D9 is decided.

Always allowed, regardless of the policy, because they correct records and carry no usage decision: stocktake adjustments, correcting an expiry date (audited), and viewing.

API effects:

P1.available_actions comes from the policy, and the response carries expired_policy_status: "PLACEHOLDER_PENDING_D9".

A disallowed action returns 409 ACTION_NOT_PERMITTED_FOR_EXPIRED_BATCH.

kitchen_settings and T1/T2 gain the two fields.

2.C Idempotency protocol (D29, revised, PROPOSED)

Design principle: claim the key and execute the business operation in one database transaction. A claim that has not committed is, by construction, invisible and self-cleaning, so no persisted IN_PROGRESS state exists to go stale.

Table idempotency_keys: kitchen_id, endpoint (method + route template), key, request_hash (sha256 of method, path parameters and canonicalized JSON body), actor_id, status (CLAIMED or COMPLETED), response_status, response_body jsonb, created_at, completed_at. UNIQUE (kitchen_id, endpoint, key). A key is scoped per endpoint, so the same key on a different endpoint is a different claim.

Protocol (each idempotent request):

Validate headers and body; compute request_hash.

BEGIN (READ COMMITTED); SET LOCAL lock_timeout = '2s' (placeholder).

INSERT … ON CONFLICT (kitchen_id, endpoint, key) DO NOTHING RETURNING id.

A row returned means this request owns the claim. Continue.

No row returned means another transaction holds or committed the key. Postgres makes the second inserter wait for the first to commit or roll back, so after the insert returns, the existing row is visible and committed:

same request_hash and COMPLETED → roll back and replay the stored status and body (add header Idempotent-Replay: true);

different request_hash → roll back, 422 IDEMPOTENCY_KEY_REUSED.

If the wait exceeds lock_timeout → roll back, 409 REQUEST_IN_PROGRESS with Retry-After.

Lock the primary resource (for example SELECT … FROM documents … FOR UPDATE) and check its state. A different key against an already confirmed document gets 409 DOCUMENT_ALREADY_CONFIRMED, so confirm is protected even without a matching key.

Run the business operation (lock order unchanged: ascending ingredient id).

UPDATE idempotency_keys SET status='COMPLETED', response_status=…, response_body=….

COMMIT. Business effects and the stored response become visible atomically.

Failure handling:

| Situation | Outcome |
| --- | --- |
| Process or connection dies before commit | Everything rolls back, including the claim. Nothing to recover. A retry runs fresh. |
| Commit succeeds but the response is lost | Retry with the same key replays the stored response. |
| Commit outcome unknown | Retry with the same key. Either replay or fresh execution is correct. |
| Business validation error (4xx) | The transaction rolls back, nothing is stored, and the user can fix the request and reuse the key. |
| Defensive sweeper | A cleanup command deletes CLAIMED rows older than a few minutes (should never exist, and an integration test asserts none remain) and COMPLETED rows past the retention window (placeholder 24 h). |

Retry safety:

| Failure | Retry with the same key and body? |
| --- | --- |
| Network error, timeout, 5xx, 503 | Yes, safe |
| 409 REQUEST_IN_PROGRESS | Yes, after Retry-After |
| 409 LOCK_TIMEOUT (row-lock wait) | Yes, safe |
| 409 INSUFFICIENT_STOCK | Only after the state changes |
| 422 VALIDATION_ERROR and similar | After fixing the request; the key is still free |
| 422 IDEMPOTENCY_KEY_REUSED | No: use a new key for a different request |

Applies to: document confirm, POST /batches, adjustments, disposals, cook, shortage resolve.

Frontend rule: generate one key per user intent (when the form is opened or submitted) and reuse it for retries of that intent, never per click.

Residual risk: two deliberate submissions with different keys execute twice (for example a double-clicked disposal). Adjustments are naturally safe because they set an absolute target (a repeat becomes 422 NO_CHANGE). Document confirm is guarded by document state.

Alternative rejected: claim in a short transaction with a lease, run the operation, complete in another transaction. It needs lease expiry, a recovery worker and handles a duplicate-execution window. It is only justified if an idempotent operation gains external side effects (storage, email). None of the MVP operations has any.

2.D COOK separated from disposals

POST /batches/{id}/cook is owned by sales, which calls InventoryService. dispositions is left with DONATION, SELLOFF and WASTE only.

// request   (Idempotency-Key required)

{ dish_id: UUID, portions: number /* int ≥ 1 */, business_date?: Date, note?: string }

// 201 response

{ sale_id: UUID,

sale_line: { id, dish_name, quantity, unit_price_vnd, revenue_vnd, cogs_vnd,

estimated_cogs_vnd, consumption_status: "FULL"|"PARTIAL"|"RESOLVED",

origin: "REPURPOSE", source_batch_id: UUID },

consumption: { fully_covered_lines: number, partial_lines: number },

shortages: [ { id, ingredient, short_qty, unit, status } ] }

Rules:

The dish's recipe must use the batch's ingredient, else 422 DISH_DOES_NOT_USE_BATCH_INGREDIENT.

For that ingredient the chosen batch is consumed first, then normal FEFO. Other ingredients use normal FEFO. Anything uncovered becomes a shortage.

Allowed on an expired batch only if the policy lists COOK (2.B).

Movements are ordinary SALE_CONSUMPTION rows referencing the sale line.

Schema: sale_lines.source_batch_id (composite FK to batches), with CHECK (origin = 'REPURPOSE' AND source_batch_id IS NOT NULL OR origin = 'NORMAL' AND source_batch_id IS NULL).

P1.available_actions still offers COOK, pointing to this endpoint.

Tests: creates a sale with origin REPURPOSE; batch priority respected; shortage on insufficient stock; idempotent replay; expired-policy enforcement; dish that does not use the ingredient rejected.

Updated flow:

flowchart TD

A[GET /expiring-batches] --> B{expiry_status and policy}

B --> D[POST /batches/id/disposals: DONATION, SELLOFF, WASTE]

B --> F[POST /batches/id/cook: sale origin REPURPOSE]

D --> L[(ledger + audit)]

F --> S[sales: sale_line + SALE_CONSUMPTION] --> L

2.E Replenishment edge cases (D25 formula unchanged)

All steps use decimal arithmetic.

| Case | Behavior |
| --- | --- |
| Observation period | Complete days only. window_end = yesterday. history_start = the earliest occurred_on of any ledger movement for that ingredient. window_start = max(window_end − window_days + 1, history_start). observed_days = window_end − window_start + 1. |
| Denominator | observed_days, never the configured window when history is shorter. |
| Consumption | Net of reversals: Σ(SALE_CONSUMPTION + USAGE_CONSUMPTION) quantities with occurred_on in the window, minus reversals of those rows. Waste, donation, sell-off and adjustments are not demand. |
| History below min_history_days (observed_days < min_history_days, or no movements) | Listed in insufficient_data (HISTORY_TOO_SHORT or NO_HISTORY). No suggestion, even if stock is below the minimum. The ingredient's min_stock_qty rule still applies on its own and is flagged rule: MIN_STOCK_ONLY. |
| Zero average consumption | avg_daily = 0, days_of_cover = null (no division). The coverage term is 0. The ingredient is suggested only if usable_qty < min_stock_qty. Otherwise it appears in no_recent_consumption (informational). |
| Usable stock | Remaining quantity in batches that are not EXPIRED. |
| Rounding | suggested_order_qty = ceil(raw ÷ step) × step. |
| Order step | New optional ingredients.order_step numeric(14,3) CHECK > 0, in base units. If null, round up to 0.001 base units (the storage precision). Not required, but the UI should prompt for it (for example a pack size). |

Known limitations, shown as assumptions: stock-outs depress observed consumption; unmet demand recorded as shortages is not counted as demand; the average ignores weekday patterns.

New response shape for GET /replenishment-suggestions (renamed RS1):

{ as_of: Date, parameters: { target_coverage_days, window_days, min_history_days },

items: [{ ingredient, usable_qty, unit, observation: { from: Date, to: Date, observed_days: number },

consumption_total: Decimal, avg_daily_consumption: Decimal, days_of_cover: Decimal | null,

rule: "COVERAGE" | "MIN_STOCK_ONLY" | "BOTH",

raw_order_qty: Decimal, order_step: Decimal | null, suggested_order_qty: Decimal,

basis: "ESTIMATE", assumptions: string[] }],

insufficient_data: [{ ingredient, reason: "HISTORY_TOO_SHORT" | "NO_HISTORY", observed_days: number }],

no_recent_consumption: [{ ingredient, usable_qty, unit }] }

2.F Shortage resolution and COGS (D32, revised, PROPOSED; D7 stays OPEN)

Baseline meaning of figures

sale_lines.cogs_vnd is always actual: the sum of the value_vnd of that line's SALE_CONSUMPTION movements (net of reversals).

Estimates never go into cogs_vnd. They live on the shortage row and are reported separately.

consumption_status: FULL (never short), PARTIAL (at least one OPEN shortage), RESOLVED (had shortages, none OPEN). The transition PARTIAL → RESOLVED happens in the same transaction as the last resolution.

Revenue never changes through resolution.

| Action | Movement created | References | cogs_vnd | Report treatment |
| --- | --- | --- | --- | --- |
| CONSUME_FROM_STOCK | FEFO SALE_CONSUMPTION (or USAGE_CONSUMPTION for usage-slip shortages) for the full short_qty, possibly several batches. If usable stock is below short_qty: 409 INSUFFICIENT_STOCK, nothing changes. | sale_line_id (or document_line_id) and shortage_id (new column), batch ids, cost snapshots | Increases by the new movements' values | ACTUAL cost. occurred_on = resolution date. Reports attribute sale-linked COGS to the sale's business_date (below). Shortage → RESOLVED / CONSUMED_FROM_STOCK. |
| WRITE_OFF_ESTIMATED | None. There is no stock to move, and a movement would require negative stock. | Shortage row stores estimated_unit_cost, estimated_cost_vnd, estimate_batch_id (the batch whose cost was used) | Unchanged | ESTIMATE. Included in cogs.estimated_vnd. Cost basis (PLACEHOLDER, D7) = unit_cost of the ingredient's most recent receipt by received_on. Shortage → RESOLVED / WRITTEN_OFF_ESTIMATED. |
| WAIVE | None | Required resolution_note. If a cost basis exists, the same estimate columns are filled as an indicative value. | Unchanged | Contributes to neither COGS nor profit. Reported only as unrecorded_cost (memo, labeled ESTIMATE). Shortage → RESOLVED / WAIVED. |

No cost history (the ingredient has never been received):

WRITE_OFF_ESTIMATED returns 422 NO_COST_HISTORY.

WAIVE is allowed, with the estimate columns null; reports count it in unrecorded_cost.ingredients_without_cost.

CONSUME_FROM_STOCK is unaffected.

Report attribution (PLACEHOLDER, D7):

Sale-linked COGS (including late resolution consumption) is attributed to the sale's business_date, so revenue and cost meet in the same period.

A consequence is that a past period's COGS can change when a shortage is resolved later. cogs_complete tells readers whether it is final.

Disposal costs use the disposal's occurred_on; adjustments use their occurred_on.

Replenishment (2.E) uses the movement's own occurred_on (the physical date).

Schema changes

stock_shortages: add document_line_id (composite FK, nullable). CHECK exactly one of sale_line_id, document_line_id. Partial uniques (sale_line_id, ingredient_id) and (document_line_id). Add estimate_batch_id (composite FK, nullable). Checks:

CONSUMED_FROM_STOCK ⇒ estimate columns null;

WRITTEN_OFF_ESTIMATED ⇒ estimated_cost_vnd not null;

WAIVED ⇒ resolution_note not null.

stock_movements: add shortage_id (composite FK, nullable).

sale_lines.consumption_status: FULL | PARTIAL | RESOLVED.

Revised report fields:

// R1 (replaces the earlier cogs/profit fields)

{ revenue: { sales_vnd, selloff_vnd, total_vnd },                        // ACTUAL

cogs: { actual_vnd, estimated_vnd /* ESTIMATE: written-off shortages */ },

gross_profit: { excluding_estimates_vnd, including_estimates_vnd },

waste_cost_vnd, donation_cost_vnd, adjustment_net_vnd,                 // ACTUAL

shortages: { open_count, written_off_estimated_count, waived_count },

unrecorded_cost: { indicative_estimate_vnd: Money | null /* ESTIMATE */, ingredients_without_cost: number },

cogs_complete: boolean,                                                // false while any OPEN shortage in period

result_after_ingredient_loss: { excluding_estimates_vnd, including_estimates_vnd,

policy_status: "PLACEHOLDER_PENDING_D7" },

period, portions_sold, comparison }

// R3 rows gain: cogs_complete: boolean, estimated_cogs_vnd

Which headline profit figure to show is a D7 decision. The API returns both, and neither is called "profit".

3. D30: ledger-trigger safeguards (stays PROPOSED)

Safeguards specified:

| Concern | Mechanism |
| --- | --- |
| Apply movement to cache | AFTER INSERT row trigger adds qty_delta to batches.remaining_qty, matching id, kitchen_id and ingredient_id. Zero rows updated raises an error. |
| Non-negative stock | CHECK (remaining_qty >= 0). The violation aborts the statement and the whole transaction; the service maps it to INSUFFICIENT_STOCK. |
| Receipt | A batch is created with remaining_qty = 0. A deferred constraint trigger on batches verifies at commit that exactly one RECEIPT movement exists with qty_delta = initial_qty. Partial unique index: one RECEIPT per batch. A batch with no receipt cannot commit. |
| Consumption, disposal | Negative qty_delta by type check, required reference per type, FEFO locks taken before inserting. |
| Adjustment | ADJUSTMENT_IN positive, ADJUSTMENT_OUT negative, reason_code required, value at the batch's unit_cost. |
| Reversal | BEFORE INSERT trigger on REVERSAL rows requires: the original exists, same kitchen and batch; the original is not itself a REVERSAL; qty_delta is exactly the negation, and unit_cost_snapshot and value_vnd match the original; reference columns are copied from the original so reports can net it. UNIQUE (reverses_movement_id) stops double or excessive reversal. Reversing a receipt that has been consumed fails through the non-negative check. Undoing a reversal means posting a new operation. |
| Direct updates of remaining_qty | BEFORE UPDATE trigger on batches rejects any change to remaining_qty unless a transaction-local flag (set_config('app.ledger_apply','on', true)) is set, which only the movement trigger sets and resets. |
| Other batch immutables | The same trigger rejects changes to id, kitchen_id, ingredient_id, initial_qty, unit_cost. Only location, expiry_date, received_on may change (audited in the service). |
| Ledger immutability | BEFORE UPDATE OR DELETE trigger on stock_movements and audit_log raises. |
| TRUNCATE | BEFORE TRUNCATE statement trigger raises unless app.allow_demo_reset = 'on', which only reset_demo sets (I.3). |
| Rollback guarantees | The trigger runs inside the caller's transaction, so any error aborts everything. Services use one transaction per request, never commit midway, never swallow exceptions, and never use savepoints to hide a failed insert. |
| ORM staleness | After inserting movements, the service refreshes affected Batch objects (or reads with RETURNING) because the cached quantity changed in the database. |

Integration tests (mandatory, one per movement type):

RECEIPT: deferred receipt trigger passes and fails correctly; a second receipt per batch is rejected.

SALE_CONSUMPTION: single batch, multi-batch FEFO, partial with shortage.

USAGE_CONSUMPTION.

DONATION, SELLOFF, WASTE: each with its disposal reference.

ADJUSTMENT_IN, ADJUSTMENT_OUT.

REVERSAL: valid; double reversal rejected; reversal of a reversal rejected; mismatched fields rejected; reversing a consumed receipt rejected.

Negative-stock attempt rolls back every row of the request.

Injected failure after N movements leaves no batches, movements, sale rows or idempotency rows.

Direct UPDATE batches SET remaining_qty, UPDATE/DELETE on movements, and TRUNCATE are all rejected.

Per-type sign and reference CHECKs.

Two concurrent transactions against one batch never go negative.

Reconciliation query: for every batch, remaining_qty equals the sum of its movements; for every sale line, cogs_vnd equals the sum of its movement values.

A schema test asserts the triggers exist (Alembic does not detect trigger drift).

Trigger versus application-level updates:

| Aspect | DB trigger (proposed) | Application-level |
| --- | --- | --- |
| Invariant strength | Holds for every writer: services, seed scripts, manual SQL | Holds only if every code path goes through InventoryService |
| "Forgot to update" failure mode | Impossible | Possible; needs review and tests |
| Testability | Needs real Postgres tests (already required) | Unit-testable more cheaply |
| Visibility | Logic lives in SQL; Alembic does not autogenerate it; needs hand-written migrations and drift tests | Everything in Python |
| Performance | One extra UPDATE per movement in both approaches | Same |
| Supabase / local Postgres | Works on both | Works on both |
| Debugging | Errors surface as constraint messages that the service must map | Direct |

Recommendation: keep the trigger. It enforces the accepted "never negative" rule at the lowest level, and the safeguards above address its weaknesses. The accepted architecture (ledger and FEFO) does not change either way. If the team cannot commit to the test matrix above, fall back to application-level updates plus the same CHECK and reconciliation tests. Hardening for later: a dedicated non-owner database role for runtime with column-level grants (see section 8).

4. Consistency review: findings and resolutions

| # | Finding in Revision 3 | Resolution | Impact |
| --- | --- | --- | --- |
| 1 | COUNT units auto-convertible | 2.A | DB, API |
| 2 | Expired policy mixed with classification | 2.B | DB, API |
| 3 | Idempotency in-progress state undefined | 2.C | DB, API |
| 4 | COOK under disposals | 2.D | API |
| 5 | Replenishment edge cases missing; no order step | 2.E | DB, API |
| 6 | Shortage resolution accounting missing | 2.F | DB, API |
| 7 | Usage-slip shortages impossible: stock_shortages.sale_line_id was mandatory but usage slips have no sale line | document_line_id alternative with exactly-one check | DB |
| 8 | Movements could not be traced to the shortage they resolved | stock_movements.shortage_id | DB |
| 9 | Migration order: shortages created after movements, but movements reference shortages | Shortages before movements (section 5) | DB |
| 10 | Composite FK parents lacked their required UNIQUE (kitchen_id, id) listed | Explicit matrix (section 4.1) | DB |
| 11 | Missing indexes on FK child columns and filters | Index list (section 4.2) | DB |
| 12 | I3 request named unit_cost_vnd_per_unit but invoices carry price per entered unit | Renamed unit_price_vnd (per entered unit). Server computes unit_cost per base unit = unit_price ÷ conversion factor, stored at 6 decimals. value_vnd is rounded once per movement with the shared helper. Remaining value (remaining × unit_cost) may differ from summed movement values by rounding; documented, not hidden. | API |
| 13 | documents.business_date meaning for invoices unspecified | For IMPORT_INVOICE, business_date becomes the created batches' received_on | API |
| 14 | Uploaded file display name missing | documents.original_filename (sanitized, display only) | DB, API |
| 15 | One sales report could be applied to two sales | Partial UNIQUE (source_document_id) WHERE NOT NULL on sales | DB |
| 16 | A document line could name both a dish and an ingredient | CHECK (NOT (ingredient_id IS NOT NULL AND dish_id IS NOT NULL)) | DB |
| 17 | min_history_days could exceed the window | CHECK (min_history_days <= consumption_window_days) | DB |
| 18 | Reports must net reversals but reversal rows carry no category | Reversals are classified through the reversed movement's type (join), and copy its references (G) | none |
| 19 | No GET for one batch; notifications link to batches | Added GET /batches/{id} (B1) | API |
| 20 | Low-stock notification definition unclear | LOW_STOCK uses the replenishment rules (2.E); below min_history_days only the minimum-stock rule applies | none |
| 21 | Privilege assumptions implicit: the backend connects as a privileged role that bypasses RLS | See section 8 risks; RLS with no policies protects against Data API exposure, not against backend bugs | docs |

Derivability check for the required reports. Every figure can be derived from the proposed tables without inventing data:

Actual COGS: sum of value_vnd of SALE_CONSUMPTION movements joined to sale_lines and sales.business_date, netted with reversals.

Estimated COGS: estimated_cost_vnd of shortages with WRITTEN_OFF_ESTIMATED, joined to the sale's date.

Unrecorded cost: shortages with WAIVED.

Disposal costs: DONATION, SELLOFF, WASTE movements by disposal_id; sell-off revenue from disposals.revenue_vnd.

Adjustments: ADJUSTMENT_IN/OUT values. Reversals: through reverses_movement_id.

Consumption for replenishment: movements by type and occurred_on.

4.1 Composite foreign key matrix

Every tenant table has UNIQUE (kitchen_id, id). Additional uniques: ingredients (kitchen_id, id, base_unit_code) and batches (kitchen_id, ingredient_id, id).

| Child column(s) | Parent |
| --- | --- |
| ingredient_aliases (kitchen_id, ingredient_id) | ingredients |
| ingredient_unit_conversions (kitchen_id, ingredient_id, base_unit_code) | ingredients (kitchen_id, id, base_unit_code) |
| batches (kitchen_id, ingredient_id); source_document_line_id | ingredients; document_lines |
| recipe_items (kitchen_id, dish_id), (kitchen_id, ingredient_id) | dishes, ingredients |
| documents, document_lines (kitchen_id, document_id); ingredient_id, dish_id | documents, ingredients, dishes |
| sales.source_document_id; sale_lines (kitchen_id, sale_id), dish_id, source_batch_id | documents, sales, dishes, batches |
| disposals (kitchen_id, batch_id) | batches |
| stock_shortages: sale_line_id or document_line_id, ingredient_id, estimate_batch_id | sale_lines, document_lines, ingredients, batches |
| stock_movements: (kitchen_id, ingredient_id, batch_id), sale_line_id, disposal_id, document_line_id, shortage_id, reverses_movement_id | batches, sale_lines, disposals, document_lines, stock_shortages, stock_movements |

4.2 Indexes (additions to Revision 3)

| Table | Index |
| --- | --- |
| batches | (kitchen_id, ingredient_id, received_on) (history), plus the two partial indexes already specified |
| recipe_items | (kitchen_id, ingredient_id) ("ingredient in use" check) |
| documents | (kitchen_id, status, created_at) |
| sales | (kitchen_id, business_date); partial unique (source_document_id) |
| sale_lines | (kitchen_id, sale_id), (kitchen_id, dish_id) |
| disposals | (kitchen_id, occurred_on), (batch_id) |
| stock_shortages | partial (kitchen_id) WHERE status = 'OPEN', (sale_line_id), (document_line_id) |
| stock_movements | existing five, plus (shortage_id) |
| audit_log | (kitchen_id, created_at), (entity_type, entity_id) |
| idempotency_keys | (created_at) for cleanup |

5. Revised migration order

| Rev | Content |
| --- | --- |
| 0001 | Naming convention, user_profiles, kitchens, kitchen_settings (with the new settings and the min_history_days check) |
| 0002 | units (with nullable-factor constraint and seed), ingredients (with order_step), aliases, ingredient_unit_conversions (with base_unit_code) |
| 0003 | dishes, recipe_items |
| 0004 | documents (with original_filename), document_lines, idempotency_keys |
| 0005 | batches (no triggers yet) |
| 0006 | sales, sale_lines (with source_batch_id, status FULL/PARTIAL/RESOLVED) |
| 0007 | disposals |
| 0008 | stock_shortages (with document_line_id, estimate_batch_id) |
| 0009 | stock_movements, all triggers and guards from section 3, the deferred receipt constraint trigger, the TRUNCATE guard |
| 0010 | notification_reads, audit_log (append-only trigger) |
| 0011 | RLS enabled on every table including units, no policies; role revokes guarded by a role-exists check |

Build approach (recommended): write the complete schema in one pass (0001–0011), even though some tables stay unused in the MVP. Retrofitting ledger CHECKs and composite keys later is far costlier than creating empty tables. Features are staged in the API and UI, not in the schema.

6. MVP versus deferred scope

Three tiers: Core (the end-to-end demo path), Stretch (build if core is stable), Deferred (documented, not built; schema already supports it where noted).

| Area | Core | Stretch | Deferred |
| --- | --- | --- | --- |
| Account | Login, JWT verification, GET /me, kitchen resolution, seed and reset | CSP in report-only mode | Registration UI, MFA, deletion, members |
| Ingredients | C1–C6 (aliases, conversions, order_step) |  |  |
| Inventory | I1 overview with expiry classification, I2, B1, I3 manual receipt (idempotent), I6 summary | I4 metadata edit, I5 adjustments, I7 movement history | Stocktake sessions |
| Import | CSV and Excel upload (parsed in memory), manual draft, D3–D8, human confirm of imports, expiry required | D2 document list | OCR for image/PDF (schema and ocr_status retained) |
| Menu | M1–M5 with estimated cost, margin, max portions | sort=suitability ranking | Recipe versioning |
| Sales | Sales-report confirm (CSV/Excel), FEFO consumption, S1–S3, shortage resolve S4 with CONSUME_FROM_STOCK and WAIVE | WRITE_OFF_ESTIMATED; S5 cook | Usage slips; sale void and correction; resolution reversal |
| Expiring stock | P1 list (policy placeholder) | P2 WASTE, DONATION, SELLOFF |  |
| Reports | R1 summary with labels | R2 waste, R3 dishes | Quarter and custom-range UI, charts |
| Replenishment | RS1 |  | Forecasting, supplier and purchase orders |
| Notifications |  | N1 computed alerts | N2 read state (table retained), push notifications |
| AI assistant | AI1 with rule-based provider and tools: stock, expiring, cookable dishes, dish margins, period summary, replenishment | get_waste_summary tool, evaluation set run | External LLM provider |
| Platform | Idempotency protocol on write endpoints, composite FKs, ledger triggers, RLS | Audit log writes, FileStore stub | Rate limiting, dedicated runtime DB role, production hosting, monitoring, backups |

Nothing in the architecture is removed. Deferred items stay in the design and in the schema.

7. Decisions

7.1 Remaining OPEN

| ID | Decision |
| --- | --- |
| D7 | Accounting policy: COGS attribution and treatment of estimates, donation treatment, headline profit figure, rounding, direct usage in COGS, report naming |
| D9, D9a, D9b | Food-safety assumptions; expiry boundary and whether every ingredient needs an expiry date; how back-dated reports treat stock; shelf-life and storage-tip catalog; the expired-stock defaults in 2.B |
| D18 | Antigravity conventions (deferred) |
| D20 | Production hosting (local-first accepted) |
| D24 | Choice of an external LLM provider (rule-based default accepted) |
| D26 | Supabase plan limits, pausing, backups |
| Parameters | Warning days, coverage days, window, minimum history, unusual-quantity ratio, back-date limit, upload limits, lock timeout, idempotency retention |

7.2 Remaining PROPOSED

D29 (revised protocol, 2.C), D30 (with safeguards, section 3), D32 (revised, 2.F), plus the Revision 3 items D4a, D23 optional set, D31, D33, D34 with the implementation conditions below, and the demo runbook from Revision 3.

Implementation conditions (recommendations unchanged):

| ID | Condition |
| --- | --- |
| D4a | Before wiring auth, verify in the project: whether tokens use asymmetric signing, the supabase-js session storage default, and the public key variable name. Roll out CSP in report-only mode before enforcing. |
| D23 | ocr extras stay uninstalled in the MVP. Excel read through openpyxl in read-only, values-only mode. |
| D31 | Central models in backend/app/db/models/. Modules may import models only inside their own repositories, never another module's repository. The Database Agent owns model PRs; the Backend Agent requests changes through an issue. |
| D33 | The MVP parses CSV and Excel uploads in memory and stores only file_sha256, original_filename and parsed lines. It does not persist the original file, so it cannot be re-downloaded. FileStore exists as an interface; the first real adapter arrives with OCR. |
| D34 | PyJWT with an algorithm allowlist, JWKS cache with refresh on unknown kid, small clock leeway, tests for expired, wrong-audience, wrong-issuer and unsigned tokens. |

7.3 Decisions that need business or team approval versus technical choices

Needs team or business approval: everything in 7.1, plus the expired-stock defaults, the shortage resolution set (D32), and cost basis for estimates.

Decided technically (made in this revision, no further approval requested): conversion algorithm, idempotency claim mechanics, trigger and guard details, index and constraint additions, migration order, replenishment arithmetic and rounding mechanics, and API shape changes.

8. Risks and assumptions

Risks

Privileged backend role. The backend connects as a role that bypasses RLS. RLS with no policies protects against Data API exposure, not against a backend bug or a leaked database credential. The triggers guard against code bugs, not against a database owner who disables them. Hardening (deferred): separate migration and runtime roles; runtime role without ownership and with column-level grants.

Token revocation lag. A JWT stays valid until exp even if the Supabase user is banned. Acceptable for a single-account demo; revisit for production.

Trigger complexity under a 24-hour build: mitigated by the test matrix; fallback described in section 3.

Estimates may be mistaken for facts if the UI drops the ESTIMATE label. Treat the label as a contract and test for it.

Past-period COGS can change after late shortage resolutions (2.F). cogs_complete mitigates but does not eliminate this.

Double submission with different keys (2.C residual risk).

Supabase specifics unverified: signing method, pooler IPv4/IPv6 reachability from the demo network, plan limits (D26). Verify before the demo date.

Rule-based assistant limits: only the supported question types are understood; everything else returns a clear "cannot answer" with suggestions.

24-hour scope: the Core tier is already large. If the schedule slips, cut Stretch first, never the ledger tests.

Assumptions

One kitchen, one account, one timezone (Asia/Ho_Chi_Minh).

VND only; no tax or discount handling.

Sales reports list dishes and portions; recipes in the system define consumption.

Demo data goes through the real services, so the ledger is genuine.

Placeholders are values to be replaced, not recommendations.

9. API and database change summary

API

Added: POST /batches/{id}/cook (S5), GET /batches/{id} (B1).

Renamed: GET /replenishment-suggestions is now RS1; I3 field unit_cost_vnd_per_unit → unit_price_vnd.

Changed: P2 accepts DONATION | SELLOFF | WASTE only; P1 gains policy fields; Settings gain expired_batches_consumable and expired_batch_actions; Ingredient gains order_step; Document gains original_filename; sale line gains estimated_cogs_vnd, consumption_status RESOLVED, source_batch_id; S4 response and R1, R3 and RS1 schemas revised as in 2.E and 2.F; I7 references include shortages.

New errors: ACTION_NOT_PERMITTED_FOR_EXPIRED_BATCH, DISH_DOES_NOT_USE_BATCH_INGREDIENT, NO_COST_HISTORY, NO_CHANGE, LOCK_TIMEOUT; idempotent endpoints add the Idempotent-Replay response header.

Database

units: nullable factor with CHECK. ingredient_unit_conversions: base_unit_code, extra FK and CHECK.

ingredients: order_step. kitchen_settings: two expired-stock fields and the history CHECK.

documents: original_filename. document_lines: not-both CHECK.

sales: unique on source_document_id. sale_lines: source_batch_id, status RESOLVED.

stock_shortages: document_line_id, estimate_batch_id, exactly-one and per-resolution checks.

stock_movements: shortage_id.

idempotency_keys: status, actor_id, completed_at.

batches: deferred receipt constraint trigger, update guards. New indexes (4.2). Migration order (section 5).

I have not started Phase 4 and have created no code, migrations, repository files or agent files. I'll wait for your review of Revision 4.
