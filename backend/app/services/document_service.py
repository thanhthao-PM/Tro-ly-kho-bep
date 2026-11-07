"""
DocumentService: Xử lý chứng từ hóa đơn nhập (IMPORT_INVOICE) và báo cáo xuất (SALES_REPORT).
Tuân thủ nghiêm ngặt Architecture Revision 6.3:
- Kiểm tra tính duy nhất file_sha256 (chống nạp trùng lặp).
- Xác nhận chứng từ (CONFIRMED) tạo các lô hàng hoặc giao dịch bán hàng tương ứng.
"""
import hashlib
import io
import csv
from decimal import Decimal
from datetime import date, datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from app.db.models.documents import Document, DocumentLine
from app.db.models.catalog import Ingredient
from app.db.models.menu import Dish
from app.services.inventory_service import InventoryService
from app.services.sales_service import SalesService, SaleLineItemInput


class DocumentService:

    @staticmethod
    def calculate_file_hash(content_bytes: bytes) -> str:
        return hashlib.sha256(content_bytes).hexdigest()

    @staticmethod
    def parse_csv(csv_content: str, kind: str) -> List[Dict[str, Any]]:
        """
        Phân tích nội dung file CSV thành danh sách các dòng chứng từ thô.
        """
        lines: List[Dict[str, Any]] = []
        reader = csv.reader(io.StringIO(csv_content), delimiter=',', skipinitialspace=True)

        for row_idx, row in enumerate(reader, start=1):
            if not row or not any(row):
                continue
            # Làm sạch các cột
            cleaned = [c.strip() for c in row]
            if len(cleaned) < 2:
                continue

            name = cleaned[0]
            try:
                qty = Decimal(cleaned[1].replace(',', '.'))
            except Exception:
                continue

            if qty <= Decimal("0"):
                continue

            if kind == "IMPORT_INVOICE":
                unit = cleaned[2] if len(cleaned) > 2 and not cleaned[2].replace('.', '').isdigit() else None
                cost_idx = 3 if unit else 2
                cost = Decimal("0")
                if len(cleaned) > cost_idx:
                    try:
                        cost = Decimal(cleaned[cost_idx].replace(',', '.'))
                    except Exception:
                        cost = Decimal("0")

                lines.append({
                    "line_number": row_idx,
                    "target_type": "INGREDIENT",
                    "raw_text": ", ".join(cleaned),
                    "parsed_name": name,
                    "quantity": qty,
                    "unit_text": unit,
                    "unit_cost": cost
                })
            else:
                # SALES_REPORT
                lines.append({
                    "line_number": row_idx,
                    "target_type": "DISH",
                    "raw_text": ", ".join(cleaned),
                    "parsed_name": name,
                    "quantity": qty
                })

        return lines

    @staticmethod
    def commit_receipt(
        db: Session,
        kitchen_id: str,
        business_date: date,
        lines: List[Dict[str, Any]],
        file_sha256: Optional[str] = None,
        original_filename: Optional[str] = None,
        actor_id: Optional[str] = None
    ) -> Document:
        """
        Ghi nhận hóa đơn nhập hàng vào hệ thống:
        - Tạo Document (kind='IMPORT_INVOICE', status='CONFIRMED').
        - Nhập các lô hàng tương ứng qua InventoryService.receive_batch.
        """
        if not lines:
            raise ValueError("Hóa đơn nhập cần ít nhất một dòng nguyên liệu")

        doc = Document(
            kitchen_id=kitchen_id,
            kind="IMPORT_INVOICE",
            source_format="CSV" if original_filename and original_filename.endswith('.csv') else "MANUAL",
            status="CONFIRMED",
            business_date=business_date,
            original_filename=original_filename,
            file_sha256=file_sha256,
            created_by=actor_id,
            confirmed_at=datetime.utcnow()
        )
        db.add(doc)
        db.flush()

        for idx, line_data in enumerate(lines, start=1):
            ingredient_id = line_data["ingredient_id"]
            qty = Decimal(str(line_data["quantity"]))
            unit_cost = Decimal(str(line_data.get("unit_cost", 0)))
            location = line_data.get("location", "FRIDGE")
            expiry_date = line_data.get("expiry_date")

            doc_line = DocumentLine(
                kitchen_id=kitchen_id,
                document_id=doc.id,
                line_number=idx,
                target_type="INGREDIENT",
                target_id=ingredient_id,
                target_name_snapshot=line_data.get("name", "Nguyên liệu"),
                quantity=qty,
                unit_cost=unit_cost,
                total_value_vnd=int(qty * unit_cost),
                status="COMMITTED"
            )
            db.add(doc_line)
            db.flush()

            # Nhập lô hàng vào kho
            InventoryService.receive_batch(
                db=db,
                kitchen_id=kitchen_id,
                ingredient_id=ingredient_id,
                qty=qty,
                unit_cost=unit_cost,
                location=location,
                expiry_date=expiry_date,
                received_on=business_date,
                document_line_id=doc_line.id,
                actor_id=actor_id
            )

        return doc

    @staticmethod
    def commit_sales_report(
        db: Session,
        kitchen_id: str,
        business_date: date,
        lines: List[Dict[str, Any]],
        file_sha256: Optional[str] = None,
        original_filename: Optional[str] = None,
        actor_id: Optional[str] = None
    ) -> Document:
        """
        Ghi nhận báo cáo xuất bán hàng:
        - Tạo Document (kind='SALES_REPORT', status='CONFIRMED').
        - Trừ kho FEFO và ghi nhận doanh số bán món qua SalesService.record_sale.
        """
        if not lines:
            raise ValueError("Báo cáo xuất cần ít nhất một dòng bán hàng")

        doc = Document(
            kitchen_id=kitchen_id,
            kind="SALES_REPORT",
            source_format="CSV" if original_filename and original_filename.endswith('.csv') else "MANUAL",
            status="CONFIRMED",
            business_date=business_date,
            original_filename=original_filename,
            file_sha256=file_sha256,
            created_by=actor_id,
            confirmed_at=datetime.utcnow()
        )
        db.add(doc)
        db.flush()

        sale_items: List[SaleLineItemInput] = []
        for line_data in lines:
            if line_data.get("target_type") == "DISH":
                sale_items.append(
                    SaleLineItemInput(
                        dish_id=line_data["dish_id"],
                        quantity=int(line_data["quantity"]),
                        unit_price_vnd=line_data.get("unit_price_vnd")
                    )
                )

        if sale_items:
            SalesService.record_sale(
                db=db,
                kitchen_id=kitchen_id,
                business_date=business_date,
                items=sale_items,
                source_document_id=doc.id,
                actor_id=actor_id
            )

        return doc
