"""0006: Sales, Sale Lines, and Stock Shortages (Option C)

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-07 10:25:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. sales
    op.create_table(
        "sales",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("kitchen_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kitchens.id", ondelete="CASCADE"), nullable=False),
        sa.Column("business_date", sa.Date(), nullable=False),
        sa.Column("source_document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("kitchen_id", "id", name="uq_sales_kitchen_id"),
    )
    op.create_index("idx_sales_business_date", "sales", ["kitchen_id", "business_date"])
    op.create_index("uq_sales_source_doc", "sales", ["source_document_id"], unique=True, postgresql_where=sa.text("source_document_id IS NOT NULL"))

    # 2. sale_lines
    op.create_table(
        "sale_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("kitchen_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sale_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dish_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dish_name_snapshot", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price_snapshot_vnd", sa.BigInteger(), nullable=False),
        sa.Column("revenue_vnd", sa.BigInteger(), nullable=False),
        sa.Column("cogs_vnd", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("consumption_status", sa.Text(), server_default="FULL", nullable=False),
        sa.Column("origin", sa.Text(), server_default="NORMAL", nullable=False),
        sa.Column("source_batch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["kitchen_id", "sale_id"],
            ["sales.kitchen_id", "sales.id"],
            ondelete="CASCADE",
            name="fk_sale_lines_sale"
        ),
        sa.ForeignKeyConstraint(
            ["kitchen_id", "dish_id"],
            ["dishes.kitchen_id", "dishes.id"],
            ondelete="RESTRICT",
            name="fk_sale_lines_dish"
        ),
        sa.UniqueConstraint("kitchen_id", "id", name="uq_sale_lines_kitchen_id"),
        sa.CheckConstraint("quantity > 0", name="chk_sale_lines_qty_positive"),
        sa.CheckConstraint("cogs_vnd >= 0", name="chk_sale_lines_cogs_non_negative"),
        sa.CheckConstraint("consumption_status IN ('FULL', 'PARTIAL', 'RESOLVED')", name="chk_sale_lines_consumption_status"),
        sa.CheckConstraint("origin IN ('NORMAL', 'REPURPOSE')", name="chk_sale_lines_origin"),
        sa.CheckConstraint(
            "(origin = 'REPURPOSE' AND source_batch_id IS NOT NULL) OR (origin = 'NORMAL' AND source_batch_id IS NULL)",
            name="chk_sale_lines_repurpose_source_batch"
        ),
    )
    op.create_index("idx_sale_lines_sale", "sale_lines", ["kitchen_id", "sale_id"])
    op.create_index("idx_sale_lines_dish", "sale_lines", ["kitchen_id", "dish_id"])

    # 3. stock_shortages
    op.create_table(
        "stock_shortages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("kitchen_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sale_line_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("document_line_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ingredient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("short_qty", sa.Numeric(14, 3), nullable=False),
        sa.Column("status", sa.Text(), server_default="OPEN", nullable=False),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("estimated_unit_cost", sa.Numeric(18, 6), nullable=True),
        sa.Column("estimated_cost_vnd", sa.BigInteger(), nullable=True),
        sa.Column("estimate_batch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=True),
        sa.ForeignKeyConstraint(
            ["kitchen_id", "sale_line_id"],
            ["sale_lines.kitchen_id", "sale_lines.id"],
            ondelete="CASCADE",
            name="fk_stock_shortages_sale_line"
        ),
        sa.ForeignKeyConstraint(
            ["kitchen_id", "ingredient_id"],
            ["ingredients.kitchen_id", "ingredients.id"],
            ondelete="RESTRICT",
            name="fk_stock_shortages_ingredient"
        ),
        sa.UniqueConstraint("kitchen_id", "id", name="uq_stock_shortages_kitchen_id"),
        sa.CheckConstraint("short_qty > 0", name="chk_stock_shortages_qty_positive"),
        sa.CheckConstraint("status IN ('OPEN', 'RESOLVED')", name="chk_stock_shortages_status"),
        sa.CheckConstraint("resolution IS NULL OR resolution IN ('CONSUMED_FROM_STOCK', 'WRITTEN_OFF_ESTIMATED', 'WAIVED')", name="chk_stock_shortages_resolution"),
        sa.CheckConstraint(
            "(sale_line_id IS NOT NULL AND document_line_id IS NULL) OR (sale_line_id IS NULL AND document_line_id IS NOT NULL)",
            name="chk_stock_shortages_exactly_one_parent"
        ),
        sa.CheckConstraint(
            "(status = 'RESOLVED' AND resolution IS NOT NULL AND resolved_at IS NOT NULL) OR (status = 'OPEN' AND resolution IS NULL AND resolved_at IS NULL)",
            name="chk_stock_shortages_resolution_consistency"
        ),
        sa.CheckConstraint(
            "(resolution = 'WAIVED' AND resolution_note IS NOT NULL) OR (resolution <> 'WAIVED')",
            name="chk_stock_shortages_waived_note_required"
        ),
        sa.CheckConstraint(
            "(resolution = 'WRITTEN_OFF_ESTIMATED' AND estimated_cost_vnd IS NOT NULL) OR (resolution <> 'WRITTEN_OFF_ESTIMATED')",
            name="chk_stock_shortages_written_off_cost_required"
        ),
        sa.CheckConstraint(
            "(resolution = 'CONSUMED_FROM_STOCK' AND estimated_cost_vnd IS NULL AND estimated_unit_cost IS NULL) OR (resolution <> 'CONSUMED_FROM_STOCK')",
            name="chk_stock_shortages_consumed_cost_null"
        ),
    )
    op.create_index("idx_stock_shortages_open", "stock_shortages", ["kitchen_id"], postgresql_where=sa.text("status = 'OPEN'"))
    op.create_index("idx_stock_shortages_sale_line", "stock_shortages", ["sale_line_id"])
    op.create_index("idx_stock_shortages_document_line", "stock_shortages", ["document_line_id"])


def downgrade() -> None:
    op.drop_index("idx_stock_shortages_document_line", table_name="stock_shortages")
    op.drop_index("idx_stock_shortages_sale_line", table_name="stock_shortages")
    op.drop_index("idx_stock_shortages_open", table_name="stock_shortages")
    op.drop_table("stock_shortages")
    op.drop_index("idx_sale_lines_dish", table_name="sale_lines")
    op.drop_index("idx_sale_lines_sale", table_name="sale_lines")
    op.drop_table("sale_lines")
    op.drop_index("uq_sales_source_doc", table_name="sales")
    op.drop_index("idx_sales_business_date", table_name="sales")
    op.drop_table("sales")
