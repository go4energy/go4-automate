#!/usr/bin/env python
"""Manual login script - waits 5 minutes for login."""

import asyncio
import os
import sys

sys.path.insert(0, "/opt/go4-automate/backend")
os.environ["DISPLAY"] = ":1"

from dotenv import load_dotenv

load_dotenv()

from datetime import datetime, timedelta

from playwright.async_api import async_playwright


async def main():
    print("=" * 50)
    print("Browser startet...")
    print("VNC: 192.168.1.227:5901")
    print("=" * 50)

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=False,
        args=["--no-sandbox", "--start-maximized"],
    )
    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    )
    page = await context.new_page()

    print("Navigiere zu LinkedIn Login...")
    await page.goto("https://www.linkedin.com/login")

    print("\nWarte auf Login (max 5 Minuten)...")

    for i in range(300):
        await asyncio.sleep(1)
        try:
            url = page.url
            if "/feed" in url or "/sales" in url or "/mynetwork" in url:
                print(f"\nLogin erkannt nach {i} Sekunden!")
                print(f"URL: {url}")
                break
            if i % 30 == 0 and i > 0:
                print(f"  {300-i}s verbleibend...")
        except Exception:
            pass

    url = page.url
    print(f"\nFinale URL: {url}")

    if "/login" not in url and "/checkpoint" not in url:
        print("\nSpeichere Session...")
        storage = await context.storage_state()

        session_data = {
            "storage_state": storage,
            "saved_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat(),
        }

        print(f"Cookies gefunden: {len(storage.get('cookies', []))}")

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

        print("\n" + "=" * 50)
        print("SESSION ERFOLGREICH GESPEICHERT!")
        print("=" * 50)
    else:
        print("\nFEHLER: Login nicht erfolgreich")

    await browser.close()
    await playwright.stop()


if __name__ == "__main__":
    asyncio.run(main())
