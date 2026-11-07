from app.ai.core import Composed, Fact, Recommendation, RuleBasedProvider, ToolResult, render, render_plain, validate


def tools(q):
    return [c["tool"] for c in RuleBasedProvider().plan(q, [])]


def test_plan_vietnamese_intents():
    assert "list_expiring" in tools("Hôm nay nên xử lý gì trước?")
    assert tools("Thịt ba rọi còn bao nhiêu?") == ["get_stock"]
    assert "get_cookable_dishes" in tools("Kho còn đủ nấu gì?") or "get_stock" in tools("Kho còn đủ nấu gì?")
    assert tools("Doanh thu tuần này thế nào?") == ["get_period_summary"]
    assert "get_waste_summary" in tools("Đồ nào bỏ nhiều nhất?")
    assert "get_replenishment_suggestions" in tools("Tuần này cần nhập thêm gì?")


def test_plan_unknown_question_calls_nothing():
    assert tools("kể chuyện cười đi") == []


def test_compose_validate_render_roundtrip():
    f = [Fact("E1", "list_expiring", "Cà chua (hạn 03/11)", "1.500", "kg")]
    c = RuleBasedProvider().compose("x", [ToolResult("list_expiring", f)])
    assert validate(c, f) == []
    out = render(c.answer_template, f)
    assert "1.500 kg" in out and "Cà chua (hạn 03/11)" in out


def test_validator_rejects_fabricated_numbers_and_unknown_facts():
    f = [Fact("A1", "t", "x", "5", "kg")]
    assert "digits outside placeholders" in validate(Composed("Còn 5 kg {{fact:A1}}"), f)
    assert any("unknown placeholder" in e for e in validate(Composed("{{fact:ZZ}}"), f))
    bad = Composed("{{fact:A1}}", [Recommendation("mua", [], "ESTIMATE")])
    assert "recommendation without basis or assumptions" in validate(bad, f)


def test_plain_fallback_contains_only_facts():
    assert render_plain([Fact("A1", "t", "Gạo", "10.000", "kg")]) == "- Gạo: 10.000 kg"
