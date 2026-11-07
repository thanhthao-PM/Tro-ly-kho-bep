"""Batches, receipts, FEFO consumption, disposals, overview. Writes stock only by inserting ledger rows; the
database trigger maintains batches.remaining_qty (6.3 s3.1)."""
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select, text

from app.core.errors import ApiError
from app.db import models as m
from app.domain.expiry import ExpiryStatus, classify_expiry, explicit_cook_batch_eligibility, today_vn
from app.domain.fefo import BatchView, allocate
from app.domain.money import round_cost, round_qty, vnd
from app.domain.units import UnitNotConvertible, convert_to_base, factor_to_base
from app.services import catalog
from app.services.common import Ctx, audit, cstr, qstr


# ---------- helpers ----------
def usable_clause(today: date, consumable: bool):
    """usable(batch) (6.3 s3.7): remaining > 0 and (not EXPIRED or expired_batches_consumable)."""
    cond = m.Batch.remaining_qty > 0
    if not consumable:
        cond = cond & (m.Batch.expiry_date.is_(None) | (m.Batch.expiry_date >= today))
    return cond


def warning_days(ing: m.Ingredient, st: m.KitchenSettings) -> int:
    return ing.expiry_warning_days if ing.expiry_warning_days is not None else st.expiry_warning_days


def batch_out(b: m.Batch, ing: m.Ingredient, st: m.KitchenSettings, today: date) -> dict:
    status = classify_expiry(b.expiry_date, today, warning_days(ing, st))
    return {"id": str(b.id), "ingredient_id": str(b.ingredient_id), "ingredient_name": ing.name,
            "received_on": b.received_on.isoformat(),
            "expiry_date": b.expiry_date.isoformat() if b.expiry_date else None,
            "initial_qty": qstr(b.initial_qty), "remaining_qty": qstr(b.remaining_qty), "unit": ing.base_unit_code,
            "unit_cost": cstr(b.unit_cost), "stock_value_vnd": vnd(b.remaining_qty * b.unit_cost),
            "location": b.location, "expiry_status": status.value,
            "days_to_expiry": (b.expiry_date - today).days if b.expiry_date else None}


def post_movement(ctx: Ctx, batch: m.Batch, mtype: str, qty_delta: Decimal, occurred_on: date, **refs) -> m.StockMovement:
    mv = m.StockMovement(
        kitchen_id=ctx.kitchen_id, batch_id=batch.id, ingredient_id=batch.ingredient_id, type=mtype,
        qty_delta=qty_delta, unit_cost_snapshot=batch.unit_cost, value_vnd=vnd(qty_delta * batch.unit_cost),
        occurred_on=occurred_on, actor_id=ctx.user_id, **refs)
    ctx.session.add(mv)
    ctx.session.flush()
    return mv


def lock_batches(ctx: Ctx, ingredient_id, today: date, consumable: bool):
    """Usable batches of one ingredient, locked FOR UPDATE in FEFO order. Returns (orm_by_id, views)."""
    rows = ctx.session.execute(
        select(m.Batch).where(m.Batch.kitchen_id == ctx.kitchen_id, m.Batch.ingredient_id == ingredient_id,
                              usable_clause(today, consumable))
        .order_by(m.Batch.expiry_date.asc().nulls_last(), m.Batch.received_on, m.Batch.id).with_for_update()).scalars().all()
    orm = {str(b.id): b for b in rows}
    views = [BatchView(str(b.id), b.expiry_date, b.received_on, b.remaining_qty, b.unit_cost) for b in rows]
    return orm, views


def consume_from(ctx: Ctx, orm: dict, views: list[BatchView], need: Decimal, mtype: str, occurred_on: date, **refs):
    """Allocate `need` FEFO against already-locked batches and post negative movements. Returns (cost_vnd, short)."""
    takes, short = allocate(views, need)
    cost = 0
    for v, t in takes:
        mv = post_movement(ctx, orm[v.id], mtype, -t, occurred_on, **refs)
        cost += -mv.value_vnd
    return cost, short


# ---------- receipt (I3) ----------
def receive(ctx: Ctx, d: dict) -> dict:
    s = ctx.session
    ing = catalog.get_ingredient(ctx, d["ingredient_id"], lock_share=True)
    st = catalog.get_settings_row(ctx)
    today = today_vn()
    received_on = d.get("received_on") or today
    if received_on > today:
        raise ApiError(422, "VALIDATION_ERROR", "received_on cannot be in the future")
    expiry = d.get("expiry_date")
    if expiry is None and ing.tracks_expiry:
        raise ApiError(422, "EXPIRY_REQUIRED", "This ingredient tracks expiry; expiry_date is required")
    if expiry is not None and expiry < received_on:
        raise ApiError(422, "VALIDATION_ERROR", "expiry_date cannot be before received_on")
    unit = d.get("unit") or ing.base_unit_code
    try:
        conv = catalog.conversions_for(ctx, ing.id)
        factor = factor_to_base(unit, ing.base_unit_code, catalog.unit_map(s), conv)
        base_qty = convert_to_base(Decimal(str(d["quantity"])), unit, ing.base_unit_code, catalog.unit_map(s), conv)
    except UnitNotConvertible as e:
        raise ApiError(422, "UNIT_NOT_CONVERTIBLE", f"Cannot convert {e.from_unit} to {e.to_unit}")
    if base_qty <= 0:
        raise ApiError(422, "VALIDATION_ERROR", "Quantity is too small after conversion")
    unit_cost = round_cost(Decimal(str(d["unit_price_vnd"])) / factor)
    batch = m.Batch(kitchen_id=ctx.kitchen_id, ingredient_id=ing.id, received_on=received_on, expiry_date=expiry,
                    initial_qty=base_qty, unit_cost=unit_cost, location=d.get("location") or ing.default_location)
    s.add(batch)
    s.flush()
    post_movement(ctx, batch, "RECEIPT", base_qty, received_on)
    s.refresh(batch)
    audit(ctx, "BATCH_RECEIVED", "batch", batch.id, after={"ingredient": ing.name, "qty": str(base_qty)})
    return batch_out(batch, ing, st, today)


# ---------- reads ----------
def batches_of(ctx: Ctx, ingredient_id, include_empty: bool = False) -> dict:
    ing = catalog.get_ingredient(ctx, ingredient_id)
    st, today = catalog.get_settings_row(ctx), today_vn()
    q = select(m.Batch).where(m.Batch.kitchen_id == ctx.kitchen_id, m.Batch.ingredient_id == ing.id)
    if not include_empty:
        q = q.where(m.Batch.remaining_qty > 0)
    rows = ctx.session.execute(q.order_by(m.Batch.expiry_date.asc().nulls_last(), m.Batch.received_on)).scalars().all()
    return {"ingredient_id": str(ing.id), "unit": ing.base_unit_code,
            "total_remaining": qstr(sum((b.remaining_qty for b in rows), Decimal(0))),
            "batches": [batch_out(b, ing, st, today) for b in rows]}


def get_batch(ctx: Ctx, batch_id, lock: bool = False) -> m.Batch:
    q = select(m.Batch).where(m.Batch.kitchen_id == ctx.kitchen_id, m.Batch.id == batch_id)
    if lock:
        q = q.with_for_update()
    b = ctx.session.execute(q).scalar_one_or_none()
    if b is None:
        raise ApiError(404, "NOT_FOUND", "Batch not found")
    return b


def _stock_rows(ctx: Ctx):
    ings = ctx.session.execute(select(m.Ingredient).where(
        m.Ingredient.kitchen_id == ctx.kitchen_id, m.Ingredient.deleted_at.is_(None))
        .order_by(m.Ingredient.normalized_name)).scalars().all()
    batches = ctx.session.execute(select(m.Batch).where(
        m.Batch.kitchen_id == ctx.kitchen_id, m.Batch.remaining_qty > 0)).scalars().all()
    by_ing: dict = {}
    for b in batches:
        by_ing.setdefault(b.ingredient_id, []).append(b)
    return ings, by_ing


def overview(ctx: Ctx) -> list[dict]:
    """I1: one row per active ingredient."""
    st, today = catalog.get_settings_row(ctx), today_vn()
    ings, by_ing = _stock_rows(ctx)
    out = []
    for ing in ings:
        bs = by_ing.get(ing.id, [])
        dated = [b.expiry_date for b in bs if b.expiry_date]
        nearest = min(dated) if dated else None
        out.append({
            "ingredient": {"id": str(ing.id), "name": ing.name}, "unit": ing.base_unit_code,
            "total_remaining": qstr(sum((b.remaining_qty for b in bs), Decimal(0))), "batch_count": len(bs),
            "location": ing.default_location, "min_stock_qty": qstr(ing.min_stock_qty),
            "nearest_expiry": nearest.isoformat() if nearest else None,
            "expiry_status": classify_expiry(nearest, today, warning_days(ing, st)).value if bs else None,
            "last_received_on": max((b.received_on for b in bs)).isoformat() if bs else None})
    return out


def summary(ctx: Ctx) -> dict:
    """I6."""
    st, today = catalog.get_settings_row(ctx), today_vn()
    ings, by_ing = _stock_rows(ctx)
    ing_by_id = {i.id: i for i in ings}
    value, n_batches = Decimal(0), 0
    by_status = {"expired": 0, "expires_soon": 0, "ok": 0}
    by_loc = {"FRIDGE": 0, "FREEZER": 0, "PANTRY": 0}
    for iid, bs in by_ing.items():
        ing = ing_by_id.get(iid)
        if ing is None:
            continue
        for b in bs:
            n_batches += 1
            value += b.remaining_qty * b.unit_cost
            by_loc[b.location] += 1
            s = classify_expiry(b.expiry_date, today, warning_days(ing, st))
            by_status["expired" if s == ExpiryStatus.EXPIRED else "expires_soon" if s == ExpiryStatus.EXPIRES_SOON else "ok"] += 1
    return {"ingredient_count": len(ings), "batch_count": n_batches, "stock_value_vnd": vnd(value),
            "by_status": by_status, "by_location": by_loc}


def usable_stock_map(ctx: Ctx) -> dict:
    """{ingredient_id: (usable_qty, usable_value)} using the shared usable(batch) definition."""
    st, today = catalog.get_settings_row(ctx), today_vn()
    rows = ctx.session.execute(
        select(m.Batch.ingredient_id, func.sum(m.Batch.remaining_qty), func.sum(m.Batch.remaining_qty * m.Batch.unit_cost))
        .where(m.Batch.kitchen_id == ctx.kitchen_id, usable_clause(today, st.expired_batches_consumable))
        .group_by(m.Batch.ingredient_id)).all()
    return {r[0]: (r[1] or Decimal(0), r[2] or Decimal(0)) for r in rows}


def expiring(ctx: Ctx) -> dict:
    """P1: batches EXPIRED or EXPIRES_SOON. Suggested dishes are deterministic queries, never generated text."""
    from app.services import sales  # local import: sales depends on inventory
    st, today = catalog.get_settings_row(ctx), today_vn()
    ings, by_ing = _stock_rows(ctx)
    dishes = sales.dish_snapshots(ctx)
    items = []
    for ing in ings:
        for b in by_ing.get(ing.id, []):
            status = classify_expiry(b.expiry_date, today, warning_days(ing, st))
            if status not in (ExpiryStatus.EXPIRED, ExpiryStatus.EXPIRES_SOON):
                continue
            if status == ExpiryStatus.EXPIRED:
                actions, suggestions = list(st.expired_batch_actions), []
            else:
                actions = ["DONATION", "SELLOFF", "WASTE"]
                suggestions = [{"dish_id": x["id"], "name": x["name"], "portions_possible": x["max_portions"],
                                "gross_margin_estimate_vnd": {"value": x["gross_profit_estimate_vnd"], "basis": "ESTIMATE"}}
                               for x in dishes if x["max_portions"] > 0 and str(ing.id) in x["ingredient_ids"]]
            items.append({"batch": batch_out(b, ing, st, today), "status": status.value, "suggested_dishes": suggestions,
                          "available_actions": actions, "expired_policy_status": "PLACEHOLDER_PENDING_D9"})
    items.sort(key=lambda x: x["batch"]["expiry_date"] or "9999")
    return {"as_of": today.isoformat(), "items": items}


def movements(ctx: Ctx, limit: int, offset: int, mtype: str | None = None) -> tuple[list[dict], int | None]:
    q = (select(m.StockMovement, m.Ingredient.name, m.Ingredient.base_unit_code)
         .join(m.Ingredient, (m.Ingredient.kitchen_id == m.StockMovement.kitchen_id) & (m.Ingredient.id == m.StockMovement.ingredient_id))
         .where(m.StockMovement.kitchen_id == ctx.kitchen_id))
    if mtype:
        q = q.where(m.StockMovement.type == mtype)
    rows = ctx.session.execute(q.order_by(m.StockMovement.occurred_on.desc(), m.StockMovement.created_at.desc())
                               .limit(limit + 1).offset(offset)).all()
    items = [{"id": str(mv.id), "occurred_on": mv.occurred_on.isoformat(), "type": mv.type,
              "ingredient": {"id": str(mv.ingredient_id), "name": name}, "batch_id": str(mv.batch_id),
              "qty_delta": qstr(mv.qty_delta), "unit": unit, "value_vnd": mv.value_vnd}
             for mv, name, unit in rows[:limit]]
    return items, (offset + limit if len(rows) > limit else None)


# ---------- disposals (P2: DONATION, SELLOFF, WASTE) ----------
def dispose(ctx: Ctx, batch_id, d: dict) -> dict:
    s = ctx.session
    batch = get_batch(ctx, batch_id, lock=True)
    ing = catalog.get_ingredient(ctx, batch.ingredient_id, lock_share=True, include_deleted=True)
    st, today = catalog.get_settings_row(ctx), today_vn()
    typ = d["type"]
    qty = round_qty(Decimal(str(d["quantity"])))
    if qty <= 0 or qty > batch.remaining_qty:
        raise ApiError(409, "INSUFFICIENT_STOCK", "Quantity exceeds the batch's remaining stock")
    status = classify_expiry(batch.expiry_date, today, warning_days(ing, st))
    if status == ExpiryStatus.EXPIRED and typ not in st.expired_batch_actions:
        raise ApiError(409, "ACTION_NOT_PERMITTED_FOR_EXPIRED_BATCH", f"{typ} is not permitted for an expired batch")
    reason = d.get("reason_code")
    if typ == "WASTE" and not reason:
        raise ApiError(422, "VALIDATION_ERROR", "reason_code is required for WASTE")
    if reason == "OTHER" and not d.get("note"):
        raise ApiError(422, "VALIDATION_ERROR", "note is required when reason_code is OTHER")
    if typ == "SELLOFF" and d.get("revenue_vnd") is None:
        raise ApiError(422, "VALIDATION_ERROR", "revenue_vnd is required for SELLOFF")
    occurred = d.get("occurred_on") or today
    disp = m.Disposal(kitchen_id=ctx.kitchen_id, batch_id=batch.id, type=typ, quantity=qty, occurred_on=occurred,
                      reason_code=reason if typ == "WASTE" else None, note=d.get("note"),
                      counterparty_name=d.get("counterparty_name"),
                      revenue_vnd=d.get("revenue_vnd") if typ == "SELLOFF" else None, created_by=ctx.user_id)
    s.add(disp)
    s.flush()
    mv = post_movement(ctx, batch, typ, -qty, occurred, disposal_id=disp.id, note=d.get("note"))
    s.refresh(batch)
    audit(ctx, "DISPOSAL_" + typ, "disposal", disp.id, after={"batch": str(batch.id), "qty": str(qty)})
    return {"disposal": {"id": str(disp.id), "type": typ, "quantity": qstr(qty), "occurred_on": occurred.isoformat()},
            "movement": {"id": str(mv.id), "type": mv.type, "qty_delta": qstr(mv.qty_delta), "value_vnd": mv.value_vnd},
            "cost_vnd": {"value": -mv.value_vnd, "basis": "ACTUAL"}, "batch": batch_out(batch, ing, st, today)}
