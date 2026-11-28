import sentry_sdk

from app.core.config import settings


def setup_sentry(service: str) -> None:
    if not settings.SENTRY_DSN:
        return
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        server_name=service,
        environment="dev" if settings.DEBUG else "prod",
    )
