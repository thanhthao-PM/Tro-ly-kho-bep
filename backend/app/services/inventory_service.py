"""
InventoryService: Lõi quản lý tồn kho theo lô (Batches) và FEFO.
Tuân thủ nghiêm ngặt Architecture Revision 6.3:
1. Tồn kho không âm: batches.remaining_qty >= 0.
2. Sổ cái bất biến: mọi biến động ghi vào stock_movements.
3. Thuật toán FEFO: ưu tiên hạn sử dụng gần nhất (expiry_date ASC, received_on ASC).
4. Xử lý đồng thời: Sử dụng SELECT ... FOR UPDATE trên PostgreSQL.
"""
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime
from typing import List, Dict, Any, Optional, Tuple
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func

from app.db.models.inventory import Batch, StockMovement
from app.db.models.catalog import Ingredient


class DeductResult:
    def __init__(
        self,
        ingredient_id: str,
        requested_qty: Decimal,
        deducted_qty: Decimal,
        shortage_qty: Decimal,
        actual_cogs_vnd: int,
        movements: List[StockMovement]
    ):
        self.ingredient_id = ingredient_id
        self.requested_qty = requested_qty
        self.deducted_qty = deducted_qty
        self.shortage_qty = shortage_qty
        self.actual_cogs_vnd = actual_cogs_vnd
        self.movements = movements


class InventoryService:

    @staticmethod
    def get_usable_batches(
        db: Session,
        kitchen_id: str,
        ingredient_id: str,
        for_update: bool = False,
        allow_expired: bool = False
    ) -> List[Batch]:
        """
        Lấy danh sách các lô hàng còn tồn theo thứ tự FEFO.
        Khi for_update=True, khóa các hàng bằng SELECT ... FOR UPDATE trên PostgreSQL
        để tránh race conditions khi xử lý đồng thời.
        """
        stmt = (
            select(Batch)
            .where(
                and_(
                    Batch.kitchen_id == kitchen_id,
                    Batch.ingredient_id == ingredient_id,
                    Batch.remaining_qty > Decimal("0")
                )
            )
            .order_by(
                Batch.expiry_date.asc().nullslast(),
                Batch.received_on.asc(),
                Batch.id.asc()
            )
        )

        if not allow_expired:
            today = date.today()
            stmt = stmt.where(
                (Batch.expiry_date.is_(None)) | (Batch.expiry_date >= today)
            )

        if for_update:
            stmt = stmt.with_for_update()

        result = db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    def deduct_fefo(
        db: Session,
        kitchen_id: str,
        ingredient_id: str,
        quantity_to_deduct: Decimal,
        movement_type: str = "SALE_CONSUMPTION",
        occurred_on: Optional[date] = None,
        actor_id: Optional[str] = None,
        sale_line_id: Optional[str] = None,
        document_line_id: Optional[str] = None,
        disposal_id: Optional[str] = None,
        reason_code: Optional[str] = None,
        note: Optional[str] = None,
        for_update: bool = True,
        explicit_batch_id: Optional[str] = None
    ) -> DeductResult:
        """
        Thực hiện trừ kho FEFO cho một nguyên liệu.
        Ràng buộc cốt lõi (Revision 6.3):
        - Không bao giờ để remaining_qty < 0 (CheckConstraint trên DB).
        - Nếu có explicit_batch_id: ưu tiên trừ lô chỉ định trước, phần còn lại trừ qua FEFO.
          Lô chỉ định được loại trừ khỏi danh sách FEFO để không bị tính 2 lần (3.7).
        - Nếu số lượng yêu cầu vượt quá tồn kho khả dụng, phần thiếu hụt được ghi nhận
          riêng vào shortage_qty và không làm âm kho (Option C).
        - Mỗi lần trừ lô, tạo 1 bản ghi bất biến StockMovement với qty_delta âm và value_vnd âm.
        """
        if quantity_to_deduct <= Decimal("0"):
            return DeductResult(
                ingredient_id=ingredient_id,
                requested_qty=quantity_to_deduct,
                deducted_qty=Decimal("0"),
                shortage_qty=Decimal("0"),
                actual_cogs_vnd=0,
                movements=[]
            )

        occurred_date = occurred_on or date.today()
        remaining_need = quantity_to_deduct
        total_deducted = Decimal("0")
        total_cogs_vnd = Decimal("0")
        created_movements: List[StockMovement] = []

        # 1. Nếu có explicit_batch_id, ưu tiên trừ lô này trước
        if explicit_batch_id:
            stmt_exp = select(Batch).where(
                and_(
                    Batch.kitchen_id == kitchen_id,
                    Batch.id == explicit_batch_id,
                    Batch.ingredient_id == ingredient_id
                )
            )
            if for_update:
                stmt_exp = stmt_exp.with_for_update()
            exp_batch = db.execute(stmt_exp).scalar_one_or_none()

            if exp_batch and exp_batch.remaining_qty > Decimal("0"):
                avail = exp_batch.remaining_qty
                deduct_exp = min(avail, remaining_need)
                exp_batch.remaining_qty = avail - deduct_exp

                unit_cost = Decimal(str(exp_batch.unit_cost))
                line_val = (deduct_exp * unit_cost).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
                total_cogs_vnd += line_val

                m = StockMovement(
                    kitchen_id=kitchen_id,
                    ingredient_id=ingredient_id,
                    batch_id=exp_batch.id,
                    type=movement_type,
                    qty_delta=-deduct_exp,
                    unit_cost_snapshot=unit_cost,
                    value_vnd=-int(line_val),
                    occurred_on=occurred_date,
                    actor_id=actor_id,
                    sale_line_id=sale_line_id,
                    document_line_id=document_line_id,
                    disposal_id=disposal_id,
                    reason_code=reason_code,
                    note=f"{note or ''} (Lô chỉ định {explicit_batch_id})".strip()
                )
                db.add(m)
                created_movements.append(m)

                total_deducted += deduct_exp
                remaining_need -= deduct_exp

        # 2. Nếu vẫn còn nhu cầu, trừ tiếp qua các lô FEFO thông thường (loại trừ explicit_batch_id)
        if remaining_need > Decimal("0.0001"):
            usable_batches = InventoryService.get_usable_batches(
                db=db,
                kitchen_id=kitchen_id,
                ingredient_id=ingredient_id,
                for_update=for_update
            )

            for batch in usable_batches:
                if explicit_batch_id and str(batch.id) == str(explicit_batch_id):
                    continue
                if remaining_need <= Decimal("0.0001"):
                    break

                available = batch.remaining_qty
                deduct_amount = min(available, remaining_need)

                batch.remaining_qty = available - deduct_amount
                unit_cost = Decimal(str(batch.unit_cost))
                line_value = (deduct_amount * unit_cost).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
                total_cogs_vnd += line_value

                movement = StockMovement(
                    kitchen_id=kitchen_id,
                    ingredient_id=ingredient_id,
                    batch_id=batch.id,
                    type=movement_type,
                    qty_delta=-deduct_amount,
                    unit_cost_snapshot=unit_cost,
                    value_vnd=-int(line_value),
                    occurred_on=occurred_date,
                    actor_id=actor_id,
                    sale_line_id=sale_line_id,
                    document_line_id=document_line_id,
                    disposal_id=disposal_id,
                    reason_code=reason_code,
                    note=note
                )
                db.add(movement)
                created_movements.append(movement)

                total_deducted += deduct_amount
                remaining_need -= deduct_amount

        shortage = remaining_need if remaining_need > Decimal("0.0001") else Decimal("0")

        return DeductResult(
            ingredient_id=ingredient_id,
            requested_qty=quantity_to_deduct,
            deducted_qty=total_deducted,
            shortage_qty=shortage,
            actual_cogs_vnd=int(total_cogs_vnd),
            movements=created_movements
        )

    @staticmethod
    def receive_batch(
        db: Session,
        kitchen_id: str,
        ingredient_id: str,
        qty: Decimal,
        unit_cost: Decimal,
        location: str,
        expiry_date: Optional[date] = None,
        received_on: Optional[date] = None,
        document_line_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        note: Optional[str] = None
    ) -> Batch:
        """
        Nhập một lô hàng mới vào kho và ghi nhận sổ cái bất biến (type='RECEIPT').
        """
        if qty <= Decimal("0"):
            raise ValueError("Số lượng nhập phải lớn hơn 0")
        if unit_cost < Decimal("0"):
            raise ValueError("Đơn giá nhập không được âm")
        if location not in ("FRIDGE", "FREEZER", "PANTRY"):
            raise ValueError(f"Vị trí lưu trữ không hợp lệ: {location}")

        rec_date = received_on or date.today()
        if expiry_date and expiry_date < rec_date:
            raise ValueError("Hạn dùng không được trước ngày nhận hàng")

        batch = Batch(
            kitchen_id=kitchen_id,
            ingredient_id=ingredient_id,
            received_on=rec_date,
            expiry_date=expiry_date,
            initial_qty=qty,
            # The stock-movement trigger applies the receipt quantity to this starting balance.
            remaining_qty=Decimal("0"),
            unit_cost=unit_cost,
            location=location,
            source_document_line_id=document_line_id
        )
        db.add(batch)
        db.flush()  # Để sinh batch.id

        total_value_vnd = int((qty * unit_cost).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

        movement = StockMovement(
            kitchen_id=kitchen_id,
            ingredient_id=ingredient_id,
            batch_id=batch.id,
            type="RECEIPT",
            qty_delta=qty,
            unit_cost_snapshot=unit_cost,
            value_vnd=total_value_vnd,
            occurred_on=rec_date,
            actor_id=actor_id,
            document_line_id=document_line_id,
            note=note
        )
        db.add(movement)
        return batch

    @staticmethod
    def adjust_batch(
        db: Session,
        kitchen_id: str,
        batch_id: str,
        new_qty: Decimal,
        new_unit_cost: Optional[Decimal] = None,
        reason: str = "Kiểm kho",
        actor_id: Optional[str] = None
    ) -> Tuple[Batch, StockMovement]:
        """
        Điều chỉnh kiểm kho thực tế cho một lô hàng:
        - So sánh chênh lệch tồn kho.
        - Cập nhật số lượng còn lại.
        - Ghi sổ cái ADJUSTMENT_IN (nếu dư) hoặc ADJUSTMENT_OUT (nếu thiếu).
        """
        stmt = (
            select(Batch)
            .where(and_(Batch.kitchen_id == kitchen_id, Batch.id == batch_id))
            .with_for_update()
        )
        batch = db.execute(stmt).scalar_one_or_none()
        if not batch:
            raise ValueError(f"Không tìm thấy lô hàng {batch_id}")

        if new_qty < Decimal("0"):
            raise ValueError("Số lượng kiểm kho mới không được âm")

        old_qty = Decimal(str(batch.remaining_qty))
        qty_delta = new_qty - old_qty

        if abs(qty_delta) < Decimal("0.0001"):
            # Không thay đổi số lượng, chỉ cập nhật chi phí nếu có
            if new_unit_cost is not None and new_unit_cost >= Decimal("0"):
                batch.unit_cost = new_unit_cost
            return batch, None

        unit_cost = Decimal(str(new_unit_cost if new_unit_cost is not None else batch.unit_cost))
        delta_val = int((qty_delta * unit_cost).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        movement_type = "ADJUSTMENT_IN" if qty_delta > 0 else "ADJUSTMENT_OUT"

        batch.remaining_qty = new_qty
        if new_unit_cost is not None:
            batch.unit_cost = new_unit_cost

        movement = StockMovement(
            kitchen_id=kitchen_id,
            ingredient_id=batch.ingredient_id,
            batch_id=batch.id,
            type=movement_type,
            qty_delta=qty_delta,
            unit_cost_snapshot=unit_cost,
            value_vnd=delta_val,
            occurred_on=date.today(),
            actor_id=actor_id,
            reason_code=reason,
            note=f"Điều chỉnh kiểm kho từ {old_qty} thành {new_qty}"
        )
        db.add(movement)
        return batch, movement
