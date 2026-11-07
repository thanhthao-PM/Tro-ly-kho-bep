"""
Pydantic Schemas dùng chung cho toàn bộ API.
Tuân thủ định dạng chuẩn Decimal, Money, UUID, CursorPage.
"""
from typing import TypeVar, Generic, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


T = TypeVar("T")


class Labeled(BaseModel, Generic[T]):
    value: T
    basis: str = Field(description="ACTUAL | ESTIMATE")


class CursorPage(BaseModel, Generic[T]):
    items: List[T]
    next_cursor: Optional[str] = None
    total_count: Optional[int] = None


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[dict] = None
    request_id: Optional[str] = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
