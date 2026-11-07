"""0004: Documents, Document Lines, and Idempotency Keys

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-07 10:15:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. documents
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("kitchen_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kitchens.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("source_format", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default="DRAFT", nullable=False),
        sa.Column("business_date", sa.Date(), nullable=False),
        sa.Column("original_filename", sa.Text(), nullable=True),
        sa.Column("file_sha256", sa.Text(), nullable=True),
        sa.Column("storage_key", sa.Text(), nullable=True),
        sa.Column("ocr_status", sa.Text(), server_default="NOT_APPLICABLE", nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("kitchen_id", "id", name="uq_documents_kitchen_id"),
        sa.CheckConstraint("kind IN ('IMPORT_INVOICE', 'SALES_REPORT', 'USAGE_SLIP')", name="chk_documents_kind"),
        sa.CheckConstraint("source_format IN ('CSV', 'XLSX', 'IMAGE', 'PDF', 'MANUAL')", name="chk_documents_source_format"),
        sa.CheckConstraint("status IN ('DRAFT', 'CONFIRMED', 'CANCELLED')", name="chk_documents_status"),
        sa.CheckConstraint("ocr_status IN ('NOT_APPLICABLE', 'PENDING', 'DONE', 'FAILED')", name="chk_documents_ocr_status"),
    )
    op.create_index(
        "uq_documents_hash",
        "documents",
        ["kitchen_id", "kind", "file_sha256"],
        unique=True,
        postgresql_where=sa.text("status <> 'CANCELLED' AND file_sha256 IS NOT NULL")
    )
    op.create_index("idx_documents_status", "documents", ["kitchen_id", "status", "created_at"])

    # 2. document_lines
    op.create_table(
        "document_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("kitchen_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("parsed_name", sa.Text(), nullable=True),
        sa.Column("ingredient_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("dish_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("quantity", sa.Numeric(14, 3), nullable=True),
        sa.Column("unit_code", sa.Text(), sa.ForeignKey("units.code", ondelete="RESTRICT"), nullable=True),
        sa.Column("unit_price_vnd", sa.Numeric(18, 2), nullable=True),
        sa.Column("line_total_vnd", sa.BigInteger(), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("confidence", postgresql.JSONB(), nullable=True),
        sa.Column("flags", postgresql.ARRAY(sa.Text()), server_default="{}", nullable=False),
        sa.Column("is_selected", sa.Boolean(), server_default="true", nullable=False),
        sa.ForeignKeyConstraint(
            ["kitchen_id", "document_id"],
            ["documents.kitchen_id", "documents.id"],
            ondelete="CASCADE",
            name="fk_document_lines_document"
        ),
        sa.UniqueConstraint("kitchen_id", "id", name="uq_document_lines_kitchen_id"),
        sa.UniqueConstraint("document_id", "line_no", name="uq_document_lines_document_line_no"),
        sa.CheckConstraint("NOT (ingredient_id IS NOT NULL AND dish_id IS NOT NULL)", name="chk_document_lines_not_both_targets"),
    )

    # 3. idempotency_keys
    op.create_table(
        "idempotency_keys",
        sa.Column("kitchen_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("request_hash", sa.Text(), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("response_body", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("kitchen_id", "endpoint", "key", name="pk_idempotency_keys"),
        sa.CheckConstraint("status IN ('CLAIMED', 'COMPLETED')", name="chk_idempotency_status"),
    )
    op.create_index("idx_idempotency_created_at", "idempotency_keys", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_idempotency_created_at", table_name="idempotency_keys")
    op.drop_table("idempotency_keys")
    op.drop_table("document_lines")
    op.drop_index("idx_documents_status", table_name="documents")
    op.drop_index("uq_documents_hash", table_name="documents")
    op.drop_table("documents")
