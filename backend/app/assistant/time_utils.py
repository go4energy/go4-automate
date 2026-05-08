"""Datetime helpers for Assistant persistence.

The assistant tables currently use `TIMESTAMP WITHOUT TIME ZONE`.
Persisting timezone-aware UTC datetimes via asyncpg can fail, so Assistant
state writes use naive UTC consistently.
"""

from datetime import UTC, datetime, timedelta


def utc_now_naive() -> datetime:
    """Return current UTC time as naive datetime for DB writes/comparisons."""
    return datetime.now(UTC).replace(tzinfo=None)


def utc_in_naive(*, minutes: int = 0) -> datetime:
    """Return a future naive UTC timestamp."""
    return utc_now_naive() + timedelta(minutes=minutes)
