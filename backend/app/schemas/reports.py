"""
Pydantic Schemas cho Module Reports (Báo cáo P&L, Hao hụt, Bổ sung hàng D25).
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import date
from pydantic import BaseModel
from app.schemas.common import Labeled


class PeriodRange(BaseModel):
    from_date: date
    to_date: date


class SalesReportSection(BaseModel):
    revenue_vnd: int
    cogs_actual_vnd: int
    cogs_estimated_vnd: int
    gross_profit_excluding_estimates_vnd: int
    gross_profit_including_estimates_vnd: int
    portions_sold: int


class SelloffReportSection(BaseModel):
    revenue_vnd: int
    cost_vnd: int
    margin_vnd: int


class TotalsReportSection(BaseModel):
    revenue_vnd: int
    gross_profit_excluding_estimates_vnd: int
    gross_profit_including_estimates_vnd: int


class ShortageCountSummary(BaseModel):
    open_count: int
    written_off_estimated_count: int
    waived_count: int


class COGSStatusSummary(BaseModel):
    has_open_shortages: bool
    all_actual: bool


class ResultAfterLoss(BaseModel):
    excluding_estimates_vnd: int
    including_estimates_vnd: int
    policy_status: str = "CONFIRMED_REVISION_6_3"


class PeriodReportResponse(BaseModel):
    period: PeriodRange
    sales: SalesReportSection
    selloff: SelloffReportSection
    totals: TotalsReportSection
    waste_cost_vnd: int
    donation_cost_vnd: int
    adjustment_net_vnd: int
    shortages: ShortageCountSummary
    cogs_status: COGSStatusSummary
    result_after_ingredient_loss: ResultAfterLoss


class WasteReasonItem(BaseModel):
    reason: str
    cost_vnd: int
    count: int


class WasteIngredientItem(BaseModel):
    ingredient_name: str
    quantity: str
    unit: str
    cost_vnd: int
    count: int


class WasteReportResponse(BaseModel):
    total_waste_cost_vnd: int
    waste_count: int
    by_reason: List[WasteReasonItem]
    by_ingredient: List[WasteIngredientItem]


class DishProfitItem(BaseModel):
    dish_id: UUID
    dish_name: str
    portions: int
    revenue_vnd: int
    cogs_actual_vnd: int
    cogs_estimated_vnd: int
    gross_profit_vnd: int
    has_open_shortages: bool
    all_actual: bool


class DishProfitReportResponse(BaseModel):
    items: List[DishProfitItem]


class ReplenishmentItem(BaseModel):
    ingredient_id: UUID
    ingredient_name: str
    usable_qty: str
    unit: str
    avg_daily_consumption: Optional[str] = None
    days_of_cover: Optional[str] = None
    rule: str  # COVERAGE | MIN_STOCK_ONLY | BOTH
    raw_order_qty: str
    order_step: Optional[str] = None
    suggested_order_qty: str
    basis: str = "ESTIMATE"
    assumptions: List[str] = []


class ReplenishmentResponse(BaseModel):
    as_of: date
    parameters: Dict[str, Any]
    items: List[ReplenishmentItem]
    insufficient_data: List[Dict[str, Any]] = []
    no_recent_consumption: List[Dict[str, Any]] = []
