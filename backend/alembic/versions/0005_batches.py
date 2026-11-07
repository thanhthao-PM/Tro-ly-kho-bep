"""0005: Inventory Batches

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-07 10:20:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("kitchen_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ingredient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("received_on", sa.Date(), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("initial_qty", sa.Numeric(14, 3), nullable=False),
        sa.Column("remaining_qty", sa.Numeric(14, 3), server_default="0", nullable=False),
        sa.Column("unit_cost", sa.Numeric(18, 6), nullable=False),
        sa.Column("location", sa.Text(), nullable=False),
        sa.Column("source_document_line_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["kitchen_id", "ingredient_id"],
            ["ingredients.kitchen_id", "ingredients.id"],
            ondelete="RESTRICT",
            name="fk_batches_ingredient"
        ),
        sa.UniqueConstraint("kitchen_id", "id", name="uq_batches_kitchen_id"),
        sa.UniqueConstraint("kitchen_id", "ingredient_id", "id", name="uq_batches_kitchen_ingredient_id"),
        sa.CheckConstraint("initial_qty > 0", name="chk_batches_initial_qty_positive"),
        sa.CheckConstraint("remaining_qty >= 0", name="chk_batches_remaining_qty_non_negative"),
        sa.CheckConstraint("unit_cost >= 0", name="chk_batches_unit_cost_non_negative"),
        sa.CheckConstraint("location IN ('FRIDGE', 'FREEZER', 'PANTRY')", name="chk_batches_location"),
        sa.CheckConstraint("expiry_date IS NULL OR expiry_date >= received_on", name="chk_batches_expiry_valid"),
    )
    op.create_index(
        "idx_batches_fefo",
        "batches",
        ["kitchen_id", "ingredient_id", "expiry_date", "received_on", "id"],
        postgresql_where=sa.text("remaining_qty > 0")
    )
    op.create_index(
        "idx_batches_expiring",
        "batches",
        ["kitchen_id", "expiry_date"],
        postgresql_where=sa.text("remaining_qty > 0")
    )
    op.create_index("idx_batches_received", "batches", ["kitchen_id", "received_on"])


def downgrade() -> None:
    op.drop_index("idx_batches_received", table_name="batches")
    op.drop_index("idx_batches_expiring", table_name="batches")
    op.drop_index("idx_batches_fefo", table_name="batches")
    op.drop_table("batches")
