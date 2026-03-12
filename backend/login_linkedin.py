#!/usr/bin/env python
"""Open LinkedIn login page for manual authentication."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import select

from app.database import async_session
from app.linkedin.models import LinkedInAccount
from app.linkedin.scraper.browser import LinkedInBrowser


async def main():
    """Open browser for LinkedIn login."""
    print("=" * 60)
    print("LinkedIn Login - Verbinde mit VNC (192.168.1.227:5901)")
    print("=" * 60)

    # Get account from database
    async with async_session() as db:
        result = await db.execute(
            select(LinkedInAccount).where(LinkedInAccount.id == 4)
        )
        account = result.scalar_one()
        print(f"\nAccount: {account.name} ({account.email})")
        print(f"Status: {account.status}")

    # Start browser
    os.environ["DISPLAY"] = ":1"
    browser = LinkedInBrowser(
        session_dir="sessions/go4energy",
        headless=False,
    )

    print("\nStarte Browser...")
    await browser.start(account.email, session_data=None)

    print("\nNavigiere zur Login-Seite...")
    await browser.page.goto("https://www.linkedin.com/login")

    print("\n" + "=" * 60)
    print("BITTE IM VNC-FENSTER EINLOGGEN!")
    print("Nach erfolgreichem Login druecke ENTER hier...")
    print("=" * 60)

    input()

    # Check if login was successful
    print("\nPruefe Session...")
    is_valid = await browser.check_session_valid()

    if is_valid:
        print("Login erfolgreich!")

        # Save session
        session_data = await browser.stop()

        if session_data:
            async with async_session() as db:
                result = await db.execute(
                    select(LinkedInAccount).where(LinkedInAccount.id == 4)
                )
                account = result.scalar_one()
                account.session_data = session_data
                account.status = "active"
                account.last_error = None
                await db.commit()
                print("Session gespeichert!")
    else:
        print("Login fehlgeschlagen - Session nicht gueltig")
        await browser.stop()


if __name__ == "__main__":
    asyncio.run(main())
