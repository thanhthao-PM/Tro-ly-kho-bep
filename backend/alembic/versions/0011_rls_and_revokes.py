"""0011 RLS on every table; revoke from PUBLIC, anon, authenticated (Rev 6.3 s3.2.6 step 4, s5, implementation-plan 1.3).

Role-independent: custom roles (ledger_owner, app_runtime) and policies belong to D30a, which is DISABLED.
No ALTER DEFAULT PRIVILEGES here (not specified for Core by 6.3).
RLS is enabled but NOT forced, so the owner role used by the API in Core mode bypasses it.
The built-in Supabase roles anon/authenticated are skipped only if they do not exist (local test DBs).
alembic_version is included, so the C6 catalog test needs no exclusion.
"""
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

UP = [
"""DO $do$
DECLARE t text; r text;
BEGIN
  FOR t IN SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public' LOOP
    EXECUTE 'ALTER TABLE public.' || quote_ident(t) || ' ENABLE ROW LEVEL SECURITY';
  END LOOP;
  REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC;
  REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC;
  REVOKE ALL ON SCHEMA ledger_internal FROM PUBLIC;
  REVOKE ALL ON ALL FUNCTIONS IN SCHEMA ledger_internal FROM PUBLIC;
  FOREACH r IN ARRAY ARRAY['anon','authenticated'] LOOP
    IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = r) THEN
      EXECUTE 'REVOKE ALL ON ALL TABLES IN SCHEMA public FROM ' || quote_ident(r);
      EXECUTE 'REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM ' || quote_ident(r);
      EXECUTE 'REVOKE ALL ON SCHEMA ledger_internal FROM ' || quote_ident(r);
      EXECUTE 'REVOKE ALL ON ALL FUNCTIONS IN SCHEMA ledger_internal FROM ' || quote_ident(r);
    END IF;
  END LOOP;
END
$do$""",
]
DOWN = [
"""DO $do$
DECLARE t text;
BEGIN
  FOR t IN SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public' LOOP
    EXECUTE 'ALTER TABLE public.' || quote_ident(t) || ' DISABLE ROW LEVEL SECURITY';
  END LOOP;
END
$do$""",
]


def upgrade() -> None:
    for s in UP:
        op.execute(s)


def downgrade() -> None:
    for s in DOWN:
        op.execute(s)
