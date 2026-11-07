"""
Pydantic Schemas cho Module Menu (Món ăn, Định lượng, Giá vốn).
"""
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field
from app.schemas.common import Labeled


class RecipeItemSchema(BaseModel):
    ingredient_id: UUID
    ingredient_name: Optional[str] = None
    quantity: str
    unit: Optional[str] = None


class DishMarginEstimate(BaseModel):
    amount_vnd: int
    percent: int
    basis: str = "ESTIMATE"


class DishCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    price_vnd: int = Field(ge=0)
    recipe: List[RecipeItemSchema] = Field(min_length=1)


class DishUpdate(BaseModel):
    name: Optional[str] = None
    price_vnd: Optional[int] = Field(default=None, ge=0)
    recipe: Optional[List[RecipeItemSchema]] = None


class DishResponse(BaseModel):
    id: UUID
    name: str
    price_vnd: int
    recipe: List[RecipeItemSchema]
    cost_estimate_vnd: Labeled[int]
    gross_margin_estimate: DishMarginEstimate
    max_portions: int
    missing_ingredients: List[str]
    uses_expiring_stock: bool
