"""
Кеш меню (ЛР № 4): Cache-Aside в SqlAlchemyMenuRepository поверх SQLite,
Redis подменён fakeredis.
"""
import json
import time
from concurrent.futures import ThreadPoolExecutor

import fakeredis
import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from app.domain.entities import MenuItem
from app.modules.menu.repository import MENU_CACHE_KEY, MENU_CACHE_TTL, SqlAlchemyMenuRepository
from app.modules.menu.service import MenuService


@pytest.fixture
def cache():
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def repo(sqlite_session, cache):
    return SqlAlchemyMenuRepository(sqlite_session, cache=cache)


def count_queries(session):
    """Считает SQL-запросы, ушедшие в БД."""
    from sqlalchemy import event

    calls = []
    event.listen(session.get_bind(), "before_cursor_execute", lambda *a: calls.append(a[2]))
    return calls


def test_miss_loads_from_db_and_fills_cache_with_ttl(repo, cache):
    repo.add(MenuItem(id=None, name="Борщ", price=150))

    items = repo.list_all()

    assert [i.name for i in items] == ["Борщ"]
    assert json.loads(cache.get(MENU_CACHE_KEY))[0]["name"] == "Борщ"
    assert 0 < cache.ttl(MENU_CACHE_KEY) <= MENU_CACHE_TTL


def test_hit_does_not_query_db(repo, sqlite_session):
    repo.add(MenuItem(id=None, name="Борщ", price=150))
    repo.list_all()  # miss: кеш заполнен
    queries = count_queries(sqlite_session)

    items = repo.list_all()  # hit

    assert [i.name for i in items] == ["Борщ"]
    assert queries == []


def test_create_and_update_invalidate_cache(repo):
    service = MenuService(repo)
    item = service.create_item("Борщ", 150)
    assert [i.name for i in service.list_items()] == ["Борщ"]  # кеш заполнен

    service.create_item("Плов", 200)
    assert [i.name for i in service.list_items()] == ["Борщ", "Плов"]

    service.update_item(item.id, price=170)
    assert service.list_items()[0].price == 170


def test_warm_up_fills_cache(repo, cache):
    repo.add(MenuItem(id=None, name="Борщ", price=150))

    repo.warm_up()

    assert cache.exists(MENU_CACHE_KEY)


def test_redis_down_falls_back_to_db(sqlite_session):
    class DownRedis:
        """Упавший Redis: любая команда — ConnectionError."""

        def __getattr__(self, name):
            def fail(*args, **kwargs):
                raise RedisConnectionError("Redis недоступен")

            return fail

    repo = SqlAlchemyMenuRepository(sqlite_session, cache=DownRedis())
    repo.add(MenuItem(id=None, name="Борщ", price=150))

    assert [i.name for i in repo.list_all()] == ["Борщ"]
    repo.invalidate_cache()  # не падает


def test_stampede_only_one_request_goes_to_db(cache):
    """10 параллельных запросов при пустом кеше: в БД идёт только один."""
    loads = []

    def slow_load():
        loads.append(1)
        time.sleep(0.3)  # «тяжёлый» запрос к БД
        return [MenuItem(id=1, name="Борщ", price=150)]

    def request():
        repo = SqlAlchemyMenuRepository(db=None, cache=cache)
        repo._load_all = slow_load
        return repo.list_all()

    with ThreadPoolExecutor(10) as pool:
        results = list(pool.map(lambda _: request(), range(10)))

    assert len(loads) == 1
    assert all(r[0].name == "Борщ" for r in results)
