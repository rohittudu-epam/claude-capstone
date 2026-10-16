"""Password hashing and JWT helpers."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from uuid import UUID, uuid4

import bcrypt
import jwt

from shared.config import get_settings
from shared.timeutil import utcnow

ACCESS = "access"
REFRESH = "refresh"
MAX_PASSWORD_BYTES = 72  # bcrypt ignores (or rejects) anything longer


class InvalidTokenError(Exception):
    pass


@dataclass(frozen=True)
class TokenClaims:
    user_id: UUID
    jti: str
    token_type: str
    expires_at: datetime  # naive UTC


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=get_settings().bcrypt_rounds)
    return bcrypt.hashpw(password.encode(), salt).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


@lru_cache
def _dummy_hash() -> str:
    return hash_password("timing-equalisation-placeholder")


def burn_password_check(password: str) -> None:
    """Spend the same time as a real check so unknown emails are not distinguishable by latency."""
    verify_password(password, _dummy_hash())


def create_token(user_id: UUID, token_type: str) -> tuple[str, TokenClaims]:
    settings = get_settings()
    lifetime = (
        timedelta(minutes=settings.access_token_expire_minutes)
        if token_type == ACCESS
        else timedelta(days=settings.refresh_token_expire_days)
    )
    now = datetime.now(UTC)
    expires = now + lifetime
    jti = uuid4().hex
    token = jwt.encode(
        {
            "sub": str(user_id),
            "jti": jti,
            "type": token_type,
            "iat": int(now.timestamp()),
            "exp": int(expires.timestamp()),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    claims = TokenClaims(user_id, jti, token_type, expires.replace(tzinfo=None, microsecond=0))
    return token, claims


def decode_token(token: str, expected_type: str | None = None) -> TokenClaims:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "iat", "sub", "jti", "type"]},
        )
        claims = TokenClaims(
            user_id=UUID(payload["sub"]),
            jti=str(payload["jti"]),
            token_type=str(payload["type"]),
            expires_at=datetime.fromtimestamp(payload["exp"], UTC).replace(tzinfo=None),
        )
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise InvalidTokenError("invalid token") from exc
    if expected_type is not None and claims.token_type != expected_type:
        raise InvalidTokenError("wrong token type")
    return claims


def seconds_until(expires_at: datetime) -> int:
    return max(0, int((expires_at - utcnow()).total_seconds()))
