"""
SQLAlchemy Models cho Nhật ký kiểm toán (AuditLog).
Tuân thủ nghiêm ngặt Architecture Revision 6.3.
"""
from datetime import datetime
from sqlalchemy import Column, Text, BigInteger, DateTime, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    kitchen_id = Column(UUID(as_uuid=True), nullable=False)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=True)
    action = Column(Text, nullable=False)
    entity_type = Column(Text, nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    before = Column(JSONB, nullable=True)
    after = Column(JSONB, nullable=True)
    request_id = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)

    __table_args__ = (
        Index("idx_audit_log_created_at", "kitchen_id", "created_at"),
        Index("idx_audit_log_entity", "entity_type", "entity_id"),
    )
