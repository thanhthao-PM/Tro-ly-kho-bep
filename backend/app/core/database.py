from collections.abc import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings, to_sqlalchemy_url

_engine: Engine | None = None
_factory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """Lazy engine so the app can start (and /health work) without a DB URL."""
    global _engine, _factory
    if _engine is None:
        s = get_settings()
        if not s.database_url:
            raise RuntimeError("DATABASE_URL is not configured")
        _engine = create_engine(
            to_sqlalchemy_url(s.database_url),
            pool_size=s.pool_size,
            max_overflow=s.max_overflow,
            pool_timeout=s.pool_timeout,
            pool_recycle=s.pool_recycle,
            pool_pre_ping=True,
            # Required behind Supabase Transaction Pooler (port 6543).
            connect_args={"prepare_threshold": None},
        )
        _factory = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def get_session() -> Iterator[Session]:
    get_engine()
    assert _factory is not None
    with _factory() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
