"""JS-rendering web adapter via Playwright + bundled Chromium.

Loaded lazily by ``adapters/__init__.py`` so playwright stays optional.
The Chromium binary lives inside our backend container (installed via
Dockerfile's ``playwright install chromium``). We NEVER mount or shell
out to ``/projects/ragflow/chrome-linux64`` — that belongs to ragflow.
"""

from __future__ import annotations

from datetime import datetime

from bs4 import BeautifulSoup
from loguru import logger

from app.intel.adapters.base import AdapterError, SourceAdapter
from app.intel.schemas import FetchResult

_DEFAULT_UA = (
    "Mozilla/5.0 (compatible; go4-automate-intel/1.0; "
    "+https://automate.go4.energy) playwright"
)


class WebJsAdapter(SourceAdapter):
    """Fetch a page with JS rendering enabled."""

    name = "web_js"

    async def fetch(
        self, source_config: dict, tenant_id: str
    ) -> FetchResult:
        url = source_config.get("url")
        if not url:
            raise AdapterError("source_config.url is required")
        ua = source_config.get("user_agent") or _DEFAULT_UA
        wait_for = source_config.get("wait_for")  # CSS selector or 'networkidle'
        timeout_ms = int(source_config.get("timeout_ms") or 30_000)
        selector = source_config.get("selector")

        try:
            from playwright.async_api import (
                Error as PWError,
            )
            from playwright.async_api import (
                TimeoutError as PWTimeout,
            )
            from playwright.async_api import (
                async_playwright,
            )
        except ImportError as e:
            raise AdapterError(
                "playwright not installed; pip install playwright + "
                "playwright install chromium"
            ) from e

        html = ""
        final_url = url
        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True)
                try:
                    ctx = await browser.new_context(user_agent=ua)
                    page = await ctx.new_page()
                    await page.goto(url, timeout=timeout_ms, wait_until="load")
                    if wait_for == "networkidle":
                        await page.wait_for_load_state("networkidle", timeout=timeout_ms)
                    elif wait_for:
                        await page.wait_for_selector(wait_for, timeout=timeout_ms)
                    html = await page.content()
                    final_url = page.url
                finally:
                    await browser.close()
        except PWTimeout as e:
            raise AdapterError(f"Playwright timeout for {url}: {e}") from e
        except PWError as e:
            raise AdapterError(f"Playwright error for {url}: {e}") from e
        except Exception as e:
            logger.exception("web_js unexpected error for {url}", url=url)
            raise AdapterError(f"web_js failed for {url}: {e}") from e

        text, parsed = self._extract(html, selector)
        return FetchResult(
            text=text,
            parsed=parsed,
            source_url=final_url,
            fetched_at=datetime.utcnow(),
            raw_size_bytes=len(html.encode("utf-8")),
        )

    @staticmethod
    def _extract(html: str, selector: str | None) -> tuple[str, dict]:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript", "iframe"]):
            tag.decompose()
        text_root = soup.select_one(selector) if selector else soup
        text_root = text_root if text_root is not None else soup
        text = text_root.get_text(separator="\n", strip=True)
        text = "\n".join(line for line in text.splitlines() if line)
        title = (soup.title.get_text(strip=True) if soup.title else "") or ""
        meta_description = ""
        md_tag = soup.find("meta", attrs={"name": "description"})
        if md_tag and md_tag.get("content"):
            meta_description = md_tag["content"].strip()
        parsed = {"title": title, "meta_description": meta_description}
        return text, parsed
