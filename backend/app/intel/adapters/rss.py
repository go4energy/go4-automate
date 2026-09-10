"""RSS / Atom adapter — wraps feedparser, returns normalized text + items."""

from __future__ import annotations

import asyncio
from datetime import datetime

import feedparser
import httpx
from loguru import logger

from app.intel.adapters.base import AdapterError, SourceAdapter
from app.intel.schemas import FetchResult


class RssAdapter(SourceAdapter):
    """Fetch + parse an RSS/Atom feed."""

    name = "rss"

    async def fetch(
        self, source_config: dict, tenant_id: str
    ) -> FetchResult:
        url = source_config.get("url")
        if not url:
            raise AdapterError("source_config.url is required")

        # Fetch ourselves with httpx so we control timeout + UA
        try:
            async with httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers={
                    "User-Agent": (
                        source_config.get("user_agent")
                        or "go4-automate-intel/1.0"
                    )
                },
            ) as client:
                r = await client.get(url)
                r.raise_for_status()
                body = r.content
                final_url = str(r.url)
        except httpx.HTTPError as e:
            logger.warning(
                "RssAdapter fetch failed for {url}: {err}", url=url, err=str(e)
            )
            raise AdapterError(f"HTTP error for {url}: {e}") from e

        # feedparser is sync — run in thread so we don't block the loop
        feed = await asyncio.to_thread(feedparser.parse, body)
        if feed.bozo and not feed.entries:
            raise AdapterError(
                f"feedparser could not parse {url}: {feed.bozo_exception!r}"
            )

        items = []
        text_chunks: list[str] = []
        for e in feed.entries:
            title = (e.get("title") or "").strip()
            link = (e.get("link") or "").strip()
            summary = (e.get("summary") or "").strip()
            published = (
                e.get("published") or e.get("updated") or ""
            ).strip()
            items.append(
                {
                    "title": title,
                    "link": link,
                    "summary": summary,
                    "published": published,
                }
            )
            text_chunks.append(f"{title}\n{published}\n{summary}".strip())

        text = "\n\n---\n\n".join(text_chunks)

        parsed = {
            "feed_title": (feed.feed.get("title") or "").strip(),
            "feed_link": (feed.feed.get("link") or "").strip(),
            "item_count": len(items),
            "items": items,
        }

        return FetchResult(
            text=text,
            parsed=parsed,
            source_url=final_url,
            fetched_at=datetime.utcnow(),
            raw_size_bytes=len(body),
        )
