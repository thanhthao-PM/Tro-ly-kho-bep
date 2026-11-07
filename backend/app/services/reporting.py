"""R1 period summary (Rev 5 s2.3 formulas; D7 policy items are PLACEHOLDERS) and RS1 replenishment (Rev 5 s2.4).
Everything reads ledger_effective / ledger rows, never the sale_lines cache for costs (6.3 s3.4)."""
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select, text

from app.core.errors import ApiError
from app.db import models as m
from app.domain.expiry import today_vn
from app.domain.ledger_rules import Shortage, cost_status, observation_window
from app.domain.replenishment import ReplenishmentInput, classify
from app.services import catalog, inventory
from app.services.common import Ctx, cstr, qstr

LABEL = lambda v: {"value": v, "basis": "ACTUAL"}  # noqa: E731


def _period(ctx: Ctx, f: date, t: date) -> dict:
    s, k = ctx.session, ctx.kitchen_id
    p = {"k": k, "f": f, "t": t}
    cat = {r[0]: int(r[1]) for r in s.execute(text(
        "SELECT category, COALESCE(SUM(value_vnd), 0) FROM ledger_effective "
        "WHERE kitchen_id = :k AND attribution_date BETWEEN :f AND :t GROUP BY category"), p)}
    rev, portions = s.execute(text(
        "SELECT COALESCE(SUM(sl.revenue_vnd), 0), COALESCE(SUM(sl.quantity), 0) FROM sale_lines sl "
        "JOIN sales sa ON sa.kitchen_id = sl.kitchen_id AND sa.id = sl.sale_id "
        "WHERE sa.kitchen_id = :k AND sa.business_date BETWEEN :f AND :t"), p).one()
    sell_rev = s.execute(text(
        "SELECT COALESCE(SUM(revenue_vnd), 0) FROM disposals WHERE kitchen_id = :k AND type = 'SELLOFF' "
        "AND occurred_on BETWEEN :f AND :t"), p).scalar_one()
    shorts = s.execute(text(
        "SELECT ss.status, ss.resolution, COALESCE(ss.estimated_cost_vnd, 0) FROM stock_shortages ss "
        "JOIN sale_lines sl ON sl.kitchen_id = ss.kitchen_id AND sl.id = ss.sale_line_id "
        "JOIN sales sa ON sa.kitchen_id = sl.kitchen_id AND sa.id = sl.sale_id "
        "WHERE ss.kitchen_id = :k AND sa.business_date BETWEEN :f AND :t"), p).all()
    sh = [Shortage(r[0] == "OPEN", r[1]) for r in shorts]
    cs = cost_status(sh)
    est = sum(int(r[2]) for r in shorts if r[0] != "OPEN" and r[1] == "WRITTEN_OFF_ESTIMATED")
    cogs = -cat.get("SALE_CONSUMPTION", 0)
    sell_cost = -cat.get("SELLOFF", 0)
    waste, donation = -cat.get("WASTE", 0), -cat.get("DONATION", 0)
    adj = cat.get("ADJUSTMENT_IN", 0) + cat.get("ADJUSTMENT_OUT", 0)
    gp_ex = int(rev) - cogs
    gp_in = gp_ex - est
    sell_margin = int(sell_rev) - sell_cost
    tot_ex, tot_in = gp_ex + sell_margin, gp_in + sell_margin
    return {
        "sales": {"revenue_vnd": LABEL(int(rev)), "cogs": {"actual_vnd": LABEL(cogs), "estimated_vnd": {"value": est, "basis": "ESTIMATE"}},
                  "gross_profit": {"excluding_estimates_vnd": gp_ex, "including_estimates_vnd": {"value": gp_in, "basis": "ESTIMATE"}},
                  "portions_sold": int(portions)},
        "selloff": {"revenue_vnd": LABEL(int(sell_rev)), "cost_vnd": LABEL(sell_cost), "margin_vnd": LABEL(sell_margin)},
        "totals": {"revenue_vnd": LABEL(int(rev) + int(sell_rev)),
                   "gross_profit": {"excluding_estimates_vnd": tot_ex, "including_estimates_vnd": {"value": tot_in, "basis": "ESTIMATE"}}},
        "waste_cost_vnd": LABEL(waste), "donation_cost_vnd": LABEL(donation), "adjustment_net_vnd": LABEL(adj),
        "shortages": {"open_count": cs.open_count, "written_off_estimated_count": cs.written_off_estimated_count,
                      "waived_count": cs.waived_count},
        "cogs_status": {"has_open_shortages": cs.has_open_shortages, "all_actual": cs.all_actual},
        "result_after_ingredient_loss": {
            "excluding_estimates_vnd": tot_ex - waste - donation + adj,
            "including_estimates_vnd": {"value": tot_in - waste - donation + adj, "basis": "ESTIMATE"},
            "policy_status": "PLACEHOLDER_PENDING_D7"},
        "_ex": tot_ex}


def summary(ctx: Ctx, f: date, t: date) -> dict:
    if t < f:
        raise ApiError(422, "VALIDATION_ERROR", "'to' must not be before 'from'")
    cur = _period(ctx, f, t)
    n = (t - f).days + 1
    pf, pt = f - timedelta(days=n), f - timedelta(days=1)
    prev = _period(ctx, pf, pt)
    cur["period"] = {"from": f.isoformat(), "to": t.isoformat()}
    cur["comparison"] = {
        "previous_period": {"from": pf.isoformat(), "to": pt.isoformat(), "revenue_vnd": prev["totals"]["revenue_vnd"],
                            "gross_profit_excluding_estimates_vnd": prev["_ex"]},
        "note": "Previous period of equal length. Past periods can change when shortages are resolved late."}
    del cur["_ex"]
    return cur


def replenishment(ctx: Ctx) -> dict:
    s, st, today = ctx.session, catalog.get_settings_row(ctx), today_vn()
    stock = inventory.usable_stock_map(ctx)
    ings = s.execute(select(m.Ingredient).where(m.Ingredient.kitchen_id == ctx.kitchen_id, m.Ingredient.deleted_at.is_(None))
                     .order_by(m.Ingredient.normalized_name)).scalars().all()
    hist = {r[0]: r[1] for r in s.execute(text(
        "SELECT ingredient_id, MIN(attribution_date) FROM ledger_effective WHERE kitchen_id = :k GROUP BY ingredient_id"),
        {"k": ctx.kitchen_id})}
    items, insufficient, no_recent = [], [], []
    for ing in ings:
        usable = stock.get(ing.id, (Decimal(0), Decimal(0)))[0]
        win = observation_window(hist.get(ing.id), today, st.consumption_window_days)
        cons = Decimal(0)
        if win.window_start is not None:
            cons = s.execute(text(
                "SELECT COALESCE(-SUM(qty_delta), 0) FROM ledger_effective WHERE kitchen_id = :k AND ingredient_id = :i "
                "AND category IN ('SALE_CONSUMPTION', 'USAGE_CONSUMPTION') AND attribution_date BETWEEN :f AND :t"),
                {"k": ctx.kitchen_id, "i": ing.id, "f": win.window_start, "t": win.window_end}).scalar_one()
        res = classify(ReplenishmentInput(str(ing.id), ing.name, ing.base_unit_code, usable, ing.min_stock_qty, ing.order_step,
                                          Decimal(cons), win, st.target_coverage_days, st.min_history_days))
        ref = {"id": str(ing.id), "name": ing.name}
        for r in res:
            if r.kind == "item":
                items.append({"ingredient": ref, "usable_qty": qstr(usable), "unit": ing.base_unit_code,
                              "observation": {"from": win.window_start.isoformat(), "to": win.window_end.isoformat(),
                                              "observed_days": win.observed_days} if win.window_start else None,
                              "consumption_total": qstr(cons) if win.observed_days else None,
                              "avg_daily_consumption": qstr(r.avg_daily) if r.avg_daily is not None else None,
                              "days_of_cover": f"{r.days_of_cover:.2f}" if r.days_of_cover is not None else None,
                              "rule": r.rule, "raw_order_qty": qstr(r.raw_order_qty),
                              "order_step": qstr(ing.order_step) if ing.order_step else None,
                              "suggested_order_qty": qstr(r.suggested_order_qty), "basis": "ESTIMATE",
                              "assumptions": ["Average of net sale/usage consumption over complete days in the window",
                                              "Stock-outs and unmet demand lower observed consumption",
                                              "Weekday patterns are ignored", "Parameters are placeholders pending approval"]})
            elif r.kind == "insufficient_data":
                insufficient.append({"ingredient": ref, "reason": r.reason, "observed_days": win.observed_days,
                                     "coverage_rule_skipped": True})
            elif r.kind == "no_recent_consumption":
                no_recent.append({"ingredient": ref, "usable_qty": qstr(usable), "unit": ing.base_unit_code})
    return {"as_of": today.isoformat(),
            "parameters": {"target_coverage_days": st.target_coverage_days, "window_days": st.consumption_window_days,
                           "min_history_days": st.min_history_days},
            "items": items, "insufficient_data": insufficient, "no_recent_consumption": no_recent}
