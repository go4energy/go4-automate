"""Jobs-board adapter — placeholder for v1.

A future version will detect new job postings (LinkedIn Jobs API,
Stepstone scraping, etc.) as a hiring-signal. Skeleton kept so the
adapter-name discovery (intel_source.adapter='jobs_board') doesn't
crash with KeyError; it just raises a clear NotImplemented.
"""

from __future__ import annotations

from app.intel.adapters.base import AdapterError, SourceAdapter
from app.intel.schemas import FetchResult


class JobsBoardAdapter(SourceAdapter):
    name = "jobs_board"

    async def fetch(
        self, source_config: dict, tenant_id: str
    ) -> FetchResult:
        raise AdapterError(
            "jobs_board adapter not implemented in v1; comes in v2"
        )
