"""
API Endpoints cho Module Reports (Báo cáo P&L, Hao hụt, Bổ sung hàng D25).
"""
from typing import Optional
from datetime import date
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.orm import Session, selectinload

from app.db.models.documents import Document
from app.db.session import get_db
from app.services.replenishment_service import ReplenishmentService
from app.schemas.reports import ReplenishmentResponse

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/daily-invoices")
def get_daily_invoice_summary(
    kitchen_id: UUID = Query(..., description="ID của bếp"),
    business_date: date = Query(..., description="Ngày hóa đơn"),
    db: Session = Depends(get_db),
):
    documents = db.execute(
        select(Document)
        .options(selectinload(Document.lines))
        .where(
            and_(
                Document.kitchen_id == kitchen_id,
                Document.kind == "IMPORT_INVOICE",
                Document.status == "CONFIRMED",
                Document.business_date == business_date,
            )
        )
        .order_by(Document.created_at.desc())
    ).scalars().all()

    invoices = [
        {
            "id": str(document.id),
            "business_date": document.business_date.isoformat(),
            "original_filename": document.original_filename,
            "source_format": document.source_format,
            "line_count": len(document.lines),
            "total_value_vnd": sum(line.line_total_vnd or 0 for line in document.lines),
            "file_url": (
                f"/documents/{document.id}/file?kitchen_id={kitchen_id}"
                if document.storage_key else None
            ),
        }
        for document in documents
    ]
    return {
        "business_date": business_date.isoformat(),
        "invoice_count": len(invoices),
        "line_count": sum(invoice["line_count"] for invoice in invoices),
        "total_value_vnd": sum(invoice["total_value_vnd"] for invoice in invoices),
        "invoices": invoices,
    }


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
