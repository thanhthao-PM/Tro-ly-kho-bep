"""0007: Disposals (Donation, Selloff, Waste)

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-07 10:30:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "disposals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("kitchen_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 3), nullable=False),
        sa.Column("occurred_on", sa.Date(), nullable=False),
        sa.Column("reason_code", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("counterparty_name", sa.Text(), nullable=True),
        sa.Column("revenue_vnd", sa.BigInteger(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["kitchen_id", "batch_id"],
            ["batches.kitchen_id", "batches.id"],
            ondelete="RESTRICT",
            name="fk_disposals_batch"
        ),
        sa.UniqueConstraint("kitchen_id", "id", name="uq_disposals_kitchen_id"),
        sa.CheckConstraint("type IN ('DONATION', 'SELLOFF', 'WASTE')", name="chk_disposals_type"),
        sa.CheckConstraint("quantity > 0", name="chk_disposals_quantity_positive"),
        sa.CheckConstraint("reason_code IS NULL OR reason_code IN ('EXPIRED', 'SPOILED', 'OVERSTOCK', 'OTHER')", name="chk_disposals_reason_code"),
        sa.CheckConstraint("(type = 'WASTE' AND reason_code IS NOT NULL) OR (type <> 'WASTE' AND reason_code IS NULL)", name="chk_disposals_waste_reason_required"),
        sa.CheckConstraint("(reason_code = 'OTHER' AND note IS NOT NULL) OR (reason_code <> 'OTHER')", name="chk_disposals_other_note_required"),
        sa.CheckConstraint("(type = 'SELLOFF' AND revenue_vnd IS NOT NULL) OR (type <> 'SELLOFF' AND revenue_vnd IS NULL)", name="chk_disposals_selloff_revenue_required"),
    )
    op.create_index("idx_disposals_occurred_on", "disposals", ["kitchen_id", "occurred_on"])
    op.create_index("idx_disposals_batch_id", "disposals", ["batch_id"])


def downgrade() -> None:
    op.drop_index("idx_disposals_batch_id", table_name="disposals")
    op.drop_index("idx_disposals_occurred_on", table_name="disposals")
    op.drop_table("disposals")
