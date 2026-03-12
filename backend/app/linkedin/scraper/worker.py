"""LinkedIn scraper background worker.

Processes queued scraper jobs in the background with
human-like delays and rate limiting.
"""

import asyncio
import os
import random
from datetime import datetime

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.linkedin.browser_manager import browser_manager
from app.linkedin.debug_bridge import bridge
from app.linkedin.models import (
    LinkedInAccount,
    LinkedInContact,
    LinkedInJobLog,
    LinkedInScraperJob,
)
from app.linkedin.scraper.human_like import (
    human_delay,
    short_pause,
    wait_for_rate_limit_recovery,
)
from app.linkedin.scraper.parsers import (
    detect_pagination_info,
    extract_linkedin_id,
    is_rate_limited,
    normalize_linkedin_url,
    parse_connected_time_text,
    parse_connections_list,
    parse_contact_info_modal,
    parse_sales_navigator_profile,
    parse_search_results,
    split_name,
)
from app.linkedin.scraper.profile_extractor import extract_profile_from_sections


class LinkedInWorker:
    """Background worker for processing LinkedIn scraper jobs."""

    def __init__(self, db_session_factory, poll_interval: int = 30):
        """Initialize the worker.

        Args:
            db_session_factory: Async session factory for database access
            poll_interval: Seconds between job queue checks
        """
        self.db_session_factory = db_session_factory
        self.poll_interval = poll_interval
        self.running = False
        self.current_job_id: int | None = None
        self._task = None

    async def start(self) -> None:
        """Start the worker loop."""
        self.running = True
        logger.info("LinkedIn worker started")

        while self.running:
            try:
                await self._process_next_job()
            except Exception as e:
                logger.exception("Error in worker loop: {err}", err=str(e))

            await asyncio.sleep(self.poll_interval)

    async def stop(self) -> None:
        """Stop the worker gracefully.

        Note: Browser stays open (managed by browser_manager).
        """
        self.running = False
        logger.info("LinkedIn worker stopped")

    async def _process_next_job(self) -> bool:
        """Find and process the next queued job.

        Returns:
            True if a job was found and processed, False otherwise.
        """
        async with self.db_session_factory() as db:
            # Find next queued job
            result = await db.execute(
                select(LinkedInScraperJob)
                .options(selectinload(LinkedInScraperJob.account))
                .where(LinkedInScraperJob.status == "queued")
                .order_by(LinkedInScraperJob.created_at)
                .limit(1)
            )
            job = result.scalar_one_or_none()

            if not job:
                return False

            self.current_job_id = job.id
            logger.info("Processing job {id}: {name}", id=job.id, name=job.name)

            try:
                # Mark as running
                job.status = "running"
                job.started_at = datetime.utcnow()
                await db.commit()

                # Process based on job type
                if job.job_type == "search":
                    await self._process_search_job(db, job)
                elif job.job_type == "profile_list":
                    await self._process_profile_list_job(db, job)
                elif job.job_type == "connections":
                    await self._process_connections_job(db, job)

                # Mark as completed if not already paused/failed
                if job.status == "running":
                    job.status = "completed"
                    job.completed_at = datetime.utcnow()
                await db.commit()

                logger.info(
                    "Job {id} finished: {scraped}/{found} profiles",
                    id=job.id,
                    scraped=job.profiles_scraped,
                    found=job.profiles_found,
                )

            except Exception as e:
                logger.exception("Job {id} failed: {err}", id=job.id, err=str(e))
                job.status = "failed"
                job.error_message = str(e)[:500]
                job.retry_count += 1
                await db.commit()

            finally:
                self.current_job_id = None
                # Save session via browser_manager (browser stays open)
                if job.account_id and browser_manager.has_browser(job.account_id):
                    await browser_manager.save_session(
                        job.account_id, db=db, account=job.account
                    )

            return True

    async def _init_browser(
        self,
        db: AsyncSession,
        job: LinkedInScraperJob,
        skip_sales_navigator: bool = False,
    ) -> bool:
        """Initialize browser via global browser_manager.

        Args:
            db: Database session
            job: The scraper job
            skip_sales_navigator: If True, skip Sales Navigator navigation

        Returns:
            True if browser initialized successfully with valid session
        """
        # Get fresh account data
        account_result = await db.execute(
            select(LinkedInAccount).where(LinkedInAccount.id == job.account_id)
        )
        account = account_result.scalar_one()

        # Get or create browser via global manager
        already_open = browser_manager.has_browser(job.account_id)

        if not already_open and not await bridge.checkpoint(
            "browser_start", "Browser starten", f"Account: {account.email}"
        ):
            return False

        self.browser = await browser_manager.get_browser(
            account_id=job.account_id,
            account_email=account.email,
            session_data=account.session_data,
            tenant_id=account.tenant_id,
        )

        if already_open:
            await bridge.log("ok", f"Browser wiederverwendet: {account.email}")
        else:
            await bridge.log("ok", "Browser gestartet")

        # Check if session is valid
        if not await bridge.checkpoint(
            "session_check", "Session validieren", f"Login prüfen: {account.email}"
        ):
            return False

        is_valid = await self.browser.check_session_valid()
        if not is_valid:
            logger.warning("Session not valid for {email}", email=account.email)
            await bridge.log("warn", f"Session abgelaufen: {account.email}")

            # Auto-Login versuchen wenn Passwort gespeichert
            logged_in = await self._try_auto_login(db, account)
            if not logged_in:
                account.status = "session_expired"
                account.last_error = "Session abgelaufen - bitte neu einloggen"
                await db.commit()
                # Browser bleibt offen für manuellen Login!
                return False

        # Reactivate account if it was expired
        if account.status != "active":
            account.status = "active"
            account.last_error = None
            await db.commit()
            await bridge.log("ok", "Account reaktiviert")

        await bridge.log("ok", "Session ist gültig")

        # Save session to DB after successful validation
        await browser_manager.save_session(
            job.account_id, db=db, account=account
        )

        # Navigate to Sales Navigator if needed (skip for connections jobs)
        if account.is_sales_navigator and not skip_sales_navigator:
            if not await bridge.checkpoint("navigate_sn", "Sales Navigator öffnen", ""):
                return False

            nav_success = await self.browser.navigate_to_sales_navigator()
            if not nav_success:
                logger.error("Could not navigate to Sales Navigator")
                await bridge.log("error", "Sales Navigator nicht erreichbar")
                return False
            await bridge.log("ok", "Sales Navigator geöffnet")

        account.status = "active"
        account.last_login_at = datetime.utcnow()
        await db.commit()
        return True

    async def _try_auto_login(
        self, db: AsyncSession, account: LinkedInAccount
    ) -> bool:
        """Try auto-login with stored password.

        Returns True if login succeeded, False otherwise.
        Browser stays open in both cases.
        """
        if not account.password_encrypted:
            await bridge.log(
                "error",
                "Kein Passwort gespeichert — bitte im Browser manuell einloggen",
            )
            return False

        try:
            from app.linkedin.service import get_fernet

            fernet = get_fernet()
            password = fernet.decrypt(account.password_encrypted.encode()).decode()
        except Exception:
            await bridge.log("error", "Passwort konnte nicht entschlüsselt werden")
            return False

        await bridge.log("info", f"Auto-Login versuchen: {account.email}")

        if not await bridge.checkpoint(
            "auto_login", "Auto-Login", f"Einloggen als {account.email}"
        ):
            return False

        result = await self.browser.login(
            email=account.email,
            password=password,
            wait_for_2fa_timeout=120,
        )

        if result.get("success"):
            await bridge.log("ok", "Auto-Login erfolgreich!")
            # Session in DB speichern
            await browser_manager.save_session(
                account.id, db=db, account=account
            )
            account.status = "active"
            account.last_login_at = datetime.utcnow()
            account.last_error = None
            await db.commit()
            return True

        error = result.get("error", "Unbekannter Fehler")
        await bridge.log(
            "error",
            f"Auto-Login fehlgeschlagen: {error} — "
            "bitte im offenen Browser manuell einloggen",
        )
        return False

    async def _process_search_job(
        self, db: AsyncSession, job: LinkedInScraperJob
    ) -> None:
        """Process a search-based scraper job.

        Args:
            db: Database session
            job: The scraper job to process
        """
        if not job.search_url:
            logger.error("Job {id} has no search URL", id=job.id)
            job.status = "failed"
            job.error_message = "Keine Such-URL angegeben"
            return

        # Initialize browser
        if not await self._init_browser(db, job):
            job.status = "failed"
            job.error_message = "Browser-Session konnte nicht initialisiert werden"
            return

        # Navigate to search
        if not await bridge.checkpoint(
            "navigate_search", "Zur Suche navigieren", job.search_url[:80]
        ):
            return

        if not await self.browser.navigate_to_search(job.search_url):
            job.status = "failed"
            job.error_message = "Konnte nicht zur Suche navigieren"
            await bridge.log("error", "Such-Seite nicht erreichbar")
            return

        await bridge.log("ok", "Such-Seite geladen")

        # Get account for limits
        account_result = await db.execute(
            select(LinkedInAccount).where(LinkedInAccount.id == job.account_id)
        )
        account = account_result.scalar_one()

        # Resume from last page (current_page is the NEXT page to scrape)
        start_page = job.current_page if job.current_page > 1 else 1
        page_num = start_page

        pages_scraped_this_run = 0

        # Create job log entry
        job_log = LinkedInJobLog(
            tenant_id=job.tenant_id,
            job_id=job.id,
            started_at=datetime.utcnow(),
            start_page=start_page,
            status="running",
        )
        db.add(job_log)
        await db.flush()
        logger.info(
            "Job {id} starting from page {page}",
            id=job.id,
            page=start_page,
        )

        profiles_scraped_this_run = 0
        profiles_failed_this_run = 0
        profiles_skipped_this_run = 0
        error_message = None

        try:
            while self.running:
                # Check daily limits
                if account.profiles_scraped_today >= account.daily_profile_limit:
                    logger.warning(
                        "Daily limit reached for account {email}",
                        email=account.email,
                    )
                    await bridge.log("warning", "Account-Tageslimit erreicht")
                    job.status = "paused"
                    job.error_message = "Tageslimit des Accounts erreicht"
                    break

                if job.profiles_scraped >= job.daily_limit:
                    logger.info("Job daily limit reached")
                    await bridge.log("warning", "Job-Tageslimit erreicht")
                    job.status = "paused"
                    job.error_message = "Job-Tageslimit erreicht"
                    break

                if not await bridge.checkpoint(
                    f"search_page_{page_num}",
                    f"Seite {page_num} verarbeiten",
                    f"Bisher: {job.profiles_scraped} Profile",
                ):
                    break

                # Get page content
                html = await self.browser.get_page_content()

                # Check for rate limiting
                if is_rate_limited(html):
                    logger.warning("Rate limit detected")
                    await bridge.log("warning", "Rate-Limit erkannt!")
                    await wait_for_rate_limit_recovery()
                    account.status = "rate_limited"
                    await db.commit()
                    continue

                # Parse search results
                profiles = parse_search_results(html)
                if not profiles:
                    logger.warning("No profiles found on page {page}", page=page_num)
                    await bridge.log("warning", f"0 Profile auf Seite {page_num}")
                    # Take screenshot for debugging
                    await self.browser.screenshot(
                        f"job_{job.id}_page_{page_num}_empty.png"
                    )
                    break

                job.profiles_found += len(profiles)
                await bridge.log(
                    "info", f"Seite {page_num}: {len(profiles)} Profile gefunden"
                )
                logger.info(
                    "Found {count} profiles on page {page}",
                    count=len(profiles),
                    page=page_num,
                )

                # Save contacts
                for profile in profiles:
                    if job.profiles_scraped >= job.daily_limit:
                        break
                    if account.profiles_scraped_today >= account.daily_profile_limit:
                        break

                    try:
                        # Optionally scrape full profile page for detailed data
                        if job.scrape_full_profiles:
                            profile_url = profile.get(
                                "sales_navigator_url"
                            ) or profile.get("linkedin_url")
                            if profile_url:
                                await human_delay(
                                    job.min_delay_seconds,
                                    job.min_delay_seconds + 1,
                                )
                                if await self.browser.click_profile_link(profile_url):
                                    profile_html = await self.browser.get_page_content()
                                    if not is_rate_limited(profile_html):
                                        full_profile = parse_sales_navigator_profile(
                                            profile_html, profile_url
                                        )
                                        # Merge full profile data with search results
                                        profile.update(
                                            {
                                                k: v
                                                for k, v in full_profile.items()
                                                if v and not profile.get(k)
                                            }
                                        )
                                        # Overwrite with richer data
                                        profile["summary"] = full_profile.get("summary")
                                        profile["experience"] = full_profile.get(
                                            "experience"
                                        )
                                        profile["education"] = full_profile.get(
                                            "education"
                                        )
                                        profile["connection_count"] = full_profile.get(
                                            "connection_count"
                                        )
                                    else:
                                        logger.warning("Rate limited on profile page")
                                        await wait_for_rate_limit_recovery()
                                    # Navigate back to search
                                    await self.browser.navigate_to_search(
                                        job.search_url
                                    )

                        contact = await self._save_contact(db, job, profile)
                        if contact:
                            job.profiles_scraped += 1
                            profiles_scraped_this_run += 1
                            account.profiles_scraped_today += 1
                            account.total_profiles_scraped += 1
                            job.last_profile_url = profile.get("linkedin_url", "")
                        else:
                            # Duplicate contact (cross-job duplicate check)
                            profiles_skipped_this_run += 1
                        await db.commit()
                    except Exception as e:
                        logger.error("Error saving contact: {err}", err=str(e))
                        job.profiles_failed += 1
                        profiles_failed_this_run += 1

                # Page completed - update current_page to NEXT page
                pages_scraped_this_run += 1
                page_num += 1
                job.current_page = page_num  # Next page to scrape
                await db.commit()

                # Check for next page
                pagination = detect_pagination_info(html)
                if not pagination["has_next"]:
                    logger.info("No more pages - search exhausted")
                    break

                # Go to next page (browser waits for results to load)
                await human_delay(job.min_delay_seconds, job.min_delay_seconds + 1)
                if not await self.browser.click_next_page():
                    logger.info("Could not click next page")
                    break

        except Exception as e:
            logger.exception("Error in search job: {err}", err=str(e))
            error_message = str(e)[:500]

        finally:
            # Complete job log
            job_log.completed_at = datetime.utcnow()
            job_log.end_page = page_num - 1 if page_num > start_page else start_page
            job_log.profiles_scraped = profiles_scraped_this_run
            job_log.profiles_failed = profiles_failed_this_run
            job_log.profiles_skipped = profiles_skipped_this_run
            job_log.status = "failed" if error_message else "completed"
            job_log.error_message = error_message
            if job_log.started_at:
                duration = (job_log.completed_at - job_log.started_at).total_seconds()
                job_log.duration_seconds = int(duration)
            await db.commit()

            logger.info(
                "Job {id} run complete: pages {start}-{end}, "
                "{scraped} scraped, {failed} failed, {skipped} skipped",
                id=job.id,
                start=start_page,
                end=job_log.end_page,
                scraped=profiles_scraped_this_run,
                failed=profiles_failed_this_run,
                skipped=profiles_skipped_this_run,
            )

    async def _process_profile_list_job(
        self, db: AsyncSession, job: LinkedInScraperJob
    ) -> None:
        """Process a profile list scraper job.

        Args:
            db: Database session
            job: The scraper job to process
        """
        if not job.profile_urls:
            logger.warning("Job {id} has no profile URLs", id=job.id)
            return

        # Initialize browser
        if not await self._init_browser(db, job):
            job.status = "failed"
            job.error_message = "Browser-Session konnte nicht initialisiert werden"
            return

        # Get account for limits
        account_result = await db.execute(
            select(LinkedInAccount).where(LinkedInAccount.id == job.account_id)
        )
        account = account_result.scalar_one()

        job.profiles_found = len(job.profile_urls)

        # Filter out already-scraped URLs (check DB)
        already_scraped = set()
        for url in job.profile_urls:
            norm_url = normalize_linkedin_url(url)
            lid = extract_linkedin_id(url)
            existing = await db.execute(
                select(LinkedInContact.id).where(
                    LinkedInContact.tenant_id == job.tenant_id,
                    (
                        (LinkedInContact.linkedin_url == norm_url)
                        | (LinkedInContact.linkedin_id == lid)
                    ),
                ).limit(1)
            )
            if existing.scalar_one_or_none():
                already_scraped.add(url)

        remaining_urls = [
            u for u in job.profile_urls if u not in already_scraped
        ]

        if already_scraped:
            await bridge.log(
                "info",
                f"{len(already_scraped)} bereits in DB, "
                f"{len(remaining_urls)} neue Profile",
            )

        if not remaining_urls:
            await bridge.log("ok", "Alle Profile bereits in DB")
            return

        await bridge.log(
            "info",
            f"{len(remaining_urls)} Profile-URLs zu verarbeiten "
            f"(max: {job.max_profiles})",
        )

        scraped_this_run = 0
        for i, url in enumerate(remaining_urls):
            if not self.running:
                logger.info("Worker stopped, pausing job {id}", id=job.id)
                job.status = "paused"
                break

            # Check max_profiles limit (per run)
            if scraped_this_run >= job.max_profiles:
                await bridge.log(
                    "ok",
                    f"Max-Limit erreicht: {scraped_this_run}/{job.max_profiles}",
                )
                job.status = "paused"
                job.error_message = f"Max-Limit erreicht ({job.max_profiles})"
                break

            # Check daily limits
            if account.profiles_scraped_today >= account.daily_profile_limit:
                logger.warning(
                    "Daily limit reached for account {email}",
                    email=account.email,
                )
                await bridge.log("warning", "Account-Tageslimit erreicht")
                job.status = "paused"
                job.error_message = "Tageslimit erreicht"
                break

            if scraped_this_run >= job.daily_limit:
                logger.info("Job daily limit reached")
                await bridge.log("warning", "Job-Tageslimit erreicht")
                job.status = "paused"
                job.error_message = "Job-Tageslimit erreicht"
                break

            if not await bridge.checkpoint(
                f"profile_list_{i}",
                f"Profil öffnen ({i + 1}/{len(remaining_urls)})",
                url[:80],
            ):
                break

            try:
                # Navigate to profile
                if not await self.browser.click_profile_link(url):
                    logger.error("Could not navigate to {url}", url=url)
                    await bridge.log("error", f"Fehler: {url[:60]}")
                    job.profiles_failed += 1
                    continue

                # Get page content
                html = await self.browser.get_page_content()

                # Check for rate limiting
                if is_rate_limited(html):
                    await bridge.log("warning", "Rate-Limit auf Profil!")
                    await wait_for_rate_limit_recovery()
                    account.status = "rate_limited"
                    account.last_error = "Rate-Limit erreicht"
                    await db.commit()
                    continue

                # Parse full profile data using the Sales Navigator parser
                profile_data = parse_sales_navigator_profile(html, url)

                # Ensure we have the URL even if parsing failed
                if not profile_data.get("linkedin_url"):
                    profile_data["linkedin_url"] = normalize_linkedin_url(url)
                if not profile_data.get("linkedin_id"):
                    profile_data["linkedin_id"] = extract_linkedin_id(url)
                if not profile_data.get("sales_navigator_url"):
                    profile_data["sales_navigator_url"] = url

                contact = await self._save_contact(db, job, profile_data)
                if contact:
                    scraped_this_run += 1
                    job.profiles_scraped += 1
                    account.profiles_scraped_today += 1
                    account.total_profiles_scraped += 1
                    job.last_profile_url = url
                    await bridge.log(
                        "ok", f"Gespeichert: {profile_data.get('name', 'N/A')}"
                    )
                else:
                    await bridge.log(
                        "info", f"Duplikat: {profile_data.get('name', url[:40])}"
                    )

                await db.commit()

                # Anti-detection delay between profiles
                await human_delay(job.min_delay_seconds, job.min_delay_seconds + 1)

            except Exception as e:
                logger.error("Error scraping {url}: {err}", url=url, err=str(e))
                await bridge.log("error", f"Fehler bei {url[:60]}: {e}")
                job.profiles_failed += 1

                # Check for rate limiting
                if "rate" in str(e).lower() or "blocked" in str(e).lower():
                    await wait_for_rate_limit_recovery()
                    account.status = "rate_limited"
                    account.last_error = str(e)

                await db.commit()

    async def _process_connections_job(
        self, db: AsyncSession, job: LinkedInScraperJob
    ) -> None:
        """Process a connections scraper job (1st-degree contacts).

        Two-pass approach:
        1. Scroll connections page to collect all profile URLs
        2. Visit each profile to scrape detailed data + contact info

        Args:
            db: Database session
            job: The scraper job to process
        """
        # Initialize browser (skip Sales Navigator - connections page is regular LI)
        if not await self._init_browser(db, job, skip_sales_navigator=True):
            job.status = "failed"
            job.error_message = "Browser-Session konnte nicht initialisiert werden"
            return

        # Navigate to connections page
        if not await bridge.checkpoint(
            "navigate_connections",
            "Zur Kontakte-Seite navigieren",
            "https://www.linkedin.com/mynetwork/invite-connect/connections/",
        ):
            return

        if not await self.browser.navigate_to_connections():
            job.status = "failed"
            job.error_message = "Konnte nicht zur Kontakte-Seite navigieren"
            await bridge.log("error", "Connections-Seite nicht erreichbar")
            return

        await bridge.log("ok", "Connections-Seite geladen")

        # Dump HTML for parser debugging
        if self.browser and self.browser.page:
            try:
                dump_html = await self.browser.get_page_content()
                dump_path = os.path.join(
                    os.path.dirname(
                        os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                    ),
                    "logs",
                    "connections_page.html",
                )
                with open(dump_path, "w", encoding="utf-8") as f:
                    f.write(dump_html)
                await bridge.log("debug", f"HTML-Dump gespeichert: {dump_path}")
            except Exception as e:
                await bridge.log("warning", f"HTML-Dump fehlgeschlagen: {e}")

        # Get account for limits
        account_result = await db.execute(
            select(LinkedInAccount).where(LinkedInAccount.id == job.account_id)
        )
        account = account_result.scalar_one()

        # Create job log
        job_log = LinkedInJobLog(
            tenant_id=job.tenant_id,
            job_id=job.id,
            started_at=datetime.utcnow(),
            start_page=1,
            status="running",
        )
        db.add(job_log)
        await db.flush()

        profiles_scraped_this_run = 0
        profiles_failed_this_run = 0
        profiles_skipped_this_run = 0
        error_message = None

        try:
            # ===== PASS 1: Scroll and collect connection URLs =====
            if not await bridge.checkpoint(
                "pass1_start",
                "Pass 1: URLs sammeln",
                "Scrolle Kontakte-Seite und sammle Profil-URLs",
            ):
                return

            collected_urls = []
            seen_urls = set()
            cutoff_reached = False

            # Scroll in batches
            for scroll_batch in range(50):  # Max 50 batches
                if not self.running:
                    break

                if not await bridge.checkpoint(
                    f"scroll_{scroll_batch}",
                    f"Scroll-Batch {scroll_batch + 1}",
                    f"Bisher: {len(collected_urls)} URLs",
                ):
                    break

                # Scroll a few times
                await self.browser.scroll_connections_page(max_scrolls=5)

                # Get current page and parse
                html = await self.browser.get_page_content()

                if is_rate_limited(html):
                    logger.warning("Rate limit detected during scroll")
                    await bridge.log("warning", "Rate-Limit erkannt!")
                    await wait_for_rate_limit_recovery()
                    continue

                connections = parse_connections_list(html)

                new_found = 0
                for conn in connections:
                    url = conn.get("linkedin_url", "")
                    if not url or url in seen_urls:
                        continue
                    seen_urls.add(url)
                    new_found += 1

                    # Check cutoff date if set
                    if job.connections_since_date and conn.get("connected_at_text"):
                        connected_date = parse_connected_time_text(
                            conn["connected_at_text"]
                        )
                        if (
                            connected_date
                            and connected_date < job.connections_since_date
                        ):
                            logger.info(
                                "Reached cutoff date at connection: {name}",
                                name=conn.get("name", ""),
                            )
                            cutoff_reached = True
                            break

                    collected_urls.append(conn)

                await bridge.log(
                    "info",
                    f"Batch {scroll_batch + 1}: {new_found} neue, "
                    f"{len(collected_urls)} gesamt",
                )

                if cutoff_reached or new_found == 0:
                    if new_found == 0:
                        await bridge.log("info", "Keine neuen Kontakte gefunden")
                    break

            job.profiles_found = len(collected_urls)
            await db.commit()
            await bridge.log(
                "ok", f"Pass 1 fertig: {len(collected_urls)} URLs gesammelt"
            )

            if not collected_urls:
                await bridge.log("warning", "0 Kontakte — Selektoren prüfen!")
                # Dump DOM info for debugging
                if self.browser and self.browser.page:
                    dom = await self.browser.page.evaluate("""
                        () => {
                            const all = document.querySelectorAll('a[href*="/in/"]');
                            const items = [];
                            for (let i = 0; i < Math.min(10, all.length); i++) {
                                items.push({
                                    href: all[i].href,
                                    text: all[i].textContent.trim().substring(0, 60),
                                    parentHtml: (all[i].closest('li') || all[i].parentElement)
                                        ?.outerHTML?.substring(0, 300) || '',
                                });
                            }
                            return { count: all.length, items };
                        }
                    """)
                    await bridge.log("debug", f"Profil-Links auf Seite: {dom['count']}")
                    for item in dom.get("items", []):
                        await bridge.log(
                            "debug", f"  {item['text']} → {item['href'][:60]}"
                        )
                        await bridge.log(
                            "debug", f"  Parent: {item['parentHtml'][:200]}"
                        )
                return

            # ===== PASS 2: Visit each profile for detailed scraping =====
            # Filter out already-scraped URLs (check DB, not numeric offset)
            already_scraped = set()
            for conn in collected_urls:
                url = normalize_linkedin_url(conn["linkedin_url"])
                lid = conn.get("linkedin_id") or extract_linkedin_id(url)
                existing = await db.execute(
                    select(LinkedInContact.id).where(
                        LinkedInContact.tenant_id == job.tenant_id,
                        (
                            (LinkedInContact.linkedin_url == url)
                            | (LinkedInContact.linkedin_id == lid)
                        ),
                    ).limit(1)
                )
                if existing.scalar_one_or_none():
                    already_scraped.add(url)

            remaining = [
                c for c in collected_urls
                if normalize_linkedin_url(c["linkedin_url"]) not in already_scraped
            ]

            if already_scraped:
                await bridge.log(
                    "info",
                    f"{len(already_scraped)} bereits in DB, "
                    f"{len(remaining)} neue Profile",
                )

            if not remaining:
                await bridge.log("ok", "Alle Profile bereits in DB")
                return

            if not await bridge.checkpoint(
                "pass2_start",
                f"Pass 2: {len(remaining)} Profile scrapen",
                f"Gesamt: {len(collected_urls)}, übersprungen: {len(already_scraped)}, "
                f"max: {job.max_profiles}",
            ):
                return

            scraped_this_run = 0
            for i, conn_data in enumerate(remaining):
                if not self.running:
                    job.status = "paused"
                    break

                # Check max_profiles limit (per run)
                if scraped_this_run >= job.max_profiles:
                    logger.info(
                        "Max profiles reached: {scraped}/{max}",
                        scraped=scraped_this_run,
                        max=job.max_profiles,
                    )
                    await bridge.log(
                        "ok",
                        f"Max-Limit erreicht: {scraped_this_run}/{job.max_profiles}",
                    )
                    job.status = "paused"
                    job.error_message = f"Max-Limit erreicht ({job.max_profiles})"
                    break

                # Check daily limits
                if account.profiles_scraped_today >= account.daily_profile_limit:
                    logger.warning(
                        "Daily limit reached for account {email}",
                        email=account.email,
                    )
                    await bridge.log("warning", "Account-Tageslimit erreicht")
                    job.status = "paused"
                    job.error_message = "Tageslimit des Accounts erreicht"
                    break

                if scraped_this_run >= job.daily_limit:
                    logger.info("Job daily limit reached")
                    await bridge.log("warning", "Job-Tageslimit erreicht")
                    job.status = "paused"
                    job.error_message = "Job-Tageslimit erreicht"
                    break

                profile_url = conn_data["linkedin_url"]
                profile_name = conn_data.get("name", "Unbekannt")

                if not await bridge.checkpoint(
                    f"profile_{i}",
                    f"Profil öffnen ({i + 1}/{len(remaining)})",
                    f"{profile_name} — {profile_url}",
                ):
                    break

                try:
                    # --- Step 1: Navigate to profile ---
                    if not await self.browser.click_profile_link(profile_url):
                        logger.error("Could not navigate to {url}", url=profile_url)
                        await bridge.log("error", f"Fehler: {profile_url}")
                        profiles_failed_this_run += 1
                        job.profiles_failed += 1
                        continue

                    # Check for rate limiting
                    html = await self.browser.get_page_content()
                    if is_rate_limited(html):
                        await bridge.log("warning", "Rate-Limit auf Profil!")
                        await wait_for_rate_limit_recovery()
                        account.status = "rate_limited"
                        await db.commit()
                        continue

                    # --- Step 2: Scroll through profile naturally ---
                    await self.browser.scroll_profile_naturally()

                    # --- Step 3: Extract sections via componentkey JS ---
                    sections = await self.browser.extract_profile_sections()
                    profile_data = extract_profile_from_sections(sections)

                    await bridge.log(
                        "info",
                        f"Profil: {profile_data.get('name', 'N/A')} | "
                        f"{profile_data.get('headline', '')[:50]} | "
                        f"Exp:{len(profile_data.get('experience', []))} "
                        f"Edu:{len(profile_data.get('education', []))} "
                        f"Skills:{len(profile_data.get('skills', []))}",
                    )

                    # Merge with data from connections list (Pass 1)
                    merge_keys = (
                        "name",
                        "first_name",
                        "last_name",
                        "headline",
                        "profile_picture_url",
                        "profile_urn",
                        "messaging_url",
                        "connected_at_text",
                    )
                    for key in merge_keys:
                        if conn_data.get(key) and not profile_data.get(key):
                            profile_data[key] = conn_data[key]
                    profile_data["contact_degree"] = 1
                    profile_data["linkedin_url"] = profile_url
                    profile_data["linkedin_id"] = conn_data.get(
                        "linkedin_id"
                    ) or extract_linkedin_id(profile_url)

                    # Parse connected_at datetime from text
                    if conn_data.get("connected_at_text"):
                        profile_data["connected_at"] = parse_connected_time_text(
                            conn_data["connected_at_text"]
                        )

                    # --- Step 4: Open contact info modal ---
                    if not await bridge.checkpoint(
                        f"contact_info_{i}",
                        f"Kontaktinfo ({i + 1}/{len(remaining)})",
                        f"Klicke 'Kontaktinformationen' für {profile_name}",
                    ):
                        break

                    contact_html = await self.browser.click_contact_info()
                    if contact_html:
                        # Extract via JS (more reliable than HTML parsing)
                        contact_info = (
                            await self.browser.extract_contact_info_from_modal()
                        )
                        # Also try old HTML parser as fallback
                        if not contact_info.get("email"):
                            old_info = parse_contact_info_modal(contact_html)
                            for k, v in old_info.items():
                                if v and not contact_info.get(k):
                                    contact_info[k] = v
                        # Merge contact info
                        for key, value in contact_info.items():
                            if value and not profile_data.get(key):
                                profile_data[key] = value
                        await bridge.log(
                            "info",
                            f"Kontaktinfo: Email={contact_info.get('email', '-')}, "
                            f"Phone={contact_info.get('phone', '-')}",
                        )
                    else:
                        await bridge.log("info", "Keine Kontaktinfo verfügbar")

                    # --- Step 5: Visit interests page (optional) ---
                    profile_slug = profile_url.rstrip("/").split("/")[-1]
                    if await self.browser.navigate_to_interests_page(profile_slug):
                        interests = await self.browser.extract_interests_page()
                        if any(interests.get(k) for k in interests):
                            profile_data["interests"] = interests
                            await bridge.log(
                                "info",
                                f"Interessen: {sum(len(v) for v in interests.values())} Einträge",
                            )
                    else:
                        await bridge.log("info", "Interessen-Seite nicht verfügbar")

                    # --- Step 6: Save contact ---
                    contact = await self._save_contact(db, job, profile_data)
                    if contact:
                        profiles_scraped_this_run += 1
                        scraped_this_run += 1
                        job.profiles_scraped += 1
                        account.profiles_scraped_today += 1
                        account.total_profiles_scraped += 1
                        job.last_profile_url = profile_url
                        await bridge.log(
                            "ok",
                            f"Gespeichert: {profile_data.get('name', 'N/A')}",
                        )
                    else:
                        profiles_skipped_this_run += 1
                        await bridge.log(
                            "info",
                            f"Duplikat: {profile_data.get('name', 'N/A')}",
                        )

                    await db.commit()

                    # --- Step 7: Back to connections list, scroll, then next ---
                    if i < len(remaining) - 1:
                        await self.browser._goto(
                            "https://www.linkedin.com/mynetwork/invite-connect/connections/",
                            self.browser.SEL_PROFILE_LINK,
                            timeout=10000,
                        )
                        # Scroll 1-2 times like browsing the list
                        for _ in range(random.randint(1, 2)):
                            await self.browser.page.evaluate(
                                f"window.scrollBy(0, {random.randint(300, 600)})"
                            )
                            await short_pause()
                        await human_delay(
                            job.min_delay_seconds,
                            job.max_delay_seconds,
                        )

                except Exception as e:
                    logger.error(
                        "Error scraping profile {url}: {err}",
                        url=profile_url,
                        err=str(e),
                    )
                    await bridge.log("error", f"Fehler bei {profile_url}: {e}")
                    profiles_failed_this_run += 1
                    job.profiles_failed += 1

                    if "rate" in str(e).lower() or "blocked" in str(e).lower():
                        await wait_for_rate_limit_recovery()
                        account.status = "rate_limited"
                    await db.commit()

        except Exception as e:
            logger.exception("Error in connections job: {err}", err=str(e))
            error_message = str(e)[:500]

        finally:
            job_log.completed_at = datetime.utcnow()
            job_log.end_page = 1
            job_log.profiles_scraped = profiles_scraped_this_run
            job_log.profiles_failed = profiles_failed_this_run
            job_log.profiles_skipped = profiles_skipped_this_run
            job_log.status = "failed" if error_message else "completed"
            job_log.error_message = error_message
            if job_log.started_at:
                duration = (job_log.completed_at - job_log.started_at).total_seconds()
                job_log.duration_seconds = int(duration)
            await db.commit()

            logger.info(
                "Job {id} connections complete: {scraped} scraped, "
                "{failed} failed, {skipped} skipped",
                id=job.id,
                scraped=profiles_scraped_this_run,
                failed=profiles_failed_this_run,
                skipped=profiles_skipped_this_run,
            )

    async def _save_contact(
        self, db: AsyncSession, job: LinkedInScraperJob, profile_data: dict
    ) -> LinkedInContact | None:
        """Save scraped contact to database.

        Args:
            db: Database session
            job: The scraper job
            profile_data: Parsed profile data

        Returns:
            Created contact record or None if duplicate
        """
        linkedin_url = profile_data.get("linkedin_url", "")
        linkedin_id = profile_data.get("linkedin_id") or extract_linkedin_id(
            linkedin_url
        )

        # Check for duplicate by LinkedIn URL or ID
        if linkedin_url or linkedin_id:
            existing = await db.execute(
                select(LinkedInContact).where(
                    LinkedInContact.tenant_id == job.tenant_id,
                    (
                        (LinkedInContact.linkedin_url == linkedin_url)
                        | (LinkedInContact.linkedin_id == linkedin_id)
                    ),
                )
            )
            if existing.scalar_one_or_none():
                logger.debug("Duplicate contact: {url}", url=linkedin_url)
                return None

        first_name, last_name = split_name(profile_data.get("name", ""))

        contact = LinkedInContact(
            tenant_id=job.tenant_id,
            scraper_job_id=job.id,
            linkedin_url=normalize_linkedin_url(linkedin_url),
            linkedin_id=linkedin_id,
            profile_urn=profile_data.get("profile_urn"),
            sales_navigator_url=profile_data.get("sales_navigator_url"),
            name=profile_data.get("name", "Unknown"),
            first_name=first_name,
            last_name=last_name,
            headline=profile_data.get("headline"),
            position=profile_data.get("position"),
            location=profile_data.get("location"),
            profile_picture_url=profile_data.get("profile_picture_url"),
            # Extended profile data
            contact_degree=profile_data.get("contact_degree"),
            is_premium=profile_data.get("is_premium", False),
            gender=profile_data.get("gender"),
            is_followed=profile_data.get("is_followed", False),
            follower_count=profile_data.get("follower_count"),
            connection_count=profile_data.get("connection_count"),
            # Company info
            company_name=profile_data.get("company_name"),
            company_linkedin_url=profile_data.get("company_linkedin_url"),
            company_size=profile_data.get("company_size"),
            company_industry=profile_data.get("company_industry"),
            # Contact info
            email=profile_data.get("email"),
            phone=profile_data.get("phone"),
            # Summary and structured data
            summary=profile_data.get("summary") or profile_data.get("about"),
            connected_at=profile_data.get("connected_at"),
            connected_at_text=profile_data.get("connected_at_text"),
            experience=profile_data.get("experience"),
            education=profile_data.get("education"),
            skills=profile_data.get("skills"),
            languages=profile_data.get("languages"),
            interests=profile_data.get("interests"),
            raw_data={
                k: (v.isoformat() if isinstance(v, datetime) else v)
                for k, v in profile_data.items()
                if k != "_raw_sections"  # exclude verbose debug data
            },
            status="scraped",
        )
        db.add(contact)
        await db.flush()
        logger.debug("Saved contact: {name}", name=contact.name)
        return contact


# Singleton worker instance
_worker: LinkedInWorker | None = None


def get_worker() -> LinkedInWorker | None:
    """Get the singleton worker instance."""
    return _worker


async def start_worker(db_session_factory) -> LinkedInWorker:
    """Start the background worker.

    Args:
        db_session_factory: Async session factory

    Returns:
        The worker instance
    """
    global _worker
    if _worker is None:
        _worker = LinkedInWorker(db_session_factory)
        _worker._task = asyncio.create_task(_worker.start())
    return _worker


async def stop_worker() -> None:
    """Stop the background worker."""
    global _worker
    if _worker is not None:
        await _worker.stop()
        if _worker._task:
            _worker._task.cancel()
            import contextlib

            with contextlib.suppress(asyncio.CancelledError):
                await _worker._task
        _worker = None


async def process_job_now(db_session_factory, job_id: int) -> dict:
    """Process a specific job immediately (for testing).

    Args:
        db_session_factory: Async session factory
        job_id: Job ID to process

    Returns:
        Result dictionary
    """
    worker = LinkedInWorker(db_session_factory, poll_interval=0)

    async with db_session_factory() as db:
        result = await db.execute(
            select(LinkedInScraperJob)
            .options(selectinload(LinkedInScraperJob.account))
            .where(LinkedInScraperJob.id == job_id)
        )
        job = result.scalar_one_or_none()

        if not job:
            return {"error": "Job nicht gefunden"}

        if job.status not in ("draft", "queued", "paused"):
            return {"error": f"Job hat falschen Status: {job.status}"}

        # Set to queued so worker picks it up
        job.status = "queued"
        await db.commit()

    # Process the job
    worker.running = True
    await worker._process_next_job()
    worker.running = False

    async with db_session_factory() as db:
        result = await db.execute(
            select(LinkedInScraperJob).where(LinkedInScraperJob.id == job_id)
        )
        job = result.scalar_one()

        return {
            "status": job.status,
            "profiles_found": job.profiles_found,
            "profiles_scraped": job.profiles_scraped,
            "profiles_failed": job.profiles_failed,
            "error_message": job.error_message,
        }
