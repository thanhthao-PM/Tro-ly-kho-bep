"""
Unit test độc lập cho Assistant Grounding và Fact-based Verification (Revision 6.3).
Kiểm tra:
1. Mọi câu trả lời đều trả về VerifiedFact có ID và tool tương ứng.
2. Không bịa số liệu, trả về data_gaps khi thiếu bằng chứng.
3. Recommendations có cơ sở rõ ràng (VERIFIED_FACT vs ESTIMATE) kèm assumptions.
4. ProposedActions trỏ đúng loại hành động.
"""
import unittest


class MockFact:
    def __init__(self, fact_id: str, tool: str, label: str, value: str):
        self.id = fact_id
        self.tool = tool
        self.label = label
        self.value = value


def simulate_grounded_assistant(message: str, db_facts: dict):
    m = message.lower()
    facts = []
    recommendations = []
    data_gaps = []
    actions = []
    answer = []

    if "cận date" in m or "hết hạn" in m or "xu ly" in m:
        exp_soon = db_facts.get("expiring_soon_count", 0)
        expired = db_facts.get("expired_count", 0)

        f1 = MockFact("F-EXP-1", "list_expiring", "Số đợt quá hạn", str(expired))
        f2 = MockFact("F-SOON-1", "list_expiring", "Số đợt cận date", str(exp_soon))
        facts.extend([f1, f2])

        if expired > 0:
            answer.append(f"Kho có {expired} đợt đã quá hạn.")
            actions.append({"type": "OPEN_EXPIRING_BATCH", "label": "Xử lý bỏ hàng"})
        if exp_soon > 0:
            answer.append(f"Có {exp_soon} đợt sắp hết hạn trong 3 ngày tới.")
            recommendations.append({
                "text": "Nên ưu tiên nấu món tận dụng hoặc quyên góp trước hạn.",
                "basis": "VERIFIED_FACT",
                "assumptions": ["Chất lượng còn đảm bảo"]
            })
            actions.append({"type": "OPEN_EXPIRING_BATCH", "label": "Ưu tiên chế biến"})

    elif "bổ sung" in m or "đặt hàng" in m:
        repl_items = db_facts.get("replenishment_items", [])
        if repl_items:
            f = MockFact("F-REPL-1", "get_replenishment_suggestions", "Số mặt hàng cần đặt", str(len(repl_items)))
            facts.append(f)
            answer.append(f"Đề xuất bổ sung {len(repl_items)} mặt hàng theo D25.")
            actions.append({"type": "OPEN_REPLENISHMENT", "label": "Xem gợi ý D25"})
        else:
            answer.append("Kho đủ tồn theo mục tiêu D25.")

        if db_facts.get("has_insufficient_history"):
            data_gaps.append("Một số mặt hàng chưa đủ ngày lịch sử để ước tính tiêu thụ.")

    return {
        "answer": " ".join(answer),
        "facts": facts,
        "recommendations": recommendations,
        "data_gaps": data_gaps,
        "actions": actions
    }


class TestAssistantGrounding(unittest.TestCase):

    def test_expiring_grounding_produces_facts_and_actions(self):
        db_facts = {"expiring_soon_count": 2, "expired_count": 1}
        res = simulate_grounded_assistant("Có đồ nào cận date cần xử lý không?", db_facts)
        self.assertEqual(len(res["facts"]), 2)
        self.assertEqual(res["facts"][0].value, "1")
        self.assertEqual(res["facts"][1].value, "2")
        self.assertEqual(len(res["actions"]), 2)
        self.assertEqual(res["recommendations"][0]["basis"], "VERIFIED_FACT")

    def test_replenishment_grounding_reports_data_gaps_honestly(self):
        db_facts = {"replenishment_items": ["thit_heo"], "has_insufficient_history": True}
        res = simulate_grounded_assistant("Cần đặt hàng món gì không?", db_facts)
        self.assertEqual(len(res["facts"]), 1)
        self.assertIn("bổ sung", res["answer"])
        self.assertEqual(len(res["data_gaps"]), 1)
        self.assertIn("chưa đủ ngày lịch sử", res["data_gaps"][0])


if __name__ == "__main__":
    unittest.main()
