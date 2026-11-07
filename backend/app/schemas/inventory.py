"""
Pydantic Schemas cho Module Inventory (Kho hàng, Lô hàng, Sổ cái).
"""
from typing import List, Optional, Dict
from uuid import UUID
from datetime import date, datetime
from pydantic import BaseModel, Field
from app.core.constants import StorageLocation, ExpiryStatus, MovementType


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
