"""Kitchen context, settings, units, ingredients."""
import uuid
from decimal import Decimal

from sqlalchemy import func, select

from app.core.errors import ApiError
from app.db import models as m
from app.domain.text import normalize, search_name
from app.domain.units import UnitInfo
from app.services.common import Ctx, audit, qstr


def resolve_kitchen_id(session, user_id: uuid.UUID) -> uuid.UUID:
    kid = session.execute(select(m.Kitchen.id).where(m.Kitchen.owner_user_id == user_id)).scalar_one_or_none()
    if kid is None:
        raise ApiError(403, "KITCHEN_NOT_PROVISIONED", "No kitchen is provisioned for this account")
    return kid


def get_settings_row(ctx: Ctx) -> m.KitchenSettings:
    row = ctx.session.get(m.KitchenSettings, ctx.kitchen_id)
    if row is None:
        row = m.KitchenSettings(kitchen_id=ctx.kitchen_id)
        ctx.session.add(row)
        ctx.session.flush()
        ctx.session.refresh(row)
    return row


def settings_out(s: m.KitchenSettings) -> dict:
    return {"expiry_warning_days": s.expiry_warning_days, "target_coverage_days": s.target_coverage_days,
            "consumption_window_days": s.consumption_window_days, "min_history_days": s.min_history_days,
            "unusual_quantity_ratio": str(s.unusual_quantity_ratio), "backdate_limit_days": s.backdate_limit_days,
            "expired_batches_consumable": s.expired_batches_consumable,
            "expired_batch_actions": list(s.expired_batch_actions),
            "policy_status": "PLACEHOLDER_PENDING_D9"}


def list_units(session) -> list[dict]:
    return [{"code": u.code, "label_vi": u.label_vi, "dimension": u.dimension}
            for u in session.execute(select(m.Unit).order_by(m.Unit.code)).scalars()]


def unit_map(session) -> dict[str, UnitInfo]:
    return {u.code: UnitInfo(u.dimension, u.factor_to_dimension_base)
            for u in session.execute(select(m.Unit)).scalars()}


def conversions_for(ctx: Ctx, ingredient_id) -> dict[str, Decimal]:
    rows = ctx.session.execute(select(m.IngredientUnitConversion).where(
        m.IngredientUnitConversion.kitchen_id == ctx.kitchen_id,
        m.IngredientUnitConversion.ingredient_id == ingredient_id)).scalars()
    return {r.unit_code: r.factor_to_base for r in rows}


def get_ingredient(ctx: Ctx, ingredient_id, lock_share: bool = False, include_deleted: bool = False) -> m.Ingredient:
    q = select(m.Ingredient).where(m.Ingredient.kitchen_id == ctx.kitchen_id, m.Ingredient.id == ingredient_id)
    if not include_deleted:
        q = q.where(m.Ingredient.deleted_at.is_(None))
    if lock_share:
        q = q.with_for_update(read=True)
    ing = ctx.session.execute(q).scalar_one_or_none()
    if ing is None:
        raise ApiError(404, "NOT_FOUND", "Ingredient not found")
    return ing


def ingredient_out(ctx: Ctx, ing: m.Ingredient) -> dict:
    s = ctx.session
    aliases = [a.alias for a in s.execute(select(m.IngredientAlias).where(
        m.IngredientAlias.kitchen_id == ctx.kitchen_id, m.IngredientAlias.ingredient_id == ing.id)).scalars()]
    unit = s.get(m.Unit, ing.base_unit_code)
    return {"id": str(ing.id), "name": ing.name,
            "base_unit": {"code": ing.base_unit_code, "dimension": unit.dimension if unit else None},
            "default_location": ing.default_location, "tracks_expiry": ing.tracks_expiry,
            "min_stock_qty": qstr(ing.min_stock_qty), "expiry_warning_days": ing.expiry_warning_days,
            "order_step": qstr(ing.order_step) if ing.order_step is not None else None,
            "aliases": aliases,
            "conversions": [{"unit": u, "factor_to_base": str(f)} for u, f in conversions_for(ctx, ing.id).items()],
            "deleted": ing.deleted_at is not None}


def create_ingredient(ctx: Ctx, d: dict) -> dict:
    s = ctx.session
    units = unit_map(s)
    base = d["base_unit"]
    if base not in units:
        raise ApiError(422, "VALIDATION_ERROR", f"Unknown unit {base}")
    norm = normalize(d["name"])
    dup = s.execute(select(m.Ingredient.id).where(
        m.Ingredient.kitchen_id == ctx.kitchen_id, m.Ingredient.normalized_name == norm,
        m.Ingredient.deleted_at.is_(None))).first()
    if dup:
        raise ApiError(409, "DUPLICATE_NAME", "An ingredient with this name already exists")
    ing = m.Ingredient(
        kitchen_id=ctx.kitchen_id, name=d["name"].strip(), normalized_name=norm, search_name=search_name(d["name"]),
        base_unit_code=base, default_location=d.get("default_location", "FRIDGE"),
        tracks_expiry=d.get("tracks_expiry", True), min_stock_qty=Decimal(str(d.get("min_stock_qty", 0))),
        expiry_warning_days=d.get("expiry_warning_days"),
        order_step=Decimal(str(d["order_step"])) if d.get("order_step") is not None else None)
    s.add(ing)
    s.flush()
    for a in d.get("aliases", []):
        na = normalize(a)
        if na and na != norm:
            s.add(m.IngredientAlias(kitchen_id=ctx.kitchen_id, ingredient_id=ing.id, alias=a.strip(), normalized_alias=na))
    for c in d.get("conversions", []):
        cu, bu = units.get(c["unit"]), units[base]
        if cu is None or c["unit"] == base:
            raise ApiError(422, "VALIDATION_ERROR", "Invalid conversion unit")
        if cu.dimension == bu.dimension and cu.dimension in ("MASS", "VOLUME"):
            raise ApiError(422, "VALIDATION_ERROR", "Same-dimension units convert automatically; no row needed")
        s.add(m.IngredientUnitConversion(kitchen_id=ctx.kitchen_id, ingredient_id=ing.id, unit_code=c["unit"],
                                         base_unit_code=base, factor_to_base=Decimal(str(c["factor_to_base"]))))
    s.flush()
    audit(ctx, "INGREDIENT_CREATED", "ingredient", ing.id, after={"name": ing.name})
    return ingredient_out(ctx, ing)


def list_ingredients(ctx: Ctx, q: str | None, include_deleted: bool, limit: int, offset: int) -> tuple[list[dict], int | None]:
    stmt = select(m.Ingredient).where(m.Ingredient.kitchen_id == ctx.kitchen_id)
    if not include_deleted:
        stmt = stmt.where(m.Ingredient.deleted_at.is_(None))
    if q:
        stmt = stmt.where(m.Ingredient.search_name.like(f"%{search_name(q)}%"))
    rows = ctx.session.execute(stmt.order_by(m.Ingredient.normalized_name).limit(limit + 1).offset(offset)).scalars().all()
    nxt = offset + limit if len(rows) > limit else None
    return [ingredient_out(ctx, r) for r in rows[:limit]], nxt


def delete_ingredient(ctx: Ctx, ingredient_id) -> None:
    ing = get_ingredient(ctx, ingredient_id)
    in_use = ctx.session.execute(select(func.count()).select_from(m.RecipeItem).join(
        m.Dish, (m.Dish.kitchen_id == m.RecipeItem.kitchen_id) & (m.Dish.id == m.RecipeItem.dish_id)).where(
        m.RecipeItem.kitchen_id == ctx.kitchen_id, m.RecipeItem.ingredient_id == ing.id,
        m.Dish.deleted_at.is_(None))).scalar_one()
    if in_use:
        raise ApiError(409, "INGREDIENT_IN_USE", "An active recipe uses this ingredient")
    ing.deleted_at = func.now()
    audit(ctx, "INGREDIENT_DELETED", "ingredient", ing.id)
