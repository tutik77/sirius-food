from functools import lru_cache

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.redis import redis_client
from app.database import SessionLocal, get_db
from app.memory_storage import InMemoryStorage
from app.modules.assistant.knowledge import qdrant_knowledge_base
from app.modules.assistant.langgraph_agent import LangGraphAssistantAgent
from app.modules.assistant.llm import chat_model
from app.modules.assistant.repository import (
    AssistantMessageRepository,
    InMemoryAssistantMessageRepository,
    SqlAlchemyAssistantMessageRepository,
)
from app.modules.assistant.service import AssistantService
from app.modules.assistant.tools import AssistantContext
from app.modules.auth.repository import AuthRepository, InMemoryAuthRepository, SqlAlchemyAuthRepository
from app.modules.auth.service import AuthService
from app.modules.delivery.gateway import DeliveryGateway
from app.modules.delivery.grpc_client import DeliveryGrpcClient
from app.modules.loyalty.repository import InMemoryLoyaltyRepository, LoyaltyRepository, SqlAlchemyLoyaltyRepository
from app.modules.loyalty.service import LoyaltyService
from app.modules.menu.repository import InMemoryMenuRepository, MenuRepository, SqlAlchemyMenuRepository
from app.modules.menu.service import MenuService
from app.modules.orders.repository import InMemoryOrderRepository, OrderRepository, SqlAlchemyOrderRepository
from app.modules.orders.service import OrderService
from app.modules.promo.repository import InMemoryPromoRepository, PromoRepository, SqlAlchemyPromoRepository
from app.modules.promo.service import PromoService
from app.modules.users.repository import InMemoryUserRepository, SqlAlchemyUserRepository, UserRepository
from app.modules.users.service import UserService

memory_storage = InMemoryStorage()


def get_session():
    if settings.STORAGE_BACKEND == "memory":
        yield None
    else:
        yield from get_db()


def get_auth_repository(db: Session | None = Depends(get_session)) -> AuthRepository:
    if settings.STORAGE_BACKEND == "memory":
        return InMemoryAuthRepository(memory_storage)
    return SqlAlchemyAuthRepository(db)


def get_auth_service(repository: AuthRepository = Depends(get_auth_repository)) -> AuthService:
    return AuthService(repository)


def get_user_repository(db: Session | None = Depends(get_session)) -> UserRepository:
    if settings.STORAGE_BACKEND == "memory":
        return InMemoryUserRepository(memory_storage)
    return SqlAlchemyUserRepository(db)


def get_user_service(repository: UserRepository = Depends(get_user_repository)) -> UserService:
    return UserService(repository)


def get_menu_repository(db: Session | None = Depends(get_session)) -> MenuRepository:
    if settings.STORAGE_BACKEND == "memory":
        return InMemoryMenuRepository(memory_storage)
    return SqlAlchemyMenuRepository(db, cache=redis_client)


def warm_up_menu_cache() -> None:
    if settings.STORAGE_BACKEND == "memory":
        return
    with SessionLocal() as db:
        SqlAlchemyMenuRepository(db, cache=redis_client).warm_up()


def get_menu_service(repository: MenuRepository = Depends(get_menu_repository)) -> MenuService:
    return MenuService(repository)


def get_order_repository(db: Session | None = Depends(get_session)) -> OrderRepository:
    if settings.STORAGE_BACKEND == "memory":
        return InMemoryOrderRepository(memory_storage)
    return SqlAlchemyOrderRepository(db)


def get_promo_repository(db: Session | None = Depends(get_session)) -> PromoRepository:
    if settings.STORAGE_BACKEND == "memory":
        return InMemoryPromoRepository(memory_storage)
    return SqlAlchemyPromoRepository(db)


def get_promo_service(repository: PromoRepository = Depends(get_promo_repository)) -> PromoService:
    return PromoService(repository)


def get_loyalty_repository(db: Session | None = Depends(get_session)) -> LoyaltyRepository:
    if settings.STORAGE_BACKEND == "memory":
        return InMemoryLoyaltyRepository(memory_storage)
    return SqlAlchemyLoyaltyRepository(db)


def get_loyalty_service(repository: LoyaltyRepository = Depends(get_loyalty_repository)) -> LoyaltyService:
    return LoyaltyService(repository)


def get_order_service(
    repository: OrderRepository = Depends(get_order_repository),
    promo: PromoService = Depends(get_promo_service),
    loyalty: LoyaltyService = Depends(get_loyalty_service),
) -> OrderService:
    return OrderService(repository, promo, loyalty)


@lru_cache
def delivery_client(address: str) -> DeliveryGrpcClient:
    return DeliveryGrpcClient(address)


def get_delivery_gateway() -> DeliveryGateway:
    return delivery_client(settings.DELIVERY_GRPC_ADDR)


def get_assistant_repository(db: Session | None = Depends(get_session)) -> AssistantMessageRepository:
    if settings.STORAGE_BACKEND == "memory":
        return InMemoryAssistantMessageRepository(memory_storage)
    return SqlAlchemyAssistantMessageRepository(db)


def get_assistant_context(
    orders: OrderService = Depends(get_order_service),
    menu: MenuService = Depends(get_menu_service),
    loyalty: LoyaltyService = Depends(get_loyalty_service),
    promo: PromoService = Depends(get_promo_service),
) -> AssistantContext:
    return AssistantContext(knowledge=qdrant_knowledge_base, orders=orders, menu=menu, loyalty=loyalty, promo=promo)


def get_assistant_service(
    context: AssistantContext = Depends(get_assistant_context),
    repository: AssistantMessageRepository = Depends(get_assistant_repository),
) -> AssistantService:
    return AssistantService(LangGraphAssistantAgent(chat_model, context), repository)
