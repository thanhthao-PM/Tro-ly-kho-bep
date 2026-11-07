"""
SQLAlchemy Models cho Thực đơn (Dishes) và Công thức định lượng (RecipeItems).
Tuân thủ nghiêm ngặt Architecture Revision 6.3.
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, Text, BigInteger, Numeric, DateTime,
    ForeignKey, CheckConstraint, UniqueConstraint, Index,
    ForeignKeyConstraint, text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class Dish(Base):
    __tablename__ = "dishes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kitchen_id = Column(UUID(as_uuid=True), ForeignKey("kitchens.id", ondelete="CASCADE"), nullable=False)
    name = Column(Text, nullable=False)
    normalized_name = Column(Text, nullable=False)
    price_vnd = Column(BigInteger, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)

    recipe_items = relationship("RecipeItem", back_populates="dish", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("kitchen_id", "id", name="uq_dishes_kitchen_id"),
        CheckConstraint("price_vnd >= 0", name="chk_dishes_price_non_negative"),
        Index("uq_dishes_normalized", "kitchen_id", "normalized_name", unique=True, postgresql_where=text("deleted_at IS NULL")),
    )


class RecipeItem(Base):
    __tablename__ = "recipe_items"

    kitchen_id = Column(UUID(as_uuid=True), primary_key=True)
    dish_id = Column(UUID(as_uuid=True), primary_key=True)
    ingredient_id = Column(UUID(as_uuid=True), primary_key=True)
    quantity_base = Column(Numeric(14, 3), nullable=False)

    dish = relationship("Dish", back_populates="recipe_items")
    ingredient = relationship("Ingredient")

    __table_args__ = (
        ForeignKeyConstraint(
            ["kitchen_id", "dish_id"],
            ["dishes.kitchen_id", "dishes.id"],
            ondelete="CASCADE",
            name="fk_recipe_items_dish"
        ),
        ForeignKeyConstraint(
            ["kitchen_id", "ingredient_id"],
            ["ingredients.kitchen_id", "ingredients.id"],
            ondelete="RESTRICT",
            name="fk_recipe_items_ingredient"
        ),
        CheckConstraint("quantity_base > 0", name="chk_recipe_items_qty_positive"),
        Index("idx_recipe_items_ingredient", "kitchen_id", "ingredient_id"),
    )
