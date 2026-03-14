"""Scope definitions for Microsoft Graph usage in go4-automate."""

from app.integrations.types import IntegrationCapability

MICROSOFT_GRAPH_SCOPES: dict[IntegrationCapability, tuple[str, ...]] = {
    IntegrationCapability.READ_MAIL: ("Mail.Read", "User.Read", "offline_access"),
    IntegrationCapability.READ_CALENDAR: (
        "Calendars.Read",
        "User.Read",
        "offline_access",
    ),
    IntegrationCapability.SEND_MAIL: ("Mail.Send", "User.Read", "offline_access"),
    IntegrationCapability.MAIL_ACTIONS: (
        "Mail.ReadWrite",
        "Mail.Send",
        "User.Read",
        "offline_access",
    ),
}


def get_microsoft_graph_scopes(
    capabilities: set[IntegrationCapability],
) -> list[str]:
    """Return a deduplicated list of delegated scopes for the requested capabilities."""
    scope_order: list[str] = []
    seen: set[str] = set()
    for capability in capabilities:
        for scope in MICROSOFT_GRAPH_SCOPES.get(capability, ()):
            if scope not in seen:
                scope_order.append(scope)
                seen.add(scope)
    return scope_order
