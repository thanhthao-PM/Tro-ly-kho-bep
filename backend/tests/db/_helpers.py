import os
import uuid
from datetime import date

import psycopg
import pytest

URL = os.environ.get("TEST_DATABASE_URL")


def connect():
    return psycopg.connect(URL, prepare_threshold=None, autocommit=False)


def one(cx, sql, args=()):
    return cx.execute(sql, args).fetchone()[0]


def expect_error(cx, sql, args=(), contains=None):
    cx.execute("SAVEPOINT s")
    with pytest.raises(psycopg.Error) as e:
        cx.execute(sql, args)
    cx.execute("ROLLBACK TO SAVEPOINT s")
    if contains:
        assert contains in str(e.value), str(e.value)


def settle(cx):
    cx.execute("SET CONSTRAINTS ALL IMMEDIATE")


def mk_kitchen(cx):
    uid = uuid.uuid4()
    cx.execute("INSERT INTO user_profiles (id, display_name) VALUES (%s, 'test')", (uid,))
    return uid, one(cx, "INSERT INTO kitchens (owner_user_id, name) VALUES (%s, 'k') RETURNING id", (uid,))


def mk_ingredient(cx, k, name="x", unit="kg"):
    return one(cx, """INSERT INTO ingredients (kitchen_id, name, normalized_name, search_name, base_unit_code, default_location)
                      VALUES (%s, %s, %s, %s, %s, 'FRIDGE') RETURNING id""", (k, name, name, name, unit))


def mk_batch(cx, k, ing, qty=10, cost=1000):
    b = one(cx, """INSERT INTO batches (kitchen_id, ingredient_id, received_on, expiry_date, initial_qty, unit_cost, location)
                   VALUES (%s, %s, %s, %s, %s, %s, 'FRIDGE') RETURNING id""", (k, ing, date(2026, 1, 1), date(2099, 1, 1), qty, cost))
    cx.execute("""INSERT INTO stock_movements (kitchen_id, batch_id, ingredient_id, type, qty_delta, unit_cost_snapshot, value_vnd, occurred_on)
                  VALUES (%s, %s, %s, 'RECEIPT', %s, %s, %s, %s)""", (k, b, ing, qty, cost, qty * cost, date(2026, 1, 1)))
    return b


def remaining(cx, b):
    return one(cx, "SELECT remaining_qty FROM batches WHERE id = %s", (b,))
