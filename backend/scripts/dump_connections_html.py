"""Dump LinkedIn connections page HTML for parser debugging.

Usage: cd backend && source .venv/bin/activate && python scripts/dump_connections_html.py
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import select
from app.database import async_session
from app.linkedin.models import LinkedInAccount
from app.linkedin.scraper.browser import LinkedInBrowser


async def main():
    # Get first active account
    async with async_session() as db:
        result = await db.execute(
            select(LinkedInAccount).where(LinkedInAccount.status != "disabled").limit(1)
        )
        account = result.scalar_one_or_none()
        if not account:
            print("Kein Account gefunden!")
            return

        print(f"Account: {account.email}")
        print(f"Session vorhanden: {bool(account.session_data)}")

    # Start browser
    browser = LinkedInBrowser(
        session_dir=f"sessions/{account.tenant_id}",
        headless=False,
    )
    await browser.start(account.email, account.session_data)
    print("Browser gestartet")

    # Check session
    valid = await browser.check_session_valid()
    print(f"Session gültig: {valid}")
    if not valid:
        print("Session abgelaufen!")
        await browser.stop()
        return

    # Navigate to connections
    print("Navigiere zu Connections...")
    await browser.navigate_to_connections()
    print("Connections-Seite geladen")

    # Wait a bit for full render
    await asyncio.sleep(3)

    # Get HTML
    html = await browser.get_page_content()
    dump_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "connections_page.html")
    os.makedirs(os.path.dirname(dump_path), exist_ok=True)
    with open(dump_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"HTML gespeichert: {dump_path} ({len(html)} bytes)")

    # Quick test: count profile links
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    links = soup.select('a[href*="/in/"]')
    cards = soup.select('div[componentkey]')
    print(f"Profile-Links: {len(links)}")
    print(f"componentkey-Divs: {len(cards)}")

    if cards:
        # Show first card structure
        card = cards[0]
        card_links = card.select('a[href*="/in/"]')
        print(f"\nErste Card hat {len(card_links)} Links:")
        for i, lnk in enumerate(card_links):
            text = lnk.get_text(strip=True)[:60]
            href = lnk.get("href", "")[:60]
            parent_tag = lnk.parent.name if lnk.parent else "?"
            print(f"  Link {i+1}: <{parent_tag}> text={text!r} href={href}")

    # Stop browser
    await browser.stop()
    print("\nBrowser gestoppt. Jetzt parser testen mit:")
    print(f"  python -c \"from app.linkedin.scraper.parsers import parse_connections_list; ...")


asyncio.run(main())
