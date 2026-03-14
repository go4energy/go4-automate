"""Microsoft Graph integration primitives."""

from app.integrations.microsoft_graph.auth import MicrosoftGraphAuthService
from app.integrations.microsoft_graph.calendar import MicrosoftGraphCalendarProvider
from app.integrations.microsoft_graph.client import MicrosoftGraphClient
from app.integrations.microsoft_graph.mail_actions import MicrosoftGraphMailActionProvider
from app.integrations.microsoft_graph.mail_read import MicrosoftGraphMailReadProvider
from app.integrations.microsoft_graph.scopes import (
    MICROSOFT_GRAPH_SCOPES,
    get_microsoft_graph_scopes,
)

__all__ = [
    "MICROSOFT_GRAPH_SCOPES",
    "MicrosoftGraphAuthService",
    "MicrosoftGraphCalendarProvider",
    "MicrosoftGraphClient",
    "MicrosoftGraphMailActionProvider",
    "MicrosoftGraphMailReadProvider",
    "get_microsoft_graph_scopes",
]
