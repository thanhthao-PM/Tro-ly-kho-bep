"""0008: Stock Movements Ledger, Triggers, and Effective View

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-07 10:35:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Tạo schema ledger_internal nếu chưa có
    op.execute("CREATE SCHEMA IF NOT EXISTS ledger_internal;")

    # 2. Tạo bảng stock_movements
    op.create_table(
        "stock_movements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("kitchen_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ingredient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("qty_delta", sa.Numeric(14, 3), nullable=False),
        sa.Column("unit_cost_snapshot", sa.Numeric(18, 6), nullable=False),
        sa.Column("value_vnd", sa.BigInteger(), nullable=False),
        sa.Column("occurred_on", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reason_code", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("sale_line_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("disposal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("document_line_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("shortage_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reverses_movement_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stock_movements.id"), unique=True, nullable=True),
        sa.ForeignKeyConstraint(
            ["kitchen_id", "ingredient_id", "batch_id"],
            ["batches.kitchen_id", "batches.ingredient_id", "batches.id"],
            ondelete="RESTRICT",
            name="fk_stock_movements_batch"
        ),
        sa.CheckConstraint(
            "type IN ('RECEIPT', 'SALE_CONSUMPTION', 'USAGE_CONSUMPTION', 'DONATION', 'SELLOFF', 'WASTE', 'ADJUSTMENT_IN', 'ADJUSTMENT_OUT', 'REVERSAL')",
            name="chk_stock_movements_type"
        ),
        sa.CheckConstraint("qty_delta <> 0", name="chk_stock_movements_qty_delta_nonzero"),
        sa.CheckConstraint("value_vnd = 0 OR sign(value_vnd) = sign(qty_delta)", name="chk_stock_movements_sign_agreement"),
        sa.CheckConstraint("abs(value_vnd - (qty_delta * unit_cost_snapshot)) < 1", name="chk_stock_movements_value_tolerance"),
        sa.CheckConstraint(
            "(type IN ('RECEIPT', 'ADJUSTMENT_IN') AND qty_delta > 0) OR "
            "(type IN ('SALE_CONSUMPTION', 'USAGE_CONSUMPTION', 'DONATION', 'SELLOFF', 'WASTE', 'ADJUSTMENT_OUT') AND qty_delta < 0) OR "
            "(type = 'REVERSAL')",
            name="chk_stock_movements_type_direction"
        ),
    )
    op.create_index("idx_stock_movements_occurred", "stock_movements", ["kitchen_id", "occurred_on", "created_at"])
    op.create_index("idx_stock_movements_batch", "stock_movements", ["batch_id"])
    op.create_index("idx_stock_movements_ingredient", "stock_movements", ["kitchen_id", "ingredient_id", "occurred_on"])
    op.create_index("idx_stock_movements_sale_line", "stock_movements", ["sale_line_id"])
    op.create_index("idx_stock_movements_disposal", "stock_movements", ["disposal_id"])
    op.create_index("idx_stock_movements_shortage", "stock_movements", ["shortage_id"])

    # 3. Hàm trigger cập nhật remaining_qty trên batches
    op.execute("""
    CREATE OR REPLACE FUNCTION ledger_internal.trg_apply_stock_movement()
    RETURNS TRIGGER AS $$
    DECLARE
        v_updated INT;
    BEGIN
        UPDATE batches
        SET remaining_qty = remaining_qty + NEW.qty_delta
        WHERE id = NEW.batch_id
          AND kitchen_id = NEW.kitchen_id
          AND ingredient_id = NEW.ingredient_id;

        GET DIAGNOSTICS v_updated = ROW_COUNT;
        IF v_updated = 0 THEN
            RAISE EXCEPTION 'Target batch not found or mismatched kitchen/ingredient for movement %', NEW.id;
        END IF;

        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("""
    CREATE TRIGGER trg_stock_movements_after_insert
    AFTER INSERT ON stock_movements
    FOR EACH ROW
    EXECUTE FUNCTION ledger_internal.trg_apply_stock_movement();
    """)

    # 4. Trigger bảo vệ batches.remaining_qty chống sửa trực tiếp (pg_trigger_depth guard)
    op.execute("""
    CREATE OR REPLACE FUNCTION ledger_internal.trg_guard_batch_remaining_qty()
    RETURNS TRIGGER AS $$
    BEGIN
        IF NEW.remaining_qty <> OLD.remaining_qty AND pg_trigger_depth() < 2 THEN
            RAISE EXCEPTION 'Direct update of batches.remaining_qty is prohibited. Mutate via stock_movements only.';
        END IF;
        IF NEW.id <> OLD.id OR NEW.kitchen_id <> OLD.kitchen_id OR NEW.ingredient_id <> OLD.ingredient_id OR NEW.initial_qty <> OLD.initial_qty OR NEW.unit_cost <> OLD.unit_cost THEN
            RAISE EXCEPTION 'Immutable fields of batches cannot be updated.';
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("""
    CREATE TRIGGER trg_batches_guard_update
    BEFORE UPDATE ON batches
    FOR EACH ROW
    EXECUTE FUNCTION ledger_internal.trg_guard_batch_remaining_qty();
    """)

    # 5. Trigger bảo vệ tính bất biến của sổ cái (chống UPDATE và DELETE)
    op.execute("""
    CREATE OR REPLACE FUNCTION ledger_internal.trg_block_ledger_mutation()
    RETURNS TRIGGER AS $$
    BEGIN
        RAISE EXCEPTION 'Table stock_movements is append-only. Use REVERSAL movements instead of mutation.';
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("""
    CREATE TRIGGER trg_stock_movements_immutable
    BEFORE UPDATE OR DELETE ON stock_movements
    FOR EACH STATEMENT
    EXECUTE FUNCTION ledger_internal.trg_block_ledger_mutation();
    """)

    # 6. Trigger bảo vệ đơn vị cơ sở base_unit_code trên ingredients (BASE_UNIT_LOCKED)
    op.execute("""
    CREATE OR REPLACE FUNCTION ledger_internal.trg_guard_base_unit_immutable()
    RETURNS TRIGGER AS $$
    DECLARE
        v_has_data BOOLEAN;
    BEGIN
        IF NEW.base_unit_code <> OLD.base_unit_code THEN
            SELECT (
                EXISTS(SELECT 1 FROM batches WHERE ingredient_id = OLD.id) OR
                EXISTS(SELECT 1 FROM stock_movements WHERE ingredient_id = OLD.id) OR
                EXISTS(SELECT 1 FROM recipe_items WHERE ingredient_id = OLD.id) OR
                EXISTS(SELECT 1 FROM document_lines dl JOIN documents d ON dl.document_id = d.id WHERE dl.ingredient_id = OLD.id AND d.status <> 'CANCELLED') OR
                EXISTS(SELECT 1 FROM stock_shortages WHERE ingredient_id = OLD.id) OR
                EXISTS(SELECT 1 FROM ingredient_unit_conversions WHERE ingredient_id = OLD.id)
            ) INTO v_has_data;

            IF v_has_data THEN
                RAISE EXCEPTION 'BASE_UNIT_LOCKED: Cannot modify base_unit_code for ingredient with operational data.';
            END IF;
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("""
    CREATE TRIGGER trg_ingredients_base_unit_guard
    BEFORE UPDATE OF base_unit_code ON ingredients
    FOR EACH ROW
    EXECUTE FUNCTION ledger_internal.trg_guard_base_unit_immutable();
    """)

    # 7. View ledger_effective
    op.execute("""
    CREATE OR REPLACE VIEW ledger_effective AS
    SELECT
      sm.id AS movement_id,
      sm.kitchen_id,
      sm.batch_id,
      sm.ingredient_id,
      COALESCE(orig.type, sm.type) AS category,
      sm.type AS original_type,
      CASE
        WHEN sm.sale_line_id IS NOT NULL THEN s.business_date
        WHEN sm.type = 'USAGE_CONSUMPTION' AND sm.document_line_id IS NOT NULL THEN doc.business_date
        WHEN sm.disposal_id IS NOT NULL THEN d.occurred_on
        WHEN sm.type = 'REVERSAL' THEN (
          CASE
            WHEN orig.sale_line_id IS NOT NULL THEN orig_s.business_date
            WHEN orig.type = 'USAGE_CONSUMPTION' AND orig.document_line_id IS NOT NULL THEN orig_doc.business_date
            WHEN orig.disposal_id IS NOT NULL THEN orig_d.occurred_on
            ELSE orig.occurred_on
          END
        )
        ELSE sm.occurred_on
      END AS attribution_date,
      sm.qty_delta,
      sm.unit_cost_snapshot,
      sm.value_vnd,
      sm.sale_line_id,
      sm.disposal_id,
      sm.document_line_id,
      sm.shortage_id,
      sm.reverses_movement_id,
      sm.created_at
    FROM stock_movements sm
    LEFT JOIN stock_movements orig ON sm.reverses_movement_id = orig.id
    LEFT JOIN sale_lines sl ON sm.sale_line_id = sl.id
    LEFT JOIN sales s ON sl.sale_id = s.id
    LEFT JOIN disposals d ON sm.disposal_id = d.id
    LEFT JOIN document_lines dl ON sm.document_line_id = dl.id
    LEFT JOIN documents doc ON dl.document_id = doc.id
    LEFT JOIN sale_lines orig_sl ON orig.sale_line_id = orig_sl.id
    LEFT JOIN sales orig_s ON orig_sl.sale_id = orig_s.id
    LEFT JOIN disposals orig_d ON orig.disposal_id = orig_d.id
    LEFT JOIN document_lines orig_dl ON orig.document_line_id = orig_dl.id
    LEFT JOIN documents orig_doc ON orig_dl.document_id = orig_doc.id;
    """)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS ledger_effective;")
    op.execute("DROP TRIGGER IF EXISTS trg_ingredients_base_unit_guard ON ingredients;")
    op.execute("DROP FUNCTION IF EXISTS ledger_internal.trg_guard_base_unit_immutable();")
    op.execute("DROP TRIGGER IF EXISTS trg_stock_movements_immutable ON stock_movements;")
    op.execute("DROP FUNCTION IF EXISTS ledger_internal.trg_block_ledger_mutation();")
    op.execute("DROP TRIGGER IF EXISTS trg_batches_guard_update ON batches;")
    op.execute("DROP FUNCTION IF EXISTS ledger_internal.trg_guard_batch_remaining_qty();")
    op.execute("DROP TRIGGER IF EXISTS trg_stock_movements_after_insert ON stock_movements;")
    op.execute("DROP FUNCTION IF EXISTS ledger_internal.trg_apply_stock_movement();")
    op.drop_table("stock_movements")
    op.execute("DROP SCHEMA IF EXISTS ledger_internal CASCADE;")
