"""0012 Review 1 fixes (approved): disposal and shortage consistency with the ledger, stronger batch guard,
shortage status/resolution rule. Adds no tables, so no new grants or RLS are needed.

R1: disposal movement must match its disposal (batch, type, quantity); exactly one original movement per
    disposal, checked in both directions (movement insert, and disposal insert/update at commit).
R2: movement with shortage_id must match the shortage (ingredient and sale/document line).
2.1: batch id, kitchen, ingredient, initial_qty, unit_cost, source_document_line_id, created_at are immutable.
2.2: a shortage is RESOLVED exactly when it has a resolution.
Future migrations that create tables MUST enable RLS and revoke from PUBLIC/anon/authenticated
(enforced by tests/test_migrations_static.py). Never executed against PostgreSQL by the author.
"""
import importlib.util
import pathlib

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None

VALIDATE = """CREATE OR REPLACE FUNCTION ledger_internal.validate_movement() RETURNS trigger
LANGUAGE plpgsql AS $fn$
DECLARE
  v_cost numeric;
  o_batch uuid; o_type text; o_qty numeric; o_cost numeric; o_val bigint;
  o_sale uuid; o_disp uuid; o_doc uuid; o_short uuid;
  d_batch uuid; d_type text; d_qty numeric;
  s_ing uuid; s_sale uuid; s_doc uuid;
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
  ELSE
    -- R1: a disposal movement must agree with its disposal row (batch, type, quantity)
    IF NEW.type IN ('DONATION','SELLOFF','WASTE') THEN
      SELECT batch_id, type, quantity INTO d_batch, d_type, d_qty
        FROM public.disposals WHERE id = NEW.disposal_id AND kitchen_id = NEW.kitchen_id;
      IF NOT FOUND THEN
        RAISE EXCEPTION USING MESSAGE = 'disposal movement references no disposal in this kitchen', ERRCODE = 'foreign_key_violation';
      END IF;
      IF d_batch <> NEW.batch_id OR d_type <> NEW.type OR -NEW.qty_delta <> d_qty THEN
        RAISE EXCEPTION USING MESSAGE = 'disposal movement must match its disposal: same batch, same type, quantity equal to -qty_delta',
          ERRCODE = 'integrity_constraint_violation';
      END IF;
    END IF;
    -- R2: a movement that resolves a shortage must agree with that shortage
    IF NEW.shortage_id IS NOT NULL THEN
      SELECT ingredient_id, sale_line_id, document_line_id INTO s_ing, s_sale, s_doc
        FROM public.stock_shortages WHERE id = NEW.shortage_id AND kitchen_id = NEW.kitchen_id;
      IF FOUND AND (s_ing <> NEW.ingredient_id OR s_sale IS DISTINCT FROM NEW.sale_line_id
                    OR s_doc IS DISTINCT FROM NEW.document_line_id) THEN
        RAISE EXCEPTION USING MESSAGE = 'shortage movement must match its shortage: same ingredient and same sale or document line',
          ERRCODE = 'integrity_constraint_violation';
      END IF;
    END IF;
  END IF;
  RETURN NEW;
END
$fn$"""

GUARD = """CREATE OR REPLACE FUNCTION ledger_internal.guard_batches_update() RETURNS trigger
LANGUAGE plpgsql AS $fn$
BEGIN
  IF NEW.id IS DISTINCT FROM OLD.id OR NEW.kitchen_id IS DISTINCT FROM OLD.kitchen_id
     OR NEW.ingredient_id IS DISTINCT FROM OLD.ingredient_id
     OR NEW.initial_qty IS DISTINCT FROM OLD.initial_qty OR NEW.unit_cost IS DISTINCT FROM OLD.unit_cost
     OR NEW.source_document_line_id IS DISTINCT FROM OLD.source_document_line_id
     OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
    RAISE EXCEPTION USING MESSAGE = 'only location, expiry_date and received_on of a batch may change',
      ERRCODE = 'integrity_constraint_violation';
  END IF;
  IF NEW.remaining_qty IS DISTINCT FROM OLD.remaining_qty AND pg_trigger_depth() < 2 THEN
    RAISE EXCEPTION USING MESSAGE = 'remaining_qty is maintained by the ledger only',
      ERRCODE = 'integrity_constraint_violation';
  END IF;
  RETURN NEW;
END
$fn$"""

LINK = """CREATE FUNCTION ledger_internal.check_disposal_link() RETURNS trigger
LANGUAGE plpgsql AS $fn$
DECLARE
  v_id uuid; d_batch uuid; d_type text; d_qty numeric; v_n integer; m_batch uuid; m_type text; m_qty numeric;
BEGIN
  IF TG_TABLE_NAME = 'disposals' THEN v_id := NEW.id; ELSE v_id := NEW.disposal_id; END IF;
  IF v_id IS NULL THEN RETURN NULL; END IF;
  SELECT batch_id, type, quantity INTO d_batch, d_type, d_qty FROM public.disposals WHERE id = v_id;
  IF NOT FOUND THEN RETURN NULL; END IF;
  SELECT COUNT(*) INTO v_n FROM public.stock_movements WHERE disposal_id = v_id AND type <> 'REVERSAL';
  IF v_n <> 1 THEN
    RAISE EXCEPTION USING MESSAGE = 'disposal ' || v_id::text || ' must have exactly one original movement',
      ERRCODE = 'integrity_constraint_violation';
  END IF;
  SELECT batch_id, type, qty_delta INTO m_batch, m_type, m_qty
    FROM public.stock_movements WHERE disposal_id = v_id AND type <> 'REVERSAL';
  IF m_batch <> d_batch OR m_type <> d_type OR -m_qty <> d_qty THEN
    RAISE EXCEPTION USING MESSAGE = 'disposal ' || v_id::text || ' and its movement disagree on batch, type or quantity',
      ERRCODE = 'integrity_constraint_violation';
  END IF;
  RETURN NULL;
END
$fn$"""

UP = [
    VALIDATE,
    GUARD,
    "CREATE UNIQUE INDEX uq_sm_one_disposal_movement ON stock_movements (disposal_id) WHERE disposal_id IS NOT NULL AND type <> 'REVERSAL'",
    LINK,
    """CREATE CONSTRAINT TRIGGER ctrg_disposals_link AFTER INSERT OR UPDATE ON public.disposals
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION ledger_internal.check_disposal_link()""",
    """CREATE CONSTRAINT TRIGGER ctrg_sm_disposal_link AFTER INSERT ON public.stock_movements
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION ledger_internal.check_disposal_link()""",
    "ALTER TABLE stock_shortages ADD CONSTRAINT ck_shortages_status_resolution CHECK ((status = 'RESOLVED') = (resolution IS NOT NULL))",
]
DOWN = [
    "ALTER TABLE stock_shortages DROP CONSTRAINT ck_shortages_status_resolution",
    "DROP TRIGGER ctrg_sm_disposal_link ON public.stock_movements",
    "DROP TRIGGER ctrg_disposals_link ON public.disposals",
    "DROP FUNCTION ledger_internal.check_disposal_link()",
    "DROP INDEX uq_sm_one_disposal_movement",
]


def _original(fn_name: str) -> str:
    p = pathlib.Path(__file__).resolve().parent / "0009_ledger.py"
    spec = importlib.util.spec_from_file_location("m0009", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    sql = [s for s in m.UP if ("FUNCTION ledger_internal." + fn_name) in s][0]
    return sql.replace("CREATE FUNCTION", "CREATE OR REPLACE FUNCTION", 1)


def upgrade() -> None:
    for s in UP:
        op.execute(s)


def downgrade() -> None:
    for s in DOWN:
        op.execute(s)
    op.execute(_original("validate_movement"))
    op.execute(_original("guard_batches_update"))
