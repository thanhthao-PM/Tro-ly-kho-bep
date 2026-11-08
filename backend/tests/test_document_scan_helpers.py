import unittest
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch
from uuid import UUID

import httpx
from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.core.config import settings
from app.db.session import get_db
from app.main import app
from app.api.v1.endpoints.documents import (
    CommitReceiptLine,
    _invoice_file_format,
    _normalize_name,
    _parse_model_lines,
    _parse_number,
    _parse_tabular_invoice,
)
from app.services.document_service import DocumentService


class TestInvoiceScanHelpers(unittest.TestCase):
    def test_normalizes_vietnamese_ingredient_names(self):
        self.assertEqual(_normalize_name("Thịt Ba Chỉ"), "thit ba chi")
        self.assertEqual(_normalize_name("Đậu hũ"), "dau hu")

    def test_parses_vietnamese_number_formats(self):
        self.assertEqual(_parse_number("1,5"), Decimal("1.5"))
        self.assertEqual(_parse_number("35.000"), Decimal("35000"))
        self.assertEqual(_parse_number("1.234,56"), Decimal("1234.56"))
        self.assertEqual(_parse_number("1.234", decimal_dot=True), Decimal("1.234"))
        self.assertEqual(_parse_number("1,234", decimal_comma=True), Decimal("1.234"))

    def test_reads_structured_json_from_model(self):
        lines, source = _parse_model_lines(
            '{"lines":[{"name":"cà chua","qty":2,"unit":"kg","cost":35000}]}'
        )
        self.assertEqual(source, "gemini")
        self.assertEqual(lines[0]["name"], "cà chua")

    def test_accepts_valid_invoice_image_and_pdf_signatures(self):
        self.assertEqual(_invoice_file_format("image/jpeg", b"\xff\xd8\xffdata"), ("IMAGE", ".jpg"))
        self.assertEqual(_invoice_file_format("application/pdf", b"%PDF-1.7 data"), ("PDF", ".pdf"))
        self.assertIsNone(_invoice_file_format("application/pdf", b"not a pdf"))
        self.assertIsNone(_invoice_file_format("text/plain", b"%PDF-1.7 data"))

    def test_reads_csv_with_vietnamese_decimal_and_thousands_formats(self):
        lines = DocumentService.parse_csv(
            "Tên;Số lượng;Đơn vị;Đơn giá\nCà chua;1,5;kg;35.000\nRau muống;1.234;kg;1.234,50",
            "IMPORT_INVOICE",
        )
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0]["quantity"], Decimal("1.5"))
        self.assertEqual(lines[0]["unit_cost"], Decimal("35000"))
        self.assertEqual(lines[1]["quantity"], Decimal("1.234"))
        self.assertEqual(lines[1]["unit_cost"], Decimal("1234.50"))

    def test_reads_xlsx_invoice_rows(self):
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.append(["Tên nguyên liệu", "Số lượng", "Đơn vị", "Đơn giá"])
        worksheet.append(["Cà chua", 2, "kg", 35000])
        content = BytesIO()
        workbook.save(content)
        data = content.getvalue()

        self.assertEqual(
            _invoice_file_format(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                data,
                "invoice.xlsx",
            ),
            ("XLSX", ".xlsx"),
        )
        lines = _parse_tabular_invoice(data, "invoice.xlsx")
        self.assertEqual(lines, [{"name": "Cà chua", "qty": 2.0, "unit": "kg", "cost": 35000}])

    def test_parse_invoice_file_endpoint_returns_importable_lines(self):
        class EmptyScalars:
            @staticmethod
            def all():
                return []

        class EmptyResult:
            @staticmethod
            def scalars():
                return EmptyScalars()

        class EmptyDatabase:
            @staticmethod
            def execute(_statement):
                return EmptyResult()

        app.dependency_overrides[get_db] = lambda: EmptyDatabase()
        try:
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/documents/parse-invoice-file",
                    params={"kitchen_id": "00000000-0000-0000-0000-000000000002"},
                    files={
                        "file": (
                            "invoice.csv",
                            "Tên;Số lượng;Đơn vị;Đơn giá\nCà chua;2;kg;35.000".encode("utf-8"),
                            "text/csv",
                        )
                    },
                )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["lines"][0]["qty"], 2.0)
            self.assertEqual(response.json()["lines"][0]["cost"], 35000)
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_uses_regex_when_model_returns_delimited_text(self):
        lines, source = _parse_model_lines("cà chua, 2, kg, 35.000")
        self.assertEqual(source, "regex")
        self.assertEqual(lines[0]["qty"], 2)
        self.assertEqual(lines[0]["cost"], 35000)

    def test_receipt_request_accepts_frontend_field_names(self):
        line = CommitReceiptLine.model_validate({
            "ingredient_id": str(UUID("11111111-0004-0000-0000-000000000004")),
            "name": "cà chua",
            "qty": 2,
            "unit": "kg",
            "cost": 35000,
        })
        self.assertEqual(line.quantity, Decimal("2"))
        self.assertEqual(line.unit_code, "kg")
        self.assertEqual(line.unit_cost, Decimal("35000"))

    def test_receipt_request_accepts_unresolved_ingredient_name(self):
        line = CommitReceiptLine.model_validate({
            "name": "Cà chua",
            "quantity": 2,
            "unit": "kg",
            "unit_cost": 35000,
        })
        self.assertIsNone(line.ingredient_id)
        self.assertEqual(line.name, "Cà chua")

    def test_scan_endpoint_reports_missing_api_key(self):
        original_key = settings.GEMINI_API_KEY
        settings.GEMINI_API_KEY = ""
        app.dependency_overrides[get_db] = lambda: None
        try:
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/documents/scan-invoice-image",
                    params={"kitchen_id": "00000000-0000-0000-0000-000000000002"},
                    files={"file": ("invoice.jpg", b"\xff\xd8\xfftest", "image/jpeg")},
                )
                pdf_response = client.post(
                    "/api/v1/documents/scan-invoice-image",
                    params={"kitchen_id": "00000000-0000-0000-0000-000000000002"},
                    files={"file": ("invoice.pdf", b"%PDF-1.7 test", "application/pdf")},
                )
            self.assertEqual(response.status_code, 503)
            self.assertIn("GEMINI_API_KEY", response.json()["detail"])
            self.assertEqual(pdf_response.status_code, 503)
            self.assertIn("GEMINI_API_KEY", pdf_response.json()["detail"])
        finally:
            settings.GEMINI_API_KEY = original_key
            app.dependency_overrides.pop(get_db, None)

    def test_scan_endpoint_uses_backup_model_after_primary_model_fails(self):
        class EmptyScalars:
            @staticmethod
            def all():
                return []

        class EmptyResult:
            @staticmethod
            def scalars():
                return EmptyScalars()

        class EmptyDatabase:
            @staticmethod
            def execute(_statement):
                return EmptyResult()

        class FakeResponse:
            def raise_for_status(self):
                return None

            @staticmethod
            def json():
                return {
                    "candidates": [{
                        "content": {
                            "parts": [{
                                "text": '{"lines":[{"name":"cà chua","qty":2,"unit":"kg","cost":35000}]}'
                            }]
                        }
                    }]
                }

        class FakeClient:
            def __init__(self, timeout):
                self.models = []

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return None

            async def post(self, url, **_kwargs):
                model_name = url.split("/models/", 1)[1].split(":", 1)[0]
                self.models.append(model_name)
                if model_name == settings.GEMINI_VISION_MODEL:
                    request = httpx.Request("POST", url)
                    response = httpx.Response(404, request=request)
                    raise httpx.HTTPStatusError("model unavailable", request=request, response=response)
                return FakeResponse()

        original_key = settings.GEMINI_API_KEY
        settings.GEMINI_API_KEY = "test-key"
        app.dependency_overrides[get_db] = lambda: EmptyDatabase()
        try:
            with patch("app.api.v1.endpoints.documents.httpx.AsyncClient", FakeClient):
                with TestClient(app) as client:
                    response = client.post(
                        "/api/v1/documents/scan-invoice-image",
                        params={"kitchen_id": "00000000-0000-0000-0000-000000000002"},
                        files={"file": ("invoice.jpg", b"\xff\xd8\xfftest", "image/jpeg")},
                    )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["lines"][0]["name"], "cà chua")
        finally:
            settings.GEMINI_API_KEY = original_key
            app.dependency_overrides.pop(get_db, None)


if __name__ == "__main__":
    unittest.main()
