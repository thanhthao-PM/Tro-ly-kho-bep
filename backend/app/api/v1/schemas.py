"""Request schemas. Responses are plain dicts built by services (Decimals already rendered as strings)."""
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID

Location = Literal["FRIDGE", "FREEZER", "PANTRY"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConversionIn(Strict):
    unit: str
    factor_to_base: Decimal = Field(gt=0)


class IngredientCreate(Strict):
    name: str = Field(min_length=1, max_length=80)
    base_unit: str
    default_location: Location = "FRIDGE"
    tracks_expiry: bool = True
    min_stock_qty: Decimal = Field(default=Decimal(0), ge=0)
    expiry_warning_days: int | None = Field(default=None, ge=0, le=30)
    order_step: Decimal | None = Field(default=None, gt=0)
    aliases: list[str] = []
    conversions: list[ConversionIn] = []


class ReceiptIn(Strict):
    ingredient_id: UUID
    quantity: Decimal = Field(gt=0)
    unit: str | None = None
    unit_price_vnd: Decimal = Field(ge=0, description="price per ENTERED unit")
    received_on: date | None = None
    expiry_date: date | None = None
    location: Location | None = None


class DisposalIn(Strict):
    type: Literal["DONATION", "SELLOFF", "WASTE"]
    quantity: Decimal = Field(gt=0)
    occurred_on: date | None = None
    note: str | None = Field(default=None, max_length=300)
    counterparty_name: str | None = Field(default=None, max_length=100)
    revenue_vnd: int | None = Field(default=None, ge=0)
    reason_code: Literal["EXPIRED", "SPOILED", "OVERSTOCK", "OTHER"] | None = None


class RecipeLineIn(Strict):
    ingredient_id: UUID
    quantity: Decimal = Field(gt=0)
    unit: str | None = None


class DishCreate(Strict):
    name: str = Field(min_length=1, max_length=80)
    price_vnd: int = Field(ge=0)
    recipe: list[RecipeLineIn] = Field(min_length=1)


class DocumentCreate(Strict):
    kind: Literal["IMPORT_INVOICE", "SALES_REPORT", "USAGE_SLIP"]
    source_format: Literal["MANUAL"] = "MANUAL"
    business_date: date


class LineIn(Strict):
    dish_id: UUID
    quantity: int = Field(gt=0, le=10000)


class ResolveIn(Strict):
    action: Literal["CONSUME_FROM_STOCK", "WRITE_OFF_ESTIMATED", "WAIVE"]
    note: str | None = Field(default=None, max_length=300)


class HistoryTurn(Strict):
    role: Literal["user", "assistant"]
    text: str = Field(max_length=500)


class AssistantIn(Strict):
    message: str = Field(min_length=1, max_length=500)
    history: list[HistoryTurn] = Field(default=[], max_length=10)
