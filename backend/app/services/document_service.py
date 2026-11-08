"""
DocumentService: Xử lý chứng từ hóa đơn nhập (IMPORT_INVOICE) và báo cáo xuất (SALES_REPORT).
Tuân thủ nghiêm ngặt Architecture Revision 6.3:
- Kiểm tra tính duy nhất file_sha256 (chống nạp trùng lặp).
- Xác nhận chứng từ (CONFIRMED) tạo các lô hàng hoặc giao dịch bán hàng tương ứng.
"""
import hashlib
import io
import csv
import re
import unicodedata
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime
from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from app.db.models.documents import Document, DocumentLine
from app.db.models.catalog import Ingredient, IngredientUnitConversion, Unit
from app.db.models.menu import Dish
from app.services.inventory_service import InventoryService
from app.services.sales_service import SalesService, SaleLineItemInput


class DocumentService:

    @staticmethod
    def _normalize_ingredient_name(name: str) -> str:
        folded = unicodedata.normalize("NFD", name.casefold().replace("đ", "d"))
        without_marks = "".join(char for char in folded if unicodedata.category(char) != "Mn")
        return re.sub(r"[^a-z0-9]+", " ", without_marks).strip()

    @staticmethod
    def _resolve_receipt_ingredient(
        db: Session,
        kitchen_id: UUID,
        line_data: Dict[str, Any],
    ) -> Ingredient:
        ingredient_id = line_data.get("ingredient_id")
        ingredient = None
        if ingredient_id:
            try:
                parsed_id = UUID(str(ingredient_id))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Mã nguyên liệu không hợp lệ: {ingredient_id}") from exc
            ingredient = db.execute(
                select(Ingredient).where(
                    and_(
                        Ingredient.kitchen_id == kitchen_id,
                        Ingredient.id == parsed_id,
                        Ingredient.deleted_at.is_(None)
                    )
                )
            ).scalar_one_or_none()
            if ingredient is None:
                candidates = db.execute(
                    select(Ingredient).where(
                        and_(
                            Ingredient.kitchen_id == kitchen_id,
                            Ingredient.deleted_at.is_(None)
                        )
                    )
                ).scalars()
                ingredient = next(
                    (
                        candidate for candidate in candidates
                        if DocumentService._normalize_ingredient_name(candidate.normalized_name) == normalized_name
                    ),
                    None,
                )

        name = str(line_data.get("name") or line_data.get("parsed_name") or "").strip()
        if ingredient is None:
            if not name:
                raise ValueError("Mỗi dòng nhập kho cần mã nguyên liệu hợp lệ hoặc tên nguyên liệu")

            normalized_name = DocumentService._normalize_ingredient_name(name)
            ingredient = db.execute(
                select(Ingredient).where(
                    and_(
                        Ingredient.kitchen_id == kitchen_id,
                        Ingredient.normalized_name == normalized_name,
                        Ingredient.deleted_at.is_(None)
                    )
                )
            ).scalar_one_or_none()

            if ingredient is None:
                base_unit_code = str(line_data.get("unit_code") or line_data.get("unit") or "kg").strip().lower()
                if db.get(Unit, base_unit_code) is None:
                    raise ValueError(f"Đơn vị tính không tồn tại: {base_unit_code}")

                location = line_data.get("location") or "FRIDGE"
                if hasattr(location, "value"):
                    location = location.value
                if location == "DRY":
                    location = "PANTRY"
                if location not in {"FRIDGE", "FREEZER", "PANTRY"}:
                    raise ValueError(f"Vị trí lưu trữ không hợp lệ: {location}")

                ingredient = Ingredient(
                    kitchen_id=kitchen_id,
                    name=name,
                    normalized_name=normalized_name,
                    search_name=normalized_name,
                    base_unit_code=base_unit_code,
                    default_location=location,
                )
                db.add(ingredient)
                db.flush()

        return ingredient

    @staticmethod
    def _parse_csv_number(
        value: str,
        *,
        decimal_dot: bool = False,
        decimal_comma: bool = False,
    ) -> Decimal:
        normalized = value.strip().replace(" ", "")
        if "," in normalized and "." in normalized:
            decimal_separator = "," if normalized.rfind(",") > normalized.rfind(".") else "."
            grouping_separator = "." if decimal_separator == "," else ","
            normalized = normalized.replace(grouping_separator, "").replace(decimal_separator, ".")
        elif "," in normalized:
            normalized = normalized.replace(
                ",",
                "." if decimal_comma or len(normalized.rsplit(",", 1)[-1]) != 3 else "",
            )
        elif "." in normalized:
            normalized = normalized.replace(
                ".",
                "" if not decimal_dot and len(normalized.rsplit(".", 1)[-1]) == 3 else ".",
            )
        return Decimal(normalized)

    @staticmethod
    def calculate_file_hash(content_bytes: bytes) -> str:
        return hashlib.sha256(content_bytes).hexdigest()

    @staticmethod
    def parse_csv(csv_content: str, kind: str) -> List[Dict[str, Any]]:
        """
        Phân tích nội dung file CSV thành danh sách các dòng chứng từ thô.
        """
        lines: List[Dict[str, Any]] = []
        sample = next((line for line in csv_content.splitlines() if line.strip()), "")
        delimiter = max((",", ";", "\t"), key=sample.count)
        reader = csv.reader(io.StringIO(csv_content), delimiter=delimiter, skipinitialspace=True)

        for row_idx, row in enumerate(reader, start=1):
            if not row or not any(row):
                continue
            # Làm sạch các cột
            cleaned = [c.strip() for c in row]
            if len(cleaned) < 2:
                continue

            name = cleaned[0]
            try:
                qty = DocumentService._parse_csv_number(
                    cleaned[1], decimal_dot=True, decimal_comma=True
                )
            except (ArithmeticError, ValueError):
                continue

            if not qty.is_finite() or qty <= Decimal("0"):
                continue

            if kind == "IMPORT_INVOICE":
                unit = cleaned[2] if len(cleaned) > 2 and not cleaned[2].replace('.', '').isdigit() else None
                cost_idx = 3 if unit else 2
                if len(cleaned) <= cost_idx:
                    continue
                try:
                    cost = DocumentService._parse_csv_number(cleaned[cost_idx])
                except (ArithmeticError, ValueError):
                    continue
                if not cost.is_finite() or cost < Decimal("0"):
                    continue

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
        storage_key: Optional[str] = None,
        source_format: Optional[str] = None,
        actor_id: Optional[str] = None
    ) -> Document:
        """
        Ghi nhận hóa đơn nhập hàng vào hệ thống:
        - Tạo Document (kind='IMPORT_INVOICE', status='CONFIRMED').
        - Nhập các lô hàng tương ứng qua InventoryService.receive_batch.
        """
        if not lines:
            raise ValueError("Hóa đơn nhập cần ít nhất một dòng nguyên liệu")

        kitchen_uuid = UUID(str(kitchen_id))
        doc = Document(
            kitchen_id=kitchen_uuid,
            kind="IMPORT_INVOICE",
            source_format=source_format or (
                "IMAGE" if original_filename and original_filename.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
                else "PDF" if original_filename and original_filename.lower().endswith(".pdf")
                else "CSV" if original_filename and original_filename.lower().endswith(".csv")
                else "XLSX" if original_filename and original_filename.lower().endswith((".xls", ".xlsx"))
                else "MANUAL"
            ),
            status="CONFIRMED",
            ocr_status="DONE" if source_format in {"IMAGE", "PDF"} or (
                original_filename and original_filename.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".pdf"))
            ) else "NOT_APPLICABLE",
            business_date=business_date,
            original_filename=original_filename,
            file_sha256=file_sha256,
            storage_key=storage_key,
            created_by=actor_id,
            confirmed_at=datetime.utcnow()
        )
        db.add(doc)
        db.flush()

        for idx, line_data in enumerate(lines, start=1):
            ingredient = DocumentService._resolve_receipt_ingredient(db, kitchen_uuid, line_data)

            qty = Decimal(str(line_data["quantity"]))
            unit_cost = Decimal(str(line_data.get("unit_cost", 0)))
            unit_code = str(
                line_data.get("unit_code") or line_data.get("unit") or ingredient.base_unit_code
            ).strip().lower()
            if unit_code != ingredient.base_unit_code:
                conversion = db.execute(
                    select(IngredientUnitConversion).where(
                        and_(
                            IngredientUnitConversion.kitchen_id == kitchen_uuid,
                            IngredientUnitConversion.ingredient_id == ingredient.id,
                            IngredientUnitConversion.unit_code == unit_code,
                            IngredientUnitConversion.base_unit_code == ingredient.base_unit_code
                        )
                    )
                ).scalar_one_or_none()
                if conversion:
                    factor = Decimal(str(conversion.factor_to_base))
                else:
                    source_unit = db.get(Unit, unit_code)
                    base_unit = db.get(Unit, ingredient.base_unit_code)
                    if (
                        source_unit is None
                        or base_unit is None
                        or source_unit.dimension != base_unit.dimension
                        or source_unit.dimension not in {"MASS", "VOLUME"}
                    ):
                        raise ValueError(
                            f"Không có quy đổi đơn vị {unit_code} sang {ingredient.base_unit_code} "
                            f"cho nguyên liệu {ingredient.name}"
                        )
                    factor = (
                        Decimal(str(source_unit.factor_to_dimension_base))
                        / Decimal(str(base_unit.factor_to_dimension_base))
                    )
                if factor <= 0:
                    raise ValueError(
                        f"Hệ số quy đổi đơn vị {unit_code} không hợp lệ cho {ingredient.name}"
                    )
                qty *= factor
                unit_cost /= factor

            location = line_data.get("location") or ingredient.default_location
            if hasattr(location, "value"):
                location = location.value
            expiry_date = line_data.get("expiry_date")

            doc_line = DocumentLine(
                kitchen_id=kitchen_uuid,
                document_id=doc.id,
                line_no=idx,
                raw_text=line_data.get("raw_text"),
                parsed_name=line_data.get("name"),
                ingredient_id=ingredient.id,
                quantity=qty,
                unit_code=ingredient.base_unit_code,
                unit_price_vnd=unit_cost,
                line_total_vnd=int((qty * unit_cost).quantize(Decimal("1"), rounding=ROUND_HALF_UP)),
                expiry_date=expiry_date,
                is_selected=True
            )
            db.add(doc_line)
            db.flush()

            # Nhập lô hàng vào kho
            InventoryService.receive_batch(
                db=db,
                kitchen_id=kitchen_uuid,
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
