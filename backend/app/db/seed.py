"""
seed.py: Kịch bản khởi tạo và nạp dữ liệu mẫu cho Cơ sở dữ liệu PostgreSQL.
Hỗ trợ 2 chế độ:
- Chế độ sạch (--clean): Chỉ tạo UserProfile, Kitchen, KitchenSettings, Units, Ingredients và Dishes.
- Chế độ demo (--demo): Nạp thêm các lô hàng mẫu, biến động kho và bán hàng giả định phục vụ trình diễn.
"""
import sys
import argparse
import uuid
from decimal import Decimal
from datetime import date, datetime, timedelta

from sqlalchemy import select, and_, delete
from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.db.models.kitchen import UserProfile, Kitchen, KitchenSettings
from app.db.models.catalog import Unit, Ingredient, IngredientUnitConversion
from app.db.models.menu import Dish, DishRecipeItem
from app.db.models.inventory import Batch, StockMovement
from app.core.config import settings

# ID cố định cho môi trường đơn bếp (Single Kitchen MVP)
DEMO_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
DEMO_KITCHEN_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")

STANDARD_UNITS = [
    {"code": "kg", "label_vi": "Kilogram", "dimension": "MASS", "factor": Decimal("1.0")},
    {"code": "g", "label_vi": "Gram", "dimension": "MASS", "factor": Decimal("0.001")},
    {"code": "l", "label_vi": "Lít", "dimension": "VOLUME", "factor": Decimal("1.0")},
    {"code": "ml", "label_vi": "Mililít", "dimension": "VOLUME", "factor": Decimal("0.001")},
    {"code": "quả", "label_vi": "Quả", "dimension": "COUNT", "factor": None},
    {"code": "hộp", "label_vi": "Hộp", "dimension": "COUNT", "factor": None},
    {"code": "bó", "label_vi": "Bó", "dimension": "COUNT", "factor": None},
    {"code": "gói", "label_vi": "Gói", "dimension": "COUNT", "factor": None},
    {"code": "chai", "label_vi": "Chai", "dimension": "COUNT", "factor": None},
    {"code": "củ", "label_vi": "Củ", "dimension": "COUNT", "factor": None},
]

STANDARD_INGREDIENTS = [
    {
        "id": "11111111-0001-0000-0000-000000000001",
        "name": "rau muống",
        "unit": "kg",
        "location": "FRIDGE",
        "min_stock": Decimal("1.0"),
        "step": Decimal("0.5"),
        "warning_days": 3
    },
    {
        "id": "11111111-0002-0000-0000-000000000002",
        "name": "sữa tươi",
        "unit": "hộp",
        "location": "FRIDGE",
        "min_stock": Decimal("2.0"),
        "step": Decimal("1.0"),
        "warning_days": 3
    },
    {
        "id": "11111111-0003-0000-0000-000000000003",
        "name": "trứng gà",
        "unit": "quả",
        "location": "FRIDGE",
        "min_stock": Decimal("20.0"),
        "step": Decimal("10.0"),
        "warning_days": 5
    },
    {
        "id": "11111111-0004-0000-0000-000000000004",
        "name": "cà chua",
        "unit": "kg",
        "location": "FRIDGE",
        "min_stock": Decimal("1.0"),
        "step": Decimal("0.5"),
        "warning_days": 3
    },
    {
        "id": "11111111-0005-0000-0000-000000000005",
        "name": "hành lá",
        "unit": "bó",
        "location": "FRIDGE",
        "min_stock": Decimal("2.0"),
        "step": Decimal("1.0"),
        "warning_days": 2
    },
    {
        "id": "11111111-0006-0000-0000-000000000006",
        "name": "thịt ba rọi",
        "unit": "kg",
        "location": "FREEZER",
        "min_stock": Decimal("2.0"),
        "step": Decimal("1.0"),
        "warning_days": 3
    },
    {
        "id": "11111111-0007-0000-0000-000000000007",
        "name": "thịt bò thăn",
        "unit": "kg",
        "location": "FREEZER",
        "min_stock": Decimal("1.5"),
        "step": Decimal("0.5"),
        "warning_days": 3
    },
    {
        "id": "11111111-0008-0000-0000-000000000008",
        "name": "cá hồi fillet",
        "unit": "kg",
        "location": "FREEZER",
        "min_stock": Decimal("1.0"),
        "step": Decimal("0.5"),
        "warning_days": 2
    },
    {
        "id": "11111111-0009-0000-0000-000000000009",
        "name": "tỏi tây",
        "unit": "bó",
        "location": "FRIDGE",
        "min_stock": Decimal("1.0"),
        "step": Decimal("1.0"),
        "warning_days": 3
    },
    {
        "id": "11111111-0010-0000-0000-000000000010",
        "name": "gạo thơm st25",
        "unit": "kg",
        "location": "PANTRY",
        "min_stock": Decimal("10.0"),
        "step": Decimal("5.0"),
        "warning_days": 7
    },
]

STANDARD_DISHES = [
    {
        "id": "22222222-0001-0000-0000-000000000001",
        "name": "Thịt kho trứng cút",
        "price_vnd": 65000,
        "recipe": [
            {"ingredient_name": "thịt ba rọi", "qty": Decimal("0.2"), "unit": "kg"},
            {"ingredient_name": "trứng gà", "qty": Decimal("2"), "unit": "quả"},
            {"ingredient_name": "hành lá", "qty": Decimal("0.2"), "unit": "bó"}
        ]
    },
    {
        "id": "22222222-0002-0000-0000-000000000002",
        "name": "Bò xào cà chua hành tây",
        "price_vnd": 75000,
        "recipe": [
            {"ingredient_name": "thịt bò thăn", "qty": Decimal("0.18"), "unit": "kg"},
            {"ingredient_name": "cà chua", "qty": Decimal("0.15"), "unit": "kg"},
            {"ingredient_name": "hành lá", "qty": Decimal("0.2"), "unit": "bó"}
        ]
    },
    {
        "id": "22222222-0003-0000-0000-000000000003",
        "name": "Rau muống xào tỏi",
        "price_vnd": 35000,
        "recipe": [
            {"ingredient_name": "rau muống", "qty": Decimal("0.35"), "unit": "kg"}
        ]
    },
    {
        "id": "22222222-0004-0000-0000-000000000004",
        "name": "Cá hồi áp chảo sốt bơ chanh",
        "price_vnd": 125000,
        "recipe": [
            {"ingredient_name": "cá hồi fillet", "qty": Decimal("0.22"), "unit": "kg"}
        ]
    }
]


def seed_database(demo_mode: bool = False, reset: bool = False):
    db = SessionLocal()
    try:
        print("Bắt đầu khởi tạo dữ liệu Database...")

        # 1. Tạo UserProfile
        user = db.get(UserProfile, DEMO_USER_ID)
        if not user:
            user = UserProfile(
                id=DEMO_USER_ID,
                display_name="Bếp Trưởng"
            )
            db.add(user)
            db.flush()
            print("✓ Đã khởi tạo UserProfile mặc định.")

        # 2. Tạo Kitchen
        kitchen = db.get(Kitchen, DEMO_KITCHEN_ID)
        if not kitchen:
            kitchen = Kitchen(
                id=DEMO_KITCHEN_ID,
                owner_user_id=DEMO_USER_ID,
                name="Bếp Chính",
                timezone="Asia/Ho_Chi_Minh"
            )
            db.add(kitchen)
            db.flush()
            print("✓ Đã khởi tạo Kitchen mặc định.")

        # 3. Tạo KitchenSettings
        k_settings = db.get(KitchenSettings, DEMO_KITCHEN_ID)
        if not k_settings:
            k_settings = KitchenSettings(
                kitchen_id=DEMO_KITCHEN_ID,
                expiry_warning_days=3,
                target_coverage_days=3,
                consumption_window_days=14,
                min_history_days=7,
                unusual_quantity_ratio=Decimal("2.0"),
                backdate_limit_days=2,
                expired_batches_consumable=False,
                expired_batch_actions=["WASTE"]
            )
            db.add(k_settings)
            db.flush()
            print("✓ Đã khởi tạo KitchenSettings tham số Revision 6.3.")

        # 4. Tạo Đơn vị chuẩn (Units)
        for u in STANDARD_UNITS:
            existing_u = db.get(Unit, u["code"])
            if not existing_u:
                db.add(Unit(
                    code=u["code"],
                    label_vi=u["label_vi"],
                    dimension=u["dimension"],
                    factor_to_dimension_base=u["factor"]
                ))
        db.flush()
        print(f"✓ Đã nạp {len(STANDARD_UNITS)} đơn vị tính chuẩn.")

        # 5. Tạo Danh mục nguyên liệu (Ingredients)
        ing_map = {}
        for item in STANDARD_INGREDIENTS:
            ing_id = uuid.UUID(item["id"])
            existing_ing = db.get(Ingredient, ing_id)
            if not existing_ing:
                ing = Ingredient(
                    id=ing_id,
                    kitchen_id=DEMO_KITCHEN_ID,
                    name=item["name"],
                    normalized_name=item["name"].lower().strip(),
                    search_name=item["name"].lower().strip(),
                    base_unit_code=item["unit"],
                    default_location=item["location"],
                    tracks_expiry=True,
                    min_stock_qty=item["min_stock"],
                    order_step=item["step"],
                    expiry_warning_days=item["warning_days"]
                )
                db.add(ing)
                ing_map[item["name"]] = ing_id
            else:
                ing_map[item["name"]] = existing_ing.id
        db.flush()
        print(f"✓ Đã nạp {len(STANDARD_INGREDIENTS)} nguyên liệu danh mục.")

        # 6. Tạo Thực đơn & Công thức món (Dishes & Recipes)
        for d in STANDARD_DISHES:
            dish_id = uuid.UUID(d["id"])
            existing_dish = db.get(Dish, dish_id)
            if not existing_dish:
                new_dish = Dish(
                    id=dish_id,
                    kitchen_id=DEMO_KITCHEN_ID,
                    name=d["name"],
                    normalized_name=d["name"].lower().strip(),
                    price_vnd=d["price_vnd"]
                )
                db.add(new_dish)
                db.flush()

                for r in d["recipe"]:
                    mapped_ing_id = ing_map.get(r["ingredient_name"])
                    if mapped_ing_id:
                        db.add(DishRecipeItem(
                            kitchen_id=DEMO_KITCHEN_ID,
                            dish_id=dish_id,
                            ingredient_id=mapped_ing_id,
                            quantity=r["qty"],
                            unit_code=r["unit"]
                        ))
        db.flush()
        print(f"✓ Đã nạp {len(STANDARD_DISHES)} món ăn và định lượng công thức chuẩn.")

        # 7. Nạp dữ liệu lô hàng Demo (nếu chạy với --demo)
        if demo_mode:
            print("Đang nạp dữ liệu đợt hàng và lịch sử demo...")
            today = date.today()
            sample_batches = [
                # Rau muống cận date (hết hạn ngày mai)
                {
                    "id": "bbbbbbbb-0001-0000-0000-000000000001",
                    "ing_name": "rau muống",
                    "qty": Decimal("0.5"),
                    "cost": 20000,
                    "rec": today - timedelta(days=2),
                    "exp": today + timedelta(days=1),
                    "loc": "FRIDGE"
                },
                # Thịt ba rọi (còn hạn dài)
                {
                    "id": "bbbbbbbb-0002-0000-0000-000000000002",
                    "ing_name": "thịt ba rọi",
                    "qty": Decimal("4.0"),
                    "cost": 120000,
                    "rec": today - timedelta(days=1),
                    "exp": today + timedelta(days=14),
                    "loc": "FREEZER"
                },
                # Trứng gà (còn hạn 10 ngày)
                {
                    "id": "bbbbbbbb-0003-0000-0000-000000000003",
                    "ing_name": "trứng gà",
                    "qty": Decimal("30"),
                    "cost": 3500,
                    "rec": today - timedelta(days=3),
                    "exp": today + timedelta(days=10),
                    "loc": "FRIDGE"
                },
                # Cà chua (cận date - hết hạn trong 2 ngày)
                {
                    "id": "bbbbbbbb-0004-0000-0000-000000000004",
                    "ing_name": "cà chua",
                    "qty": Decimal("1.2"),
                    "cost": 35000,
                    "rec": today - timedelta(days=4),
                    "exp": today + timedelta(days=2),
                    "loc": "FRIDGE"
                },
                # Hành lá (hết hạn hôm nay)
                {
                    "id": "bbbbbbbb-0005-0000-0000-000000000005",
                    "ing_name": "hành lá",
                    "qty": Decimal("1.0"),
                    "cost": 8000,
                    "rec": today - timedelta(days=3),
                    "exp": today,
                    "loc": "FRIDGE"
                }
            ]

            for b in sample_batches:
                b_uuid = uuid.UUID(b["id"])
                if not db.get(Batch, b_uuid):
                    ing_id = ing_map.get(b["ing_name"])
                    if ing_id:
                        db.add(Batch(
                            id=b_uuid,
                            kitchen_id=DEMO_KITCHEN_ID,
                            ingredient_id=ing_id,
                            initial_qty=b["qty"],
                            remaining_qty=b["qty"],
                            unit_cost=Decimal(str(b["cost"])),
                            received_on=b["rec"],
                            expiry_date=b["exp"],
                            location=b["loc"]
                        ))
            db.flush()
            print(f"✓ Đã nạp {len(sample_batches)} lô hàng demo (gồm các lô cận date phục vụ thử nghiệm AI).")

        db.commit()
        print("Hoàn tất nạp dữ liệu Database thành công!")
    except Exception as e:
        db.rollback()
        print(f"Lỗi khi nạp dữ liệu database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Khởi tạo dữ liệu cơ sở dữ liệu Trợ lý kho bếp")
    parser.add_argument("--demo", action="store_true", help="Nạp thêm các lô hàng mẫu phục vụ demo")
    parser.add_argument("--clean", action="store_true", help="Chỉ nạp danh mục và thiết lập ban đầu")
    parser.add_argument("--reset", action="store_true", help="Reset dữ liệu")
    args = parser.parse_args()

    seed_database(demo_mode=args.demo or not args.clean)
