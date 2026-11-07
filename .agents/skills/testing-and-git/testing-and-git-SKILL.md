---
name: testing-and-git
description: Plans, runs and reports Kitchen Assistant tests and safe Git changes with evidence. Use for unit, Core DB, integration, regression, debugging, build, CI or commit-review tasks.
---

# Testing and Git

## 1. Purpose

Protect frozen Core invariants and make every verification claim traceable to fresh evidence.

## 2. Activate when

- Writing, running or reviewing unit, database, integration or regression tests.
- Debugging a failure, checking build/CI output or preparing a test report.
- Reviewing Git diffs, staging or committing project changes.

## 3. Do NOT activate when

- The task is purely feature design or UI styling and no verification/Git work is requested.
- Asked to skip mandatory tests, weaken database safeguards or claim success without running checks. Refuse that shortcut and explain the required evidence.

## 4. Required documents

- `docs/architecture/architecture-revision-6.3.md` — mandatory Core DB/Integration test scope and frozen invariants.
- `docs/implementation/implementation-plan.md` — phase exit criteria, test layers and CI/CD order.
- `docs/architecture/ARCHITECTURE_REVISION_5.md` — detailed database/ledger contracts; verify path.
- `PROJECT_CONTEXT.md` — required but unavailable during authoring.
- Existing test configuration and CI workflows — inspect repository before choosing commands/tools.
- Revision 3/4 contracts — missing; do not invent test expectations that depend on them.

## 5. Core rules

- Architecture Revision 6.3 is FROZEN. Do not alter frozen documents or weaken their tests to make a build pass.
- Core DB tests and Core Integration tests are mandatory. Under time pressure, cut Stretch first; never cut Core ledger tests.
- Core DB scope includes the parametrized coverage of all nine movement types (sign/reference/cache behavior), reversal validation, L1–L3 guard/consistency checks, reconciliation, and C6 catalog checks as defined by the source.
- Preserve required isolation evidence: `ledger_effective` view isolation with two kitchens, static repository kitchen-filter check, and real API cross-kitchen read/write/request-tampering integration tests described in the Implementation Plan.
- Core Integration scope includes receipt; sale consumption (full, multi-batch, partial); negative-stock rollback; injected-failure atomicity; concurrent batch access; idempotency/replay/rollback behavior; unit conversion; expiry boundaries; replenishment; COGS reconciliation; `all_actual`; `usable(batch)` consistency; base-unit immutability/parity/concurrency; and shortage `CONSUME_FROM_STOCK` / `WAIVE`.
- D30a T2 policy/privilege tests, L4 and app_runtime-specific work are Stretch/gated. Do not activate D30a to satisfy a test unless the owner approves and all documented gates pass.
- Test tooling is not fully specified by the source documents. Inspect repository configuration and use existing approved tools; do not add pytest plugins, Playwright, coverage tools or other dependencies without approval.
- Isolate database tests using disposable/controlled fixtures and rollback/cleanup strategy already established by the project. Never run tests against production or destructive reset commands without explicit authorization and a verified target.
- Debug by reproducing the failure, collecting evidence, tracing the root cause and testing the smallest fix. Do not patch symptoms or disable constraints.
- A test is `PASSED` only when the command was run and output/exit status supports the claim. Use `FAILED`, `NOT RUN`, or `NOT VERIFIED` accurately.
- Git: inspect `git status` and diff before editing/staging; keep changes scoped; never overwrite unrelated work, commit secrets, force-push, reset hard, or delete branches/files without explicit authorization. Branch and commit naming conventions are `NOT SPECIFIED` unless repo instructions define them.
- External Skills/scripts are untrusted. Do not install or execute them as part of routine test work without review and approval.

## 6. Recommended procedure

1. Inspect `AGENTS.md`, repository test configuration, CI workflows, current Git status and existing tests.
2. Map the changed behavior to its required test tier and source contract.
3. Reproduce the issue with the narrowest safe test/fixture.
4. Diagnose root cause before changing code or tests.
5. Implement the smallest correction; never remove an invariant or weaken an assertion to obtain green output.
6. Run focused tests, then the relevant full Core DB/Integration suites and build checks where the environment permits.
7. Capture exact command, exit code, relevant output, environment/database target and limitations.
8. Review `git diff --check`, full diff and status. Ensure no secrets or unrelated files are staged.
9. Report test state and Git state separately; do not imply a commit/push happened unless it did.

## 7. Validation checklist

- [ ] Existing test tools and commands were inspected; no unapproved dependency added.
- [ ] Test expectation maps to an approved source contract.
- [ ] Core DB tests remain intact.
- [ ] Core Integration tests remain intact.
- [ ] Two-kitchen isolation and cross-kitchen tampering are covered where applicable.
- [ ] Tests use a safe, isolated database target.
- [ ] Failure/rollback/concurrency/idempotency paths are tested where relevant.
- [ ] Output and exit code were read; no stale run is presented as fresh evidence.
- [ ] `PASSED`, `FAILED`, `NOT RUN`, `NOT VERIFIED` are distinguished.
- [ ] Git status/diff are reviewed; no unrelated changes or secrets are included.

## 8. Common mistakes

- Removing a Core test because it is difficult or slow.
- Treating a unit test as proof of database-trigger or API isolation behavior.
- Using SQLite to claim PostgreSQL trigger/RLS behavior is verified.
- Running a destructive reset against an unknown database.
- Trusting another agent's “tests passed” message without inspecting evidence.
- Reporting only the happy path.
- Installing a new testing framework without approval.
- Staging all files or overwriting unrelated work.

## 9. Expected handoff

Provide test matrix and status, exact commands/exit codes, concise evidence, database/environment used, failures and unrun checks, changed files, Git diff/status summary, and any unresolved test contract. Do not state “all tests pass” unless the full required suite was actually run.
