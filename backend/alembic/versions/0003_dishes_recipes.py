"""0003: Dishes and Recipe Items

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-07 10:10:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. dishes
    op.create_table(
        "dishes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("kitchen_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kitchens.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("normalized_name", sa.Text(), nullable=False),
        sa.Column("price_vnd", sa.BigInteger(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("kitchen_id", "id", name="uq_dishes_kitchen_id"),
        sa.CheckConstraint("price_vnd >= 0", name="chk_dishes_price_non_negative"),
    )
    op.create_index(
        "uq_dishes_normalized",
        "dishes",
        ["kitchen_id", "normalized_name"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL")
    )

    # 2. recipe_items
    op.create_table(
        "recipe_items",
        sa.Column("kitchen_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dish_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ingredient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity_base", sa.Numeric(14, 3), nullable=False),
        sa.PrimaryKeyConstraint("kitchen_id", "dish_id", "ingredient_id", name="pk_recipe_items"),
        sa.ForeignKeyConstraint(
            ["kitchen_id", "dish_id"],
            ["dishes.kitchen_id", "dishes.id"],
            ondelete="CASCADE",
            name="fk_recipe_items_dish"
        ),
        sa.ForeignKeyConstraint(
            ["kitchen_id", "ingredient_id"],
            ["ingredients.kitchen_id", "ingredients.id"],
            ondelete="RESTRICT",
            name="fk_recipe_items_ingredient"
        ),
        sa.CheckConstraint("quantity_base > 0", name="chk_recipe_items_qty_positive"),
    )
    op.create_index("idx_recipe_items_ingredient", "recipe_items", ["kitchen_id", "ingredient_id"])


def downgrade() -> None:
    op.drop_index("idx_recipe_items_ingredient", table_name="recipe_items")
    op.drop_table("recipe_items")
    op.drop_index("uq_dishes_normalized", table_name="dishes")
    op.drop_table("dishes")
