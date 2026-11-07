"""
Unit test độc lập cho cơ chế Option C (Xử lý thiếu hụt kho khi bán hàng).
Tuân thủ Architecture Revision 6.3:
1. Không bao giờ cho phép kho âm.
2. Thiếu hụt được ghi nhận vào StockShortage (status='OPEN').
3. Ba phương án giải quyết:
   - CONSUME_FROM_STOCK: Trừ bù khi lô hàng bổ sung đã về.
   - WRITE_OFF_ESTIMATED: Ghi nhận chi phí ước tính vào P&L.
   - WAIVE: Miễn trừ chênh lệch.
"""
from decimal import Decimal
import unittest


class MockShortage:
    def __init__(self, shortage_id: str, ingredient_id: str, short_qty: Decimal):
        self.id = shortage_id
        self.ingredient_id = ingredient_id
        self.short_qty = short_qty
        self.status = "OPEN"
        self.resolution = None


def resolve_shortage_logic(shortage: MockShortage, mode: str, available_stock: Decimal):
    """Mô phỏng hàm resolve_shortage của SalesService."""
    if mode not in ("CONSUME_FROM_STOCK", "WRITE_OFF_ESTIMATED", "WAIVE"):
        raise ValueError(f"Chế độ không hợp lệ: {mode}")

    if shortage.status != "OPEN":
        raise ValueError("Chỉ xử lý được bản ghi đang OPEN")

    if mode == "CONSUME_FROM_STOCK":
        if available_stock < shortage.short_qty:
            raise ValueError("Kho chưa đủ hàng để thực hiện CONSUME_FROM_STOCK")
        shortage.status = "RESOLVED"
        shortage.resolution = mode
        return {"deducted": shortage.short_qty, "remaining_stock": available_stock - shortage.short_qty}

    elif mode == "WRITE_OFF_ESTIMATED":
        shortage.status = "RESOLVED"
        shortage.resolution = mode
        return {"write_off_qty": shortage.short_qty, "remaining_stock": available_stock}

    else:  # WAIVE
        shortage.status = "RESOLVED"
        shortage.resolution = mode
        return {"waived_qty": shortage.short_qty, "remaining_stock": available_stock}


class TestOptionCMechanism(unittest.TestCase):

    def test_consume_from_stock_success(self):
        shortage = MockShortage("s1", "ca_chua", Decimal("1.5"))
        # Có 2.0 kg hàng mới về -> đủ bù
        res = resolve_shortage_logic(shortage, "CONSUME_FROM_STOCK", available_stock=Decimal("2.0"))
        self.assertEqual(shortage.status, "RESOLVED")
        self.assertEqual(shortage.resolution, "CONSUME_FROM_STOCK")
        self.assertEqual(res["remaining_stock"], Decimal("0.5"))

    def test_consume_from_stock_fails_if_insufficient(self):
        shortage = MockShortage("s2", "ca_chua", Decimal("1.5"))
        # Chỉ có 1.0 kg hàng mới về -> chưa đủ bù, báo lỗi
        with self.assertRaises(ValueError):
            resolve_shortage_logic(shortage, "CONSUME_FROM_STOCK", available_stock=Decimal("1.0"))

    def test_write_off_estimated(self):
        shortage = MockShortage("s3", "thit_ba_roi", Decimal("0.5"))
        res = resolve_shortage_logic(shortage, "WRITE_OFF_ESTIMATED", available_stock=Decimal("0.0"))
        self.assertEqual(shortage.status, "RESOLVED")
        self.assertEqual(shortage.resolution, "WRITE_OFF_ESTIMATED")
        self.assertEqual(res["write_off_qty"], Decimal("0.5"))

    def test_waive(self):
        shortage = MockShortage("s4", "hanh_la", Decimal("0.2"))
        res = resolve_shortage_logic(shortage, "WAIVE", available_stock=Decimal("0.0"))
        self.assertEqual(shortage.status, "RESOLVED")
        self.assertEqual(shortage.resolution, "WAIVE")
        self.assertEqual(res["waived_qty"], Decimal("0.2"))


if __name__ == "__main__":
    unittest.main()
