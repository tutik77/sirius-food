from app import models
from app.database import SessionLocal

DISHES = [
    ("Сырники со сметаной", 150),
    ("Борщ с пампушками", 250),
    ("Плов с бараниной", 290),
    ("Цезарь с курицей", 320),
    ("Паста карбонара", 340),
    ("Пельмени домашние", 260),
    ("Блины с ягодами", 180),
    ("Капучино", 140),
]


def seed() -> None:
    with SessionLocal() as db:
        existing = {name for (name,) in db.query(models.MenuItem.name)}
        added = [models.MenuItem(name=name, price=price, is_available=True) for name, price in DISHES if name not in existing]
        db.add_all(added)
        db.commit()
        print(f"Добавлено блюд: {len(added)}")


if __name__ == "__main__":
    seed()
