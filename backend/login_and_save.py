#!/usr/bin/env python
"""Login to LinkedIn and save session - waits for user input."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["DISPLAY"] = ":1"

from dotenv import load_dotenv

load_dotenv()

from datetime import datetime, timedelta

from playwright.async_api import async_playwright


async def main():
    print("=" * 60)
    print("LinkedIn Login & Session Save")
    print("=" * 60)

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=False,
        args=["--no-sandbox", "--disable-blink-features=AutomationControlled", "--start-maximized"],
    )

    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    )

    page = await context.new_page()
    print("\nNavigiere zu LinkedIn Login...")
    await page.goto("https://www.linkedin.com/login")

    print("\n>>> Bitte im VNC-Fenster einloggen <<<")
    print(">>> Wenn du eingeloggt bist, tippe 'ok' und druecke Enter <<<\n")

    # Wait for user input
    while True:
        try:
            user_input = input("Eingeloggt? (ok/exit): ").strip().lower()
            if user_input == "ok":
                break
            elif user_input == "exit":
                print("Abbruch.")
                await browser.close()
                await playwright.stop()
                return
        except EOFError:
            # Running non-interactively, wait and check
            await asyncio.sleep(2)
            break

    # Check if logged in
    url = page.url
    print(f"\nAktuelle URL: {url}")

    if "/login" in url or "/checkpoint" in url:
        print("WARNUNG: Noch auf Login-Seite!")
        print("Warte 30 Sekunden fuer Login...")
        await asyncio.sleep(30)
        url = page.url
        print(f"Neue URL: {url}")

    if "/login" not in url and "/checkpoint" not in url:
        print("\nEingeloggt! Speichere Session...")
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

        print("\n" + "=" * 60)
        print("SESSION ERFOLGREICH GESPEICHERT!")
        print("=" * 60)
    else:
        print("\nFEHLER: Login nicht erfolgreich.")

    await browser.close()
    await playwright.stop()


if __name__ == "__main__":
    asyncio.run(main())
