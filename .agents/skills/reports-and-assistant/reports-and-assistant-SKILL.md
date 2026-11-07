---
name: reports-and-assistant
description: Builds Kitchen Assistant reports and the provider-independent rule-based assistant from real inventory data. Use for R1/R3/RS1 reporting, cost labels, stock questions, expiry suggestions or assistant tools.
---

# Reports and Assistant

## 1. Purpose

Keep reports and assistant responses grounded in authoritative database data, with deterministic business rules separated from any AI provider.

## 2. Activate when

- Implementing or reviewing R1, R3, RS1 or documented inventory/cost reporting.
- Building the rule-based assistant, its internal query tools or response formatting.
- Handling `ESTIMATE`, actual-vs-estimated status, usable stock, cost or replenishment suggestions.

## 3. Do NOT activate when

- Integrating an external LLM provider in the MVP; that is Deferred.
- Defining new accounting policy, report formulas, assistant tools or response contracts not specified by the sources.
- Building unrelated UI or persistence modules.

## 4. Required documents

- `docs/architecture/architecture-revision-6.3.md` — R1/R3/RS1, `ledger_effective`, usable stock and estimate rules.
- `docs/architecture/ARCHITECTURE_REVISION_5.md` — cumulative formulas and API contracts; verify path.
- `docs/implementation/implementation-plan.md` — rule-based provider and service boundaries.
- `PROJECT_CONTEXT.md` — required but unavailable during authoring.
- Revision 3/4 source contracts — not supplied; request them if report/API details depend on them.

## 5. Core rules

- Reports must derive from actual persisted application/database data, not demo fixtures, localStorage or guessed totals.
- Preserve the documented report contracts R1 and R3 and replenishment contract RS1. Do not invent filters, formulas, rounding rules, time attribution or headline profit definitions.
- Use the documented `ledger_effective`/attribution-date basis and cost snapshot rules. Do not independently recompute historical ledger values using current ingredient prices.
- Preserve `all_actual`, `has_open_shortages`, COGS/consumption status and estimate semantics. If a value is estimated, display the required `ESTIMATE` label; never present it as actual.
- RS1 uses the approved Revision 5/6.3 replenishment contract. Do not replace its observed-day, minimum-stock, coverage or order-step rules with a simpler heuristic.
- `usable(batch)` is the shared stock eligibility definition for FEFO, replenishment and assistant tools. Never create a report-specific variant.
- MVP assistant is provider-independent with a default **rule-based provider**. The Implementation Plan identifies internal tools for usable inventory, cookable dishes and replenishment suggestions.
- Deterministic business calculations and authorization remain in backend services/database. The assistant may query approved tools and summarize their results; it must not bypass services or write directly to ledger tables.
- External LLM integration is **DEFERRED**. Do not add OpenAI, Gemini or other provider SDKs, API keys, network calls or provider-specific code to the MVP.
- The assistant must not fabricate stock, expiry, profit or menu facts. If data is missing, stale, unavailable or insufficient, say so and distinguish estimates from actuals.
- D20 discrepancy remains unresolved in this Skill: Revision 6.3 says OPEN; Implementation Plan records Firebase Hosting + Cloud Run. Do not change deployment architecture here.

## 6. Recommended procedure

1. Identify the report/tool contract and the source of each value.
2. Trace data from the approved database view/service to the report or assistant output.
3. Reuse deterministic domain services for stock, FEFO, costs and replenishment.
4. Preserve report flags, attribution dates, units and estimate labels.
5. For assistant questions, map intent to an approved internal tool; do not create a new tool contract from a sample prompt.
6. Return concise results with relevant dates, units and caveats supported by data.
7. Test known fixtures, boundary conditions, insufficient history and open-shortage/estimate cases.
8. Record missing formulas or provider contracts as `NOT SPECIFIED` / Deferred.

## 7. Validation checklist

- [ ] Data originates from the approved database/service path.
- [ ] R1, R3 and RS1 match their source contracts.
- [ ] Attribution-date and cost snapshot semantics are preserved.
- [ ] `ESTIMATE`, `all_actual` and shortage status are represented correctly.
- [ ] Shared `usable(batch)` semantics are used consistently.
- [ ] Assistant answers are grounded in tool results and state uncertainty.
- [ ] Assistant cannot directly mutate ledger data.
- [ ] No external LLM integration or secret was introduced.
- [ ] Tests cover actual/estimated, shortage and insufficient-data cases.

## 8. Common mistakes

- Treating demo assistant text as proof of an LLM integration.
- Returning plausible answers without querying the database.
- Hiding estimate caveats or reporting estimated values as actual.
- Rewriting R1/R3/RS1 formulas from memory.
- Using raw batch quantity instead of `usable(batch)`.
- Adding external provider calls in Core.
- Giving the assistant a direct write path to stock movements.

## 9. Expected handoff

Document report/tool contracts used, data lineage, calculation/flag semantics, example grounded responses, test commands and evidence, estimate limitations, and unresolved policy/API contracts.
