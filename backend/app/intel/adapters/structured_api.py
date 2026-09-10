"""Structured-API adapter — placeholder for v1.

A future version will fetch from REST/GraphQL endpoints that return
JSON (e.g. EPO patent API, BAFA-API, regulatory bulletin APIs). For
now this is a stub.
"""

from __future__ import annotations

from app.intel.adapters.base import AdapterError, SourceAdapter
from app.intel.schemas import FetchResult


class StructuredApiAdapter(SourceAdapter):
    name = "structured_api"

    async def fetch(
        self, source_config: dict, tenant_id: str
    ) -> FetchResult:
        raise AdapterError(
            "structured_api adapter not implemented in v1; comes in v2"
        )
