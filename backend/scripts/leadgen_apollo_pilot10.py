"""Read-only 10-contact pilot: Serper vs Apollo LinkedIn-URL discovery.

Picks 5 contacts that already have a Serper-matched LinkedIn URL and 5 with
no URL at all, then runs the Apollo bulk_match endpoint against both groups
and prints a side-by-side comparison. **No DB writes** — purely diagnostic
so we can decide whether to commit to a 100-contact run.

Usage:
    cd backend && source .venv/bin/activate
    python scripts/leadgen_apollo_pilot10.py
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import async_session
from app.leadgen.apollo_client import bulk_match_people
from app.leadgen.models import LeadgenContact, LeadgenPlace


async def _pick_contacts(db, *, n: int, with_url: bool) -> list[LeadgenContact]:
    stmt = (
        select(LeadgenContact)
        .options(selectinload(LeadgenContact.place))
        .where(LeadgenContact.first_name.isnot(None))
        .where(LeadgenContact.last_name.isnot(None))
        .order_by(LeadgenContact.id.asc())
        .limit(n)
    )
    if with_url:
        stmt = stmt.where(LeadgenContact.linkedin_url.isnot(None))
    else:
        stmt = stmt.where(LeadgenContact.linkedin_url.is_(None))
    return list((await db.execute(stmt)).scalars().all())


def _row(label: str, c: LeadgenContact, profile: dict | None) -> str:
    name = f"{c.first_name} {c.last_name}".strip()
    place_name = c.place.name if c.place else "?"
    serper = c.linkedin_url or "—"
    if profile:
        apollo = profile.get("linkedin_url") or "—"
        title = profile.get("title") or "—"
        city = profile.get("city") or "—"
        seniority = profile.get("seniority") or "—"
    else:
        apollo = "(no_match)"
        title = "—"
        city = "—"
        seniority = "—"
    return (
        f"  [{label}] {name:<28}  @ {place_name[:34]:<34}\n"
        f"      Serper : {serper}\n"
        f"      Apollo : {apollo}\n"
        f"      Title  : {title}  ·  Seniority: {seniority}  ·  City: {city}\n"
    )


async def main() -> None:
    if not settings.apollo_api_key:
        print("ERROR: APOLLO_API_KEY is not set in env")
        return

    async with async_session() as db:
        with_url = await _pick_contacts(db, n=5, with_url=True)
        no_url = await _pick_contacts(db, n=5, with_url=False)
    contacts = with_url + no_url
    if not contacts:
        print("No eligible contacts.")
        return

    details = []
    for c in contacts:
        d: dict = {}
        # Don't pre-seed Apollo with the LinkedIn URL — we want to see if it
        # finds the same URL from name+org, otherwise the comparison is moot.
        if c.first_name:
            d["first_name"] = c.first_name
        if c.last_name:
            d["last_name"] = c.last_name
        if c.place is not None and c.place.name:
            d["organization_name"] = c.place.name
        details.append(d)

    print(f"Sending {len(details)} details to Apollo /people/bulk_match …")
    result = await bulk_match_people(
        details=details,
        api_key=settings.apollo_api_key,
        base_url=settings.apollo_api_base_url,
    )

    print()
    print("=== Apollo response ===")
    print(f"  status            : {result.raw_status}")
    print(f"  error             : {result.error}")
    print(f"  requested         : {result.requested}")
    print(f"  matched           : {result.matched}")
    print(f"  missing           : {result.missing}")
    print(f"  credits_consumed  : {result.credits_consumed}  ← realer Verbrauch")
    print()

    matches = list(result.matches)
    matches.extend([None] * (len(contacts) - len(matches)))

    print("=== With Serper URL (5) — does Apollo find the same? ===")
    for c, p in zip(with_url, matches[: len(with_url)]):
        print(_row("S+", c, p))

    print("=== Without Serper URL (5) — does Apollo find what Serper missed? ===")
    for c, p in zip(no_url, matches[len(with_url):]):
        print(_row("  ", c, p))

    n_with_apollo = sum(
        1 for p in matches if p and p.get("linkedin_url")
    )
    n_with_serper = sum(1 for c in contacts if c.linkedin_url)
    same = sum(
        1
        for c, p in zip(contacts, matches)
        if p and c.linkedin_url and (p.get("linkedin_url") or "").rstrip("/") ==
        (c.linkedin_url or "").rstrip("/")
    )
    print("=== Summary ===")
    print(f"  Serper-URLs present : {n_with_serper}/10")
    print(f"  Apollo-URLs found   : {n_with_apollo}/10")
    print(f"  Same URL (S∩A)      : {same}/{n_with_serper}")
    print(f"  Apollo-credits used : {result.credits_consumed}")


if __name__ == "__main__":
    asyncio.run(main())
