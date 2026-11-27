from app.database import SessionLocal
from app.modules.assistant.knowledge import reindex
from app.modules.menu.repository import SqlAlchemyMenuRepository

if __name__ == "__main__":
    with SessionLocal() as db:
        count = reindex(SqlAlchemyMenuRepository(db).list_all())
    print(f"Проиндексировано документов: {count}")
