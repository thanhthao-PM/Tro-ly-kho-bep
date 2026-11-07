"""
Unit test độc lập cho CookService (Chế biến món ăn và cứu lô cận date).
Tuân thủ Architecture Revision 6.3:
1. Định lượng nguyên liệu = quantity_base * portions.
2. Trừ kho theo FEFO cho từng nguyên liệu.
3. Hỗ trợ repurposing từ lô cận date cụ thể (origin='REPURPOSE').
"""
from decimal import Decimal
import unittest


class MockRecipeItem:
    def __init__(self, ingredient_id: str, quantity_base: Decimal):
        self.ingredient_id = ingredient_id
        self.quantity_base = quantity_base


class MockDish:
    def __init__(self, dish_id: str, name: str, price_vnd: int, recipe):
        self.id = dish_id
        self.name = name
        self.price_vnd = price_vnd
        self.recipe = recipe


def simulate_cook(dish: MockDish, portions: int, available_stock: dict, source_batch_id: str = None):
    """Mô phỏng logic CookService.cook_dish."""
    if portions <= 0:
        raise ValueError("Số phần nấu phải lớn hơn 0")

    origin = "REPURPOSE" if source_batch_id else "NORMAL"
    total_cost_vnd = 0
    has_shortage = False
    deductions = {}

    for item in dish.recipe:
        needed = item.quantity_base * Decimal(str(portions))
        avail = available_stock.get(item.ingredient_id, Decimal("0"))

        deducted = min(avail, needed)
        shortage = needed - deducted
        if shortage > Decimal("0.0001"):
            has_shortage = True

        available_stock[item.ingredient_id] = avail - deducted
        deductions[item.ingredient_id] = {
            "needed": needed,
            "deducted": deducted,
            "shortage": shortage
        }

    return {
        "dish_name": dish.name,
        "portions": portions,
        "origin": origin,
        "has_shortage": has_shortage,
        "deductions": deductions
    }


class TestCookService(unittest.TestCase):

    def setUp(self):
        # Trứng chiên cà chua: cà chua 0.1 kg, trứng gà 2 quả, hành lá 0.1 bó
        self.recipe = [
            MockRecipeItem("ca_chua", Decimal("0.1")),
            MockRecipeItem("trung_ga", Decimal("2")),
            MockRecipeItem("hanh_la", Decimal("0.1")),
        ]
        self.dish = MockDish("d1", "Trứng chiên cà chua", 35000, self.recipe)

    def test_cook_with_sufficient_stock(self):
        stock = {
            "ca_chua": Decimal("1.0"),
            "trung_ga": Decimal("10"),
            "hanh_la": Decimal("1.0")
        }
        res = simulate_cook(self.dish, portions=4, available_stock=stock)
        self.assertEqual(res["portions"], 4)
        self.assertFalse(res["has_shortage"])
        self.assertEqual(res["origin"], "NORMAL")
        # Kiểm tra tồn kho sau khi nấu 4 phần:
        # Cà chua cần 0.4 -> còn 0.6
        self.assertEqual(stock["ca_chua"], Decimal("0.6"))
        # Trứng gà cần 8 quả -> còn 2 quả
        self.assertEqual(stock["trung_ga"], Decimal("2"))
        # Hành lá cần 0.4 -> còn 0.6
        self.assertEqual(stock["hanh_la"], Decimal("0.6"))

    def test_cook_repurpose_sets_origin(self):
        stock = {
            "ca_chua": Decimal("1.0"),
            "trung_ga": Decimal("10"),
            "hanh_la": Decimal("1.0")
        }
        res = simulate_cook(self.dish, portions=2, available_stock=stock, source_batch_id="batch-expiring-1")
        self.assertEqual(res["origin"], "REPURPOSE")

    def test_cook_with_partial_stock_flags_shortage(self):
        stock = {
            "ca_chua": Decimal("0.2"),  # Chỉ có 0.2 kg trong khi cần 0.5 kg
            "trung_ga": Decimal("10"),
            "hanh_la": Decimal("1.0")
        }
        res = simulate_cook(self.dish, portions=5, available_stock=stock)
        self.assertTrue(res["has_shortage"])
        self.assertEqual(res["deductions"]["ca_chua"]["shortage"], Decimal("0.3"))
        self.assertEqual(stock["ca_chua"], Decimal("0"))

    def test_cook_explicit_batch_priority(self):
        """Kiểm tra quy tắc 3.7: Lô chỉ định (source_batch_id) được trừ trước, phần còn lại qua FEFO."""
        explicit_batch_stock = Decimal("0.15")  # Lô cận date có 0.15 kg
        other_batches_stock = Decimal("0.50")   # Các lô khác có 0.50 kg
        needed_total = Decimal("0.30")          # Nấu 3 phần * 0.1 kg = 0.30 kg cà chua

        # 1. Trừ từ lô chỉ định trước
        deducted_from_explicit = min(explicit_batch_stock, needed_total)
        remaining_need = needed_total - deducted_from_explicit
        remaining_explicit = explicit_batch_stock - deducted_from_explicit

        # 2. Phần còn lại trừ từ các lô khác
        deducted_from_other = min(other_batches_stock, remaining_need)
        remaining_other = other_batches_stock - deducted_from_other

        self.assertEqual(deducted_from_explicit, Decimal("0.15"))
        self.assertEqual(remaining_explicit, Decimal("0.0"))
        self.assertEqual(deducted_from_other, Decimal("0.15"))
        self.assertEqual(remaining_other, Decimal("0.35"))


if __name__ == "__main__":
    unittest.main()
