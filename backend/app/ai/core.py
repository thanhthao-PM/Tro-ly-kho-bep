"""Provider-independent assistant core (Rev 3 II.8). Pure: no database, no framework.
The provider PLANS tool calls and COMPOSES a template whose numbers are placeholders; figures only ever come from
Facts produced by deterministic backend tools. A validator rejects any stray digit or unknown placeholder."""
import re
from dataclasses import dataclass, field
from typing import Protocol

from app.domain.text import search_name

PLACEHOLDER = re.compile(r"\{\{(fact|label):([A-Za-z0-9_]+)\}\}")


@dataclass
class Fact:
    id: str
    tool: str
    label: str
    value: str
    unit: str = ""
    as_of: str = ""


@dataclass
class Recommendation:
    text: str
    assumptions: list[str]
    basis: str = "VERIFIED_FACT"          # or ESTIMATE


@dataclass
class Composed:
    answer_template: str
    recommendations: list[Recommendation] = field(default_factory=list)
    data_gaps: list[str] = field(default_factory=list)
    proposed_actions: list[dict] = field(default_factory=list)


@dataclass
class ToolResult:
    tool: str
    facts: list[Fact] = field(default_factory=list)
    data_gaps: list[str] = field(default_factory=list)
    actions: list[dict] = field(default_factory=list)
    notes: dict = field(default_factory=dict)       # small deterministic extras (e.g. suggested dish names)


class LLMProvider(Protocol):
    name: str
    def plan(self, question: str, history: list[dict]) -> list[dict]: ...
    def compose(self, question: str, results: list[ToolResult]) -> Composed: ...


INTENTS = [  # (tool, keywords on accent-stripped text)
    ("list_expiring", ["het han", "sap het", "han dung", "xu ly", "can dung truoc", "expir", "near expiry", "gan het han"]),
    ("get_stock", ["con bao nhieu", "ton kho", "con lai", "ton bao nhieu", "how much", "stock of", "con khong"]),
    ("get_cookable_dishes", ["nau gi", "nau duoc", "mon nao", "co the nau", "cook", "du nguyen lieu"]),
    ("get_dish_margins", ["mon nao lai", "lai nhat", "bien loi nhuan", "margin"]),
    ("get_period_summary", ["doanh thu", "loi nhuan", "bao cao", "revenue", "profit", "tuan nay", "thang nay"]),
    ("get_waste_summary", ["bo nhieu", "lang phi", "hao hut", "bo di", "waste"]),
    ("get_replenishment_suggestions", ["nen nhap", "can nhap", "can mua", "nhap them", "mua them", "nhap hang", "replen", "order"]),
]


class RuleBasedProvider:
    """Deterministic keyword/intent provider. Default and fallback; needs no API key."""
    name = "rule_based"

    def plan(self, question: str, history: list[dict]) -> list[dict]:
        q = search_name(question)
        calls, seen = [], set()
        for tool, kws in INTENTS:
            if any(k in q for k in kws) and tool not in seen:
                seen.add(tool)
                calls.append({"tool": tool, "args": {"question": question} if tool == "get_stock" else {}})
        if "get_dish_margins" in seen and "get_period_summary" in seen:   # "lợi nhuận món nào" means dish margins
            calls = [c for c in calls if c["tool"] != "get_period_summary"]
        return calls

    def compose(self, question: str, results: list[ToolResult]) -> Composed:
        lines, recs, gaps, actions = [], [], [], []
        for r in results:
            gaps += r.data_gaps
            actions += r.actions
            if not r.facts:
                continue
            lines.append(HEADERS.get(r.tool, ""))
            lines += [f"- {{{{label:{f.id}}}}}: {{{{fact:{f.id}}}}}" for f in r.facts]
            recs += _recommendations(r)
        if not lines:
            gaps.append("Mình chưa hiểu câu hỏi hoặc chưa có dữ liệu để trả lời.")
        return Composed("\n".join(lines), recs, gaps, actions)


HEADERS = {
    "list_expiring": "Các lô cần ưu tiên (đã hết hạn hoặc sắp hết hạn):",
    "get_stock": "Tồn kho hiện tại:",
    "get_cookable_dishes": "Món có thể nấu với kho hiện tại:",
    "get_dish_margins": "Lãi gộp ước tính mỗi phần (ước tính, không phải số thực tế):",
    "get_period_summary": "Tổng hợp kỳ gần nhất:",
    "get_waste_summary": "Hao hụt theo mặt hàng:",
    "get_replenishment_suggestions": "Gợi ý nhập hàng (ước tính):",
}


def _recommendations(r: ToolResult) -> list[Recommendation]:
    if r.tool == "list_expiring" and r.notes.get("suggested"):
        return [Recommendation("Ưu tiên nấu: " + ", ".join(r.notes["suggested"]) + ". Chỉ dùng lô chưa hết hạn.",
                               ["Chỉ các lô còn hạn và dùng được mới được gợi ý", "Số phần tính theo tồn kho dùng được hiện tại"], "ESTIMATE")]
    if r.tool == "list_expiring" and any(f.value for f in r.facts):
        return [Recommendation("Lô đã hết hạn chỉ nên ghi nhận bỏ đi theo chính sách hiện hành; không dùng để nấu.",
                               ["Chính sách hàng hết hạn đang là giá trị tạm, chờ phê duyệt"], "VERIFIED_FACT")]
    if r.tool == "get_replenishment_suggestions":
        return [Recommendation("Số lượng gợi ý dựa trên tiêu thụ trung bình và số ngày tồn mục tiêu.",
                               list(r.notes.get("assumptions", [])), "ESTIMATE")]
    return []


def validate(composed: Composed, facts: list[Fact]) -> list[str]:
    """Returns violations. Every placeholder must reference a returned fact; no digits outside placeholders."""
    ids = {f.id for f in facts}
    errs = [f"unknown placeholder {m.group(0)}" for m in PLACEHOLDER.finditer(composed.answer_template) if m.group(2) not in ids]
    stripped = PLACEHOLDER.sub("", composed.answer_template)
    if re.search(r"\d", stripped):
        errs.append("digits outside placeholders")
    for rec in composed.recommendations:
        if not rec.assumptions or rec.basis not in ("VERIFIED_FACT", "ESTIMATE"):
            errs.append("recommendation without basis or assumptions")
        if re.search(r"\d", rec.text):
            errs.append("digits in recommendation text")
    return errs


def render(template: str, facts: list[Fact]) -> str:
    by = {f.id: f for f in facts}
    def sub(mo):
        f = by[mo.group(2)]
        return f.label if mo.group(1) == "label" else (f"{f.value} {f.unit}".strip())
    return PLACEHOLDER.sub(sub, template)


def render_plain(facts: list[Fact]) -> str:
    return "\n".join(f"- {f.label}: {f.value} {f.unit}".rstrip() for f in facts)
