"""Static-HTML web adapter (httpx + BeautifulSoup).

For sites that don't need a JS runtime. If ``source_config['render_js']``
is True, raises ``AdapterError`` pointing callers at ``web_js``.

NEVER mounts ``/projects/ragflow/chrome-linux64`` — JS rendering uses
its own Playwright in ``web_js.py``.
"""

from __future__ import annotations

from datetime import datetime

import httpx
from bs4 import BeautifulSoup
from loguru import logger

from app.intel.adapters.base import AdapterError, SourceAdapter
from app.intel.schemas import FetchResult

_DEFAULT_UA = (
    "Mozilla/5.0 (compatible; go4-automate-intel/1.0; "
    "+https://automate.go4.energy)"
)


class WebAdapter(SourceAdapter):
    """Fetch + extract text content from a static HTML page."""

    name = "web"

    async def fetch(
        self, source_config: dict, tenant_id: str
    ) -> FetchResult:
        url = source_config.get("url")
        if not url:
            raise AdapterError("source_config.url is required")

        if source_config.get("render_js"):
            raise AdapterError(
                "render_js=true requires the web_js adapter, not web"
            )

        ua = source_config.get("user_agent") or _DEFAULT_UA
        extra_headers = source_config.get("headers") or {}
        selector = source_config.get("selector")

        headers = {"User-Agent": ua, **extra_headers}

        try:
            async with httpx.AsyncClient(
                timeout=30.0, follow_redirects=True, headers=headers
            ) as client:
                r = await client.get(url)
                r.raise_for_status()
                html = r.text
                final_url = str(r.url)
                size = len(r.content)
        except httpx.HTTPError as e:
            logger.warning(
                "WebAdapter fetch failed for {url}: {err}", url=url, err=str(e)
            )
            raise AdapterError(f"HTTP error for {url}: {e}") from e

        text, parsed = self._extract(html, selector)

        return FetchResult(
            text=text,
            parsed=parsed,
            source_url=final_url,
            fetched_at=datetime.utcnow(),
            raw_size_bytes=size,
        )

    @staticmethod
    def _extract(html: str, selector: str | None) -> tuple[str, dict]:
        """Strip scripts/styles, optionally scope to CSS selector."""
        soup = BeautifulSoup(html, "html.parser")
        # Drop noise
        for tag in soup(["script", "style", "noscript", "iframe"]):
            tag.decompose()

        if selector:
            scope = soup.select_one(selector)
            text_root = scope if scope is not None else soup
        else:
            text_root = soup

        text = text_root.get_text(separator="\n", strip=True)
        # Collapse long whitespace runs to single blank lines
        text = "\n".join(line for line in text.splitlines() if line)

        title = (soup.title.get_text(strip=True) if soup.title else "") or ""
        meta_description = ""
        md_tag = soup.find("meta", attrs={"name": "description"})
        if md_tag and md_tag.get("content"):
            meta_description = md_tag["content"].strip()

        h1 = ""
        h1_tag = soup.find("h1")
        if h1_tag:
            h1 = h1_tag.get_text(strip=True)

        parsed = {
            "title": title,
            "meta_description": meta_description,
            "h1": h1,
        }
        return text, parsed
