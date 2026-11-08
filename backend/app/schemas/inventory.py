"""
Pydantic Schemas cho Module Inventory (Kho hàng, Lô hàng, Sổ cái).
"""
from typing import Optional, Dict
from uuid import UUID
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field
from app.core.constants import StorageLocation, ExpiryStatus, MovementType


class BatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kitchen_id: UUID
    ingredient_id: UUID
    received_on: date
    expiry_date: Optional[date] = None
    initial_qty: Decimal
    remaining_qty: Decimal
    unit_cost: Decimal
    location: StorageLocation
    source_document_line_id: Optional[UUID] = None
    created_at: datetime


class BatchCreateRequest(BaseModel):
    ingredient_id: UUID
    quantity: Decimal = Field(gt=0)
    unit_cost: Decimal = Field(ge=0)
    location: StorageLocation
    expiry_date: Optional[date] = None
    received_on: Optional[date] = None


class BatchAdjustmentRequest(BaseModel):
    actual_quantity: Decimal = Field(ge=0)
    new_unit_cost: Optional[Decimal] = Field(default=None, ge=0)
    reason_code: Optional[str] = None


class BatchResponse(BaseModel):
    id: UUID
    ingredient_id: UUID
    ingredient_name: str
    received_on: date
    expiry_date: Optional[date] = None
    initial_qty: str
    remaining_qty: str
    unit: str
    unit_cost: str
    stock_value_vnd: int
    location: StorageLocation
    expiry_status: ExpiryStatus
    days_to_expiry: Optional[int] = None


class BatchCreate(BaseModel):
    ingredient_id: UUID
    quantity: str
    unit: Optional[str] = None
    unit_price_vnd: str
    received_on: date
    expiry_date: Optional[date] = None
    location: Optional[StorageLocation] = None


class BatchMetadataUpdate(BaseModel):
    location: Optional[StorageLocation] = None
    expiry_date: Optional[date] = None
    received_on: Optional[date] = None


class StocktakeAdjustmentRequest(BaseModel):
    new_remaining_quantity: str
    unit: Optional[str] = None
    reason_code: str = Field(description="COUNT_CORRECTION | LOSS | FOUND | OTHER")
    note: Optional[str] = None


class StockMovementResponse(BaseModel):
    id: UUID
    occurred_on: date
    type: MovementType
    category: str
    ingredient_id: UUID
    ingredient_name: str
    batch_id: UUID
    qty_delta: str
    unit: str
    unit_cost_snapshot: str
    value_vnd: int
    reference_kind: Optional[str] = None
    reference_id: Optional[UUID] = None
    created_at: datetime


class InventoryIngredientSummary(BaseModel):
    ingredient_id: UUID
    name: str
    total_remaining: str
    unit: str
    location: StorageLocation
    batch_count: int
    nearest_expiry: Optional[date] = None
    expiry_status: ExpiryStatus
    last_received_on: Optional[date] = None


class InventorySummaryResponse(BaseModel):
    ingredient_count: int
    batch_count: int
    stock_value_vnd: int
    by_status: Dict[str, int]
    by_location: Dict[str, int]
