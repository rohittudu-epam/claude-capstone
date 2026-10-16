"""Request authentication shared by every service.

Services verify the JWT signature locally and consult the shared revoked_tokens table,
so a revoked token is rejected everywhere without a round trip to auth-service.
"""

from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from shared.db import get_db
from shared.models import RevokedToken
from shared.security import ACCESS, InvalidTokenError, decode_token

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"


def bearer_token(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    scheme, _, value = header.partition(" ")
    return value.strip() if scheme.lower() == "bearer" and value.strip() else None


def request_access_token(request: Request) -> str | None:
    return request.cookies.get(ACCESS_COOKIE) or bearer_token(request)


def is_revoked(db: Session, jti: str) -> bool:
    return db.scalar(select(RevokedToken.id).where(RevokedToken.token_jti == jti)) is not None


def unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user_id(request: Request, db: Session = Depends(get_db)) -> UUID:
    token = request_access_token(request)
    if token is None:
        raise unauthorized()
    try:
        claims = decode_token(token, ACCESS)
    except InvalidTokenError:
        raise unauthorized() from None
    if is_revoked(db, claims.jti):
        raise unauthorized()
    return claims.user_id
