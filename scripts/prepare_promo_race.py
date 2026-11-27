import sys
from datetime import datetime, timedelta

from sqlalchemy import text

from app.core.security import hash_password
from app.database import SessionLocal

STUDENTS = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
FIRST_ID = 1000


def prepare() -> None:
    now = datetime.utcnow()
    password_hash = hash_password("RacePass123")
    with SessionLocal() as db:
        student_role = db.execute(text("SELECT id FROM roles WHERE name = 'student'")).scalar_one()
        db.execute(
            text(
                "INSERT INTO users (id, email, balance, is_blocked, password_hash, role_id) "
                "SELECT g, 'race' || g || '@sirius.ru', 1000, false, :hash, :role "
                "FROM generate_series(:first, :last) g ON CONFLICT (id) DO NOTHING"
            ),
            {"hash": password_hash, "role": student_role, "first": FIRST_ID, "last": FIRST_ID + STUDENTS - 1},
        )
        db.execute(text("DELETE FROM promo_code_usages WHERE promo_code_id IN (SELECT id FROM promo_codes WHERE code = 'RACE1')"))
        db.execute(text("DELETE FROM promo_codes WHERE code = 'RACE1' AND NOT EXISTS (SELECT 1 FROM orders o WHERE o.promo_code_id = promo_codes.id)"))
        db.execute(
            text(
                "INSERT INTO promo_codes (code, discount_type, discount_value, valid_from, valid_until, max_uses, "
                "current_uses, min_order_amount, is_active) "
                "VALUES ('RACE1', 'percent', 50, :start, :end, 1, 0, 0, true) "
                "ON CONFLICT (code) DO UPDATE SET current_uses = 0, max_uses = 1, is_active = true"
            ),
            {"start": now - timedelta(days=1), "end": now + timedelta(days=1)},
        )
        db.commit()
    print(f"Студенты {FIRST_ID}..{FIRST_ID + STUDENTS - 1}, промокод RACE1 (max_uses=1)")


if __name__ == "__main__":
    prepare()
