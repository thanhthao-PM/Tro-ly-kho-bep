"""
SQLAlchemy Models cho Thông báo & Cảnh báo (NotificationReads).
Tuân thủ nghiêm ngặt Architecture Revision 6.3.
"""
from datetime import datetime
from sqlalchemy import Column, Text, DateTime, text
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class NotificationRead(Base):
    __tablename__ = "notification_reads"

    kitchen_id = Column(UUID(as_uuid=True), primary_key=True)
    notification_key = Column(Text, primary_key=True)
    read_at = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
