"""Create the demo profile, kitchen and DEMO data through the real services (Rev 3 I.3: no hand-made ledger rows).

    python -m app.scripts.seed_demo --user-id <SUPABASE_USER_UUID> [--name "Bếp demo"]

Uses MIGRATION_DATABASE_URL (session pooler, port 5432) when set. Idempotent: does nothing if the kitchen already has
ingredients. The kitchen is named 'DEMO ...' so sample data is never mistaken for real operations.
Run it on the database you intend to demo with; it only inserts.
"""
import argparse
import uuid
from datetime import timedelta

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import get_settings, to_sqlalchemy_url
from app.db import models as m
from app.domain.expiry import today_vn
from app.services import catalog, inventory, sales
from app.services.common import Ctx

# name, base unit, location, min stock
INGREDIENTS = [
    ("rau muống", "kg", "FRIDGE", "1"), ("sữa tươi", "hộp", "FRIDGE", "2"), ("trứng gà", "quả", "FRIDGE", "10"),
    ("cà chua", "kg", "FRIDGE", "1"), ("hành lá", "bó", "FRIDGE", "2"), ("thịt ba rọi", "kg", "FREEZER", "1"),
    ("ức gà", "kg", "FRIDGE", "1"), ("gạo", "kg", "PANTRY", "5"), ("hành tây", "kg", "PANTRY", "1"),
    ("tỏi", "kg", "PANTRY", "0.2"), ("nấm", "kg", "FRIDGE", "0.5"), ("đậu hũ", "bìa", "FRIDGE", "4"),
]
# name, qty, unit price per base unit, received days ago, expiry in N days (relative to today)
BATCHES = [
    ("rau muống", 1, 20000, 2, -1), ("sữa tươi", 2, 30000, 5, 1), ("cà chua", 1, 35000, 5, 2), ("cà chua", 1.5, 38000, 1, 6),
    ("trứng gà", 60, 3500, 6, 9), ("thịt ba rọi", 1, 150000, 3, 25), ("thịt ba rọi", 2, 155000, 0, 28),
    ("gạo", 25, 24000, 10, 300), ("tỏi", 0.5, 60000, 8, 20), ("hành tây", 2, 30000, 6, 12), ("hành lá", 8, 8000, 2, 3),
    ("ức gà", 2, 85000, 1, 2), ("nấm", 1, 90000, 1, 4), ("đậu hũ", 8, 6000, 1, 3),
]
DISHES = [
    ("Trứng chiên cà chua", 35000, [("cà chua", "0.1"), ("trứng gà", "2"), ("hành lá", "0.1")]),
    ("Canh cà chua trứng", 30000, [("cà chua", "0.1"), ("trứng gà", "1"), ("hành lá", "0.1")]),
    ("Rau muống xào tỏi", 30000, [("rau muống", "0.2"), ("tỏi", "0.02")]),
    ("Thịt kho trứng", 65000, [("thịt ba rọi", "0.15"), ("trứng gà", "2"), ("hành tây", "0.05")]),
    ("Gà xào nấm", 60000, [("ức gà", "0.15"), ("nấm", "0.1"), ("hành tây", "0.05"), ("tỏi", "0.01")]),
    ("Đậu hũ sốt cà chua", 35000, [("đậu hũ", "1"), ("cà chua", "0.1"), ("hành lá", "0.1")]),
    ("Cơm chiên trứng", 40000, [("gạo", "0.15"), ("trứng gà", "2"), ("hành lá", "0.1")]),
]
SALES = [  # days ago, [(dish, portions)]
    (6, [("Cơm chiên trứng", 8), ("Trứng chiên cà chua", 6)]), (5, [("Gà xào nấm", 4), ("Cơm chiên trứng", 6)]),
    (4, [("Trứng chiên cà chua", 7), ("Thịt kho trứng", 3)]), (3, [("Cơm chiên trứng", 7), ("Canh cà chua trứng", 5)]),
    (2, [("Trứng chiên cà chua", 8), ("Gà xào nấm", 3)]), (1, [("Cơm chiên trứng", 9), ("Đậu hũ sốt cà chua", 4)]),
]


def seed(session: Session, user_id: uuid.UUID, display_name: str) -> str:
    if session.get(m.UserProfile, user_id) is None:
        session.add(m.UserProfile(id=user_id, display_name=display_name))
        session.flush()
    kitchen = session.execute(select(m.Kitchen).where(m.Kitchen.owner_user_id == user_id)).scalar_one_or_none()
    if kitchen is None:
        kitchen = m.Kitchen(owner_user_id=user_id, name="DEMO - dữ liệu mẫu")
        session.add(kitchen)
        session.flush()
    ctx = Ctx(session, user_id, kitchen.id, "seed_demo")
    catalog.get_settings_row(ctx)
    if session.execute(select(m.Ingredient.id).where(m.Ingredient.kitchen_id == kitchen.id).limit(1)).first():
        return "kitchen already has data: nothing changed"
    ids = {}
    for name, unit, loc, mn in INGREDIENTS:
        ids[name] = uuid.UUID(catalog.create_ingredient(ctx, {"name": name, "base_unit": unit, "default_location": loc,
                                                              "min_stock_qty": mn})["id"])
    today = today_vn()
    for name, qty, price, ago, exp in BATCHES:
        inventory.receive(ctx, {"ingredient_id": ids[name], "quantity": qty, "unit_price_vnd": price,
                                "received_on": today - timedelta(days=ago), "expiry_date": today + timedelta(days=exp)})
    dish_ids = {}
    for name, price, recipe in DISHES:
        d = sales.create_dish(ctx, {"name": name, "price_vnd": price,
                                    "recipe": [{"ingredient_id": ids[i], "quantity": q} for i, q in recipe]})
        dish_ids[name] = uuid.UUID(d["id"])
    for ago, lines in SALES:
        sales.record_sale(ctx, today - timedelta(days=ago), [{"dish_id": dish_ids[n], "quantity": q} for n, q in lines])
    session.commit()   # deferred ledger triggers run here; a failure means a real inconsistency
    return "demo data created"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--user-id", required=True)
    ap.add_argument("--name", default="Bếp demo")
    a = ap.parse_args()
    s = get_settings()
    url = s.migration_database_url or s.database_url
    if not url:
        raise SystemExit("Set MIGRATION_DATABASE_URL (or DATABASE_URL) in backend/.env")
    engine = create_engine(to_sqlalchemy_url(url), connect_args={"prepare_threshold": None})
    with Session(engine, expire_on_commit=False) as session:
        print(seed(session, uuid.UUID(a.user_id), a.name))


if __name__ == "__main__":
    main()
