"""0009: Notifications and Audit Log

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-07 10:40:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. notification_reads
    op.create_table(
        "notification_reads",
        sa.Column("kitchen_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("notification_key", sa.Text(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("kitchen_id", "notification_key", name="pk_notification_reads"),
    )

    # 2. audit_log
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("kitchen_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("before", postgresql.JSONB(), nullable=True),
        sa.Column("after", postgresql.JSONB(), nullable=True),
        sa.Column("request_id", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_audit_log_created_at", "audit_log", ["kitchen_id", "created_at"])
    op.create_index("idx_audit_log_entity", "audit_log", ["entity_type", "entity_id"])

    # 3. Trigger cấm update hoặc delete trên audit_log
    op.execute("""
    CREATE OR REPLACE FUNCTION ledger_internal.trg_block_audit_mutation()
    RETURNS TRIGGER AS $$
    BEGIN
        RAISE EXCEPTION 'Table audit_log is append-only.';
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("""
    CREATE TRIGGER trg_audit_log_immutable
    BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH STATEMENT
    EXECUTE FUNCTION ledger_internal.trg_block_audit_mutation();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_audit_log_immutable ON audit_log;")
    op.execute("DROP FUNCTION IF EXISTS ledger_internal.trg_block_audit_mutation();")
    op.drop_index("idx_audit_log_entity", table_name="audit_log")
    op.drop_index("idx_audit_log_created_at", table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_table("notification_reads")
