"""
SalesService: Xử lý bán hàng, định lượng món ăn và xử lý thiếu hụt theo Option C.
Tuân thủ nghiêm ngặt Architecture Revision 6.3:
- Không bao giờ sinh tồn kho âm.
- Khi kho không đủ nguyên liệu định lượng: ghi nhận StockShortage (status='OPEN').
- Hỗ trợ 3 phương án giải quyết (Option C):
  1. CONSUME_FROM_STOCK: Trừ bù khi lô hàng bổ sung đã về.
  2. WRITE_OFF_ESTIMATED: Trừ chi phí ước tính vào P&L.
  3. WAIVE: Miễn trừ chênh lệch.
"""
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from typing import List, Optional, Dict, Any
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from app.db.models.sales import Sale, SaleLine, StockShortage
from app.db.models.menu import Dish, RecipeItem
from app.db.models.catalog import Ingredient
from app.services.inventory_service import InventoryService


class SaleLineItemInput:
    def __init__(
        self,
        dish_id: str,
        quantity: int,
        unit_price_vnd: Optional[int] = None,
        origin: str = "NORMAL",
        source_batch_id: Optional[str] = None
    ):
        self.dish_id = dish_id
        self.quantity = quantity
        self.unit_price_vnd = unit_price_vnd
        self.origin = origin
        self.source_batch_id = source_batch_id


class SalesService:

    @staticmethod
    def record_sale(
        db: Session,
        kitchen_id: str,
        business_date: date,
        items: List[SaleLineItemInput],
        source_document_id: Optional[str] = None,
        actor_id: Optional[str] = None
    ) -> Sale:
        """
        Ghi nhận giao dịch bán hàng từ báo cáo xuất hoặc bán lẻ.
        Áp dụng nguyên tắc FEFO và cơ chế Option C để bảo toàn kho không âm.
        """
        if not items:
            raise ValueError("Giao dịch bán hàng cần ít nhất 1 dòng món ăn")

        sale = Sale(
            kitchen_id=kitchen_id,
            business_date=business_date,
            source_document_id=source_document_id,
            created_by=actor_id
        )
        db.add(sale)
        db.flush()

        for item in items:
            dish = db.execute(
                select(Dish).where(and_(Dish.kitchen_id == kitchen_id, Dish.id == item.dish_id))
            ).scalar_one_or_none()

            if not dish:
                raise ValueError(f"Không tìm thấy món ăn {item.dish_id}")

            unit_price = item.unit_price_vnd if item.unit_price_vnd is not None else dish.price_vnd
            revenue = unit_price * item.quantity

            # Lấy công thức định lượng của món ăn
            recipe_items = db.execute(
                select(RecipeItem).where(
                    and_(RecipeItem.kitchen_id == kitchen_id, RecipeItem.dish_id == item.dish_id)
                )
            ).scalars().all()

            sale_line = SaleLine(
                kitchen_id=kitchen_id,
                sale_id=sale.id,
                dish_id=dish.id,
                dish_name_snapshot=dish.name,
                quantity=item.quantity,
                unit_price_snapshot_vnd=unit_price,
                revenue_vnd=revenue,
                cogs_vnd=0,
                consumption_status="FULL",
                origin=item.origin,
                source_batch_id=item.source_batch_id
            )
            db.add(sale_line)
            db.flush()

            total_line_cogs = 0
            has_shortage = False

            for r_item in recipe_items:
                needed_qty = Decimal(str(r_item.quantity_base)) * Decimal(str(item.quantity))

                # Thực hiện trừ kho FEFO
                deduct_res = InventoryService.deduct_fefo(
                    db=db,
                    kitchen_id=kitchen_id,
                    ingredient_id=r_item.ingredient_id,
                    quantity_to_deduct=needed_qty,
                    movement_type="SALE_CONSUMPTION",
                    occurred_on=business_date,
                    actor_id=actor_id,
                    sale_line_id=sale_line.id,
                    for_update=True
                )

                total_line_cogs += deduct_res.actual_cogs_vnd

                # Áp dụng cơ chế Option C nếu thiếu hàng
                if deduct_res.shortage_qty > Decimal("0.0001"):
                    has_shortage = True
                    # Ghi nhận bản ghi thiếu hụt mở (status='OPEN')
                    shortage_record = StockShortage(
                        kitchen_id=kitchen_id,
                        sale_line_id=sale_line.id,
                        ingredient_id=r_item.ingredient_id,
                        short_qty=deduct_res.shortage_qty,
                        status="OPEN"
                    )
                    db.add(shortage_record)

            sale_line.cogs_vnd = total_line_cogs
            if has_shortage:
                sale_line.consumption_status = "PARTIAL"

        return sale

    @staticmethod
    def resolve_shortage(
        db: Session,
        kitchen_id: str,
        shortage_id: str,
        resolution_mode: str,
        actor_id: Optional[str] = None
    ) -> StockShortage:
        """
        Xử lý thiếu hụt Option C:
        1. CONSUME_FROM_STOCK: Trừ kho FEFO từ các lô mới nhập.
        2. WRITE_OFF_ESTIMATED: Ghi nhận chi phí ước tính, không trừ thêm kho.
        3. WAIVE: Miễn trừ chênh lệch.
        """
        valid_modes = ("CONSUME_FROM_STOCK", "WRITE_OFF_ESTIMATED", "WAIVE")
        if resolution_mode not in valid_modes:
            raise ValueError(f"Chế độ xử lý thiếu hụt không hợp lệ: {resolution_mode}")

        shortage = db.execute(
            select(StockShortage).where(
                and_(StockShortage.kitchen_id == kitchen_id, StockShortage.id == shortage_id)
            ).with_for_update()
        ).scalar_one_or_none()

        if not shortage:
            raise ValueError(f"Không tìm thấy bản ghi thiếu hụt {shortage_id}")

        if shortage.status != "OPEN":
            raise ValueError(f"Bản ghi thiếu hụt đã ở trạng thái {shortage.status}")

        if resolution_mode == "CONSUME_FROM_STOCK":
            # Trừ kho từ các lô có sẵn hiện tại
            deduct_res = InventoryService.deduct_fefo(
                db=db,
                kitchen_id=kitchen_id,
                ingredient_id=shortage.ingredient_id,
                quantity_to_deduct=shortage.short_qty,
                movement_type="SALE_CONSUMPTION",
                actor_id=actor_id,
                sale_line_id=shortage.sale_line_id
            )
            if deduct_res.shortage_qty > Decimal("0.0001"):
                raise ValueError("Kho vẫn chưa đủ hàng để thực hiện CONSUME_FROM_STOCK")

            # Cập nhật COGS cho SaleLine nếu có
            if shortage.sale_line_id:
                s_line = db.execute(
                    select(SaleLine).where(
                        and_(SaleLine.kitchen_id == kitchen_id, SaleLine.id == shortage.sale_line_id)
                    ).with_for_update()
                ).scalar_one_or_none()
                if s_line:
                    s_line.cogs_vnd += deduct_res.actual_cogs_vnd
                    s_line.consumption_status = "RESOLVED"

        shortage.status = "RESOLVED"
        shortage.resolution = resolution_mode
        return shortage
