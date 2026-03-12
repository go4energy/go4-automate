#!/usr/bin/env python
"""Direct scraping script - loads session from DB."""

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
from app.linkedin.scraper.human_like import human_delay
from app.linkedin.scraper.parsers import parse_search_results


async def main():
    print("=" * 60)
    print("LinkedIn Scraper - Mit gespeicherter Session")
    print("=" * 60)

    # Get job and account from database
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

        print(f"\nJob: {job.name}")
        print(f"Account: {account.name}")

    if not session_data:
        print("FEHLER: Keine Session-Daten!")
        return

    # Extract storage state
    storage_state = session_data.get("storage_state")
    if not storage_state:
        print("FEHLER: Keine storage_state in Session!")
        return

    print(f"Cookies geladen: {len(storage_state.get('cookies', []))}")

    # Start browser with session
    print("\nStarte Browser mit Session...")
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

    # Go directly to Sales Navigator search
    print("\nNavigiere direkt zur Suche...")
    await page.goto(search_url, wait_until="domcontentloaded")
    await human_delay(5, 8)

    url = page.url
    print(f"URL: {url[:100]}")

    # Check if login is required
    if "/login" in url or "/checkpoint" in url:
        print("\nSession abgelaufen - warte auf manuellen Login (2 Min)...")
        for i in range(120):
            await asyncio.sleep(1)
            url = page.url
            if "/sales/" in url:
                print("Login erfolgreich!")
                break
            if i % 30 == 0:
                print(f"  {120-i}s verbleibend...")

    # Scrape first page
    print("\nScrape Suchergebnisse...")
    html = await page.content()
    contacts = parse_search_results(html)
    print(f"Gefunden: {len(contacts)} Profile auf Seite 1")

    # Show first few contacts
    for i, c in enumerate(contacts[:5]):
        print(f"  {i+1}. {c.get('name', 'N/A')} - {c.get('headline', 'N/A')[:40]}")

    if len(contacts) == 0:
        print("\nKeine Kontakte gefunden - speichere HTML...")
        with open("/tmp/search_page.html", "w") as f:
            f.write(html)
        print("HTML: /tmp/search_page.html")

    # Save to database
    if contacts:
        print(f"\nSpeichere {len(contacts)} Kontakte...")
        async with async_session() as db:
            for contact_data in contacts:
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

            result = await db.execute(
                select(LinkedInScraperJob).where(LinkedInScraperJob.id == 2)
            )
            job = result.scalar_one()
            job.profiles_found = len(contacts)
            job.profiles_scraped = len(contacts)
            job.status = "running"
            job.started_at = datetime.utcnow()

            await db.commit()
            print("Gespeichert!")

    # Save updated session
    print("\nSpeichere aktualisierte Session...")
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

    print("\nBrowser bleibt 30s offen...")
    await asyncio.sleep(30)

    await browser.close()
    await playwright.stop()
    print("Fertig!")


if __name__ == "__main__":
    asyncio.run(main())
