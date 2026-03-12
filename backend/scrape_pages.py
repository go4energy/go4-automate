#!/usr/bin/env python
"""Scrape multiple pages of LinkedIn Sales Navigator search results."""

import asyncio
import os
import sys

sys.path.insert(0, "/opt/go4-automate/backend")
os.environ["DISPLAY"] = ":1"

from dotenv import load_dotenv

load_dotenv()

from datetime import datetime

from playwright.async_api import async_playwright
from sqlalchemy import select

from app.database import async_session
from app.linkedin.models import LinkedInAccount, LinkedInContact, LinkedInScraperJob
from app.linkedin.scraper.human_like import human_delay, human_scroll
from app.linkedin.scraper.parsers import parse_search_results

MAX_PAGES = 10


async def main():
    print("=" * 60)
    print(f"LinkedIn Scraper - {MAX_PAGES} Seiten")
    print("=" * 60)

    # Get job and account
    async with async_session() as db:
        result = await db.execute(
            select(LinkedInScraperJob).where(LinkedInScraperJob.id == 2)
        )
        job = result.scalar_one()
        search_url = job.search_url

        result = await db.execute(
            select(LinkedInAccount).where(LinkedInAccount.id == 4)
        )
        account = result.scalar_one()
        session_data = account.session_data

    storage_state = session_data.get("storage_state")
    if not storage_state:
        print("FEHLER: Keine Session!")
        return

    print(f"\nJob: {job.name}")
    print(f"Cookies: {len(storage_state.get('cookies', []))}")

    # Start browser
    print("\nStarte Browser...")
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=False,
        args=["--no-sandbox", "--start-maximized"],
    )
    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        storage_state=storage_state,
    )
    page = await context.new_page()

    # Navigate to search
    print("Navigiere zur Suche...")
    await page.goto(search_url, wait_until="domcontentloaded")
    await human_delay(3, 5)

    total_contacts = 0
    all_contacts = []

    for page_num in range(1, MAX_PAGES + 1):
        print(f"\n{'='*40}")
        print(f"SEITE {page_num}/{MAX_PAGES}")
        print(f"{'='*40}")

        # Scroll to load all results
        print("Scrolle durch die Seite...")
        await human_scroll(page)
        await human_delay(2, 3)

        # Parse results
        html = await page.content()
        contacts = parse_search_results(html)
        print(f"Gefunden: {len(contacts)} Profile")

        # Show contacts
        for i, c in enumerate(contacts[:5]):
            print(f"  {i+1}. {c.get('name', 'N/A')} - {c.get('company_name', '')}")
        if len(contacts) > 5:
            print(f"  ... und {len(contacts)-5} weitere")

        # Filter duplicates
        new_contacts = []
        existing_urls = {c.get("linkedin_url") for c in all_contacts}
        for c in contacts:
            if c.get("linkedin_url") and c.get("linkedin_url") not in existing_urls:
                new_contacts.append(c)
                existing_urls.add(c.get("linkedin_url"))

        all_contacts.extend(new_contacts)
        total_contacts += len(new_contacts)
        print(f"Neu: {len(new_contacts)} | Gesamt: {total_contacts}")

        # Save to database
        if new_contacts:
            async with async_session() as db:
                for contact_data in new_contacts:
                    contact = LinkedInContact(
                        tenant_id="go4energy",
                        scraper_job_id=2,
                        linkedin_url=contact_data.get("linkedin_url", ""),
                        linkedin_id=contact_data.get("linkedin_id", ""),
                        name=contact_data.get("name", ""),
                        first_name=contact_data.get("first_name", ""),
                        last_name=contact_data.get("last_name", ""),
                        headline=contact_data.get("headline", ""),
                        position=contact_data.get("position", ""),
                        location=contact_data.get("location", ""),
                        company_name=contact_data.get("company_name", ""),
                        company_linkedin_url=contact_data.get("company_linkedin_url"),
                        contact_degree=contact_data.get("contact_degree"),
                        is_premium=contact_data.get("is_premium", False),
                        status="scraped",
                    )
                    db.add(contact)
                await db.commit()
            print("Gespeichert!")

        # Go to next page
        if page_num < MAX_PAGES:
            print("\nWarte vor nächster Seite...")
            await human_delay(5, 10)

            # Find and click next button
            next_button = await page.query_selector('button[aria-label="Weiter"]')
            if not next_button:
                next_button = await page.query_selector('button[aria-label="Next"]')
            if not next_button:
                next_button = await page.query_selector('button.artdeco-pagination__button--next')

            if next_button:
                is_disabled = await next_button.get_attribute("disabled")
                if is_disabled:
                    print("Keine weiteren Seiten verfügbar!")
                    break
                print("Klicke 'Weiter'...")
                await next_button.click()
                await page.wait_for_load_state("domcontentloaded")
                await human_delay(3, 5)
            else:
                print("Weiter-Button nicht gefunden!")
                break

    # Update job stats
    print(f"\n{'='*60}")
    print(f"FERTIG: {total_contacts} Kontakte gescraped")
    print(f"{'='*60}")

    async with async_session() as db:
        result = await db.execute(
            select(LinkedInScraperJob).where(LinkedInScraperJob.id == 2)
        )
        job = result.scalar_one()
        job.profiles_found = total_contacts
        job.profiles_scraped = total_contacts
        job.current_page = page_num
        job.status = "completed"
        job.completed_at = datetime.utcnow()
        await db.commit()

    # Save session
    print("\nSpeichere Session...")
    new_storage = await context.storage_state()
    async with async_session() as db:
        result = await db.execute(
            select(LinkedInAccount).where(LinkedInAccount.id == 4)
        )
        account = result.scalar_one()
        account.session_data = {
            "storage_state": new_storage,
            "saved_at": datetime.utcnow().isoformat(),
        }
        await db.commit()

    print("\nBrowser bleibt 10s offen...")
    await asyncio.sleep(10)

    await browser.close()
    await playwright.stop()
    print("Fertig!")


if __name__ == "__main__":
    asyncio.run(main())
