"""0008 stock_shortages (Rev 3 II.2, Rev 4 2.F/4.1/4.2). Created before stock_movements (Rev 4 s5)."""
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

UP = [
"""CREATE TABLE stock_shortages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  kitchen_id uuid NOT NULL REFERENCES kitchens (id),
  sale_line_id uuid,
  document_line_id uuid,
  ingredient_id uuid NOT NULL,
  short_qty numeric(14,3) NOT NULL,
  status text NOT NULL DEFAULT 'OPEN',
  resolution text,
  estimated_unit_cost numeric(18,6),
  estimated_cost_vnd bigint,
  estimate_batch_id uuid,
  resolution_note text,
  resolved_at timestamptz,
  resolved_by uuid REFERENCES user_profiles (id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_shortages_kid UNIQUE (kitchen_id, id),
  CONSTRAINT fk_shortages_saleline FOREIGN KEY (kitchen_id, sale_line_id) REFERENCES sale_lines (kitchen_id, id),
  CONSTRAINT fk_shortages_docline FOREIGN KEY (kitchen_id, document_line_id) REFERENCES document_lines (kitchen_id, id),
  CONSTRAINT fk_shortages_ingredient FOREIGN KEY (kitchen_id, ingredient_id) REFERENCES ingredients (kitchen_id, id),
  CONSTRAINT fk_shortages_estbatch FOREIGN KEY (kitchen_id, estimate_batch_id) REFERENCES batches (kitchen_id, id),
  CONSTRAINT ck_shortages_qty CHECK (short_qty > 0),
  CONSTRAINT ck_shortages_status CHECK (status IN ('OPEN','RESOLVED')),
  CONSTRAINT ck_shortages_resolution CHECK (resolution IS NULL OR resolution IN ('CONSUMED_FROM_STOCK','WRITTEN_OFF_ESTIMATED','WAIVED')),
  CONSTRAINT ck_shortages_one_parent CHECK ((sale_line_id IS NOT NULL) <> (document_line_id IS NOT NULL)),
  CONSTRAINT ck_shortages_resolved CHECK (status <> 'RESOLVED' OR (resolution IS NOT NULL AND resolved_at IS NOT NULL)),
  CONSTRAINT ck_shortages_consumed CHECK (resolution IS DISTINCT FROM 'CONSUMED_FROM_STOCK'
    OR (estimated_unit_cost IS NULL AND estimated_cost_vnd IS NULL AND estimate_batch_id IS NULL)),
  CONSTRAINT ck_shortages_written_off CHECK (resolution IS DISTINCT FROM 'WRITTEN_OFF_ESTIMATED' OR estimated_cost_vnd IS NOT NULL),
  CONSTRAINT ck_shortages_waived CHECK (resolution IS DISTINCT FROM 'WAIVED' OR resolution_note IS NOT NULL)
)""",
"CREATE UNIQUE INDEX uq_shortages_saleline_ing ON stock_shortages (sale_line_id, ingredient_id) WHERE sale_line_id IS NOT NULL",
"CREATE UNIQUE INDEX uq_shortages_docline ON stock_shortages (document_line_id) WHERE document_line_id IS NOT NULL",
"CREATE INDEX ix_shortages_open ON stock_shortages (kitchen_id) WHERE status = 'OPEN'",
"CREATE INDEX ix_shortages_saleline ON stock_shortages (sale_line_id)",
"CREATE INDEX ix_shortages_docline ON stock_shortages (document_line_id)",
]
DOWN = ["DROP TABLE stock_shortages"]


def upgrade() -> None:
    for s in UP:
        op.execute(s)


def downgrade() -> None:
    for s in DOWN:
        op.execute(s)
