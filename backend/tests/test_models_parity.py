"""Models must mirror the migrations column-for-column. Needs SQLAlchemy (installed on Windows, not in the build sandbox)."""
import importlib.util
import pathlib
import re
import types

import pytest

pytest.importorskip("sqlalchemy")
VERSIONS = pathlib.Path(__file__).resolve().parents[1] / "alembic" / "versions"
CONSTRAINT_WORDS = ("CONSTRAINT", "PRIMARY KEY (", "UNIQUE (", "CHECK (", "FOREIGN KEY")


def migration_columns():
    import sys
    sys.modules.setdefault("alembic", types.SimpleNamespace(op=types.SimpleNamespace(execute=lambda s: None)))
    tables = {}
    for p in sorted(VERSIONS.glob("00*.py")):
        spec = importlib.util.spec_from_file_location(p.stem, p)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        for s in m.UP:
            t = re.match(r"CREATE TABLE (\w+) \(", s)
            if not t:
                continue
            cols = set()
            for raw in s.splitlines()[1:]:
                if not raw.startswith("  ") or raw.startswith("   "):   # column lines are indented exactly 2 spaces
                    continue
                line = raw.strip().rstrip(",")
                if line.upper().startswith(CONSTRAINT_WORDS):
                    continue
                cols.add(line.split()[0])
            tables[t.group(1)] = cols
    return tables


def test_every_table_and_column_has_a_model():
    from app.db.models import Base
    mine = {t.name: {c.name for c in t.columns} for t in Base.metadata.tables.values()}
    mig = migration_columns()
    assert set(mine) == set(mig) - {"alembic_version"}
    for name, cols in mig.items():
        assert mine[name] == cols, (name, cols ^ mine[name])
