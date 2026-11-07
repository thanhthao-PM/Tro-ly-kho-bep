from datetime import date
from decimal import Decimal as D

import pytest

from app.domain.fefo import BatchView, allocate
from app.domain.ledger_rules import observation_window
from app.domain.replenishment import ReplenishmentInput, classify
from app.domain.units import UnitInfo, UnitNotConvertible, convert_to_base

U = {"g": UnitInfo("MASS", D(1)), "kg": UnitInfo("MASS", D(1000)), "ml": UnitInfo("VOLUME", D(1)),
     "l": UnitInfo("VOLUME", D(1000)), "quả": UnitInfo("COUNT", None), "hộp": UnitInfo("COUNT", None),
     "bó": UnitInfo("COUNT", None), "chai": UnitInfo("COUNT", None)}


@pytest.mark.parametrize("q,frm,base,conv,want", [
    ("2", "kg", "kg", {}, "2"), ("1500", "g", "kg", {}, "1.5"), ("2", "kg", "g", {}, "2000"),
    ("1", "l", "ml", {}, "1000"), ("2", "hộp", "quả", {"hộp": D(12)}, "24"),
])
def test_convert_ok(q, frm, base, conv, want):
    assert convert_to_base(D(q), frm, base, U, conv) == D(want)


@pytest.mark.parametrize("frm,base", [("kg", "ml"), ("hộp", "quả"), ("bó", "chai"), ("quả", "kg")])
def test_convert_rejected_without_row(frm, base):
    with pytest.raises(UnitNotConvertible):
        convert_to_base(D(1), frm, base, U, {})


def bv(i, exp, rec, q, c=1000):
    return BatchView(i, exp, rec, D(q), D(c))


def test_fefo_order_and_split():
    a = bv("a", date(2026, 3, 1), date(2026, 1, 1), 2)
    b = bv("b", date(2026, 2, 1), date(2026, 1, 5), 3)
    n = bv("n", None, date(2026, 1, 1), 5)
    takes, short = allocate([a, n, b], D(6))
    assert [(t[0].id, t[1]) for t in takes] == [("b", D(3)), ("a", D(2)), ("n", D(1))] and short == 0


def test_fefo_shortage_and_tiebreak():
    x = bv("x", date(2026, 2, 1), date(2026, 1, 2), 1)
    y = bv("y", date(2026, 2, 1), date(2026, 1, 1), 1)
    takes, short = allocate([x, y], D(5))
    assert [t[0].id for t in takes] == ["y", "x"] and short == D(3)


def w(hist, today=date(2026, 11, 6), days=14):
    return observation_window(hist, today, days)


def inp(usable, cons, window, mn="0", step=None, tcd=3, mh=7):
    return ReplenishmentInput("i", "n", "kg", D(usable), D(mn), D(step) if step else None, D(cons), window, tcd, mh)


def test_repl_coverage_item_rounds_to_step():
    r = classify(inp("2", "28", w(date(2026, 10, 1)), step="5"))   # 14 days, avg 2/day, cover 1 < 3
    assert r[0].kind == "item" and r[0].rule == "COVERAGE" and r[0].raw_order_qty == D(4) and r[0].suggested_order_qty == D(5)


def test_repl_enough_cover_is_none():
    assert classify(inp("100", "28", w(date(2026, 10, 1))))[0].kind == "none"


def test_repl_zero_average():
    assert classify(inp("5", "0", w(date(2026, 10, 1))))[0].kind == "no_recent_consumption"
    r = classify(inp("1", "0", w(date(2026, 10, 1)), mn="3"))
    assert r[0].kind == "item" and r[0].rule == "MIN_STOCK_ONLY" and r[0].raw_order_qty == D(2)


def test_repl_short_history_gives_caveat_and_min_stock_item():
    r = classify(inp("1", "4", w(date(2026, 11, 3)), mn="3"))
    assert [x.kind for x in r] == ["insufficient_data", "item"] and r[0].reason == "HISTORY_TOO_SHORT"


def test_repl_no_history_and_no_complete_days():
    assert classify(inp("0", "0", w(None)))[0].reason == "NO_HISTORY"
    assert classify(inp("0", "0", w(date(2026, 11, 6))))[0].reason == "NO_COMPLETE_DAYS"


def test_repl_both_rule_takes_larger_raw():
    r = classify(inp("2", "28", w(date(2026, 10, 1)), mn="10"))
    assert r[0].rule == "BOTH" and r[0].raw_order_qty == D(8)
