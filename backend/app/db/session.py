"""
Quản lý kết nối cơ sở dữ liệu SQLAlchemy 2.x (Synchronous mode).
Tuân thủ quyết định D2 & D21: Sử dụng synchronous SQLAlchemy với psycopg 3 driver.
"""
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings

# Engine kết nối PostgreSQL
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.DEBUG and settings.APP_ENV == "development"
)

# Session factory
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)


def get_db() -> Generator[Session, None, None]:
    """Dependency cung cấp SQLAlchemy session cho các router FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
