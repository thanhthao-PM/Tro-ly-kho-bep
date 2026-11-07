"""
API Endpoints cho Thực đơn (Menu), Định lượng (Recipes) và Chế biến (CookService).
"""
from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from app.db.session import get_db
from app.db.models.menu import Dish, RecipeItem
from app.services.cook_service import CookService
from app.schemas.menu import DishResponse, DishCreateRequest, DishUpdateRequest

router = APIRouter(prefix="/menu", tags=["Menu"])


class CookDishRequest(BaseModel):
    portions: int = Field(..., gt=0, description="Số phần chế biến")
    source_batch_id: Optional[str] = Field(None, description="Lô cận date dùng làm món mới nếu có (Repurposing)")


@router.get("/dishes", response_model=List[DishResponse])
def list_dishes(
    kitchen_id: str = Query(..., description="ID của bếp"),
    db: Session = Depends(get_db)
):
    stmt = (
        select(Dish)
        .where(and_(Dish.kitchen_id == kitchen_id, Dish.deleted_at.is_(None)))
        .order_by(Dish.name.asc())
    )
    return db.execute(stmt).scalars().all()


@router.post("/dishes", response_model=DishResponse, status_code=status.HTTP_201_CREATED)
def create_dish(
    kitchen_id: str = Query(..., description="ID của bếp"),
    payload: DishCreateRequest = ...,
    db: Session = Depends(get_db)
):
    normalized = payload.name.lower().strip()
    existing = db.execute(
        select(Dish).where(
            and_(Dish.kitchen_id == kitchen_id, Dish.normalized_name == normalized, Dish.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Thực đơn đã có món cùng tên")

    dish = Dish(
        kitchen_id=kitchen_id,
        name=payload.name.strip(),
        normalized_name=normalized,
        price_vnd=payload.price_vnd
    )
    db.add(dish)
    db.flush()

    for item in payload.recipe:
        recipe_item = RecipeItem(
            kitchen_id=kitchen_id,
            dish_id=dish.id,
            ingredient_id=item.ingredient_id,
            quantity_base=item.quantity_base
        )
        db.add(recipe_item)

    db.commit()
    db.refresh(dish)
    return dish


@router.put("/dishes/{dish_id}", response_model=DishResponse)
def update_dish(
    dish_id: str,
    kitchen_id: str = Query(..., description="ID của bếp"),
    payload: DishUpdateRequest = ...,
    db: Session = Depends(get_db)
):
    dish = db.execute(
        select(Dish).where(
            and_(Dish.kitchen_id == kitchen_id, Dish.id == dish_id, Dish.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    if not dish:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy món ăn")

    if payload.name:
        dish.name = payload.name.strip()
        dish.normalized_name = payload.name.lower().strip()
    if payload.price_vnd is not None:
        dish.price_vnd = payload.price_vnd

    if payload.recipe is not None:
        # Xóa công thức cũ và cập nhật công thức mới
        existing_items = db.execute(
            select(RecipeItem).where(
                and_(RecipeItem.kitchen_id == kitchen_id, RecipeItem.dish_id == dish.id)
            )
        ).scalars().all()
        for it in existing_items:
            db.delete(it)

        for item in payload.recipe:
            recipe_item = RecipeItem(
                kitchen_id=kitchen_id,
                dish_id=dish.id,
                ingredient_id=item.ingredient_id,
                quantity_base=item.quantity_base
            )
            db.add(recipe_item)

    db.commit()
    db.refresh(dish)
    return dish


@router.post("/dishes/{dish_id}/cook")
def cook_dish(
    dish_id: str,
    kitchen_id: str = Query(..., description="ID của bếp"),
    payload: CookDishRequest = ...,
    db: Session = Depends(get_db)
):
    try:
        res = CookService.cook_dish(
            db=db,
            kitchen_id=kitchen_id,
            dish_id=dish_id,
            portions=payload.portions,
            source_batch_id=payload.source_batch_id
        )
        db.commit()
        return {
            "dish_id": res.dish_id,
            "dish_name": res.dish_name,
            "portions": res.portions,
            "total_cost_vnd": res.total_cost_vnd,
            "origin": res.origin,
            "has_shortage": res.has_shortage,
            "details": res.details
        }
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
