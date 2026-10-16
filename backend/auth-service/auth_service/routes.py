import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from auth_service.schemas import LoginRequest, RegisterRequest, SessionOut, UserOut
from shared.auth import ACCESS_COOKIE, REFRESH_COOKIE, bearer_token, is_revoked
from shared.config import get_settings
from shared.db import get_db
from shared.models import RevokedToken, User
from shared.security import (
    ACCESS,
    REFRESH,
    InvalidTokenError,
    TokenClaims,
    burn_password_check,
    create_token,
    decode_token,
    hash_password,
    seconds_until,
    verify_password,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])

AUTH_FAILED = "Authentication failed"
REFRESH_COOKIE_PATH = "/api/auth"


def _set_session_cookies(response: Response, user_id: UUID) -> SessionOut:
    settings = get_settings()
    access, access_claims = create_token(user_id, ACCESS)
    refresh, refresh_claims = create_token(user_id, REFRESH)

    def set_cookie(name: str, value: str, expires_at: datetime, path: str) -> None:
        response.set_cookie(
            name,
            value,
            max_age=seconds_until(expires_at),
            path=path,
            httponly=True,
            secure=settings.cookie_secure,
            samesite="lax",
        )

    set_cookie(ACCESS_COOKIE, access, access_claims.expires_at, "/")
    set_cookie(REFRESH_COOKIE, refresh, refresh_claims.expires_at, REFRESH_COOKIE_PATH)
    return SessionOut(user_id=user_id, expires_in=seconds_until(access_claims.expires_at))


def _clear_session_cookies(response: Response) -> None:
    secure = get_settings().cookie_secure
    response.delete_cookie(ACCESS_COOKIE, path="/", httponly=True, secure=secure, samesite="lax")
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH, httponly=True, secure=secure, samesite="lax")


def _revoke(db: Session, claims: TokenClaims) -> None:
    db.execute(
        pg_insert(RevokedToken)
        .values(user_id=claims.user_id, token_jti=claims.jti, expires_at=claims.expires_at)
        .on_conflict_do_nothing(index_elements=["token_jti"])
    )


def _auth_error() -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, AUTH_FAILED)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> User:
    if db.scalar(select(User.id).where(User.email == payload.email)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = User(email=payload.email, password_hash=hash_password(payload.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered") from None
    logger.info("user registered", extra={"user_id": str(user.id)})
    return user


@router.post("/login", response_model=SessionOut)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> SessionOut:
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None:
        burn_password_check(payload.password)
        raise _auth_error()
    if not verify_password(payload.password, user.password_hash):
        raise _auth_error()
    return _set_session_cookies(response, user.id)


@router.post("/refresh", response_model=SessionOut)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)) -> SessionOut:
    token = request.cookies.get(REFRESH_COOKIE)
    try:
        if token is None:
            raise InvalidTokenError("missing")
        claims = decode_token(token, REFRESH)
        if is_revoked(db, claims.jti):
            raise InvalidTokenError("revoked")
        # Rotation: the presented refresh token is spent. The unique jti makes concurrent reuse fail.
        db.add(RevokedToken(user_id=claims.user_id, token_jti=claims.jti, expires_at=claims.expires_at))
        db.commit()
    except InvalidTokenError, IntegrityError:
        db.rollback()
        _clear_session_cookies(response)
        raise _auth_error() from None
    return _set_session_cookies(response, claims.user_id)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, db: Session = Depends(get_db)) -> Response:
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    candidates = [
        (request.cookies.get(ACCESS_COOKIE) or bearer_token(request), ACCESS),
        (request.cookies.get(REFRESH_COOKIE), REFRESH),
    ]
    for token, token_type in candidates:
        if token is None:
            continue
        try:
            _revoke(db, decode_token(token, token_type))
        except InvalidTokenError:
            continue  # unusable already (expired, forged, wrong type): nothing to revoke
    db.commit()
    _clear_session_cookies(response)
    return response


@router.get("/verify")
def verify(
    request: Request,
    token: str | None = Query(default=None, max_length=4096),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    raw = token or bearer_token(request)
    try:
        if raw is None:
            raise InvalidTokenError("missing")
        claims = decode_token(raw)
        if is_revoked(db, claims.jti):
            raise InvalidTokenError("revoked")
    except InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or revoked token") from None
    return {
        "user_id": str(claims.user_id),
        "token_type": claims.token_type,
        "expires_at": claims.expires_at.isoformat() + "Z",
    }
