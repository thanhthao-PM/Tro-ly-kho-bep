"""
SQLAlchemy Models cho Xử lý hàng cận date & Quá hạn (Disposals).
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


class Disposal(Base):
    __tablename__ = "disposals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kitchen_id = Column(UUID(as_uuid=True), nullable=False)
    batch_id = Column(UUID(as_uuid=True), nullable=False)
    type = Column(Text, nullable=False)
    quantity = Column(Numeric(14, 3), nullable=False)
    occurred_on = Column(Date, nullable=False)
    reason_code = Column(Text, nullable=True)
    note = Column(Text, nullable=True)
    counterparty_name = Column(Text, nullable=True)
    revenue_vnd = Column(BigInteger, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)

    batch = relationship("Batch")

    __table_args__ = (
        ForeignKeyConstraint(
            ["kitchen_id", "batch_id"],
            ["batches.kitchen_id", "batches.id"],
            ondelete="RESTRICT",
            name="fk_disposals_batch"
        ),
        UniqueConstraint("kitchen_id", "id", name="uq_disposals_kitchen_id"),
        CheckConstraint(
            "type IN ('DONATION', 'SELLOFF', 'WASTE')",
            name="chk_disposals_type"
        ),
        CheckConstraint("quantity > 0", name="chk_disposals_quantity_positive"),
        CheckConstraint(
            "reason_code IS NULL OR reason_code IN ('EXPIRED', 'SPOILED', 'OVERSTOCK', 'OTHER')",
            name="chk_disposals_reason_code"
        ),
        CheckConstraint(
            "(type = 'WASTE' AND reason_code IS NOT NULL) OR (type <> 'WASTE' AND reason_code IS NULL)",
            name="chk_disposals_waste_reason_required"
        ),
        CheckConstraint(
            "(reason_code = 'OTHER' AND note IS NOT NULL) OR (reason_code <> 'OTHER')",
            name="chk_disposals_other_note_required"
        ),
        CheckConstraint(
            "(type = 'SELLOFF' AND revenue_vnd IS NOT NULL) OR (type <> 'SELLOFF' AND revenue_vnd IS NULL)",
            name="chk_disposals_selloff_revenue_required"
        ),
        Index("idx_disposals_occurred_on", "kitchen_id", "occurred_on"),
        Index("idx_disposals_batch_id", "batch_id"),
    )
