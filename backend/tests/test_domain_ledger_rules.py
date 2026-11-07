from datetime import date

import pytest

from app.domain.ledger_rules import (
    CONSUMED_FROM_STOCK, WAIVED, WRITTEN_OFF_ESTIMATED, MovementDates, OperationalDataCounts,
    Shortage, attribution_date, consumption_status, cost_status, has_operational_data,
    observation_window, reversal_attribution_date,
)

D = date


def test_attribution_precedence():
    occ = D(2026, 11, 1)
    assert attribution_date(MovementDates(occ)) == occ
    assert attribution_date(MovementDates(occ, sale_business_date=D(2026, 10, 1))) == D(2026, 10, 1)
    assert attribution_date(MovementDates(occ, document_business_date=D(2026, 10, 2))) == D(2026, 10, 2)
    assert attribution_date(MovementDates(occ, disposal_occurred_on=D(2026, 10, 3))) == D(2026, 10, 3)
    assert reversal_attribution_date(MovementDates(occ, sale_business_date=D(2026, 9, 1))) == D(2026, 9, 1)


def test_consumption_status():
    assert consumption_status([]) == "FULL"
    assert consumption_status([Shortage(True)]) == "PARTIAL"
    assert consumption_status([Shortage(False, WAIVED), Shortage(True)]) == "PARTIAL"
    assert consumption_status([Shortage(False, WAIVED)]) == "RESOLVED"


@pytest.mark.parametrize("sh,open_,actual", [
    ([], False, True),
    ([Shortage(True)], True, False),
    ([Shortage(False, WRITTEN_OFF_ESTIMATED)], False, False),   # even a 0 VND write-off
    ([Shortage(False, WAIVED)], False, False),
    ([Shortage(False, CONSUMED_FROM_STOCK)], False, True),      # does not affect it
])
def test_cost_status(sh, open_, actual):
    c = cost_status(sh)
    assert (c.has_open_shortages, c.all_actual) == (open_, actual)


def test_cost_status_counts():
    c = cost_status([Shortage(True), Shortage(False, WAIVED), Shortage(False, WAIVED),
                     Shortage(False, WRITTEN_OFF_ESTIMATED)])
    assert (c.open_count, c.written_off_estimated_count, c.waived_count) == (1, 1, 2)


TODAY = D(2026, 11, 6)


def test_window_no_history():
    w = observation_window(None, TODAY, 28)
    assert (w.reason, w.observed_days) == ("NO_HISTORY", 0)


def test_window_all_rows_today():
    w = observation_window(TODAY, TODAY, 28)
    assert (w.reason, w.observed_days) == ("NO_COMPLETE_DAYS", 0)


def test_window_one_complete_day():
    w = observation_window(D(2026, 11, 5), TODAY, 28)
    assert (w.reason, w.window_start, w.window_end, w.observed_days) == (None, D(2026, 11, 5), D(2026, 11, 5), 1)


def test_window_history_shorter_than_window():
    w = observation_window(D(2026, 11, 1), TODAY, 28)
    assert (w.window_start, w.observed_days) == (D(2026, 11, 1), 5)


def test_window_history_longer_than_window():
    w = observation_window(D(2026, 1, 1), TODAY, 7)
    assert (w.window_start, w.window_end, w.observed_days) == (D(2026, 10, 30), D(2026, 11, 5), 7)


def test_window_invalid():
    with pytest.raises(ValueError):
        observation_window(TODAY, TODAY, 0)


@pytest.mark.parametrize("field", ["batches", "stock_movements", "recipe_items",
                                   "non_cancelled_document_lines", "stock_shortages", "unit_conversions"])
def test_has_operational_data_each_condition(field):
    assert has_operational_data(OperationalDataCounts(**{field: 1})) is True


def test_has_operational_data_empty():
    assert has_operational_data(OperationalDataCounts()) is False
