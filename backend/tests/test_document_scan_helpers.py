import unittest
from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.session import get_db
from app.main import app
from app.api.v1.endpoints.documents import (
    CommitReceiptLine,
    _normalize_name,
    _parse_model_lines,
    _parse_number,
)


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
            self.assertEqual(response.status_code, 503)
            self.assertIn("GEMINI_API_KEY", response.json()["detail"])
        finally:
            settings.GEMINI_API_KEY = original_key
            app.dependency_overrides.pop(get_db, None)


if __name__ == "__main__":
    unittest.main()
