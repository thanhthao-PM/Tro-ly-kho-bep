"""
Hằng số và Enum chuẩn cho toàn bộ hệ thống Trợ lý kho bếp.
Tuân thủ nghiêm ngặt theo Architecture Revision 6.3.
"""
from enum import Enum


class UnitDimension(str, Enum):
    MASS = "MASS"
    VOLUME = "VOLUME"
    COUNT = "COUNT"


class StorageLocation(str, Enum):
    FRIDGE = "FRIDGE"
    FREEZER = "FREEZER"
    PANTRY = "PANTRY"


class ExpiryStatus(str, Enum):
    EXPIRED = "EXPIRED"
    EXPIRES_SOON = "EXPIRES_SOON"
    OK = "OK"
    NO_EXPIRY = "NO_EXPIRY"


class MovementType(str, Enum):
    RECEIPT = "RECEIPT"
    SALE_CONSUMPTION = "SALE_CONSUMPTION"
    USAGE_CONSUMPTION = "USAGE_CONSUMPTION"
    DONATION = "DONATION"
    SELLOFF = "SELLOFF"
    WASTE = "WASTE"
    ADJUSTMENT_IN = "ADJUSTMENT_IN"
    ADJUSTMENT_OUT = "ADJUSTMENT_OUT"
    REVERSAL = "REVERSAL"


class DocumentKind(str, Enum):
    IMPORT_INVOICE = "IMPORT_INVOICE"
    SALES_REPORT = "SALES_REPORT"
    USAGE_SLIP = "USAGE_SLIP"


class DocumentSourceFormat(str, Enum):
    CSV = "CSV"
    XLSX = "XLSX"
    IMAGE = "IMAGE"
    PDF = "PDF"
    MANUAL = "MANUAL"


class DocumentStatus(str, Enum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


class OCRStatus(str, Enum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    PENDING = "PENDING"
    DONE = "DONE"
    FAILED = "FAILED"


class SaleOrigin(str, Enum):
    NORMAL = "NORMAL"
    REPURPOSE = "REPURPOSE"


class ConsumptionStatus(str, Enum):
    FULL = "FULL"
    PARTIAL = "PARTIAL"
    RESOLVED = "RESOLVED"


class ShortageStatus(str, Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"


class ShortageResolution(str, Enum):
    CONSUMED_FROM_STOCK = "CONSUMED_FROM_STOCK"
    WRITTEN_OFF_ESTIMATED = "WRITTEN_OFF_ESTIMATED"
    WAIVED = "WAIVED"


class DisposalType(str, Enum):
    DONATION = "DONATION"
    SELLOFF = "SELLOFF"
    WASTE = "WASTE"


class WasteReason(str, Enum):
    EXPIRED = "EXPIRED"
    SPOILED = "SPOILED"
    OVERSTOCK = "OVERSTOCK"
    OTHER = "OTHER"


class NotificationKind(str, Enum):
    EXPIRED = "EXPIRED"
    EXPIRING_SOON = "EXPIRING_SOON"
    LOW_STOCK = "LOW_STOCK"
    OPEN_SHORTAGE = "OPEN_SHORTAGE"
    MOVEMENT = "MOVEMENT"


class NotificationSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"


class IdempotencyStatus(str, Enum):
    CLAIMED = "CLAIMED"
    COMPLETED = "COMPLETED"
