"""Environment-driven settings shared by all backend services."""

from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PLACEHOLDER_SECRETS = {
    "dev-secret-key-change-in-production",
    "your-super-secret-jwt-key-change-in-production",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    log_level: str = "INFO"
    heartbeat_file: str | None = None

    database_url: str = "postgresql://linknote:linknote_password@localhost:5432/linknote"
    redis_url: str = "redis://localhost:6379"

    jwt_secret_key: str = "dev-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=15, gt=0)
    refresh_token_expire_days: int = Field(default=7, gt=0)
    bcrypt_rounds: int = Field(default=12, ge=4, le=16)
    cookie_secure: bool = True

    note_max_body_bytes: int = Field(default=512 * 1024, gt=0)
    outbox_batch_size: int = Field(default=100, gt=0)
    outbox_poll_interval_seconds: float = Field(default=1.0, gt=0)
    note_events_stream_maxlen: int = Field(default=100_000, gt=0)

    link_suggestion_threshold: float = Field(default=0.30, gt=0, le=1)
    link_suggestion_min_shared_keywords: int = Field(default=2, ge=1)
    link_suggestion_max_per_note: int = Field(default=10, gt=0)
    link_candidate_limit: int = Field(default=200, gt=0)
    graph_max_nodes: int = Field(default=500, gt=0)

    consumer_group: str = "link-service"
    consumer_block_ms: int = Field(default=5000, gt=0)
    consumer_claim_idle_ms: int = Field(default=60_000, ge=0)
    consumer_max_deliveries: int = Field(default=5, gt=0)
    event_dedupe_ttl_seconds: int = Field(default=86_400, gt=0)

    @property
    def sqlalchemy_url(self) -> str:
        url = self.database_url
        for prefix in ("postgresql://", "postgres://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url[len(prefix) :]
        return url

    @model_validator(mode="after")
    def _check_secret(self) -> Settings:
        if len(self.jwt_secret_key) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters")
        if self.environment.lower() == "production" and self.jwt_secret_key in PLACEHOLDER_SECRETS:
            raise ValueError("JWT_SECRET_KEY must be changed from the placeholder value in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
