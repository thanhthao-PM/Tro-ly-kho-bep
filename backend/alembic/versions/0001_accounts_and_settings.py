"""0001 user_profiles, kitchens, kitchen_settings (Rev 3 II.2, Rev 4 2.B/E, Rev 5 2.6)"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

UP = [
"""CREATE TABLE user_profiles (
  id uuid PRIMARY KEY,
  display_name text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
)""",
"""CREATE TABLE kitchens (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_user_id uuid NOT NULL,
  name text NOT NULL,
  timezone text NOT NULL DEFAULT 'Asia/Ho_Chi_Minh',
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_kitchens_owner UNIQUE (owner_user_id),
  CONSTRAINT fk_kitchens_owner FOREIGN KEY (owner_user_id) REFERENCES user_profiles (id) ON DELETE RESTRICT
)""",
# All defaults below are PLACEHOLDERS pending D7/D9/D25 (Rev 3 II.2, Rev 4 2.B).
"""CREATE TABLE kitchen_settings (
  kitchen_id uuid PRIMARY KEY REFERENCES kitchens (id) ON DELETE CASCADE,
  expiry_warning_days smallint NOT NULL DEFAULT 3,
  target_coverage_days smallint NOT NULL DEFAULT 3,
  consumption_window_days smallint NOT NULL DEFAULT 14,
  min_history_days smallint NOT NULL DEFAULT 7,
  unusual_quantity_ratio numeric(6,2) NOT NULL DEFAULT 2.0,
  backdate_limit_days smallint NOT NULL DEFAULT 2,
  expired_batches_consumable boolean NOT NULL DEFAULT false,
  expired_batch_actions text[] NOT NULL DEFAULT ARRAY['WASTE']::text[],
  CONSTRAINT ck_ks_warning CHECK (expiry_warning_days BETWEEN 0 AND 30),
  CONSTRAINT ck_ks_coverage CHECK (target_coverage_days BETWEEN 1 AND 60),
  CONSTRAINT ck_ks_window CHECK (consumption_window_days BETWEEN 7 AND 90),
  CONSTRAINT ck_ks_min_history CHECK (min_history_days >= 1 AND min_history_days <= consumption_window_days),
  CONSTRAINT ck_ks_actions CHECK (
    expired_batch_actions <@ ARRAY['WASTE','DONATION','SELLOFF','COOK']::text[]
    AND 'WASTE' = ANY (expired_batch_actions))
)""",
]
DOWN = ["DROP TABLE kitchen_settings", "DROP TABLE kitchens", "DROP TABLE user_profiles"]


def upgrade() -> None:
    for s in UP:
        op.execute(s)


def downgrade() -> None:
    for s in DOWN:
        op.execute(s)
