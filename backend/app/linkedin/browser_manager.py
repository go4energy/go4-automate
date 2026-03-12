"""Global browser manager — one browser per LinkedIn account.

All code (worker, debug router, etc.) uses the same browser instance.
The browser stays open until explicitly closed or the app shuts down.
"""

from __future__ import annotations

import contextlib
from datetime import datetime
from typing import TYPE_CHECKING

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from app.linkedin.scraper.browser import LinkedInBrowser


class BrowserManager:
    """Singleton manager for LinkedIn browser instances.

    One browser per account_id. Browser stays open between jobs,
    debug scrapes, and any other operation.
    """

    def __init__(self) -> None:
        self._browsers: dict[int, LinkedInBrowser] = {}
        self._account_emails: dict[int, str] = {}

    async def get_browser(
        self,
        account_id: int,
        account_email: str,
        session_data: dict | None = None,
        tenant_id: str = "",
    ) -> LinkedInBrowser:
        """Get or create a browser for the given account.

        If a browser already exists for this account, return it.
        Otherwise start a new one with the session data.
        """
        from app.linkedin.scraper.browser import LinkedInBrowser

        # Reuse existing browser
        if account_id in self._browsers:
            browser = self._browsers[account_id]
            # Check if browser is still alive (page not closed)
            if browser.page and not browser.page.is_closed():
                logger.info(
                    "Browser wiederverwendet: {email}", email=account_email
                )
                return browser
            else:
                # Browser died — clean up
                logger.warning(
                    "Browser für {email} war tot, starte neu",
                    email=account_email,
                )
                await self._cleanup_browser(account_id)

        # Start new browser
        logger.info("Starte neuen Browser: {email}", email=account_email)
        session_dir = f"sessions/{tenant_id}" if tenant_id else "sessions"
        browser = LinkedInBrowser(
            session_dir=session_dir,
            headless=False,
        )
        await browser.start(account_email, session_data)

        self._browsers[account_id] = browser
        self._account_emails[account_id] = account_email
        return browser

    def has_browser(self, account_id: int) -> bool:
        """Check if a browser exists for the given account."""
        if account_id not in self._browsers:
            return False
        browser = self._browsers[account_id]
        return browser.page is not None and not browser.page.is_closed()

    async def save_session(
        self,
        account_id: int,
        db: AsyncSession | None = None,
        account=None,
    ) -> dict | None:
        """Save the current browser session to file and optionally to DB.

        Args:
            account_id: The account ID
            db: Optional DB session to save session_data to account
            account: Optional account model to update
        """
        browser = self._browsers.get(account_id)
        if not browser:
            return None

        try:
            session_data = await browser.save_session()
            if session_data and db and account:
                account.session_data = session_data
                account.session_expires_at = datetime.fromisoformat(
                    session_data.get(
                        "expires_at", datetime.utcnow().isoformat()
                    )
                )
                await db.commit()
                logger.info(
                    "Session gespeichert in DB: {email}",
                    email=self._account_emails.get(account_id, "?"),
                )
            return session_data
        except Exception:
            logger.exception("Fehler beim Session-Speichern")
            return None

    async def close_browser(self, account_id: int) -> None:
        """Close a specific browser."""
        await self._cleanup_browser(account_id)

    async def close_all(self) -> None:
        """Close all browsers (app shutdown)."""
        for account_id in list(self._browsers.keys()):
            await self._cleanup_browser(account_id)

    async def _cleanup_browser(self, account_id: int) -> None:
        """Clean up a single browser instance."""
        browser = self._browsers.pop(account_id, None)
        self._account_emails.pop(account_id, None)
        if browser:
            with contextlib.suppress(Exception):
                await browser.stop()
            logger.info("Browser geschlossen: account_id={id}", id=account_id)


# Global singleton
browser_manager = BrowserManager()
