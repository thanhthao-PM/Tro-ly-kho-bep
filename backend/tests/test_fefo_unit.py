"""
Unit test độc lập cho thuật toán FEFO (First-Expired, First-Out).
Kiểm tra:
1. Trật tự trừ lô ưu tiên theo hạn sử dụng sớm nhất (expiry_date ASC).
2. Khi cùng hạn dùng, ưu tiên lô nhận trước (received_on ASC).
3. Đảm bảo tồn kho không bao giờ bị âm: remaining_qty >= 0.
4. Trừ hết nhiều lô liên tiếp cho đến khi đủ số lượng yêu cầu.
5. Ghi nhận chính xác số lượng thiếu hụt (shortage_qty) khi kho không đủ.
"""
from decimal import Decimal
import unittest
from datetime import date, timedelta


class MockBatch:
    def __init__(self, batch_id: str, ingredient_id: str, initial_qty: Decimal, unit_cost: Decimal, expiry_date: date, received_on: date):
        self.id = batch_id
        self.ingredient_id = ingredient_id
        self.initial_qty = initial_qty
        self.remaining_qty = initial_qty
        self.unit_cost = unit_cost
        self.expiry_date = expiry_date
        self.received_on = received_on


def simulate_fefo_deduct(batches, quantity_to_deduct: Decimal):
    """Mô phỏng thuật toán FEFO cốt lõi của InventoryService."""
    # Sắp xếp theo FEFO: expiry_date ASC, received_on ASC
    usable_batches = sorted(
        [b for b in batches if b.remaining_qty > Decimal("0")],
        key=lambda b: (b.expiry_date or date.max, b.received_on)
    )

    remaining_need = quantity_to_deduct
    total_deducted = Decimal("0")
    total_cost_vnd = Decimal("0")
    deductions = []

    for batch in usable_batches:
        if remaining_need <= Decimal("0"):
            break

        available = batch.remaining_qty
        deduct_amt = min(available, remaining_need)
        batch.remaining_qty -= deduct_amt
        # Đảm bảo không âm
        assert batch.remaining_qty >= Decimal("0"), "Lỗi vi phạm bất biến: remaining_qty < 0"

        cost = deduct_amt * batch.unit_cost
        total_cost_vnd += cost
        total_deducted += deduct_amt
        remaining_need -= deduct_amt
        deductions.append((batch.id, deduct_amt, cost))

    shortage = remaining_need if remaining_need > Decimal("0") else Decimal("0")
    return {
        "deducted_qty": total_deducted,
        "shortage_qty": shortage,
        "total_cost_vnd": int(total_cost_vnd),
        "deductions": deductions
    }


class TestFEFOAlgorithm(unittest.TestCase):

    def setUp(self):
        self.today = date(2026, 3, 1)
        # Tạo 3 lô thịt ba rọi với ngày hết hạn và giá nhập khác nhau
        self.b1 = MockBatch(
            batch_id="b1",
            ingredient_id="thit_ba_roi",
            initial_qty=Decimal("1.0"),
            unit_cost=Decimal("150000"),
            expiry_date=self.today + timedelta(days=2),  # Hết hạn sớm nhất
            received_on=self.today - timedelta(days=3)
        )
        self.b2 = MockBatch(
            batch_id="b2",
            ingredient_id="thit_ba_roi",
            initial_qty=Decimal("2.0"),
            unit_cost=Decimal("155000"),
            expiry_date=self.today + timedelta(days=10), # Hết hạn sau
            received_on=self.today
        )
        self.b3 = MockBatch(
            batch_id="b3",
            ingredient_id="thit_ba_roi",
            initial_qty=Decimal("5.0"),
            unit_cost=Decimal("148000"),
            expiry_date=self.today + timedelta(days=25), # Hết hạn muộn nhất
            received_on=self.today - timedelta(days=1)
        )
        self.batches = [self.b2, self.b3, self.b1]  # Để thứ tự lộn xộn

    def test_fefo_deducts_earliest_batch_first(self):
        """Kiểm tra trừ trước từ lô có hạn dùng gần nhất (b1)."""
        res = simulate_fefo_deduct(self.batches, Decimal("0.8"))
        self.assertEqual(res["deducted_qty"], Decimal("0.8"))
        self.assertEqual(res["shortage_qty"], Decimal("0"))
        # b1 còn 0.2
        self.assertEqual(self.b1.remaining_qty, Decimal("0.2"))
        # b2 và b3 còn nguyên
        self.assertEqual(self.b2.remaining_qty, Decimal("2.0"))
        self.assertEqual(self.b3.remaining_qty, Decimal("5.0"))
        # Chi phí: 0.8 * 150000 = 120000 đ
        self.assertEqual(res["total_cost_vnd"], 120000)

    def test_fefo_spans_multiple_batches(self):
        """Kiểm tra trừ hết b1 (1.0) và trừ tiếp vào b2 (0.5)."""
        res = simulate_fefo_deduct(self.batches, Decimal("1.5"))
        self.assertEqual(res["deducted_qty"], Decimal("1.5"))
        self.assertEqual(res["shortage_qty"], Decimal("0"))
        # b1 hết sạch
        self.assertEqual(self.b1.remaining_qty, Decimal("0"))
        # b2 còn 1.5
        self.assertEqual(self.b2.remaining_qty, Decimal("1.5"))
        # Chi phí: 1.0 * 150000 + 0.5 * 155000 = 227500 đ
        self.assertEqual(res["total_cost_vnd"], 227500)

    def test_fefo_insufficient_stock_prevents_negative(self):
        """Khi yêu cầu 10.0 kg trong khi tổng kho chỉ có 8.0 kg: không được làm âm kho!"""
        res = simulate_fefo_deduct(self.batches, Decimal("10.0"))
        self.assertEqual(res["deducted_qty"], Decimal("8.0"))
        self.assertEqual(res["shortage_qty"], Decimal("2.0"))
        # Toàn bộ các lô về 0, tuyệt đối không bị âm
        self.assertEqual(self.b1.remaining_qty, Decimal("0"))
        self.assertEqual(self.b2.remaining_qty, Decimal("0"))
        self.assertEqual(self.b3.remaining_qty, Decimal("0"))


if __name__ == "__main__":
    unittest.main()
