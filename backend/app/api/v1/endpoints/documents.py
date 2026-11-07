"""
API Endpoints cho Xử lý Chứng từ (Documents).
"""
from typing import List, Optional, Dict, Any
from datetime import date
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.document_service import DocumentService
from app.schemas.documents import DocumentResponse

router = APIRouter(prefix="/documents", tags=["Documents"])


class ParseCsvRequest(BaseModel):
    csv_text: str = Field(..., description="Nội dung file CSV thô")
    kind: str = Field(..., description="IMPORT_INVOICE hoặc SALES_REPORT")


class CommitReceiptRequest(BaseModel):
    business_date: date
    lines: List[Dict[str, Any]]
    original_filename: Optional[str] = None
    file_sha256: Optional[str] = None


class CommitSalesReportRequest(BaseModel):
    business_date: date
    lines: List[Dict[str, Any]]
    original_filename: Optional[str] = None
    file_sha256: Optional[str] = None


@router.post("/parse-csv")
def parse_csv(payload: ParseCsvRequest):
    try:
        lines = DocumentService.parse_csv(payload.csv_text, payload.kind)
        return {"kind": payload.kind, "line_count": len(lines), "lines": lines}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/receipts", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def commit_receipt(
    kitchen_id: str = Query(..., description="ID của bếp"),
    payload: CommitReceiptRequest = ...,
    db: Session = Depends(get_db)
):
    try:
        doc = DocumentService.commit_receipt(
            db=db,
            kitchen_id=kitchen_id,
            business_date=payload.business_date,
            lines=payload.lines,
            file_sha256=payload.file_sha256,
            original_filename=payload.original_filename
        )
        db.commit()
        db.refresh(doc)
        return doc
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/sales-reports", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def commit_sales_report(
    kitchen_id: str = Query(..., description="ID của bếp"),
    payload: CommitSalesReportRequest = ...,
    db: Session = Depends(get_db)
):
    try:
        doc = DocumentService.commit_sales_report(
            db=db,
            kitchen_id=kitchen_id,
            business_date=payload.business_date,
            lines=payload.lines,
            file_sha256=payload.file_sha256,
            original_filename=payload.original_filename
        )
        db.commit()
        db.refresh(doc)
        return doc
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
