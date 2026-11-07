"""0009 stock_movements, ledger_internal functions, triggers, ledger_effective (Rev 6.3 s3.1-3.8, Rev 5 2.1/2.2/2.5).

Core mode: functions are owned by the migration owner (D30a DISABLED). No custom roles here.
Written without percent signs and without colon-name tokens so op.execute() never treats
anything as a bind parameter.
"""
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

TRUNCATE_GUARD = """DO $do$
DECLARE t text;
BEGIN
  FOR t IN SELECT tablename FROM pg_catalog.pg_tables
           WHERE schemaname = 'public' AND tablename <> 'alembic_version' LOOP
    EXECUTE 'DROP TRIGGER IF EXISTS ' || quote_ident('no_truncate_' || t) || ' ON public.' || quote_ident(t);
    EXECUTE 'CREATE TRIGGER ' || quote_ident('no_truncate_' || t)
         || ' BEFORE TRUNCATE ON public.' || quote_ident(t)
         || ' FOR EACH STATEMENT EXECUTE FUNCTION ledger_internal.reject_truncate()';
  END LOOP;
END
$do$"""

UP = [
"""CREATE TABLE stock_movements (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  kitchen_id uuid NOT NULL REFERENCES kitchens (id),
  batch_id uuid NOT NULL,
  ingredient_id uuid NOT NULL,
  type text NOT NULL,
  qty_delta numeric(14,3) NOT NULL,
  unit_cost_snapshot numeric(18,6) NOT NULL,
  value_vnd bigint NOT NULL,
  occurred_on date NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  actor_id uuid REFERENCES user_profiles (id),
  reason_code text,
  note text,
  sale_line_id uuid,
  disposal_id uuid,
  document_line_id uuid,
  shortage_id uuid,
  reverses_movement_id uuid,
  CONSTRAINT uq_sm_kid UNIQUE (kitchen_id, id),
  CONSTRAINT uq_sm_reverses UNIQUE (reverses_movement_id),
  CONSTRAINT fk_sm_batch FOREIGN KEY (kitchen_id, ingredient_id, batch_id) REFERENCES batches (kitchen_id, ingredient_id, id),
  CONSTRAINT fk_sm_saleline FOREIGN KEY (kitchen_id, sale_line_id) REFERENCES sale_lines (kitchen_id, id),
  CONSTRAINT fk_sm_disposal FOREIGN KEY (kitchen_id, disposal_id) REFERENCES disposals (kitchen_id, id),
  CONSTRAINT fk_sm_docline FOREIGN KEY (kitchen_id, document_line_id) REFERENCES document_lines (kitchen_id, id),
  CONSTRAINT fk_sm_shortage FOREIGN KEY (kitchen_id, shortage_id) REFERENCES stock_shortages (kitchen_id, id),
  CONSTRAINT ck_sm_type CHECK (type IN ('RECEIPT','SALE_CONSUMPTION','USAGE_CONSUMPTION','DONATION','SELLOFF','WASTE','ADJUSTMENT_IN','ADJUSTMENT_OUT','REVERSAL')),
  CONSTRAINT ck_sm_nonzero CHECK (qty_delta <> 0),
  CONSTRAINT ck_sm_cost CHECK (unit_cost_snapshot >= 0),
  CONSTRAINT ck_sm_sign CHECK (
    CASE
      WHEN type IN ('RECEIPT','ADJUSTMENT_IN') THEN qty_delta > 0
      WHEN type IN ('SALE_CONSUMPTION','USAGE_CONSUMPTION','DONATION','SELLOFF','WASTE','ADJUSTMENT_OUT') THEN qty_delta < 0
      ELSE true END),
  CONSTRAINT ck_sm_refs CHECK (
    CASE
      WHEN type = 'SALE_CONSUMPTION' THEN sale_line_id IS NOT NULL
      WHEN type = 'USAGE_CONSUMPTION' THEN document_line_id IS NOT NULL
      WHEN type IN ('DONATION','SELLOFF','WASTE') THEN disposal_id IS NOT NULL
      WHEN type IN ('ADJUSTMENT_IN','ADJUSTMENT_OUT') THEN reason_code IS NOT NULL
      ELSE true END),
  CONSTRAINT ck_sm_reversal_ref CHECK ((type = 'REVERSAL') = (reverses_movement_id IS NOT NULL)),
  CONSTRAINT ck_sm_value_sign CHECK (value_vnd = 0 OR sign(value_vnd::numeric) = sign(qty_delta)),
  CONSTRAINT ck_sm_value_tolerance CHECK (abs(value_vnd - qty_delta * unit_cost_snapshot) < 1)
)""",
"""ALTER TABLE stock_movements ADD CONSTRAINT fk_sm_reverses
  FOREIGN KEY (kitchen_id, reverses_movement_id) REFERENCES stock_movements (kitchen_id, id)""",
"CREATE UNIQUE INDEX uq_sm_one_receipt ON stock_movements (batch_id) WHERE type = 'RECEIPT'",
"CREATE INDEX ix_sm_date ON stock_movements (kitchen_id, occurred_on, created_at)",
"CREATE INDEX ix_sm_batch ON stock_movements (batch_id)",
"CREATE INDEX ix_sm_ingredient ON stock_movements (kitchen_id, ingredient_id, occurred_on)",
"CREATE INDEX ix_sm_saleline ON stock_movements (sale_line_id)",
"CREATE INDEX ix_sm_disposal ON stock_movements (disposal_id)",
"CREATE INDEX ix_sm_shortage ON stock_movements (shortage_id)",

"CREATE SCHEMA IF NOT EXISTS ledger_internal",

# --- the one cache function (SECURITY DEFINER, fixed search_path, no params, no dynamic SQL) ---
"""CREATE FUNCTION ledger_internal.apply_movement() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $fn$
BEGIN
  UPDATE public.batches
     SET remaining_qty = remaining_qty + NEW.qty_delta
   WHERE id = NEW.batch_id AND kitchen_id = NEW.kitchen_id AND ingredient_id = NEW.ingredient_id;
  IF NOT FOUND THEN
    RAISE EXCEPTION USING MESSAGE = 'movement references no matching batch', ERRCODE = 'foreign_key_violation';
  END IF;
  RETURN NULL;
END
$fn$""",
"""CREATE TRIGGER trg_sm_apply AFTER INSERT ON public.stock_movements
  FOR EACH ROW EXECUTE FUNCTION ledger_internal.apply_movement()""",

# --- depth guard on batches (not a security boundary, 6.3 s3.1) ---
"""CREATE FUNCTION ledger_internal.guard_batches_update() RETURNS trigger
LANGUAGE plpgsql AS $fn$
BEGIN
  IF NEW.id IS DISTINCT FROM OLD.id OR NEW.kitchen_id IS DISTINCT FROM OLD.kitchen_id
     OR NEW.ingredient_id IS DISTINCT FROM OLD.ingredient_id
     OR NEW.initial_qty IS DISTINCT FROM OLD.initial_qty OR NEW.unit_cost IS DISTINCT FROM OLD.unit_cost THEN
    RAISE EXCEPTION USING MESSAGE = 'batch id, kitchen, ingredient, initial quantity and unit cost are immutable',
      ERRCODE = 'integrity_constraint_violation';
  END IF;
  IF NEW.remaining_qty IS DISTINCT FROM OLD.remaining_qty AND pg_trigger_depth() < 2 THEN
    RAISE EXCEPTION USING MESSAGE = 'remaining_qty is maintained by the ledger only',
      ERRCODE = 'integrity_constraint_violation';
  END IF;
  RETURN NEW;
END
$fn$""",
"""CREATE TRIGGER trg_batches_guard BEFORE UPDATE ON public.batches
  FOR EACH ROW EXECUTE FUNCTION ledger_internal.guard_batches_update()""",
"""CREATE FUNCTION ledger_internal.guard_batches_insert() RETURNS trigger
LANGUAGE plpgsql AS $fn$
BEGIN
  IF NEW.remaining_qty <> 0 THEN
    RAISE EXCEPTION USING MESSAGE = 'a batch must be inserted with remaining_qty = 0; the RECEIPT movement posts the quantity',
      ERRCODE = 'integrity_constraint_violation';
  END IF;
  RETURN NEW;
END
$fn$""",
"""CREATE TRIGGER trg_batches_insert_guard BEFORE INSERT ON public.batches
  FOR EACH ROW EXECUTE FUNCTION ledger_internal.guard_batches_insert()""",

# --- deferred consistency: remaining_qty = sum(qty_delta), exactly one RECEIPT = initial_qty ---
"""CREATE FUNCTION ledger_internal.check_batch_consistency() RETURNS trigger
LANGUAGE plpgsql AS $fn$
DECLARE
  v_batch uuid; v_rem numeric; v_init numeric; v_sum numeric; v_n integer; v_rq numeric;
BEGIN
  IF TG_TABLE_NAME = 'batches' THEN v_batch := NEW.id; ELSE v_batch := NEW.batch_id; END IF;
  SELECT remaining_qty, initial_qty INTO v_rem, v_init FROM public.batches WHERE id = v_batch;
  IF NOT FOUND THEN RETURN NULL; END IF;
  SELECT COALESCE(SUM(qty_delta), 0),
         COUNT(*) FILTER (WHERE type = 'RECEIPT'),
         COALESCE(SUM(qty_delta) FILTER (WHERE type = 'RECEIPT'), 0)
    INTO v_sum, v_n, v_rq
    FROM public.stock_movements WHERE batch_id = v_batch;
  IF v_rem <> v_sum THEN
    RAISE EXCEPTION USING MESSAGE = 'batch ' || v_batch::text || ': remaining_qty does not equal the sum of its movements',
      ERRCODE = 'integrity_constraint_violation';
  END IF;
  IF v_n <> 1 THEN
    RAISE EXCEPTION USING MESSAGE = 'batch ' || v_batch::text || ': exactly one RECEIPT movement is required',
      ERRCODE = 'integrity_constraint_violation';
  END IF;
  IF v_rq <> v_init THEN
    RAISE EXCEPTION USING MESSAGE = 'batch ' || v_batch::text || ': RECEIPT quantity must equal initial_qty',
      ERRCODE = 'integrity_constraint_violation';
  END IF;
  RETURN NULL;
END
$fn$""",
"""CREATE CONSTRAINT TRIGGER ctrg_batches_consistency AFTER INSERT OR UPDATE ON public.batches
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION ledger_internal.check_batch_consistency()""",
"""CREATE CONSTRAINT TRIGGER ctrg_sm_consistency AFTER INSERT ON public.stock_movements
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION ledger_internal.check_batch_consistency()""",

# --- movement validation: cost snapshot, reversal rules (Rev 5 2.1) ---
"""CREATE FUNCTION ledger_internal.validate_movement() RETURNS trigger
LANGUAGE plpgsql AS $fn$
DECLARE
  v_cost numeric;
  o_batch uuid; o_type text; o_qty numeric; o_cost numeric; o_val bigint;
  o_sale uuid; o_disp uuid; o_doc uuid; o_short uuid;
BEGIN
  SELECT unit_cost INTO v_cost FROM public.batches
   WHERE id = NEW.batch_id AND kitchen_id = NEW.kitchen_id AND ingredient_id = NEW.ingredient_id;
  IF NOT FOUND THEN
    RAISE EXCEPTION USING MESSAGE = 'movement references no matching batch', ERRCODE = 'foreign_key_violation';
  END IF;
  IF NEW.unit_cost_snapshot <> v_cost THEN
    RAISE EXCEPTION USING MESSAGE = 'unit_cost_snapshot must equal the batch unit cost', ERRCODE = 'integrity_constraint_violation';
  END IF;
  IF NEW.type = 'REVERSAL' THEN
    SELECT batch_id, type, qty_delta, unit_cost_snapshot, value_vnd, sale_line_id, disposal_id, document_line_id, shortage_id
      INTO o_batch, o_type, o_qty, o_cost, o_val, o_sale, o_disp, o_doc, o_short
      FROM public.stock_movements WHERE id = NEW.reverses_movement_id AND kitchen_id = NEW.kitchen_id;
    IF NOT FOUND THEN
      RAISE EXCEPTION USING MESSAGE = 'reversal original not found in this kitchen', ERRCODE = 'integrity_constraint_violation';
    END IF;
    IF o_batch <> NEW.batch_id THEN
      RAISE EXCEPTION USING MESSAGE = 'reversal must target the same batch as the original', ERRCODE = 'integrity_constraint_violation';
    END IF;
    IF o_type = 'REVERSAL' THEN
      RAISE EXCEPTION USING MESSAGE = 'a reversal cannot be reversed', ERRCODE = 'integrity_constraint_violation';
    END IF;
    IF NEW.qty_delta <> -o_qty OR NEW.unit_cost_snapshot <> o_cost OR NEW.value_vnd <> -o_val THEN
      RAISE EXCEPTION USING MESSAGE = 'reversal must negate qty_delta and value_vnd and keep the original snapshot cost',
        ERRCODE = 'integrity_constraint_violation';
    END IF;
    NEW.sale_line_id := o_sale; NEW.disposal_id := o_disp;
    NEW.document_line_id := o_doc; NEW.shortage_id := o_short;
  END IF;
  RETURN NEW;
END
$fn$""",
"""CREATE TRIGGER trg_sm_validate BEFORE INSERT ON public.stock_movements
  FOR EACH ROW EXECUTE FUNCTION ledger_internal.validate_movement()""",

# --- append-only and TRUNCATE guards ---
"""CREATE FUNCTION ledger_internal.reject_modification() RETURNS trigger
LANGUAGE plpgsql AS $fn$
BEGIN
  RAISE EXCEPTION USING MESSAGE = TG_TABLE_NAME || ' is append-only', ERRCODE = 'integrity_constraint_violation';
  RETURN NULL;
END
$fn$""",
"""CREATE TRIGGER trg_sm_immutable BEFORE UPDATE OR DELETE ON public.stock_movements
  FOR EACH ROW EXECUTE FUNCTION ledger_internal.reject_modification()""",
"""CREATE FUNCTION ledger_internal.reject_truncate() RETURNS trigger
LANGUAGE plpgsql AS $fn$
BEGIN
  RAISE EXCEPTION USING MESSAGE = 'TRUNCATE is not allowed on ' || TG_TABLE_NAME, ERRCODE = 'integrity_constraint_violation';
  RETURN NULL;
END
$fn$""",
TRUNCATE_GUARD,

# --- base-unit backstop (6.3 s3.8): same six conditions as the service predicate ---
"""CREATE FUNCTION ledger_internal.guard_base_unit() RETURNS trigger
LANGUAGE plpgsql AS $fn$
BEGIN
  IF EXISTS (SELECT 1 FROM public.batches WHERE kitchen_id = OLD.kitchen_id AND ingredient_id = OLD.id)
     OR EXISTS (SELECT 1 FROM public.stock_movements WHERE kitchen_id = OLD.kitchen_id AND ingredient_id = OLD.id)
     OR EXISTS (SELECT 1 FROM public.recipe_items WHERE kitchen_id = OLD.kitchen_id AND ingredient_id = OLD.id)
     OR EXISTS (SELECT 1 FROM public.document_lines dl
                  JOIN public.documents d ON d.kitchen_id = dl.kitchen_id AND d.id = dl.document_id
                 WHERE dl.kitchen_id = OLD.kitchen_id AND dl.ingredient_id = OLD.id AND d.status <> 'CANCELLED')
     OR EXISTS (SELECT 1 FROM public.stock_shortages WHERE kitchen_id = OLD.kitchen_id AND ingredient_id = OLD.id)
     OR EXISTS (SELECT 1 FROM public.ingredient_unit_conversions WHERE kitchen_id = OLD.kitchen_id AND ingredient_id = OLD.id)
  THEN
    RAISE EXCEPTION USING MESSAGE = 'BASE_UNIT_LOCKED', ERRCODE = 'integrity_constraint_violation';
  END IF;
  RETURN NEW;
END
$fn$""",
"""CREATE TRIGGER trg_ingredients_base_unit BEFORE UPDATE OF base_unit_code ON public.ingredients
  FOR EACH ROW WHEN (OLD.base_unit_code IS DISTINCT FROM NEW.base_unit_code)
  EXECUTE FUNCTION ledger_internal.guard_base_unit()""",

# --- sale_lines cache verified at commit (6.3 s3.4) ---
"""CREATE FUNCTION ledger_internal.check_sale_line_cache() RETURNS trigger
LANGUAGE plpgsql AS $fn$
DECLARE
  v_line uuid; c_cogs bigint; c_status text; v_cogs numeric; v_status text; n_short integer; n_open integer;
BEGIN
  IF TG_TABLE_NAME = 'sale_lines' THEN v_line := NEW.id; ELSE v_line := NEW.sale_line_id; END IF;
  IF v_line IS NULL THEN RETURN NULL; END IF;
  SELECT cogs_vnd, consumption_status INTO c_cogs, c_status FROM public.sale_lines WHERE id = v_line;
  IF NOT FOUND THEN RETURN NULL; END IF;
  SELECT COALESCE(-SUM(m.value_vnd), 0) INTO v_cogs
    FROM public.stock_movements m
    LEFT JOIN public.stock_movements o ON o.id = m.reverses_movement_id
   WHERE m.sale_line_id = v_line AND COALESCE(o.type, m.type) = 'SALE_CONSUMPTION';
  SELECT COUNT(*), COUNT(*) FILTER (WHERE status = 'OPEN') INTO n_short, n_open
    FROM public.stock_shortages WHERE sale_line_id = v_line;
  v_status := CASE WHEN n_short = 0 THEN 'FULL' WHEN n_open > 0 THEN 'PARTIAL' ELSE 'RESOLVED' END;
  IF c_cogs <> v_cogs OR c_status <> v_status THEN
    RAISE EXCEPTION USING MESSAGE = 'sale line ' || v_line::text || ': cogs_vnd or consumption_status does not match the ledger',
      ERRCODE = 'integrity_constraint_violation';
  END IF;
  RETURN NULL;
END
$fn$""",
"""CREATE CONSTRAINT TRIGGER ctrg_salelines_cache AFTER INSERT OR UPDATE ON public.sale_lines
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION ledger_internal.check_sale_line_cache()""",
"""CREATE CONSTRAINT TRIGGER ctrg_sm_salelines_cache AFTER INSERT ON public.stock_movements
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION ledger_internal.check_sale_line_cache()""",
"""CREATE CONSTRAINT TRIGGER ctrg_shortages_salelines_cache AFTER INSERT OR UPDATE ON public.stock_shortages
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION ledger_internal.check_sale_line_cache()""",

# --- ledger_effective (6.3 s3.3): read-only, security_invoker (needs PostgreSQL 15+, item U1) ---
"""CREATE VIEW public.ledger_effective WITH (security_invoker = true) AS
SELECT m.id AS movement_id, m.kitchen_id, m.batch_id, m.ingredient_id, m.type,
       COALESCE(o.type, m.type) AS category,
       CASE
         WHEN m.sale_line_id IS NOT NULL THEN s.business_date
         WHEN COALESCE(o.type, m.type) = 'USAGE_CONSUMPTION' AND m.document_line_id IS NOT NULL THEN doc.business_date
         WHEN m.disposal_id IS NOT NULL THEN dsp.occurred_on
         ELSE COALESCE(o.occurred_on, m.occurred_on)
       END AS attribution_date,
       m.occurred_on, m.sale_line_id, m.disposal_id, m.document_line_id, m.shortage_id,
       m.reverses_movement_id, m.qty_delta, m.unit_cost_snapshot, m.value_vnd
  FROM public.stock_movements m
  LEFT JOIN public.stock_movements o ON o.kitchen_id = m.kitchen_id AND o.id = m.reverses_movement_id
  LEFT JOIN public.sale_lines sl ON sl.kitchen_id = m.kitchen_id AND sl.id = m.sale_line_id
  LEFT JOIN public.sales s ON s.kitchen_id = sl.kitchen_id AND s.id = sl.sale_id
  LEFT JOIN public.document_lines dl ON dl.kitchen_id = m.kitchen_id AND dl.id = m.document_line_id
  LEFT JOIN public.documents doc ON doc.kitchen_id = dl.kitchen_id AND doc.id = dl.document_id
  LEFT JOIN public.disposals dsp ON dsp.kitchen_id = m.kitchen_id AND dsp.id = m.disposal_id""",
]
DOWN = [
"DROP VIEW public.ledger_effective",
"DROP TABLE public.stock_movements",
"DROP TRIGGER trg_ingredients_base_unit ON public.ingredients",
"DROP TRIGGER trg_batches_insert_guard ON public.batches",
"DROP TRIGGER trg_batches_guard ON public.batches",
"DROP TRIGGER ctrg_batches_consistency ON public.batches",
"DROP TRIGGER ctrg_salelines_cache ON public.sale_lines",
"DROP TRIGGER ctrg_shortages_salelines_cache ON public.stock_shortages",
"""DO $do$
DECLARE t text;
BEGIN
  FOR t IN SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public' AND tablename <> 'alembic_version' LOOP
    EXECUTE 'DROP TRIGGER IF EXISTS ' || quote_ident('no_truncate_' || t) || ' ON public.' || quote_ident(t);
  END LOOP;
END
$do$""",
"DROP SCHEMA ledger_internal CASCADE",
]


def upgrade() -> None:
    for s in UP:
        op.execute(s)


def downgrade() -> None:
    for s in DOWN:
        op.execute(s)
