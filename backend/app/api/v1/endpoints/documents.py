"""
API Endpoints cho Xử lý Chứng từ (Documents).
"""
import base64
import csv
import io
import json
import logging
import os
import re
import unicodedata
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo
from zipfile import BadZipFile, ZipFile

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException
from pydantic import AliasChoices, BaseModel, Field
from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.constants import StorageLocation
from app.db.models.catalog import Ingredient
from app.db.models.documents import Document
from app.db.session import get_db
from app.schemas.documents import DocumentResponse
from app.services.document_service import DocumentService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["Documents"])
MAX_INVOICE_IMAGE_BYTES = 10 * 1024 * 1024
ALLOWED_INVOICE_TYPES = {
    "image/jpeg": ("IMAGE", ".jpg"),
    "image/png": ("IMAGE", ".png"),
    "image/webp": ("IMAGE", ".webp"),
    "application/pdf": ("PDF", ".pdf"),
}
ALLOWED_SPREADSHEET_TYPES = {
    "text/csv": ("CSV", ".csv"),
    "application/csv": ("CSV", ".csv"),
    "application/vnd.ms-excel": ("CSV", ".csv"),
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ("XLSX", ".xlsx"),
    "application/octet-stream": ("CSV", ".csv"),
}
DEMO_KITCHEN_ID = UUID("00000000-0000-0000-0000-000000000002")


class ParseCsvRequest(BaseModel):
    csv_text: str = Field(..., description="Nội dung file CSV thô")
    kind: str = Field(..., description="IMPORT_INVOICE hoặc SALES_REPORT")


class CommitReceiptLine(BaseModel):
    ingredient_id: UUID
    name: Optional[str] = Field(default=None, max_length=200)
    quantity: Decimal = Field(gt=0, validation_alias=AliasChoices("quantity", "qty"))
    unit_code: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=20,
        validation_alias=AliasChoices("unit_code", "unit"),
    )
    unit_cost: Decimal = Field(ge=0, validation_alias=AliasChoices("unit_cost", "cost"))
    location: StorageLocation = StorageLocation.FRIDGE
    expiry_date: Optional[date] = None


class CommitReceiptRequest(BaseModel):
    business_date: date
    lines: List[CommitReceiptLine] = Field(min_length=1)
    original_filename: Optional[str] = None
    file_sha256: Optional[str] = None


class CommitSalesReportRequest(BaseModel):
    business_date: date
    lines: List[Dict[str, Any]]
    original_filename: Optional[str] = None
    file_sha256: Optional[str] = None


def _invoice_file_format(
    content_type: Optional[str],
    content: bytes,
    filename: Optional[str] = None,
) -> Optional[tuple[str, str]]:
    extension = Path(filename or "").suffix.lower()
    if extension == ".csv":
        if content_type not in ALLOWED_SPREADSHEET_TYPES and content_type not in {"", None}:
            return None
        try:
            content.decode("utf-8-sig")
        except UnicodeDecodeError:
            return None
        return "CSV", ".csv"
    if extension == ".xlsx":
        if content_type and content_type not in ALLOWED_SPREADSHEET_TYPES:
            return None
        try:
            with ZipFile(io.BytesIO(content)) as workbook:
                if "xl/workbook.xml" not in workbook.namelist():
                    return None
        except BadZipFile:
            return None
        return "XLSX", ".xlsx"

    file_format = ALLOWED_INVOICE_TYPES.get(content_type or "")
    if not file_format:
        return None
    valid_signature = (
        content_type == "image/jpeg" and content.startswith(b"\xff\xd8\xff")
        or content_type == "image/png" and content.startswith(b"\x89PNG\r\n\x1a\n")
        or content_type == "image/webp" and content.startswith(b"RIFF") and content[8:12] == b"WEBP"
        or content_type == "application/pdf" and content.lstrip().startswith(b"%PDF-")
    )
    return file_format if valid_signature else None


def _parse_tabular_invoice(content: bytes, filename: str) -> List[Dict[str, Any]]:
    extension = Path(filename).suffix.lower()
    if extension == ".csv":
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError("Tệp CSV phải dùng bảng mã UTF-8.") from exc
    elif extension == ".xlsx":
        try:
            workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
            worksheet = workbook.active
            output = io.StringIO()
            writer = csv.writer(output)
            for row in worksheet.iter_rows(values_only=True):
                writer.writerow(["" if value is None else str(value) for value in row])
            workbook.close()
            text = output.getvalue()
        except (BadZipFile, InvalidFileException, KeyError, OSError, TypeError, ValueError) as exc:
            raise ValueError("Không đọc được bảng tính XLSX. Hãy kiểm tra lại tệp.") from exc
    else:
        raise ValueError("Chỉ hỗ trợ bảng tính CSV hoặc XLSX.")

    lines = DocumentService.parse_csv(text, "IMPORT_INVOICE")
    if not lines:
        raise ValueError(
            "Không tìm thấy dòng dữ liệu. Hãy dùng các cột: tên nguyên liệu, số lượng, đơn vị, đơn giá."
        )
    return [
        {
            "name": line["parsed_name"],
            "qty": float(line["quantity"]),
            "unit": line["unit_text"] or "kg",
            "cost": int(line["unit_cost"]),
        }
        for line in lines
    ]


def _match_invoice_lines(extracted: List[Dict[str, Any]], db: Session, kitchen_id: UUID) -> List[Dict[str, Any]]:
    ingredients = _catalog_for_kitchen(db, kitchen_id)
    lookup: Dict[str, Ingredient] = {}
    for ingredient in ingredients:
        lookup[_normalize_name(ingredient.name)] = ingredient
        for alias in ingredient.aliases:
            lookup[_normalize_name(alias.alias)] = ingredient

    lines = []
    for item in extracted:
        name = str(item.get("name", "")).strip().lower()
        try:
            quantity = _parse_number(str(item.get("qty", item.get("quantity", 0))), decimal_dot=True, decimal_comma=True)
            cost = _parse_number(str(item.get("cost", item.get("unit_cost", 0))))
        except (InvalidOperation, ValueError):
            continue
        if not name or not quantity.is_finite() or not cost.is_finite() or quantity <= 0 or cost < 0:
            continue

        ingredient = lookup.get(_normalize_name(name))
        location_value = str(item.get("location") or (ingredient.default_location if ingredient else "FRIDGE")).upper()
        location = "PANTRY" if location_value == "DRY" else location_value
        if location not in {"FRIDGE", "FREEZER", "PANTRY"}:
            location = ingredient.default_location if ingredient else "FRIDGE"
        expiry = _parse_expiry(item.get("expiry_date")) or _default_expiry(name, ingredient)

        lines.append({
            "name": name,
            "qty": float(quantity),
            "unit": str(item.get("unit") or (ingredient.base_unit_code if ingredient else "kg")).lower(),
            "cost": int(cost),
            "location": location,
            "expiry_date": expiry.isoformat(),
            "ingredient_id": str(ingredient.id) if ingredient else None,
            "catalog_name": ingredient.name if ingredient else None,
            "base_unit_code": ingredient.base_unit_code if ingredient else None,
        })
    return lines


def _receipt_response(doc: Document) -> Dict[str, Any]:
    response_lines = []
    total_value = 0
    for line in doc.lines:
        ingredient = line.ingredient
        total_value += line.line_total_vnd or 0
        response_lines.append({
            "id": line.id,
            "line_no": line.line_no,
            "raw_text": line.raw_text,
            "is_selected": line.is_selected,
            "ingredient": {"id": ingredient.id, "name": ingredient.name} if ingredient else None,
            "dish": None,
            "quantity": str(line.quantity) if line.quantity is not None else None,
            "unit": line.unit_code,
            "unit_price_vnd": str(line.unit_price_vnd) if line.unit_price_vnd is not None else None,
            "line_total_vnd": line.line_total_vnd,
            "expiry_date": line.expiry_date,
            "confidence": None,
            "flags": [],
        })
    return {
        "id": doc.id,
        "kind": doc.kind,
        "source_format": doc.source_format,
        "status": doc.status,
        "ocr_status": doc.ocr_status,
        "business_date": doc.business_date,
        "original_filename": doc.original_filename,
        "storage_key": doc.storage_key,
        "lines": response_lines,
        "summary": {
            "line_count": len(response_lines),
            "total_value_vnd": total_value,
            "blocking_issues": [],
        },
    }


def _normalize_name(value: str) -> str:
    folded = unicodedata.normalize("NFD", value.casefold().strip().replace("đ", "d"))
    without_marks = "".join(char for char in folded if unicodedata.category(char) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", without_marks).strip()


def _parse_expiry(value: Any) -> Optional[date]:
    if not isinstance(value, str) or not value.strip():
        return None
    candidate = value.strip()
    try:
        return date.fromisoformat(candidate)
    except ValueError:
        for date_format in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"):
            try:
                return datetime.strptime(candidate, date_format).date()
            except ValueError:
                continue
    return None


def _regex_parse_lines(text: str) -> List[Dict[str, Any]]:
    pattern = re.compile(
        r"^\s*(?:\d+[.)]\s*)?(?P<name>[^,;|]+?)\s*[,;|]\s*"
        r"(?P<qty>\d+(?:[.,]\d+)?)\s*[,;|]\s*(?P<unit>kg|g|l|ml|quả|hộp|bó|gói|chai)?"
        r"\s*[,;|]\s*(?P<cost>[\d.,]+)\s*(?:đ|đồng|vnd)?\s*$",
        re.IGNORECASE,
    )
    lines: List[Dict[str, Any]] = []
    for row in text.splitlines():
        match = pattern.match(row)
        if not match:
            continue
        try:
            quantity = _parse_number(match.group("qty"), decimal_dot=True, decimal_comma=True)
            cost = _parse_number(match.group("cost"))
        except (InvalidOperation, ValueError):
            continue
        if not quantity.is_finite() or not cost.is_finite() or quantity <= 0 or cost < 0:
            continue
        lines.append({
            "name": match.group("name").strip().lower(),
            "qty": float(quantity),
            "unit": (match.group("unit") or "kg").lower(),
            "cost": int(cost),
        })
    return lines


def _parse_number(value: str, *, decimal_dot: bool = False, decimal_comma: bool = False) -> Decimal:
    normalized = value.strip().replace(" ", "")
    if "," in normalized and "." in normalized:
        decimal_separator = "," if normalized.rfind(",") > normalized.rfind(".") else "."
        grouping_separator = "." if decimal_separator == "," else ","
        normalized = normalized.replace(grouping_separator, "").replace(decimal_separator, ".")
    elif "," in normalized:
        normalized = normalized.replace(",", "." if decimal_comma or len(normalized.rsplit(",", 1)[-1]) != 3 else "")
    elif "." in normalized:
        normalized = normalized.replace(".", "" if not decimal_dot and len(normalized.rsplit(".", 1)[-1]) == 3 else ".")
    return Decimal(normalized)


def _parse_model_lines(text: str) -> tuple[List[Dict[str, Any]], str]:
    candidates = [text.strip()]
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if fenced:
        candidates.insert(0, fenced.group(1).strip())
    object_match = re.search(r"\{[\s\S]*\}", text)
    if object_match:
        candidates.append(object_match.group(0))

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        entries = parsed.get("lines", []) if isinstance(parsed, dict) else parsed
        if isinstance(entries, list):
            return [entry for entry in entries if isinstance(entry, dict)], "gemini"

    regex_lines = _regex_parse_lines(text)
    if regex_lines:
        return regex_lines, "regex"
    return [], "manual"


def _default_expiry(name: str, ingredient: Optional[Ingredient]) -> date:
    if ingredient and ingredient.expiry_warning_days is not None:
        warning_days = int(ingredient.expiry_warning_days)
    else:
        normalized = _normalize_name(name)
        if any(token in normalized for token in ("thit", "ca ", "tom", "hai san", "ga ")):
            warning_days = 3
        elif any(token in normalized for token in ("sua", "pho mai", "yogurt", "ya ua")):
            warning_days = 5
        elif any(token in normalized for token in ("gao", "toi", "hanh kho", "dau an")):
            warning_days = 30
        else:
            warning_days = 7
    today = datetime.now(ZoneInfo(settings.TIMEZONE)).date()
    return today + timedelta(days=warning_days)


def _catalog_for_kitchen(db: Session, kitchen_id: UUID) -> List[Ingredient]:
    return list(db.execute(
        select(Ingredient)
        .options(selectinload(Ingredient.aliases))
        .where(
            and_(
                Ingredient.kitchen_id == kitchen_id,
                Ingredient.deleted_at.is_(None)
            )
        )
        .order_by(Ingredient.name.asc())
    ).scalars().all())


@router.post("/parse-csv")
def parse_csv(payload: ParseCsvRequest):
    try:
        lines = DocumentService.parse_csv(payload.csv_text, payload.kind)
        return {"kind": payload.kind, "line_count": len(lines), "lines": lines}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/ingredients")
def list_document_ingredients(
    kitchen_id: UUID = Query(DEMO_KITCHEN_ID, description="ID của bếp"),
    db: Session = Depends(get_db),
):
    ingredients = _catalog_for_kitchen(db, kitchen_id)
    return {
        "ingredients": [
            {
                "id": str(item.id),
                "name": item.name,
                "base_unit_code": item.base_unit_code,
                "default_location": item.default_location,
                "expiry_warning_days": item.expiry_warning_days,
                "aliases": [alias.alias for alias in item.aliases],
            }
            for item in ingredients
        ]
    }


@router.post("/parse-invoice-file")
async def parse_invoice_file(
    file: UploadFile = File(...),
    kitchen_id: UUID = Query(DEMO_KITCHEN_ID, description="ID của bếp"),
    db: Session = Depends(get_db),
):
    content = await file.read(MAX_INVOICE_IMAGE_BYTES + 1)
    if len(content) > MAX_INVOICE_IMAGE_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Tệp tối đa 10 MB.")
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tệp hóa đơn đang trống.")
    file_format = _invoice_file_format(file.content_type, content, file.filename)
    if not file_format or file_format[0] not in {"CSV", "XLSX"}:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Chỉ hỗ trợ tệp CSV hoặc XLSX hợp lệ.",
        )
    try:
        extracted = _parse_tabular_invoice(content, file.filename or file_format[1])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    lines = _match_invoice_lines(extracted, db, kitchen_id)
    if not lines:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Không đọc được dòng hóa đơn hợp lệ. Hãy kiểm tra số lượng và đơn giá trong tệp.",
        )
    return {
        "lines": lines,
        "source": "file",
        "message": f"Đã đọc {len(lines)} dòng từ tệp. Hãy kiểm tra và xác nhận để nhập vào kho.",
    }


@router.post("/scan-invoice-image")
async def scan_invoice_image(
    file: UploadFile = File(...),
    kitchen_id: UUID = Query(DEMO_KITCHEN_ID, description="ID của bếp"),
    db: Session = Depends(get_db),
):
    if file.content_type not in ALLOWED_INVOICE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Chỉ hỗ trợ ảnh JPEG, PNG, WebP hoặc tệp PDF.",
        )
    image_bytes = await file.read(MAX_INVOICE_IMAGE_BYTES + 1)
    if len(image_bytes) > MAX_INVOICE_IMAGE_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Tệp hóa đơn tối đa 10 MB.")
    if not image_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tệp hóa đơn đang trống.")
    if not _invoice_file_format(file.content_type, image_bytes):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nội dung tệp không khớp định dạng ảnh/PDF.")

    if not settings.GEMINI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OCR chưa được bật: backend thiếu GEMINI_API_KEY. Hãy cấu hình key rồi khởi động lại backend.",
        )

    prompt = (
        "Đọc ảnh hoặc PDF hóa đơn nhập nguyên liệu bằng tiếng Việt. Chỉ trả JSON object dạng "
        '{"lines":[{"name":"thịt ba chỉ","qty":1.5,"unit":"kg","cost":120000,'
        '"location":"FRIDGE","expiry_date":null}]}. '
        "Tên nguyên liệu viết thường; qty là số lượng dương; cost là đơn giá nguyên VNĐ; "
        "unit chỉ chọn kg, g, l, ml, quả, hộp, bó, gói hoặc chai. "
        "location chỉ chọn FRIDGE, FREEZER hoặc PANTRY (hàng khô là PANTRY). "
        "expiry_date dùng YYYY-MM-DD chỉ khi nhìn thấy trên hóa đơn, còn lại null. "
        "Bỏ qua tổng tiền, thuế và các dòng không phải hàng hóa. Không đoán số liệu không đọc được; "
        "nếu ảnh mờ hoặc không có mặt hàng, trả về {\"lines\":[]}."
    )
    request_body = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {
                    "inline_data": {
                        "mime_type": file.content_type,
                        "data": base64.b64encode(image_bytes).decode("ascii"),
                    }
                },
            ]
        }],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1},
    }

    extracted: List[Dict[str, Any]] = []
    source = "manual"
    last_http_status: Optional[int] = None
    network_failed = False
    response_received = False
    model_names = list(dict.fromkeys((
        settings.GEMINI_VISION_MODEL,
        settings.GEMINI_BACKUP_VISION_MODEL,
    )))

    async with httpx.AsyncClient(timeout=45.0) as client:
        for model_name in model_names:
            try:
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent",
                    params={"key": settings.GEMINI_API_KEY},
                    json=request_body,
                )
                response.raise_for_status()
                response_data = response.json()
                response_received = True
            except httpx.HTTPStatusError as exc:
                last_http_status = exc.response.status_code
                logger.warning(
                    "Gemini invoice OCR model %s returned HTTP %s",
                    model_name,
                    last_http_status,
                )
                continue
            except (httpx.RequestError, json.JSONDecodeError) as exc:
                network_failed = True
                logger.warning(
                    "Gemini invoice OCR model %s failed: %s",
                    model_name,
                    type(exc).__name__,
                )
                continue

            try:
                model_text = response_data["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError, TypeError):
                model_text = ""
            extracted, source = _parse_model_lines(model_text)
            if extracted:
                if model_name != settings.GEMINI_VISION_MODEL:
                    logger.info("Invoice OCR succeeded using backup model %s", model_name)
                break

            logger.info("Gemini invoice OCR model %s returned no parsable line items", model_name)

    if not extracted and not response_received and last_http_status is not None:
        if last_http_status in {401, 403}:
            detail = "Gemini từ chối quyền truy cập API/model. Kiểm tra API key và quyền sử dụng model; lỗi này không phải quyền camera."
        else:
            detail = f"Dịch vụ OCR từ chối yêu cầu (HTTP {last_http_status}). Kiểm tra API key hoặc thử lại sau."
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)
    if not extracted and not response_received and network_failed:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Không kết nối hoặc đọc được phản hồi từ các model OCR. Kiểm tra mạng rồi thử lại.",
        )

    lines = _match_invoice_lines(extracted, db, kitchen_id)

    message = (
        "Không đọc được mặt hàng rõ ràng. Hãy chọn nguyên liệu và bổ sung số liệu trong bảng."
        if not lines else
        "Đã bóc tách bằng quy tắc dự phòng; vui lòng kiểm tra kỹ."
        if source == "regex" else
        "Đã quét hóa đơn. Vui lòng kiểm tra lại số liệu trước khi xác nhận."
    )
    return {"lines": lines, "source": source, "message": message}


@router.post("/receipts", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def commit_receipt(
    kitchen_id: UUID = Query(..., description="ID của bếp"),
    payload: CommitReceiptRequest = ...,
    db: Session = Depends(get_db),
):
    try:
        if payload.file_sha256:
            duplicate = db.execute(
                select(Document.id).where(
                    and_(
                        Document.kitchen_id == kitchen_id,
                        Document.kind == "IMPORT_INVOICE",
                        Document.file_sha256 == payload.file_sha256,
                        Document.status != "CANCELLED",
                    )
                )
            ).scalar_one_or_none()
            if duplicate:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Hóa đơn này đã được nhập kho.")

        doc = DocumentService.commit_receipt(
            db=db,
            kitchen_id=str(kitchen_id),
            business_date=payload.business_date,
            lines=[line.model_dump(mode="python") for line in payload.lines],
            file_sha256=payload.file_sha256,
            original_filename=payload.original_filename,
        )
        db.commit()
        db.refresh(doc)
        return _receipt_response(doc)
    except HTTPException:
        db.rollback()
        raise
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Không thể ghi chứng từ; hóa đơn có thể đã được nhập trước đó.",
        ) from exc


@router.post("/receipts/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_receipt(
    kitchen_id: UUID = Query(..., description="ID của bếp"),
    payload: str = Form(..., description="Metadata hóa đơn dạng JSON"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    try:
        receipt = CommitReceiptRequest.model_validate_json(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Metadata hóa đơn không hợp lệ.") from exc

    content = await file.read(MAX_INVOICE_IMAGE_BYTES + 1)
    file_format = _invoice_file_format(file.content_type, content, file.filename)
    if len(content) > MAX_INVOICE_IMAGE_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Tệp hóa đơn tối đa 10 MB.")
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tệp hóa đơn đang trống.")
    if not file_format:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Chỉ nhận ảnh, PDF, CSV hoặc XLSX hợp lệ.",
        )

    file_hash = DocumentService.calculate_file_hash(content)
    if receipt.file_sha256 and receipt.file_sha256 != file_hash:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mã kiểm tra tệp hóa đơn không khớp.")
    duplicate = db.execute(
        select(Document.id).where(
            and_(
                Document.kitchen_id == kitchen_id,
                Document.kind == "IMPORT_INVOICE",
                Document.file_sha256 == file_hash,
                Document.status != "CANCELLED",
            )
        )
    ).scalar_one_or_none()
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Hóa đơn này đã được nhập kho.")

    storage_dir = Path(settings.INVOICE_STORAGE_DIR)
    storage_dir.mkdir(parents=True, exist_ok=True)
    storage_key = f"{uuid4()}{file_format[1]}"
    storage_path = storage_dir / storage_key
    safe_filename = os.path.basename(
        (file.filename or f"invoice{file_format[1]}").replace("\\", "/")
    ).replace("\x00", "")
    try:
        storage_path.write_bytes(content)
        doc = DocumentService.commit_receipt(
            db=db,
            kitchen_id=str(kitchen_id),
            business_date=receipt.business_date,
            lines=[line.model_dump(mode="python") for line in receipt.lines],
            file_sha256=file_hash,
            original_filename=safe_filename,
            storage_key=storage_key,
            source_format=file_format[0],
        )
        db.commit()
        db.refresh(doc)
        return _receipt_response(doc)
    except HTTPException:
        db.rollback()
        storage_path.unlink(missing_ok=True)
        raise
    except ValueError as exc:
        db.rollback()
        storage_path.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        storage_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Không thể ghi chứng từ; hóa đơn có thể đã được nhập trước đó.",
        ) from exc
    except OSError as exc:
        db.rollback()
        if storage_path.exists():
            storage_path.unlink()
        logger.exception("Could not save uploaded invoice")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Không lưu được tệp hóa đơn.") from exc
    except Exception:
        db.rollback()
        try:
            storage_path.unlink(missing_ok=True)
        except OSError:
            logger.exception("Could not remove invoice file after failed database commit")
        raise


@router.get("/{document_id}/file")
def download_document_file(
    document_id: UUID,
    kitchen_id: UUID = Query(..., description="ID của bếp"),
    db: Session = Depends(get_db),
):
    doc = db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.kitchen_id == kitchen_id,
            Document.kind == "IMPORT_INVOICE",
        )
    ).scalar_one_or_none()
    if not doc or not doc.storage_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tệp hóa đơn.")

    storage_dir = Path(settings.INVOICE_STORAGE_DIR).resolve()
    storage_path = (storage_dir / doc.storage_key).resolve()
    if storage_path.parent != storage_dir or not storage_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tệp hóa đơn không còn khả dụng.")
    download_name = os.path.basename(
        (doc.original_filename or storage_path.name).replace("\\", "/")
    ).replace("\r", "").replace("\n", "")
    media_type = {
        "IMAGE": {
            ".jpg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
        }.get(storage_path.suffix.lower(), "application/octet-stream"),
        "PDF": "application/pdf",
        "CSV": "text/csv",
        "XLSX": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }.get(doc.source_format, "application/octet-stream")
    return FileResponse(storage_path, media_type=media_type, filename=download_name)


@router.post("/sales-reports", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def commit_sales_report(
    kitchen_id: str = Query(..., description="ID của bếp"),
    payload: CommitSalesReportRequest = ...,
    db: Session = Depends(get_db),
):
    try:
        doc = DocumentService.commit_sales_report(
            db=db,
            kitchen_id=kitchen_id,
            business_date=payload.business_date,
            lines=payload.lines,
            file_sha256=payload.file_sha256,
            original_filename=payload.original_filename,
        )
        db.commit()
        db.refresh(doc)
        return doc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
