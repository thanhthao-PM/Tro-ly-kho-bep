"""0001: Initial Core and Kitchen Settings

Revision ID: 0001
Revises: 
Create Date: 2026-11-07 10:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. user_profiles
    op.create_table(
        "user_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # 2. kitchens
    op.create_table(
        "kitchens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_profiles.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("timezone", sa.Text(), server_default="Asia/Ho_Chi_Minh", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # 3. kitchen_settings
    op.create_table(
        "kitchen_settings",
        sa.Column("kitchen_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kitchens.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("expiry_warning_days", sa.SmallInteger(), server_default="3", nullable=False),
        sa.Column("target_coverage_days", sa.SmallInteger(), server_default="3", nullable=False),
        sa.Column("consumption_window_days", sa.SmallInteger(), server_default="14", nullable=False),
        sa.Column("min_history_days", sa.SmallInteger(), server_default="7", nullable=False),
        sa.Column("unusual_quantity_ratio", sa.Numeric(6, 2), server_default="2.0", nullable=False),
        sa.Column("backdate_limit_days", sa.SmallInteger(), server_default="2", nullable=False),
        sa.Column("expired_batches_consumable", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("expired_batch_actions", postgresql.ARRAY(sa.Text()), server_default="{'WASTE'}", nullable=False),
        sa.CheckConstraint("expiry_warning_days >= 0 AND expiry_warning_days <= 30", name="chk_kitchen_settings_expiry_warning"),
        sa.CheckConstraint("target_coverage_days >= 1 AND target_coverage_days <= 60", name="chk_kitchen_settings_target_coverage"),
        sa.CheckConstraint("consumption_window_days >= 7 AND consumption_window_days <= 90", name="chk_kitchen_settings_consumption_window"),
        sa.CheckConstraint("min_history_days >= 1 AND min_history_days <= consumption_window_days", name="chk_kitchen_settings_min_history"),
        sa.CheckConstraint("'WASTE' = ANY(expired_batch_actions)", name="chk_kitchen_settings_waste_required"),
    )


def downgrade() -> None:
    op.drop_table("kitchen_settings")
    op.drop_table("kitchens")
    op.drop_table("user_profiles")
