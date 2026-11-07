"""0002: Catalog Units, Ingredients, Aliases, and Conversions

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-07 10:05:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. units
    units_table = op.create_table(
        "units",
        sa.Column("code", sa.Text(), primary_key=True),
        sa.Column("label_vi", sa.Text(), nullable=False),
        sa.Column("dimension", sa.Text(), nullable=False),
        sa.Column("factor_to_dimension_base", sa.Numeric(18, 6), nullable=True),
        sa.CheckConstraint("dimension IN ('MASS', 'VOLUME', 'COUNT')", name="chk_units_dimension"),
        sa.CheckConstraint(
            "(dimension IN ('MASS', 'VOLUME') AND factor_to_dimension_base > 0) OR "
            "(dimension = 'COUNT' AND factor_to_dimension_base IS NULL)",
            name="chk_units_factor_dimension"
        ),
    )

    # Seed chuẩn cho units
    op.bulk_insert(
        units_table,
        [
            {"code": "g", "label_vi": "gam", "dimension": "MASS", "factor_to_dimension_base": 1.0},
            {"code": "kg", "label_vi": "kilogam", "dimension": "MASS", "factor_to_dimension_base": 1000.0},
            {"code": "ml", "label_vi": "mililít", "dimension": "VOLUME", "factor_to_dimension_base": 1.0},
            {"code": "l", "label_vi": "lít", "dimension": "VOLUME", "factor_to_dimension_base": 1000.0},
            {"code": "quả", "label_vi": "quả", "dimension": "COUNT", "factor_to_dimension_base": None},
            {"code": "hộp", "label_vi": "hộp", "dimension": "COUNT", "factor_to_dimension_base": None},
            {"code": "bó", "label_vi": "bó", "dimension": "COUNT", "factor_to_dimension_base": None},
            {"code": "củ", "label_vi": "củ", "dimension": "COUNT", "factor_to_dimension_base": None},
            {"code": "bìa", "label_vi": "bìa", "dimension": "COUNT", "factor_to_dimension_base": None},
            {"code": "gói", "label_vi": "gói", "dimension": "COUNT", "factor_to_dimension_base": None},
            {"code": "chai", "label_vi": "chai", "dimension": "COUNT", "factor_to_dimension_base": None},
        ]
    )

    # 2. ingredients
    op.create_table(
        "ingredients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("kitchen_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kitchens.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("normalized_name", sa.Text(), nullable=False),
        sa.Column("search_name", sa.Text(), nullable=False),
        sa.Column("base_unit_code", sa.Text(), sa.ForeignKey("units.code", ondelete="RESTRICT"), nullable=False),
        sa.Column("default_location", sa.Text(), nullable=False),
        sa.Column("tracks_expiry", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("min_stock_qty", sa.Numeric(14, 3), server_default="0", nullable=False),
        sa.Column("order_step", sa.Numeric(14, 3), nullable=True),
        sa.Column("expiry_warning_days", sa.SmallInteger(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("kitchen_id", "id", name="uq_ingredients_kitchen_id"),
        sa.UniqueConstraint("kitchen_id", "id", "base_unit_code", name="uq_ingredients_kitchen_id_base_unit"),
        sa.CheckConstraint("default_location IN ('FRIDGE', 'FREEZER', 'PANTRY')", name="chk_ingredients_location"),
        sa.CheckConstraint("min_stock_qty >= 0", name="chk_ingredients_min_stock"),
        sa.CheckConstraint("order_step IS NULL OR order_step > 0", name="chk_ingredients_order_step"),
        sa.CheckConstraint("expiry_warning_days IS NULL OR (expiry_warning_days >= 0 AND expiry_warning_days <= 30)", name="chk_ingredients_expiry_warning"),
    )
    op.create_index(
        "uq_ingredients_normalized",
        "ingredients",
        ["kitchen_id", "normalized_name"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL")
    )

    # 3. ingredient_aliases
    op.create_table(
        "ingredient_aliases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("kitchen_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ingredient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alias", sa.Text(), nullable=False),
        sa.Column("normalized_alias", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["kitchen_id", "ingredient_id"],
            ["ingredients.kitchen_id", "ingredients.id"],
            ondelete="CASCADE",
            name="fk_ingredient_aliases_ingredient"
        ),
        sa.UniqueConstraint("kitchen_id", "normalized_alias", name="uq_ingredient_aliases_normalized"),
    )

    # 4. ingredient_unit_conversions
    op.create_table(
        "ingredient_unit_conversions",
        sa.Column("kitchen_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ingredient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("unit_code", sa.Text(), sa.ForeignKey("units.code", ondelete="RESTRICT"), nullable=False),
        sa.Column("base_unit_code", sa.Text(), nullable=False),
        sa.Column("factor_to_base", sa.Numeric(18, 6), nullable=False),
        sa.PrimaryKeyConstraint("kitchen_id", "ingredient_id", "unit_code", name="pk_ingredient_unit_conversions"),
        sa.ForeignKeyConstraint(
            ["kitchen_id", "ingredient_id", "base_unit_code"],
            ["ingredients.kitchen_id", "ingredients.id", "ingredients.base_unit_code"],
            ondelete="CASCADE",
            name="fk_ingredient_unit_conversions_ingredient"
        ),
        sa.CheckConstraint("factor_to_base > 0", name="chk_unit_conversions_factor_positive"),
        sa.CheckConstraint("unit_code <> base_unit_code", name="chk_unit_conversions_different_unit"),
    )


def downgrade() -> None:
    op.drop_table("ingredient_unit_conversions")
    op.drop_table("ingredient_aliases")
    op.drop_index("uq_ingredients_normalized", table_name="ingredients")
    op.drop_table("ingredients")
    op.drop_table("units")
