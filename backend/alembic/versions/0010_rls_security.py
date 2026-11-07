"""0010: Row Level Security (RLS) Baseline

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-07 10:45:00

"""
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

TABLES = [
    "user_profiles",
    "kitchens",
    "kitchen_settings",
    "units",
    "ingredients",
    "ingredient_aliases",
    "ingredient_unit_conversions",
    "batches",
    "stock_movements",
    "dishes",
    "recipe_items",
    "documents",
    "document_lines",
    "idempotency_keys",
    "sales",
    "sale_lines",
    "stock_shortages",
    "disposals",
    "notification_reads",
    "audit_log",
]


def upgrade() -> None:
    # Bật Row Level Security trên toàn bộ bảng
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")

    # Thu hồi quyền mặc định từ anon và authenticated nếu các role này tồn tại (ví dụ trên Supabase)
    op.execute("""
    DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
            REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon;
            REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon;
            REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM anon;
        END IF;

        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
            REVOKE ALL ON ALL TABLES IN SCHEMA public FROM authenticated;
            REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM authenticated;
            REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM authenticated;
        END IF;
    END $$;
    """)


def downgrade() -> None:
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")
