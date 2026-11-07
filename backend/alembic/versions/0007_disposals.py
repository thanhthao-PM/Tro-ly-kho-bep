"""0007 disposals (Rev 3 II.2, Rev 4 4.1/4.2)"""
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

UP = [
"""CREATE TABLE disposals (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  kitchen_id uuid NOT NULL REFERENCES kitchens (id),
  batch_id uuid NOT NULL,
  type text NOT NULL,
  quantity numeric(14,3) NOT NULL,
  occurred_on date NOT NULL,
  reason_code text,
  note text,
  counterparty_name text,
  revenue_vnd bigint,
  created_by uuid REFERENCES user_profiles (id),
  CONSTRAINT uq_disposals_kid UNIQUE (kitchen_id, id),
  CONSTRAINT fk_disposals_batch FOREIGN KEY (kitchen_id, batch_id) REFERENCES batches (kitchen_id, id),
  CONSTRAINT ck_disposals_type CHECK (type IN ('DONATION','SELLOFF','WASTE')),
  CONSTRAINT ck_disposals_qty CHECK (quantity > 0),
  CONSTRAINT ck_disposals_reason CHECK (reason_code IS NULL OR reason_code IN ('EXPIRED','SPOILED','OVERSTOCK','OTHER')),
  CONSTRAINT ck_disposals_waste_reason CHECK (type <> 'WASTE' OR reason_code IS NOT NULL),
  CONSTRAINT ck_disposals_other_note CHECK (reason_code IS DISTINCT FROM 'OTHER' OR note IS NOT NULL),
  CONSTRAINT ck_disposals_selloff_rev CHECK (type <> 'SELLOFF' OR revenue_vnd IS NOT NULL),
  CONSTRAINT ck_disposals_other_rev CHECK (type = 'SELLOFF' OR revenue_vnd IS NULL)
)""",
"CREATE INDEX ix_disposals_date ON disposals (kitchen_id, occurred_on)",
"CREATE INDEX ix_disposals_batch ON disposals (batch_id)",
]
DOWN = ["DROP TABLE disposals"]


def upgrade() -> None:
    for s in UP:
        op.execute(s)


def downgrade() -> None:
    for s in DOWN:
        op.execute(s)
