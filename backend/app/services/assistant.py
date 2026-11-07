"""Assistant orchestration: plan -> read-only tools (kitchen from the verified JWT, never from tool args) -> compose ->
validate -> render. No write tools. AI output cannot change the database."""
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select, text

from app.ai.core import Composed, Fact, RuleBasedProvider, ToolResult, render, render_plain, validate
from app.db import models as m
from app.domain.expiry import today_vn
from app.domain.text import search_name
from app.services import catalog, inventory, reporting, sales
from app.services.common import Ctx, audit, qstr


def _fid(prefix: str, n: int) -> str:
    return f"{prefix}{n}"


def tool_get_stock(ctx: Ctx, question: str = "") -> ToolResult:
    q, today = search_name(question), today_vn().isoformat()
    ings = ctx.session.execute(select(m.Ingredient).where(m.Ingredient.kitchen_id == ctx.kitchen_id, m.Ingredient.deleted_at.is_(None))).scalars().all()
    aliases = ctx.session.execute(select(m.IngredientAlias).where(m.IngredientAlias.kitchen_id == ctx.kitchen_id)).scalars().all()
    amap = {}
    for a in aliases:
        amap.setdefault(a.ingredient_id, []).append(a.alias)
    hits = [i for i in ings if search_name(i.name) in q or any(search_name(a) in q for a in amap.get(i.id, []))]
    r = ToolResult("get_stock")
    if not hits:
        r.data_gaps.append("Không nhận ra mặt hàng nào trong câu hỏi.")
        return r
    for n, ing in enumerate(hits[:5], 1):
        b = inventory.batches_of(ctx, ing.id)
        r.facts.append(Fact(_fid("S", n), "get_stock", ing.name, b["total_remaining"], ing.base_unit_code, today))
        for j, x in enumerate(b["batches"][:3], 1):
            r.facts.append(Fact(_fid(f"S{n}B", j), "get_stock", f"  {ing.name}, lô nhập {x['received_on']}, hạn {x['expiry_date'] or 'không có'}",
                                x["remaining_qty"], ing.base_unit_code, today))
    return r


def tool_list_expiring(ctx: Ctx) -> ToolResult:
    data = inventory.expiring(ctx)
    r = ToolResult("list_expiring")
    names = []
    for n, it in enumerate(data["items"][:8], 1):
        b = it["batch"]
        tag = "ĐÃ HẾT HẠN" if it["status"] == "EXPIRED" else "sắp hết hạn"
        r.facts.append(Fact(_fid("E", n), "list_expiring", f"{b['ingredient_name']} ({tag}, hạn {b['expiry_date']})",
                            b["remaining_qty"], b["unit"], data["as_of"]))
        r.actions.append({"type": "OPEN_EXPIRING_BATCH", "target_id": b["id"], "label": f"Xử lý {b['ingredient_name']}"})
        if it["status"] == "EXPIRES_SOON":
            names += [d["name"] for d in it["suggested_dishes"][:2]]
    r.notes["suggested"] = list(dict.fromkeys(names))[:4]
    if not data["items"]:
        r.data_gaps.append("Không có lô nào đã hết hạn hoặc sắp hết hạn.")
    return r


def tool_get_cookable_dishes(ctx: Ctx) -> ToolResult:
    r = ToolResult("get_cookable_dishes")
    ds = [d for d in sales.dish_snapshots(ctx) if d["max_portions"] > 0]
    ds.sort(key=lambda d: (-int(d["uses_expiring_stock"]), -d["gross_profit_estimate_vnd"]))
    for n, d in enumerate(ds[:8], 1):
        r.facts.append(Fact(_fid("C", n), "get_cookable_dishes", d["name"], str(d["max_portions"]), "phần tối đa", today_vn().isoformat()))
        r.actions.append({"type": "OPEN_DISH", "target_id": d["id"], "label": d["name"]})
    if not ds:
        r.data_gaps.append("Kho hiện chưa đủ nguyên liệu cho món nào.")
    return r


def tool_get_dish_margins(ctx: Ctx) -> ToolResult:
    r = ToolResult("get_dish_margins")
    ds = sorted(sales.dish_snapshots(ctx), key=lambda d: -d["gross_profit_estimate_vnd"])
    for n, d in enumerate(ds[:6], 1):
        r.facts.append(Fact(_fid("M", n), "get_dish_margins", d["name"], f"{d['gross_profit_estimate_vnd']:,}".replace(",", "."), "đ/phần (ước tính)"))
    if not ds:
        r.data_gaps.append("Thực đơn đang trống.")
    return r


def tool_get_period_summary(ctx: Ctx, days: int = 7) -> ToolResult:
    t = today_vn()
    s = reporting.summary(ctx, t - timedelta(days=days - 1), t)
    r = ToolResult("get_period_summary")
    fm = lambda v: f"{v:,}".replace(",", ".")  # noqa: E731
    asof = t.isoformat()
    r.facts = [
        Fact("P1", "get_period_summary", f"Doanh thu {days} ngày gần nhất", fm(s["totals"]["revenue_vnd"]["value"]), "đ", asof),
        Fact("P2", "get_period_summary", "Giá vốn thực tế bán hàng", fm(s["sales"]["cogs"]["actual_vnd"]["value"]), "đ", asof),
        Fact("P3", "get_period_summary", "Hao hụt do bỏ đi", fm(s["waste_cost_vnd"]["value"]), "đ", asof)]
    if s["cogs_status"]["has_open_shortages"]:
        r.data_gaps.append("Còn thiếu hụt chưa xử lý nên giá vốn đang bị thấp hơn thực tế.")
    if not s["cogs_status"]["all_actual"]:
        r.data_gaps.append("Có khoản chi phí ước tính hoặc bỏ qua; xem nhãn ESTIMATE trong báo cáo.")
    return r


def tool_get_waste_summary(ctx: Ctx, days: int = 30) -> ToolResult:
    t = today_vn()
    rows = ctx.session.execute(text(
        "SELECT i.name, COALESCE(-SUM(le.value_vnd), 0) c FROM ledger_effective le "
        "JOIN ingredients i ON i.kitchen_id = le.kitchen_id AND i.id = le.ingredient_id "
        "WHERE le.kitchen_id = :k AND le.category = 'WASTE' AND le.attribution_date BETWEEN :f AND :t "
        "GROUP BY i.name ORDER BY c DESC LIMIT 5"), {"k": ctx.kitchen_id, "f": t - timedelta(days=days - 1), "t": t}).all()
    r = ToolResult("get_waste_summary")
    for n, (name, cost) in enumerate(rows, 1):
        r.facts.append(Fact(_fid("W", n), "get_waste_summary", name, f"{int(cost):,}".replace(",", "."), "đ", t.isoformat()))
    if not rows:
        r.data_gaps.append("Chưa có dữ liệu bỏ đi trong 30 ngày gần nhất.")
    return r


def tool_get_replenishment(ctx: Ctx) -> ToolResult:
    data = reporting.replenishment(ctx)
    r = ToolResult("get_replenishment_suggestions")
    for n, it in enumerate(data["items"][:8], 1):
        r.facts.append(Fact(_fid("R", n), "get_replenishment_suggestions", f"{it['ingredient']['name']} (quy tắc {it['rule']})",
                            it["suggested_order_qty"], it["unit"], data["as_of"]))
        r.actions.append({"type": "OPEN_REPLENISHMENT", "target_id": it["ingredient"]["id"], "label": it["ingredient"]["name"]})
        r.notes["assumptions"] = it["assumptions"]
    for x in data["insufficient_data"][:3]:
        r.data_gaps.append(f"{x['ingredient']['name']}: chưa đủ lịch sử tiêu thụ để tính theo ngày tồn.")
    if not data["items"]:
        r.data_gaps.append("Hiện chưa có mặt hàng nào cần nhập thêm theo quy tắc.")
    return r


TOOLS = {"get_stock": tool_get_stock, "list_expiring": tool_list_expiring, "get_cookable_dishes": tool_get_cookable_dishes,
         "get_dish_margins": tool_get_dish_margins, "get_period_summary": tool_get_period_summary,
         "get_waste_summary": tool_get_waste_summary, "get_replenishment_suggestions": tool_get_replenishment}


def answer(ctx: Ctx, message: str, history: list[dict] | None = None) -> dict:
    provider = RuleBasedProvider()       # external providers (D24) would plug in here and fall back to this one
    calls = provider.plan(message, history or [])
    results = [TOOLS[c["tool"]](ctx, **c["args"]) for c in calls if c["tool"] in TOOLS]
    facts = [f for r in results for f in r.facts]
    composed: Composed = provider.compose(message, results)
    errs = validate(composed, facts)
    if errs:  # deterministic fallback: plain facts, no free text
        text_out = render_plain(facts) or "Không có dữ liệu để trả lời."
        composed.recommendations = []
    else:
        text_out = render(composed.answer_template, facts)
    gaps = list(composed.data_gaps) + (["Câu trả lời mẫu bị từ chối khi kiểm tra; hiển thị dữ liệu thô."] if errs else [])
    audit(ctx, "ASSISTANT_QUERY", "assistant", "n/a",
          after={"tools": [c["tool"] for c in calls], "provider": provider.name, "violations": errs, "question": message[:200]})
    return {"answer_text": text_out or "\n".join(gaps),
            "facts": [{"id": f.id, "tool": f.tool, "label": f.label.strip(), "value": f.value, "unit": f.unit, "as_of": f.as_of} for f in facts],
            "recommendations": [{"text": r.text, "assumptions": r.assumptions, "basis": r.basis} for r in composed.recommendations],
            "data_gaps": gaps, "proposed_actions": composed.proposed_actions or [a for r in results for a in r.actions][:6],
            "provider": provider.name, "request_id": ctx.request_id}
