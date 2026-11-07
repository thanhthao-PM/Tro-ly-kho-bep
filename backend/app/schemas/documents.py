"""
Pydantic Schemas cho Module Documents (Chứng từ, Bóc tách dòng, Xác nhận).
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import date, datetime
from pydantic import BaseModel, Field
from app.core.constants import DocumentKind, DocumentSourceFormat, DocumentStatus, OCRStatus


class DocumentLineResponse(BaseModel):
    id: UUID
    line_no: int
    raw_text: Optional[str] = None
    is_selected: bool
    ingredient: Optional[Dict[str, Any]] = None
    dish: Optional[Dict[str, Any]] = None
    quantity: Optional[str] = None
    unit: Optional[str] = None
    unit_price_vnd: Optional[str] = None
    line_total_vnd: Optional[int] = None
    expiry_date: Optional[date] = None
    confidence: Optional[Dict[str, float]] = None
    flags: List[str] = []


class DocumentSummary(BaseModel):
    line_count: int
    total_value_vnd: Optional[int] = None
    blocking_issues: List[str] = []


class DocumentResponse(BaseModel):
    id: UUID
    kind: DocumentKind
    source_format: DocumentSourceFormat
    status: DocumentStatus
    ocr_status: OCRStatus
    business_date: date
    original_filename: Optional[str] = None
    lines: List[DocumentLineResponse]
    summary: DocumentSummary


class DocumentLineUpdate(BaseModel):
    ingredient_id: Optional[UUID] = None
    dish_id: Optional[UUID] = None
    quantity: Optional[str] = None
    unit: Optional[str] = None
    unit_price_vnd: Optional[str] = None
    expiry_date: Optional[date] = None
    is_selected: Optional[bool] = None
    parsed_name: Optional[str] = None


class DocumentConfirmResponse(BaseModel):
    document_id: UUID
    status: DocumentStatus
    batches_created: Optional[int] = None
    total_value_vnd: Optional[int] = None
    sales_recorded: Optional[int] = None
    revenue_vnd: Optional[int] = None
    shortages: List[Dict[str, Any]] = []
