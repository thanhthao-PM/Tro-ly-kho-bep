"""End-to-end service flow on a MIGRATED scratch database (TEST_DATABASE_URL). NOT RUN in the build sandbox.
Everything runs in one transaction that is rolled back; SET CONSTRAINTS ALL IMMEDIATE makes the deferred ledger
triggers (cache, sale-line cache, disposal link) fire, so passing here exercises them for real."""
import uuid
from datetime import timedelta
from decimal import Decimal

import pytest

pytest.importorskip("sqlalchemy")
from . import _helpers as h  # noqa: E402

pytestmark = pytest.mark.skipif(not h.URL, reason="TEST_DATABASE_URL not set")


@pytest.fixture()
def ctx():
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session
    from app.core.config import to_sqlalchemy_url
    from app.db import models as m
    from app.services import catalog
    from app.services.common import Ctx
    engine = create_engine(to_sqlalchemy_url(h.URL), connect_args={"prepare_threshold": None})
    s = Session(engine)
    uid = uuid.uuid4()
    s.add(m.UserProfile(id=uid, display_name="t"))
    s.flush()
    k = m.Kitchen(owner_user_id=uid, name="t")
    s.add(k)
    s.flush()
    c = Ctx(s, uid, k.id, "test")
    catalog.get_settings_row(c)
    yield c
    s.rollback()
    s.close()
    engine.dispose()


def settle(ctx):
    from sqlalchemy import text
    ctx.session.flush()
    ctx.session.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))


def test_receive_sell_shortage_resolve_dispose_report_assistant(ctx):
    from app.core.errors import ApiError
    from app.domain.expiry import today_vn
    from app.services import assistant, catalog, inventory, reporting, sales
    today = today_vn()
    a = uuid.UUID(catalog.create_ingredient(ctx, {"name": "x", "base_unit": "kg"})["id"])
    inventory.receive(ctx, {"ingredient_id": a, "quantity": 5, "unit_price_vnd": 10000, "expiry_date": today + timedelta(days=10)})
    inventory.receive(ctx, {"ingredient_id": a, "quantity": 3, "unit_price_vnd": 10000, "expiry_date": today + timedelta(days=5)})
    with pytest.raises(ApiError) as e:      # tracks expiry, none given
        inventory.receive(ctx, {"ingredient_id": a, "quantity": 1, "unit_price_vnd": 1})
    assert e.value.detail["code"] == "EXPIRY_REQUIRED"
    dish = sales.create_dish(ctx, {"name": "d", "price_vnd": 50000, "recipe": [{"ingredient_id": a, "quantity": 2}]})
    sale = sales.record_sale(ctx, today, [{"dish_id": uuid.UUID(dish["id"]), "quantity": 5}])   # needs 10 kg, has 8
    line = sale["lines"][0]
    assert line["consumption_status"] == "PARTIAL" and line["cogs_vnd"] == 80000
    assert sale["shortages"][0]["short_qty"] == "2.000"
    settle(ctx)
    first_batch = inventory.batches_of(ctx, a, include_empty=True)["batches"]
    assert all(b["remaining_qty"] == "0.000" for b in first_batch)
    sid = uuid.UUID(sale["shortages"][0]["id"])
    with pytest.raises(ApiError) as e:
        sales.resolve_shortage(ctx, sid, "CONSUME_FROM_STOCK", None)
    assert e.value.detail["code"] == "INSUFFICIENT_STOCK"
    inventory.receive(ctx, {"ingredient_id": a, "quantity": 4, "unit_price_vnd": 12000, "expiry_date": today + timedelta(days=9)})
    sales.resolve_shortage(ctx, sid, "CONSUME_FROM_STOCK", None)
    assert sales.get_sale(ctx, uuid.UUID(sale["id"]))["lines"][0]["cogs_vnd"] == 80000 + 24000
    settle(ctx)
    batch = uuid.UUID(inventory.batches_of(ctx, a)["batches"][0]["id"])
    out = inventory.dispose(ctx, batch, {"type": "WASTE", "quantity": 1, "reason_code": "SPOILED"})
    assert out["movement"]["type"] == "WASTE"
    settle(ctx)
    rep = reporting.summary(ctx, today, today)
    assert rep["sales"]["revenue_vnd"]["value"] == 250000 and rep["cogs_status"]["all_actual"] is True
    assert rep["waste_cost_vnd"]["value"] == 12000
    assert isinstance(reporting.replenishment(ctx)["items"], list)
    ans = assistant.answer(ctx, "Hôm nay nên xử lý gì trước?")
    assert ans["provider"] == "rule_based" and "facts" in ans
