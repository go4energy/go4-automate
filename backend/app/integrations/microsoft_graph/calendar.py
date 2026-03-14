"""Read-only calendar access via Microsoft Graph."""

from datetime import datetime

from app.integrations.interfaces import CalendarReadProvider
from app.integrations.microsoft_graph.client import MicrosoftGraphClient
from app.integrations.types import CalendarEventRef


class MicrosoftGraphCalendarProvider(CalendarReadProvider):
    """Normalize Outlook calendar events behind the shared interface."""

    def __init__(self, client: MicrosoftGraphClient) -> None:
        self.client = client

    async def list_events(
        self,
        *,
        mailbox: str | None = None,
        limit: int = 20,
    ) -> list[CalendarEventRef]:
        params = {
            "$top": max(1, min(limit, 100)),
            "$orderby": "start/dateTime asc",
            "$select": ",".join(
                [
                    "id",
                    "subject",
                    "start",
                    "end",
                    "organizer",
                    "location",
                ]
            ),
        }
        principal = f"users/{mailbox}" if mailbox else "me"
        payload = await self.client.get(f"{principal}/events", params=params)
        return [self._normalize_event(item) for item in payload.get("value", [])]

    @staticmethod
    def _normalize_event(item: dict) -> CalendarEventRef:
        start_data = item.get("start") or {}
        end_data = item.get("end") or {}
        organizer = (item.get("organizer") or {}).get("emailAddress") or {}
        location = item.get("location") or {}
        return CalendarEventRef(
            provider_event_id=item["id"],
            title=item.get("subject") or "",
            starts_at=MicrosoftGraphCalendarProvider._parse_datetime(
                start_data.get("dateTime")
            ),
            ends_at=MicrosoftGraphCalendarProvider._parse_datetime(
                end_data.get("dateTime")
            ),
            organizer_email=organizer.get("address"),
            location=location.get("displayName"),
            raw=item,
        )

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        if not value:
            return None
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
