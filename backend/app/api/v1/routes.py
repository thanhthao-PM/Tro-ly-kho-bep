"""Thin HTTP layer: validate, call ONE service, commit, return. No business logic here."""
from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import JSONResponse

from app.api.deps import get_ctx
from app.api.v1 import schemas as sc
from app.domain.expiry import today_vn
from app.services import assistant, catalog, inventory, reporting, sales
from app.services.common import Ctx, request_hash, run_idempotent

router = APIRouter(prefix="/api/v1")


def done(ctx: Ctx, body, status: int = 200):
    ctx.session.commit()          # explicit commit: deferred ledger triggers fire here, so failures become API errors
    return JSONResponse(body, status_code=status) if status != 200 else body


def page(ctx: Ctx, items, nxt):
    ctx.session.commit()
    return {"items": items, "next_cursor": str(nxt) if nxt is not None else None}


def idem(ctx: Ctx, request: Request, key: str | None, endpoint: str, payload, fn, ok_status: int = 201):
    body = payload.model_dump(mode="json") if payload is not None else None
    st, resp, replay = run_idempotent(ctx, endpoint, key, request_hash(request.method, request.url.path, body),
                                      lambda: (ok_status, fn()))
    ctx.session.commit()
    return JSONResponse(resp, status_code=st, headers={"Idempotent-Replay": "true"} if replay else {})


def cursor(c: str | None) -> int:
    return int(c) if c and c.isdigit() else 0


# ----- settings, units, ingredients -----
@router.get("/settings")
def get_settings_(ctx: Ctx = Depends(get_ctx)):
    return done(ctx, catalog.settings_out(catalog.get_settings_row(ctx)))


@router.get("/units")
def units(ctx: Ctx = Depends(get_ctx)):
    return done(ctx, {"items": catalog.list_units(ctx.session)})


@router.get("/ingredients")
def ingredients(q: str | None = None, include_deleted: bool = False, limit: int = Query(50, ge=1, le=100),
                cursor_: str | None = Query(None, alias="cursor"), ctx: Ctx = Depends(get_ctx)):
    items, nxt = catalog.list_ingredients(ctx, q, include_deleted, limit, cursor(cursor_))
    return page(ctx, items, nxt)


@router.post("/ingredients", status_code=201)
def create_ingredient(p: sc.IngredientCreate, ctx: Ctx = Depends(get_ctx)):
    return done(ctx, catalog.create_ingredient(ctx, p.model_dump(exclude_none=True)), 201)


@router.get("/ingredients/{ingredient_id}")
def ingredient(ingredient_id: UUID, ctx: Ctx = Depends(get_ctx)):
    return done(ctx, catalog.ingredient_out(ctx, catalog.get_ingredient(ctx, ingredient_id)))


@router.delete("/ingredients/{ingredient_id}", status_code=204)
def delete_ingredient(ingredient_id: UUID, ctx: Ctx = Depends(get_ctx)):
    catalog.delete_ingredient(ctx, ingredient_id)
    ctx.session.commit()


# ----- inventory -----
@router.get("/inventory/ingredients")
def inventory_overview(ctx: Ctx = Depends(get_ctx)):
    return done(ctx, {"items": inventory.overview(ctx), "next_cursor": None})


@router.get("/inventory/ingredients/{ingredient_id}/batches")
def ingredient_batches(ingredient_id: UUID, include_empty: bool = False, ctx: Ctx = Depends(get_ctx)):
    return done(ctx, inventory.batches_of(ctx, ingredient_id, include_empty))


@router.get("/inventory/summary")
def inventory_summary(ctx: Ctx = Depends(get_ctx)):
    return done(ctx, inventory.summary(ctx))


@router.get("/stock-movements")
def stock_movements(type: str | None = None, limit: int = Query(50, ge=1, le=100),
                    cursor_: str | None = Query(None, alias="cursor"), ctx: Ctx = Depends(get_ctx)):
    items, nxt = inventory.movements(ctx, limit, cursor(cursor_), type)
    return page(ctx, items, nxt)


@router.post("/batches", status_code=201)
def receive(p: sc.ReceiptIn, request: Request, idempotency_key: str | None = Header(None), ctx: Ctx = Depends(get_ctx)):
    return idem(ctx, request, idempotency_key, "POST /batches", p, lambda: inventory.receive(ctx, p.model_dump()))


@router.post("/batches/{batch_id}/disposals", status_code=201)
def dispose(batch_id: UUID, p: sc.DisposalIn, request: Request, idempotency_key: str | None = Header(None),
            ctx: Ctx = Depends(get_ctx)):
    return idem(ctx, request, idempotency_key, "POST /batches/{id}/disposals", p,
                lambda: inventory.dispose(ctx, batch_id, p.model_dump()))


@router.get("/expiring-batches")
def expiring(ctx: Ctx = Depends(get_ctx)):
    return done(ctx, inventory.expiring(ctx))


# ----- menu -----
@router.get("/dishes")
def dishes(ctx: Ctx = Depends(get_ctx)):
    items = [{k: v for k, v in d.items() if k != "ingredient_ids"} for d in sales.dish_snapshots(ctx)]
    return done(ctx, {"items": items, "next_cursor": None})


@router.post("/dishes", status_code=201)
def create_dish(p: sc.DishCreate, ctx: Ctx = Depends(get_ctx)):
    d = sales.create_dish(ctx, p.model_dump())
    d.pop("ingredient_ids", None)
    return done(ctx, d, 201)


# ----- sales report documents (manual) -----
@router.post("/documents", status_code=201)
def create_document(p: sc.DocumentCreate, ctx: Ctx = Depends(get_ctx)):
    return done(ctx, sales.create_document(ctx, p.kind, p.business_date), 201)


@router.get("/documents/{doc_id}")
def document(doc_id: UUID, ctx: Ctx = Depends(get_ctx)):
    return done(ctx, sales.get_document(ctx, doc_id))


@router.post("/documents/{doc_id}/lines", status_code=201)
def add_line(doc_id: UUID, p: sc.LineIn, ctx: Ctx = Depends(get_ctx)):
    return done(ctx, sales.add_line(ctx, doc_id, p.dish_id, p.quantity), 201)


@router.delete("/documents/{doc_id}/lines/{line_id}", status_code=204)
def delete_line(doc_id: UUID, line_id: UUID, ctx: Ctx = Depends(get_ctx)):
    sales.delete_line(ctx, doc_id, line_id)
    ctx.session.commit()


@router.post("/documents/{doc_id}/confirm", status_code=200)
def confirm(doc_id: UUID, request: Request, idempotency_key: str | None = Header(None), ctx: Ctx = Depends(get_ctx)):
    return idem(ctx, request, idempotency_key, "POST /documents/{id}/confirm", None,
                lambda: sales.confirm_document(ctx, doc_id), ok_status=200)


# ----- sales, shortages -----
@router.get("/sales")
def list_sales(limit: int = Query(50, ge=1, le=100), cursor_: str | None = Query(None, alias="cursor"), ctx: Ctx = Depends(get_ctx)):
    items, nxt = sales.list_sales(ctx, limit, cursor(cursor_))
    return page(ctx, items, nxt)


@router.get("/sales/{sale_id}")
def get_sale(sale_id: UUID, ctx: Ctx = Depends(get_ctx)):
    return done(ctx, sales.get_sale(ctx, sale_id))


@router.get("/shortages")
def shortages(status: str | None = Query(None, pattern="^(OPEN|RESOLVED)$"), ctx: Ctx = Depends(get_ctx)):
    return done(ctx, {"items": sales.list_shortages(ctx, status), "next_cursor": None})


@router.post("/shortages/{shortage_id}/resolve")
def resolve(shortage_id: UUID, p: sc.ResolveIn, request: Request, idempotency_key: str | None = Header(None),
            ctx: Ctx = Depends(get_ctx)):
    return idem(ctx, request, idempotency_key, "POST /shortages/{id}/resolve", p,
                lambda: sales.resolve_shortage(ctx, shortage_id, p.action, p.note), ok_status=200)


# ----- reports, replenishment, assistant -----
@router.get("/reports/summary")
def report_summary(from_: str | None = Query(None, alias="from"), to: str | None = None, ctx: Ctx = Depends(get_ctx)):
    from datetime import date
    t = date.fromisoformat(to) if to else today_vn()
    f = date.fromisoformat(from_) if from_ else t - timedelta(days=6)
    return done(ctx, reporting.summary(ctx, f, t))


@router.get("/replenishment-suggestions")
def replenishment(ctx: Ctx = Depends(get_ctx)):
    return done(ctx, reporting.replenishment(ctx))


@router.post("/assistant/messages")
def assistant_message(p: sc.AssistantIn, ctx: Ctx = Depends(get_ctx)):
    return done(ctx, assistant.answer(ctx, p.message, [h.model_dump() for h in p.history]))
