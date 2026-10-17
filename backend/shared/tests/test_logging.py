import io
import json
import logging
import threading
import time

import fakeredis
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from auth_service.main import app as auth_app
from link_service.consumer import NoteEventConsumer
from note_service.main import app as note_app
from note_service.publisher import OutboxPublisher
from shared.config import get_settings
from shared.events import STREAM_NOTE_EVENTS
from shared.heartbeat import touch_heartbeat
from shared.jsonlog import REDACTED, JsonFormatter, correlation_context, current_correlation_id, valid_correlation_id
from shared.models import OutboxEntry
from shared.observability import init_service

PASSWORD = "correct horse battery"


@pytest.fixture
def logs():
    """Captures everything logged (DEBUG and up) as parsed JSON lines, whichever service logged it."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter("test"))
    # The test client's own request logging (it prints the URL it called) is not what the services emit.
    handler.addFilter(lambda record: not record.name.startswith(("httpx", "httpcore")))
    root = logging.getLogger()
    previous = root.level
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)

    class Captured:
        @property
        def raw(self) -> str:
            return stream.getvalue()

        @property
        def lines(self) -> list[dict]:
            return [json.loads(line) for line in self.raw.splitlines() if line.strip()]

    yield Captured()
    root.removeHandler(handler)
    root.setLevel(previous)


def emit(**extra) -> dict:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter("svc"))
    logger = logging.getLogger("unit")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    try:
        logger.info("hello %s", "world", extra=extra)
    finally:
        logger.removeHandler(handler)
    return json.loads(stream.getvalue())


class TestFormatter:
    def test_emits_one_json_object_with_the_standard_fields(self):
        entry = emit(user_id="u1")
        assert entry["message"] == "hello world" and entry["service"] == "svc" and entry["level"] == "INFO"
        assert entry["logger"] == "unit" and entry["user_id"] == "u1" and entry["correlation_id"] is None
        assert entry["timestamp"].endswith("+00:00")

    @pytest.mark.parametrize(
        "key",
        [
            "password",
            "new_password",
            "access_token",
            "refreshToken",
            "Authorization",
            "cookie",
            "jwt_secret",
            "body",
            "note_content",
        ],
    )
    def test_secret_looking_fields_are_redacted(self, key):
        raw_value = "super-secret-value-123"
        entry = emit(**{key: raw_value})
        assert entry[key] == REDACTED and raw_value not in json.dumps(entry)

    def test_sqlalchemy_errors_never_leak_bound_parameters(self, logs):
        params = {
            "email": "victim@example.com",
            "password_hash": "$2b$12$abcdefghijklmnopqrstuv",
            "body": "private text",
        }
        try:
            raise IntegrityError("INSERT INTO users VALUES (%(email)s)", params, Exception("duplicate key"))
        except IntegrityError:
            logging.getLogger("unit").exception("write failed")
        assert "victim@example.com" not in logs.raw and "$2b$12$" not in logs.raw and "private text" not in logs.raw
        exception = logs.lines[0]["exception"]
        assert exception["type"].endswith("IntegrityError") and "message" not in exception and exception["frames"]

    def test_other_exceptions_keep_their_message_for_debugging(self, logs):
        try:
            raise ValueError("configuration value out of range")
        except ValueError:
            logging.getLogger("unit").exception("bad config")
        assert logs.lines[0]["exception"]["message"] == "configuration value out of range"


class TestCorrelationContext:
    def test_binds_and_restores(self):
        assert current_correlation_id() is None
        with correlation_context("trace-1") as cid:
            assert cid == current_correlation_id() == "trace-1"
            with correlation_context("trace-2"):
                assert current_correlation_id() == "trace-2"
            assert current_correlation_id() == "trace-1"
        assert current_correlation_id() is None

    @pytest.mark.parametrize("value", [None, "", "has space", "x" * 65, "semi;colon", "new\nline"])
    def test_invalid_ids_are_replaced(self, value):
        assert valid_correlation_id(value) is None
        with correlation_context(value) as cid:
            assert len(cid) == 32


class TestRequestLogging:
    def test_echoes_a_valid_incoming_id_and_generates_one_otherwise(self, session_factory, logs):
        client = TestClient(auth_app)
        echoed = client.get("/health", headers={"X-Correlation-ID": "trace.abc-123"})
        assert echoed.headers["x-correlation-id"] == "trace.abc-123"
        generated = client.get("/health")
        assert len(generated.headers["x-correlation-id"]) == 32
        replaced = client.get("/health", headers={"X-Correlation-ID": "bad id!"})
        assert replaced.headers["x-correlation-id"] != "bad id!"

    def test_logs_one_line_per_request_without_query_string_or_headers(self, session_factory, logs):
        client = TestClient(auth_app)
        response = client.get(
            "/api/auth/verify", params={"token": "SECRET-TOKEN-VALUE"}, headers={"X-Correlation-ID": "t1"}
        )
        assert response.status_code == 401
        assert "SECRET-TOKEN-VALUE" not in logs.raw
        (line,) = [entry for entry in logs.lines if entry["message"] == "request completed"]
        assert (line["method"], line["path"], line["status"], line["correlation_id"]) == (
            "GET",
            "/api/auth/verify",
            401,
            "t1",
        )
        assert line["duration_ms"] >= 0 and "query" not in line

    def test_health_checks_are_debug_level_but_failures_are_not(self, session_factory, logs):
        TestClient(auth_app).get("/health")
        assert [entry["level"] for entry in logs.lines if entry.get("path") == "/health"] == ["DEBUG"]

    def test_a_full_authentication_flow_leaves_no_password_or_token_in_any_log(self, session_factory, logs):
        client = TestClient(auth_app)
        creds = {"email": "alice@example.com", "password": PASSWORD}
        client.post("/api/auth/register", json=creds)
        client.post("/api/auth/login", json=creds)
        client.post("/api/auth/login", json={**creds, "password": "wrong password!!"})
        secrets = [client.cookies.get("access_token"), client.cookies.get("refresh_token", path="/api/auth")]
        client.post("/api/auth/refresh")
        client.post("/api/auth/logout")
        assert all(secrets)
        for secret in [PASSWORD, "wrong password!!", *secrets]:
            assert secret not in logs.raw
        assert any(entry["message"] == "user registered" for entry in logs.lines)

    def test_note_content_never_appears_in_logs(self, session_factory, make_user, logs):
        user = make_user("writer@example.com")
        client = TestClient(note_app)
        payload = {
            "title": "Confidential merger plans",
            "body": "Project Falcon acquisition details",
            "tags": ["secretproj"],
        }
        client.post("/api/notes", json=payload, headers=user.headers)
        client.get("/api/notes/search", params={"q": "falcon"}, headers=user.headers)
        assert "Falcon" not in logs.raw and "merger" not in logs.raw and user.token not in logs.raw

    def test_error_responses_carry_the_correlation_id_in_header_and_body(self, session_factory):
        client = TestClient(note_app)
        unauthorised = client.get("/api/notes", headers={"X-Correlation-ID": "err-1"})
        assert unauthorised.status_code == 401
        assert unauthorised.headers["x-correlation-id"] == "err-1" and unauthorised.json()["correlation_id"] == "err-1"
        assert unauthorised.headers["www-authenticate"] == "Bearer"
        invalid = client.post("/api/notes", json={}, headers={"X-Correlation-ID": "err-2"})
        assert invalid.json()["correlation_id"] == "err-2"

    def test_unhandled_errors_return_a_generic_500_with_an_id_and_log_the_cause(self, logs):
        app = FastAPI()
        init_service(app, "boom-service")

        @app.get("/boom")
        def boom():
            raise RuntimeError("internal detail xyz")

        response = TestClient(app, raise_server_exceptions=False).get("/boom", headers={"X-Correlation-ID": "boom-1"})
        assert response.status_code == 500
        assert response.json() == {"detail": "Internal server error", "correlation_id": "boom-1"}
        assert "internal detail xyz" not in response.text
        failure = next(entry for entry in logs.lines if entry["message"] == "unhandled error")
        assert failure["correlation_id"] == "boom-1" and "internal detail xyz" in failure["exception"]["message"]


class TestCorrelationAcrossEvents:
    def test_the_request_id_follows_the_event_into_the_worker_logs(self, session_factory, make_user, logs):
        user = make_user("trace@example.com")
        response = TestClient(note_app).post(
            "/api/notes",
            json={"title": "Traced", "body": "b"},
            headers={**user.headers, "X-Correlation-ID": "trace-xyz-9"},
        )
        assert response.status_code == 201
        with session_factory() as db:
            assert '"correlation_id":"trace-xyz-9"' in db.scalar(select(OutboxEntry.payload))

        redis = fakeredis.FakeRedis(decode_responses=True)
        OutboxPublisher(session_factory, redis).publish_pending()
        assert redis.xrange(STREAM_NOTE_EVENTS)[0][1]["correlation_id"] == "trace-xyz-9"

        consumer = NoteEventConsumer(redis, lambda event: None, consumer_name="c", block_ms=10, claim_idle_ms=0)
        consumer.ensure_group()
        consumer.poll_once()
        processed = next(entry for entry in logs.lines if entry["message"] == "note event processed")
        assert processed["correlation_id"] == "trace-xyz-9"

    def test_events_without_an_id_still_get_a_stable_one_in_the_worker(self, session_factory, make_user, logs):
        redis = fakeredis.FakeRedis(decode_responses=True)
        redis.xadd(
            STREAM_NOTE_EVENTS,
            {
                "event_id": "0b0a8c6e-0000-4000-8000-000000000001",
                "schema_version": "1",
                "event_type": "created",
                "note_id": "0b0a8c6e-0000-4000-8000-000000000002",
                "owner_id": "0b0a8c6e-0000-4000-8000-000000000003",
                "occurred_at": "2026-10-17T00:00:00",
            },
        )
        consumer = NoteEventConsumer(redis, lambda event: None, consumer_name="c", block_ms=10, claim_idle_ms=0)
        consumer.ensure_group()
        consumer.poll_once()
        processed = next(entry for entry in logs.lines if entry["message"] == "note event processed")
        assert processed["correlation_id"] == "0b0a8c6e000040008000000000000001"


class TestHeartbeat:
    def test_touches_the_configured_file_and_does_nothing_otherwise(self, tmp_path, monkeypatch):
        path = tmp_path / "heartbeat"
        touch_heartbeat()
        assert not path.exists()
        monkeypatch.setattr(get_settings(), "heartbeat_file", str(path))
        touch_heartbeat()
        assert path.exists()

    def test_an_unwritable_path_is_survivable(self, tmp_path, monkeypatch, logs):
        monkeypatch.setattr(get_settings(), "heartbeat_file", str(tmp_path / "missing-dir" / "heartbeat"))
        touch_heartbeat()
        assert any("heartbeat" in entry["message"] for entry in logs.lines)

    def test_the_consumer_loop_keeps_the_heartbeat_fresh(self, tmp_path, monkeypatch):
        path = tmp_path / "heartbeat"
        monkeypatch.setattr(get_settings(), "heartbeat_file", str(path))
        consumer = NoteEventConsumer(
            fakeredis.FakeRedis(decode_responses=True), lambda e: None, consumer_name="c", block_ms=10
        )
        stop = threading.Event()
        thread = threading.Thread(target=consumer.run_forever, args=(stop,), daemon=True)
        thread.start()
        deadline = time.time() + 5
        while not path.exists() and time.time() < deadline:
            time.sleep(0.02)
        stop.set()
        thread.join(timeout=5)
        assert path.exists()
