# AGENTS.md
# KITCHEN ASSISTANT — PROJECT-WIDE AI AGENT INSTRUCTIONS

## 1. Purpose

This file defines shared, platform-independent instructions for AI agents working on the Kitchen Assistant project, regardless of AI platform, model, IDE, or agent framework.

The objectives are to:

- Preserve consistency with approved architecture and project decisions.
- Prevent unauthorized changes to business rules, scope, and technical contracts.
- Implement changes in small, reviewable units.
- Protect database integrity, tenant isolation, and application security.
- Make testing and completion claims evidence-based.
- Support collaboration across team members using different AI tools.
- Minimize unnecessary context loading, repeated work, and token consumption.

This file is the common instruction layer. It does not replace architecture documents, implementation plans, technical contracts, or individual Skills.

## 2. Source of truth and decision handling

Before starting a task, inspect the relevant project documents and current implementation.

Use this precedence:

1. Explicitly approved project-owner decisions and accepted Change Proposals.
2. Architecture Revision 6.3 as the frozen Core Mode baseline.
3. Referenced specifications and contracts from Revisions 3, 4, and 5, when the actual source documents are available.
4. The current Implementation Plan.
5. `PROJECT_CONTEXT.md` and other project guides.
6. Source code, migrations, and tests as evidence of what has actually been implemented.

Important distinctions:

- Architecture documents describe intended behavior.
- Source code describes the current implementation; it does not automatically override approved architecture.
- Tests prove only the behavior they actually exercise.
- A successful syntax check does not prove runtime correctness.
- If a referenced source document is unavailable, report it as missing. Do not reconstruct or invent its contents.

### 2.1 Frozen architecture

Architecture Revision 6.3 is the frozen Core Mode baseline.

Agents MUST NOT:

- Edit Revision 6.3 directly.
- Change its schema, formulas, constraints, triggers, privileges, policies, migration order, or business workflows without approval.
- Treat implementation convenience as authorization to change architecture.
- Introduce an alternative architecture without a documented proposal.

Any proposed architectural change must be recorded as a Change Proposal. Only after approval may it be incorporated into a subsequent revision, such as Revision 6.4.

### 2.2 Unresolved decisions and discrepancies

Use these statuses consistently:

- `OPEN`: The architecture records a decision that has not been finalized.
- `NEEDS DECISION`: The project owner or team must choose an option.
- `NOT SPECIFIED`: Available source documents do not define the behavior.
- `PROPOSED`: A change has been suggested but not approved.
- `DISABLED`: The feature or implementation path must remain inactive.
- `VERIFIED`: Evidence demonstrates that the stated requirement was checked.
- `NOT VERIFIED`: Evidence is insufficient to claim successful verification.

Never silently resolve an `OPEN`, `NEEDS DECISION`, or `NOT SPECIFIED` item.

If a task depends on an unresolved decision:

1. Identify the exact decision and its source.
2. Explain why it blocks the task.
3. Do not implement behavior that assumes an answer.
4. Continue only with independent work that does not depend on that decision.

Known documentation issues that must remain visible:

- **D20 discrepancy:** The Implementation Plan records Firebase Hosting, Google Cloud Run, Supabase PostgreSQL, and Supabase Auth as the selected deployment approach, while Architecture Revision 6.3 still records D20 as `OPEN`. Do not silently reconcile the documents.
- **Frontend styling:** Tailwind CSS, CSS Modules, or a component library has not been selected in the available project context. Do not assume one is approved.
- **Alembic version table / Test Catalog C6:** The Implementation Plan records this as `NEEDS DECISION`. Do not choose an option independently.
- **Missing contracts:** If Revision 3 or Revision 4 source documents are not present, do not invent their ERD, API contracts, or detailed requirements.

## 3. Project architecture

The documented technology direction is:

| Layer | Technology |
|---|---|
| Frontend | React + TypeScript + Vite |
| Backend | FastAPI Modular Monolith |
| ORM | SQLAlchemy 2.x, synchronous |
| PostgreSQL driver | psycopg 3 |
| Database | Supabase PostgreSQL |
| Authentication | Supabase Auth |
| Database migrations | Alembic |
| AI | Provider-independent interface; Rule-based Provider by default |
| CI/CD | GitHub Actions |
| Frontend hosting | Firebase Hosting, as recorded in the Implementation Plan |
| Backend hosting | Google Cloud Run, as recorded in the Implementation Plan |

### 3.1 Architectural boundaries

- Keep the backend as a Modular Monolith.
- Do not introduce microservices without approval.
- Keep business logic out of frontend presentation components.
- Keep database access within the established backend data-access boundaries.
- Preserve the documented separation between API, domain services, repositories/data access, database, and AI provider.
- Do not introduce infrastructure, frameworks, or architectural dependencies without approval.

### 3.2 Frontend direction

The confirmed direction is one responsive React application for mobile and desktop web:

- One shared codebase.
- Shared application logic, API client, authentication, types, and validation.
- Responsive layouts and presentation where needed.

PWA support is reserved for future extension and is not part of the current MVP implementation. Do not add Service Workers, offline writes, background synchronization, push notifications, or local database synchronization unless separately approved.

Native Android/iOS applications and a separate mobile frontend are outside the current scope.

## 4. Core business and data-integrity rules

Consult the relevant architecture contracts before changing database or business logic. Do not infer detailed formulas or workflows from these summaries; the source contracts remain authoritative.

### 4.1 Ledger-first

- Treat the inventory ledger as the authoritative record of stock movements.
- Do not bypass the documented ledger workflow with independent stock-update mechanisms.
- Preserve approved movement sign conventions, value formulas, reversal rules, and immutability requirements.
- Do not invent movement types or movement workflows.

### 4.2 FEFO and batch eligibility

- Follow the documented FEFO rules and shared batch-usability definition.
- Do not create separate interpretations of batch eligibility in individual modules.
- Preserve expiry handling and settings behavior exactly as specified.
- If a required policy is unresolved or unspecified, do not invent a default.

### 4.3 Stock integrity and concurrency

- Stock must never become negative.
- Preserve database constraints, triggers, locking protocols, transaction boundaries, concurrency safeguards, and idempotency requirements.
- Do not replace database-enforced integrity with frontend-only validation.
- Do not bypass documented rollback behavior.

### 4.4 Costing and estimates

- Preserve actual batch-cost snapshots and approved costing formulas.
- Do not mix estimated and actual values.
- Display estimates with the labels required by the UI contract.
- Do not represent an estimate as an actual cost.
- Preserve documented attribution and reconciliation rules.

### 4.5 Tenant isolation

Every tenant-scoped data operation must follow the documented kitchen scope.

- Apply the required `kitchen_id` filters to tenant-scoped queries.
- Preserve composite foreign keys and commit-time validation triggers.
- Preserve cross-kitchen access protections and their tests.
- Do not assume RLS alone provides tenant isolation in Core Mode.

Core Mode uses the documented admin/migration-owner connection behavior. RLS is enabled, but the owner connection bypasses RLS because `FORCE ROW LEVEL SECURITY` is not used. Tenant isolation therefore also depends on application-level kitchen filters, composite foreign keys, and commit-time triggers, as documented.

Do not describe this configuration as if RLS alone protects all runtime access.

### 4.6 Database migrations

Alembic is the sole authority for database schema migrations.

Agents MUST NOT:

- Create ad-hoc schema-changing scripts as an alternative migration system.
- Modify a database schema manually as a substitute for migrations.
- Bypass the approved migration order.
- Change migration ownership, privileges, policies, or triggers without authorization.
- Delete or rewrite existing migrations merely to make a test pass.

Before writing a migration:

1. Inspect the existing migration history.
2. Read the relevant architecture specification.
3. Check dependencies and migration ordering.
4. Identify unresolved decisions.
5. Implement only the approved change.
6. Test migration application and the relevant database behavior where the environment permits.

### 4.7 D30a

D30a is `PROPOSED / DISABLED`.

Do not implement or activate D30a-specific runtime roles, ownership changes, or RLS policies unless the project owner explicitly approves the relevant change.

## 5. Scope control

Respect the project's Core, Stretch, and Deferred classifications.

- **Core:** Mandatory MVP requirements. Do not remove Core business rules, integrity protections, or required tests to save time.
- **Stretch:** May be postponed when schedule or implementation constraints require it. Do not silently promote Stretch functionality into Core.
- **Deferred:** Must not be implemented as active MVP functionality unless explicitly approved.

The Rule-based Provider remains the default AI implementation for the current Core MVP. OCR and external LLM provider integration are documented as deferred.

Before expanding or reducing scope, identify the affected requirement, reason, dependencies, and test impact. Obtain approval when an approved scope decision would change.

## 6. Security and secret management

- Never commit database credentials, Supabase secret keys, JWT secrets, API keys, or other credentials.
- Never place secrets in frontend code.
- Never expose secrets through `VITE_` environment variables.
- Use `.env.example` with placeholders only.
- Keep actual environment files local and excluded from Git.
- Do not ask users to paste secrets into public documentation or shared prompts.
- Do not weaken authentication, authorization, validation, or database privileges to make development easier.
- Do not disable security checks merely to make tests pass.
- Do not introduce unreviewed dependencies, scripts, or external services.

For security-sensitive work, use the relevant security and testing Skills.

## 7. AI agent working rules

### 7.1 Inspect before editing

Before changing code:

1. Read this file.
2. Identify the requested task and its boundaries.
3. Inspect the relevant source files and current Git status.
4. Read the relevant architecture contracts.
5. Identify existing tests and implementation patterns.
6. Identify unresolved decisions, missing documents, and dependencies.
7. Check whether another team member's changes may be affected.

Do not assume the repository is clean. Do not overwrite another person's work.

### 7.2 Work in small, coherent units

- Implement one clearly defined module or task at a time.
- Keep changes limited to the requested scope.
- Reuse established project patterns.
- Avoid unrelated refactoring and speculative features.
- Avoid unnecessary dependencies and duplicate documentation.
- Do not scan or load the entire repository when targeted inspection is sufficient.

### 7.3 Skills usage

The project maintains six core Skills:

- `inventory-ledger`
- `backend-module`
- `frontend-responsive`
- `document-ingestion`
- `reports-and-assistant`
- `testing-and-git`

Use the relevant Skill when its task domain applies.

- Load only Skills required for the current task.
- Follow each Skill's activation and non-activation conditions.
- Do not duplicate Skill instructions inside unrelated files.
- Do not assume a Skill exists at a particular path; inspect the repository's actual Skill structure.
- If a required Skill is missing or inaccessible, report that fact.
- Do not modify approved Skills without authorization.

### 7.4 Agent responsibilities

The project may use these specialized roles:

- System Architect
- Backend Developer
- Frontend Developer
- Database Engineer
- QA & Security Engineer

Each agent must stay within its assigned responsibility. An agent may identify a cross-domain issue, but must not independently change another domain's approved implementation or architecture.

The System Architect coordinates architecture consistency. This role does not have permission to override unresolved project-owner decisions.

### 7.5 Team collaboration

Different team members may use different AI tools.

- Treat this file and approved project documents as shared instructions.
- Do not assume another AI agent has access to your conversation history.
- Record important findings in project files, not only in chat.
- Avoid duplicating work already completed by another team member.
- Before editing shared files, inspect their current contents and Git status.
- Provide concise handoffs with exact file paths and verification evidence.

## 8. Token and context efficiency

Token efficiency is a required engineering constraint, but it must never weaken correctness, security, or required verification. These rules guide context usage; they do not guarantee a fixed token count because model and platform tokenization differ.

### 8.1 Context loading: progressive disclosure

Use the smallest sufficient context, in this order:

1. Read this `AGENTS.md`.
2. Read the task description and inspect only the directly relevant files.
3. Identify the relevant architecture section or contract; read that section rather than loading every architecture document.
4. Identify the one or two Skills that directly apply; load their metadata/instructions as supported by the platform.
5. Read additional files only when the task reveals a concrete dependency or ambiguity.

Do not automatically load all architecture documents, all Skills, all Agent definitions, all Commands, or the entire repository for every task.

Load a complete document only when:
- The task genuinely spans the whole document.
- The relevant section depends on definitions elsewhere in that document.
- A conflict cannot be resolved from targeted excerpts.
- The user explicitly requests a full-document review.

### 8.2 Task sizing and context budget

Classify work before starting:

- **Small:** One focused edit, explanation, or isolated bug. Load only the target file, its immediate dependencies, and the relevant rule.
- **Medium:** One module or feature spanning a few files. Load the module, its direct interfaces, relevant tests, and the applicable Skill.
- **Large:** Cross-module work, architecture review, migrations, or security-sensitive changes. Create a short task plan, identify required source documents, and load only the relevant sections from each.

Do not invent numeric token limits. If the platform exposes token usage or context limits, use that information. Otherwise, apply the qualitative budgets above.

If context becomes too large:
1. Stop loading unrelated material.
2. Summarize verified findings and unresolved questions in a compact handoff.
3. Continue from that handoff in a fresh task/session if needed.
4. Preserve exact file paths, decisions, test results, and next actions.

### 8.3 Avoid repeated work

- Do not reread unchanged files without a reason.
- Do not repeat explanations already recorded in `AGENTS.md`, architecture documents, Skills, or a current handoff.
- Do not regenerate files that already satisfy the task.
- Do not repeat successful checks unless the relevant code, configuration, environment, or test inputs changed.
- Before searching broadly, use known file paths, symbols, or prior search results.
- Do not ask the user for information already present in accessible project files or the current conversation.
- Do not ask an AI agent to summarize the entire repository when a targeted file list is sufficient.

### 8.4 Minimal file operations

- Inspect only files needed for the task.
- Prefer targeted search, targeted reads, and small diffs.
- Do not print or paste entire files into chat when a concise diff or summary is sufficient.
- Do not rewrite an entire file to change a small section unless necessary.
- Do not create duplicate reports, plans, or documentation.
- Do not generate large scaffolds or placeholder files unrelated to the requested task.
- Keep generated logs and test output focused on relevant failures and results.

### 8.5 Concise communication

Use compact, structured communication.

For routine tasks, report only:
- Result.
- Files changed.
- Checks executed and their outcomes.
- Remaining blocker or next action, if any.

For handoffs, use the template in Section 9. Avoid lengthy narratives, repeated architecture summaries, and speculative recommendations.

Do not omit important warnings, failed tests, security findings, or unresolved decisions merely to make a report shorter.

### 8.6 No uncontrolled all-in-one prompts

Do not attempt to implement the entire application, all modules, all tests, and deployment in one uncontrolled task.

Break large work into dependency-aware tasks. Each task must have:
- A clear scope.
- Explicit inputs.
- Expected outputs.
- Acceptance criteria.
- Relevant tests.
- A handoff.

This reduces repeated context, makes failures easier to isolate, and prevents broad unreviewed changes.

### 8.7 Platform limitations

`AGENTS.md`, Agent definitions, Skills, and Commands may be discovered differently by different AI platforms.

- Do not assume every platform automatically loads every project instruction file.
- Use platform-specific adapters only after verifying the platform's supported conventions.
- Keep platform adapters short and point them to canonical project instructions where supported.
- Do not copy the full contents of this file into every adapter or Skill.
- If the platform cannot load a required instruction automatically, include a concise reference to the required file in the task prompt.

## 9. Implementation workflow and handoff

Follow this sequence for implementation tasks.

### Step 1 — Understand

- Identify expected behavior and acceptance criteria.
- Locate relevant architecture contracts.
- Identify dependencies and unresolved decisions.
- Determine the smallest relevant context set.

### Step 2 — Plan

Prepare a proportionate plan containing:
- Files to inspect or change.
- Required tests.
- Risks and dependencies.
- Decisions or approvals needed.

For a small, unambiguous task, keep the plan to a few bullets or proceed directly.

### Step 3 — Implement

- Make the smallest coherent change.
- Follow established naming and module conventions.
- Preserve architecture and business invariants.
- Avoid unrelated modifications.
- Do not add speculative features.

### Step 4 — Verify

Run relevant checks that are available, such as formatting, linting, type checking, syntax/import checks, unit tests, database tests, API integration tests, frontend tests, or end-to-end tests.

Do not claim a check passed unless it was actually executed and its result was observed. If a check cannot be executed, state why.

### Step 5 — Review

Inspect the final diff for accidental changes, security implications, tenant-scoping behavior, database-integrity implications, test coverage, and documentation consistency.

### Step 6 — Handoff

Use this compact handoff format:

```text
TASK:
STATUS: DONE | PARTIAL | BLOCKED

CHANGED:
- path/to/file — concise description

VERIFICATION:
- command/check — PASS | FAIL | NOT RUN
- Environment: Windows | Linux | CI | PostgreSQL | Supabase | Mock (specify only what applies)

NOT VERIFIED / RISKS:
- Only material limitations or unresolved issues.

DECISIONS NEEDED:
- Exact question, or NONE.

NEXT:
- One recommended next task.
```

Do not include empty sections or repeat information already captured in an updated status document.

## 10. Testing and evidence

Testing is mandatory for implementation work.

Core DB tests and Core integration tests must not be removed or weakened to save time. Preserve the documented test tiers:

- Core DB invariants and Core DB tests.
- Core integration tests.
- Stretch tests.
- Deferred tests.

When reporting verification, distinguish clearly between:

- Static inspection.
- Syntax or compilation checks.
- Unit tests.
- Tests using mocks or fixtures.
- Tests against a real PostgreSQL database.
- Tests against Supabase.
- Tests executed on Windows.
- Tests executed in CI.
- Manual end-to-end verification.

A passing mock test does not prove Supabase integration works. A passing automated test does not prove the application has been manually verified on Windows.

Never fabricate test results, runtime behavior, database state, deployment status, environment configuration, or user acceptance.

If a test fails, report the failure. Do not hide or silently skip it.

## 11. Documentation and project status

Keep project documentation synchronized with actual implementation progress.

Where applicable, update:

- `BUILD_STATUS.md`
- `HANDOFF.md`
- Relevant README files.
- Relevant technical documentation.
- Test and verification records.

Distinguish accurately between implemented, tested and passed, tested and failed, partially verified, not verified, blocked, and deferred.

Do not mark a feature complete merely because its source files exist. Do not claim the application is fully runnable unless setup, configuration, database, integrations, and runtime behavior have been verified.

Avoid duplicating the same status in multiple documents. Update the designated source-of-status file and link or refer to it elsewhere when appropriate.

## 12. Git and file safety

- Inspect `git status` before editing.
- Preserve unrelated user changes.
- Do not discard, reset, or overwrite another person's work.
- Do not run destructive Git commands without explicit approval.
- Do not commit secrets, local environment files, or unnecessary build artifacts.
- Do not create duplicate files when an existing project file should be updated.
- Do not commit or push unless the task explicitly authorizes it.

If the working tree contains unexpected changes, report them before taking actions that could affect those files.

## 13. Stop conditions

Stop the affected implementation and report the issue when:

- A required architecture document or contract is missing.
- A task conflicts with Architecture Revision 6.3.
- An unresolved decision blocks correct implementation.
- A requested change would weaken database integrity or security.
- Existing user changes may be overwritten.
- Required credentials or external access are unavailable.
- The task requires an unapproved scope or architecture change.
- The available environment cannot verify a critical requirement.

Do not guess through a blocking issue. Independent work may continue only when it does not depend on the unresolved issue.

## 14. Definition of done

A task is complete only when:

- The requested behavior is implemented within scope.
- Relevant architecture requirements are preserved.
- Relevant tests have been executed where possible.
- Test results are reported accurately.
- Security and data-integrity implications have been reviewed.
- Documentation and status records are updated where applicable.
- Remaining limitations and unverified behavior are clearly stated.
- A usable handoff is provided.

Creating code is not, by itself, proof that a task is complete.

## 15. Final principle

**Preserve the approved architecture. Use the smallest sufficient context. Implement only authorized behavior. Verify before claiming completion. Report uncertainty instead of inventing answers.**
