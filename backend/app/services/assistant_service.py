"""
AssistantService: Dịch vụ Trợ lý AI có grounding dữ liệu thực tế (Fact-based Assistant).
Tuân thủ nghiêm ngặt Architecture Revision 6.3:
- Không bịa số liệu: mọi số liệu đều được neo vào VerifiedFact từ Database.
- Trả về cấu trúc chuẩn: answer_text, facts, recommendations, data_gaps, proposed_actions.
- Hỗ trợ rule-based provider độc lập và kết nối LLM an toàn.
"""
import uuid
from decimal import Decimal
from datetime import date, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func

from app.db.models.catalog import Ingredient
from app.db.models.inventory import Batch, StockMovement
from app.db.models.sales import Sale, SaleLine, StockShortage
from app.db.models.disposals import Disposal
from app.db.models.menu import Dish
from app.services.replenishment_service import ReplenishmentService
from app.schemas.assistant import (
    AssistantMessageRequest,
    AssistantMessageResponse,
    VerifiedFact,
    RecommendationItem,
    ProposedAction
)


class AssistantService:

    @staticmethod
    def collect_grounding_facts(db: Session, kitchen_id: str) -> Dict[str, Any]:
        """
        Truy xuất toàn bộ dữ liệu thực tế từ cơ sở dữ liệu làm cơ sở đối chiếu (Grounding).
        """
        today = date.today()
        three_days_later = today + timedelta(days=3)

        # 1. Tồn kho & Lô hàng
        batches = db.execute(
            select(Batch).where(
                and_(Batch.kitchen_id == kitchen_id, Batch.remaining_qty > Decimal("0"))
            ).order_by(Batch.expiry_date.asc().nullslast())
        ).scalars().all()

        total_batches = len(batches)
        total_stock_value = sum(int(b.remaining_qty * b.unit_cost) for b in batches)

        expiring_soon_batches = [
            b for b in batches
            if b.expiry_date and today <= b.expiry_date <= three_days_later
        ]
        expired_batches = [
            b for b in batches
            if b.expiry_date and b.expiry_date < today
        ]

        # 2. Thiếu hụt Option C (OPEN)
        open_shortages = db.execute(
            select(StockShortage).where(
                and_(StockShortage.kitchen_id == kitchen_id, StockShortage.status == "OPEN")
            )
        ).scalars().all()

        # 3. Hao hụt gần đây (Disposals)
        disposals = db.execute(
            select(Disposal).where(Disposal.kitchen_id == kitchen_id).order_by(Disposal.occurred_on.desc()).limit(10)
        ).scalars().all()
        waste_disposals = [d for d in disposals if d.type == "WASTE"]

        # 4. Món ăn thực đơn
        dishes = db.execute(
            select(Dish).where(
                and_(Dish.kitchen_id == kitchen_id, Dish.deleted_at.is_(None))
            )
        ).scalars().all()

        return {
            "today": today,
            "batches": batches,
            "total_batches": total_batches,
            "total_stock_value": total_stock_value,
            "expiring_soon_batches": expiring_soon_batches,
            "expired_batches": expired_batches,
            "open_shortages": open_shortages,
            "waste_disposals": waste_disposals,
            "dishes": dishes,
        }

    @staticmethod
    def answer_query(
        db: Session,
        kitchen_id: str,
        payload: AssistantMessageRequest
    ) -> AssistantMessageResponse:
        grounding = AssistantService.collect_grounding_facts(db, kitchen_id)
        msg_lower = payload.message.lower().strip()
        request_id = str(uuid.uuid4())

        facts: List[VerifiedFact] = []
        recommendations: List[RecommendationItem] = []
        data_gaps: List[str] = []
        proposed_actions: List[ProposedAction] = []
        answer_parts: List[str] = []

        # Thêm fact tổng quan tồn kho
        f_stock_val = VerifiedFact(
            id=f"F-VAL-{uuid.uuid4().hex[:6]}",
            tool="get_stock_overview",
            label="Tổng giá trị tồn kho",
            value=f"{grounding['total_stock_value']:,} đ".replace(",", "."),
            unit="VND",
            as_of=str(grounding["today"])
        )
        facts.append(f_stock_val)

        # 1. Hỏi về đồ cận date / cần xử lý / hôm nay
        if any(w in msg_lower for w in ("cận date", "hết hạn", "xử lý", "hôm nay", "gợi ý", "can xu ly")):
            exp_soon = grounding["expiring_soon_batches"]
            expired = grounding["expired_batches"]

            if expired:
                f_exp = VerifiedFact(
                    id=f"F-EXP-{uuid.uuid4().hex[:6]}",
                    tool="list_expiring",
                    label="Số lô đã quá hạn",
                    value=str(len(expired)),
                    unit="đợt",
                    as_of=str(grounding["today"])
                )
                facts.append(f_exp)
                answer_parts.append(f"Kho đang có {len(expired)} đợt hàng đã quá hạn sử dụng. Cần xử lý bỏ hoặc hủy để tránh mất an toàn thực phẩm.")
                for b in expired[:2]:
                    proposed_actions.append(ProposedAction(
                        type="OPEN_EXPIRING_BATCH",
                        target_id=b.id,
                        label=f"Xử lý bỏ đợt {b.id} ({b.ingredient_id})"
                    ))

            if exp_soon:
                f_soon = VerifiedFact(
                    id=f"F-SOON-{uuid.uuid4().hex[:6]}",
                    tool="list_expiring",
                    label="Số lô cận date (≤ 3 ngày)",
                    value=str(len(exp_soon)),
                    unit="đợt",
                    as_of=str(grounding["today"])
                )
                facts.append(f_soon)
                answer_parts.append(f"Có {len(exp_soon)} đợt hàng sắp hết hạn trong 3 ngày tới.")
                recommendations.append(RecommendationItem(
                    text="Ưu tiên đưa các nguyên liệu cận date vào thực đơn nấu trưa hoặc quyên góp / bán thu mua trước hạn.",
                    assumptions=["Chất lượng cảm quan còn tốt và nằm trong thời hạn dùng an toàn"],
                    basis="VERIFIED_FACT"
                ))
                for b in exp_soon[:2]:
                    proposed_actions.append(ProposedAction(
                        type="OPEN_EXPIRING_BATCH",
                        target_id=b.id,
                        label=f"Ưu tiên chế biến đợt {b.id}"
                    ))
            elif not expired:
                answer_parts.append("Hôm nay kho không có lô hàng nào quá hạn hoặc cận date dưới 3 ngày. Tình trạng hạn dùng đang an toàn.")

        # 2. Hỏi về tồn kho mặt hàng cụ thể
        elif any(w in msg_lower for w in ("còn bao nhiêu", "tồn", "kho còn", "het hang", "hết hàng")):
            matched_batches = []
            for b in grounding["batches"]:
                matched_batches.append(b)

            if matched_batches:
                answer_parts.append(f"Hiện tại trong kho đang quản lý {len(grounding['batches'])} đợt hàng với tổng giá trị {grounding['total_stock_value']:,} đ.")
            else:
                answer_parts.append("Kho hiện tại đang trống hoặc chưa ghi nhận lô hàng còn tồn.")
                data_gaps.append("Chưa có chứng từ nhập hàng gần đây.")

        # 3. Hỏi về bổ sung hàng / đặt hàng / replenishment
        elif any(w in msg_lower for w in ("đặt hàng", "bổ sung", "nhập thêm", "replenishment", "mua")):
            repl = ReplenishmentService.get_replenishment_suggestions(db, kitchen_id, grounding["today"])
            if repl.items:
                f_repl = VerifiedFact(
                    id=f"F-REPL-{uuid.uuid4().hex[:6]}",
                    tool="get_replenishment_suggestions",
                    label="Số mặt hàng cần đặt",
                    value=str(len(repl.items)),
                    unit="mặt hàng",
                    as_of=str(grounding["today"])
                )
                facts.append(f_repl)
                item_names = [f"{it.ingredient_name} ({it.suggested_order_qty} {it.unit})" for it in repl.items[:3]]
                answer_parts.append(f"Thuật toán D25 đề xuất bổ sung {len(repl.items)} mặt hàng: {', '.join(item_names)}.")
                recommendations.append(RecommendationItem(
                    text="Đề xuất đặt hàng được tính dựa trên số ngày tồn kho khả dụng dưới ngưỡng mục tiêu (D25).",
                    assumptions=[f"Mục tiêu bao phủ: {repl.parameters.get('target_coverage_days')} ngày"],
                    basis="ESTIMATE"
                ))
                proposed_actions.append(ProposedAction(
                    type="OPEN_REPLENISHMENT",
                    target_id=None,
                    label="Xem chi tiết danh sách đề xuất đặt hàng D25"
                ))
            else:
                answer_parts.append("Tồn kho hiện tại đủ đáp ứng nhu cầu mục tiêu theo công thức D25. Chưa cần đặt thêm hàng.")

            if repl.insufficient_data:
                data_gaps.append(f"Có {len(repl.insufficient_data)} mặt hàng chưa đủ ngày lịch sử tiêu thụ để tính trung bình ngày.")

        # 4. Thiếu hụt kho Option C
        if grounding["open_shortages"]:
            f_short = VerifiedFact(
                id=f"F-SHORT-{uuid.uuid4().hex[:6]}",
                tool="get_shortages",
                label="Bản ghi thiếu hụt đang mở",
                value=str(len(grounding["open_shortages"])),
                unit="bản ghi",
                as_of=str(grounding["today"])
            )
            facts.append(f_short)
            recommendations.append(RecommendationItem(
                text=f"Đang có {len(grounding['open_shortages'])} trường hợp thiếu hụt tồn kho Option C cần xử lý giải quyết.",
                assumptions=["Chờ trừ bù từ lô hàng mới, ghi nhận chi phí ước tính vào P&L hoặc miễn trừ"],
                basis="VERIFIED_FACT"
            ))

        if not answer_parts:
            answer_parts.append(
                f"Trợ lý kho ghi nhận kho có {grounding['total_batches']} đợt hàng, tổng giá trị {grounding['total_stock_value']:,} đ. "
                "Bạn có thể hỏi chi tiết về: các đợt cận date cần xử lý, gợi ý bổ sung hàng D25, lãi lỗ từng món hoặc kiểm kê kho."
            )

        return AssistantMessageResponse(
            answer_text=" ".join(answer_parts),
            facts=facts,
            recommendations=recommendations,
            data_gaps=data_gaps,
            proposed_actions=proposed_actions,
            provider="rule_based",
            request_id=request_id
        )
