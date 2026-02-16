"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    app_name: str = "go4-automate"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/go4automate"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Security
    secret_key: str = "change-me-in-production"
    allowed_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # API Keys
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # n8n
    n8n_url: str = "http://localhost:5678"
    n8n_api_key: str = ""

    # SMTP
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@go4.energy"

    # Tenant
    default_tenant_id: str = "default"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
