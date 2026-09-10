"""Intel source adapters — registry + factory."""

from app.intel.adapters.base import AdapterError, SourceAdapter
from app.intel.adapters.jobs_board import JobsBoardAdapter
from app.intel.adapters.rss import RssAdapter
from app.intel.adapters.structured_api import StructuredApiAdapter
from app.intel.adapters.web import WebAdapter

_REGISTRY: dict[str, type[SourceAdapter]] = {
    WebAdapter.name: WebAdapter,
    RssAdapter.name: RssAdapter,
    JobsBoardAdapter.name: JobsBoardAdapter,
    StructuredApiAdapter.name: StructuredApiAdapter,
}


def get_adapter(name: str) -> SourceAdapter:
    """Return an adapter instance by registered name.

    Raises ``AdapterError`` for unknown names. ``web_js`` is loaded
    lazily so playwright stays an optional dependency.
    """
    if name == "web_js":
        from app.intel.adapters.web_js import WebJsAdapter

        return WebJsAdapter()
    cls = _REGISTRY.get(name)
    if cls is None:
        raise AdapterError(f"unknown adapter: {name!r}")
    return cls()


__all__ = ["AdapterError", "SourceAdapter", "get_adapter"]
