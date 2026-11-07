"""SQLAlchemy models mirroring Alembic 0001-0012 (Alembic stays the schema authority, D31).

Relationships are intentionally NOT declared: the schema uses composite (kitchen_id, x_id) keys and I could not
execute mapper configuration here. Services use explicit, kitchen-scoped joins instead.
remaining_qty is never written by the application (maintained by the ledger trigger), so it carries only a server default.
"""
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Integer, Numeric, SmallInteger, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

PK = dict(primary_key=True, default=uuid.uuid4)
NOW = dict(server_default=text("now()"))


class Base(DeclarativeBase):
    pass


class UserProfile(Base):
    __tablename__ = "user_profiles"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    display_name: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), **NOW)


class Kitchen(Base):
    __tablename__ = "kitchens"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), **PK)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    name: Mapped[str] = mapped_column(Text)
    timezone: Mapped[str] = mapped_column(Text, server_default="Asia/Ho_Chi_Minh")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), **NOW)


class KitchenSettings(Base):
    __tablename__ = "kitchen_settings"
    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    expiry_warning_days: Mapped[int] = mapped_column(SmallInteger, server_default="3")
    target_coverage_days: Mapped[int] = mapped_column(SmallInteger, server_default="3")
    consumption_window_days: Mapped[int] = mapped_column(SmallInteger, server_default="14")
    min_history_days: Mapped[int] = mapped_column(SmallInteger, server_default="7")
    unusual_quantity_ratio: Mapped[Decimal] = mapped_column(Numeric(6, 2), server_default="2.0")
    backdate_limit_days: Mapped[int] = mapped_column(SmallInteger, server_default="2")
    expired_batches_consumable: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    expired_batch_actions: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("ARRAY['WASTE']::text[]"))


class Unit(Base):
    __tablename__ = "units"
    code: Mapped[str] = mapped_column(Text, primary_key=True)
    label_vi: Mapped[str] = mapped_column(Text)
    dimension: Mapped[str] = mapped_column(Text)
    factor_to_dimension_base: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)


class Ingredient(Base):
    __tablename__ = "ingredients"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), **PK)
    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    name: Mapped[str] = mapped_column(Text)
    normalized_name: Mapped[str] = mapped_column(Text)
    search_name: Mapped[str] = mapped_column(Text)
    base_unit_code: Mapped[str] = mapped_column(Text)
    default_location: Mapped[str] = mapped_column(Text)
    tracks_expiry: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    min_stock_qty: Mapped[Decimal] = mapped_column(Numeric(14, 3), server_default="0")
    expiry_warning_days: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    order_step: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), **NOW)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), **NOW)


class IngredientAlias(Base):
    __tablename__ = "ingredient_aliases"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), **PK)
    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    ingredient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    alias: Mapped[str] = mapped_column(Text)
    normalized_alias: Mapped[str] = mapped_column(Text)


class IngredientUnitConversion(Base):
    __tablename__ = "ingredient_unit_conversions"
    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    ingredient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    unit_code: Mapped[str] = mapped_column(Text, primary_key=True)
    base_unit_code: Mapped[str] = mapped_column(Text)
    factor_to_base: Mapped[Decimal] = mapped_column(Numeric(18, 6))


class Dish(Base):
    __tablename__ = "dishes"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), **PK)
    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    name: Mapped[str] = mapped_column(Text)
    normalized_name: Mapped[str] = mapped_column(Text)
    price_vnd: Mapped[int] = mapped_column(BigInteger)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), **NOW)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), **NOW)


class RecipeItem(Base):
    __tablename__ = "recipe_items"
    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    dish_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    ingredient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    quantity_base: Mapped[Decimal] = mapped_column(Numeric(14, 3))


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), **PK)
    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    kind: Mapped[str] = mapped_column(Text)
    source_format: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    business_date: Mapped[date] = mapped_column(Date)
    file_sha256: Mapped[str | None] = mapped_column(Text, nullable=True)
    storage_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_filename: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_status: Mapped[str] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), **NOW)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DocumentLine(Base):
    __tablename__ = "document_lines"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), **PK)
    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    line_no: Mapped[int] = mapped_column(Integer)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    ingredient_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    dish_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
    unit_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit_price_vnd: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    line_total_vnd: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    confidence: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    flags: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'"))
    is_selected: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), **PK)
    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    endpoint: Mapped[str] = mapped_column(Text)
    key: Mapped[str] = mapped_column(Text)
    request_hash: Mapped[str] = mapped_column(Text)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(Text)
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), **NOW)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Batch(Base):
    __tablename__ = "batches"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), **PK)
    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    ingredient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    received_on: Mapped[date] = mapped_column(Date)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    initial_qty: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    remaining_qty: Mapped[Decimal] = mapped_column(Numeric(14, 3), server_default="0")
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    location: Mapped[str] = mapped_column(Text)
    source_document_line_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), **NOW)


class Sale(Base):
    __tablename__ = "sales"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), **PK)
    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    business_date: Mapped[date] = mapped_column(Date)
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), **NOW)


class SaleLine(Base):
    __tablename__ = "sale_lines"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), **PK)
    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    sale_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    dish_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    dish_name_snapshot: Mapped[str] = mapped_column(Text)
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price_snapshot_vnd: Mapped[int] = mapped_column(BigInteger)
    revenue_vnd: Mapped[int] = mapped_column(BigInteger)
    cogs_vnd: Mapped[int] = mapped_column(BigInteger, server_default="0")
    consumption_status: Mapped[str] = mapped_column(Text, server_default="FULL")
    origin: Mapped[str] = mapped_column(Text, server_default="NORMAL")
    source_batch_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class Disposal(Base):
    __tablename__ = "disposals"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), **PK)
    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    type: Mapped[str] = mapped_column(Text)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    occurred_on: Mapped[date] = mapped_column(Date)
    reason_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    counterparty_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    revenue_vnd: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class StockShortage(Base):
    __tablename__ = "stock_shortages"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), **PK)
    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    sale_line_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    document_line_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    ingredient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    short_qty: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    status: Mapped[str] = mapped_column(Text, server_default="OPEN")
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    estimated_cost_vnd: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    estimate_batch_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), **NOW)


class StockMovement(Base):
    __tablename__ = "stock_movements"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), **PK)
    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    ingredient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    type: Mapped[str] = mapped_column(Text)
    qty_delta: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    unit_cost_snapshot: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    value_vnd: Mapped[int] = mapped_column(BigInteger)
    occurred_on: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), **NOW)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reason_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    sale_line_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    disposal_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    document_line_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    shortage_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reverses_movement_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class NotificationRead(Base):
    __tablename__ = "notification_reads"
    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    notification_key: Mapped[str] = mapped_column(Text, primary_key=True)
    read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), **NOW)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    action: Mapped[str] = mapped_column(Text)
    entity_type: Mapped[str] = mapped_column(Text)
    entity_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    before: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    after: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    request_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), **NOW)
