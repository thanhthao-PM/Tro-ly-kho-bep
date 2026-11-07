# HANDOFF

## State
Phase 1 files exist (see BUILD_STATUS.md). No dependency installed from this session, no test run except py_compile.

## Next exact task
1. Owner runs the README "Verify Phase 1" steps and reports output (pytest, npm run build, /health/db, login).
2. Resolve blocker 1 (schema source) before Phase 2.
3. Then write Alembic 0001-0008 (tables, composite FKs), 0009 (ledger_internal, cache function, triggers, ledger_effective), 0010-0011 (remaining tables, RLS enable + revokes). Core mode only: D30a stays DISABLED.

## Rules for a new Claude session
Source priority: Rev 6.3 > implementation-plan > functional docx > demo HTML. No new revisions. Backend connects as migration owner (Core mode). Never put service_role key in frontend. Do not re-run successful setup.

## Failed commands
None recorded yet (nothing executed against Supabase from this session).
