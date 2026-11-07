"""
Pydantic Schemas cho Module Catalog (Nguyên liệu, Đơn vị, Quy đổi).
"""
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field
from app.core.constants import UnitDimension, StorageLocation


class UnitResponse(BaseModel):
    code: str
    label_vi: str
    dimension: UnitDimension
    factor_to_dimension_base: Optional[str] = None


class ConversionSchema(BaseModel):
    unit_code: str
    factor_to_base: str


class IngredientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    base_unit_code: str
    default_location: StorageLocation = StorageLocation.FRIDGE
    tracks_expiry: bool = True
    min_stock_qty: str = "0.000"
    order_step: Optional[str] = None
    expiry_warning_days: Optional[int] = Field(default=None, ge=0, le=30)
    aliases: List[str] = []
    conversions: List[ConversionSchema] = []


class IngredientUpdate(BaseModel):
    name: Optional[str] = None
    default_location: Optional[StorageLocation] = None
    tracks_expiry: Optional[bool] = None
    min_stock_qty: Optional[str] = None
    order_step: Optional[str] = None
    expiry_warning_days: Optional[int] = None
    aliases: Optional[List[str]] = None
    conversions: Optional[List[ConversionSchema]] = None


class IngredientResponse(BaseModel):
    id: UUID
    name: str
    normalized_name: str
    search_name: str
    base_unit: UnitResponse
    default_location: StorageLocation
    tracks_expiry: bool
    min_stock_qty: str
    order_step: Optional[str] = None
    expiry_warning_days: Optional[int] = None
    aliases: List[str] = []
    conversions: List[ConversionSchema] = []
    deleted: bool = False
