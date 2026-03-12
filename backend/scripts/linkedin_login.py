#!/usr/bin/env python3
"""Interactive LinkedIn login script.

Run this script, log in manually via VNC, then the session will be saved.
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.async_api import async_playwright


async def interactive_login(account_name: str = "default"):
    """Open browser for manual LinkedIn login.

    Args:
        account_name: Name for the session file
    """
    # Ensure DISPLAY is set for VNC
    os.environ.setdefault("DISPLAY", ":1")

    session_dir = Path(__file__).parent.parent / "sessions"
    session_dir.mkdir(exist_ok=True)
    session_file = session_dir / f"{account_name}_session.json"

    print(f"\n{'='*60}")
    print("LinkedIn Login Script")
    print(f"{'='*60}")
    print(f"\nSession wird gespeichert in: {session_file}")
    print("\nBrowser öffnet sich gleich...")
    print("1. Verbinde dich per VNC: 192.168.1.227:5901 (Passwort: linkedin)")
    print("2. Logge dich bei LinkedIn ein")
    print("3. Warte bis 'Sales Navigator' geladen ist")
    print("4. Drücke ENTER hier um die Session zu speichern")
    print(f"{'='*60}\n")

    p = await async_playwright().start()

    browser = await p.chromium.launch(
        headless=False,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--start-maximized",
        ],
    )

    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        locale="de-DE",
        timezone_id="Europe/Berlin",
    )

    # Stealth mode
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        Object.defineProperty(navigator, 'languages', {get: () => ['de-DE', 'de', 'en-US', 'en']});
    """)

    page = await context.new_page()

    # Navigate to LinkedIn login
    print("Öffne LinkedIn...")
    await page.goto("https://www.linkedin.com/login")

    print("\n>>> Bitte im VNC-Fenster einloggen <<<")
    print(">>> Nach erfolgreichem Login ENTER drücken <<<\n")

    # Wait for user input
    input("Drücke ENTER wenn du eingeloggt bist...")

    # Check if logged in
    current_url = page.url
    print(f"\nAktuelle URL: {current_url}")

    if "/feed" in current_url or "/sales" in current_url or "/mynetwork" in current_url:
        print("✓ Login erfolgreich!")
    else:
        print("⚠ Möglicherweise nicht eingeloggt, speichere trotzdem...")

    # Navigate to Sales Navigator to verify
    print("\nPrüfe Sales Navigator Zugang...")
    await page.goto("https://www.linkedin.com/sales")
    await asyncio.sleep(3)

    if "/sales" in page.url:
        print("✓ Sales Navigator verfügbar!")
        is_sales_nav = True
    else:
        print("⚠ Kein Sales Navigator Zugang")
        is_sales_nav = False

    # Save session
    print("\nSpeichere Session...")
    storage_state = await context.storage_state()

    session_data = {
        "storage_state": storage_state,
        "saved_at": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
        "is_sales_navigator": is_sales_nav,
    }

    with open(session_file, "w") as f:
        json.dump(session_data, f, indent=2)

    print(f"✓ Session gespeichert: {session_file}")

    # Also print the session data for API import
    print(f"\n{'='*60}")
    print("Session für API-Import:")
    print(f"{'='*60}")

    # Extract just the cookies for easier import
    cookies = storage_state.get("cookies", [])
    li_at = next((c for c in cookies if c["name"] == "li_at"), None)
    if li_at:
        print(f"\nli_at Token: {li_at['value'][:20]}...")

    print("\nFür API-Import verwende:")
    print('curl -X POST "http://localhost:8002/api/v1/linkedin/accounts/{ACCOUNT_ID}/import-session" \\')
    print('  -H "Content-Type: application/json" \\')
    print('  -H "X-Tenant-ID: go4energy" \\')
    print('  -H "Authorization: Bearer test" \\')
    print(f"  -d '@{session_file}'")

    await browser.close()
    await p.stop()

    print(f"\n{'='*60}")
    print("Fertig! Du kannst jetzt einen Scraper-Job starten.")
    print(f"{'='*60}\n")

    return session_file


if __name__ == "__main__":
    account = sys.argv[1] if len(sys.argv) > 1 else "default"
    asyncio.run(interactive_login(account))
