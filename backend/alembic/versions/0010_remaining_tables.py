"""0010 notification_reads, audit_log (Rev 3 II.2, Rev 4 s5). Re-applies the TRUNCATE guard to the new tables."""
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

UP = [
"""CREATE TABLE notification_reads (
  kitchen_id uuid NOT NULL REFERENCES kitchens (id),
  notification_key text NOT NULL,
  read_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (kitchen_id, notification_key)
)""",
"""CREATE TABLE audit_log (
  id bigserial PRIMARY KEY,
  kitchen_id uuid NOT NULL REFERENCES kitchens (id),
  actor_id uuid REFERENCES user_profiles (id),
  action text NOT NULL,
  entity_type text NOT NULL,
  entity_id text,
  before jsonb,
  after jsonb,
  request_id text,
  created_at timestamptz NOT NULL DEFAULT now()
)""",
"CREATE INDEX ix_audit_kitchen_created ON audit_log (kitchen_id, created_at)",
"CREATE INDEX ix_audit_entity ON audit_log (entity_type, entity_id)",
"""CREATE TRIGGER trg_audit_immutable BEFORE UPDATE OR DELETE ON public.audit_log
  FOR EACH ROW EXECUTE FUNCTION ledger_internal.reject_modification()""",
]
DOWN = ["DROP TABLE audit_log", "DROP TABLE notification_reads"]


def upgrade() -> None:
    for s in UP:
        op.execute(s)
    # same guard statement as 0009, now covering the tables created here
    op.execute(_truncate_guard())


def downgrade() -> None:
    for s in DOWN:
        op.execute(s)


def _truncate_guard() -> str:
    return """DO $do$
DECLARE t text;
BEGIN
  FOR t IN SELECT tablename FROM pg_catalog.pg_tables
           WHERE schemaname = 'public' AND tablename <> 'alembic_version' LOOP
    EXECUTE 'DROP TRIGGER IF EXISTS ' || quote_ident('no_truncate_' || t) || ' ON public.' || quote_ident(t);
    EXECUTE 'CREATE TRIGGER ' || quote_ident('no_truncate_' || t)
         || ' BEFORE TRUNCATE ON public.' || quote_ident(t)
         || ' FOR EACH STATEMENT EXECUTE FUNCTION ledger_internal.reject_truncate()';
  END LOOP;
END
$do$"""
