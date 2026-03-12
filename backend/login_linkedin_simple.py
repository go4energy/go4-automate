#!/usr/bin/env python
"""Open LinkedIn login page - keeps browser open."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ["DISPLAY"] = ":1"

from dotenv import load_dotenv

load_dotenv()

from playwright.async_api import async_playwright


async def main():
    print("Starte Browser...")

    playwright = await async_playwright().start()

    browser = await playwright.chromium.launch(
        headless=False,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--start-maximized",
        ],
    )

    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    )

    page = await context.new_page()

    print("Navigiere zu LinkedIn...")
    await page.goto("https://www.linkedin.com/login")

    print("\n" + "=" * 60)
    print("Browser ist offen - logge dich im VNC ein!")
    print("Schliesse dieses Script mit Ctrl+C wenn fertig")
    print("=" * 60 + "\n")

    # Keep running until interrupted
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nSpeichere Session...")
        storage = await context.storage_state()

        # Save to database
        from datetime import datetime, timedelta

        from sqlalchemy import update

        from app.database import async_session
        from app.linkedin.models import LinkedInAccount

        session_data = {
            "cookies": storage.get("cookies", []),
            "origins": storage.get("origins", []),
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat(),
        }

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

        print("Session gespeichert!")
        await browser.close()
        await playwright.stop()


if __name__ == "__main__":
    asyncio.run(main())
