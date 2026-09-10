"""Source adapter base — every fetch source implements this contract."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.intel.schemas import FetchResult


class AdapterError(Exception):
    """Adapter failed to fetch — wraps network/parse/HTTP errors.

    Adapters MUST raise this (never return None) so the worker can
    update ``intel_source.last_status`` + ``consecutive_failures``.
    """


class SourceAdapter(ABC):
    """Async adapter contract.

    Subclass and set ``name`` (matches ``intel_source.adapter``).
    """

    name: str = ""

    @abstractmethod
    async def fetch(
        self, source_config: dict, tenant_id: str
    ) -> FetchResult:
        """Fetch the source, return normalized text + parsed dict.

        Raises ``AdapterError`` on failure. Never returns None.
        """
        raise NotImplementedError
