"""
SQLAlchemy Models cho Lô hàng (Batches) và Sổ cái kho bất biến (StockMovements).
Tuân thủ nghiêm ngặt Architecture Revision 6.3.
"""
import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column, Text, Numeric, Date, DateTime, BigInteger,
    ForeignKey, CheckConstraint, UniqueConstraint, Index,
    ForeignKeyConstraint, text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class Batch(Base):
    __tablename__ = "batches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kitchen_id = Column(UUID(as_uuid=True), nullable=False)
    ingredient_id = Column(UUID(as_uuid=True), nullable=False)
    received_on = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=True)
    initial_qty = Column(Numeric(14, 3), nullable=False)
    remaining_qty = Column(Numeric(14, 3), nullable=False, server_default="0")
    unit_cost = Column(Numeric(18, 6), nullable=False)
    location = Column(Text, nullable=False)
    source_document_line_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)

    ingredient = relationship("Ingredient")

    __table_args__ = (
        ForeignKeyConstraint(
            ["kitchen_id", "ingredient_id"],
            ["ingredients.kitchen_id", "ingredients.id"],
            ondelete="RESTRICT",
            name="fk_batches_ingredient"
        ),
        UniqueConstraint("kitchen_id", "id", name="uq_batches_kitchen_id"),
        UniqueConstraint("kitchen_id", "ingredient_id", "id", name="uq_batches_kitchen_ingredient_id"),
        CheckConstraint("initial_qty > 0", name="chk_batches_initial_qty_positive"),
        CheckConstraint("remaining_qty >= 0", name="chk_batches_remaining_qty_non_negative"),
        CheckConstraint("unit_cost >= 0", name="chk_batches_unit_cost_non_negative"),
        CheckConstraint("location IN ('FRIDGE', 'FREEZER', 'PANTRY')", name="chk_batches_location"),
        CheckConstraint("expiry_date IS NULL OR expiry_date >= received_on", name="chk_batches_expiry_valid"),
        # Indexes phục vụ FEFO và tìm kiếm nhanh
        Index(
            "idx_batches_fefo",
            "kitchen_id", "ingredient_id", "expiry_date", "received_on", "id",
            postgresql_where=text("remaining_qty > 0")
        ),
        Index(
            "idx_batches_expiring",
            "kitchen_id", "expiry_date",
            postgresql_where=text("remaining_qty > 0")
        ),
        Index("idx_batches_received", "kitchen_id", "received_on"),
    )


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kitchen_id = Column(UUID(as_uuid=True), nullable=False)
    ingredient_id = Column(UUID(as_uuid=True), nullable=False)
    batch_id = Column(UUID(as_uuid=True), nullable=False)
    type = Column(Text, nullable=False)
    qty_delta = Column(Numeric(14, 3), nullable=False)
    unit_cost_snapshot = Column(Numeric(18, 6), nullable=False)
    value_vnd = Column(BigInteger, nullable=False)
    occurred_on = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=True)
    reason_code = Column(Text, nullable=True)
    note = Column(Text, nullable=True)
    sale_line_id = Column(UUID(as_uuid=True), nullable=True)
    disposal_id = Column(UUID(as_uuid=True), nullable=True)
    document_line_id = Column(UUID(as_uuid=True), nullable=True)
    shortage_id = Column(UUID(as_uuid=True), nullable=True)
    reverses_movement_id = Column(UUID(as_uuid=True), ForeignKey("stock_movements.id"), unique=True, nullable=True)

    batch = relationship("Batch")
    actor = relationship("UserProfile")

    __table_args__ = (
        ForeignKeyConstraint(
            ["kitchen_id", "ingredient_id", "batch_id"],
            ["batches.kitchen_id", "batches.ingredient_id", "batches.id"],
            ondelete="RESTRICT",
            name="fk_stock_movements_batch"
        ),
        CheckConstraint(
            "type IN ('RECEIPT', 'SALE_CONSUMPTION', 'USAGE_CONSUMPTION', 'DONATION', 'SELLOFF', 'WASTE', 'ADJUSTMENT_IN', 'ADJUSTMENT_OUT', 'REVERSAL')",
            name="chk_stock_movements_type"
        ),
        CheckConstraint("qty_delta <> 0", name="chk_stock_movements_qty_delta_nonzero"),
        CheckConstraint("value_vnd = 0 OR sign(value_vnd) = sign(qty_delta)", name="chk_stock_movements_sign_agreement"),
        CheckConstraint("abs(value_vnd - (qty_delta * unit_cost_snapshot)) < 1", name="chk_stock_movements_value_tolerance"),
        CheckConstraint(
            "(type IN ('RECEIPT', 'ADJUSTMENT_IN') AND qty_delta > 0) OR "
            "(type IN ('SALE_CONSUMPTION', 'USAGE_CONSUMPTION', 'DONATION', 'SELLOFF', 'WASTE', 'ADJUSTMENT_OUT') AND qty_delta < 0) OR "
            "(type = 'REVERSAL')",
            name="chk_stock_movements_type_direction"
        ),
        Index("idx_stock_movements_occurred", "kitchen_id", "occurred_on", "created_at"),
        Index("idx_stock_movements_batch", "batch_id"),
        Index("idx_stock_movements_ingredient", "kitchen_id", "ingredient_id", "occurred_on"),
        Index("idx_stock_movements_sale_line", "sale_line_id"),
        Index("idx_stock_movements_disposal", "disposal_id"),
        Index("idx_stock_movements_shortage", "shortage_id"),
    )
