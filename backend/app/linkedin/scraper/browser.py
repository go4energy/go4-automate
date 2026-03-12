"""Playwright browser session management for LinkedIn.

Event-based waiting (no fixed sleeps for page loads).
Small randomized delays only for mouse/keyboard transitions.
"""

import asyncio
import contextlib
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from loguru import logger
from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from app.linkedin.scraper.human_like import (
    human_scroll,
    human_type_text,
    micro_pause,
    move_mouse_to,
    random_mouse_move,
    short_pause,
    wait_for_element,
    wait_for_navigation,
    wait_for_page_ready,
)


class LinkedInBrowser:
    """Manages Playwright browser sessions for LinkedIn scraping."""

    LINKEDIN_URL = "https://www.linkedin.com"
    SALES_NAV_URL = "https://www.linkedin.com/sales"
    LOGIN_URL = "https://www.linkedin.com/login"

    # Selectors for key LinkedIn elements
    SEL_TOPCARD = '[componentkey$="Topcard"]'
    SEL_NAV = "[data-test-global-nav], nav"
    SEL_PROFILE_LINK = 'a[href*="/in/"]'
    SEL_SEARCH_RESULTS = (
        "[data-x--lead-search-results],"
        ".search-results__result-list,"
        '[data-anonymize="person-name"]'
    )
    SEL_MODAL = (
        ".pv-contact-info,"
        ".artdeco-modal__content,"
        '[class*="contact-info"],'
        "#artdeco-modal-outlet .artdeco-modal"
    )
    SEL_MODAL_CLOSE = (
        ".artdeco-modal__dismiss,"
        'button[aria-label="Dismiss"],'
        'button[aria-label="Schliessen"],'
        'button[data-control-name="contact_close"]'
    )

    def __init__(
        self,
        session_dir: str | Path = "sessions",
        headless: bool = False,
    ):
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.headless = headless
        self.playwright = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self._account_email: str | None = None

    # ======================== LIFECYCLE ========================

    async def start(self, account_email: str, session_data: dict | None = None) -> None:
        """Start browser with saved session if available."""
        self._account_email = account_email

        # Ensure DISPLAY is set for VNC
        os.environ.setdefault("DISPLAY", ":1")

        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )

        # Create context with session if available
        storage_state = None
        if session_data and "storage_state" in session_data:
            storage_state = session_data["storage_state"]
        elif session_data is None:
            # Try loading from file
            file_session = await self.load_session_from_file(account_email)
            if file_session:
                storage_state = file_session.get("storage_state")

        self.context = await self.browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="de-DE",
            storage_state=storage_state,
        )
        self.page = await self.context.new_page()

        logger.info("Browser started for {email}", email=account_email)

    async def stop(self) -> dict | None:
        """Stop browser, save and return session."""
        session_data = None
        if self.context:
            with contextlib.suppress(Exception):
                session_data = await self.save_session()
            await self.context.close()

        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

        self.page = None
        self.context = None
        self.browser = None
        self.playwright = None

        logger.info("Browser stopped")
        return session_data

    # ======================== SESSION ========================

    async def check_session_valid(self) -> bool:
        """Check if LinkedIn session is still valid."""
        if not self.page:
            return False
        try:
            await self.page.goto(
                self.LINKEDIN_URL + "/feed/", wait_until="domcontentloaded"
            )
            await wait_for_page_ready(self.page, self.SEL_NAV, timeout=10000)

            url = self.page.url
            if self.is_login_required(url):
                logger.warning("Session invalid - redirected to login")
                return False

            if any(p in url for p in ("/feed", "/mynetwork", "/in/")):
                logger.info("Session is valid")
                return True

            # Fallback: check for nav element
            nav = await self.page.query_selector(self.SEL_NAV)
            if nav:
                logger.info("Session is valid (nav found)")
                return True

            logger.warning("Session check: no indicators at {url}", url=url)
            return False

        except Exception as e:
            logger.error("Error checking session: {err}", err=str(e))
            return False

    async def save_session(self) -> dict:
        """Save current browser session."""
        if not self.context:
            raise RuntimeError("No browser context available")

        storage_state = await self.context.storage_state()
        session_data = {
            "storage_state": storage_state,
            "saved_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(days=30)).isoformat(),
        }

        if self._account_email:
            session_path = self.get_session_path(self._account_email)
            with open(session_path, "w") as f:
                json.dump(session_data, f)
            logger.info("Session saved to {path}", path=str(session_path))

        return session_data

    async def load_session_from_file(self, account_email: str) -> dict | None:
        """Load session from file."""
        session_path = self.get_session_path(account_email)
        if not session_path.exists():
            return None
        try:
            with open(session_path) as f:
                session_data = json.load(f)
            expires_at = datetime.fromisoformat(session_data.get("expires_at", ""))
            if expires_at < datetime.utcnow():
                logger.warning("Session file expired")
                return None
            return session_data
        except Exception as e:
            logger.error("Error loading session file: {err}", err=str(e))
            return None

    def get_session_path(self, account_email: str) -> Path:
        safe_name = account_email.replace("@", "_at_").replace(".", "_")
        return self.session_dir / f"{safe_name}_session.json"

    async def import_cookies(self, cookies: list[dict]) -> None:
        if not self.context:
            raise RuntimeError("Browser context not started")
        await self.context.add_cookies(cookies)
        logger.info("Imported {count} cookies", count=len(cookies))

    # ======================== NAVIGATION ========================

    async def _goto(
        self,
        url: str,
        wait_selector: str | None = None,
        timeout: int = 15000,
    ) -> bool:
        """Navigate to URL and wait for page ready (event-based).

        Args:
            url: Target URL
            wait_selector: CSS selector to wait for after navigation
            timeout: Max wait in ms

        Returns:
            True if page loaded successfully
        """
        if not self.page:
            raise RuntimeError("Browser not started")
        try:
            await self.page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            await wait_for_page_ready(self.page, wait_selector, timeout=timeout)
            return True
        except Exception as e:
            logger.warning("Navigation to {url} issue: {err}", url=url[:60], err=str(e))
            return False

    async def navigate_to_sales_navigator(self) -> bool:
        """Navigate to Sales Navigator."""
        ok = await self._goto(self.SALES_NAV_URL, self.SEL_SEARCH_RESULTS)
        if not ok:
            return False

        url = self.page.url
        if "/sales" in url:
            logger.info("Navigated to Sales Navigator")
            return True

        if "premium" in url.lower() or "subscription" in url.lower():
            logger.error("Sales Navigator subscription required")
            return False

        return False

    async def navigate_to_search(self, search_url: str) -> bool:
        """Navigate to a Sales Navigator search URL."""
        await random_mouse_move(self.page)
        ok = await self._goto(search_url, self.SEL_SEARCH_RESULTS)

        if not ok:
            content = await self.page.content()
            if self.is_rate_limited(content):
                logger.error("Rate limited by LinkedIn")
                return False

        await human_scroll(self.page, 1, 2)
        logger.info("Search results loaded")
        return True

    async def navigate_to_connections(self) -> bool:
        """Navigate to LinkedIn connections page (1st-degree, recently added)."""
        url = "https://www.linkedin.com/mynetwork/invite-connect/connections/"
        ok = await self._goto(url, self.SEL_PROFILE_LINK)

        if not ok:
            logger.warning("Connections page may not have loaded fully")

        # Check sort order
        sort_btn = await self.page.query_selector(
            'button[aria-label*="Sortier"], '
            'button[class*="sort"], '
            ".mn-connections__sort-dropdown button"
        )
        if sort_btn:
            btn_text = await sort_btn.inner_text()
            if "neu" not in btn_text.lower() and "recent" not in btn_text.lower():
                logger.info("Changing sort to recently added")
                await move_mouse_to(self.page, sort_btn)
                await sort_btn.click()
                await short_pause()

                for option_text in [
                    "Neu hinzugef\u00fcgt",
                    "Neu hinzugefuegt",
                    "Recently added",
                ]:
                    option = await self.page.query_selector(
                        f'li:has-text("{option_text}"), '
                        f'div[role="option"]:has-text("{option_text}")'
                    )
                    if option:
                        await option.click()
                        await wait_for_page_ready(
                            self.page, self.SEL_PROFILE_LINK, timeout=5000
                        )
                        break

        logger.info("Connections page loaded")
        return True

    async def scroll_connections_page(self, max_scrolls: int = 200) -> int:
        """Scroll connections page to load more entries via infinite scroll."""
        if not self.page:
            return 0

        previous_count = 0
        no_change_count = 0

        for i in range(max_scrolls):
            current_count = await self.page.evaluate("""
                () => {
                    const links = document.querySelectorAll('a[href*="/in/"]');
                    const urls = new Set();
                    links.forEach(a => {
                        const m = a.href.match(/\\/in\\/([^/?]+)/);
                        if (m) urls.add(m[1]);
                    });
                    return urls.size;
                }
            """)

            if current_count == previous_count:
                no_change_count += 1
                if no_change_count >= 3:
                    logger.info(
                        "No new connections after {i} scrolls, total: {n}",
                        i=i,
                        n=current_count,
                    )
                    break
            else:
                no_change_count = 0
                if i % 10 == 0:
                    logger.info(
                        "Scroll {i}: {n} connections loaded", i=i, n=current_count
                    )

            previous_count = current_count
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            # Short wait for lazy-load content
            await short_pause(300, 700)

            if i % 7 == 0:
                await random_mouse_move(self.page)

        return previous_count

    async def navigate_to_interests_page(
        self,
        profile_slug: str,
        scrolls_per_tab: int = 10,
        save_dir: str | None = None,
    ) -> bool:
        """Navigate to interests, click each tab, scroll, optionally save HTML.

        Args:
            profile_slug: LinkedIn profile slug.
            scrolls_per_tab: How many times to scroll down per tab.
            save_dir: If set, save HTML per tab here (debug only).
        """
        if not self.page:
            return False

        url = f"https://www.linkedin.com/in/{profile_slug}/details/interests/"
        try:
            ok = await self._goto(url, '[role="main"]', timeout=10000)
            if not ok:
                return False
        except Exception as e:
            logger.debug("Could not navigate to interests: {err}", err=str(e))
            return False

        # Count tabs
        tab_count = await self.page.evaluate("""
            () => document.querySelectorAll('div[role="radio"]').length
        """)

        if tab_count == 0:
            logger.debug("No interest tabs found")
            await self.scroll_interests_tab(scrolls_per_tab)
            return True

        for idx in range(tab_count):
            # Always re-query from DOM (clicking may re-render)
            tab_name = await self.page.evaluate(f"""
                () => {{
                    const tab = document.querySelectorAll('div[role="radio"]')[{idx}];
                    if (!tab) return null;
                    tab.click();
                    const label = tab.querySelector('label');
                    return label ? label.innerText.trim() : 'tab_{idx}';
                }}
            """)
            if not tab_name:
                continue

            await asyncio.sleep(0.5)

            # Scroll down
            await self.scroll_interests_tab(scrolls_per_tab)
            logger.info("Interests tab '{tab}': scrolled", tab=tab_name)

            # Save HTML (debug only)
            if save_dir:
                from pathlib import Path

                safe = tab_name.lower().replace(" ", "_")
                html = await self.get_page_content()
                path = Path(save_dir) / f"{profile_slug}_interests_{safe}.html"
                path.write_text(html, encoding="utf-8")
                logger.info("Saved {path} ({n} bytes)", path=str(path), n=len(html))

        return True

    # ======================== PROFILE SCRAPING ========================

    async def click_profile_link(self, profile_url: str) -> bool:
        """Navigate to a profile page. Waits for Topcard to load."""
        if not self.page:
            return False
        try:
            await random_mouse_move(self.page)
            await micro_pause()
            ok = await self._goto(profile_url, self.SEL_TOPCARD)
            if ok:
                await human_scroll(self.page, 1, 3)
            return ok
        except Exception as e:
            logger.error("Error navigating to profile: {err}", err=str(e))
            return False

    async def click_contact_info(self) -> str | None:
        """Click 'Kontaktinformationen' and return modal innerHTML."""
        if not self.page:
            return None

        try:
            contact_info_selectors = [
                'a[href*="/overlay/contact-info/"]',
                "#top-card-text-details-contact-info",
                'a:has-text("Kontaktinformationen")',
                'a:has-text("Contact info")',
            ]

            el = await wait_for_element(self.page, contact_info_selectors, timeout=3000)
            if not el:
                logger.debug("Contact info link not found")
                return None

            await move_mouse_to(self.page, el)
            await micro_pause()
            await el.click()

            # Wait for modal to appear (event-based)
            modal = await wait_for_element(
                self.page, self.SEL_MODAL.split(","), timeout=5000
            )
            modal_html = await modal.inner_html() if modal else None

            if not modal_html:
                modal_html = await self.page.content()

            # Close modal
            close_btn = await wait_for_element(
                self.page, self.SEL_MODAL_CLOSE.split(","), timeout=2000
            )
            if close_btn:
                await close_btn.click()
                await micro_pause()
            else:
                await self.page.keyboard.press("Escape")
                await micro_pause()

            return modal_html

        except Exception as e:
            logger.debug("Error getting contact info: {err}", err=str(e))
            with contextlib.suppress(Exception):
                await self.page.keyboard.press("Escape")
            return None

    async def extract_profile_sections(self) -> dict:
        """Extract profile data using componentkey selectors (JS)."""
        if not self.page:
            raise RuntimeError("Browser not started")

        from app.linkedin.scraper.profile_extractor import EXTRACT_SECTIONS_JS

        sections = await self.page.evaluate(EXTRACT_SECTIONS_JS)
        found = [k for k, v in sections.items() if v and not k.startswith("_")]
        logger.debug("Extracted sections: {found}", found=found)
        return sections

    async def extract_contact_info_from_modal(self) -> dict:
        """Extract contact info using JS from the currently open modal."""
        if not self.page:
            return {}
        from app.linkedin.scraper.profile_extractor import EXTRACT_CONTACT_INFO_JS

        return await self.page.evaluate(EXTRACT_CONTACT_INFO_JS)

    async def extract_interests_page(self) -> dict:
        """Extract interests from the currently loaded interests page."""
        if not self.page:
            return {}
        from app.linkedin.scraper.profile_extractor import EXTRACT_INTERESTS_JS

        return await self.page.evaluate(EXTRACT_INTERESTS_JS)

    # LinkedIn sets body { overflow: hidden } and uses <main> as
    # the actual scroll container (overflow: scroll). Neither keyboard
    # events nor window.scrollBy work. We must scroll <main> directly.

    _SCROLL_DOWN_JS = """
        (amount) => {
            const m = document.querySelector('main');
            if (m) { m.scrollBy(0, amount); return m.scrollTop; }
            return -1;
        }
    """
    _SCROLL_TO_JS = """
        (pos) => {
            const m = document.querySelector('main');
            if (m) { m.scrollTo(0, pos); return m.scrollTop; }
            return -1;
        }
    """
    _SCROLL_INFO_JS = """
        () => {
            const m = document.querySelector('main');
            if (!m) return null;
            return {
                scrollTop: m.scrollTop,
                scrollHeight: m.scrollHeight,
                clientHeight: m.clientHeight
            };
        }
    """

    async def scroll_profile_naturally(self) -> None:
        """Scroll profile down then back up to trigger lazy-loading.

        Scrolls <main> directly (LinkedIn uses body overflow:hidden).
        Down in steps over ~1s, wait 0.5s, back up over ~1s.
        """
        if not self.page:
            return

        info = await self.page.evaluate(self._SCROLL_INFO_JS)
        if not info:
            logger.warning("No <main> scroll container found")
            return

        # Scroll down in steps (~1s total)
        step_size = info["clientHeight"]
        total = info["scrollHeight"]
        pos = 0
        while pos < total:
            pos += step_size
            await self.page.evaluate(self._SCROLL_TO_JS, pos)
            await asyncio.sleep(0.15)

        await asyncio.sleep(0.5)

        # Scroll back up in steps (~1s total)
        while pos > 0:
            pos -= step_size
            await self.page.evaluate(self._SCROLL_TO_JS, max(0, pos))
            await asyncio.sleep(0.15)

        final = await self.page.evaluate(self._SCROLL_INFO_JS)
        logger.info(
            "Profile scroll complete: height={h}, clientH={c}",
            h=final["scrollHeight"] if final else "?",
            c=final["clientHeight"] if final else "?",
        )

    async def scroll_interests_tab(self, presses: int = 10) -> None:
        """Scroll an interests tab by scrolling <main> N times.

        Args:
            presses: Number of viewport-height scrolls.
        """
        if not self.page:
            return

        for _ in range(presses):
            info = await self.page.evaluate(self._SCROLL_INFO_JS)
            if not info:
                break
            await self.page.evaluate(
                self._SCROLL_DOWN_JS, int(info["clientHeight"] * 0.8)
            )
            await asyncio.sleep(0.3)

    # ======================== SEARCH ========================

    async def scroll_to_bottom(self) -> None:
        """Scroll to bottom of page to load all lazy content."""
        if not self.page:
            return

        prev_height = 0
        for i in range(20):
            height = await self.page.evaluate("document.body.scrollHeight")
            if height == prev_height:
                logger.debug("Reached bottom after {i} scrolls", i=i)
                break
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await short_pause(300, 700)
            prev_height = height

    async def click_next_page(self) -> bool:
        """Click next page button in search results."""
        if not self.page:
            return False

        try:
            next_selectors = [
                'button[aria-label="Next"]',
                'button[aria-label="Weiter"]',
                '[data-test-pagination-page-btn="next"]',
                ".search-results__pagination-next-button",
                "button.artdeco-pagination__button--next",
            ]

            for selector in next_selectors:
                btn = await self.page.query_selector(selector)
                if btn:
                    is_disabled = await btn.get_attribute("disabled")
                    if not is_disabled:
                        await move_mouse_to(self.page, btn)
                        await micro_pause()
                        await btn.click()
                        # Wait for new results to load
                        await wait_for_page_ready(
                            self.page, self.SEL_SEARCH_RESULTS, timeout=10000
                        )
                        logger.info("Clicked next page")
                        return True

            logger.info("No next page button found or disabled")
            return False

        except Exception as e:
            logger.error("Error clicking next page: {err}", err=str(e))
            return False

    # ======================== UTILITIES ========================

    async def get_page_content(self) -> str:
        if not self.page:
            raise RuntimeError("Browser not started")
        return await self.page.content()

    async def screenshot(self, filename: str = "screenshot.png") -> str:
        if not self.page:
            raise RuntimeError("Browser not started")
        path = self.session_dir / filename
        await self.page.screenshot(path=str(path))
        logger.debug("Screenshot saved: {path}", path=str(path))
        return str(path)

    def is_rate_limited(self, content: str) -> bool:
        """Check if page content indicates rate limiting."""
        strong = [
            "rate limit",
            "too many requests",
            "unusual activity",
            "security verification",
            "/checkpoint/challenge",
        ]
        content_lower = content.lower()
        if any(ind in content_lower for ind in strong):
            return True
        return "captcha" in content_lower and len(content) < 50000

    def is_login_required(self, url: str) -> bool:
        login_indicators = ["/login", "/checkpoint", "/authwall", "/uas/login"]
        return any(indicator in url.lower() for indicator in login_indicators)

    # ======================== LOGIN ========================

    async def login(
        self,
        email: str,
        password: str,
        wait_for_2fa_timeout: int = 300,
    ) -> dict:
        """Login to LinkedIn. Waits for 2FA/CAPTCHA via VNC if needed."""
        if not self.page:
            raise RuntimeError("Browser not started")

        try:
            logger.info("Starting login for {email}", email=email)

            await self._goto(self.LOGIN_URL, 'input[name="session_key"], #username')

            # Enter email
            email_input = await wait_for_element(
                self.page, 'input[name="session_key"], #username'
            )
            if email_input:
                await human_type_text(self.page, email_input, email)

            await micro_pause(200, 400)

            # Enter password
            password_input = await wait_for_element(
                self.page, 'input[name="session_password"], #password'
            )
            if password_input:
                await human_type_text(self.page, password_input, password)

            await micro_pause(200, 500)
            await random_mouse_move(self.page)

            # Click login button
            login_btn = await self.page.query_selector(
                'button[type="submit"], .login__form_action_container button'
            )
            if login_btn:
                await move_mouse_to(self.page, login_btn)
                await micro_pause()
                await login_btn.click()

            logger.info("Login form submitted, waiting for response...")

            # Wait for navigation result
            await wait_for_navigation(self.page, timeout=15000)
            url = self.page.url

            # Handle 2FA/CAPTCHA
            if "/checkpoint" in url or "/challenge" in url:
                logger.warning(
                    "2FA/CAPTCHA detected! Solve in VNC within {t}s",
                    t=wait_for_2fa_timeout,
                )
                import time

                start = time.time()
                while time.time() - start < wait_for_2fa_timeout:
                    import asyncio

                    await asyncio.sleep(2)
                    url = self.page.url
                    if "/feed" in url or "/sales" in url:
                        logger.info("2FA resolved!")
                        break
                    if "/checkpoint" not in url and "/challenge" not in url:
                        logger.info("Checkpoint passed")
                        break
                else:
                    return {
                        "success": False,
                        "error": "2FA/CAPTCHA timeout",
                        "needs_manual_intervention": True,
                    }

            # Check for login errors
            error_elem = await self.page.query_selector(
                '#error-for-password, .form__label--error, [data-test="login-error"]'
            )
            if error_elem:
                error_text = await error_elem.text_content()
                return {
                    "success": False,
                    "error": f"Login fehlgeschlagen: {error_text}",
                }

            url = self.page.url
            if self.is_login_required(url):
                return {
                    "success": False,
                    "error": "Login fehlgeschlagen - immer noch auf Login-Seite",
                }

            logger.info("Login successful!")
            session_data = await self.save_session()
            return {
                "success": True,
                "session_data": session_data,
                "message": "Login erfolgreich",
            }

        except Exception as e:
            logger.exception("Login error")
            return {"success": False, "error": f"Login-Fehler: {e!s}"}

    # ======================== OUTREACH ========================

    async def send_connection_request(
        self,
        profile_url: str,
        message: str | None = None,
    ) -> dict:
        """Send a connection request to a profile."""
        if not self.page:
            raise RuntimeError("Browser not started")

        try:
            logger.info("Sending connection request to {url}", url=profile_url)
            await self._goto(profile_url, self.SEL_TOPCARD)

            status = await self._get_connection_status()
            if status == "1st":
                return {
                    "success": False,
                    "error": "Bereits verbunden",
                    "already_connected": True,
                }
            if status == "pending":
                return {
                    "success": False,
                    "error": "Anfrage bereits gesendet",
                    "already_pending": True,
                }

            connect_btn = await self._find_connect_button()
            if not connect_btn:
                # Try "More" dropdown
                more_btn = await self.page.query_selector(
                    'button[aria-label*="Mehr"], button[aria-label*="More"]'
                )
                if more_btn:
                    await move_mouse_to(self.page, more_btn)
                    await more_btn.click()
                    await short_pause()
                    connect_btn = await self.page.query_selector(
                        '[data-control-name="connect"], '
                        'div[role="menuitem"]:has-text("Verbinden"), '
                        'div[role="menuitem"]:has-text("Connect")'
                    )

            if not connect_btn:
                return {"success": False, "error": "Connect-Button nicht gefunden"}

            await move_mouse_to(self.page, connect_btn)
            await micro_pause()
            await connect_btn.click()

            # Wait for connection modal
            await short_pause(300, 600)

            if message:
                add_note_btn = await wait_for_element(
                    self.page,
                    [
                        'button[aria-label*="Notiz hinzuf\u00fcgen"]',
                        'button[aria-label*="Add a note"]',
                        'button:has-text("Notiz hinzuf\u00fcgen")',
                        'button:has-text("Add a note")',
                    ],
                    timeout=3000,
                )
                if add_note_btn:
                    await add_note_btn.click()
                    await short_pause()

                    textarea = await wait_for_element(
                        self.page,
                        'textarea[name="message"], textarea#custom-message',
                        timeout=3000,
                    )
                    if textarea:
                        note = message[:300]
                        await human_type_text(self.page, textarea, note)

            # Click Send
            send_btn = await self.page.query_selector(
                'button[aria-label*="Senden"], '
                'button[aria-label*="Send"], '
                'button:has-text("Senden"):not([disabled]), '
                'button:has-text("Send invitation"):not([disabled]), '
                'button:has-text("Send"):not([disabled])'
            )
            if not send_btn:
                send_btn = await self.page.query_selector(
                    'button:has-text("Verbinden"):not([disabled]), '
                    'button:has-text("Connect"):not([disabled])'
                )

            if send_btn:
                await move_mouse_to(self.page, send_btn)
                await micro_pause()
                await send_btn.click()
                await short_pause(500, 1000)

                error_msg = await self.page.query_selector(
                    ".artdeco-toast--error, .error-message"
                )
                if error_msg:
                    error_text = await error_msg.text_content()
                    return {"success": False, "error": f"Fehler: {error_text}"}

                logger.info("Connection request sent successfully")
                return {"success": True, "message": "Verbindungsanfrage gesendet"}

            return {"success": False, "error": "Send-Button nicht gefunden"}

        except Exception as e:
            logger.exception("Error sending connection request")
            return {"success": False, "error": f"Fehler: {e!s}"}

    async def send_message(
        self,
        profile_url: str,
        content: str,
        subject: str | None = None,
    ) -> dict:
        """Send a direct message to a connection."""
        if not self.page:
            raise RuntimeError("Browser not started")

        try:
            logger.info("Sending message to {url}", url=profile_url)
            await self._goto(profile_url, self.SEL_TOPCARD)

            status = await self._get_connection_status()
            if status != "1st":
                return {
                    "success": False,
                    "error": f"Nicht verbunden (Status: {status})",
                    "not_connected": True,
                }

            message_btn = await self.page.query_selector(
                'button[aria-label*="Nachricht"], '
                'button[aria-label*="Message"], '
                'button:has-text("Nachricht"), '
                'button:has-text("Message")'
            )
            if not message_btn:
                return {"success": False, "error": "Message-Button nicht gefunden"}

            await move_mouse_to(self.page, message_btn)
            await micro_pause()
            await message_btn.click()

            # Wait for messaging window (event-based)
            msg_input = await wait_for_element(
                self.page,
                [
                    'div[role="textbox"][contenteditable="true"]',
                    "div.msg-form__contenteditable",
                    'textarea[name="message"]',
                ],
                timeout=10000,
            )
            if not msg_input:
                return {"success": False, "error": "Nachrichtenfeld nicht gefunden"}

            await human_type_text(self.page, msg_input, content)

            # Find and click Send
            send_btn = await self.page.query_selector(
                'button[type="submit"][aria-label*="Senden"], '
                'button[type="submit"][aria-label*="Send"], '
                "button.msg-form__send-button, "
                'button[aria-label*="Nachricht senden"], '
                'button[aria-label*="Send message"]'
            )
            if not send_btn:
                send_btn = await self.page.query_selector(
                    'button[type="submit"]:has-text("Senden"), '
                    'button[type="submit"]:has-text("Send")'
                )

            if send_btn:
                await move_mouse_to(self.page, send_btn)
                await micro_pause()
                await send_btn.click()
                await short_pause(500, 1000)

                error_msg = await self.page.query_selector(
                    ".artdeco-toast--error, .error-message"
                )
                if error_msg:
                    error_text = await error_msg.text_content()
                    return {"success": False, "error": f"Fehler: {error_text}"}

                logger.info("Message sent successfully")
                return {"success": True, "message": "Nachricht gesendet"}

            return {"success": False, "error": "Send-Button nicht gefunden"}

        except Exception as e:
            logger.exception("Error sending message")
            return {"success": False, "error": f"Fehler: {e!s}"}

    async def withdraw_connection_request(self, profile_url: str) -> dict:
        """Withdraw a pending connection request."""
        if not self.page:
            raise RuntimeError("Browser not started")

        try:
            logger.info("Withdrawing request for {url}", url=profile_url)
            await self._goto(profile_url, self.SEL_TOPCARD)

            pending_btn = await self.page.query_selector(
                'button[aria-label*="Ausstehend"], '
                'button[aria-label*="Pending"], '
                'button:has-text("Ausstehend"), '
                'button:has-text("Pending")'
            )
            if not pending_btn:
                return {"success": False, "error": "Keine ausstehende Anfrage gefunden"}

            await move_mouse_to(self.page, pending_btn)
            await pending_btn.click()
            await short_pause()

            withdraw_btn = await wait_for_element(
                self.page,
                [
                    'button:has-text("Zur\u00fcckziehen")',
                    'button:has-text("Withdraw")',
                    'div[role="menuitem"]:has-text("Zur\u00fcckziehen")',
                    'div[role="menuitem"]:has-text("Withdraw")',
                ],
                timeout=3000,
            )
            if withdraw_btn:
                await withdraw_btn.click()
                await short_pause(300, 600)
                logger.info("Connection request withdrawn")
                return {"success": True, "message": "Anfrage zur\u00fcckgezogen"}

            return {"success": False, "error": "Withdraw-Button nicht gefunden"}

        except Exception as e:
            logger.exception("Error withdrawing connection request")
            return {"success": False, "error": f"Fehler: {e!s}"}

    async def view_profile(self, profile_url: str) -> dict:
        """View a profile (for engagement/visibility)."""
        if not self.page:
            raise RuntimeError("Browser not started")

        try:
            await self._goto(profile_url, self.SEL_TOPCARD)
            await human_scroll(self.page, 2, 4)
            await random_mouse_move(self.page)

            name_elem = await self.page.query_selector(
                'h1.text-heading-xlarge, h1[data-anonymize="person-name"]'
            )
            name = await name_elem.text_content() if name_elem else "Unknown"

            headline_elem = await self.page.query_selector(
                'div.text-body-medium, div[data-anonymize="headline"]'
            )
            headline = await headline_elem.text_content() if headline_elem else None

            logger.info("Profile viewed: {name}", name=name)
            return {
                "success": True,
                "name": name.strip() if name else "Unknown",
                "headline": headline.strip() if headline else None,
            }

        except Exception as e:
            logger.exception("Error viewing profile")
            return {"success": False, "error": f"Fehler: {e!s}"}

    async def check_inbox_for_replies(self) -> list[dict]:
        """Check messaging inbox for new replies."""
        if not self.page:
            raise RuntimeError("Browser not started")

        try:
            await self._goto(
                "https://www.linkedin.com/messaging/",
                ".msg-conversation-card, [data-test-conversation-card]",
            )

            messages = []
            unread_items = await self.page.query_selector_all(
                ".msg-conversation-card--unread, "
                '[data-test-conversation-card][class*="unread"]'
            )

            for item in unread_items[:10]:
                try:
                    name_elem = await item.query_selector(
                        ".msg-conversation-card__participant-names, "
                        "[data-test-conversation-card-name]"
                    )
                    name = await name_elem.text_content() if name_elem else "Unknown"

                    preview_elem = await item.query_selector(
                        ".msg-conversation-card__message-snippet, "
                        "[data-test-conversation-card-snippet]"
                    )
                    preview = await preview_elem.text_content() if preview_elem else ""

                    link = await item.query_selector('a[href*="/in/"]')
                    profile_url = await link.get_attribute("href") if link else None

                    messages.append(
                        {
                            "profile_name": name.strip() if name else "Unknown",
                            "preview": preview.strip() if preview else "",
                            "profile_url": profile_url,
                        }
                    )
                except Exception as e:
                    logger.warning("Error parsing inbox item: {err}", err=str(e))

            logger.info("Found {count} unread messages", count=len(messages))
            return messages

        except Exception:
            logger.exception("Error checking inbox")
            return []

    # ======================== PRIVATE HELPERS ========================

    async def _get_connection_status(self) -> str:
        """Get connection status: '1st', '2nd', '3rd', 'pending', or 'none'."""
        if not self.page:
            return "none"
        try:
            degree_elem = await self.page.query_selector(
                '.dist-value, span[class*="degree-icon"], [data-test-distance-badge]'
            )
            if degree_elem:
                text = await degree_elem.text_content()
                if "1" in text:
                    return "1st"
                if "2" in text:
                    return "2nd"
                if "3" in text:
                    return "3rd"

            pending_btn = await self.page.query_selector(
                'button[aria-label*="Ausstehend"], '
                'button[aria-label*="Pending"], '
                'button:has-text("Ausstehend"), '
                'button:has-text("Pending")'
            )
            if pending_btn:
                return "pending"

            message_btn = await self.page.query_selector(
                'button[aria-label*="Nachricht"]:not([disabled]), '
                'button[aria-label*="Message"]:not([disabled])'
            )
            if message_btn:
                return "1st"

            return "none"
        except Exception:
            return "none"

    async def _find_connect_button(self):
        """Find the Connect button on a profile page."""
        if not self.page:
            return None

        selectors = [
            'button[aria-label*="Verbinden"]',
            'button[aria-label*="Connect"]',
            'button:has-text("Verbinden")',
            'button:has-text("Connect")',
            '[data-control-name="connect"]',
        ]
        for selector in selectors:
            try:
                btn = await self.page.query_selector(selector)
                if btn and not await btn.get_attribute("disabled"):
                    return btn
            except Exception:
                continue
        return None
