"""
API Endpoints cho Module Reports (Báo cáo P&L, Hao hụt, Bổ sung hàng D25).
"""
from typing import Optional
from datetime import date
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.replenishment_service import ReplenishmentService
from app.schemas.reports import ReplenishmentResponse

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/replenishment-suggestions", response_model=ReplenishmentResponse)
def get_replenishment_suggestions(
    kitchen_id: str = Query(..., description="ID của bếp"),
    as_of: Optional[date] = Query(None, description="Ngày chốt tính toán (mặc định hôm nay)"),
    target_coverage_days: Optional[int] = Query(None, ge=1, le=60, description="Số ngày bao phủ mục tiêu"),
    consumption_window_days: Optional[int] = Query(None, ge=7, le=90, description="Độ dài cửa sổ quan sát tiêu thụ"),
    min_history_days: Optional[int] = Query(None, ge=1, description="Số ngày quan sát tối thiểu"),
    db: Session = Depends(get_db)
):
    """
    Trả về danh sách đề xuất bổ sung hàng thông minh theo Thuật toán D25 (Revision 6.3).
    """
    try:
        return ReplenishmentService.get_replenishment_suggestions(
            db=db,
            kitchen_id=kitchen_id,
            as_of_date=as_of,
            target_coverage_days=target_coverage_days,
            consumption_window_days=consumption_window_days,
            min_history_days=min_history_days
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
