#!/usr/bin/env python
"""Save LinkedIn session after manual login."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["DISPLAY"] = ":1"

from dotenv import load_dotenv

load_dotenv()

from datetime import datetime, timedelta

from playwright.async_api import async_playwright


async def save_session():
    print("Starte Browser...")

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=False,
        args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
    )

    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    )

    page = await context.new_page()
    print("Navigiere zu LinkedIn...")
    await page.goto("https://www.linkedin.com/feed/")

    print("Warte 5 Sekunden...")
    await asyncio.sleep(5)

    url = page.url
    print(f"Aktuelle URL: {url}")

    if "/login" not in url and "/checkpoint" not in url:
        print("Eingeloggt! Speichere Session...")
        storage = await context.storage_state()

        session_data = {
            "cookies": storage.get("cookies", []),
            "origins": storage.get("origins", []),
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat(),
        }

        print(f"Cookies gefunden: {len(session_data['cookies'])}")

        from sqlalchemy import update

        from app.database import async_session
        from app.linkedin.models import LinkedInAccount

        async with async_session() as db:
            await db.execute(
                update(LinkedInAccount)
                .where(LinkedInAccount.id == 4)
                .values(
                    session_data=session_data,
                    status="active",
                    last_error=None,
                    last_login_at=datetime.utcnow(),
                )
            )
            await db.commit()

        print("Session erfolgreich gespeichert!")
    else:
        print("FEHLER: Nicht eingeloggt!")

    await browser.close()
    await playwright.stop()


if __name__ == "__main__":
    asyncio.run(save_session())
