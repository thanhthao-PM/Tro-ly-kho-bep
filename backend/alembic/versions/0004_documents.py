"""0004 documents, document_lines, idempotency_keys (Rev 3 II.2, Rev 4 2.C/4.1/4.2)"""
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

UP = [
"""CREATE TABLE documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  kitchen_id uuid NOT NULL REFERENCES kitchens (id),
  kind text NOT NULL,
  source_format text NOT NULL,
  status text NOT NULL,
  business_date date NOT NULL,
  file_sha256 text,
  storage_key text,
  original_filename text,
  ocr_status text NOT NULL,
  created_by uuid REFERENCES user_profiles (id),
  created_at timestamptz NOT NULL DEFAULT now(),
  confirmed_at timestamptz,
  CONSTRAINT uq_documents_kid UNIQUE (kitchen_id, id),
  CONSTRAINT ck_documents_kind CHECK (kind IN ('IMPORT_INVOICE','SALES_REPORT','USAGE_SLIP')),
  CONSTRAINT ck_documents_format CHECK (source_format IN ('CSV','XLSX','IMAGE','PDF','MANUAL')),
  CONSTRAINT ck_documents_status CHECK (status IN ('DRAFT','CONFIRMED','CANCELLED')),
  CONSTRAINT ck_documents_ocr CHECK (ocr_status IN ('NOT_APPLICABLE','PENDING','DONE','FAILED'))
)""",
"""CREATE UNIQUE INDEX uq_documents_hash ON documents (kitchen_id, kind, file_sha256)
  WHERE status <> 'CANCELLED' AND file_sha256 IS NOT NULL""",
"CREATE INDEX ix_documents_status ON documents (kitchen_id, status, created_at)",
"""CREATE TABLE document_lines (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  kitchen_id uuid NOT NULL REFERENCES kitchens (id),
  document_id uuid NOT NULL,
  line_no integer NOT NULL,
  raw_text text,
  parsed_name text,
  ingredient_id uuid,
  dish_id uuid,
  quantity numeric(14,3),
  unit_code text REFERENCES units (code),
  unit_price_vnd numeric(18,2),
  line_total_vnd bigint,
  expiry_date date,
  confidence jsonb,
  flags text[] NOT NULL DEFAULT '{}',
  is_selected boolean NOT NULL DEFAULT true,
  CONSTRAINT uq_doclines_kid UNIQUE (kitchen_id, id),
  CONSTRAINT uq_doclines_lineno UNIQUE (document_id, line_no),
  CONSTRAINT fk_doclines_document FOREIGN KEY (kitchen_id, document_id) REFERENCES documents (kitchen_id, id),
  CONSTRAINT fk_doclines_ingredient FOREIGN KEY (kitchen_id, ingredient_id) REFERENCES ingredients (kitchen_id, id),
  CONSTRAINT fk_doclines_dish FOREIGN KEY (kitchen_id, dish_id) REFERENCES dishes (kitchen_id, id),
  CONSTRAINT ck_doclines_not_both CHECK (NOT (ingredient_id IS NOT NULL AND dish_id IS NOT NULL))
)""",
"""CREATE TABLE idempotency_keys (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  kitchen_id uuid NOT NULL REFERENCES kitchens (id),
  endpoint text NOT NULL,
  key text NOT NULL,
  request_hash text NOT NULL,
  actor_id uuid REFERENCES user_profiles (id),
  status text NOT NULL,
  response_status integer,
  response_body jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz,
  CONSTRAINT uq_idem UNIQUE (kitchen_id, endpoint, key),
  CONSTRAINT ck_idem_status CHECK (status IN ('CLAIMED','COMPLETED'))
)""",
"CREATE INDEX ix_idem_created ON idempotency_keys (created_at)",
]
DOWN = ["DROP TABLE idempotency_keys", "DROP TABLE document_lines", "DROP TABLE documents"]


def upgrade() -> None:
    for s in UP:
        op.execute(s)


def downgrade() -> None:
    for s in DOWN:
        op.execute(s)
