"""Shared service plumbing: request context, audit rows, formatting, the idempotency protocol (Rev 4 s2.C)."""
import hashlib
import json
import uuid
from dataclasses import dataclass
from decimal import Decimal

from fastapi.encoders import jsonable_encoder
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.db import models as m


@dataclass
class Ctx:
    session: Session
    user_id: uuid.UUID
    kitchen_id: uuid.UUID
    request_id: str = ""


def qstr(v) -> str:
    return f"{Decimal(v):.3f}"


def cstr(v) -> str:
    return f"{Decimal(v):.6f}"


def audit(ctx: Ctx, action: str, entity_type: str, entity_id, before=None, after=None) -> None:
    ctx.session.add(m.AuditLog(
        kitchen_id=ctx.kitchen_id, actor_id=ctx.user_id, action=action, entity_type=entity_type,
        entity_id=str(entity_id), before=jsonable_encoder(before) if before is not None else None,
        after=jsonable_encoder(after) if after is not None else None, request_id=ctx.request_id or None))


def request_hash(method: str, path: str, body) -> str:
    raw = json.dumps([method, path, jsonable_encoder(body)], sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def _sqlstate(e: DBAPIError):
    return getattr(getattr(e, "orig", None), "sqlstate", None)


def run_idempotent(ctx: Ctx, endpoint: str, key: str | None, req_hash: str, fn):
    """Claim the key and run the operation in ONE transaction (the request's transaction).
    fn() -> (status_code, body). Returns (status_code, body, replayed)."""
    if not key:
        raise ApiError(422, "VALIDATION_ERROR", "Idempotency-Key header is required")
    s = ctx.session
    args = {"id": uuid.uuid4(), "k": ctx.kitchen_id, "e": endpoint, "key": key, "h": req_hash, "a": ctx.user_id}
    try:
        s.execute(text("SET LOCAL lock_timeout = '2s'"))
        claimed = s.execute(text(
            "INSERT INTO idempotency_keys (id, kitchen_id, endpoint, key, request_hash, actor_id, status) "
            "VALUES (:id, :k, :e, :key, :h, :a, 'CLAIMED') "
            "ON CONFLICT (kitchen_id, endpoint, key) DO NOTHING RETURNING id"), args).first()
        if claimed is None:
            ex = s.execute(text(
                "SELECT request_hash, status, response_status, response_body FROM idempotency_keys "
                "WHERE kitchen_id = :k AND endpoint = :e AND key = :key"), args).first()
            if ex is None or ex.status != "COMPLETED":
                raise ApiError(409, "REQUEST_IN_PROGRESS", "The same request is still being processed")
            if ex.request_hash != req_hash:
                raise ApiError(422, "IDEMPOTENCY_KEY_REUSED", "This key was used for a different request")
            return ex.response_status, ex.response_body, True
    except DBAPIError as e:
        if _sqlstate(e) == "55P03":
            raise ApiError(409, "REQUEST_IN_PROGRESS", "The same request is still being processed")
        raise
    try:
        status, body = fn()
    except DBAPIError as e:
        if _sqlstate(e) == "55P03":
            raise ApiError(409, "LOCK_TIMEOUT", "A resource is locked by another request; retry")
        raise
    body = jsonable_encoder(body)
    s.execute(text(
        "UPDATE idempotency_keys SET status = 'COMPLETED', response_status = :st, "
        "response_body = CAST(:b AS jsonb), completed_at = now() WHERE id = :id"),
        {"st": status, "b": json.dumps(body), "id": args["id"]})
    return status, body, False
