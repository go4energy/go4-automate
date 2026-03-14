"""Shared source fetching utilities for Collector and Briefing modules."""

from datetime import datetime

import feedparser
import httpx

from app.exceptions import ExternalServiceError


def matches_keywords(title: str, text: str, keywords: list[str]) -> bool:
    """Check if title or text contains any of the keywords (case-insensitive)."""
    combined = (title + " " + text).lower()
    return any(kw in combined for kw in keywords)


async def fetch_rss(url: str, keywords: list[str] | None = None) -> list[dict]:
    """Fetch and filter RSS feed entries."""
    feed = feedparser.parse(url)
    kw_lower = [k.lower() for k in (keywords or [])]
    items: list[dict] = []

    for entry in feed.entries[:50]:
        title = entry.get("title", "")
        summary = entry.get("summary", "")
        link = entry.get("link", "")

        if kw_lower and not matches_keywords(title, summary, kw_lower):
            continue

        published = entry.get("published_parsed")
        found_at = datetime(*published[:6]) if published else datetime.utcnow()

        items.append(
            {
                "title": title[:500],
                "summary": summary[:1000] if summary else None,
                "url": link,
                "found_at": found_at,
            }
        )

    return items


async def fetch_website(
    url: str,
    keywords: list[str] | None = None,
    selector: str = "article, .post, .entry",
) -> list[dict]:
    """Scrape a website for articles matching keywords."""
    from urllib.parse import urljoin

    from bs4 import BeautifulSoup

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url)
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    kw_lower = [k.lower() for k in (keywords or [])]
    items: list[dict] = []

    articles = soup.select(selector)
    if not articles:
        articles = soup.find_all(["article", "h2", "h3"])

    for article in articles[:30]:
        title_el = article.find(["h1", "h2", "h3", "a"])
        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            continue

        link_el = article.find("a", href=True)
        link = link_el["href"] if link_el else url
        if link.startswith("/"):
            link = urljoin(url, link)

        snippet_el = article.find("p")
        snippet = snippet_el.get_text(strip=True)[:500] if snippet_el else None

        if kw_lower and not matches_keywords(title, snippet or "", kw_lower):
            continue

        items.append(
            {
                "title": title[:500],
                "summary": snippet,
                "url": link,
                "content_snippet": snippet,
                "found_at": datetime.utcnow(),
            }
        )

    return items


async def fetch_websearch(keywords: list[str], serper_api_key: str) -> list[dict]:
    """Search via Serper API."""
    if not serper_api_key:
        raise ExternalServiceError("Serper", "API Key nicht konfiguriert")

    query = " ".join(keywords)
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://google.serper.dev/search",
            headers={
                "X-API-KEY": serper_api_key,
                "Content-Type": "application/json",
            },
            json={"q": query, "num": 10},
        )
        resp.raise_for_status()

    data = resp.json()
    items: list[dict] = []

    for result in data.get("organic", [])[:10]:
        items.append(
            {
                "title": result.get("title", "")[:500],
                "summary": result.get("snippet", "")[:1000],
                "url": result.get("link", ""),
                "found_at": datetime.utcnow(),
            }
        )

    return items


async def fetch_calendar(
    access_token: str, provider: str, days_back: int = 7
) -> list[dict]:
    """Fetch calendar events from Microsoft Graph or Google Calendar API."""
    from datetime import timedelta

    headers = {"Authorization": f"Bearer {access_token}"}
    now = datetime.utcnow()
    start = (now - timedelta(days=days_back)).isoformat() + "Z"
    end = now.isoformat() + "Z"

    async with httpx.AsyncClient(timeout=30) as client:
        if provider == "microsoft":
            url = (
                "https://graph.microsoft.com/v1.0/me/calendarView"
                f"?startDateTime={start}&endDateTime={end}"
                "&$top=50&$orderby=start/dateTime"
            )
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            events = resp.json().get("value", [])
            return [
                {
                    "title": e.get("subject", "")[:500],
                    "summary": e.get("bodyPreview", "")[:1000] or None,
                    "url": e.get("webLink", ""),
                    "found_at": datetime.fromisoformat(
                        e["start"]["dateTime"].rstrip("Z")
                    ),
                }
                for e in events
            ]
        else:
            url = (
                "https://www.googleapis.com/calendar/v3/calendars/primary/events"
                f"?timeMin={start}&timeMax={end}"
                "&maxResults=50&orderBy=startTime&singleEvents=true"
            )
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            events = resp.json().get("items", [])
            return [
                {
                    "title": e.get("summary", "")[:500],
                    "summary": (e.get("description", "") or "")[:1000] or None,
                    "url": e.get("htmlLink", ""),
                    "found_at": datetime.fromisoformat(
                        e["start"]
                        .get("dateTime", e["start"].get("date", ""))
                        .rstrip("Z")
                    ),
                }
                for e in events
            ]


async def fetch_emails(
    access_token: str,
    provider: str,
    days_back: int = 7,
    keywords: list[str] | None = None,
) -> list[dict]:
    """Fetch emails from Microsoft Graph or Gmail API."""
    from datetime import timedelta

    headers = {"Authorization": f"Bearer {access_token}"}
    since = (datetime.utcnow() - timedelta(days=days_back)).isoformat() + "Z"
    kw_lower = [k.lower() for k in (keywords or [])]

    async with httpx.AsyncClient(timeout=30) as client:
        if provider == "microsoft":
            url = (
                "https://graph.microsoft.com/v1.0/me/messages"
                f"?$top=50&$orderby=receivedDateTime desc"
                f"&$filter=receivedDateTime ge {since}"
            )
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            messages = resp.json().get("value", [])
            items: list[dict] = []
            for msg in messages:
                title = msg.get("subject", "")
                preview = msg.get("bodyPreview", "")
                if kw_lower and not matches_keywords(title, preview, kw_lower):
                    continue
                items.append(
                    {
                        "title": title[:500],
                        "summary": preview[:1000] or None,
                        "url": msg.get("webLink", ""),
                        "found_at": datetime.fromisoformat(
                            msg["receivedDateTime"].rstrip("Z")
                        ),
                        "metadata": {
                            "is_unread": not bool(msg.get("isRead", False)),
                            "from": (
                                ((msg.get("from") or {}).get("emailAddress") or {}).get(
                                    "address"
                                )
                            ),
                        },
                    }
                )
            return items
        else:
            ts = int((datetime.utcnow() - timedelta(days=days_back)).timestamp())
            query = f"after:{ts}"
            if keywords:
                query += f" ({' OR '.join(keywords)})"
            url = (
                "https://www.googleapis.com/gmail/v1/users/me/messages"
                f"?q={query}&maxResults=50"
            )
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            msg_list = resp.json().get("messages", [])
            items = []
            for msg_ref in msg_list[:50]:
                detail_resp = await client.get(
                    f"https://www.googleapis.com/gmail/v1/users/me/messages/{msg_ref['id']}"
                    "?format=metadata&metadataHeaders=Subject&metadataHeaders=From",
                    headers=headers,
                )
                if detail_resp.status_code != 200:
                    continue
                msg_data = detail_resp.json()
                hdrs = {
                    h["name"]: h["value"]
                    for h in msg_data.get("payload", {}).get("headers", [])
                }
                title = hdrs.get("Subject", "")
                snippet = msg_data.get("snippet", "")
                if kw_lower and not matches_keywords(title, snippet, kw_lower):
                    continue
                items.append(
                    {
                        "title": title[:500],
                        "summary": snippet[:1000] or None,
                        "url": f"https://mail.google.com/mail/#inbox/{msg_ref['id']}",
                        "found_at": datetime.fromtimestamp(
                            int(msg_data.get("internalDate", "0")) / 1000
                        ),
                        "metadata": {
                            "is_unread": "UNREAD" in msg_data.get("labelIds", []),
                            "from": hdrs.get("From"),
                        },
                    }
                )
            return items
