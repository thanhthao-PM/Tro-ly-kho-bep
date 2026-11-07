"""
SQLAlchemy Models cho Tài khoản, Bếp và Cài đặt tham số bếp.
Tuân thủ Architecture Revision 6.3.
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Boolean, Integer, SmallInteger,
    Numeric, DateTime, ForeignKey, CheckConstraint, text
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from app.db.base import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    display_name = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)

    kitchen = relationship("Kitchen", back_populates="owner", uselist=False)


class Kitchen(Base):
    __tablename__ = "kitchens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("user_profiles.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True
    )
    name = Column(Text, nullable=False)
    timezone = Column(Text, nullable=False, server_default="Asia/Ho_Chi_Minh")
    created_at = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)

    owner = relationship("UserProfile", back_populates="kitchen")
    settings = relationship("KitchenSettings", back_populates="kitchen", uselist=False)


class KitchenSettings(Base):
    __tablename__ = "kitchen_settings"

    kitchen_id = Column(
        UUID(as_uuid=True),
        ForeignKey("kitchens.id", ondelete="CASCADE"),
        primary_key=True
    )
    expiry_warning_days = Column(SmallInteger, nullable=False, server_default="3")
    target_coverage_days = Column(SmallInteger, nullable=False, server_default="3")
    consumption_window_days = Column(SmallInteger, nullable=False, server_default="14")
    min_history_days = Column(SmallInteger, nullable=False, server_default="7")
    unusual_quantity_ratio = Column(Numeric(6, 2), nullable=False, server_default="2.0")
    backdate_limit_days = Column(SmallInteger, nullable=False, server_default="2")
    expired_batches_consumable = Column(Boolean, nullable=False, server_default="false")
    expired_batch_actions = Column(ARRAY(Text), nullable=False, server_default="{'WASTE'}")

    kitchen = relationship("Kitchen", back_populates="settings")

    __table_args__ = (
        CheckConstraint(
            "expiry_warning_days >= 0 AND expiry_warning_days <= 30",
            name="chk_kitchen_settings_expiry_warning"
        ),
        CheckConstraint(
            "target_coverage_days >= 1 AND target_coverage_days <= 60",
            name="chk_kitchen_settings_target_coverage"
        ),
        CheckConstraint(
            "consumption_window_days >= 7 AND consumption_window_days <= 90",
            name="chk_kitchen_settings_consumption_window"
        ),
        CheckConstraint(
            "min_history_days >= 1 AND min_history_days <= consumption_window_days",
            name="chk_kitchen_settings_min_history"
        ),
        CheckConstraint(
            "'WASTE' = ANY(expired_batch_actions)",
            name="chk_kitchen_settings_waste_required"
        ),
    )
