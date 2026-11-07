"""Static checks on the Alembic migrations. No database needed. These do NOT prove the SQL is valid
in PostgreSQL; that needs tests/db (TEST_DATABASE_URL) or a real `alembic upgrade`."""
import importlib.util
import pathlib
import re

VERSIONS = pathlib.Path(__file__).resolve().parents[1] / "alembic" / "versions"
BIND_LIKE = re.compile(r"(?<![:\w\\]):[A-Za-z_]\w*")
NO_COMPOSITE_UNIQUE_NEEDED = {  # tables whose kitchen_id is part of the PK or that no child references
    "kitchen_settings", "recipe_items", "ingredient_unit_conversions", "notification_reads",
    "audit_log", "idempotency_keys",
}


def load():
    mods = []
    for p in sorted(VERSIONS.glob("00*.py")):
        spec = importlib.util.spec_from_file_location(p.stem, p)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        mods.append(m)
    return mods


def statements(m):
    return list(m.UP) + list(m.DOWN)


def test_revision_chain_is_linear_0001_to_0012():
    mods = load()
    assert [m.revision for m in mods] == [f"{i:04d}" for i in range(1, 13)]
    assert mods[0].down_revision is None
    for prev, cur in zip(mods, mods[1:]):
        assert cur.down_revision == prev.revision


def test_every_migration_has_up_and_down():
    for m in load():
        assert m.UP and m.DOWN and callable(m.upgrade) and callable(m.downgrade)


def test_no_percent_signs_or_bind_like_tokens():
    for m in load():
        for s in statements(m):
            assert "%" not in s, (m.revision, s[:80])
            assert not BIND_LIKE.search(s), (m.revision, BIND_LIKE.search(s).group(0), s[:80])


def test_tenant_tables_have_composite_unique_for_children():
    for m in load():
        for s in m.UP:
            t = re.match(r"CREATE TABLE (\w+) \(", s)
            if not t or "kitchen_id uuid NOT NULL" not in s:
                continue
            if t.group(1) in NO_COMPOSITE_UNIQUE_NEEDED:
                continue
            assert "UNIQUE (kitchen_id, id)" in s, t.group(1)


def test_core_mode_has_no_custom_roles_or_policies():
    for m in load():
        for s in m.UP:
            up = s.upper()
            assert "CREATE ROLE" not in up and "CREATE POLICY" not in up, m.revision
            assert "FORCE ROW LEVEL SECURITY" not in up
            assert "ALTER DEFAULT PRIVILEGES" not in up


def test_security_invoker_view_and_definer_function_pinned():
    m9 = [m for m in load() if m.revision == "0009"][0]
    sql = "\n".join(m9.UP)
    assert "WITH (security_invoker = true)" in sql
    assert "SECURITY DEFINER SET search_path = pg_catalog" in sql
    assert sql.count("SECURITY DEFINER") == 1  # only the cache function


def test_migrations_after_0011_that_create_tables_manage_rls_and_privileges():
    for m in load():
        if m.revision <= "0011":
            continue
        for s in m.UP:
            if s.startswith("CREATE TABLE"):
                joined = "\n".join(m.UP).upper()
                assert "ENABLE ROW LEVEL SECURITY" in joined and "REVOKE ALL ON" in joined, m.revision
