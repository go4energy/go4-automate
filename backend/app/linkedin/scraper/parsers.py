"""LinkedIn HTML/JSON parsing utilities.

Extracts structured data from LinkedIn Sales Navigator pages.
Uses multiple parsing strategies with fallbacks for robustness.
"""

import contextlib
import json
import re
from datetime import datetime, timedelta
from typing import Any

from bs4 import BeautifulSoup
from loguru import logger


def parse_search_results(html: str) -> list[dict[str, Any]]:
    """Parse Sales Navigator search results page.

    Args:
        html: HTML content of the search results

    Returns:
        List of profile data from search results
    """
    soup = BeautifulSoup(html, "html.parser")
    results = []

    # Try multiple selectors for result cards
    card_selectors = [
        "[data-x--lead-search-results] li",
        ".search-results__result-list li",
        ".artdeco-list__item",
        'li[class*="search-result"]',
        '[data-anonymize="person-name"]',  # Fallback - less specific
    ]

    cards = []
    for selector in card_selectors:
        cards = soup.select(selector)
        if cards:
            logger.debug(
                "Found {count} cards with selector: {sel}",
                count=len(cards),
                sel=selector,
            )
            break

    if not cards:
        # Try JSON-LD data as fallback
        json_results = _extract_json_ld(soup)
        if json_results:
            return json_results
        logger.warning("No result cards found in search results")
        return []

    for card in cards:
        try:
            profile = _parse_result_card(card)
            if profile.get("name") and profile.get("linkedin_url"):
                results.append(profile)
        except Exception as e:
            logger.debug("Error parsing card: {err}", err=str(e))
            continue

    logger.info("Parsed {count} profiles from search results", count=len(results))
    return results


def _parse_result_card(card) -> dict[str, Any]:
    """Parse a single search result card.

    Args:
        card: BeautifulSoup element for the card

    Returns:
        Profile data dictionary
    """
    profile = {
        "name": "",
        "first_name": "",
        "last_name": "",
        "headline": "",
        "position": "",
        "company_name": "",
        "company_linkedin_url": "",
        "location": "",
        "linkedin_url": "",
        "sales_navigator_url": "",
        "profile_picture_url": "",
        "contact_degree": None,
        "is_premium": False,
        "is_followed": False,
        "gender": None,
    }

    # Extract name
    name_selectors = [
        '[data-anonymize="person-name"]',
        ".result-lockup__name",
        ".artdeco-entity-lockup__title",
        'a[data-control-name="view_lead_panel_via_search_lead_name"]',
        'span[dir="ltr"]',
    ]
    for sel in name_selectors:
        el = card.select_one(sel)
        if el:
            profile["name"] = _clean_text(el.get_text())
            profile["first_name"], profile["last_name"] = split_name(profile["name"])
            break

    # Extract headline/title
    headline_selectors = [
        '[data-anonymize="title"]',
        ".result-lockup__highlight-keyword",
        ".artdeco-entity-lockup__subtitle",
        ".t-14.t-black--light",
    ]
    for sel in headline_selectors:
        el = card.select_one(sel)
        if el:
            profile["headline"] = _clean_text(el.get_text())
            break

    # Extract company
    company_selectors = [
        '[data-anonymize="company-name"]',
        ".result-lockup__position-company a",
        'a[data-control-name="search_srp_result_company_name"]',
    ]
    for sel in company_selectors:
        el = card.select_one(sel)
        if el:
            profile["company_name"] = _clean_text(el.get_text())
            href = el.get("href", "")
            if "/company/" in href or "/sales/company/" in href:
                profile["company_linkedin_url"] = _normalize_company_url(href)
            break

    # Extract location
    location_selectors = [
        '[data-anonymize="location"]',
        ".result-lockup__misc-item",
        ".t-12.t-black--light",
    ]
    for sel in location_selectors:
        el = card.select_one(sel)
        if el:
            text = _clean_text(el.get_text())
            # Skip if it looks like a date or connection info
            if not any(x in text.lower() for x in ["connection", "days ago", "shared"]):
                profile["location"] = text
                break

    # Extract profile URL
    link_selectors = [
        'a[href*="/sales/lead/"]',
        'a[href*="/sales/people/"]',
        'a[href*="/in/"]',
        'a[data-control-name="view_lead_panel_via_search_lead_name"]',
    ]
    for sel in link_selectors:
        el = card.select_one(sel)
        if el:
            href = el.get("href", "")
            if "/sales/" in href:
                profile["sales_navigator_url"] = _build_full_url(href)
                # Extract regular LinkedIn URL from sales URL
                linkedin_id = extract_linkedin_id(href)
                if linkedin_id:
                    profile["linkedin_url"] = (
                        f"https://www.linkedin.com/in/{linkedin_id}"
                    )
            elif "/in/" in href:
                profile["linkedin_url"] = _build_full_url(href)
            break

    # Extract profile picture
    img = card.select_one('img[src*="profile"], img[data-delayed-url*="profile"]')
    if img:
        profile["profile_picture_url"] = img.get("src") or img.get(
            "data-delayed-url", ""
        )

    # Extract connection degree (1st, 2nd, 3rd)
    degree_selectors = [
        '[data-anonymize="degree"]',
        '.degree-icon',
        '.distance-badge',
        'span[class*="degree"]',
    ]
    for sel in degree_selectors:
        el = card.select_one(sel)
        if el:
            text = _clean_text(el.get_text())
            if "1" in text:
                profile["contact_degree"] = 1
            elif "2" in text:
                profile["contact_degree"] = 2
            elif "3" in text:
                profile["contact_degree"] = 3
            break
    # Fallback: search in card text
    if not profile["contact_degree"]:
        card_text = card.get_text()
        if "1st" in card_text or "1." in card_text:
            profile["contact_degree"] = 1
        elif "2nd" in card_text or "2." in card_text:
            profile["contact_degree"] = 2
        elif "3rd" in card_text or "3." in card_text:
            profile["contact_degree"] = 3

    # Check for Premium badge
    premium_indicators = [
        '.premium-icon',
        '[data-test-premium-badge]',
        'li-icon[type="linkedin-premium"]',
        'svg[data-test-icon="premium"]',
        '.premium-badge',
    ]
    for sel in premium_indicators:
        if card.select_one(sel):
            profile["is_premium"] = True
            break
    # Fallback: check for "Premium" text
    if not profile["is_premium"] and "premium" in card.get_text().lower():
        profile["is_premium"] = True

    # Check if followed
    follow_indicators = [
        'button[aria-label*="Following"]',
        'button[aria-label*="Gefolgt"]',
        '.is-following',
    ]
    for sel in follow_indicators:
        if card.select_one(sel):
            profile["is_followed"] = True
            break

    # Infer gender from first name
    profile["gender"] = _infer_gender(profile["first_name"])

    return profile


def parse_profile_page(html: str) -> dict[str, Any]:
    """Parse a full LinkedIn profile page.

    Args:
        html: HTML content of the profile page

    Returns:
        Extracted profile data with experience, education, etc.
    """
    soup = BeautifulSoup(html, "html.parser")

    profile = {
        "name": "",
        "first_name": "",
        "last_name": "",
        "headline": "",
        "position": "",
        "company_name": "",
        "company_linkedin_url": "",
        "location": "",
        "linkedin_url": "",
        "profile_picture_url": "",
        "email": None,
        "phone": None,
        "experience": [],
        "education": [],
        "skills": [],
        "about": "",
    }

    # Try JSON-LD first (most reliable)
    json_ld = _extract_json_ld_profile(soup)
    if json_ld:
        profile.update(json_ld)

    # Extract name
    name_el = soup.select_one(
        ".text-heading-xlarge, .pv-text-details__left-panel h1, "
        '[data-anonymize="person-name"], .top-card__title'
    )
    if name_el:
        profile["name"] = _clean_text(name_el.get_text())
        profile["first_name"], profile["last_name"] = split_name(profile["name"])

    # Extract headline
    headline_el = soup.select_one(
        ".text-body-medium, .pv-text-details__left-panel .text-body-medium, "
        '[data-anonymize="title"]'
    )
    if headline_el:
        profile["headline"] = _clean_text(headline_el.get_text())

    # Extract location
    location_el = soup.select_one(
        ".text-body-small.inline.t-black--light, "
        ".pv-text-details__left-panel .pb2 span, "
        '[data-anonymize="location"]'
    )
    if location_el:
        profile["location"] = _clean_text(location_el.get_text())

    # Extract current position from experience section
    experience = _parse_experience(soup)
    if experience:
        profile["experience"] = experience
        # Get current position
        current = next((e for e in experience if e.get("is_current")), None)
        if current:
            profile["position"] = current.get("title", "")
            profile["company_name"] = current.get("company", "")
            profile["company_linkedin_url"] = current.get("company_url", "")

    # Extract education
    profile["education"] = _parse_education(soup)

    # Extract skills
    profile["skills"] = _parse_skills(soup)

    # Extract about/summary
    about_el = soup.select_one(
        '.pv-shared-text-with-see-more span[aria-hidden="true"], '
        '#about ~ .display-flex span[aria-hidden="true"]'
    )
    if about_el:
        profile["about"] = _clean_text(about_el.get_text())
        profile["summary"] = profile["about"]  # alias for DB field

    # Extract languages
    profile["languages"] = _parse_languages(soup)

    # Extract interests (influencers, companies, groups)
    profile["interests"] = _parse_interests(soup)

    # Extract follower count
    profile["follower_count"] = _parse_follower_count(soup)

    # Extract connection count
    profile["connection_count"] = _parse_connection_count(soup)

    # Extract premium badge
    profile["is_premium"] = _parse_is_premium(soup)

    # Extract pronouns
    pronouns_el = soup.select_one(
        '.text-body-small.v-align-middle span[aria-hidden="true"]'
    )
    if pronouns_el:
        text = _clean_text(pronouns_el.get_text())
        if text and text.startswith("(") and text.endswith(")"):
            profile["pronouns"] = text.strip("()")

    # Extract contact info if visible
    contact_section = soup.select_one('[data-section="contact"]')
    if contact_section:
        email_el = contact_section.select_one('a[href^="mailto:"]')
        if email_el:
            profile["email"] = email_el.get("href", "").replace("mailto:", "")
        phone_el = contact_section.select_one('a[href^="tel:"]')
        if phone_el:
            profile["phone"] = phone_el.get("href", "").replace("tel:", "")

    return profile


def _parse_experience(soup) -> list[dict]:
    """Parse experience section."""
    experiences = []
    exp_section = soup.select_one('#experience, [data-section="experience"]')
    if not exp_section:
        return []

    exp_items = exp_section.select("li.artdeco-list__item, .pvs-list__item")
    for item in exp_items[:10]:  # Limit to 10 most recent
        exp = {}
        title_el = item.select_one('.t-bold span[aria-hidden="true"], .mr1.t-bold span')
        if title_el:
            exp["title"] = _clean_text(title_el.get_text())

        company_el = item.select_one('.t-normal span[aria-hidden="true"]')
        if company_el:
            exp["company"] = _clean_text(company_el.get_text())

        date_el = item.select_one('.t-black--light span[aria-hidden="true"]')
        if date_el:
            date_text = _clean_text(date_el.get_text())
            exp["date_range"] = date_text
            exp["is_current"] = (
                "present" in date_text.lower() or "heute" in date_text.lower()
            )

        company_link = item.select_one('a[href*="/company/"]')
        if company_link:
            exp["company_url"] = _normalize_company_url(company_link.get("href", ""))

        if exp.get("title"):
            experiences.append(exp)

    return experiences


def _parse_education(soup) -> list[dict]:
    """Parse education section."""
    education = []
    edu_section = soup.select_one('#education, [data-section="education"]')
    if not edu_section:
        return []

    edu_items = edu_section.select("li.artdeco-list__item, .pvs-list__item")
    for item in edu_items[:5]:
        edu = {}
        school_el = item.select_one('.t-bold span[aria-hidden="true"]')
        if school_el:
            edu["school"] = _clean_text(school_el.get_text())

        degree_el = item.select_one('.t-normal span[aria-hidden="true"]')
        if degree_el:
            edu["degree"] = _clean_text(degree_el.get_text())

        if edu.get("school"):
            education.append(edu)

    return education


def _parse_skills(soup) -> list[str]:
    """Parse skills section."""
    skills = []
    skills_section = soup.select_one('#skills, [data-section="skills"]')
    if not skills_section:
        return []

    skill_items = skills_section.select('.t-bold span[aria-hidden="true"]')
    for item in skill_items[:20]:
        skill = _clean_text(item.get_text())
        if skill and len(skill) < 100:
            skills.append(skill)

    return skills


def _parse_languages(soup) -> list[str]:
    """Parse languages section from profile page."""
    languages = []
    lang_section = soup.select_one('#languages, [data-section="languages"]')
    if not lang_section:
        return []

    lang_items = lang_section.select('.t-bold span[aria-hidden="true"]')
    for item in lang_items[:10]:
        lang = _clean_text(item.get_text())
        if lang and len(lang) < 100:
            languages.append(lang)

    return languages


def _parse_interests(soup) -> dict[str, list[str]]:
    """Parse interests section (influencers, companies, groups, schools).

    Returns:
        Dict with keys 'influencers', 'companies', 'groups', 'schools'
        each containing a list of names.
    """
    interests: dict[str, list[str]] = {
        "influencers": [],
        "companies": [],
        "groups": [],
        "schools": [],
    }

    interest_section = soup.select_one('#interests, [data-section="interests"]')
    if not interest_section:
        return interests

    # LinkedIn interest tabs: each tab panel has items with names
    # The section header text determines the category
    panels = interest_section.select(
        ".artdeco-tab-panel, .pvs-list__container, .pvs-list"
    )

    for panel in panels:
        # Collect names from this panel
        names = []
        for item in panel.select('.t-bold span[aria-hidden="true"]'):
            name = _clean_text(item.get_text())
            if name and len(name) < 200:
                names.append(name)

        if not names:
            continue

        # Try to figure out category from tab headers or nearby text
        panel_text = _clean_text(panel.get_text()).lower()
        if any(kw in panel_text for kw in ("influencer", "top voices", "creator")):
            interests["influencers"].extend(names)
        elif any(kw in panel_text for kw in ("unternehmen", "companies", "company")):
            interests["companies"].extend(names)
        elif any(kw in panel_text for kw in ("gruppen", "groups")):
            interests["groups"].extend(names)
        elif any(kw in panel_text for kw in ("schule", "school", "uni")):
            interests["schools"].extend(names)
        else:
            # Default: put in influencers
            interests["influencers"].extend(names)

    # Also try simpler approach: all links in interest section
    if not any(interests.values()):
        for link in interest_section.select("a"):
            href = link.get("href", "")
            name = _clean_text(link.get_text())
            if not name or len(name) < 2 or len(name) > 200:
                continue
            if "/company/" in href:
                interests["companies"].append(name)
            elif "/groups/" in href:
                interests["groups"].append(name)
            elif "/school/" in href:
                interests["schools"].append(name)
            elif "/in/" in href:
                interests["influencers"].append(name)

    return interests


def _parse_follower_count(soup) -> int | None:
    """Extract follower count from profile page.

    Looks for text like '1.234 Follower' or '1,234 followers'.
    """
    for el in soup.select("span, p"):
        text = _clean_text(el.get_text())
        if not text:
            continue
        m = re.search(r"([\d.,]+)\s*(?:follower|Follower)", text)
        if m:
            count_str = m.group(1).replace(".", "").replace(",", "")
            with contextlib.suppress(ValueError):
                return int(count_str)
    return None


def _parse_connection_count(soup) -> int | None:
    """Extract connection count from profile page.

    Looks for text like '500+ Kontakte' or '500+ connections'.
    """
    for el in soup.select("span, p, a"):
        text = _clean_text(el.get_text())
        if not text:
            continue
        m = re.search(
            r"([\d.,]+)\+?\s*(?:Kontakte|connections|Verbindungen)", text, re.IGNORECASE
        )
        if m:
            count_str = m.group(1).replace(".", "").replace(",", "")
            with contextlib.suppress(ValueError):
                return int(count_str)
    return None


def _parse_is_premium(soup) -> bool:
    """Check if profile has premium badge."""
    # LinkedIn shows a gold/premium icon
    premium_selectors = [
        '[data-test-premium-badge]',
        '.premium-icon',
        'li-icon[type="linkedin-premium"]',
        '[class*="premium"]',
        '.pv-member-badge--premium',
    ]
    return any(soup.select_one(selector) for selector in premium_selectors)


def _extract_json_ld(soup) -> list[dict]:
    """Extract structured data from JSON-LD scripts."""
    results = []
    scripts = soup.select('script[type="application/ld+json"]')
    for script in scripts:
        try:
            data = json.loads(script.string)
            if isinstance(data, list):
                for item in data:
                    if item.get("@type") == "Person":
                        results.append(_json_ld_to_profile(item))
            elif isinstance(data, dict) and data.get("@type") == "Person":
                results.append(_json_ld_to_profile(data))
        except (json.JSONDecodeError, TypeError):
            continue
    return results


def _extract_json_ld_profile(soup) -> dict | None:
    """Extract profile data from JSON-LD."""
    scripts = soup.select('script[type="application/ld+json"]')
    for script in scripts:
        try:
            data = json.loads(script.string)
            if isinstance(data, dict) and data.get("@type") == "Person":
                return _json_ld_to_profile(data)
        except (json.JSONDecodeError, TypeError):
            continue
    return None


def _json_ld_to_profile(data: dict) -> dict:
    """Convert JSON-LD Person data to profile dict."""
    profile = {
        "name": data.get("name", ""),
        "headline": data.get("jobTitle", ""),
        "location": "",
        "linkedin_url": data.get("url", ""),
    }
    if data.get("address"):
        addr = data["address"]
        if isinstance(addr, dict):
            profile["location"] = addr.get("addressLocality", "")
        elif isinstance(addr, str):
            profile["location"] = addr

    profile["first_name"], profile["last_name"] = split_name(profile["name"])
    return profile


def extract_linkedin_id(url: str) -> str | None:
    """Extract LinkedIn member ID from profile URL.

    Args:
        url: LinkedIn profile URL

    Returns:
        Member ID or None if not found
    """
    if not url:
        return None

    # Match patterns like /in/john-doe-123abc/ or /sales/lead/ACwAAA.../
    patterns = [
        r"/in/([^/?#]+)",
        r"/sales/lead/([^,/?#]+)",
        r"/sales/people/([^,/?#]+)",
        r"miniProfileUrn=urn%3Ali%3Afs_miniProfile%3A([^&]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def normalize_linkedin_url(url: str) -> str:
    """Normalize LinkedIn URL to standard format.

    Args:
        url: Raw LinkedIn URL

    Returns:
        Normalized URL
    """
    if not url:
        return ""

    url = url.strip()
    # Remove query params
    if "?" in url:
        url = url.split("?")[0]
    # Remove trailing slash
    url = url.rstrip("/")
    # Ensure https
    if url.startswith("http://"):
        url = url.replace("http://", "https://")
    # Add protocol if missing
    if url.startswith("www."):
        url = "https://" + url
    return url


def _normalize_company_url(url: str) -> str:
    """Normalize company LinkedIn URL."""
    if not url:
        return ""
    url = normalize_linkedin_url(url)
    # Convert sales navigator company URL to regular
    if "/sales/company/" in url:
        company_id = url.split("/sales/company/")[-1].split("/")[0].split(",")[0]
        return f"https://www.linkedin.com/company/{company_id}"
    return url


def _build_full_url(href: str) -> str:
    """Build full URL from relative href."""
    if not href:
        return ""
    if href.startswith("http"):
        return normalize_linkedin_url(href)
    return normalize_linkedin_url(f"https://www.linkedin.com{href}")


def extract_company_info(profile_data: dict) -> dict[str, Any]:
    """Extract company information from profile data.

    Args:
        profile_data: Parsed profile data

    Returns:
        Company information
    """
    return {
        "name": profile_data.get("company_name"),
        "linkedin_url": profile_data.get("company_linkedin_url"),
        "industry": profile_data.get("company_industry"),
        "size": profile_data.get("company_size"),
    }


def split_name(full_name: str) -> tuple[str, str]:
    """Split full name into first and last name.

    Args:
        full_name: Full name string

    Returns:
        Tuple of (first_name, last_name)
    """
    if not full_name:
        return ("", "")

    # Remove titles and suffixes
    titles = ["Dr.", "Prof.", "Ing.", "MBA", "PhD", "MSc", "BSc"]
    name = full_name
    for title in titles:
        name = name.replace(title, "").strip()

    parts = name.strip().split()
    if len(parts) == 0:
        return ("", "")
    elif len(parts) == 1:
        return (parts[0], "")
    else:
        return (parts[0], " ".join(parts[1:]))


def _clean_text(text: str) -> str:
    """Clean and normalize extracted text."""
    if not text:
        return ""
    # Remove extra whitespace
    text = " ".join(text.split())
    # Remove common artifacts
    text = text.strip(" \n\t·•|")
    return text


def _infer_gender(first_name: str) -> str | None:
    """Infer gender from first name using common German/English names.

    Args:
        first_name: First name to analyze

    Returns:
        'male', 'female', or None if unknown
    """
    if not first_name:
        return None

    name = first_name.lower().strip()

    # Common German/English female names
    female_names = {
        "anna", "maria", "julia", "laura", "lisa", "sarah", "sandra", "sabine",
        "petra", "claudia", "andrea", "nicole", "stefanie", "stephanie", "susanne",
        "monika", "christine", "martina", "karin", "gabriele", "birgit", "angela",
        "heike", "anja", "katrin", "silke", "manuela", "simone", "ines", "jana",
        "katharina", "melanie", "jennifer", "jessica", "michelle", "vanessa",
        "franziska", "johanna", "christina", "daniela", "elena", "emma", "hannah",
        "lena", "leonie", "marie", "sophie", "charlotte", "emily", "mia", "sophia",
        "sigrid", "ute", "ilse", "helga", "gerda", "ingrid", "renate", "eva",
        "elisabeth", "barbara", "margarete", "hildegard", "ursula", "brigitte",
    }

    # Common German/English male names
    male_names = {
        "thomas", "michael", "andreas", "stefan", "christian", "martin", "peter",
        "markus", "daniel", "matthias", "frank", "alexander", "klaus", "oliver",
        "jürgen", "juergen", "hans", "werner", "helmut", "karl", "heinz", "gerhard",
        "wolfgang", "rainer", "ralf", "bernd", "dieter", "uwe", "jens", "dirk",
        "thorsten", "sven", "tobias", "florian", "sebastian", "jan", "tim", "jonas",
        "lukas", "felix", "maximilian", "paul", "leon", "david", "philipp", "fabian",
        "niklas", "julian", "moritz", "johannes", "benjamin", "simon", "max",
        "robert", "christoph", "patrick", "dominik", "marcel", "kevin", "dennis",
        "mario", "torsten", "carsten", "holger", "volker", "manfred", "joachim",
        "norbert", "horst", "walter", "fritz", "heinrich", "otto", "wilhelm",
    }

    if name in female_names:
        return "female"
    if name in male_names:
        return "male"

    # Common endings heuristics
    if name.endswith(("a", "e", "in", "ine", "elle", "ette")):
        return "female"
    if name.endswith(("o", "us", "ian", "an")):
        return "male"

    return None


def detect_pagination_info(html: str) -> dict:
    """Detect pagination information from search results.

    Args:
        html: Search results HTML

    Returns:
        Dictionary with current_page, total_pages, has_next
    """
    soup = BeautifulSoup(html, "html.parser")

    info = {
        "current_page": 1,
        "total_pages": 1,
        "total_results": 0,
        "has_next": False,
    }

    # Try to find results count
    count_selectors = [
        ".search-results__total",
        "[data-x--search-results-meta]",
        ".artdeco-dropdown__trigger span",
    ]
    for sel in count_selectors:
        el = soup.select_one(sel)
        if el:
            text = el.get_text()
            # Extract number from text like "1,234 results"
            match = re.search(r"[\d,\.]+", text.replace(",", "").replace(".", ""))
            if match:
                try:
                    info["total_results"] = int(
                        match.group().replace(",", "").replace(".", "")
                    )
                    # Estimate pages (25 results per page typically)
                    info["total_pages"] = (info["total_results"] + 24) // 25
                except ValueError:
                    pass
            break

    # Find current page
    active_page = soup.select_one(
        'button[aria-current="true"], '
        ".artdeco-pagination__indicator--number.selected"
    )
    if active_page:
        import contextlib

        with contextlib.suppress(ValueError):
            info["current_page"] = int(active_page.get_text().strip())

    # Check for next button
    next_btn = soup.select_one(
        'button[aria-label="Next"]:not([disabled]), '
        'button[aria-label="Weiter"]:not([disabled])'
    )
    info["has_next"] = next_btn is not None

    return info


def is_rate_limited(html: str) -> bool:
    """Check if page shows rate limiting.

    Only triggers on REAL rate-limit pages, not normal pages
    that happen to contain the word 'challenge' in profile text.

    Args:
        html: Page HTML

    Returns:
        True if rate limited
    """
    # Strong indicators — these only appear on actual block pages
    strong = [
        "rate limit",
        "too many requests",
        "unusual activity",
        "security verification",
        "/checkpoint/challenge",
    ]
    html_lower = html.lower()
    if any(ind in html_lower for ind in strong):
        return True

    # Captcha page has very little other content
    return "captcha" in html_lower and len(html) < 50000


def parse_sales_navigator_profile(html: str, url: str = "") -> dict[str, Any]:
    """Parse a Sales Navigator profile page.

    Extracts extended profile data including experience, education,
    connection count, and summary from Sales Navigator lead pages.

    Args:
        html: HTML content of the Sales Navigator profile page
        url: Profile URL for reference

    Returns:
        Extracted profile data
    """
    soup = BeautifulSoup(html, "html.parser")

    profile = {
        "name": "",
        "first_name": "",
        "last_name": "",
        "headline": "",
        "position": "",
        "company_name": "",
        "company_linkedin_url": "",
        "location": "",
        "linkedin_url": "",
        "sales_navigator_url": url,
        "profile_picture_url": "",
        "connection_count": None,
        "follower_count": None,
        "contact_degree": None,
        "is_premium": False,
        "gender": None,
        "summary": "",
        "experience": [],
        "education": [],
        "languages": [],
        "raw_data": {},
    }

    # Extract name from h1 or data-anonymize
    name_el = soup.select_one(
        'h1[data-anonymize="person-name"], '
        '[data-x--lead--name][data-anonymize="person-name"]'
    )
    if name_el:
        profile["name"] = _clean_text(name_el.get_text())
        profile["first_name"], profile["last_name"] = split_name(profile["name"])

    # Extract headline
    headline_el = soup.select_one('span[data-anonymize="headline"]')
    if headline_el:
        profile["headline"] = _clean_text(headline_el.get_text())

    # Extract current position and company from top card
    position_el = soup.select_one('span[data-anonymize="job-title"]')
    if position_el:
        profile["position"] = _clean_text(position_el.get_text())

    company_el = soup.select_one('a[data-anonymize="company-name"]')
    if company_el:
        profile["company_name"] = _clean_text(company_el.get_text())
        href = company_el.get("href", "")
        if href:
            profile["company_linkedin_url"] = _normalize_company_url(href)

    # Extract location and connection count from the profile header area
    # They are in divs with specific classes, each containing an SVG icon
    header_divs = soup.select('div._bodyText_1e5nen._lowEmphasis_1i6ulk')
    for div in header_divs:
        text = _clean_text(div.get_text())
        # Check for connection count pattern (e.g., "418 Kontakte")
        if "Kontakte" in text or "connections" in text.lower():
            match = re.search(r'([\d.,]+)\s*(?:Kontakte|connections)', text, re.I)
            if match:
                count_str = match.group(1).replace(".", "").replace(",", "")
                with contextlib.suppress(ValueError):
                    profile["connection_count"] = int(count_str)
        # Check if it looks like a location (contains comma or known patterns)
        elif any(kw in text for kw in ["Deutschland", "Germany", "Austria", "Schweiz", "Switzerland", "Österreich"]) and "," in text:
            if not profile["location"]:
                profile["location"] = text

    # Extract profile picture
    img_el = soup.select_one('img[data-anonymize="headshot-photo"][class*="circle-entity"]')
    if img_el:
        profile["profile_picture_url"] = img_el.get("src", "")

    # Extract summary from person-blurb (first one is usually the current position summary)
    summary_el = soup.select_one('[data-anonymize="person-blurb"]')
    if summary_el:
        # Get full text from title attribute (not truncated)
        full_text = summary_el.get("title", "")
        if full_text:
            profile["summary"] = full_text
        else:
            profile["summary"] = _clean_text(summary_el.get_text())

    # Extract experience section
    profile["experience"] = _parse_sn_experience(soup)

    # Set current position from experience if not already set
    if profile["experience"] and not profile["position"]:
        current = profile["experience"][0]  # First is usually current
        profile["position"] = current.get("title", "")
        if not profile["company_name"]:
            profile["company_name"] = current.get("company", "")

    # Extract education section
    profile["education"] = _parse_sn_education(soup)

    # Extract connection degree
    degree_pattern = re.search(r'\b([123])\.\s*(?:Grad|degree)', soup.get_text(), re.I)
    if degree_pattern:
        profile["contact_degree"] = int(degree_pattern.group(1))

    # Check for premium badge
    if soup.select_one('li-icon[type="linkedin-premium"], .premium-icon, [data-test-premium-badge]'):
        profile["is_premium"] = True

    # Infer gender from first name
    profile["gender"] = _infer_gender(profile["first_name"])

    # Extract LinkedIn URL from sales navigator URL
    if url and "/sales/lead/" in url:
        # Try to find regular LinkedIn link
        linkedin_link = soup.select_one('a[href*="linkedin.com/in/"]')
        if linkedin_link:
            profile["linkedin_url"] = normalize_linkedin_url(linkedin_link.get("href", ""))
        else:
            # Extract member ID from sales navigator URL
            linkedin_id = extract_linkedin_id(url)
            if linkedin_id:
                profile["linkedin_url"] = f"https://www.linkedin.com/in/{linkedin_id}"

    logger.debug(
        "Parsed Sales Navigator profile: {name} at {company}",
        name=profile["name"],
        company=profile["company_name"],
    )

    return profile


def _parse_sn_experience(soup) -> list[dict]:
    """Parse experience section from Sales Navigator profile.

    Returns list of experience dictionaries with:
    - title: Job title
    - company: Company name
    - company_url: LinkedIn company URL
    - location: Job location
    - description: Job description
    - date_range: Date range string
    - is_current: Boolean
    """
    experiences = []

    # Find experience section
    exp_section = soup.select_one('[data-sn-view-name="feature-lead-experience"]')
    if not exp_section:
        # Fallback: look for experience by ID
        exp_section = soup.select_one('#experience-section, #scroll-to-experience-section')

    if not exp_section:
        return []

    # Find experience items - Sales Navigator uses _experience-entry_ class
    job_items = exp_section.select('li[class*="_experience-entry"]')

    if not job_items:
        # Fallback: find all li items in the section
        job_items = exp_section.select('li')

    for item in job_items[:10]:  # Limit to 10 positions
        exp = {}

        # Extract job title from h2 with data-anonymize
        title_el = item.select_one('h2[data-anonymize="job-title"]')
        if title_el:
            exp["title"] = _clean_text(title_el.get_text())

        # Extract company name
        company_el = item.select_one('[data-anonymize="company-name"]')
        if company_el:
            exp["company"] = _clean_text(company_el.get_text())
            # Get company URL from parent link
            parent_link = company_el.find_parent('a')
            if parent_link:
                href = parent_link.get("href", "")
                if href:
                    exp["company_url"] = _normalize_company_url(href)

        # Extract description from person-blurb
        desc_el = item.select_one('[data-anonymize="person-blurb"]')
        if desc_el:
            # Prefer full text from title attribute (not truncated)
            exp["description"] = desc_el.get("title", "") or _clean_text(desc_el.get_text())

        # Extract date range - it's typically in a span with specific class or p element
        date_el = item.select_one('p._bodyText_1e5nen._sizeXSmall_1e5nen._lowEmphasis_1i6ulk span')
        if date_el:
            date_text = _clean_text(date_el.get_text())
            exp["date_range"] = date_text
            exp["is_current"] = any(kw in date_text.lower() for kw in ["heute", "present", "current", "-heute"])

        # Extract location if available (second p element with location class)
        location_els = item.select('p._bodyText_1e5nen._sizeXSmall_1e5nen._lowEmphasis_1i6ulk')
        for loc_el in location_els:
            loc_text = _clean_text(loc_el.get_text())
            # Check if it looks like a location (has comma, no date patterns)
            if "," in loc_text and any(
                kw in loc_text for kw in ["Deutschland", "Germany", "Austria", "Schweiz", "Switzerland", "USA", "UK"]
            ):
                exp["location"] = loc_text
                break

        if exp.get("title"):
            experiences.append(exp)

    return experiences


def _parse_sn_education(soup) -> list[dict]:
    """Parse education section from Sales Navigator profile.

    Returns list of education dictionaries with:
    - school: School/university name
    - degree: Degree type (e.g., "Master of Science")
    - field_of_study: Field of study
    - start_year: Start year
    - end_year: End year
    """
    education = []

    # Find education section
    edu_section = soup.select_one('[data-sn-view-name="feature-lead-education"]')
    if not edu_section:
        return []

    # Find education items
    edu_items = edu_section.select('li[class*="fmBYDDfuwgL"]')

    for item in edu_items[:5]:  # Limit to 5
        edu = {}

        # Extract school name
        school_el = item.select_one('[data-anonymize="education-name"], h3[data-anonymize="education-name"]')
        if school_el:
            edu["school"] = _clean_text(school_el.get_text())

        # Extract degree and field of study
        # Usually in a <p> element with spans
        info_el = item.select_one('p._bodyText_1e5nen._sizeSmall_1e5nen')
        if info_el:
            spans = info_el.select('span')
            if len(spans) >= 1:
                edu["degree"] = _clean_text(spans[0].get_text())
            if len(spans) >= 2:
                edu["field_of_study"] = _clean_text(spans[1].get_text())

        # Extract years from time elements
        time_els = item.select('time')
        if len(time_els) >= 2:
            edu["start_year"] = time_els[0].get("datetime", _clean_text(time_els[0].get_text()))
            edu["end_year"] = time_els[1].get("datetime", _clean_text(time_els[1].get_text()))
        elif len(time_els) == 1:
            edu["end_year"] = time_els[0].get("datetime", _clean_text(time_els[0].get_text()))

        if edu.get("school"):
            education.append(edu)

    return education


# ============== Connections Page Parser ==============


def parse_connections_list(html: str) -> list[dict[str, Any]]:
    """Parse the LinkedIn connections page (/mynetwork/invite-connect/connections/).

    LinkedIn now uses CSS-module hashed classes and <div componentkey="...">
    as card containers instead of <li> or .mn-connection-card.
    We find card containers first, then extract profile data from each.

    Args:
        html: HTML content of the connections page

    Returns:
        List of connection dicts with basic profile data
    """
    soup = BeautifulSoup(html, "html.parser")
    results = []
    seen_urls: set[str] = set()

    # Strategy 1: Find individual contact cards (auto-component-* divs)
    # NOT the outer containers like ConnectionsPage_ConnectionsList
    cards = soup.select('div[componentkey^="auto-component"]')
    logger.debug(
        "Found {count} auto-component cards on connections page",
        count=len(cards),
    )

    for card in cards:
        try:
            # Find ALL profile links in this card
            links = card.select('a[href*="/in/"]')
            if not links:
                continue

            # Deduplicate: pick the first unique /in/ URL
            href = ""
            for lnk in links:
                h = lnk.get("href", "")
                if "/in/" in h:
                    href = h
                    break

            normalized = normalize_linkedin_url(href)
            if not normalized or normalized in seen_urls:
                continue
            seen_urls.add(normalized)

            connection = _parse_connection_card_v2(card, links)
            if connection.get("name") and connection.get("linkedin_url"):
                results.append(connection)
            else:
                logger.debug(
                    "Card skipped: name={n!r} url={u!r}",
                    n=connection.get("name", ""),
                    u=connection.get("linkedin_url", ""),
                )
        except Exception as e:
            logger.debug("Error parsing connection card: {err}", err=str(e))
            continue

    # Strategy 2 fallback: if no componentkey cards, try profile links directly
    if not results:
        logger.debug("No componentkey cards — falling back to profile links")
        profile_links = soup.select('a[href*="/in/"]')
        for link in profile_links:
            try:
                href = link.get("href", "")
                if "/in/" not in href:
                    continue
                normalized = normalize_linkedin_url(href)
                if not normalized or normalized in seen_urls:
                    continue
                seen_urls.add(normalized)

                card = link.find_parent("li") or link.find_parent("div")
                if card is None:
                    card = link

                card_links = card.select('a[href*="/in/"]') or [link]
                connection = _parse_connection_card_v2(card, card_links)
                if connection.get("name") and connection.get("linkedin_url"):
                    results.append(connection)
            except Exception as e:
                logger.debug("Error parsing connection link: {err}", err=str(e))
                continue

    logger.info(
        "Parsed {count} connections from connections page", count=len(results)
    )
    return results


def _parse_connection_card_v2(card, profile_links) -> dict[str, Any]:
    """Parse a connection entry from a componentkey card.

    LinkedIn cards typically contain 3 links to the same /in/ profile:
      1. Main card link (wraps image, has no useful text)
      2. Inner link (contains "Name + Headline" concatenated)
      3. <p> link (contains just the clean name)

    We use link #3 (shortest text with /in/) for the name.

    Args:
        card: BeautifulSoup element for the container
        profile_links: List of <a> elements with /in/ hrefs in this card

    Returns:
        Connection data dictionary
    """
    # Get URL from first link
    href = profile_links[0].get("href", "") if profile_links else ""
    connection: dict[str, Any] = {
        "linkedin_url": normalize_linkedin_url(href),
        "linkedin_id": extract_linkedin_id(href),
        "contact_degree": 1,
        "name": "",
        "headline": "",
        "profile_picture_url": "",
        "connected_at_text": "",
        "profile_urn": "",
        "messaging_url": "",
    }

    # --- Profile URN from messaging link ---
    # <a href="/messaging/compose/?profileUrn=urn%3Ali%3Afsd_profile%3AACoAAD...">
    msg_link = card.select_one('a[href*="/messaging/compose/"]')
    if msg_link:
        msg_href = msg_link.get("href", "")
        connection["messaging_url"] = msg_href
        urn_match = re.search(r"profileUrn=urn%3Ali%3Afsd_profile%3A([^&]+)", msg_href)
        if urn_match:
            connection["profile_urn"] = urn_match.group(1)

    # --- Name ---
    # Find the link with the SHORTEST non-empty text = cleanest name
    best_name = ""
    for lnk in profile_links:
        t = _clean_text(lnk.get_text())
        if t and (not best_name or len(t) < len(best_name)):
            best_name = t
    connection["name"] = best_name

    if connection["name"]:
        first, last = split_name(connection["name"])
        connection["first_name"] = first
        connection["last_name"] = last

    # --- Headline ---
    # The link with the LONGEST text has "Name + Headline" concatenated
    # Strip the name prefix to get the headline
    for lnk in profile_links:
        t = _clean_text(lnk.get_text())
        if t and t != connection["name"] and len(t) > len(connection["name"]):
            # Remove name prefix to get just the headline
            headline = t
            if connection["name"] and t.startswith(connection["name"]):
                headline = t[len(connection["name"]):].strip()
            if headline:
                connection["headline"] = headline
                break

    # Fallback: look for text in non-link elements
    if not connection["headline"]:
        for el in card.select("p, span"):
            if el.select_one('a[href*="/in/"]'):
                continue  # skip elements containing profile links
            t = _clean_text(el.get_text())
            if t and t != connection["name"] and len(t) > 5:
                connection["headline"] = t
                break

    # --- Profile picture ---
    img = card.select_one("img")
    if img:
        src = img.get("src", "")
        if src and "data:image" not in src and "ghost" not in src:
            connection["profile_picture_url"] = src

    # --- Connected time ---
    # LinkedIn shows "Am 4. März 2026 vernetzt" or "Connected on March 4, 2026"
    # Always in a <p> tag, always the last text line per card.
    # Strategy: look for definitive patterns first, then fall back.

    # 1. Try <time> element
    time_el = card.select_one("time")
    if time_el:
        connection["connected_at_text"] = _clean_text(time_el.get_text())
    else:
        # 2. Look for "vernetzt" / "connected" in <p> or <span> — the definitive marker
        for el in card.select("p, span"):
            t = _clean_text(el.get_text())
            if not t:
                continue
            t_lower = t.lower()
            # Must contain the actual connection keyword (not just "verbinden" in headlines)
            if "vernetzt" in t_lower or "connected" in t_lower:
                connection["connected_at_text"] = t
                break

    return connection


def _parse_connection_card(card) -> dict[str, Any]:
    """Parse a single connection card from the connections page.

    Args:
        card: BeautifulSoup element for the card

    Returns:
        Connection data dictionary
    """
    connection: dict[str, Any] = {
        "name": "",
        "linkedin_url": "",
        "linkedin_id": "",
        "headline": "",
        "profile_picture_url": "",
        "connected_at_text": "",
        "contact_degree": 1,  # Always 1st degree on connections page
    }

    # Extract profile link and name
    link_selectors = [
        'a[href*="/in/"]',
        ".mn-connection-card__link",
        'a[data-control-name="connection_profile"]',
    ]
    for selector in link_selectors:
        link = card.select_one(selector)
        if link:
            href = link.get("href", "")
            if "/in/" in href:
                connection["linkedin_url"] = normalize_linkedin_url(href)
                connection["linkedin_id"] = extract_linkedin_id(href)

                # Name is often inside the link
                name_el = link.select_one(
                    ".mn-connection-card__name, "
                    '[data-anonymize="person-name"], '
                    "span.t-bold, "
                    ".artdeco-entity-lockup__title span"
                )
                if name_el:
                    connection["name"] = _clean_text(name_el.get_text())
                elif link.get_text().strip():
                    text = _clean_text(link.get_text())
                    connection["name"] = text.split("\n")[0].strip()
                break

    # If name not found in link, try broader selectors
    if not connection["name"]:
        name_selectors = [
            ".mn-connection-card__name",
            '[data-anonymize="person-name"]',
            "span.t-bold",
        ]
        for selector in name_selectors:
            el = card.select_one(selector)
            if el:
                connection["name"] = _clean_text(el.get_text())
                break

    if connection["name"]:
        first, last = split_name(connection["name"])
        connection["first_name"] = first
        connection["last_name"] = last

    # Extract headline/occupation
    headline_selectors = [
        ".mn-connection-card__occupation",
        '[data-anonymize="headline"]',
        "span.t-normal.t-black--light",
        ".artdeco-entity-lockup__subtitle",
        "p.mn-connection-card__occupation",
    ]
    for selector in headline_selectors:
        el = card.select_one(selector)
        if el:
            connection["headline"] = _clean_text(el.get_text())
            break

    # Extract profile picture
    img_selectors = [
        ".mn-connection-card__picture img",
        ".presence-entity__image",
        "img.EntityPhoto-circle-5",
        'img[data-anonymize="headshot-photo"]',
    ]
    for selector in img_selectors:
        img = card.select_one(selector)
        if img:
            src = img.get("src", "")
            if src and "data:image" not in src:
                connection["profile_picture_url"] = src
            break

    # Extract "connected X ago" text
    time_selectors = [
        "time",
        ".time-badge",
        "span.t-black--light.t-12",
        ".mn-connection-card__connected-time",
    ]
    for selector in time_selectors:
        el = card.select_one(selector)
        if el:
            text = _clean_text(el.get_text())
            if text:
                connection["connected_at_text"] = text
                break

    return connection


def parse_connected_time_text(text: str) -> datetime | None:
    """Parse connection time text from LinkedIn.

    Supports:
    - Absolute German: "Am 4. März 2026 vernetzt"
    - Absolute English: "Connected on March 4, 2026"
    - Relative German: "Seit 3 Tagen verbunden", "Vor 2 Wochen vernetzt"
    - Relative English: "Connected 3 days ago"

    Args:
        text: Time text from LinkedIn connection card

    Returns:
        Parsed datetime or None if unparseable
    """
    text_lower = text.lower().strip()
    now = datetime.utcnow()

    # --- 1. Absolute date: "Am DD. Monat YYYY vernetzt" ---
    german_months = {
        "januar": 1, "jänner": 1, "februar": 2, "märz": 3, "april": 4,
        "mai": 5, "juni": 6, "juli": 7, "august": 8, "september": 9,
        "oktober": 10, "november": 11, "dezember": 12,
    }
    # "Am 4. März 2026 vernetzt" or "4. März 2026"
    m = re.search(r"(\d{1,2})\.\s*(\w+)\s+(\d{4})", text_lower)
    if m:
        day = int(m.group(1))
        month_name = m.group(2)
        year = int(m.group(3))
        month = german_months.get(month_name)
        if month:
            try:
                return datetime(year, month, day)
            except ValueError:
                pass

    # --- 2. Absolute date: "Connected on March 4, 2026" ---
    english_months = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8, "september": 9,
        "october": 10, "november": 11, "december": 12,
    }
    m = re.search(r"(\w+)\s+(\d{1,2}),?\s+(\d{4})", text_lower)
    if m:
        month_name = m.group(1)
        day = int(m.group(2))
        year = int(m.group(3))
        month = english_months.get(month_name)
        if month:
            try:
                return datetime(year, month, day)
            except ValueError:
                pass

    # --- 3. Relative time: "Seit 3 Tagen", "Vor 2 Wochen", "3 days ago" ---
    relative_patterns = [
        # German
        (r"(\d+)\s*tag", "days"),
        (r"(\d+)\s*woche", "weeks"),
        (r"(\d+)\s*monat", "months"),
        (r"(\d+)\s*jahr", "years"),
        # English
        (r"(\d+)\s*day", "days"),
        (r"(\d+)\s*week", "weeks"),
        (r"(\d+)\s*month", "months"),
        (r"(\d+)\s*year", "years"),
    ]

    for pattern, unit in relative_patterns:
        match = re.search(pattern, text_lower)
        if match:
            value = int(match.group(1))
            if unit == "days":
                return now - timedelta(days=value)
            if unit == "weeks":
                return now - timedelta(weeks=value)
            if unit == "months":
                return now - timedelta(days=value * 30)
            if unit == "years":
                return now - timedelta(days=value * 365)

    # --- 4. Special cases ---
    if "heute" in text_lower or "today" in text_lower:
        return now
    if "gestern" in text_lower or "yesterday" in text_lower:
        return now - timedelta(days=1)

    return None


def parse_contact_info_modal(html: str) -> dict[str, Any]:
    """Parse the 'Kontaktinformationen' modal on a LinkedIn profile.

    Args:
        html: HTML content of the page with modal open

    Returns:
        Contact info dictionary
    """
    soup = BeautifulSoup(html, "html.parser")
    info: dict[str, Any] = {
        "email": None,
        "phone": None,
        "website": None,
        "twitter_url": None,
        "birthday": None,
        "address": None,
        "connected_date": None,
    }

    # The modal container
    modal_selectors = [
        ".pv-contact-info",
        '[class*="contact-info"]',
        ".artdeco-modal__content",
        'section[class*="ci-"]',
        "#artdeco-modal-outlet",
    ]

    modal = None
    for selector in modal_selectors:
        modal = soup.select_one(selector)
        if modal:
            break
    if not modal:
        modal = soup

    # Email
    for link in modal.select('a[href^="mailto:"]'):
        email = link.get("href", "").replace("mailto:", "").strip()
        if email and "@" in email:
            info["email"] = email
            break

    # Phone
    for link in modal.select('a[href^="tel:"]'):
        phone = link.get("href", "").replace("tel:", "").strip()
        if phone:
            info["phone"] = phone
            break

    # Website (skip LinkedIn/Twitter links)
    for link in modal.select('a[href*="://"]'):
        href = link.get("href", "")
        if href and "linkedin.com" not in href and "twitter.com" not in href and "x.com" not in href:
            info["website"] = href
            break

    # Twitter
    for link in modal.select('a[href*="twitter.com"], a[href*="x.com"]'):
        href = link.get("href", "")
        if href:
            info["twitter_url"] = href
            break

    # Birthday
    bday = modal.find(string=re.compile(r"Geburtstag|Birthday", re.IGNORECASE))
    if bday:
        parent = bday.find_parent()
        if parent:
            sibling = parent.find_next_sibling()
            if sibling:
                info["birthday"] = _clean_text(sibling.get_text())

    # Connected date
    conn = modal.find(string=re.compile(r"Verbunden seit|Connected on", re.IGNORECASE))
    if conn:
        parent = conn.find_parent()
        if parent:
            sibling = parent.find_next_sibling()
            if sibling:
                info["connected_date"] = _clean_text(sibling.get_text())

    # Address
    addr = modal.find(string=re.compile(r"Adresse|Address", re.IGNORECASE))
    if addr:
        parent = addr.find_parent()
        if parent:
            sibling = parent.find_next_sibling()
            if sibling:
                info["address"] = _clean_text(sibling.get_text())

    return info
