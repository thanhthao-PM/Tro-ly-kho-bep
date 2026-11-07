"""Core DB tests (Rev 6.3 s3.1, 3.4, 3.8, C6). NOT RUN in the build sandbox (no PostgreSQL).

Needs a MIGRATED scratch database in TEST_DATABASE_URL (alembic upgrade head already applied).
Every test runs in one transaction that is ROLLED BACK, so nothing is persisted; still, do NOT
point this at the real Supabase project. Deferred constraint triggers are fired with
SET CONSTRAINTS ALL IMMEDIATE.
"""
import os
import uuid
from datetime import date

import pytest

psycopg = pytest.importorskip("psycopg")
URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL not set")


@pytest.fixture()
def cx():
    conn = psycopg.connect(URL, prepare_threshold=None, autocommit=False)
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()


def one(cx, sql, args=()):
    return cx.execute(sql, args).fetchone()[0]


def expect_error(cx, sql, args=(), contains=None):
    cx.execute("SAVEPOINT s")
    with pytest.raises(psycopg.Error) as e:
        cx.execute(sql, args)
    cx.execute("ROLLBACK TO SAVEPOINT s")
    if contains:
        assert contains in str(e.value)


def settle(cx):
    cx.execute("SET CONSTRAINTS ALL IMMEDIATE")


def mk_kitchen(cx):
    uid = uuid.uuid4()
    cx.execute("INSERT INTO user_profiles (id, display_name) VALUES (%s, 'test')", (uid,))
    k = one(cx, "INSERT INTO kitchens (owner_user_id, name) VALUES (%s, 'k') RETURNING id", (uid,))
    return uid, k


def mk_ingredient(cx, k, name="x", unit="kg"):
    return one(cx, """INSERT INTO ingredients (kitchen_id, name, normalized_name, search_name, base_unit_code, default_location)
                      VALUES (%s, %s, %s, %s, %s, 'FRIDGE') RETURNING id""", (k, name, name, name, unit))


def mk_batch(cx, k, ing, qty=10, cost=1000, expiry=date(2099, 1, 1)):
    b = one(cx, """INSERT INTO batches (kitchen_id, ingredient_id, received_on, expiry_date, initial_qty, unit_cost, location)
                   VALUES (%s, %s, %s, %s, %s, %s, 'FRIDGE') RETURNING id""", (k, ing, date(2026, 1, 1), expiry, qty, cost))
    cx.execute("""INSERT INTO stock_movements (kitchen_id, batch_id, ingredient_id, type, qty_delta, unit_cost_snapshot, value_vnd, occurred_on)
                  VALUES (%s, %s, %s, 'RECEIPT', %s, %s, %s, %s)""", (k, b, ing, qty, cost, qty * cost, date(2026, 1, 1)))
    return b


def move(cx, k, b, ing, mtype, qty, cost, **cols):
    keys = ["kitchen_id", "batch_id", "ingredient_id", "type", "qty_delta", "unit_cost_snapshot", "value_vnd", "occurred_on"] + list(cols)
    vals = [k, b, ing, mtype, qty, cost, round(qty * cost), date(2026, 1, 2)] + list(cols.values())
    return one(cx, f"INSERT INTO stock_movements ({','.join(keys)}) VALUES ({','.join(['%s'] * len(keys))}) RETURNING id", vals)


def remaining(cx, b):
    return one(cx, "SELECT remaining_qty FROM batches WHERE id = %s", (b,))


def test_receipt_posts_cache_and_commit_check_passes(cx):
    _, k = mk_kitchen(cx); ing = mk_ingredient(cx, k); b = mk_batch(cx, k, ing)
    settle(cx)
    assert remaining(cx, b) == 10


def test_direct_update_of_remaining_qty_rejected(cx):
    _, k = mk_kitchen(cx); ing = mk_ingredient(cx, k); b = mk_batch(cx, k, ing)
    expect_error(cx, "UPDATE batches SET remaining_qty = 99 WHERE id = %s", (b,), "ledger only")


def test_batch_insert_with_nonzero_remaining_rejected(cx):
    _, k = mk_kitchen(cx); ing = mk_ingredient(cx, k)
    expect_error(cx, """INSERT INTO batches (kitchen_id, ingredient_id, received_on, initial_qty, remaining_qty, unit_cost, location)
                        VALUES (%s, %s, %s, 5, 5, 1, 'FRIDGE')""", (k, ing, date(2026, 1, 1)))


def test_batch_without_receipt_fails_at_commit_check(cx):
    _, k = mk_kitchen(cx); ing = mk_ingredient(cx, k)
    cx.execute("""INSERT INTO batches (kitchen_id, ingredient_id, received_on, initial_qty, unit_cost, location)
                  VALUES (%s, %s, %s, 5, 1, 'FRIDGE')""", (k, ing, date(2026, 1, 1)))
    with pytest.raises(psycopg.Error):
        settle(cx)


def test_negative_stock_rejected(cx):
    _, k = mk_kitchen(cx); ing = mk_ingredient(cx, k); b = mk_batch(cx, k, ing, qty=2)
    expect_error(cx, """INSERT INTO stock_movements (kitchen_id, batch_id, ingredient_id, type, qty_delta, unit_cost_snapshot, value_vnd, occurred_on, reason_code)
                        VALUES (%s, %s, %s, 'ADJUSTMENT_OUT', -3, 1000, -3000, %s, 'LOSS')""", (k, b, ing, date(2026, 1, 2)))


def test_forged_cost_snapshot_rejected(cx):
    _, k = mk_kitchen(cx); ing = mk_ingredient(cx, k); b = mk_batch(cx, k, ing)
    expect_error(cx, """INSERT INTO stock_movements (kitchen_id, batch_id, ingredient_id, type, qty_delta, unit_cost_snapshot, value_vnd, occurred_on, reason_code)
                        VALUES (%s, %s, %s, 'ADJUSTMENT_OUT', -1, 1, -1, %s, 'LOSS')""", (k, b, ing, date(2026, 1, 2)))


def test_wrong_sign_for_type_rejected(cx):
    _, k = mk_kitchen(cx); ing = mk_ingredient(cx, k); b = mk_batch(cx, k, ing)
    expect_error(cx, """INSERT INTO stock_movements (kitchen_id, batch_id, ingredient_id, type, qty_delta, unit_cost_snapshot, value_vnd, occurred_on, reason_code)
                        VALUES (%s, %s, %s, 'ADJUSTMENT_IN', -1, 1000, -1000, %s, 'LOSS')""", (k, b, ing, date(2026, 1, 2)))


def test_adjustment_updates_cache_and_reversal_rules(cx):
    _, k = mk_kitchen(cx); ing = mk_ingredient(cx, k); b = mk_batch(cx, k, ing)
    m = move(cx, k, b, ing, "ADJUSTMENT_OUT", -4, 1000, reason_code="LOSS")
    assert remaining(cx, b) == 6
    rev = move(cx, k, b, ing, "REVERSAL", 4, 1000, reverses_movement_id=m)
    assert remaining(cx, b) == 10
    settle(cx)
    expect_error(cx, """INSERT INTO stock_movements (kitchen_id, batch_id, ingredient_id, type, qty_delta, unit_cost_snapshot, value_vnd, occurred_on, reverses_movement_id)
                        VALUES (%s, %s, %s, 'REVERSAL', 4, 1000, 4000, %s, %s)""", (k, b, ing, date(2026, 1, 3), m))   # double reversal
    expect_error(cx, """INSERT INTO stock_movements (kitchen_id, batch_id, ingredient_id, type, qty_delta, unit_cost_snapshot, value_vnd, occurred_on, reverses_movement_id)
                        VALUES (%s, %s, %s, 'REVERSAL', -4, 1000, -4000, %s, %s)""", (k, b, ing, date(2026, 1, 3), rev))  # reversal of a reversal


def test_reversal_with_wrong_amount_rejected(cx):
    _, k = mk_kitchen(cx); ing = mk_ingredient(cx, k); b = mk_batch(cx, k, ing)
    m = move(cx, k, b, ing, "ADJUSTMENT_OUT", -4, 1000, reason_code="LOSS")
    expect_error(cx, """INSERT INTO stock_movements (kitchen_id, batch_id, ingredient_id, type, qty_delta, unit_cost_snapshot, value_vnd, occurred_on, reverses_movement_id)
                        VALUES (%s, %s, %s, 'REVERSAL', 3, 1000, 3000, %s, %s)""", (k, b, ing, date(2026, 1, 3), m))


def test_ledger_is_append_only_and_truncate_blocked(cx):
    _, k = mk_kitchen(cx); ing = mk_ingredient(cx, k); mk_batch(cx, k, ing)
    expect_error(cx, "UPDATE stock_movements SET note = 'x'", (), "append-only")
    expect_error(cx, "DELETE FROM stock_movements", (), "append-only")
    expect_error(cx, "TRUNCATE stock_movements CASCADE", (), "TRUNCATE")
    expect_error(cx, "TRUNCATE batches CASCADE", (), "TRUNCATE")


def test_cross_kitchen_composite_fk(cx):
    _, k1 = mk_kitchen(cx); _, k2 = mk_kitchen(cx); ing = mk_ingredient(cx, k1)
    expect_error(cx, """INSERT INTO batches (kitchen_id, ingredient_id, received_on, initial_qty, unit_cost, location)
                        VALUES (%s, %s, %s, 1, 1, 'FRIDGE')""", (k2, ing, date(2026, 1, 1)))


def test_base_unit_lock(cx):
    _, k = mk_kitchen(cx); ing = mk_ingredient(cx, k, "free")
    cx.execute("UPDATE ingredients SET base_unit_code = 'g' WHERE id = %s", (ing,))   # no data yet: allowed
    cx.execute("UPDATE ingredients SET base_unit_code = 'g' WHERE id = %s", (ing,))   # no-op: allowed
    ing2 = mk_ingredient(cx, k, "used"); mk_batch(cx, k, ing2)
    expect_error(cx, "UPDATE ingredients SET base_unit_code = 'g' WHERE id = %s", (ing2,), "BASE_UNIT_LOCKED")


def test_sale_line_cache_checked_at_commit_and_ledger_effective(cx):
    _, k = mk_kitchen(cx); ing = mk_ingredient(cx, k); b = mk_batch(cx, k, ing)
    dish = one(cx, "INSERT INTO dishes (kitchen_id, name, normalized_name, price_vnd) VALUES (%s,'d','d',50000) RETURNING id", (k,))
    sale = one(cx, "INSERT INTO sales (kitchen_id, business_date) VALUES (%s, %s) RETURNING id", (k, date(2026, 2, 1)))
    sl = one(cx, """INSERT INTO sale_lines (kitchen_id, sale_id, dish_id, dish_name_snapshot, quantity, unit_price_snapshot_vnd, revenue_vnd)
                    VALUES (%s,%s,%s,'d',1,50000,50000) RETURNING id""", (k, sale, dish))
    m = move(cx, k, b, ing, "SALE_CONSUMPTION", -2, 1000, sale_line_id=sl)
    with pytest.raises(psycopg.Error):          # cogs_vnd still 0: must not commit
        settle(cx)
    cx.rollback()
    # fresh transaction, correct cache
    _, k = mk_kitchen(cx); ing = mk_ingredient(cx, k); b = mk_batch(cx, k, ing)
    dish = one(cx, "INSERT INTO dishes (kitchen_id, name, normalized_name, price_vnd) VALUES (%s,'d','d',50000) RETURNING id", (k,))
    sale = one(cx, "INSERT INTO sales (kitchen_id, business_date) VALUES (%s, %s) RETURNING id", (k, date(2026, 2, 1)))
    sl = one(cx, """INSERT INTO sale_lines (kitchen_id, sale_id, dish_id, dish_name_snapshot, quantity, unit_price_snapshot_vnd, revenue_vnd, cogs_vnd)
                    VALUES (%s,%s,%s,'d',1,50000,50000,2000) RETURNING id""", (k, sale, dish))
    m = move(cx, k, b, ing, "SALE_CONSUMPTION", -2, 1000, sale_line_id=sl)
    settle(cx)
    r = cx.execute("SELECT category, attribution_date FROM ledger_effective WHERE movement_id = %s", (m,)).fetchone()
    assert r == ("SALE_CONSUMPTION", date(2026, 2, 1))      # sale date, not occurred_on


def test_c6_catalog_rls_view_and_revokes(cx):
    no_rls = cx.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' AND NOT rowsecurity").fetchall()
    assert no_rls == []
    view_opts = one(cx, "SELECT reloptions::text FROM pg_class WHERE relname='ledger_effective'")
    assert "security_invoker=true" in view_opts
    roles = [r[0] for r in cx.execute("SELECT rolname FROM pg_roles WHERE rolname IN ('anon','authenticated')").fetchall()]
    for role in roles + ["PUBLIC"]:
        n = one(cx, """SELECT count(*) FROM information_schema.role_table_grants
                       WHERE grantee = %s AND table_schema = 'public'""", (role,))
        assert n == 0, role
