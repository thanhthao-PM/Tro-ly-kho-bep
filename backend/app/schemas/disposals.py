"""
Pydantic Schemas cho Module Disposals (Xử lý hàng cận date & quá hạn).
"""
from typing import List, Optional
from uuid import UUID
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field
from app.core.constants import DisposalType, WasteReason, ExpiryStatus
from app.schemas.inventory import BatchResponse


class DisposalCreateRequest(BaseModel):
    batch_id: UUID
    type: DisposalType
    quantity: str = Field(gt=0)
    occurred_on: Optional[date] = None
    note: Optional[str] = None
    counterparty_name: Optional[str] = None
    revenue_vnd: Optional[int] = Field(default=None, ge=0)
    reason_code: Optional[WasteReason] = None


class DisposalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kitchen_id: UUID
    batch_id: UUID
    type: DisposalType
    quantity: str
    occurred_on: date
    reason_code: Optional[WasteReason] = None
    note: Optional[str] = None
    counterparty_name: Optional[str] = None
    revenue_vnd: Optional[int] = None
    created_by: Optional[UUID] = None
    created_at: datetime


class SuggestedDishSchema(BaseModel):
    dish_id: UUID
    name: str
    portions_possible: int
    gross_margin_estimate_vnd: int


class ExpiringBatchResponse(BaseModel):
    batch: BatchResponse
    status: ExpiryStatus
    suggested_dishes: List[SuggestedDishSchema] = []
    available_actions: List[str] = []


class DisposalCreate(BaseModel):
    type: DisposalType
    quantity: str
    unit: Optional[str] = None
    occurred_on: Optional[date] = None
    note: Optional[str] = None
    counterparty_name: Optional[str] = None
    revenue_vnd: Optional[int] = None
    reason_code: Optional[WasteReason] = None


class CookRequest(BaseModel):
    dish_id: UUID
    portions: int = Field(ge=1)
    business_date: Optional[date] = None
    note: Optional[str] = None
