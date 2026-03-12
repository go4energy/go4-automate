"""Human-like behavior utilities for LinkedIn scraping.

Fast but natural: event-based waiting for page loads,
tiny randomized delays only for mouse/keyboard transitions.
"""

import asyncio
import contextlib
import random

from loguru import logger
from playwright.async_api import Page

# --------------- micro delays (mouse move, click transition) ---------------


async def micro_pause(min_ms: int = 80, max_ms: int = 250) -> None:
    """Tiny pause between UI actions (mouse move -> click)."""
    await asyncio.sleep(random.uniform(min_ms / 1000, max_ms / 1000))


async def short_pause(min_ms: int = 300, max_ms: int = 800) -> None:
    """Short pause for visual transitions (modal open, tab switch)."""
    await asyncio.sleep(random.uniform(min_ms / 1000, max_ms / 1000))


async def human_delay(min_sec: float = 0.3, max_sec: float = 0.8) -> float:
    """Backwards-compatible delay. Defaults changed to fast values."""
    delay = random.uniform(min_sec, max_sec)
    await asyncio.sleep(delay)
    return delay


# --------------- mouse movement ---------------


async def random_mouse_move(page: Page) -> None:
    """Move mouse to random position with natural curve."""
    viewport = page.viewport_size
    if not viewport:
        return
    x = random.randint(100, viewport["width"] - 100)
    y = random.randint(100, viewport["height"] - 100)
    await page.mouse.move(x, y, steps=random.randint(3, 8))
    await micro_pause(30, 100)


async def move_mouse_to(page: Page, element) -> None:
    """Move mouse towards an element's bounding box center."""
    box = await element.bounding_box()
    if not box:
        return
    x = box["x"] + box["width"] / 2 + random.uniform(-5, 5)
    y = box["y"] + box["height"] / 2 + random.uniform(-3, 3)
    await page.mouse.move(x, y, steps=random.randint(3, 8))
    await micro_pause(50, 150)


# --------------- scrolling ---------------


async def human_scroll(page: Page, min_scrolls: int = 2, max_scrolls: int = 4) -> None:
    """Quick natural scroll using PageDown key presses."""
    n = random.randint(min_scrolls, max_scrolls)
    for _ in range(n):
        await page.keyboard.press("PageDown")
        await asyncio.sleep(random.uniform(0.15, 0.4))


async def scroll_to_bottom_fast(page: Page, max_iterations: int = 30) -> None:
    """Scroll to bottom using PageDown, stop when no new content loads."""
    prev_height = 0
    stale = 0
    for _ in range(max_iterations):
        height = await page.evaluate("document.body.scrollHeight")
        if height == prev_height:
            stale += 1
            if stale >= 2:
                break
        else:
            stale = 0
        prev_height = height
        await page.keyboard.press("PageDown")
        await asyncio.sleep(random.uniform(0.3, 0.7))


# --------------- typing ---------------


async def human_type_text(page: Page, element, text: str) -> None:
    """Type text with natural per-character delay."""
    await element.click()
    await micro_pause(100, 200)
    for char in text:
        await element.type(char, delay=random.randint(25, 70))
    await micro_pause(100, 300)


# --------------- page waiting (event-based) ---------------


async def wait_for_page_ready(
    page: Page,
    selector: str | None = None,
    timeout: int = 15000,
) -> bool:
    """Wait for page to be ready: network idle OR specific element visible.

    Args:
        page: Playwright page
        selector: Optional CSS selector to wait for
        timeout: Max wait in ms

    Returns:
        True if ready, False on timeout
    """
    try:
        if selector:
            await page.wait_for_selector(selector, timeout=timeout, state="visible")
        else:
            await page.wait_for_load_state("networkidle", timeout=timeout)
        return True
    except Exception:
        # Fallback: at least DOM is loaded
        with contextlib.suppress(Exception):
            await page.wait_for_load_state("domcontentloaded", timeout=3000)
        return False


async def wait_for_element(
    page: Page,
    selectors: str | list[str],
    timeout: int = 10000,
    state: str = "visible",
):
    """Wait for first matching selector. Returns element or None."""
    if isinstance(selectors, str):
        selectors = [selectors]
    combined = ", ".join(selectors)
    try:
        return await page.wait_for_selector(combined, timeout=timeout, state=state)
    except Exception:
        return None


async def wait_for_navigation(page: Page, timeout: int = 15000) -> None:
    """Wait for navigation to complete (URL change + network idle)."""
    with contextlib.suppress(Exception):
        await page.wait_for_load_state("networkidle", timeout=timeout)


# --------------- rate limiting ---------------


async def wait_for_rate_limit_recovery(
    base_wait: float = 60, max_wait: float = 300
) -> float:
    """Wait when rate limit is detected. Exponential backoff with jitter."""
    jitter = random.uniform(0.8, 1.2)
    delay = min(base_wait * jitter, max_wait)
    logger.warning("Rate limit detected, waiting {delay:.0f}s", delay=delay)
    await asyncio.sleep(delay)
    return delay
