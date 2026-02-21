"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    app_name: str = "go4-automate"
    debug: bool = False
    platform_name: str = "go4-automate"
    domain: str = "localhost"
    timezone: str = "Europe/Vienna"

    # Database
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/go4automate"
    )

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Security
    secret_key: str = "change-me-in-production"
    backend_secret: str = ""
    allowed_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # API Keys
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # LLM Model Routing
    llm_model_content: str = "claude-sonnet-4-5-20250929"
    llm_model_analysis: str = "gpt-4o-mini"
    llm_model_classification: str = "gpt-4o-mini"
    llm_model_scoring: str = "gpt-4o-mini"

    # Meta API
    meta_system_user_token: str = ""
    meta_page_id: str = ""
    meta_instagram_business_id: str = ""
    meta_ad_account_id: str = ""
    meta_pixel_id: str = ""
    meta_api_version: str = "v21.0"

    # OpenWeather
    openweather_api_key: str = ""

    # n8n
    n8n_url: str = "http://localhost:5678"
    n8n_api_key: str = ""
    n8n_basic_auth_user: str = ""
    n8n_basic_auth_password: str = ""

    # SMTP
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@go4.energy"

    # Uploads
    upload_dir: str = "uploads"
    max_upload_size_mb: int = 10

    # Search API
    serper_api_key: str = ""

    # LLM — Broadcaster (switchable)
    llm_model_briefing: str = "anthropic"  # "anthropic" | "ollama"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "mistral"

    # TTS (Remote Piper Server)
    tts_engine: str = "piper"  # "piper" | "disabled"
    tts_url: str = "http://localhost:10200"

    # Broadcaster
    broadcaster_audio_dir: str = "uploads/broadcaster"

    # Auth (Listener PWA)
    jwt_secret: str = "change-me-in-production"
    jwt_expiry_hours: int = 720  # 30 days
    listener_self_registration: bool = True

    # Tenant
    default_tenant_id: str = "default"
    active_tenant: str = "go4energy"
    tenant_config_dir: str = "config/tenants"
    template_dir: str = "config/templates"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
