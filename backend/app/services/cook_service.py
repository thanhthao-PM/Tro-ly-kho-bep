"""
CookService: Xử lý hoạt động chế biến món ăn và cứu lô cận date (Repurposing).
Tuân thủ nghiêm ngặt Architecture Revision 6.3:
- Tính toán lượng nguyên liệu theo định lượng món ăn.
- Trừ kho theo thuật toán FEFO.
- Hỗ trợ biến món cận date thành món mới (origin='REPURPOSE').
"""
from decimal import Decimal
from datetime import date
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from app.db.models.menu import Dish, RecipeItem
from app.db.models.inventory import Batch
from app.services.inventory_service import InventoryService


class CookResult:
    def __init__(
        self,
        dish_id: str,
        dish_name: str,
        portions: int,
        total_cost_vnd: int,
        origin: str,
        has_shortage: bool,
        details: List[Dict[str, Any]]
    ):
        self.dish_id = dish_id
        self.dish_name = dish_name
        self.portions = portions
        self.total_cost_vnd = total_cost_vnd
        self.origin = origin
        self.has_shortage = has_shortage
        self.details = details


class CookService:

    @staticmethod
    def cook_dish(
        db: Session,
        kitchen_id: str,
        dish_id: str,
        portions: int,
        source_batch_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        cook_date: Optional[date] = None
    ) -> CookResult:
        """
        Nấu một món ăn với số phần nhất định.
        Khi có source_batch_id, đây là hành động repurpose nhằm cứu một lô cận date cụ thể.
        """
        if portions <= 0:
            raise ValueError("Số phần nấu phải lớn hơn 0")

        dish = db.execute(
            select(Dish).where(and_(Dish.kitchen_id == kitchen_id, Dish.id == dish_id))
        ).scalar_one_or_none()

        if not dish:
            raise ValueError(f"Không tìm thấy món ăn {dish_id}")

        origin = "REPURPOSE" if source_batch_id else "NORMAL"
        target_date = cook_date or date.today()

        source_batch = None
        if source_batch_id:
            source_batch = db.execute(
                select(Batch).where(and_(Batch.kitchen_id == kitchen_id, Batch.id == source_batch_id))
            ).scalar_one_or_none()

        recipe_items = db.execute(
            select(RecipeItem).where(
                and_(RecipeItem.kitchen_id == kitchen_id, RecipeItem.dish_id == dish_id)
            )
        ).scalars().all()

        if not recipe_items:
            raise ValueError(f"Món ăn {dish.name} chưa có định lượng nguyên liệu")

        total_cost_vnd = 0
        has_shortage = False
        details: List[Dict[str, Any]] = []

        for r_item in recipe_items:
            needed = Decimal(str(r_item.quantity_base)) * Decimal(str(portions))
            explicit_batch = (
                str(source_batch.id)
                if source_batch and str(source_batch.ingredient_id) == str(r_item.ingredient_id)
                else None
            )

            deduct_res = InventoryService.deduct_fefo(
                db=db,
                kitchen_id=kitchen_id,
                ingredient_id=r_item.ingredient_id,
                quantity_to_deduct=needed,
                movement_type="USAGE_CONSUMPTION" if origin == "NORMAL" else "SALE_CONSUMPTION",
                occurred_on=target_date,
                actor_id=actor_id,
                note=f"Chế biến {portions} phần {dish.name}" + (f" từ lô {source_batch_id}" if source_batch_id else ""),
                explicit_batch_id=explicit_batch
            )

            total_cost_vnd += deduct_res.actual_cogs_vnd
            if deduct_res.shortage_qty > Decimal("0.0001"):
                has_shortage = True

            details.append({
                "ingredient_id": str(r_item.ingredient_id),
                "needed_qty": float(needed),
                "deducted_qty": float(deduct_res.deducted_qty),
                "shortage_qty": float(deduct_res.shortage_qty),
                "cost_vnd": deduct_res.actual_cogs_vnd
            })

        return CookResult(
            dish_id=str(dish.id),
            dish_name=dish.name,
            portions=portions,
            total_cost_vnd=total_cost_vnd,
            origin=origin,
            has_shortage=has_shortage,
            details=details
        )
