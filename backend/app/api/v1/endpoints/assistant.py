"""
API Endpoints cho Module Assistant (Trợ lý AI Fact-based).
"""
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.assistant_service import AssistantService
from app.schemas.assistant import AssistantMessageRequest, AssistantMessageResponse

router = APIRouter(prefix="/assistant", tags=["Assistant"])


@router.post("/messages", response_model=AssistantMessageResponse)
def send_assistant_message(
    kitchen_id: str = Query(..., description="ID của bếp"),
    payload: AssistantMessageRequest = ...,
    db: Session = Depends(get_db)
):
    """
    Tiếp nhận câu hỏi từ người dùng và trả về câu trả lời có grounding dữ liệu thực tế (Revision 6.3).
    """
    try:
        return AssistantService.answer_query(
            db=db,
            kitchen_id=kitchen_id,
            payload=payload
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
