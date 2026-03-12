"""LinkedIn profile extraction using componentkey selectors + HTML parsing.

Uses LinkedIn's reliable componentkey section markers to extract
section HTML, then parses with BeautifulSoup for structured data.

CSS class markers (stable across all tested profiles):
    _5e021eff = bold/title text (job title, school name, cert name)
    ebe34298  = secondary text (company, dates, location)
    b329cd84  = metadata sub-variant of ebe34298
    f4bce9df  = description paragraph
    _48535f43  = lighter/tertiary text
"""

import re
from typing import Any

from bs4 import BeautifulSoup, Tag
from loguru import logger

# CSS class constants used by LinkedIn (verified across 10+ profiles)
CLS_TITLE = "_5e021eff"
CLS_META = "ebe34298"
CLS_META_SUB = "b329cd84"
CLS_DESC = "f4bce9df"
CLS_CONTACT_FIELD = "_5de606fd"

# ============================================================
# JavaScript: Extract section HTML via componentkey
# ============================================================

EXTRACT_SECTIONS_JS = """
() => {
    const sections = {};

    function findSectionHtml(suffix) {
        const el = document.querySelector(`[componentkey$="${suffix}"]`);
        return el ? el.innerHTML : null;
    }

    // Main profile sections -> innerHTML for structured parsing
    sections.topcard = findSectionHtml('Topcard');
    sections.about = findSectionHtml('About');
    sections.experience = findSectionHtml('ExperienceTopLevelSection');
    sections.education = findSectionHtml('EducationTopLevelSection');
    sections.skills = findSectionHtml('Skills');
    sections.languages = findSectionHtml('LanguageTopLevel');
    sections.certifications = findSectionHtml('CertificationTopLevel');
    sections.volunteering = findSectionHtml('VolunteerExperienceTopLevel');
    sections.recommendations = findSectionHtml('RecommendationsTopLevel');
    sections.causes = findSectionHtml('Causes');

    // Activity -> innerText (only need hashtags, HTML too large)
    const actEl = document.querySelector('[componentkey$="Activity"]');
    if (actEl) {
        sections.activity = actEl.innerText.substring(0, 3000);
    }

    // Profile picture URL (NOT the banner)
    const profileImg = document.querySelector(
        '[componentkey$="Topcard"] img[src*="profile-displayphoto"]'
    );
    if (profileImg) {
        sections._profile_picture_url = profileImg.src;
    } else {
        // Fallback: profile pic is always inside a button or link, banner is not
        const avatarImg = document.querySelector(
            '[componentkey$="Topcard"] button img[src*="media.licdn.com"], ' +
            '[componentkey$="Topcard"] a img[src*="media.licdn.com"][width="200"]'
        );
        if (avatarImg) {
            sections._profile_picture_url = avatarImg.src;
        }
    }

    // Company URLs from experience
    const expSection = document.querySelector('[componentkey$="ExperienceTopLevelSection"]');
    if (expSection) {
        const urls = [];
        expSection.querySelectorAll('a[href*="/company/"]').forEach(a => {
            urls.push(a.href.split('?')[0]);
        });
        sections._company_urls = [...new Set(urls)];
    }

    // Follower/connection counters from topcard
    const topcard = document.querySelector('[componentkey$="Topcard"]');
    if (topcard) {
        const counters = [];
        topcard.querySelectorAll('span, p, a').forEach(el => {
            const t = el.innerText?.trim();
            if (t && (t.includes('Follower') || t.includes('follower') ||
                t.includes('Kontakte') || t.includes('connections'))) {
                if (t.length < 80) counters.push(t);
            }
        });
        sections._counters = counters;
    }

    // Premium badge
    const premiumBadge = document.querySelector(
        '[componentkey$="Topcard"] [data-icon="verified-medium"], ' +
        '[componentkey$="Topcard"] [data-icon="verified-small"], ' +
        '[componentkey$="Topcard"] use[href*="verified"]'
    );
    sections._is_premium = !!premiumBadge;

    // Profile URN from messaging link
    const msgLink = document.querySelector('a[href*="messaging/compose/?profileUrn="]');
    if (msgLink) {
        const urnMatch = msgLink.href.match(/profileUrn=([^&]+)/);
        if (urnMatch) {
            sections._profile_urn = decodeURIComponent(urnMatch[1]);
        }
        sections._messaging_url = msgLink.href;
    }

    return sections;
}
"""

# ============================================================
# JavaScript: Extract contact info from modal (HTML-based)
# ============================================================

EXTRACT_CONTACT_INFO_JS = """
() => {
    const result = {};

    // Email - most reliable: mailto link
    const mailtoLink = document.querySelector('a[href^="mailto:"]');
    if (mailtoLink) {
        result.email = mailtoLink.href.replace('mailto:', '').trim();
    }

    // Find all contact info field containers
    // Pattern: div contains p._5e021eff (label) + p.ebe34298 (value)
    // We iterate through label elements and read the value sibling
    const labels = document.querySelectorAll('p._5e021eff');
    for (const label of labels) {
        const text = label.innerText.trim();
        const parent = label.parentElement;
        if (!parent) continue;

        const valueParagraph = parent.querySelector('p.ebe34298');
        const value = valueParagraph ? valueParagraph.innerText.trim() : '';

        if (text === 'Telefon' || text === 'Phone') {
            // Phone number is in span._8f670afa inside the value paragraph
            const phoneSpan = parent.querySelector('span._8f670afa');
            if (phoneSpan) {
                result.phone = phoneSpan.innerText.trim();
            } else if (value) {
                // Fallback: extract digits from value
                const digits = value.replace(/[^\\d+]/g, '');
                if (digits.length >= 7) {
                    result.phone = digits;
                }
            }
        } else if (text === 'Geburtstag' || text === 'Birthday') {
            if (value) result.birthday = value;
        } else if (text.includes('Vernetzt seit') || text.includes('Connected since')) {
            if (value) result.connected_since = value;
        } else if (text.includes('Website') || text.includes('Webseite')) {
            const link = parent.querySelector('a[href]');
            if (link) {
                result.website = link.href;
            } else if (value) {
                result.website = value;
            }
        } else if (text.includes('Twitter') || text.includes('X (')) {
            const link = parent.querySelector('a[href]');
            if (link) result.twitter_url = link.href;
        } else if (text.includes('Adresse') || text.includes('Address')) {
            if (value) result.address = value;
        }
    }

    return result;
}
"""

# ============================================================
# JavaScript: Extract interests from interests page
# ============================================================

EXTRACT_INTERESTS_JS = """
() => {
    const result = {
        companies: [],
        groups: [],
        newsletters: [],
        schools: [],
        influencers: []
    };

    const mainContent = document.querySelector('[role="main"]');
    if (!mainContent) return result;

    // Use data-view-name and href to categorize cleanly
    // Company interests
    mainContent.querySelectorAll('a[href*="/company/"]').forEach(a => {
        const nameEl = a.querySelector('p._5e021eff');
        if (nameEl) {
            result.companies.push(nameEl.innerText.trim());
        }
    });

    // School interests
    mainContent.querySelectorAll('a[href*="/school/"]').forEach(a => {
        const nameEl = a.querySelector('p._5e021eff');
        if (nameEl) {
            result.schools.push(nameEl.innerText.trim());
        }
    });

    // Group interests
    mainContent.querySelectorAll('a[href*="/groups/"]').forEach(a => {
        const nameEl = a.querySelector('p._5e021eff');
        if (nameEl) {
            result.groups.push(nameEl.innerText.trim());
        }
    });

    // Influencer/person interests
    mainContent.querySelectorAll('a[href*="/in/"]').forEach(a => {
        const nameEl = a.querySelector('p._5e021eff');
        if (nameEl) {
            const name = nameEl.innerText.trim();
            if (name.length > 2 && name.length < 100) {
                result.influencers.push(name);
            }
        }
    });

    // Newsletter interests
    mainContent.querySelectorAll('a[href*="/newsletters/"]').forEach(a => {
        const nameEl = a.querySelector('p._5e021eff');
        if (nameEl) {
            result.newsletters.push(nameEl.innerText.trim());
        }
    });

    // Deduplicate
    result.companies = [...new Set(result.companies)];
    result.groups = [...new Set(result.groups)];
    result.schools = [...new Set(result.schools)];
    result.influencers = [...new Set(result.influencers)];
    result.newsletters = [...new Set(result.newsletters)];

    return result;
}
"""


# ============================================================
# Python HTML parsers
# ============================================================


def _soup(html: str) -> BeautifulSoup:
    """Create BeautifulSoup from HTML string."""
    return BeautifulSoup(html, "lxml")


def _find_titles(container: Tag) -> list[Tag]:
    """Find all title paragraphs (p._5e021eff) in a container."""
    return container.find_all("p", class_=lambda c: c and CLS_TITLE in c)


def _find_metas(container: Tag) -> list[Tag]:
    """Find all meta paragraphs (p.ebe34298.b329cd84) in a container."""
    return container.find_all(
        "p", class_=lambda c: c and CLS_META in c and CLS_META_SUB in c
    )


def _get_text(tag: Tag | None) -> str:
    """Get clean text from a tag, stripping button texts."""
    if not tag:
        return ""
    # Remove expandable-text-button elements before getting text
    for btn in tag.find_all("button", attrs={"data-testid": "expandable-text-button"}):
        btn.decompose()
    return tag.get_text(strip=True)


def _get_expandable_text(container: Tag) -> str | None:
    """Get full text from expandable-text-box (always contains complete text)."""
    span = container.find("span", attrs={"data-testid": "expandable-text-box"})
    if span:
        return _get_text(span)
    return None


def parse_topcard_html(html: str) -> dict[str, Any]:
    """Parse the topcard section HTML.

    Returns dict with name, headline, location, company_name,
    follower_count, connection_count.
    """
    if not html:
        return {}

    soup = _soup(html)
    result: dict[str, Any] = {}

    titles = _find_titles(soup)
    metas = soup.find_all("p", class_=lambda c: c and CLS_META in c)

    # Name is in h2 (NOT in p._5e021eff which is the headline)
    h2 = soup.find("h2")
    if h2:
        result["name"] = _get_text(h2)

    # Headline is the first title element (p._5e021eff)
    if titles:
        result["headline"] = _get_text(titles[0])

    # Location — look for location keywords in meta texts
    for tag in metas:
        text = _get_text(tag)
        if any(
            kw in text
            for kw in [
                "und Umgebung",
                "Area",
                "Deutschland",
                "Germany",
                "\u00d6sterreich",
                "Austria",
                "Schweiz",
                "Switzerland",
                "United Kingdom",
                "United States",
                "France",
                "Netherlands",
                "Polen",
                "Poland",
            ]
        ):
            result["location"] = text.rstrip(" \u00b7")
            break
        if re.match(r"^[A-Z\u00c4\u00d6\u00dc][a-z\u00e4\u00f6\u00fc\u00df]+,\s", text):
            result["location"] = text.rstrip(" \u00b7")
            break

    # Company — from figure aria-label ("Logo von {Company}")
    company_fig = soup.find(
        "figure", attrs={"aria-label": lambda v: v and v.startswith("Logo von ")}
    )
    if company_fig:
        label = company_fig.get("aria-label", "")
        result["company_name"] = label.replace("Logo von ", "").strip()

    # Fallback: company from meta text (first short meta that's not location/UI)
    if not result.get("company_name"):
        skip = {
            result.get("headline"),
            result.get("location"),
            "Kontaktinformationen",
            "Nachricht",
        }
        for tag in metas:
            text = _get_text(tag)
            if (
                text not in skip
                and 3 < len(text) < 60
                and not text.startswith("\u00b7")
                and "Follower" not in text
                and "Kontakte" not in text
                and "Sales Navigator" not in text
                and "Offen f\u00fcr" not in text
            ):
                # Multi-entity: take first
                if " \u00b7 " in text:
                    result["company_name"] = text.split(" \u00b7 ")[0].strip()
                else:
                    result["company_name"] = text
                break

    # Follower and connection counts from _counters (passed separately)

    return result


def parse_about_html(html: str) -> dict[str, Any]:
    """Parse the About section HTML.

    Full text is always in span[data-testid="expandable-text-box"].
    """
    if not html:
        return {}

    soup = _soup(html)
    result: dict[str, Any] = {}

    # Full summary text from expandable box
    full_text = _get_expandable_text(soup)
    if full_text:
        result["summary"] = full_text
    else:
        # Fallback: get text from first p.ebe34298
        meta = soup.find("p", class_=lambda c: c and CLS_META in c)
        if meta:
            result["summary"] = _get_text(meta)

    # Top skills box
    top_skills_label = soup.find(
        "p",
        class_=lambda c: c and CLS_TITLE in c,
        string=lambda s: s and ("Top-Kenntnisse" in s or "Top Skills" in s),
    )
    if top_skills_label:
        skills_text_el = top_skills_label.find_next_sibling(
            "p", class_=lambda c: c and CLS_META in c
        )
        if skills_text_el:
            skills_text = _get_text(skills_text_el)
            skills = [
                s.strip()
                for s in re.split(r"\s*[•·]\s*", skills_text)
                if s.strip() and len(s.strip()) < 100
            ]
            if skills:
                result["top_skills"] = skills

    return result


def parse_experience_html(html: str) -> list[dict[str, Any]]:
    """Parse experience section HTML into structured entries.

    Uses HTML structure: p._5e021eff = title, p.ebe34298 = meta fields.
    Multi-position companies: all in one entity-collection-item,
    first TITLE = company, first META = total duration, then sub-positions.
    """
    if not html:
        return []

    soup = _soup(html)
    entries: list[dict[str, Any]] = []

    # Find entity-collection-items (multi-position companies)
    collection_items = soup.find_all(
        attrs={"componentkey": lambda v: v and "entity-collection-item" in v}
    )

    # Also find "standalone" experience entries (not in collection items)
    # These are separated by hr[role="presentation"]

    # Strategy: Parse ALL p elements in order, grouped by hr separators
    # and entity-collection-items

    def _parse_entry_sequence(container: Tag) -> list[dict[str, Any]]:
        """Parse a sequence of TITLE/META elements into experience entries."""
        all_ps = container.find_all("p", recursive=True)
        typed_elements = []
        for p_tag in all_ps:
            classes = p_tag.get("class", [])
            if CLS_TITLE in classes:
                typed_elements.append(("TITLE", _get_text(p_tag)))
            elif CLS_META in classes and CLS_META_SUB in classes:
                typed_elements.append(("META", _get_text(p_tag)))
            elif CLS_DESC in classes:
                # Get full text from expandable box if available
                full = _get_expandable_text(p_tag)
                if full:
                    typed_elements.append(("DESC", full))
                else:
                    text = _get_text(p_tag)
                    if text:
                        typed_elements.append(("DESC", text))

        # Also collect non-b329cd84 meta (skills lines)
        for p_tag in container.find_all("p", recursive=True):
            classes = p_tag.get("class", [])
            if (
                CLS_META in classes
                and CLS_META_SUB not in classes
                and CLS_TITLE not in classes
            ):
                text = _get_text(p_tag)
                if text and (
                    "Kenntnisse" in text or "Skills" in text or "skills" in text
                ):
                    typed_elements.append(("SKILLS", text))

        return _build_entries_from_elements(typed_elements)

    def _build_entries_from_elements(
        elements: list[tuple[str, str]],
    ) -> list[dict[str, Any]]:
        """Build experience entries from typed element sequence."""
        result_entries: list[dict[str, Any]] = []
        current: dict[str, Any] = {}

        for etype, text in elements:
            if not text:
                continue

            if etype == "TITLE":
                # Career break detection
                if text in ("Karriereübergang", "Career break", "Berufliche Auszeit"):
                    if current.get("title"):
                        result_entries.append(current)
                    current = {"title": text, "is_career_break": True}
                    continue

                # New title starts a new entry
                if current.get("title"):
                    result_entries.append(current)
                current = {"title": text}

            elif etype == "META":
                if not current:
                    continue
                # Classify meta text
                _classify_meta(current, text)

            elif etype == "DESC":
                if current:
                    current["description"] = text

            elif etype == "SKILLS":
                if current:
                    current.setdefault("skills", [])
                    skill_text = re.sub(r"\s+und\s+\+\d+\s+Kenntnisse", "", text)
                    skill_text = re.sub(
                        r"\s+and\s+\+\d+\s+skills?", "", skill_text, flags=re.IGNORECASE
                    )
                    for s in re.split(r",\s*", skill_text):
                        s = s.strip()
                        if s and len(s) < 100 and "Kenntnisse" not in s:
                            current["skills"].append(s)

        if current.get("title"):
            result_entries.append(current)

        return result_entries

    # Process entity-collection-items (multi-position companies)
    collection_titles = set()
    for item in collection_items:
        sub_entries = _parse_entry_sequence(item)
        if len(sub_entries) > 1:
            # Multi-position: first entry is the company header
            # (title = company name, duration = total time)
            company_header = sub_entries[0]
            company_name = company_header.get("title", "")
            collection_titles.add(company_name)
            # Sub-entries get the company name
            for entry in sub_entries[1:]:
                entry["company"] = company_name
                collection_titles.add(entry.get("title", ""))
                entries.append(entry)
        elif sub_entries:
            collection_titles.add(sub_entries[0].get("title", ""))
            entries.append(sub_entries[0])

    # Parse all entries from the full section
    all_entries = _parse_entry_sequence(soup)
    # Add entries not already covered by collection items
    for entry in all_entries:
        if entry.get("title") not in collection_titles:
            entries.append(entry)

    return entries


def _classify_meta(entry: dict[str, Any], text: str) -> None:
    """Classify a META text and assign it to the right field."""
    # Company · Employment Type
    emp_match = re.match(
        r"^(.+?)\s*[·•]\s*(Vollzeit|Teilzeit|Selbstst.ndig|Freelance|"
        r"Full-time|Part-time|Self-employed|Contract|Internship|"
        r"Praktikum|Ausbildung|Werkstudent|Volunteer|Freiwillig|"
        r"Duales Studium)",
        text,
    )
    if emp_match:
        entry["company"] = emp_match.group(1).strip()
        entry["employment_type"] = emp_match.group(2).strip()
        return

    # Just employment type without company
    if text in (
        "Vollzeit",
        "Teilzeit",
        "Selbstständig",
        "Freelance",
        "Full-time",
        "Part-time",
        "Self-employed",
        "Contract",
        "Internship",
        "Praktikum",
        "Ausbildung",
        "Werkstudent",
        "Duales Studium",
    ):
        entry["employment_type"] = text
        return

    # Date range (contains month + year + dash)
    date_match = re.match(
        r"^(?:Jan|Feb|M\u00e4r|Apr|Mai|Jun|Jul|Aug|Sep|Okt|Nov|Dez|"
        r"Mar|May|Oct|Dec)\.?\s*\d{4}\s*[-\u2013]",
        text,
    )
    if date_match:
        # Split date range and optional duration
        dur_match = re.match(r"^(.+?[-\u2013].+?)\s*(?:[·•]\s*(.+))?$", text)
        if dur_match:
            entry["date_range"] = dur_match.group(1).strip()
            if dur_match.group(2):
                entry["duration"] = dur_match.group(2).strip()
            entry["is_current"] = any(kw in text for kw in ("Heute", "Present"))
        return

    # Duration only (e.g. "11 Jahre 8 Monate")
    dur_only = re.match(r"^\d+\s+(?:Jahr|year|Monat|month)", text, re.IGNORECASE)
    if dur_only and not entry.get("date_range"):
        entry["duration"] = text
        return

    # Location (contains country/city keywords)
    if (
        re.search(
            r"(?:Deutschland|Germany|\u00d6sterreich|Austria|Schweiz|Switzerland|"
            r"United Kingdom|United States|France|Netherlands|Poland|"
            r"Hybrid|Remote|Vor Ort|On-site)\s*$",
            text,
        )
        and len(text) < 100
    ):
        entry["location"] = text
        return

    # Skills line
    if "Kenntnisse" in text or "skills" in text.lower():
        entry.setdefault("skills", [])
        skill_text = re.sub(r"\s+und\s+\+\d+\s+Kenntnisse", "", text)
        skill_text = re.sub(
            r"\s+and\s+\+\d+\s+skills?", "", skill_text, flags=re.IGNORECASE
        )
        for s in re.split(r",\s*", skill_text):
            s = s.strip()
            if s and len(s) < 100 and "Kenntnisse" not in s:
                entry["skills"].append(s)
        return

    # If nothing matched and no company yet, could be company name
    if not entry.get("company") and len(text) < 80:
        entry["company"] = text


def parse_education_html(html: str) -> list[dict[str, Any]]:
    """Parse education section HTML.

    Pattern per entry: TITLE = school, META = degree, META = years.
    Full description in expandable-text-box.
    Entries separated by hr[role="presentation"].
    """
    if not html:
        return []

    soup = _soup(html)
    entries: list[dict[str, Any]] = []

    # Get all p elements in order
    all_ps = soup.find_all("p", recursive=True)
    typed = []
    for p_tag in all_ps:
        classes = p_tag.get("class", [])
        text = _get_text(p_tag)
        if not text:
            continue
        if CLS_TITLE in classes:
            typed.append(("TITLE", text))
        elif CLS_META in classes and CLS_META_SUB in classes:
            typed.append(("META", text))

    # Get expandable descriptions
    expandable_texts = []
    for span in soup.find_all("span", attrs={"data-testid": "expandable-text-box"}):
        expandable_texts.append(_get_text(span))

    # Build entries: TITLE = school, first META = degree, second META = years
    current: dict[str, Any] = {}

    for etype, text in typed:
        if etype == "TITLE":
            if current.get("school"):
                entries.append(current)
            current = {"school": text}
        elif etype == "META":
            if not current:
                continue
            # Year range
            year_match = re.match(
                r"^(?:(\w+\.?\s+)?(\d{4}))\s*[-\u2013]\s*(?:(\w+\.?\s+)?(\d{4})|Heute|Present)\s*$",
                text,
            )
            if year_match:
                if year_match.group(2):
                    current["start_year"] = int(year_match.group(2))
                if year_match.group(4):
                    current["end_year"] = int(year_match.group(4))
                continue

            # Simple year range "2019-2021"
            simple_year = re.match(r"^(\d{4})\s*[-\u2013]\s*(\d{4})\s*$", text)
            if simple_year:
                current["start_year"] = int(simple_year.group(1))
                current["end_year"] = int(simple_year.group(2))
                continue

            # Grade
            if text.startswith("Note:") or text.startswith("Grade:"):
                current["grade"] = text.split(":", 1)[1].strip()
                continue

            # First meta after school is degree
            if "degree" not in current:
                current["degree"] = text
            else:
                # Additional meta — could be description snippet
                current.setdefault("details", [])
                current["details"].append(text)

    if current.get("school"):
        entries.append(current)

    # Attach expandable descriptions to entries
    for i, desc_text in enumerate(expandable_texts):
        if i < len(entries):
            entries[i]["description"] = desc_text

    return entries


def parse_skills_html(html: str) -> list[str]:
    """Parse skills section HTML.

    Each skill has componentkey containing 'profile.skill' and
    the skill name is in p._5e021eff.
    """
    if not html:
        return []

    soup = _soup(html)
    skills = []

    # Find skill items by componentkey pattern
    skill_items = soup.find_all(
        attrs={"componentkey": lambda v: v and "profile.skill" in v}
    )

    for item in skill_items:
        title = item.find("p", class_=lambda c: c and CLS_TITLE in c)
        if title:
            name = _get_text(title)
            if name and len(name) < 100:
                skills.append(name)

    # Fallback: if no skill items found, use title elements
    if not skills:
        for title in _find_titles(soup):
            name = _get_text(title)
            if (
                name
                and len(name) < 100
                and name
                not in (
                    "Kenntnisse",
                    "Skills",
                )
            ):
                skills.append(name)

    # Deduplicate
    seen = set()
    unique = []
    for s in skills:
        if s.lower() not in seen:
            seen.add(s.lower())
            unique.append(s)

    return unique


def parse_languages_html(html: str) -> list[dict[str, str]]:
    """Parse languages section HTML.

    Pattern: p._5e021eff = language name, p.ebe34298.b329cd84 = proficiency.
    Separated by hr[role="presentation"].
    """
    if not html:
        return []

    soup = _soup(html)
    languages = []

    titles = _find_titles(soup)

    # Skip section heading ("Sprachen" / "Languages")
    titles = [t for t in titles if _get_text(t) not in ("Sprachen", "Languages")]

    # Pair titles with next meta (proficiency)
    for title in titles:
        name = _get_text(title)
        if not name or name in ("Alle anzeigen", "Show all"):
            continue

        lang_entry: dict[str, str] = {"language": name}

        # Find the next meta sibling (proficiency)
        next_meta = title.find_next(
            "p", class_=lambda c: c and CLS_META in c and CLS_META_SUB in c
        )
        if next_meta:
            proficiency = _get_text(next_meta)
            proficiency_keywords = [
                "Muttersprache",
                "Native",
                "Verhandlungssicher",
                "Professional",
                "Flie\u00dfend",
                "Fluent",
                "Gute Kenntnisse",
                "Grundkenntnisse",
                "Limited",
                "Elementary",
                "Full professional",
            ]
            if any(kw.lower() in proficiency.lower() for kw in proficiency_keywords):
                lang_entry["proficiency"] = proficiency

        languages.append(lang_entry)

    return languages


def parse_certifications_html(html: str) -> list[dict[str, str]]:
    """Parse certifications section HTML.

    Pattern: p._5e021eff = cert name, first meta = issuer,
    second meta = issued date.
    """
    if not html:
        return []

    soup = _soup(html)
    certs = []

    titles = _find_titles(soup)
    # Skip heading
    titles = [
        t
        for t in titles
        if _get_text(t)
        not in (
            "Bescheinigungen und Zertifikate",
            "Licenses & certifications",
        )
    ]

    for title in titles:
        name = _get_text(title)
        if not name or name in ("Alle anzeigen", "Show all"):
            continue

        cert: dict[str, str] = {"name": name}

        # Find following meta elements (issuer, date)
        # Use find_next (not find_next_sibling) as they may be in nested divs
        meta_texts = []
        next_el = title.find_next("p")
        while next_el:
            classes = next_el.get("class", []) if isinstance(next_el, Tag) else []
            if CLS_TITLE in classes:
                break  # Next cert entry
            if CLS_META in classes:
                meta_texts.append(_get_text(next_el))
            next_el = next_el.find_next("p")

        for mt in meta_texts:
            if not mt:
                continue
            if re.match(r"^(?:Ausgestellt|Issued)", mt):
                cert["issued_date"] = re.sub(
                    r"^(?:Ausgestellt|Issued):?\s*", "", mt
                ).strip()
            elif "Nachweis-ID" in mt or "Credential ID" in mt:
                cert["credential_id"] = re.sub(
                    r"^(?:Nachweis-ID|Credential ID):?\s*", "", mt
                ).strip()
            elif "issuer" not in cert and len(mt) < 100:
                cert["issuer"] = mt

        certs.append(cert)

    return certs


# ============================================================
# Main extraction function
# ============================================================


def extract_profile_from_sections(sections: dict[str, Any]) -> dict[str, Any]:
    """Convert raw section HTML into a structured profile dict.

    Takes the output of EXTRACT_SECTIONS_JS and returns a profile
    dict ready for saving to the database.
    """
    profile: dict[str, Any] = {}

    # Parse topcard
    topcard = parse_topcard_html(sections.get("topcard", ""))
    profile.update(topcard)

    # Parse about
    about = parse_about_html(sections.get("about", ""))
    if about.get("summary"):
        profile["summary"] = about["summary"]
    if about.get("top_skills"):
        profile["top_skills"] = about["top_skills"]

    # Parse experience
    experience = parse_experience_html(sections.get("experience", ""))
    if experience:
        profile["experience"] = experience
        current = next(
            (e for e in experience if e.get("is_current")),
            experience[0] if experience else None,
        )
        if current:
            if current.get("title") and not profile.get("position"):
                profile["position"] = current["title"]
            if current.get("company") and not profile.get("company_name"):
                profile["company_name"] = current["company"]

    # Parse education
    education = parse_education_html(sections.get("education", ""))
    if education:
        profile["education"] = education

    # Parse skills
    skills = parse_skills_html(sections.get("skills", ""))
    if skills:
        profile["skills"] = skills

    # Parse languages
    languages = parse_languages_html(sections.get("languages", ""))
    if languages:
        profile["languages"] = languages

    # Parse certifications
    certs = parse_certifications_html(sections.get("certifications", ""))
    if certs:
        profile["certifications"] = certs

    # Volunteering — store raw text
    if sections.get("volunteering"):
        soup = _soup(sections["volunteering"])
        profile["volunteering_text"] = soup.get_text(separator="\n", strip=True)

    # Recommendations — store raw text
    if sections.get("recommendations"):
        soup = _soup(sections["recommendations"])
        profile["recommendations_text"] = soup.get_text(separator="\n", strip=True)

    # Activity text (for hashtags — still innerText, no HTML parsing needed)
    if sections.get("activity"):
        profile["activity_text"] = sections["activity"]
        hashtags = re.findall(r"#(\w+)", sections["activity"])
        if hashtags:
            profile["hashtags"] = list(dict.fromkeys(hashtags))[:20]

    # Metadata from JS extraction
    if sections.get("_profile_picture_url"):
        profile["profile_picture_url"] = sections["_profile_picture_url"]

    # Assign company URLs to experience entries (order matches DOM order)
    company_urls = sections.get("_company_urls", [])
    if company_urls and profile.get("experience"):
        # Deduplicated list — assign to entries that don't have one yet
        seen_companies: set[str] = set()
        url_idx = 0
        for exp in profile["experience"]:
            company = exp.get("company", "")
            if (
                company
                and company not in seen_companies
                and url_idx < len(company_urls)
            ):
                exp["company_linkedin_url"] = company_urls[url_idx]
                url_idx += 1
                seen_companies.add(company)
        # First company URL also at top level for current employer
        profile["company_linkedin_url"] = company_urls[0]
    elif company_urls:
        profile["company_linkedin_url"] = company_urls[0]

    if sections.get("_is_premium"):
        profile["is_premium"] = True

    if sections.get("_profile_urn"):
        profile["profile_urn"] = sections["_profile_urn"]

    if sections.get("_messaging_url"):
        profile["messaging_url"] = sections["_messaging_url"]

    # Counters from topcard
    counters = sections.get("_counters", [])
    for counter in counters:
        if not profile.get("follower_count"):
            m = re.search(r"([\d.]+)\s*Follower", counter)
            if m:
                val = m.group(1).replace(".", "")
                if val.isdigit():
                    profile["follower_count"] = int(val)
        if not profile.get("connection_count"):
            m = re.search(r"(\d+)\+?\s*Kontakte", counter)
            if m and m.group(1).isdigit():
                profile["connection_count"] = int(m.group(1))

    logger.debug(
        "Extracted profile: name={name}, headline={headline}, "
        "exp={exp_count}, edu={edu_count}, skills={skills_count}",
        name=profile.get("name", "?"),
        headline=profile.get("headline", "?")[:50],
        exp_count=len(profile.get("experience", [])),
        edu_count=len(profile.get("education", [])),
        skills_count=len(profile.get("skills", [])),
    )

    return profile
