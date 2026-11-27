from app.core.jwt import (
    REFRESH,
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    refresh_token_expires_at,
)
from app.core.security import DUMMY_PASSWORD_HASH, hash_token, verify_password
from app.domain.entities import RefreshToken
from app.modules.auth.exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    TokenReuseError,
    UserBlockedError,
)
from app.modules.auth.repository import AuthRepository


class AuthService:
    def __init__(self, repository: AuthRepository):
        self.repository = repository

    def login(self, email: str, password: str) -> dict:
        user = self.repository.get_user_by_email(email)
        if user is None:
            verify_password(password, DUMMY_PASSWORD_HASH)
            raise InvalidCredentialsError()
        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsError()
        if user.is_blocked:
            raise UserBlockedError()

        return self._issue_tokens(user.id)

    def refresh(self, refresh_token: str) -> dict:
        try:
            user_id = decode_token(refresh_token, REFRESH)
        except TokenError as e:
            raise InvalidTokenError() from e

        token_hash = hash_token(refresh_token)
        record = self.repository.get_refresh_token(token_hash)
        if record is None or record.user_id != user_id:
            raise InvalidTokenError()

        if not self.repository.revoke_if_active(token_hash):
            self.repository.revoke_all_for_user(user_id)
            raise TokenReuseError()

        user = self.repository.get_user_by_id(user_id)
        if user is None:
            raise InvalidTokenError()
        if user.is_blocked:
            raise UserBlockedError()

        return self._issue_tokens(user.id)

    def logout(self, refresh_token: str) -> None:
        self.repository.revoke_if_active(hash_token(refresh_token))

    def _issue_tokens(self, user_id: int) -> dict:
        access_token = create_access_token(user_id)
        refresh_token = create_refresh_token(user_id)
        self.repository.add_refresh_token(
            RefreshToken(
                id=None,
                user_id=user_id,
                token_hash=hash_token(refresh_token),
                expires_at=refresh_token_expires_at(),
            )
        )
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }
