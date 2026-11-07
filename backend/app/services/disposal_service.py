"""
DisposalService: Xử lý quyên góp (DONATION), bán thu mua (SELLOFF) và tiêu hủy (WASTE).
Tuân thủ nghiêm ngặt Architecture Revision 6.3:
- Đảm bảo tính nhất quán giữa bảng disposals và sổ cái stock_movements.
- Kiểm tra tính hợp lệ của lý do bỏ (reason_code) và doanh thu thu mua (revenue_vnd).
"""
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from app.db.models.disposals import Disposal
from app.db.models.inventory import Batch, StockMovement


class DisposalService:

    @staticmethod
    def record_disposal(
        db: Session,
        kitchen_id: str,
        batch_id: str,
        disposal_type: str,
        quantity: Decimal,
        occurred_on: Optional[date] = None,
        reason_code: Optional[str] = None,
        note: Optional[str] = None,
        counterparty_name: Optional[str] = None,
        revenue_vnd: Optional[int] = None,
        actor_id: Optional[str] = None
    ) -> Disposal:
        """
        Ghi nhận xử lý hàng cho một lô cụ thể.
        disposal_type in ('DONATION', 'SELLOFF', 'WASTE').
        """
        if quantity <= Decimal("0"):
            raise ValueError("Số lượng xử lý phải lớn hơn 0")

        if disposal_type not in ("DONATION", "SELLOFF", "WASTE"):
            raise ValueError(f"Loại xử lý không hợp lệ: {disposal_type}")

        if disposal_type == "WASTE":
            if not reason_code or reason_code not in ("EXPIRED", "SPOILED", "OVERSTOCK", "OTHER"):
                raise ValueError("Bỏ hàng bắt buộc phải có reason_code: EXPIRED, SPOILED, OVERSTOCK hoặc OTHER")
            if reason_code == "OTHER" and not (note and note.strip()):
                raise ValueError("Bỏ hàng vì lý do OTHER bắt buộc phải có ghi chú (note)")
        else:
            reason_code = None

        if disposal_type == "SELLOFF":
            if revenue_vnd is None or revenue_vnd < 0:
                raise ValueError("Bán thu mua bắt buộc phải có doanh thu thu về (revenue_vnd >= 0)")
        else:
            revenue_vnd = None

        target_date = occurred_on or date.today()

        # Khóa lô hàng để đảm bảo tính toàn vẹn tồn kho
        stmt = (
            select(Batch)
            .where(and_(Batch.kitchen_id == kitchen_id, Batch.id == batch_id))
            .with_for_update()
        )
        batch = db.execute(stmt).scalar_one_or_none()
        if not batch:
            raise ValueError(f"Không tìm thấy lô hàng {batch_id}")

        available = Decimal(str(batch.remaining_qty))
        if quantity > available:
            raise ValueError(f"Số lượng xử lý ({quantity}) vượt quá tồn khả dụng của lô ({available})")

        # Cập nhật số lượng còn lại của lô
        batch.remaining_qty = available - quantity

        disposal = Disposal(
            kitchen_id=kitchen_id,
            batch_id=batch.id,
            type=disposal_type,
            quantity=quantity,
            occurred_on=target_date,
            reason_code=reason_code,
            note=note,
            counterparty_name=counterparty_name,
            revenue_vnd=revenue_vnd,
            created_by=actor_id
        )
        db.add(disposal)
        db.flush()

        # Ghi sổ cái bất biến
        unit_cost = Decimal(str(batch.unit_cost))
        disposal_cost = int((quantity * unit_cost).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

        movement = StockMovement(
            kitchen_id=kitchen_id,
            ingredient_id=batch.ingredient_id,
            batch_id=batch.id,
            type=disposal_type,
            qty_delta=-quantity,
            unit_cost_snapshot=unit_cost,
            value_vnd=-disposal_cost,
            occurred_on=target_date,
            actor_id=actor_id,
            disposal_id=disposal.id,
            reason_code=reason_code,
            note=note
        )
        db.add(movement)
        return disposal
