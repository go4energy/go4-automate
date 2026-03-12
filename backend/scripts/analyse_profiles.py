"""Analyse 10 LinkedIn profiles from contacts.

Opens headed browser, visits each profile, scrolls through all sections,
saves HTML dumps + screenshots. Then clicks on sub-sections like
"Kontaktinformationen", "Interessen", etc.

Output goes to logs/profile_analysis/
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
from sqlalchemy import select

from app.database import async_session
from app.linkedin.models import LinkedInAccount
from app.linkedin.scraper.browser import LinkedInBrowser
from app.linkedin.scraper.parsers import parse_connections_list

OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "logs", "profile_analysis",
)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# The 10 profiles to analyse (from our connections page dump)
PROFILE_URLS = [
    "https://www.linkedin.com/in/andreas-zeidler-a107b2212",
    "https://www.linkedin.com/in/justus-lampe-0172a3296",
    "https://www.linkedin.com/in/liliananowakowska",
    "https://www.linkedin.com/in/heike-droste-a16292266",
    "https://www.linkedin.com/in/falko-bretsch-07133026b",
    "https://www.linkedin.com/in/christian-hinsel-2b02bb193",
    "https://www.linkedin.com/in/lidia-loskan-1b1b3b1b3",
    "https://www.linkedin.com/in/christian-m%C3%BCller-1a2b3c",
    "https://www.linkedin.com/in/tim-kemper-0172a3296",
    "https://www.linkedin.com/in/marlene-o-sullivan",
]


async def get_session_data() -> dict | None:
    """Load session from DB."""
    async with async_session() as db:
        result = await db.execute(
            select(LinkedInAccount).where(LinkedInAccount.status == "active")
        )
        account = result.scalar_one_or_none()
        if account and account.session_data:
            return account.session_data, account.email
    return None, None


async def scroll_full_page(page) -> None:
    """Scroll the entire page slowly to trigger lazy-loading of all sections."""
    logger.info("Scrolling full page to load all sections...")
    previous_height = 0
    for i in range(30):
        # Scroll one viewport height
        await page.evaluate("window.scrollBy(0, window.innerHeight)")
        await asyncio.sleep(0.8)

        current_height = await page.evaluate("document.body.scrollHeight")
        if current_height == previous_height and i > 3:
            break
        previous_height = current_height

    # Scroll back to top
    await page.evaluate("window.scrollTo(0, 0)")
    await asyncio.sleep(0.5)


async def save_profile_data(browser: LinkedInBrowser, url: str, index: int) -> None:
    """Visit a profile and save all available data."""
    slug = url.rstrip("/").split("/")[-1]
    prefix = f"{index:02d}_{slug[:40]}"

    logger.info(f"=== Profile {index + 1}/10: {slug} ===")

    # Navigate to profile
    try:
        await browser.page.goto(url, wait_until="domcontentloaded", timeout=30000)
    except Exception as e:
        logger.error(f"Could not navigate to {url}: {e}")
        return

    await asyncio.sleep(3)

    # Screenshot before scroll (top of profile)
    await browser.page.screenshot(
        path=os.path.join(OUTPUT_DIR, f"{prefix}_01_top.png"),
        full_page=False,
    )
    logger.info("  Screenshot: top")

    # Scroll full page to load all lazy sections
    await scroll_full_page(browser.page)

    # Full-page screenshot (everything loaded)
    await browser.page.screenshot(
        path=os.path.join(OUTPUT_DIR, f"{prefix}_02_full.png"),
        full_page=True,
    )
    logger.info("  Screenshot: full page")

    # Save HTML dump
    html = await browser.page.content()
    html_path = os.path.join(OUTPUT_DIR, f"{prefix}_page.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    logger.info(f"  HTML saved: {len(html)} bytes")

    # Extract visible text (cleaner than HTML for analysis)
    text_content = await browser.page.evaluate("""
        () => {
            // Get all visible text, section by section
            const sections = {};

            // Main profile card
            const mainCard = document.querySelector('.pv-top-card, .scaffold-layout__main');
            if (mainCard) sections['top_card'] = mainCard.innerText;

            // About section
            const about = document.querySelector('#about');
            if (about) {
                const aboutSection = about.closest('section') || about.parentElement;
                if (aboutSection) sections['about'] = aboutSection.innerText;
            }

            // Experience
            const exp = document.querySelector('#experience');
            if (exp) {
                const expSection = exp.closest('section') || exp.parentElement;
                if (expSection) sections['experience'] = expSection.innerText;
            }

            // Education
            const edu = document.querySelector('#education');
            if (edu) {
                const eduSection = edu.closest('section') || edu.parentElement;
                if (eduSection) sections['education'] = eduSection.innerText;
            }

            // Skills
            const skills = document.querySelector('#skills');
            if (skills) {
                const skillsSection = skills.closest('section') || skills.parentElement;
                if (skillsSection) sections['skills'] = skillsSection.innerText;
            }

            // Languages
            const langs = document.querySelector('#languages');
            if (langs) {
                const langsSection = langs.closest('section') || langs.parentElement;
                if (langsSection) sections['languages'] = langsSection.innerText;
            }

            // Interests
            const interests = document.querySelector('#interests');
            if (interests) {
                const interestsSection = interests.closest('section') || interests.parentElement;
                if (interestsSection) sections['interests'] = interestsSection.innerText;
            }

            // Recommendations
            const recs = document.querySelector('#recommendations');
            if (recs) {
                const recsSection = recs.closest('section') || recs.parentElement;
                if (recsSection) sections['recommendations'] = recsSection.innerText;
            }

            // Volunteer
            const vol = document.querySelector('#volunteering_experience, #volunteer');
            if (vol) {
                const volSection = vol.closest('section') || vol.parentElement;
                if (volSection) sections['volunteering'] = volSection.innerText;
            }

            // Certifications / Licenses
            const certs = document.querySelector('#licenses_and_certifications');
            if (certs) {
                const certsSection = certs.closest('section') || certs.parentElement;
                if (certsSection) sections['certifications'] = certsSection.innerText;
            }

            // Featured
            const featured = document.querySelector('#featured');
            if (featured) {
                const featuredSection = featured.closest('section') || featured.parentElement;
                if (featuredSection) sections['featured'] = featuredSection.innerText;
            }

            // Activity / Posts
            const activity = document.querySelector('#recent_activity, .feed-shared-update-v2');
            if (activity) {
                const actSection = activity.closest('section') || activity.parentElement;
                if (actSection) sections['activity'] = actSection.innerText.substring(0, 2000);
            }

            // All section IDs on the page (for discovery)
            const allSections = document.querySelectorAll('section[id], [id]');
            const sectionIds = [];
            allSections.forEach(s => {
                if (s.id && !s.id.startsWith('ember') && s.id.length < 60) {
                    sectionIds.push(s.id);
                }
            });
            sections['_section_ids'] = sectionIds.join(', ');

            // All links with meaningful text (for discovery)
            const allLinks = [];
            document.querySelectorAll('a[href]').forEach(a => {
                const text = a.innerText?.trim();
                const href = a.href;
                if (text && text.length > 2 && text.length < 100 &&
                    (href.includes('linkedin.com') || href.startsWith('/'))) {
                    allLinks.push(`${text} → ${href.substring(0, 100)}`);
                }
            });
            sections['_links'] = allLinks.slice(0, 50).join('\\n');

            // Follower / connection count text
            const counters = [];
            document.querySelectorAll('span, p').forEach(el => {
                const t = el.innerText?.trim();
                if (t && (t.includes('Follower') || t.includes('follower') ||
                    t.includes('Kontakte') || t.includes('connections'))) {
                    if (t.length < 50) counters.push(t);
                }
            });
            sections['_counters'] = counters.join(', ');

            return sections;
        }
    """)

    # Save extracted text
    text_path = os.path.join(OUTPUT_DIR, f"{prefix}_sections.txt")
    with open(text_path, "w", encoding="utf-8") as f:
        for section_name, text in text_content.items():
            f.write(f"\n{'='*60}\n")
            f.write(f"SECTION: {section_name}\n")
            f.write(f"{'='*60}\n")
            f.write(str(text) + "\n")
    logger.info(f"  Sections found: {[k for k in text_content if not k.startswith('_')]}")
    logger.info(f"  Section IDs: {text_content.get('_section_ids', 'none')}")
    logger.info(f"  Counters: {text_content.get('_counters', 'none')}")

    # Try clicking "Kontaktinformationen" link
    try:
        contact_link = await browser.page.query_selector(
            'a[href*="overlay/contact-info"], '
            'a[href*="contactinfo"], '
            '#top-card-text-details-contact-info'
        )
        if contact_link:
            await contact_link.click()
            await asyncio.sleep(2)

            # Screenshot of contact info modal
            await browser.page.screenshot(
                path=os.path.join(OUTPUT_DIR, f"{prefix}_03_contactinfo.png"),
                full_page=False,
            )

            # Save modal HTML
            modal_html = await browser.page.content()
            modal_path = os.path.join(OUTPUT_DIR, f"{prefix}_contactinfo.html")
            with open(modal_path, "w", encoding="utf-8") as f:
                f.write(modal_html)
            logger.info("  Contact info modal saved")

            # Close modal
            close_btn = await browser.page.query_selector(
                'button[aria-label="Schließen"], '
                'button[aria-label="Close"], '
                'button[aria-label="Dismiss"], '
                '.artdeco-modal__dismiss'
            )
            if close_btn:
                await close_btn.click()
                await asyncio.sleep(1)
        else:
            logger.info("  No contact info link found")
    except Exception as e:
        logger.warning(f"  Contact info click failed: {e}")

    # Try clicking on "Interessen" / interests section "Alle anzeigen"
    try:
        interests_link = await browser.page.query_selector(
            '#interests ~ .pvs-list__footer-wrapper a, '
            'a[href*="/interests/"]'
        )
        if interests_link:
            await interests_link.click()
            await asyncio.sleep(2)

            await browser.page.screenshot(
                path=os.path.join(OUTPUT_DIR, f"{prefix}_04_interests.png"),
                full_page=False,
            )

            interests_html = await browser.page.content()
            interests_path = os.path.join(OUTPUT_DIR, f"{prefix}_interests.html")
            with open(interests_path, "w", encoding="utf-8") as f:
                f.write(interests_html)
            logger.info("  Interests page saved")

            # Go back
            await browser.page.go_back()
            await asyncio.sleep(2)
        else:
            logger.info("  No interests link found")
    except Exception as e:
        logger.warning(f"  Interests click failed: {e}")

    logger.info(f"  Done: {prefix}")


async def main() -> None:
    """Main analysis routine."""
    logger.info("=== LinkedIn Profile Analysis ===")
    logger.info(f"Output directory: {OUTPUT_DIR}")

    # Get session
    session_data, email = await get_session_data()
    if not session_data:
        logger.error("No active LinkedIn account with session found!")
        return

    logger.info(f"Using account: {email}")

    # Start browser (headed!)
    browser = LinkedInBrowser(headless=False)
    await browser.start(email, session_data)

    try:
        # First go to connections page and get REAL profile URLs
        logger.info("Loading connections page to get real URLs...")
        await browser.page.goto(
            "https://www.linkedin.com/mynetwork/invite-connect/connections/",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        await asyncio.sleep(4)

        # Parse connections page for real URLs
        connections_html = await browser.page.content()
        connections = parse_connections_list(connections_html)

        if len(connections) < 10:
            logger.warning(f"Only {len(connections)} connections found, using what we have")

        profile_urls = [c["linkedin_url"] for c in connections[:10]]
        logger.info(f"Analysing {len(profile_urls)} profiles:")
        for i, url in enumerate(profile_urls):
            name = connections[i].get("name", "?") if i < len(connections) else "?"
            logger.info(f"  {i + 1}. {name} — {url}")

        # Visit each profile
        for i, url in enumerate(profile_urls):
            await save_profile_data(browser, url, i)
            # Human-like delay between profiles
            if i < len(profile_urls) - 1:
                await asyncio.sleep(3)

    except Exception as e:
        logger.exception(f"Analysis failed: {e}")
    finally:
        # Save session back
        await browser.stop()
        logger.info(f"\n=== Analysis complete. Files in {OUTPUT_DIR} ===")


if __name__ == "__main__":
    asyncio.run(main())
