import time
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from auth_service.main import app
from shared.config import get_settings
from shared.models import RevokedToken, User
from shared.security import ACCESS, REFRESH, decode_token

EMAIL = "Alice@Example.com"
PASSWORD = "correct horse battery"


@pytest.fixture
def client(session_factory) -> TestClient:
    return TestClient(app)


@pytest.fixture
def registered(client) -> dict:
    response = client.post("/api/auth/register", json={"email": EMAIL, "password": PASSWORD})
    assert response.status_code == 201
    return response.json()


def login(client, email=EMAIL, password=PASSWORD):
    return client.post("/api/auth/login", json={"email": email, "password": password})


class TestRegister:
    def test_creates_user_without_exposing_password(self, client, session_factory):
        response = client.post("/api/auth/register", json={"email": EMAIL, "password": PASSWORD})
        assert response.status_code == 201
        body = response.json()
        assert body["email"] == "alice@example.com"
        assert set(body) == {"id", "email", "created_at"}
        assert PASSWORD not in response.text
        with session_factory() as db:
            user = db.scalar(select(User))
            assert user.password_hash.startswith("$2b$04$")
            assert PASSWORD not in user.password_hash

    def test_duplicate_email_rejected_case_insensitively(self, client, registered):
        response = client.post("/api/auth/register", json={"email": EMAIL.upper(), "password": PASSWORD})
        assert response.status_code == 409

    @pytest.mark.parametrize(
        "payload",
        [
            {"email": "not-an-email", "password": PASSWORD},
            {"email": EMAIL, "password": "short"},
            {"email": EMAIL, "password": "x" * 73},
            {"email": EMAIL, "password": "é" * 40},  # 80 bytes
            {"email": EMAIL},
            {"email": EMAIL, "password": PASSWORD, "is_admin": True},
        ],
    )
    def test_invalid_payload_returns_400_without_echoing_input(self, client, payload):
        response = client.post("/api/auth/register", json=payload)
        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid request"
        assert PASSWORD not in response.text


class TestLogin:
    def test_sets_httponly_cookies_and_returns_no_tokens(self, client, registered):
        response = login(client)
        assert response.status_code == 200
        assert response.json() == {"user_id": registered["id"], "expires_in": pytest.approx(900, abs=5)}
        set_cookie = response.headers.get_list("set-cookie")
        assert len(set_cookie) == 2
        for header in set_cookie:
            assert "HttpOnly" in header and "SameSite=lax" in header
        assert any(h.startswith("access_token=") and "Path=/;" in h for h in set_cookie)
        assert any(h.startswith("refresh_token=") and "Path=/api/auth" in h for h in set_cookie)
        assert "access_token" not in response.text and "eyJ" not in response.text

    def test_token_claims_and_lifetimes(self, client, registered):
        login(client)
        access = decode_token(client.cookies.get("access_token"), ACCESS)
        assert str(access.user_id) == registered["id"]
        assert (
            timedelta(minutes=14) < access.expires_at - datetime.now(UTC).replace(tzinfo=None) <= timedelta(minutes=15)
        )
        raw_refresh = client.cookies.get("refresh_token", path="/api/auth")
        refresh = decode_token(raw_refresh, REFRESH)
        assert (
            timedelta(days=6, hours=23)
            < refresh.expires_at - datetime.now(UTC).replace(tzinfo=None)
            <= timedelta(days=7)
        )

    def test_wrong_password_and_unknown_email_are_indistinguishable(self, client, registered):
        wrong = login(client, password="wrong password!")
        unknown = login(client, email="nobody@example.com")
        assert wrong.status_code == unknown.status_code == 401
        assert wrong.json()["detail"] == unknown.json()["detail"] == "Authentication failed"
        assert set(wrong.json()) == set(unknown.json()) == {"detail", "correlation_id"}
        assert "set-cookie" not in wrong.headers

    def test_email_is_case_insensitive(self, client, registered):
        assert login(client, email="ALICE@example.COM").status_code == 200


class TestRefresh:
    def test_rotates_and_rejects_reuse_of_old_refresh_token(self, client, registered):
        login(client)
        old_refresh = client.cookies.get("refresh_token", path="/api/auth")
        old_access = client.cookies.get("access_token")

        response = client.post("/api/auth/refresh")
        assert response.status_code == 200
        new_refresh = client.cookies.get("refresh_token", path="/api/auth")
        assert new_refresh != old_refresh
        assert client.cookies.get("access_token") != old_access

        replay = TestClient(app)
        replay.cookies.set("refresh_token", old_refresh, path="/api/auth")
        assert replay.post("/api/auth/refresh").status_code == 401
        assert client.post("/api/auth/refresh").status_code == 200  # the rotated token still works

    def test_requires_a_refresh_token(self, client, registered):
        assert client.post("/api/auth/refresh").status_code == 401

    def test_access_token_cannot_be_used_to_refresh(self, client, registered):
        login(client)
        access = client.cookies.get("access_token")
        other = TestClient(app)
        other.cookies.set("refresh_token", access, path="/api/auth")
        assert other.post("/api/auth/refresh").status_code == 401

    def test_expired_refresh_token_rejected(self, client, registered):
        login(client)
        expired = jwt.encode(
            {
                "sub": registered["id"],
                "jti": uuid4().hex,
                "type": REFRESH,
                "iat": int(time.time()) - 100,
                "exp": int(time.time()) - 10,
            },
            get_settings().jwt_secret_key,
            algorithm="HS256",
        )
        other = TestClient(app)
        other.cookies.set("refresh_token", expired, path="/api/auth")
        assert other.post("/api/auth/refresh").status_code == 401


class TestVerifyAndLogout:
    def test_verify_accepts_valid_token_via_query_and_bearer(self, client, registered):
        login(client)
        token = client.cookies.get("access_token")
        by_query = client.get("/api/auth/verify", params={"token": token})
        assert by_query.status_code == 200
        assert by_query.json()["user_id"] == registered["id"]
        assert by_query.json()["token_type"] == "access"
        assert client.get("/api/auth/verify", headers={"Authorization": f"Bearer {token}"}).status_code == 200

    @pytest.mark.parametrize("token", ["garbage", "a.b.c", ""])
    def test_verify_rejects_invalid_tokens(self, client, token):
        assert client.get("/api/auth/verify", params={"token": token}).status_code == 401

    def test_verify_rejects_expired_token(self, client, registered):
        expired = jwt.encode(
            {
                "sub": registered["id"],
                "jti": uuid4().hex,
                "type": ACCESS,
                "iat": int(time.time()) - 100,
                "exp": int(time.time()) - 10,
            },
            get_settings().jwt_secret_key,
            algorithm="HS256",
        )
        assert client.get("/api/auth/verify", params={"token": expired}).status_code == 401

    def test_verify_rejects_token_signed_with_another_key(self, client, registered):
        forged = jwt.encode(
            {
                "sub": registered["id"],
                "jti": uuid4().hex,
                "type": ACCESS,
                "iat": int(time.time()),
                "exp": int(time.time()) + 600,
            },
            "another-secret-another-secret-another-secret",
            algorithm="HS256",
        )
        assert client.get("/api/auth/verify", params={"token": forged}).status_code == 401

    def test_logout_revokes_both_tokens(self, client, registered, session_factory):
        login(client)
        access = client.cookies.get("access_token")
        refresh = client.cookies.get("refresh_token", path="/api/auth")

        response = client.post("/api/auth/logout")
        assert response.status_code == 204

        assert client.get("/api/auth/verify", params={"token": access}).status_code == 401
        other = TestClient(app)
        other.cookies.set("refresh_token", refresh, path="/api/auth")
        assert other.post("/api/auth/refresh").status_code == 401
        with session_factory() as db:
            assert len(db.scalars(select(RevokedToken)).all()) == 2

    def test_logout_without_session_is_a_no_op(self, client):
        assert client.post("/api/auth/logout").status_code == 204

    def test_logout_twice_is_idempotent(self, client, registered):
        login(client)
        assert client.post("/api/auth/logout").status_code == 204
        replay = TestClient(app)
        assert replay.post("/api/auth/logout").status_code == 204


class TestHealth:
    def test_health_and_ready(self, client):
        assert client.get("/health").json() == {"status": "ok", "service": "auth-service"}
        ready = client.get("/ready")
        assert ready.status_code == 200
        assert ready.json()["checks"] == {"database": "ok"}
