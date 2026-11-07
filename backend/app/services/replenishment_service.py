"""
ReplenishmentService: Dịch vụ đề xuất bổ sung hàng theo Thuật toán D25 (Revision 6.3).
Tuân thủ nghiêm ngặt:
- usable_qty: tổng remaining_qty của các lô chưa hết hạn (hoặc cả lô hết hạn nếu expired_batches_consumable=True).
- observed_days: số ngày thực tế trong cửa sổ lịch sử (từ window_start đến window_end = yesterday).
- Phân loại 3 nhóm: items (cần đặt), insufficient_data (chưa đủ dữ liệu lịch sử), no_recent_consumption (không có tiêu thụ).
- Làm tròn theo order_step: ceil(raw / step) * step.
"""
from decimal import Decimal, ROUND_CEILING
from datetime import date, timedelta
from typing import List, Dict, Any, Optional
import math
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func

from app.db.models.catalog import Ingredient
from app.db.models.inventory import Batch, StockMovement
from app.db.models.kitchen import KitchenSettings
from app.schemas.reports import ReplenishmentResponse, ReplenishmentItem


class ReplenishmentService:

    @staticmethod
    def get_replenishment_suggestions(
        db: Session,
        kitchen_id: str,
        as_of_date: Optional[date] = None,
        target_coverage_days: Optional[int] = None,
        consumption_window_days: Optional[int] = None,
        min_history_days: Optional[int] = None
    ) -> ReplenishmentResponse:
        today = as_of_date or date.today()
        yesterday = today - timedelta(days=1)

        # Lấy settings của bếp
        settings = db.execute(
            select(KitchenSettings).where(KitchenSettings.kitchen_id == kitchen_id)
        ).scalar_one_or_none()

        cov_days = target_coverage_days or (settings.target_coverage_days if settings else 3)
        win_days = consumption_window_days or (settings.consumption_window_days if settings else 14)
        min_hist = min_history_days or (settings.min_history_days if settings else 7)
        allow_expired = settings.expired_batches_consumable if settings else False

        # Lấy toàn bộ nguyên liệu chưa bị xóa
        ingredients = db.execute(
            select(Ingredient).where(
                and_(Ingredient.kitchen_id == kitchen_id, Ingredient.deleted_at.is_(None))
            ).order_by(Ingredient.name.asc())
        ).scalars().all()

        items: List[ReplenishmentItem] = []
        insufficient_data: List[Dict[str, Any]] = []
        no_recent_consumption: List[Dict[str, Any]] = []

        for ing in ingredients:
            ing_id = ing.id
            ing_name = ing.name
            unit = ing.base_unit_code
            min_stock = Decimal(str(ing.min_stock_qty or 0))
            order_step = Decimal(str(ing.order_step)) if ing.order_step else Decimal("0.001")

            # 1. usable_qty: tổng remaining_qty của các lô khả dụng
            batch_stmt = select(func.coalesce(func.sum(Batch.remaining_qty), Decimal("0"))).where(
                and_(
                    Batch.kitchen_id == kitchen_id,
                    Batch.ingredient_id == ing_id,
                    Batch.remaining_qty > Decimal("0")
                )
            )
            if not allow_expired:
                batch_stmt = batch_stmt.where(
                    (Batch.expiry_date.is_(None)) | (Batch.expiry_date >= today)
                )
            usable_qty = Decimal(str(db.execute(batch_stmt).scalar() or Decimal("0")))

            # 2. Lịch sử tiêu thụ
            # Earliest movement occurred_on
            earliest_stmt = select(func.min(StockMovement.occurred_on)).where(
                and_(
                    StockMovement.kitchen_id == kitchen_id,
                    StockMovement.ingredient_id == ing_id
                )
            )
            history_start = db.execute(earliest_stmt).scalar()

            if not history_start:
                # Không có bất kỳ biến động nào
                insufficient_data.append({
                    "ingredient_id": str(ing_id),
                    "ingredient_name": ing_name,
                    "reason": "NO_HISTORY",
                    "observed_days": 0,
                    "coverage_rule_skipped": True
                })
                # Kiểm tra min_stock_only
                if usable_qty < min_stock and min_stock > Decimal("0"):
                    raw = min_stock - usable_qty
                    suggested = (raw / order_step).quantize(Decimal("1"), rounding=ROUND_CEILING) * order_step
                    items.append(ReplenishmentItem(
                        ingredient_id=ing_id,
                        ingredient_name=ing_name,
                        usable_qty=str(usable_qty),
                        unit=unit,
                        rule="MIN_STOCK_ONLY",
                        raw_order_qty=str(raw),
                        order_step=str(order_step),
                        suggested_order_qty=str(suggested),
                        assumptions=["Chưa có lịch sử tiêu thụ; đề xuất chỉ căn cứ theo ngưỡng tồn tối thiểu"]
                    ))
                continue

            window_start = max(yesterday - timedelta(days=win_days - 1), history_start)
            observed_days = max(0, (yesterday - window_start).days + 1) if history_start <= yesterday else 0

            if observed_days < min_hist:
                reason = "NO_COMPLETE_DAYS" if observed_days == 0 else "HISTORY_TOO_SHORT"
                insufficient_data.append({
                    "ingredient_id": str(ing_id),
                    "ingredient_name": ing_name,
                    "reason": reason,
                    "observed_days": observed_days,
                    "coverage_rule_skipped": True
                })
                # Kiểm tra min_stock_only
                if usable_qty < min_stock and min_stock > Decimal("0"):
                    raw = min_stock - usable_qty
                    suggested = (raw / order_step).quantize(Decimal("1"), rounding=ROUND_CEILING) * order_step
                    items.append(ReplenishmentItem(
                        ingredient_id=ing_id,
                        ingredient_name=ing_name,
                        usable_qty=str(usable_qty),
                        unit=unit,
                        rule="MIN_STOCK_ONLY",
                        raw_order_qty=str(raw),
                        order_step=str(order_step),
                        suggested_order_qty=str(suggested),
                        assumptions=[f"Lịch sử quan sát ({observed_days} ngày) < ngưỡng tối thiểu ({min_hist} ngày); đề xuất theo tồn tối thiểu"]
                    ))
                continue

            # Tính tổng tiêu thụ trong cửa sổ quan sát: SALE_CONSUMPTION và USAGE_CONSUMPTION
            cons_stmt = select(func.coalesce(func.sum(-StockMovement.qty_delta), Decimal("0"))).where(
                and_(
                    StockMovement.kitchen_id == kitchen_id,
                    StockMovement.ingredient_id == ing_id,
                    StockMovement.type.in_(("SALE_CONSUMPTION", "USAGE_CONSUMPTION")),
                    StockMovement.occurred_on >= window_start,
                    StockMovement.occurred_on <= yesterday
                )
            )
            consumption_total = Decimal(str(db.execute(cons_stmt).scalar() or Decimal("0")))
            avg_daily = (consumption_total / Decimal(str(observed_days))).quantize(Decimal("0.001"))

            if avg_daily > Decimal("0"):
                days_of_cover = (usable_qty / avg_daily).quantize(Decimal("0.1"))
                raw_cov = max(Decimal("0"), Decimal(str(cov_days)) * avg_daily - usable_qty)
                raw_min = max(Decimal("0"), min_stock - usable_qty)

                under_cov = days_of_cover < Decimal(str(cov_days))
                under_min = usable_qty < min_stock

                if under_cov or under_min:
                    raw_order = max(raw_cov, raw_min)
                    suggested = (raw_order / order_step).quantize(Decimal("1"), rounding=ROUND_CEILING) * order_step
                    rule = "BOTH" if (under_cov and under_min) else ("COVERAGE" if under_cov else "MIN_STOCK_ONLY")

                    assumptions = [
                        f"Tiêu thụ bình quân: {avg_daily} {unit}/ngày trong {observed_days} ngày quan sát",
                        f"Tồn khả dụng đủ dùng ~{days_of_cover} ngày (mục tiêu: {cov_days} ngày)"
                    ]

                    items.append(ReplenishmentItem(
                        ingredient_id=ing_id,
                        ingredient_name=ing_name,
                        usable_qty=str(usable_qty),
                        unit=unit,
                        avg_daily_consumption=str(avg_daily),
                        days_of_cover=str(days_of_cover),
                        rule=rule,
                        raw_order_qty=str(raw_order),
                        order_step=str(order_step),
                        suggested_order_qty=str(suggested),
                        assumptions=assumptions
                    ))
            else:
                # avg_daily == 0
                if usable_qty < min_stock and min_stock > Decimal("0"):
                    raw = min_stock - usable_qty
                    suggested = (raw / order_step).quantize(Decimal("1"), rounding=ROUND_CEILING) * order_step
                    items.append(ReplenishmentItem(
                        ingredient_id=ing_id,
                        ingredient_name=ing_name,
                        usable_qty=str(usable_qty),
                        unit=unit,
                        avg_daily_consumption="0.000",
                        days_of_cover=None,
                        rule="MIN_STOCK_ONLY",
                        raw_order_qty=str(raw),
                        order_step=str(order_step),
                        suggested_order_qty=str(suggested),
                        assumptions=["Không có tiêu thụ trong kỳ quan sát; đề xuất theo tồn tối thiểu"]
                    ))
                else:
                    no_recent_consumption.append({
                        "ingredient_id": str(ing_id),
                        "ingredient_name": ing_name,
                        "observed_days": observed_days,
                        "usable_qty": str(usable_qty),
                        "unit": unit
                    })

        return ReplenishmentResponse(
            as_of=today,
            parameters={
                "target_coverage_days": cov_days,
                "consumption_window_days": win_days,
                "min_history_days": min_hist,
                "expired_batches_consumable": allow_expired
            },
            items=items,
            insufficient_data=insufficient_data,
            no_recent_consumption=no_recent_consumption
        )
