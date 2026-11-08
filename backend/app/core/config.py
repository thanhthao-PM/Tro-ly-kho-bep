"""
Cấu hình tập trung cho toàn bộ ứng dụng FastAPI.
Quản lý các tham số mặc định của Revision 6.3 không bị hardcode rải rác.
"""
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # App Environment
    APP_NAME: str = "Trợ lý kho bếp (Kitchen Inventory Assistant)"
    APP_ENV: str = Field(default="development", description="development | production | test")
    DEBUG: bool = True
    TIMEZONE: str = "Asia/Ho_Chi_Minh"

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+psycopg://postgres:postgres_password_123@localhost:5432/kitchen_inventory",
        description="URL kết nối PostgreSQL qua SQLAlchemy 2.x"
    )
    ADMIN_DATABASE_URL: str = Field(
        default="postgresql+psycopg://postgres:postgres_password_123@localhost:5432/kitchen_inventory",
        description="URL dành riêng cho migration và reset script (owner role)"
    )

    # JWT Authentication
    JWT_SECRET: str = Field(default="super_secret_jwt_key_change_in_production_123456")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 720  # 30 ngày cho demo

    # Gemini OCR for invoice images
    GEMINI_API_KEY: str = ""
    GEMINI_VISION_MODEL: str = "gemini-2.5-flash"

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:5173"
    ]

    # ==========================================
    # CÁC THAM SỐ NGHIỆP VỤ MẶC ĐỊNH (REVISION 6.3)
    # ==========================================
    # Số ngày trước hạn để bắt đầu cảnh báo cận date
    DEFAULT_EXPIRY_WARNING_DAYS: int = 3

    # Cửa sổ ngày tính mức tiêu thụ bình quân (D25)
    DEFAULT_CONSUMPTION_WINDOW_DAYS: int = 14

    # Số ngày tồn kho mục tiêu cần duy trì (D25)
    DEFAULT_TARGET_COVERAGE_DAYS: int = 3

    # Số ngày lịch sử tiêu thụ tối thiểu để kích hoạt công thức D25
    DEFAULT_MIN_HISTORY_DAYS: int = 7

    # Tỷ lệ cảnh báo số lượng nhập bất thường so với lịch sử (ví dụ gấp đôi)
    DEFAULT_UNUSUAL_QUANTITY_RATIO: float = 2.0

    # Giới hạn số ngày lùi khi nhập báo cáo hồi tố
    DEFAULT_BACKDATE_LIMIT_DAYS: int = 2

    # Chính sách hàng quá hạn (mặc định chỉ cho phép huỷ WASTE)
    DEFAULT_EXPIRED_BATCHES_CONSUMABLE: bool = False
    DEFAULT_EXPIRED_BATCH_ACTIONS: List[str] = ["WASTE"]

    # Thời gian giữ khóa Idempotency (giờ)
    IDEMPOTENCY_RETENTION_HOURS: int = 24

    # Demo reset
    ALLOW_DEMO_RESET: bool = True


settings = Settings()
