"""
SQLAlchemy Models cho Danh mục nguyên liệu, Đơn vị tính và Quy đổi đơn vị.
Tuân thủ Architecture Revision 6.3.
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Boolean, SmallInteger,
    Numeric, DateTime, ForeignKey, CheckConstraint,
    UniqueConstraint, Index, text, ForeignKeyConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class Unit(Base):
    __tablename__ = "units"

    code = Column(Text, primary_key=True)
    label_vi = Column(Text, nullable=False)
    dimension = Column(Text, nullable=False)
    factor_to_dimension_base = Column(Numeric(18, 6), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "dimension IN ('MASS', 'VOLUME', 'COUNT')",
            name="chk_units_dimension"
        ),
        CheckConstraint(
            "(dimension IN ('MASS', 'VOLUME') AND factor_to_dimension_base > 0) "
            "OR (dimension = 'COUNT' AND factor_to_dimension_base IS NULL)",
            name="chk_units_factor_dimension"
        ),
    )


class Ingredient(Base):
    __tablename__ = "ingredients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kitchen_id = Column(UUID(as_uuid=True), ForeignKey("kitchens.id", ondelete="CASCADE"), nullable=False)
    name = Column(Text, nullable=False)
    normalized_name = Column(Text, nullable=False)
    search_name = Column(Text, nullable=False)
    base_unit_code = Column(Text, ForeignKey("units.code", ondelete="RESTRICT"), nullable=False)
    default_location = Column(Text, nullable=False)
    tracks_expiry = Column(Boolean, nullable=False, server_default="true")
    min_stock_qty = Column(Numeric(14, 3), nullable=False, server_default="0")
    order_step = Column(Numeric(14, 3), nullable=True)
    expiry_warning_days = Column(SmallInteger, nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=text("now()"), onupdate=datetime.utcnow, nullable=False)

    base_unit = relationship("Unit")
    aliases = relationship("IngredientAlias", back_populates="ingredient", cascade="all, delete-orphan")
    conversions = relationship("IngredientUnitConversion", back_populates="ingredient", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("kitchen_id", "id", name="uq_ingredients_kitchen_id"),
        UniqueConstraint("kitchen_id", "id", "base_unit_code", name="uq_ingredients_kitchen_id_base_unit"),
        CheckConstraint("default_location IN ('FRIDGE', 'FREEZER', 'PANTRY')", name="chk_ingredients_location"),
        CheckConstraint("min_stock_qty >= 0", name="chk_ingredients_min_stock"),
        CheckConstraint("order_step IS NULL OR order_step > 0", name="chk_ingredients_order_step"),
        CheckConstraint("expiry_warning_days IS NULL OR (expiry_warning_days >= 0 AND expiry_warning_days <= 30)", name="chk_ingredients_expiry_warning"),
        Index("uq_ingredients_normalized", "kitchen_id", "normalized_name", unique=True, postgresql_where=text("deleted_at IS NULL")),
    )


class IngredientAlias(Base):
    __tablename__ = "ingredient_aliases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kitchen_id = Column(UUID(as_uuid=True), nullable=False)
    ingredient_id = Column(UUID(as_uuid=True), nullable=False)
    alias = Column(Text, nullable=False)
    normalized_alias = Column(Text, nullable=False)

    ingredient = relationship("Ingredient", back_populates="aliases")

    __table_args__ = (
        ForeignKeyConstraint(
            ["kitchen_id", "ingredient_id"],
            ["ingredients.kitchen_id", "ingredients.id"],
            ondelete="CASCADE",
            name="fk_ingredient_aliases_ingredient"
        ),
        UniqueConstraint("kitchen_id", "normalized_alias", name="uq_ingredient_aliases_normalized"),
    )


class IngredientUnitConversion(Base):
    __tablename__ = "ingredient_unit_conversions"

    kitchen_id = Column(UUID(as_uuid=True), primary_key=True)
    ingredient_id = Column(UUID(as_uuid=True), primary_key=True)
    unit_code = Column(Text, ForeignKey("units.code", ondelete="RESTRICT"), primary_key=True)
    base_unit_code = Column(Text, nullable=False)
    factor_to_base = Column(Numeric(18, 6), nullable=False)

    ingredient = relationship("Ingredient", back_populates="conversions")
    unit = relationship("Unit")

    __table_args__ = (
        ForeignKeyConstraint(
            ["kitchen_id", "ingredient_id", "base_unit_code"],
            ["ingredients.kitchen_id", "ingredients.id", "ingredients.base_unit_code"],
            ondelete="CASCADE",
            name="fk_ingredient_unit_conversions_ingredient"
        ),
        CheckConstraint("factor_to_base > 0", name="chk_unit_conversions_factor_positive"),
        CheckConstraint("unit_code <> base_unit_code", name="chk_unit_conversions_different_unit"),
    )
