"""Assistant provider gating helpers.

These helpers centralise which providers are currently supported for
voice/chat execution and which action paths still require Graph-specific
implementations.
"""

from app.exceptions import AppError, ValidationError

SUPPORTED_VOICE_PROVIDERS = frozenset({"microsoft_graph"})


def is_supported_voice_provider(provider: str | None) -> bool:
    return bool(provider) and provider in SUPPORTED_VOICE_PROVIDERS


def require_supported_voice_provider(provider: str | None) -> None:
    if is_supported_voice_provider(provider):
        return
    raise AppError(
        f"Provider '{provider}' wird fuer Voice-Chat noch nicht unterstuetzt. "
        "Aktuell nur Microsoft Graph.",
        400,
    )


def require_graph_action_provider(provider: str | None, feature_label: str) -> None:
    if provider == "microsoft_graph":
        return
    raise ValidationError(
        f"Provider '{provider}' wird fuer {feature_label} noch nicht unterstuetzt"
    )
