"""
Khai báo Base declarative cho toàn bộ SQLAlchemy Models.
Tập hợp toàn bộ models để Alembic autogenerate và di trú dữ liệu chính xác.
"""
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass


class Base(DeclarativeBase):
    pass
