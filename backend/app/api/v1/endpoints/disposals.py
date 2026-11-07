"""
API Endpoints cho Xử lý hàng cận date & Quá hạn (Disposals).
"""
from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from app.db.session import get_db
from app.db.models.disposals import Disposal
from app.services.disposal_service import DisposalService
from app.schemas.disposals import DisposalCreateRequest, DisposalResponse

router = APIRouter(prefix="/disposals", tags=["Disposals"])


@router.post("", response_model=DisposalResponse, status_code=status.HTTP_201_CREATED)
def create_disposal(
    kitchen_id: str = Query(..., description="ID của bếp"),
    payload: DisposalCreateRequest = ...,
    db: Session = Depends(get_db)
):
    try:
        disposal = DisposalService.record_disposal(
            db=db,
            kitchen_id=kitchen_id,
            batch_id=str(payload.batch_id),
            disposal_type=payload.type.value if hasattr(payload.type, 'value') else str(payload.type),
            quantity=payload.quantity,
            occurred_on=payload.occurred_on,
            reason_code=payload.reason_code.value if payload.reason_code and hasattr(payload.reason_code, 'value') else (str(payload.reason_code) if payload.reason_code else None),
            note=payload.note,
            counterparty_name=payload.counterparty_name,
            revenue_vnd=payload.revenue_vnd
        )
        db.commit()
        db.refresh(disposal)
        return disposal
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=List[DisposalResponse])
def list_disposals(
    kitchen_id: str = Query(..., description="ID của bếp"),
    from_date: Optional[date] = Query(None, description="Từ ngày"),
    to_date: Optional[date] = Query(None, description="Đến ngày"),
    db: Session = Depends(get_db)
):
    stmt = select(Disposal).where(Disposal.kitchen_id == kitchen_id)
    if from_date:
        stmt = stmt.where(Disposal.occurred_on >= from_date)
    if to_date:
        stmt = stmt.where(Disposal.occurred_on <= to_date)
    stmt = stmt.order_by(Disposal.occurred_on.desc(), Disposal.created_at.desc())
    return db.execute(stmt).scalars().all()
