"""
Создание и проверка JWT.

Access-токен живёт 15 минут: если его украдут, он быстро сгорит.
Refresh-токен живёт 7 дней и нужен только для получения новой пары токенов.
В payload лежат только идентификатор пользователя и служебные поля:
payload не шифруется, его может прочитать кто угодно.
"""
import uuid
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt

from app.core.config import settings

ALGORITHM = "HS256"
ACCESS = "access"
REFRESH = "refresh"


class TokenError(Exception):
    """Токен повреждён, подделан, просрочен или другого типа."""


def _create_token(user_id: int, token_type: str, lifetime: timedelta) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": token_type,
        "iat": now,
        "exp": now + lifetime,
        # Уникальный id: два токена, выданные в одну секунду, всё равно различаются.
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(user_id: int) -> str:
    """Короткоживущий access-токен."""
    return _create_token(user_id, ACCESS, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))


def create_refresh_token(user_id: int) -> str:
    """Долгоживущий refresh-токен."""
    return _create_token(user_id, REFRESH, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))


def refresh_token_expires_at() -> datetime:
    """Момент истечения нового refresh-токена (naive UTC, как хранится в БД)."""
    return datetime.now(UTC).replace(tzinfo=None) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)


def decode_token(token: str, expected_type: str) -> int:
    """
    Проверяет подпись, срок действия и тип токена, возвращает id пользователя.
    Явно задан список алгоритмов: токен с alg=none или чужим алгоритмом не пройдёт.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != expected_type:
            raise TokenError("Неверный тип токена")
        return int(payload["sub"])
    except (JWTError, KeyError, ValueError) as e:
        raise TokenError(str(e)) from e
