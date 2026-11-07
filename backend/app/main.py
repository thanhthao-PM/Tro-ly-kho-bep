import logging

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.auth import AuthUser, current_user
from app.core.config import get_settings
from app.api.v1.routes import router as api_router
from app.core.database import get_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("kitchen")
s = get_settings()

# NOTE: migrations are never run at startup (implementation plan, section 1.6).
app = FastAPI(title="Kitchen Assistant API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=s.cors_origin_list,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
    max_age=600,
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
def health_db():
    with get_engine().connect() as c:
        c.execute(text("select 1"))
    return {"status": "ok", "database": "reachable"}


@app.get("/api/v1/me")
def me(user: AuthUser = Depends(current_user)):
    # Kitchen resolution (user_profiles -> kitchen_id) comes with the schema phase.
    return {"user_id": user.user_id, "email": user.email}


app.include_router(api_router)


def _err(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse({"detail": {"code": code, "message": message}}, status_code=status)


@app.exception_handler(DBAPIError)
async def db_error(_: Request, exc: DBAPIError):
    """Map database guard failures to stable API errors without leaking SQL."""
    orig = getattr(exc, "orig", None)
    msg, state = str(orig or exc), getattr(orig, "sqlstate", None)
    log.warning("database error sqlstate=%s", state)
    if "ck_batches_remaining" in msg or "remaining_qty" in msg and state == "23514":
        return _err(409, "INSUFFICIENT_STOCK", "Not enough usable stock")
    if "BASE_UNIT_LOCKED" in msg:
        return _err(409, "BASE_UNIT_LOCKED", "The base unit cannot change once the ingredient has operational data")
    if state == "23505":
        return _err(409, "DUPLICATE", "A record with the same unique value already exists")
    if state in ("23503", "23514", "23000"):
        return _err(409, "CONSTRAINT_VIOLATION", "The operation violates a data integrity rule")
    if state == "55P03":
        return _err(409, "LOCK_TIMEOUT", "A resource is locked by another request; retry")
    return _err(500, "INTERNAL_ERROR", "Unexpected database error")
