"""0002 units (+seed), ingredients, aliases, conversions (Rev 3 II.2, Rev 4 2.A/2.E/4.1)"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

UP = [
# Rev 4 2.A check, written so NULL factors cannot slip through for MASS/VOLUME.
"""CREATE TABLE units (
  code text PRIMARY KEY,
  label_vi text NOT NULL,
  dimension text NOT NULL,
  factor_to_dimension_base numeric(18,6),
  CONSTRAINT ck_units_dimension CHECK (dimension IN ('MASS','VOLUME','COUNT')),
  CONSTRAINT ck_units_factor CHECK (
    (dimension IN ('MASS','VOLUME') AND factor_to_dimension_base IS NOT NULL AND factor_to_dimension_base > 0)
    OR (dimension = 'COUNT' AND factor_to_dimension_base IS NULL))
)""",
"""INSERT INTO units (code, label_vi, dimension, factor_to_dimension_base) VALUES
  ('g','g','MASS',1), ('kg','kg','MASS',1000),
  ('ml','ml','VOLUME',1), ('l','lít','VOLUME',1000),
  ('quả','quả','COUNT',NULL), ('hộp','hộp','COUNT',NULL), ('bó','bó','COUNT',NULL),
  ('củ','củ','COUNT',NULL), ('bìa','bìa','COUNT',NULL), ('gói','gói','COUNT',NULL),
  ('chai','chai','COUNT',NULL)""",
"""CREATE TABLE ingredients (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  kitchen_id uuid NOT NULL REFERENCES kitchens (id),
  name text NOT NULL,
  normalized_name text NOT NULL,
  search_name text NOT NULL,
  base_unit_code text NOT NULL REFERENCES units (code),
  default_location text NOT NULL,
  tracks_expiry boolean NOT NULL DEFAULT true,
  min_stock_qty numeric(14,3) NOT NULL DEFAULT 0,
  expiry_warning_days smallint,
  order_step numeric(14,3),
  deleted_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_ingredients_kid UNIQUE (kitchen_id, id),
  CONSTRAINT uq_ingredients_kid_unit UNIQUE (kitchen_id, id, base_unit_code),
  CONSTRAINT ck_ingredients_location CHECK (default_location IN ('FRIDGE','FREEZER','PANTRY')),
  CONSTRAINT ck_ingredients_min_stock CHECK (min_stock_qty >= 0),
  CONSTRAINT ck_ingredients_warning CHECK (expiry_warning_days IS NULL OR expiry_warning_days BETWEEN 0 AND 30),
  CONSTRAINT ck_ingredients_step CHECK (order_step IS NULL OR order_step > 0)
)""",
"CREATE UNIQUE INDEX uq_ingredients_name_active ON ingredients (kitchen_id, normalized_name) WHERE deleted_at IS NULL",
"""CREATE TABLE ingredient_aliases (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  kitchen_id uuid NOT NULL REFERENCES kitchens (id),
  ingredient_id uuid NOT NULL,
  alias text NOT NULL,
  normalized_alias text NOT NULL,
  CONSTRAINT uq_aliases_kid UNIQUE (kitchen_id, id),
  CONSTRAINT uq_aliases_norm UNIQUE (kitchen_id, normalized_alias),
  CONSTRAINT fk_aliases_ingredient FOREIGN KEY (kitchen_id, ingredient_id) REFERENCES ingredients (kitchen_id, id)
)""",
"""CREATE TABLE ingredient_unit_conversions (
  kitchen_id uuid NOT NULL REFERENCES kitchens (id),
  ingredient_id uuid NOT NULL,
  unit_code text NOT NULL REFERENCES units (code),
  base_unit_code text NOT NULL,
  factor_to_base numeric(18,6) NOT NULL,
  PRIMARY KEY (kitchen_id, ingredient_id, unit_code),
  CONSTRAINT fk_conv_ingredient FOREIGN KEY (kitchen_id, ingredient_id, base_unit_code)
    REFERENCES ingredients (kitchen_id, id, base_unit_code),
  CONSTRAINT ck_conv_factor CHECK (factor_to_base > 0),
  CONSTRAINT ck_conv_unit_differs CHECK (unit_code <> base_unit_code)
)""",
]
DOWN = ["DROP TABLE ingredient_unit_conversions", "DROP TABLE ingredient_aliases",
        "DROP TABLE ingredients", "DROP TABLE units"]


def upgrade() -> None:
    for s in UP:
        op.execute(s)


def downgrade() -> None:
    for s in DOWN:
        op.execute(s)
