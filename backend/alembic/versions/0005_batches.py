"""0005 batches (Rev 3 II.2, Rev 4 4.1/4.2). Triggers come in 0009."""
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

UP = [
"""CREATE TABLE batches (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  kitchen_id uuid NOT NULL REFERENCES kitchens (id),
  ingredient_id uuid NOT NULL,
  received_on date NOT NULL,
  expiry_date date,
  initial_qty numeric(14,3) NOT NULL,
  remaining_qty numeric(14,3) NOT NULL DEFAULT 0,
  unit_cost numeric(18,6) NOT NULL,
  location text NOT NULL,
  source_document_line_id uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_batches_kid UNIQUE (kitchen_id, id),
  CONSTRAINT uq_batches_kid_ing UNIQUE (kitchen_id, ingredient_id, id),
  CONSTRAINT fk_batches_ingredient FOREIGN KEY (kitchen_id, ingredient_id) REFERENCES ingredients (kitchen_id, id),
  CONSTRAINT fk_batches_docline FOREIGN KEY (kitchen_id, source_document_line_id) REFERENCES document_lines (kitchen_id, id),
  CONSTRAINT ck_batches_initial CHECK (initial_qty > 0),
  CONSTRAINT ck_batches_remaining CHECK (remaining_qty >= 0),
  CONSTRAINT ck_batches_cost CHECK (unit_cost >= 0),
  CONSTRAINT ck_batches_location CHECK (location IN ('FRIDGE','FREEZER','PANTRY')),
  CONSTRAINT ck_batches_expiry CHECK (expiry_date IS NULL OR expiry_date >= received_on)
)""",
"""CREATE INDEX ix_batches_fefo ON batches (kitchen_id, ingredient_id, expiry_date NULLS LAST, received_on, id)
  WHERE remaining_qty > 0""",
"CREATE INDEX ix_batches_expiring ON batches (kitchen_id, expiry_date) WHERE remaining_qty > 0",
"CREATE INDEX ix_batches_received ON batches (kitchen_id, received_on)",
"CREATE INDEX ix_batches_history ON batches (kitchen_id, ingredient_id, received_on)",
]
DOWN = ["DROP TABLE batches"]


def upgrade() -> None:
    for s in UP:
        op.execute(s)


def downgrade() -> None:
    for s in DOWN:
        op.execute(s)
