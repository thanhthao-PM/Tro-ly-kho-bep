"""Tests for migration 0012 (Review 1 fixes). NOT RUN in the build sandbox; needs a migrated scratch DB."""
from datetime import date

import pytest

from . import _helpers as h

psycopg = pytest.importorskip("psycopg")
pytestmark = pytest.mark.skipif(not h.URL, reason="TEST_DATABASE_URL not set")


@pytest.fixture()
def cx():
    c = h.connect()
    try:
        yield c
    finally:
        c.rollback()
        c.close()


def mk_disposal(cx, k, b, typ="WASTE", qty=2):
    return h.one(cx, """INSERT INTO disposals (kitchen_id, batch_id, type, quantity, occurred_on, reason_code)
                        VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
                 (k, b, typ, qty, date(2026, 1, 2), "SPOILED" if typ == "WASTE" else None) if typ != "SELLOFF"
                 else (k, b, typ, qty, date(2026, 1, 2), None))


SQL = """INSERT INTO stock_movements (kitchen_id, batch_id, ingredient_id, type, qty_delta, unit_cost_snapshot, value_vnd, occurred_on, disposal_id)
         VALUES (%s, %s, %s, %s, %s, 1000, %s, %s, %s)"""


def test_matching_disposal_movement_accepted(cx):
    _, k = h.mk_kitchen(cx); ing = h.mk_ingredient(cx, k); b = h.mk_batch(cx, k, ing)
    d = mk_disposal(cx, k, b)
    cx.execute(SQL, (k, b, ing, "WASTE", -2, -2000, date(2026, 1, 2), d))
    h.settle(cx)


@pytest.mark.parametrize("typ,qty", [("DONATION", -2), ("WASTE", -3)])
def test_type_or_quantity_mismatch_rejected(cx, typ, qty):
    _, k = h.mk_kitchen(cx); ing = h.mk_ingredient(cx, k); b = h.mk_batch(cx, k, ing)
    d = mk_disposal(cx, k, b)
    h.expect_error(cx, SQL, (k, b, ing, typ, qty, qty * 1000, date(2026, 1, 2), d), "must match its disposal")


def test_batch_mismatch_rejected(cx):
    _, k = h.mk_kitchen(cx); ing = h.mk_ingredient(cx, k); b1 = h.mk_batch(cx, k, ing); b2 = h.mk_batch(cx, k, ing)
    d = mk_disposal(cx, k, b1)
    h.expect_error(cx, SQL, (k, b2, ing, "WASTE", -2, -2000, date(2026, 1, 2), d), "must match its disposal")


def test_second_movement_for_same_disposal_rejected(cx):
    _, k = h.mk_kitchen(cx); ing = h.mk_ingredient(cx, k); b = h.mk_batch(cx, k, ing)
    d = mk_disposal(cx, k, b)
    cx.execute(SQL, (k, b, ing, "WASTE", -2, -2000, date(2026, 1, 2), d))
    h.expect_error(cx, SQL, (k, b, ing, "WASTE", -2, -2000, date(2026, 1, 2), d))


def test_disposal_without_movement_fails_at_commit(cx):
    _, k = h.mk_kitchen(cx); ing = h.mk_ingredient(cx, k); b = h.mk_batch(cx, k, ing)
    mk_disposal(cx, k, b)
    with pytest.raises(psycopg.Error):
        h.settle(cx)


def test_batch_source_line_and_created_at_immutable(cx):
    _, k = h.mk_kitchen(cx); ing = h.mk_ingredient(cx, k); b = h.mk_batch(cx, k, ing)
    h.expect_error(cx, "UPDATE batches SET created_at = now() - interval '1 day' WHERE id = %s", (b,), "may change")
    cx.execute("UPDATE batches SET location = 'PANTRY' WHERE id = %s", (b,))


def test_shortage_status_resolution_rule(cx):
    _, k = h.mk_kitchen(cx); ing = h.mk_ingredient(cx, k)
    dish = h.one(cx, "INSERT INTO dishes (kitchen_id, name, normalized_name, price_vnd) VALUES (%s,'d','d',1) RETURNING id", (k,))
    sale = h.one(cx, "INSERT INTO sales (kitchen_id, business_date) VALUES (%s, %s) RETURNING id", (k, date(2026, 1, 1)))
    sl = h.one(cx, """INSERT INTO sale_lines (kitchen_id, sale_id, dish_id, dish_name_snapshot, quantity, unit_price_snapshot_vnd, revenue_vnd, consumption_status)
                      VALUES (%s,%s,%s,'d',1,1,1,'PARTIAL') RETURNING id""", (k, sale, dish))
    h.expect_error(cx, """INSERT INTO stock_shortages (kitchen_id, sale_line_id, ingredient_id, short_qty, status, resolution, resolution_note)
                          VALUES (%s,%s,%s,1,'OPEN','WAIVED','n')""", (k, sl, ing), "ck_shortages_status_resolution")
