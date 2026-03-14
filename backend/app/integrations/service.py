"""Shared service helpers for provider capability checks and routing."""

from app.exceptions import ForbiddenError, ValidationError
from app.integrations.types import IntegrationCapability, IntegrationConnectionDescriptor


class IntegrationService:
    """Common integration-layer checks used by business modules."""

    @staticmethod
    def require_capability(
        connection: IntegrationConnectionDescriptor,
        capability: IntegrationCapability,
    ) -> None:
        """Ensure the connection allows the requested operation."""
        if capability not in connection.granted_capabilities:
            raise ForbiddenError(
                f"Verbindung erlaubt die Funktion '{capability.value}' nicht"
            )

    @staticmethod
    def require_mailbox(connection: IntegrationConnectionDescriptor) -> str:
        """Return the mailbox address or fail fast."""
        if not connection.mailbox_address:
            raise ValidationError("Fuer diese Verbindung ist keine Mailbox hinterlegt")
        return connection.mailbox_address
