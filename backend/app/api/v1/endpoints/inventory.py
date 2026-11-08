"""
API Endpoints cho Quản lý Lô hàng và Tồn kho (Batches & Inventory).
"""
from typing import List, Optional
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.db.models.inventory import Batch
from app.services.inventory_service import InventoryService
from app.schemas.inventory import (
    BatchRead,
    BatchCreateRequest,
    BatchAdjustmentRequest
)

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.get("/batches", response_model=List[BatchRead])
def list_batches(
    kitchen_id: str = Query(..., description="ID của bếp"),
    ingredient_id: Optional[str] = Query(None, description="Lọc theo nguyên liệu"),
    location: Optional[str] = Query(None, description="Lọc theo vị trí lưu trữ"),
    only_usable: bool = Query(True, description="Chỉ lấy lô còn tồn > 0"),
    db: Session = Depends(get_db)
):
    stmt = select(Batch).where(Batch.kitchen_id == kitchen_id)
    if ingredient_id:
        stmt = stmt.where(Batch.ingredient_id == ingredient_id)
    if location:
        stmt = stmt.where(Batch.location == location)
    if only_usable:
        stmt = stmt.where(Batch.remaining_qty > Decimal("0"))

    stmt = stmt.order_by(Batch.expiry_date.asc().nullslast(), Batch.received_on.asc())
    batches = db.execute(stmt).scalars().all()
    return batches


@router.post("/batches", response_model=BatchRead, status_code=status.HTTP_201_CREATED)
def create_batch(
    kitchen_id: str = Query(..., description="ID của bếp"),
    payload: BatchCreateRequest = ...,
    db: Session = Depends(get_db)
):
    try:
        batch = InventoryService.receive_batch(
            db=db,
            kitchen_id=kitchen_id,
            ingredient_id=str(payload.ingredient_id),
            qty=payload.quantity,
            unit_cost=payload.unit_cost,
            location=payload.location.value if hasattr(payload.location, 'value') else str(payload.location),
            expiry_date=payload.expiry_date,
            received_on=payload.received_on
        )
        db.commit()
        db.refresh(batch)
        return batch
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/batches/{batch_id}/adjust", response_model=BatchRead)
def adjust_batch(
    batch_id: str,
    kitchen_id: str = Query(..., description="ID của bếp"),
    payload: BatchAdjustmentRequest = ...,
    db: Session = Depends(get_db)
):
    try:
        batch, _ = InventoryService.adjust_batch(
            db=db,
            kitchen_id=kitchen_id,
            batch_id=batch_id,
            new_qty=payload.actual_quantity,
            new_unit_cost=payload.new_unit_cost,
            reason=payload.reason_code or "Kiểm kho"
        )
        db.commit()
        db.refresh(batch)
        return batch
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
