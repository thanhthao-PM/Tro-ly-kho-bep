"""
Unit test độc lập cho Parser CSV và tính hash SHA-256 chống nạp trùng.
Tuân thủ Architecture Revision 6.3.
"""
import unittest
import hashlib
import io
import csv
from decimal import Decimal


def calculate_file_hash(content_bytes: bytes) -> str:
    return hashlib.sha256(content_bytes).hexdigest()


def parse_csv(csv_content: str, kind: str):
    lines = []
    reader = csv.reader(io.StringIO(csv_content), delimiter=',', skipinitialspace=True)
    for row_idx, row in enumerate(reader, start=1):
        if not row or not any(row):
            continue
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
                "parsed_name": name,
                "quantity": qty,
                "unit_text": unit,
                "unit_cost": cost
            })
        else:
            lines.append({
                "line_number": row_idx,
                "target_type": "DISH",
                "parsed_name": name,
                "quantity": qty
            })
    return lines


class TestDocumentServiceUnit(unittest.TestCase):

    def test_calculate_file_hash(self):
        sample_data = b"rau muong,10,22000\nuc ga,1.5,88000"
        expected = hashlib.sha256(sample_data).hexdigest()
        actual = calculate_file_hash(sample_data)
        self.assertEqual(expected, actual)

    def test_parse_import_invoice_csv(self):
        csv_text = """rau muống, 10, 22000
        ức gà, 1.5, 88000
        nấm, 1, kg, 92000
        hành lá, 3, bó, 8000"""

        lines = parse_csv(csv_text, "IMPORT_INVOICE")
        self.assertEqual(len(lines), 4)

        self.assertEqual(lines[0]["parsed_name"], "rau muống")
        self.assertEqual(lines[0]["quantity"], Decimal("10"))
        self.assertEqual(lines[0]["unit_cost"], Decimal("22000"))

        self.assertEqual(lines[1]["parsed_name"], "ức gà")
        self.assertEqual(lines[1]["quantity"], Decimal("1.5"))
        self.assertEqual(lines[1]["unit_cost"], Decimal("88000"))

        self.assertEqual(lines[2]["parsed_name"], "nấm")
        self.assertEqual(lines[2]["quantity"], Decimal("1"))
        self.assertEqual(lines[2]["unit_text"], "kg")
        self.assertEqual(lines[2]["unit_cost"], Decimal("92000"))

    def test_parse_sales_report_csv(self):
        csv_text = """Trứng chiên cà chua, 4
        Cơm chiên trứng, 3
        Gà xào nấm, 3"""

        lines = parse_csv(csv_text, "SALES_REPORT")
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[0]["parsed_name"], "Trứng chiên cà chua")
        self.assertEqual(lines[0]["quantity"], Decimal("4"))
        self.assertEqual(lines[0]["target_type"], "DISH")


if __name__ == "__main__":
    unittest.main()
