"""0006 sales, sale_lines (Rev 3 II.2, Rev 4 2.D/2.F/4.1, Rev 5 2.1)"""
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

UP = [
"""CREATE TABLE sales (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  kitchen_id uuid NOT NULL REFERENCES kitchens (id),
  business_date date NOT NULL,
  source_document_id uuid,
  created_by uuid REFERENCES user_profiles (id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_sales_kid UNIQUE (kitchen_id, id),
  CONSTRAINT fk_sales_document FOREIGN KEY (kitchen_id, source_document_id) REFERENCES documents (kitchen_id, id)
)""",
"CREATE UNIQUE INDEX uq_sales_source_document ON sales (source_document_id) WHERE source_document_id IS NOT NULL",
"CREATE INDEX ix_sales_date ON sales (kitchen_id, business_date)",
# cogs_vnd / consumption_status are caches written only by settle_sale_lines (6.3 s3.4).
"""CREATE TABLE sale_lines (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  kitchen_id uuid NOT NULL REFERENCES kitchens (id),
  sale_id uuid NOT NULL,
  dish_id uuid NOT NULL,
  dish_name_snapshot text NOT NULL,
  quantity integer NOT NULL,
  unit_price_snapshot_vnd bigint NOT NULL,
  revenue_vnd bigint NOT NULL,
  cogs_vnd bigint NOT NULL DEFAULT 0,
  consumption_status text NOT NULL DEFAULT 'FULL',
  origin text NOT NULL DEFAULT 'NORMAL',
  source_batch_id uuid,
  CONSTRAINT uq_salelines_kid UNIQUE (kitchen_id, id),
  CONSTRAINT fk_salelines_sale FOREIGN KEY (kitchen_id, sale_id) REFERENCES sales (kitchen_id, id),
  CONSTRAINT fk_salelines_dish FOREIGN KEY (kitchen_id, dish_id) REFERENCES dishes (kitchen_id, id),
  CONSTRAINT fk_salelines_batch FOREIGN KEY (kitchen_id, source_batch_id) REFERENCES batches (kitchen_id, id),
  CONSTRAINT ck_salelines_qty CHECK (quantity > 0),
  CONSTRAINT ck_salelines_cogs CHECK (cogs_vnd >= 0),
  CONSTRAINT ck_salelines_status CHECK (consumption_status IN ('FULL','PARTIAL','RESOLVED')),
  CONSTRAINT ck_salelines_origin CHECK (origin IN ('NORMAL','REPURPOSE')),
  CONSTRAINT ck_salelines_origin_batch CHECK (
    (origin = 'REPURPOSE' AND source_batch_id IS NOT NULL)
    OR (origin = 'NORMAL' AND source_batch_id IS NULL))
)""",
"CREATE INDEX ix_salelines_sale ON sale_lines (kitchen_id, sale_id)",
"CREATE INDEX ix_salelines_dish ON sale_lines (kitchen_id, dish_id)",
]
DOWN = ["DROP TABLE sale_lines", "DROP TABLE sales"]


def upgrade() -> None:
    for s in UP:
        op.execute(s)


def downgrade() -> None:
    for s in DOWN:
        op.execute(s)
