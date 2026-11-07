---
name: frontend-responsive
description: Builds and reviews the Kitchen Assistant React, TypeScript and Vite web interface for desktop and mobile browsers. Use for pages, components, responsive layout, API client, auth state or frontend integration.
---

# Frontend Responsive

## 1. Purpose

Maintain one responsive web application while keeping business authority in the backend/database.

## 2. Activate when

- Creating or changing React components, pages, routes, forms, dashboards or responsive layouts.
- Implementing the API client, TypeScript API types, loading/error states or Supabase Auth UI integration.
- Reviewing desktop/mobile-web behavior and accessibility of the existing interface.

## 3. Do NOT activate when

- The request is to create a separate native Android/iOS app.
- The request is to implement PWA behavior for the MVP.
- The task concerns backend business logic, database schema or ledger rules rather than presentation/integration.

## 4. Required documents

- `docs/architecture/architecture-revision-6.3.md`.
- `docs/implementation/implementation-plan.md`.
- `docs/architecture/ARCHITECTURE_REVISION_5.md` for API and reporting contracts; verify path.
- `PROJECT_CONTEXT.md` — required but not available at authoring time.
- Relevant API contracts in Revision 3/4 — missing sources must be requested if needed.

## 5. Core rules

- Approved frontend stack: React + TypeScript + Vite.
- Build one responsive codebase for desktop and mobile web. Do not create a native mobile application.
- PWA is a future extension, not an MVP requirement.
- Styling choice is **NEEDS DECISION**. Do not add Tailwind, CSS Modules, a component library or another styling dependency without approval. Follow existing styles if already established.
- Keep presentation separate from business authority. The frontend may format and display API data; it must not independently decide FEFO batch selection, ledger movement signs, stock availability, cost snapshots, COGS or replenishment calculations.
- Use API contracts as the source for endpoint paths, request/response types, status values and error codes. Do not infer contracts from the demo UI.
- Use a shared API client and typed boundaries consistent with the repository. Do not duplicate fetch logic or hardcode API URLs in components.
- Supabase Auth is the selected authentication solution. Follow verified session/token handling. Do not assume JWT details or invent role/permission behavior.
- Do not trust a frontend `kitchen_id` value as authorization. The backend derives and enforces kitchen context.
- Reports must preserve the documented `ESTIMATE` labeling rules. Never hide an estimate label to improve visual appearance or present estimates as actuals.
- Core Mode remains the baseline. D30a is **PROPOSED / DISABLED**. Stretch must not block Core; Deferred features must not be silently added to MVP.
- D20 discrepancy must remain visible: Revision 6.3 says OPEN while the Implementation Plan records Firebase Hosting + Cloud Run. Do not resolve it in frontend configuration without owner confirmation.

## 6. Recommended procedure

1. Inspect existing routes, component conventions, styles, API client and state management before changing them.
2. Locate the approved API contract and create/update types from that contract, not from assumptions.
3. Separate server state, transient UI state and authentication state according to existing project conventions.
4. Implement responsive layouts with one component/application flow; verify narrow and wide viewports.
5. Represent loading, empty, validation, authorization, network and server-error states explicitly.
6. Render inventory, expiry and cost values as received from the API; do not recalculate domain values in UI.
7. Keep destructive or ledger-changing actions explicit and require the confirmation behavior defined by the contract.
8. Run the existing frontend checks. Do not add a new UI testing framework unless approved.

## 7. Validation checklist

- [ ] React + TypeScript + Vite only; no unapproved framework or dependency.
- [ ] Existing routing, styling and state conventions were inspected.
- [ ] Desktop and mobile-web layouts use the same application code.
- [ ] No native mobile or MVP PWA implementation was added.
- [ ] API client and types match approved contracts.
- [ ] Auth state follows Supabase Auth configuration without guessed JWT details.
- [ ] No business-critical inventory/cost calculations are duplicated in the UI.
- [ ] Estimate values retain visible `ESTIMATE` labels.
- [ ] Loading, empty and error states are handled.
- [ ] No secret, service-role credential or admin database credential is exposed to browser code.

## 8. Common mistakes

- Choosing Tailwind or another styling system before approval.
- Treating the HTML demo's sample behavior as a live API contract.
- Implementing a second native app or PWA scope without approval.
- Calculating stock, FEFO or COGS in the browser.
- Hiding estimate labels or confusing estimates with actual values.
- Putting privileged Supabase/database credentials in `VITE_*` variables.
- Trusting client-provided kitchen identifiers or authorization flags.

## 9. Expected handoff

List changed pages/components/API types, contract references, viewport checks, build/lint/test commands and outputs, accessibility/error-state notes, and any unresolved backend contract or styling decision.
