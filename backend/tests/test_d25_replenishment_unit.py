"""
Unit test độc lập cho Thuật toán Bổ sung hàng D25 (Revision 6.3).
Kiểm tra các trường hợp biên:
1. usable_qty: tổng remaining của các lô chưa hết hạn.
2. observed_days < min_history_days: ghi nhận insufficient_data (HISTORY_TOO_SHORT / NO_COMPLETE_DAYS / NO_HISTORY).
3. days_of_cover < target_coverage_days: đề xuất theo công thức raw = max(0, cov * avg - usable, min_stock - usable).
4. Làm tròn theo order_step: ceil(raw / step) * step.
5. avg_daily_consumption == 0: chỉ đề xuất nếu usable < min_stock (MIN_STOCK_ONLY), ngược lại no_recent_consumption.
"""
from decimal import Decimal, ROUND_CEILING
from datetime import date, timedelta
import unittest


def simulate_d25_replenishment(
    usable_qty: Decimal,
    min_stock_qty: Decimal,
    order_step: Decimal,
    history_start: date,
    as_of: date,
    consumption_in_window: Decimal,
    consumption_window_days: int = 14,
    min_history_days: int = 7,
    target_coverage_days: int = 3
):
    yesterday = as_of - timedelta(days=1)
    if history_start is None:
        return {
            "status": "insufficient_data",
            "reason": "NO_HISTORY",
            "suggested": Decimal("0") if usable_qty >= min_stock_qty else ((min_stock_qty - usable_qty) / order_step).quantize(Decimal("1"), rounding=ROUND_CEILING) * order_step
        }

    window_start = max(yesterday - timedelta(days=consumption_window_days - 1), history_start)
    observed_days = max(0, (yesterday - window_start).days + 1) if history_start <= yesterday else 0

    if observed_days < min_history_days:
        reason = "NO_COMPLETE_DAYS" if observed_days == 0 else "HISTORY_TOO_SHORT"
        suggested = Decimal("0")
        if usable_qty < min_stock_qty and min_stock_qty > Decimal("0"):
            raw = min_stock_qty - usable_qty
            suggested = (raw / order_step).quantize(Decimal("1"), rounding=ROUND_CEILING) * order_step
        return {
            "status": "insufficient_data",
            "reason": reason,
            "observed_days": observed_days,
            "suggested": suggested
        }

    avg_daily = (consumption_in_window / Decimal(str(observed_days))).quantize(Decimal("0.001"))
    if avg_daily > Decimal("0"):
        days_of_cover = (usable_qty / avg_daily).quantize(Decimal("0.1"))
        raw_cov = max(Decimal("0"), Decimal(str(target_coverage_days)) * avg_daily - usable_qty)
        raw_min = max(Decimal("0"), min_stock_qty - usable_qty)

        if days_of_cover < Decimal(str(target_coverage_days)) or usable_qty < min_stock_qty:
            raw_order = max(raw_cov, raw_min)
            suggested = (raw_order / order_step).quantize(Decimal("1"), rounding=ROUND_CEILING) * order_step
            return {
                "status": "suggested",
                "days_of_cover": days_of_cover,
                "avg_daily": avg_daily,
                "suggested": suggested
            }
        return {"status": "sufficient_stock", "days_of_cover": days_of_cover, "suggested": Decimal("0")}
    else:
        if usable_qty < min_stock_qty and min_stock_qty > Decimal("0"):
            raw = min_stock_qty - usable_qty
            suggested = (raw / order_step).quantize(Decimal("1"), rounding=ROUND_CEILING) * order_step
            return {"status": "suggested_min_only", "suggested": suggested}
        return {"status": "no_recent_consumption", "suggested": Decimal("0")}


class TestD25ReplenishmentAlgorithm(unittest.TestCase):

    def setUp(self):
        self.as_of = date(2026, 11, 7)

    def test_coverage_rule_suggests_order_with_order_step(self):
        # 14 ngày lịch sử, tiêu thụ 14 kg -> 1 kg/ngày
        # Mục tiêu 3 ngày -> cần 3 kg
        # Tồn 1 kg -> thiếu 2 kg. Order step = 0.5 kg -> đề xuất đúng 2.0 kg
        history_start = self.as_of - timedelta(days=20)
        res = simulate_d25_replenishment(
            usable_qty=Decimal("1.0"),
            min_stock_qty=Decimal("0"),
            order_step=Decimal("0.5"),
            history_start=history_start,
            as_of=self.as_of,
            consumption_in_window=Decimal("14.0"),
            consumption_window_days=14,
            min_history_days=7,
            target_coverage_days=3
        )
        self.assertEqual(res["status"], "suggested")
        self.assertEqual(res["days_of_cover"], Decimal("1.0"))
        self.assertEqual(res["suggested"], Decimal("2.0"))

    def test_order_step_rounds_up(self):
        # Cần 1.2 kg, order_step = 0.5 kg -> làm tròn trần lên 1.5 kg
        history_start = self.as_of - timedelta(days=20)
        res = simulate_d25_replenishment(
            usable_qty=Decimal("1.8"),
            min_stock_qty=Decimal("0"),
            order_step=Decimal("0.5"),
            history_start=history_start,
            as_of=self.as_of,
            consumption_in_window=Decimal("14.0"), # avg 1.0/ngày -> target 3 kg - 1.8 = 1.2 kg
            consumption_window_days=14,
            min_history_days=7,
            target_coverage_days=3
        )
        self.assertEqual(res["suggested"], Decimal("1.5"))

    def test_history_too_short_goes_to_insufficient_data(self):
        # Chỉ có 3 ngày lịch sử < min 7 ngày
        history_start = self.as_of - timedelta(days=3)
        res = simulate_d25_replenishment(
            usable_qty=Decimal("1.0"),
            min_stock_qty=Decimal("0"),
            order_step=Decimal("0.1"),
            history_start=history_start,
            as_of=self.as_of,
            consumption_in_window=Decimal("3.0"),
            min_history_days=7
        )
        self.assertEqual(res["status"], "insufficient_data")
        self.assertEqual(res["reason"], "HISTORY_TOO_SHORT")

    def test_min_stock_only_applies_when_history_insufficient(self):
        # Lịch sử chưa đủ nhưng tồn kho (0.5 kg) < ngưỡng tối thiểu (2.0 kg)
        history_start = self.as_of - timedelta(days=2)
        res = simulate_d25_replenishment(
            usable_qty=Decimal("0.5"),
            min_stock_qty=Decimal("2.0"),
            order_step=Decimal("0.5"),
            history_start=history_start,
            as_of=self.as_of,
            consumption_in_window=Decimal("1.0"),
            min_history_days=7
        )
        self.assertEqual(res["status"], "insufficient_data")
        self.assertEqual(res["suggested"], Decimal("1.5"))


if __name__ == "__main__":
    unittest.main()
