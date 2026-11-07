"""Menu, sales (FEFO consumption), shortages (Option C), settle_sale_lines, manual sales-report documents."""
import uuid
from datetime import date, timedelta
from decimal import ROUND_FLOOR, Decimal

from sqlalchemy import func, select, text

from app.core.errors import ApiError
from app.db import models as m
from app.domain.expiry import today_vn
from app.domain.ledger_rules import Shortage, consumption_status
from app.domain.money import round_qty, vnd
from app.domain.text import normalize
from app.domain.units import UnitNotConvertible, convert_to_base
from app.services import catalog, inventory
from app.services.common import Ctx, audit, cstr, qstr


# ---------- menu ----------
def _recipes(ctx: Ctx, dish_ids=None):
    q = select(m.RecipeItem).where(m.RecipeItem.kitchen_id == ctx.kitchen_id)
    if dish_ids is not None:
        q = q.where(m.RecipeItem.dish_id.in_(dish_ids))
    out: dict = {}
    for r in ctx.session.execute(q).scalars():
        out.setdefault(r.dish_id, []).append(r)
    return out


def dish_snapshots(ctx: Ctx) -> list[dict]:
    """Dishes with ESTIMATE cost, margin, max_portions (shared usable(batch) definition)."""
    s, today = ctx.session, today_vn()
    st = catalog.get_settings_row(ctx)
    dishes = s.execute(select(m.Dish).where(m.Dish.kitchen_id == ctx.kitchen_id, m.Dish.deleted_at.is_(None))
                       .order_by(m.Dish.normalized_name)).scalars().all()
    rec = _recipes(ctx)
    ings = {i.id: i for i in s.execute(select(m.Ingredient).where(m.Ingredient.kitchen_id == ctx.kitchen_id)).scalars()}
    stock = inventory.usable_stock_map(ctx)
    soon = {r[0] for r in s.execute(
        select(m.Batch.ingredient_id).where(
            m.Batch.kitchen_id == ctx.kitchen_id, inventory.usable_clause(today, st.expired_batches_consumable),
            m.Batch.expiry_date.is_not(None), m.Batch.expiry_date <= today + timedelta(days=st.expiry_warning_days)))}
    out = []
    for d in dishes:
        items, cost, mx, missing = [], Decimal(0), None, []
        for r in rec.get(d.id, []):
            ing = ings.get(r.ingredient_id)
            qty, val = stock.get(r.ingredient_id, (Decimal(0), Decimal(0)))
            avg = (val / qty) if qty > 0 else Decimal(0)
            cost += r.quantity_base * avg
            n = int((qty / r.quantity_base).to_integral_value(rounding=ROUND_FLOOR))
            mx = n if mx is None else min(mx, n)
            if qty < r.quantity_base and ing:
                missing.append(ing.name)
            items.append({"ingredient_id": str(r.ingredient_id), "ingredient_name": ing.name if ing else "?",
                          "quantity": qstr(r.quantity_base), "unit": ing.base_unit_code if ing else ""})
        cost_v = vnd(cost)
        out.append({"id": str(d.id), "name": d.name, "price_vnd": d.price_vnd, "recipe": items,
                    "ingredient_ids": [i["ingredient_id"] for i in items],
                    "cost_estimate_vnd": {"value": cost_v, "basis": "ESTIMATE"},
                    "gross_profit_estimate_vnd": d.price_vnd - cost_v,
                    "gross_margin_estimate": {"amount_vnd": d.price_vnd - cost_v,
                                              "percent": round((d.price_vnd - cost_v) / d.price_vnd * 100, 1) if d.price_vnd else 0,
                                              "basis": "ESTIMATE"},
                    "max_portions": mx or 0, "missing_ingredients": missing,
                    "uses_expiring_stock": any(uuid.UUID(i["ingredient_id"]) in soon for i in items)})
    return out


def create_dish(ctx: Ctx, d: dict) -> dict:
    s = ctx.session
    norm = normalize(d["name"])
    if s.execute(select(m.Dish.id).where(m.Dish.kitchen_id == ctx.kitchen_id, m.Dish.normalized_name == norm,
                                         m.Dish.deleted_at.is_(None))).first():
        raise ApiError(409, "DUPLICATE_NAME", "A dish with this name already exists")
    seen, items = set(), []
    for r in sorted(d["recipe"], key=lambda x: str(x["ingredient_id"])):
        if str(r["ingredient_id"]) in seen:
            raise ApiError(422, "VALIDATION_ERROR", "Duplicate ingredient in recipe")
        seen.add(str(r["ingredient_id"]))
        ing = catalog.get_ingredient(ctx, r["ingredient_id"], lock_share=True)
        try:
            q = convert_to_base(Decimal(str(r["quantity"])), r.get("unit") or ing.base_unit_code, ing.base_unit_code,
                                catalog.unit_map(s), catalog.conversions_for(ctx, ing.id))
        except UnitNotConvertible as e:
            raise ApiError(422, "UNIT_NOT_CONVERTIBLE", f"Cannot convert {e.from_unit} to {e.to_unit}")
        if q <= 0:
            raise ApiError(422, "VALIDATION_ERROR", "Recipe quantity must be positive")
        items.append((ing.id, q))
    dish = m.Dish(kitchen_id=ctx.kitchen_id, name=d["name"].strip(), normalized_name=norm, price_vnd=int(d["price_vnd"]))
    s.add(dish)
    s.flush()
    for iid, q in items:
        s.add(m.RecipeItem(kitchen_id=ctx.kitchen_id, dish_id=dish.id, ingredient_id=iid, quantity_base=q))
    s.flush()
    audit(ctx, "DISH_CREATED", "dish", dish.id, after={"name": dish.name})
    return next(x for x in dish_snapshots(ctx) if x["id"] == str(dish.id))


# ---------- settlement: the ONLY writer of cogs_vnd / consumption_status (6.3 s3.4) ----------
def settle_sale_lines(ctx: Ctx, line_ids) -> None:
    s = ctx.session
    s.flush()
    for lid in line_ids:
        cogs = s.execute(text(
            "SELECT COALESCE(-SUM(mv.value_vnd), 0) FROM stock_movements mv "
            "LEFT JOIN stock_movements o ON o.id = mv.reverses_movement_id "
            "WHERE mv.kitchen_id = :k AND mv.sale_line_id = :l AND COALESCE(o.type, mv.type) = 'SALE_CONSUMPTION'"),
            {"k": ctx.kitchen_id, "l": lid}).scalar_one()
        shorts = s.execute(select(m.StockShortage.status, m.StockShortage.resolution).where(
            m.StockShortage.kitchen_id == ctx.kitchen_id, m.StockShortage.sale_line_id == lid)).all()
        line = s.get(m.SaleLine, lid)
        line.cogs_vnd = int(cogs)
        line.consumption_status = consumption_status([Shortage(r.status == "OPEN", r.resolution) for r in shorts])
    s.flush()


# ---------- sales ----------
def record_sale(ctx: Ctx, business_date: date, lines: list[dict], source_document_id=None) -> dict:
    s = ctx.session
    if not lines:
        raise ApiError(422, "VALIDATION_ERROR", "A sale needs at least one line")
    ids = {l["dish_id"] for l in lines}
    dishes = {d.id: d for d in s.execute(select(m.Dish).where(
        m.Dish.kitchen_id == ctx.kitchen_id, m.Dish.id.in_(ids), m.Dish.deleted_at.is_(None))).scalars()}
    if len(dishes) != len(ids):
        raise ApiError(404, "NOT_FOUND", "A dish in the sale was not found")
    rec = _recipes(ctx, list(ids))
    st = catalog.get_settings_row(ctx)
    sale = m.Sale(kitchen_id=ctx.kitchen_id, business_date=business_date, source_document_id=source_document_id,
                  created_by=ctx.user_id)
    s.add(sale)
    s.flush()
    sale_lines, needs = [], {}
    for l in lines:
        d = dishes[l["dish_id"]]
        qty = int(l["quantity"])
        sl = m.SaleLine(kitchen_id=ctx.kitchen_id, sale_id=sale.id, dish_id=d.id, dish_name_snapshot=d.name, quantity=qty,
                        unit_price_snapshot_vnd=d.price_vnd, revenue_vnd=d.price_vnd * qty)
        s.add(sl)
        s.flush()
        sale_lines.append(sl)
        for r in rec.get(d.id, []):
            needs.setdefault(r.ingredient_id, []).append((sl, r.quantity_base * qty))
    # lock ingredients (share) in ascending id, then batches (update) per ingredient; Rev 6.3 s3.8 lock order
    ing_ids = sorted(needs, key=str)
    if ing_ids:
        s.execute(select(m.Ingredient.id).where(m.Ingredient.kitchen_id == ctx.kitchen_id, m.Ingredient.id.in_(ing_ids))
                  .order_by(m.Ingredient.id).with_for_update(read=True)).all()
    today = today_vn()
    shortages = []
    for iid in ing_ids:
        orm, views = inventory.lock_batches(ctx, iid, today, st.expired_batches_consumable)
        for sl, need in needs[iid]:
            _, short = inventory.consume_from(ctx, orm, views, need, "SALE_CONSUMPTION", business_date, sale_line_id=sl.id)
            if short > 0:
                sh = m.StockShortage(kitchen_id=ctx.kitchen_id, sale_line_id=sl.id, ingredient_id=iid, short_qty=round_qty(short))
                s.add(sh)
                shortages.append(sh)
    s.flush()
    settle_sale_lines(ctx, [sl.id for sl in sale_lines])
    audit(ctx, "SALE_RECORDED", "sale", sale.id, after={"lines": len(sale_lines)})
    return get_sale(ctx, sale.id)


def get_sale(ctx: Ctx, sale_id) -> dict:
    s = ctx.session
    sale = s.execute(select(m.Sale).where(m.Sale.kitchen_id == ctx.kitchen_id, m.Sale.id == sale_id)).scalar_one_or_none()
    if sale is None:
        raise ApiError(404, "NOT_FOUND", "Sale not found")
    lines = s.execute(select(m.SaleLine).where(m.SaleLine.kitchen_id == ctx.kitchen_id, m.SaleLine.sale_id == sale.id)).scalars().all()
    for l in lines:
        s.refresh(l)
    names = {i.id: (i.name, i.base_unit_code) for i in s.execute(select(m.Ingredient).where(m.Ingredient.kitchen_id == ctx.kitchen_id)).scalars()}
    shorts = s.execute(select(m.StockShortage).where(m.StockShortage.kitchen_id == ctx.kitchen_id,
                                                     m.StockShortage.sale_line_id.in_([l.id for l in lines]))).scalars().all()
    return {"id": str(sale.id), "business_date": sale.business_date.isoformat(),
            "revenue_vnd": sum(l.revenue_vnd for l in lines),
            "lines": [{"id": str(l.id), "dish_name": l.dish_name_snapshot, "quantity": l.quantity,
                       "unit_price_vnd": l.unit_price_snapshot_vnd, "revenue_vnd": l.revenue_vnd, "cogs_vnd": l.cogs_vnd,
                       "consumption_status": l.consumption_status, "origin": l.origin} for l in lines],
            "shortages": [shortage_out(x, names) for x in shorts]}


def list_sales(ctx: Ctx, limit: int, offset: int) -> tuple[list[dict], int | None]:
    s = ctx.session
    rows = s.execute(select(m.Sale).where(m.Sale.kitchen_id == ctx.kitchen_id)
                     .order_by(m.Sale.business_date.desc(), m.Sale.created_at.desc()).limit(limit + 1).offset(offset)).scalars().all()
    items = []
    for sale in rows[:limit]:
        lines = s.execute(select(m.SaleLine).where(m.SaleLine.kitchen_id == ctx.kitchen_id, m.SaleLine.sale_id == sale.id)).scalars().all()
        items.append({"id": str(sale.id), "business_date": sale.business_date.isoformat(),
                      "revenue_vnd": sum(l.revenue_vnd for l in lines), "line_count": len(lines),
                      "has_open_shortage": any(l.consumption_status == "PARTIAL" for l in lines)})
    return items, (offset + limit if len(rows) > limit else None)


# ---------- shortages (Option C) ----------
def shortage_out(x: m.StockShortage, names: dict) -> dict:
    nm, unit = names.get(x.ingredient_id, ("?", ""))
    return {"id": str(x.id), "sale_line_id": str(x.sale_line_id) if x.sale_line_id else None,
            "ingredient": {"id": str(x.ingredient_id), "name": nm}, "short_qty": qstr(x.short_qty), "unit": unit,
            "status": x.status, "resolution": x.resolution}


def list_shortages(ctx: Ctx, status: str | None) -> list[dict]:
    s = ctx.session
    q = select(m.StockShortage).where(m.StockShortage.kitchen_id == ctx.kitchen_id)
    if status:
        q = q.where(m.StockShortage.status == status)
    rows = s.execute(q.order_by(m.StockShortage.created_at.desc())).scalars().all()
    names = {i.id: (i.name, i.base_unit_code) for i in s.execute(select(m.Ingredient).where(m.Ingredient.kitchen_id == ctx.kitchen_id)).scalars()}
    out = []
    for x in rows:
        o = shortage_out(x, names)
        date_ = s.execute(select(m.Sale.business_date).join(m.SaleLine, (m.SaleLine.kitchen_id == m.Sale.kitchen_id) & (m.SaleLine.sale_id == m.Sale.id))
                          .where(m.SaleLine.id == x.sale_line_id)).scalar_one_or_none()
        o["business_date"] = date_.isoformat() if date_ else None
        out.append(o)
    return out


def resolve_shortage(ctx: Ctx, shortage_id, action: str, note: str | None) -> dict:
    s = ctx.session
    sh = s.execute(select(m.StockShortage).where(m.StockShortage.kitchen_id == ctx.kitchen_id,
                                                 m.StockShortage.id == shortage_id).with_for_update()).scalar_one_or_none()
    if sh is None:
        raise ApiError(404, "NOT_FOUND", "Shortage not found")
    if sh.status != "OPEN":
        raise ApiError(409, "SHORTAGE_ALREADY_RESOLVED", "This shortage is already resolved")
    if sh.sale_line_id is None:
        raise ApiError(501, "NOT_IMPLEMENTED", "Usage-slip shortages are deferred")
    ing = catalog.get_ingredient(ctx, sh.ingredient_id, lock_share=True, include_deleted=True)
    st, today = catalog.get_settings_row(ctx), today_vn()
    movements = []
    if action == "CONSUME_FROM_STOCK":
        orm, views = inventory.lock_batches(ctx, ing.id, today, st.expired_batches_consumable)
        if sum((v.remaining_qty for v in views), Decimal(0)) < sh.short_qty:
            raise ApiError(409, "INSUFFICIENT_STOCK", "Usable stock is still below the shortage")
        inventory.consume_from(ctx, orm, views, sh.short_qty, "SALE_CONSUMPTION", today,
                               sale_line_id=sh.sale_line_id, shortage_id=sh.id)
        sh.resolution = "CONSUMED_FROM_STOCK"
    elif action == "WAIVE":
        if not (note or "").strip():
            raise ApiError(422, "VALIDATION_ERROR", "A note is required to waive a shortage")
        last = s.execute(select(m.Batch).where(m.Batch.kitchen_id == ctx.kitchen_id, m.Batch.ingredient_id == ing.id)
                         .order_by(m.Batch.received_on.desc(), m.Batch.created_at.desc()).limit(1)).scalar_one_or_none()
        if last is not None:  # indicative estimate only; WAIVED never enters COGS (Rev 4 s2.F)
            sh.estimated_unit_cost, sh.estimate_batch_id = last.unit_cost, last.id
            sh.estimated_cost_vnd = vnd(sh.short_qty * last.unit_cost)
        sh.resolution, sh.resolution_note = "WAIVED", note.strip()
    elif action == "WRITE_OFF_ESTIMATED":
        raise ApiError(501, "NOT_IMPLEMENTED", "WRITE_OFF_ESTIMATED is a Stretch feature")
    else:
        raise ApiError(422, "VALIDATION_ERROR", "Unknown action")
    sh.status, sh.resolved_at, sh.resolved_by = "RESOLVED", func.now(), ctx.user_id
    s.flush()
    settle_sale_lines(ctx, [sh.sale_line_id])
    audit(ctx, "SHORTAGE_" + action, "shortage", sh.id, after={"qty": str(sh.short_qty)})
    s.refresh(sh)
    names = {ing.id: (ing.name, ing.base_unit_code)}
    return {"shortage": shortage_out(sh, names)}


# ---------- manual sales-report documents (D1/D3/D4/D6/D7, kind SALES_REPORT only) ----------
def _doc(ctx: Ctx, doc_id, lock: bool = False) -> m.Document:
    q = select(m.Document).where(m.Document.kitchen_id == ctx.kitchen_id, m.Document.id == doc_id)
    if lock:
        q = q.with_for_update()
    d = ctx.session.execute(q).scalar_one_or_none()
    if d is None:
        raise ApiError(404, "NOT_FOUND", "Document not found")
    return d


def document_out(ctx: Ctx, doc: m.Document) -> dict:
    s = ctx.session
    lines = s.execute(select(m.DocumentLine).where(m.DocumentLine.kitchen_id == ctx.kitchen_id,
                                                   m.DocumentLine.document_id == doc.id).order_by(m.DocumentLine.line_no)).scalars().all()
    dn = {d.id: d.name for d in s.execute(select(m.Dish).where(m.Dish.kitchen_id == ctx.kitchen_id)).scalars()}
    return {"id": str(doc.id), "kind": doc.kind, "source_format": doc.source_format, "status": doc.status,
            "ocr_status": doc.ocr_status, "business_date": doc.business_date.isoformat(),
            "lines": [{"id": str(l.id), "line_no": l.line_no, "dish": {"id": str(l.dish_id), "name": dn.get(l.dish_id, "?")} if l.dish_id else None,
                       "quantity": qstr(l.quantity) if l.quantity is not None else None, "is_selected": l.is_selected,
                       "flags": list(l.flags)} for l in lines],
            "summary": {"line_count": len(lines), "total_value_vnd": None,
                        "blocking_issues": [] if lines else ["NO_LINES"]}}


def create_document(ctx: Ctx, kind: str, business_date: date) -> dict:
    if kind != "SALES_REPORT":
        raise ApiError(501, "NOT_IMPLEMENTED", "Only manual SALES_REPORT documents are implemented; use POST /batches for receipts")
    st, today = catalog.get_settings_row(ctx), today_vn()
    if business_date > today or business_date < today - timedelta(days=st.backdate_limit_days):
        raise ApiError(422, "VALIDATION_ERROR", f"business_date must be within the last {st.backdate_limit_days} days and not in the future")
    doc = m.Document(kitchen_id=ctx.kitchen_id, kind=kind, source_format="MANUAL", status="DRAFT",
                     business_date=business_date, ocr_status="NOT_APPLICABLE", created_by=ctx.user_id)
    ctx.session.add(doc)
    ctx.session.flush()
    return document_out(ctx, doc)


def get_document(ctx: Ctx, doc_id) -> dict:
    return document_out(ctx, _doc(ctx, doc_id))


def add_line(ctx: Ctx, doc_id, dish_id, quantity: int) -> dict:
    s = ctx.session
    doc = _doc(ctx, doc_id, lock=True)
    if doc.status != "DRAFT":
        raise ApiError(409, "DOCUMENT_ALREADY_CONFIRMED", "Only draft documents can be edited")
    if s.execute(select(m.Dish.id).where(m.Dish.kitchen_id == ctx.kitchen_id, m.Dish.id == dish_id, m.Dish.deleted_at.is_(None))).first() is None:
        raise ApiError(404, "NOT_FOUND", "Dish not found")
    n = s.execute(select(func.coalesce(func.max(m.DocumentLine.line_no), 0)).where(m.DocumentLine.document_id == doc.id)).scalar_one()
    s.add(m.DocumentLine(kitchen_id=ctx.kitchen_id, document_id=doc.id, line_no=n + 1, dish_id=dish_id, quantity=Decimal(quantity)))
    s.flush()
    return document_out(ctx, doc)


def delete_line(ctx: Ctx, doc_id, line_id) -> None:
    doc = _doc(ctx, doc_id, lock=True)
    if doc.status != "DRAFT":
        raise ApiError(409, "DOCUMENT_ALREADY_CONFIRMED", "Only draft documents can be edited")
    ln = ctx.session.execute(select(m.DocumentLine).where(m.DocumentLine.kitchen_id == ctx.kitchen_id,
                                                          m.DocumentLine.document_id == doc.id, m.DocumentLine.id == line_id)).scalar_one_or_none()
    if ln is None:
        raise ApiError(404, "NOT_FOUND", "Line not found")
    ctx.session.delete(ln)
    ctx.session.flush()


def confirm_document(ctx: Ctx, doc_id) -> dict:
    s = ctx.session
    doc = _doc(ctx, doc_id, lock=True)
    if doc.status != "DRAFT":
        raise ApiError(409, "DOCUMENT_ALREADY_CONFIRMED", "This document is not a draft")
    lines = s.execute(select(m.DocumentLine).where(m.DocumentLine.kitchen_id == ctx.kitchen_id, m.DocumentLine.document_id == doc.id,
                                                   m.DocumentLine.is_selected.is_(True)).order_by(m.DocumentLine.line_no)).scalars().all()
    ok = [l for l in lines if l.dish_id and l.quantity and l.quantity > 0]
    if not ok or len(ok) != len(lines):
        raise ApiError(422, "DOCUMENT_NOT_READY", "Every selected line needs a dish and a positive quantity", )
    sale = record_sale(ctx, doc.business_date, [{"dish_id": l.dish_id, "quantity": int(l.quantity)} for l in ok], source_document_id=doc.id)
    doc.status, doc.confirmed_at = "CONFIRMED", func.now()
    s.flush()
    audit(ctx, "DOCUMENT_CONFIRMED", "document", doc.id)
    return {"document_id": str(doc.id), "status": "CONFIRMED", "sales_recorded": 1, "revenue_vnd": sale["revenue_vnd"],
            "consumption": {"fully_covered_lines": sum(1 for l in sale["lines"] if l["consumption_status"] == "FULL"),
                            "partial_lines": sum(1 for l in sale["lines"] if l["consumption_status"] == "PARTIAL")},
            "sale_id": sale["id"], "shortages": sale["shortages"]}
