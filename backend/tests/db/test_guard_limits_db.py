"""6.3 s3.1 tests L1-L3 (Core DB). NOT RUN in the build sandbox. Same safety model as test_ledger_db.py."""
import pytest

from . import _helpers as h

psycopg = pytest.importorskip("psycopg")
pytestmark = pytest.mark.skipif(not h.URL, reason="TEST_DATABASE_URL not set")


@pytest.fixture()
def cx():
    c = h.connect()
    try:
        yield c
    finally:
        c.rollback()
        c.close()


def test_L1_guard_does_not_block_trigger_initiated_update_but_commit_check_fails(cx):
    _, k = h.mk_kitchen(cx); ing = h.mk_ingredient(cx, k); b = h.mk_batch(cx, k, ing)
    cx.execute("CREATE TEMP TABLE l1_scratch (x int)")
    cx.execute(f"""CREATE FUNCTION public.l1_fn() RETURNS trigger LANGUAGE plpgsql AS $f$
      BEGIN UPDATE public.batches SET remaining_qty = remaining_qty + 1 WHERE id = '{b}'; RETURN NEW; END $f$""")
    cx.execute("CREATE TRIGGER l1_trg AFTER INSERT ON l1_scratch FOR EACH ROW EXECUTE FUNCTION public.l1_fn()")
    cx.execute("INSERT INTO l1_scratch VALUES (1)")          # depth 2: the guard does NOT stop it (documented limitation)
    assert h.remaining(cx, b) == 11
    with pytest.raises(psycopg.Error):                       # ...but the cache no longer equals the ledger: commit must fail
        h.settle(cx)


def test_L2_do_block_and_plain_function_rejected(cx):
    _, k = h.mk_kitchen(cx); ing = h.mk_ingredient(cx, k); b = h.mk_batch(cx, k, ing)
    h.expect_error(cx, f"DO $d$ BEGIN UPDATE public.batches SET remaining_qty = 5 WHERE id = '{b}'; END $d$", (), "ledger only")
    cx.execute("""CREATE FUNCTION public.l2_fn(i uuid) RETURNS void LANGUAGE plpgsql AS $f$
      BEGIN UPDATE public.batches SET remaining_qty = 5 WHERE id = i; END $f$""")
    h.expect_error(cx, "SELECT public.l2_fn(%s)", (b,), "ledger only")


def test_L3_only_the_movement_apply_function_updates_batches(cx):
    rows = cx.execute("""SELECT n.nspname || '.' || p.proname FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
                         WHERE n.nspname IN ('public','ledger_internal') AND p.prosrc ~* 'update[[:space:]]+(public\\.)?batches'""").fetchall()
    assert [r[0] for r in rows] == ["ledger_internal.apply_movement"]
