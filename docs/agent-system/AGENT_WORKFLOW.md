# AGENT_WORKFLOW.md
## Kitchen Assistant — Agent Collaboration Workflow

**Status:** Operational guide  
**Applies to:** Core MVP unless an approved change says otherwise  
**Authority:** `AGENTS.md` and the approved architecture documents take precedence over this workflow.

---

## 1. Purpose

This document defines how the five Agent roles, six existing Skills, and five reusable Commands work together.

It describes collaboration and handoffs. It does not change product architecture, implementation phases, business rules, security boundaries, or unresolved decisions.

## 2. Components and responsibilities

| Component | Responsibility | Does not do |
|---|---|---|
| `AGENTS.md` | Shared project-wide rules and constraints | Replace architecture source documents |
| Agent definitions | Define role, responsibility, boundaries, expected outputs | Grant actual filesystem access or guarantee autonomous subagents |
| Skills | Provide focused domain procedures and checklists | Override architecture or owner decisions |
| Commands | Reusable task prompt templates | Guarantee native slash-command support on every platform |
| `AGENT_WORKFLOW.md` | Define collaboration and handoffs | Change implementation scope |
| `AGENT_SYSTEM_GUIDE.md` | Explain installation and usage | Claim platform-specific integration that has not been configured |

## 3. Agent roles

### 3.1 System Architect
- Reads `AGENTS.md` and the relevant architecture/plan sections first.
- Clarifies scope, dependencies, interfaces, acceptance criteria, and affected modules.
- Identifies conflicts, missing contracts, risks, and unresolved decisions.
- Produces a concise implementation brief and assigns relevant role(s).
- Reviews cross-module consistency and prepares or recommends a Change Proposal when needed.
- Must not independently approve an owner decision or silently change frozen architecture.

### 3.2 Database Engineer
- Owns database implementation work: schema, Alembic migrations, constraints, indexes, triggers, views, and DB-level tests.
- Preserves Alembic as the sole schema authority.
- Documents migration assumptions, upgrade/downgrade behavior, and test evidence.
- Must not introduce D30a runtime roles, ownership transfers, grants, or policies while D30a remains PROPOSED / DISABLED.
- Must not claim RLS alone isolates tenants in Core Mode.

### 3.3 Backend Developer
- Implements FastAPI modules, domain services, repositories, authentication integration, and API contracts within approved architecture.
- Applies tenant `kitchen_id` filtering in repository access as required by project rules.
- Coordinates database contract changes with Database Engineer before relying on them.
- Adds unit and integration tests appropriate to the change.
- Must not move the modular monolith to microservices or bypass ledger/domain invariants.

### 3.4 Frontend Developer
- Implements React + TypeScript + Vite UI, components, hooks, client services, and responsive behavior.
- Uses documented API contracts; flags missing or conflicting contracts instead of inventing them.
- Keeps secrets out of frontend code and `VITE_` variables.
- Does not decide the unresolved styling approach without owner approval.

### 3.5 QA & Security Engineer
- Reviews acceptance criteria, tests, security boundaries, failure paths, and regression risks.
- Can participate at planning, implementation, and final review stages.
- Verifies evidence rather than assuming a command passed.
- Reports test level and environment: static check, unit, DB, integration, E2E, or manual verification.
- Must not weaken, delete, or bypass required Core tests to obtain a green result.

## 4. Skills selection

Load only the Skills relevant to the current task. Do not load all six automatically.

| Skill | Use when |
|---|---|
| `inventory-ledger` | Inventory movements, batches, FEFO, costing, ledger, stock reconciliation |
| `backend-module` | FastAPI, domain services, repositories, API implementation |
| `frontend-responsive` | React UI, responsive layout, frontend integration |
| `document-ingestion` | Importing or processing documents and structured input |
| `reports-and-assistant` | Reports, summaries, assistant responses, rule-based assistant behavior |
| `testing-and-git` | Test strategy, test execution, Git operations, handoff evidence |

If a Skill is missing or its content is not available, report that fact. Do not fabricate its instructions.

## 5. Standard task workflow

Use the smallest workflow that safely covers the task.

### Step 0 — Establish context
Run or apply `project-check` before substantial implementation, or when repository state/architecture alignment is uncertain.

Read:
1. `AGENTS.md`.
2. Relevant sections of `docs/architecture-revision-6.3.md`.
3. Relevant sections of `docs/implementation-plan.md`.
4. `docs/PROJECT_CONTEXT.md` when project constraints or current status are relevant.
5. Relevant decision records and only the code/tests needed for the task.

Do not upload or load the entire repository by default.

### Step 1 — Define the task
System Architect (or the current AI acting in that role) records:
- Goal and in-scope behavior.
- Out-of-scope behavior.
- Affected files/modules.
- Existing contract(s) and dependencies.
- Acceptance criteria.
- Required tests and verification.
- Open questions or owner decisions.

If the task is narrow and has no architecture impact, the responsible Agent may proceed without a separate formal planning document.

### Step 2 — Select responsible roles
Assign only the roles needed.

Typical routing:
- Database/schema/migration: Database Engineer + QA & Security Engineer; System Architect if contract or architecture impact exists.
- Backend API/domain: Backend Developer; Database Engineer if schema changes; QA & Security Engineer for tests/review.
- Frontend-only: Frontend Developer; QA & Security Engineer when behavior or regression risk warrants it.
- Cross-layer feature: System Architect coordinates Database Engineer → Backend Developer → Frontend Developer, with QA & Security involved throughout.
- Bug fix: relevant implementation Agent + QA & Security Engineer.
- Documentation-only: System Architect or the relevant domain Agent.

### Step 3 — Agree on the contract before dependent work
For cross-layer or parallel work, define the contract first:
- API request/response and error shape.
- Database tables/columns/constraints as applicable.
- Ownership of each file or module.
- Inputs, outputs, and acceptance criteria.
- Test responsibilities.

Do not ask multiple Agents to edit the same files concurrently.

### Step 4 — Implement in dependency order
Follow the approved Implementation Plan and task dependencies. For a cross-layer feature, the usual dependency order is:

`Database contract/migration` → `Domain/backend service and API` → `Frontend integration` → `Integration verification`

This is a default, not a reason to force irrelevant layers into every task.

### Step 5 — Review and test
Use `review-code` and `run-tests` as appropriate.
- QA & Security Engineer reviews changed behavior and security implications.
- Run the narrowest relevant tests first, then required broader tests.
- Preserve required Core DB and Core Integration tests.
- Never claim a test passed unless its output/evidence was observed.
- If a test cannot run, state why and mark it NOT RUN / UNVERIFIED.

### Step 6 — Handoff
Use `prepare-handoff` to report:
- What changed and why.
- Exact files created/modified.
- Tests run and actual results.
- Manual checks completed.
- What remains unverified.
- Blockers, risks, and next recommended action.

## 6. Parallel work rules

Parallel work is allowed only when tasks are independent and interfaces are agreed.

Safe examples:
- Frontend component work against an already-approved API contract while backend tests are being written.
- Independent documentation review and isolated unit-test review.

Do not parallelize:
- Competing edits to the same file.
- Schema changes and backend code that depends on an unsettled schema.
- Work based on unresolved architecture or owner decisions.
- Multiple implementations of the same feature without an explicit comparison task.

If the platform cannot spawn real subagents, simulate the roles sequentially in one conversation and label each role's contribution. Do not claim that independent agents ran.

## 7. Decision and escalation rules

Stop and request owner clarification when:
- A frozen architecture decision must change.
- A NEEDS DECISION or OPEN item blocks implementation.
- Source documents conflict and the hierarchy does not resolve the conflict.
- A requested feature expands Core MVP scope.
- A security or data-integrity invariant cannot be met.
- A migration could destroy or irreversibly transform data without an approved plan.

In particular:
- Keep D30a PROPOSED / DISABLED unless formally approved.
- Do not silently resolve the D20 status discrepancy between Architecture Revision 6.3 and Implementation Plan. Report it and follow the currently approved owner direction.
- Do not independently choose frontend styling while it remains NEEDS DECISION.
- Do not invent missing Revision 3/4 contract details.

Record proposed changes in `docs/DECISIONS.md` or the project's approved change-proposal process. A proposal is not an approval.

## 8. Definition of Done

A task is complete only when applicable conditions are met:
- Acceptance criteria are addressed.
- Changes follow `AGENTS.md` and approved architecture.
- Relevant tests are added/updated and run where possible.
- Test evidence and environment are recorded accurately.
- No secrets or prohibited dependencies are introduced.
- Documentation/status/handoff is updated when required.
- Unverified items and blockers are explicit.

A generated source-code ZIP is not proof that the application is integrated, runnable, or verified on the target Windows environment.

## 9. Token and context efficiency

- Read only the relevant sections and files.
- Load only the Agent roles and Skills needed for the task.
- Ask for a concise plan before large edits when scope is unclear.
- Prefer targeted diffs and file lists over repeated full-file dumps.
- Do not re-summarize unchanged architecture in every handoff.
- Keep a durable status/handoff file so a new AI session can resume without replaying the entire conversation.
