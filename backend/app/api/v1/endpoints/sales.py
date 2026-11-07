"""
API Endpoints cho Bán hàng và Giải quyết Thiếu hụt kho Option C.
"""
from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from app.db.session import get_db
from app.db.models.sales import Sale, StockShortage
from app.services.sales_service import SalesService, SaleLineItemInput
from app.schemas.sales import (
    SaleCreateRequest,
    SaleResponse,
    StockShortageResolveRequest,
    StockShortageResponse
)

router = APIRouter(prefix="/sales", tags=["Sales"])


@router.post("", response_model=SaleResponse, status_code=status.HTTP_201_CREATED)
def record_sale(
    kitchen_id: str = Query(..., description="ID của bếp"),
    payload: SaleCreateRequest = ...,
    db: Session = Depends(get_db)
):
    try:
        items = [
            SaleLineItemInput(
                dish_id=str(item.dish_id),
                quantity=item.quantity,
                unit_price_vnd=item.unit_price_vnd,
                origin=item.origin.value if hasattr(item.origin, 'value') else str(item.origin),
                source_batch_id=str(item.source_batch_id) if item.source_batch_id else None
            )
            for item in payload.items
        ]

        sale = SalesService.record_sale(
            db=db,
            kitchen_id=kitchen_id,
            business_date=payload.business_date,
            items=items
        )
        db.commit()
        db.refresh(sale)
        return sale
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/shortages/{shortage_id}/resolve", response_model=StockShortageResponse)
def resolve_shortage(
    shortage_id: str,
    kitchen_id: str = Query(..., description="ID của bếp"),
    payload: StockShortageResolveRequest = ...,
    db: Session = Depends(get_db)
):
    try:
        shortage = SalesService.resolve_shortage(
            db=db,
            kitchen_id=kitchen_id,
            shortage_id=shortage_id,
            resolution_mode=payload.resolution.value if hasattr(payload.resolution, 'value') else str(payload.resolution)
        )
        db.commit()
        db.refresh(shortage)
        return shortage
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
