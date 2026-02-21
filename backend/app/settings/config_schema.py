"""Global platform settings schema — auto-generated from Settings.model_fields."""

from __future__ import annotations

import types
import typing

from app.config import Settings

# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

GLOBAL_CATEGORIES: list[dict] = [
    {"key": "platform", "label": "Plattform", "order": 1},
    {"key": "api_keys", "label": "API-Schluessel", "order": 2},
    {"key": "llm_models", "label": "LLM-Modelle", "order": 3},
    {"key": "meta_api", "label": "Meta API", "order": 4},
    {"key": "smtp", "label": "E-Mail (SMTP)", "order": 5},
    {"key": "n8n", "label": "n8n", "order": 6},
    {"key": "tts_audio", "label": "TTS / Audio", "order": 7},
    {"key": "infrastructure", "label": "Infrastruktur", "order": 8},
    {"key": "tenant", "label": "Mandanten", "order": 9},
    {"key": "sonstige", "label": "Sonstige", "order": 99},
]

# ---------------------------------------------------------------------------
# Per-field metadata (category, description, overrides)
# Keys not listed here get category="sonstige" and key as description.
# ---------------------------------------------------------------------------

_SECRET_FRAGMENTS = {"key", "token", "secret", "password"}

FIELD_META: dict[str, dict] = {
    # Platform
    "app_name": {"cat": "platform", "desc": "Name der Plattform"},
    "debug": {"cat": "platform", "desc": "Debug-Modus aktivieren"},
    "platform_name": {"cat": "platform", "desc": "Anzeigename der Plattform"},
    "domain": {"cat": "platform", "desc": "Domain der Plattform"},
    "timezone": {"cat": "platform", "desc": "Zeitzone der Plattform"},
    "active_tenant": {"cat": "platform", "desc": "Aktiver Tenant"},
    # API Keys
    "anthropic_api_key": {"cat": "api_keys", "desc": "Anthropic API Key (Claude)"},
    "openai_api_key": {"cat": "api_keys", "desc": "OpenAI API Key"},
    "serper_api_key": {"cat": "api_keys", "desc": "Serper API Key (Web-Suche)"},
    "openweather_api_key": {"cat": "api_keys", "desc": "OpenWeather API Key"},
    # LLM Models
    "llm_model_content": {
        "cat": "llm_models",
        "desc": "LLM-Modell fuer Content-Generierung",
    },
    "llm_model_analysis": {"cat": "llm_models", "desc": "LLM-Modell fuer Analyse"},
    "llm_model_classification": {
        "cat": "llm_models",
        "desc": "LLM-Modell fuer Klassifikation",
    },
    "llm_model_scoring": {"cat": "llm_models", "desc": "LLM-Modell fuer Scoring"},
    "llm_model_briefing": {
        "cat": "llm_models",
        "desc": "LLM-Provider fuer Broadcaster Briefings",
        "options": ["anthropic", "ollama"],
    },
    "ollama_url": {"cat": "llm_models", "desc": "Ollama Server URL"},
    "ollama_model": {"cat": "llm_models", "desc": "Ollama Modell-Name"},
    # Meta API
    "meta_system_user_token": {"cat": "meta_api", "desc": "Meta System User Token"},
    "meta_page_id": {"cat": "meta_api", "desc": "Meta Page ID"},
    "meta_instagram_business_id": {
        "cat": "meta_api",
        "desc": "Instagram Business Account ID",
    },
    "meta_ad_account_id": {"cat": "meta_api", "desc": "Meta Ad Account ID"},
    "meta_pixel_id": {"cat": "meta_api", "desc": "Meta Pixel ID"},
    "meta_api_version": {"cat": "meta_api", "desc": "Meta API Version"},
    # SMTP
    "smtp_host": {"cat": "smtp", "desc": "SMTP Server Hostname"},
    "smtp_port": {"cat": "smtp", "desc": "SMTP Server Port", "min": 1, "max": 65535},
    "smtp_user": {"cat": "smtp", "desc": "SMTP Benutzername"},
    "smtp_password": {"cat": "smtp", "desc": "SMTP Passwort"},
    "smtp_from": {"cat": "smtp", "desc": "Absender E-Mail-Adresse"},
    # n8n
    "n8n_url": {"cat": "n8n", "desc": "n8n Server URL"},
    "n8n_api_key": {"cat": "n8n", "desc": "n8n API Key"},
    "n8n_basic_auth_user": {"cat": "n8n", "desc": "n8n Basic Auth Benutzername"},
    "n8n_basic_auth_password": {"cat": "n8n", "desc": "n8n Basic Auth Passwort"},
    # TTS / Audio
    "tts_engine": {
        "cat": "tts_audio",
        "desc": "TTS-Engine fuer Audio-Generierung",
        "options": ["piper", "disabled"],
    },
    "tts_url": {"cat": "tts_audio", "desc": "TTS Server URL (Piper)"},
    "broadcaster_audio_dir": {
        "cat": "tts_audio",
        "desc": "Verzeichnis fuer Audio-Dateien",
    },
    # Infrastructure
    "database_url": {
        "cat": "infrastructure",
        "desc": "PostgreSQL Datenbank-URL",
        "editable": False,
    },
    "redis_url": {
        "cat": "infrastructure",
        "desc": "Redis Server URL",
        "editable": False,
    },
    "secret_key": {
        "cat": "infrastructure",
        "desc": "Geheimer Schluessel fuer Session-Verwaltung",
    },
    "backend_secret": {
        "cat": "infrastructure",
        "desc": "Backend Secret fuer Service-Kommunikation",
    },
    "allowed_origins": {
        "cat": "infrastructure",
        "desc": "Erlaubte CORS Origins (komma-getrennt)",
    },
    "upload_dir": {"cat": "infrastructure", "desc": "Upload-Verzeichnis"},
    "max_upload_size_mb": {
        "cat": "infrastructure",
        "desc": "Maximale Upload-Groesse (MB)",
        "min": 1,
        "max": 100,
    },
    "jwt_secret": {"cat": "infrastructure", "desc": "JWT Secret fuer Listener-Auth"},
    "jwt_expiry_hours": {
        "cat": "infrastructure",
        "desc": "JWT Token Gueltigkeit (Stunden)",
        "min": 1,
        "max": 8760,
    },
    "listener_self_registration": {
        "cat": "infrastructure",
        "desc": "Listener-Selbstregistrierung erlauben",
    },
    # Tenant
    "default_tenant_id": {"cat": "tenant", "desc": "Standard-Tenant ID"},
    "tenant_config_dir": {
        "cat": "tenant",
        "desc": "Verzeichnis fuer Tenant-Konfigurationen",
    },
    "template_dir": {"cat": "tenant", "desc": "Verzeichnis fuer Templates"},
}


# ---------------------------------------------------------------------------
# Type helpers
# ---------------------------------------------------------------------------


def _resolve_python_type(annotation: type) -> str:
    """Map a Python / Pydantic annotation to a schema type string."""
    origin = typing.get_origin(annotation)
    if origin is list or origin is types.GenericAlias:
        return "string"  # list[str] → exposed as comma-separated string
    if annotation is bool:
        return "boolean"
    if annotation is int:
        return "integer"
    return "string"


def _is_secret(name: str) -> bool:
    """Heuristic: field name contains a secret-ish fragment."""
    return any(frag in name for frag in _SECRET_FRAGMENTS)


def _default_for_json(value: object) -> object:
    """Make a field default JSON-friendly."""
    if isinstance(value, list):
        return ",".join(str(v) for v in value)
    return value


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------


def _generate_global_params() -> list[dict]:
    """Build GLOBAL_PARAMS from Settings.model_fields + FIELD_META."""
    params: list[dict] = []
    for name, field_info in Settings.model_fields.items():
        meta = FIELD_META.get(name, {})

        # Determine type
        if meta.get("options"):
            param_type = "enum"
        elif _is_secret(name):
            param_type = "secret"
        else:
            param_type = _resolve_python_type(field_info.annotation)

        entry: dict = {
            "key": name,
            "type": param_type,
            "default": _default_for_json(field_info.default),
            "description": meta.get("desc", name),
            "category": meta.get("cat", "sonstige"),
        }

        # Optional fields
        if param_type == "enum":
            entry["options"] = meta["options"]
        if "min" in meta:
            entry["min"] = meta["min"]
        if "max" in meta:
            entry["max"] = meta["max"]
        if "editable" in meta:
            entry["editable"] = meta["editable"]

        params.append(entry)

    return params


# ---------------------------------------------------------------------------
# Public exports (same interface as before)
# ---------------------------------------------------------------------------

GLOBAL_PARAMS: list[dict] = _generate_global_params()
GLOBAL_PARAMS_BY_KEY: dict[str, dict] = {p["key"]: p for p in GLOBAL_PARAMS}
