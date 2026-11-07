from alembic import context
from sqlalchemy import create_engine, pool

from app.core.config import get_settings, to_sqlalchemy_url

target_metadata = None  # Hand-written SQL migrations; Alembic is the sole schema authority.


def _url() -> str:
    url = get_settings().migration_database_url
    if not url:
        raise RuntimeError("MIGRATION_DATABASE_URL is not configured (use port 5432, not 6543)")
    return to_sqlalchemy_url(url)


def run_offline() -> None:
    """`alembic upgrade head --sql` : prints SQL for review, never connects."""
    # Offline output only needs the dialect, so no database URL (secret) is required for a preview.
    raw = get_settings().migration_database_url
    url = to_sqlalchemy_url(raw) if raw else "postgresql+psycopg://"
    context.configure(url=url, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_online() -> None:
    engine = create_engine(_url(), poolclass=pool.NullPool)
    with engine.connect() as conn:
        context.configure(connection=conn, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_offline()
else:
    run_online()
