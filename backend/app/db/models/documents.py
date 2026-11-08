"""
SQLAlchemy Models cho Chứng từ (Documents, DocumentLines) và Khóa Idempotency.
Tuân thủ nghiêm ngặt Architecture Revision 6.3.
"""
import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column, Text, Integer, Numeric, Date, DateTime, BigInteger,
    Boolean, ForeignKey, CheckConstraint, UniqueConstraint, Index,
    ForeignKeyConstraint, and_, text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import foreign, relationship
from app.db.base import Base
from app.db.models.catalog import Ingredient
from app.db.models.menu import Dish


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kitchen_id = Column(UUID(as_uuid=True), ForeignKey("kitchens.id", ondelete="CASCADE"), nullable=False)
    kind = Column(Text, nullable=False)
    source_format = Column(Text, nullable=False)
    status = Column(Text, nullable=False, server_default="DRAFT")
    business_date = Column(Date, nullable=False)
    original_filename = Column(Text, nullable=True)
    file_sha256 = Column(Text, nullable=True)
    storage_key = Column(Text, nullable=True)
    ocr_status = Column(Text, nullable=False, server_default="NOT_APPLICABLE")
    created_by = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)

    lines = relationship("DocumentLine", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("kitchen_id", "id", name="uq_documents_kitchen_id"),
        CheckConstraint(
            "kind IN ('IMPORT_INVOICE', 'SALES_REPORT', 'USAGE_SLIP')",
            name="chk_documents_kind"
        ),
        CheckConstraint(
            "source_format IN ('CSV', 'XLSX', 'IMAGE', 'PDF', 'MANUAL')",
            name="chk_documents_source_format"
        ),
        CheckConstraint(
            "status IN ('DRAFT', 'CONFIRMED', 'CANCELLED')",
            name="chk_documents_status"
        ),
        CheckConstraint(
            "ocr_status IN ('NOT_APPLICABLE', 'PENDING', 'DONE', 'FAILED')",
            name="chk_documents_ocr_status"
        ),
        Index(
            "uq_documents_hash",
            "kitchen_id", "kind", "file_sha256",
            unique=True,
            postgresql_where=text("status <> 'CANCELLED' AND file_sha256 IS NOT NULL")
        ),
        Index("idx_documents_status", "kitchen_id", "status", "created_at"),
    )


class DocumentLine(Base):
    __tablename__ = "document_lines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kitchen_id = Column(UUID(as_uuid=True), nullable=False)
    document_id = Column(UUID(as_uuid=True), nullable=False)
    line_no = Column(Integer, nullable=False)
    raw_text = Column(Text, nullable=True)
    parsed_name = Column(Text, nullable=True)
    ingredient_id = Column(UUID(as_uuid=True), nullable=True)
    dish_id = Column(UUID(as_uuid=True), nullable=True)
    quantity = Column(Numeric(14, 3), nullable=True)
    unit_code = Column(Text, ForeignKey("units.code", ondelete="RESTRICT"), nullable=True)
    unit_price_vnd = Column(Numeric(18, 2), nullable=True)
    line_total_vnd = Column(BigInteger, nullable=True)
    expiry_date = Column(Date, nullable=True)
    confidence = Column(JSONB, nullable=True)
    flags = Column(ARRAY(Text), nullable=False, server_default="{}")
    is_selected = Column(Boolean, nullable=False, server_default="true")

    document = relationship("Document", back_populates="lines")
    ingredient = relationship(
        Ingredient,
        primaryjoin=lambda: and_(
            DocumentLine.kitchen_id == Ingredient.kitchen_id,
            foreign(DocumentLine.ingredient_id) == Ingredient.id
        ),
        viewonly=True
    )
    dish = relationship(
        Dish,
        primaryjoin=lambda: and_(
            DocumentLine.kitchen_id == Dish.kitchen_id,
            foreign(DocumentLine.dish_id) == Dish.id
        ),
        viewonly=True
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["kitchen_id", "document_id"],
            ["documents.kitchen_id", "documents.id"],
            ondelete="CASCADE",
            name="fk_document_lines_document"
        ),
        UniqueConstraint("kitchen_id", "id", name="uq_document_lines_kitchen_id"),
        UniqueConstraint("document_id", "line_no", name="uq_document_lines_document_line_no"),
        CheckConstraint(
            "NOT (ingredient_id IS NOT NULL AND dish_id IS NOT NULL)",
            name="chk_document_lines_not_both_targets"
        ),
    )


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    kitchen_id = Column(UUID(as_uuid=True), primary_key=True)
    endpoint = Column(Text, primary_key=True)
    key = Column(Text, primary_key=True)
    request_hash = Column(Text, nullable=False)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=True)
    status = Column(Text, nullable=False)
    response_status = Column(Integer, nullable=True)
    response_body = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('CLAIMED', 'COMPLETED')", name="chk_idempotency_status"),
        Index("idx_idempotency_created_at", "created_at"),
    )
