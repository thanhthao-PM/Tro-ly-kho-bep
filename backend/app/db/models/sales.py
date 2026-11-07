"""
SQLAlchemy Models cho Bán hàng (Sales, SaleLines) và Thiếu hụt kho Option C (StockShortages).
Tuân thủ nghiêm ngặt Architecture Revision 6.3.
"""
import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column, Text, Integer, Numeric, Date, DateTime, BigInteger,
    ForeignKey, CheckConstraint, UniqueConstraint, Index,
    ForeignKeyConstraint, text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class Sale(Base):
    __tablename__ = "sales"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kitchen_id = Column(UUID(as_uuid=True), ForeignKey("kitchens.id", ondelete="CASCADE"), nullable=False)
    business_date = Column(Date, nullable=False)
    source_document_id = Column(UUID(as_uuid=True), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)

    lines = relationship("SaleLine", back_populates="sale", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("kitchen_id", "id", name="uq_sales_kitchen_id"),
        Index("idx_sales_business_date", "kitchen_id", "business_date"),
        Index("uq_sales_source_doc", "source_document_id", unique=True, postgresql_where=text("source_document_id IS NOT NULL")),
    )


class SaleLine(Base):
    __tablename__ = "sale_lines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kitchen_id = Column(UUID(as_uuid=True), nullable=False)
    sale_id = Column(UUID(as_uuid=True), nullable=False)
    dish_id = Column(UUID(as_uuid=True), nullable=False)
    dish_name_snapshot = Column(Text, nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price_snapshot_vnd = Column(BigInteger, nullable=False)
    revenue_vnd = Column(BigInteger, nullable=False)
    cogs_vnd = Column(BigInteger, nullable=False, server_default="0")
    consumption_status = Column(Text, nullable=False, server_default="FULL")
    origin = Column(Text, nullable=False, server_default="NORMAL")
    source_batch_id = Column(UUID(as_uuid=True), nullable=True)

    sale = relationship("Sale", back_populates="lines")
    dish = relationship("Dish")
    shortages = relationship("StockShortage", back_populates="sale_line", cascade="all, delete-orphan")

    __table_args__ = (
        ForeignKeyConstraint(
            ["kitchen_id", "sale_id"],
            ["sales.kitchen_id", "sales.id"],
            ondelete="CASCADE",
            name="fk_sale_lines_sale"
        ),
        ForeignKeyConstraint(
            ["kitchen_id", "dish_id"],
            ["dishes.kitchen_id", "dishes.id"],
            ondelete="RESTRICT",
            name="fk_sale_lines_dish"
        ),
        UniqueConstraint("kitchen_id", "id", name="uq_sale_lines_kitchen_id"),
        CheckConstraint("quantity > 0", name="chk_sale_lines_qty_positive"),
        CheckConstraint("cogs_vnd >= 0", name="chk_sale_lines_cogs_non_negative"),
        CheckConstraint(
            "consumption_status IN ('FULL', 'PARTIAL', 'RESOLVED')",
            name="chk_sale_lines_consumption_status"
        ),
        CheckConstraint(
            "origin IN ('NORMAL', 'REPURPOSE')",
            name="chk_sale_lines_origin"
        ),
        CheckConstraint(
            "(origin = 'REPURPOSE' AND source_batch_id IS NOT NULL) OR "
            "(origin = 'NORMAL' AND source_batch_id IS NULL)",
            name="chk_sale_lines_repurpose_source_batch"
        ),
        Index("idx_sale_lines_sale", "kitchen_id", "sale_id"),
        Index("idx_sale_lines_dish", "kitchen_id", "dish_id"),
    )


class StockShortage(Base):
    __tablename__ = "stock_shortages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kitchen_id = Column(UUID(as_uuid=True), nullable=False)
    sale_line_id = Column(UUID(as_uuid=True), nullable=True)
    document_line_id = Column(UUID(as_uuid=True), nullable=True)
    ingredient_id = Column(UUID(as_uuid=True), nullable=False)
    short_qty = Column(Numeric(14, 3), nullable=False)
    status = Column(Text, nullable=False, server_default="OPEN")
    resolution = Column(Text, nullable=True)
    estimated_unit_cost = Column(Numeric(18, 6), nullable=True)
    estimated_cost_vnd = Column(BigInteger, nullable=True)
    estimate_batch_id = Column(UUID(as_uuid=True), nullable=True)
    resolution_note = Column(Text, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=True)

    sale_line = relationship("SaleLine", back_populates="shortages")
    ingredient = relationship("Ingredient")

    __table_args__ = (
        ForeignKeyConstraint(
            ["kitchen_id", "sale_line_id"],
            ["sale_lines.kitchen_id", "sale_lines.id"],
            ondelete="CASCADE",
            name="fk_stock_shortages_sale_line"
        ),
        ForeignKeyConstraint(
            ["kitchen_id", "ingredient_id"],
            ["ingredients.kitchen_id", "ingredients.id"],
            ondelete="RESTRICT",
            name="fk_stock_shortages_ingredient"
        ),
        UniqueConstraint("kitchen_id", "id", name="uq_stock_shortages_kitchen_id"),
        CheckConstraint("short_qty > 0", name="chk_stock_shortages_qty_positive"),
        CheckConstraint(
            "status IN ('OPEN', 'RESOLVED')",
            name="chk_stock_shortages_status"
        ),
        CheckConstraint(
            "resolution IS NULL OR resolution IN ('CONSUMED_FROM_STOCK', 'WRITTEN_OFF_ESTIMATED', 'WAIVED')",
            name="chk_stock_shortages_resolution"
        ),
        CheckConstraint(
            "(sale_line_id IS NOT NULL AND document_line_id IS NULL) OR "
            "(sale_line_id IS NULL AND document_line_id IS NOT NULL)",
            name="chk_stock_shortages_exactly_one_parent"
        ),
        CheckConstraint(
            "(status = 'RESOLVED' AND resolution IS NOT NULL AND resolved_at IS NOT NULL) OR "
            "(status = 'OPEN' AND resolution IS NULL AND resolved_at IS NULL)",
            name="chk_stock_shortages_resolution_consistency"
        ),
        CheckConstraint(
            "(resolution = 'WAIVED' AND resolution_note IS NOT NULL) OR (resolution <> 'WAIVED')",
            name="chk_stock_shortages_waived_note_required"
        ),
        CheckConstraint(
            "(resolution = 'WRITTEN_OFF_ESTIMATED' AND estimated_cost_vnd IS NOT NULL) OR (resolution <> 'WRITTEN_OFF_ESTIMATED')",
            name="chk_stock_shortages_written_off_cost_required"
        ),
        CheckConstraint(
            "(resolution = 'CONSUMED_FROM_STOCK' AND estimated_cost_vnd IS NULL AND estimated_unit_cost IS NULL) OR (resolution <> 'CONSUMED_FROM_STOCK')",
            name="chk_stock_shortages_consumed_cost_null"
        ),
        Index("idx_stock_shortages_open", "kitchen_id", postgresql_where=text("status = 'OPEN'")),
        Index("idx_stock_shortages_sale_line", "sale_line_id"),
        Index("idx_stock_shortages_document_line", "document_line_id"),
    )
