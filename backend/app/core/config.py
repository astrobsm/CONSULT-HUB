from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, loaded from environment / .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "ConsultHUB API"
    api_prefix: str = "/api"

    # SQLite for dev; override with a PostgreSQL URL in production.
    database_url: str = "sqlite:///./consulthub.db"

    # Auth / JWT. CHANGE secret_key in every real deployment (set via env).
    secret_key: str = "dev-insecure-change-me-please"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24h
    # PBKDF2 work factor. Lowered only in tests for speed.
    pbkdf2_iterations: int = 200_000

    # Password-reset / invite tokens, and the base URL used in emailed links.
    reset_token_expire_minutes: int = 60
    invite_token_expire_minutes: int = 60 * 24 * 7  # 7 days
    frontend_base_url: str = "http://localhost:5173"

    # Escalation engine. Disable in tests; the interval drives the scheduler.
    escalation_enabled: bool = True
    escalation_interval_seconds: int = 60

    # Email. If smtp_host is unset, emails are logged (console transport).
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str = "ConsultHUB <no-reply@consulthub.local>"
    smtp_tls: bool = True

    # Attachment storage. Local disk for dev; swap for S3-compatible in prod.
    storage_dir: str = "./uploads"
    max_upload_mb: int = 15

    # Appointment slot hold (temporary lock) duration, minutes.
    appointment_hold_minutes: int = 3

    # Comma-separated origins allowed by CORS.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
