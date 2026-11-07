"""0003 dishes, recipe_items (Rev 3 II.2, Rev 4 4.1/4.2)"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

UP = [
"""CREATE TABLE dishes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  kitchen_id uuid NOT NULL REFERENCES kitchens (id),
  name text NOT NULL,
  normalized_name text NOT NULL,
  price_vnd bigint NOT NULL,
  deleted_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_dishes_kid UNIQUE (kitchen_id, id),
  CONSTRAINT ck_dishes_price CHECK (price_vnd >= 0)
)""",
"CREATE UNIQUE INDEX uq_dishes_name_active ON dishes (kitchen_id, normalized_name) WHERE deleted_at IS NULL",
"""CREATE TABLE recipe_items (
  kitchen_id uuid NOT NULL REFERENCES kitchens (id),
  dish_id uuid NOT NULL,
  ingredient_id uuid NOT NULL,
  quantity_base numeric(14,3) NOT NULL,
  PRIMARY KEY (kitchen_id, dish_id, ingredient_id),
  CONSTRAINT fk_recipe_dish FOREIGN KEY (kitchen_id, dish_id) REFERENCES dishes (kitchen_id, id),
  CONSTRAINT fk_recipe_ingredient FOREIGN KEY (kitchen_id, ingredient_id) REFERENCES ingredients (kitchen_id, id),
  CONSTRAINT ck_recipe_qty CHECK (quantity_base > 0)
)""",
"CREATE INDEX ix_recipe_items_ingredient ON recipe_items (kitchen_id, ingredient_id)",
]
DOWN = ["DROP TABLE recipe_items", "DROP TABLE dishes"]


def upgrade() -> None:
    for s in UP:
        op.execute(s)


def downgrade() -> None:
    for s in DOWN:
        op.execute(s)
