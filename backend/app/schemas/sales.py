"""
Pydantic Schemas cho Module Sales & Shortages (Bán hàng & Thiếu hụt Option C).
"""
from typing import List, Optional
from uuid import UUID
from datetime import date, datetime
from pydantic import BaseModel, Field
from app.core.constants import SaleOrigin, ConsumptionStatus, ShortageStatus, ShortageResolution
from app.schemas.common import Labeled


class SaleLineResponse(BaseModel):
    id: UUID
    dish_id: UUID
    dish_name: str
    quantity: int
    unit_price_vnd: int
    revenue_vnd: int
    cogs_vnd: int
    estimated_cogs_vnd: Optional[int] = None
    consumption_status: ConsumptionStatus
    origin: SaleOrigin
    source_batch_id: Optional[UUID] = None


class SaleResponse(BaseModel):
    id: UUID
    business_date: date
    revenue_vnd: int
    line_count: int
    has_open_shortage: bool
    lines: Optional[List[SaleLineResponse]] = None


class ShortageResponse(BaseModel):
    id: UUID
    sale_line_id: Optional[UUID] = None
    document_line_id: Optional[UUID] = None
    business_date: date
    dish_name: Optional[str] = None
    ingredient_id: UUID
    ingredient_name: str
    short_qty: str
    unit: str
    status: ShortageStatus
    resolution: Optional[ShortageResolution] = None
    estimated_unit_cost: Optional[str] = None
    estimated_cost_vnd: Optional[int] = None
    resolution_note: Optional[str] = None
    resolved_at: Optional[datetime] = None


class ShortageResolveRequest(BaseModel):
    action: ShortageResolution = Field(description="CONSUME_FROM_STOCK | WRITE_OFF_ESTIMATED | WAIVE")
    note: Optional[str] = None
