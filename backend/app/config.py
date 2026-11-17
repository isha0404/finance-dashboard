"""Application settings, read from environment variables (or a .env file)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # SQLite by default so the app runs with zero setup; docker-compose switches to Postgres.
    database_url: str = "sqlite:///./finance.db"

    # IMPORTANT: override in production. Used to sign JWT access tokens.
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60

    # Comma-separated list of origins allowed to call the API from a browser.
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Upload guard rails
    max_upload_bytes: int = 2 * 1024 * 1024  # 2 MB
    max_import_rows: int = 5000

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
