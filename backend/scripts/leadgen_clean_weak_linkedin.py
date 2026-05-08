"""Invalidate weak Serper-LinkedIn matches and re-queue their places.

Run after tightening the heuristic in ``linkedin_search.py`` so the existing
data reflects the new rules. The script:

1. Finds every ``leadgen_contacts`` / ``leadgen_places`` row whose stored
   linkedin URL fails the new tests:
     - confidence < 0.6
     - host outside the DACH/global allowlist (e.g. ``ua.linkedin.com``)
     - person /in/<slug> contains a firm-token (gmbh, ohg, kg, ag, gbr, ug, se)
2. NULLs the URL + match-method + confidence on those rows.
3. Removes ``enrichment_flags["linkedin_processed_at"]`` from each affected
   place so the next worker run re-evaluates them with the tightened rules.

Usage::

    python -m scripts.leadgen_clean_weak_linkedin --campaign 13 --dry-run
    python -m scripts.leadgen_clean_weak_linkedin --campaign 13
    python -m scripts.leadgen_clean_weak_linkedin                 # all tenants
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from sqlalchemy import select, update

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import async_session  # noqa: E402
from app.leadgen.linkedin_search import (  # noqa: E402
    _ALLOWED_HOSTS,
    _has_firm_slug,
    _slug_of,
)
from app.leadgen.models import LeadgenContact, LeadgenPlace  # noqa: E402

# Threshold used by the new heuristic — kept in sync via the imported
# ACCEPT_THRESHOLD attribute would be cleaner but the constant is documented
# directly here so a quick read of the script tells the operator the policy.
MIN_CONFIDENCE = 0.6


def _host_of(url: str) -> str:
    from urllib.parse import urlparse

    try:
        return (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""


def _is_weak_company(url: str | None, confidence: float | None) -> bool:
    if not url:
        return False
    if confidence is not None and confidence < MIN_CONFIDENCE:
        return True
    host = _host_of(url)
    return bool(host) and host not in _ALLOWED_HOSTS


def _is_weak_person(url: str | None, confidence: float | None) -> bool:
    if not url:
        return False
    if confidence is not None and confidence < MIN_CONFIDENCE:
        return True
    host = _host_of(url)
    if host and host not in _ALLOWED_HOSTS:
        return True
    return _has_firm_slug(url)


async def run(*, campaign_id: int | None, dry_run: bool) -> None:
    async with async_session() as db:
        # --- contacts: flag person URLs that fail the new rules ---
        contact_stmt = select(LeadgenContact).where(
            LeadgenContact.linkedin_url.isnot(None)
        )
        if campaign_id is not None:
            contact_stmt = contact_stmt.join(
                LeadgenPlace, LeadgenPlace.id == LeadgenContact.place_id
            ).where(LeadgenPlace.campaign_id == campaign_id)
        contacts = (await db.execute(contact_stmt)).scalars().all()
        contact_invalidate_ids: list[int] = []
        affected_place_ids: set[int] = set()
        for c in contacts:
            if _is_weak_person(c.linkedin_url, c.linkedin_match_confidence):
                contact_invalidate_ids.append(c.id)
                affected_place_ids.add(c.place_id)

        # --- places: same for the company URL ---
        place_stmt = select(LeadgenPlace).where(
            LeadgenPlace.linkedin_company_url.isnot(None)
        )
        if campaign_id is not None:
            place_stmt = place_stmt.where(LeadgenPlace.campaign_id == campaign_id)
        places = (await db.execute(place_stmt)).scalars().all()
        place_invalidate_ids: list[int] = []
        for p in places:
            # Company side has no separate confidence field — only the host
            # whitelist applies here. (Old runs didn't store the score.)
            host = _host_of(p.linkedin_company_url)
            if host and host not in _ALLOWED_HOSTS:
                place_invalidate_ids.append(p.id)
                affected_place_ids.add(p.id)

        prefix = "[dry-run] " if dry_run else ""
        print(
            f"{prefix}contacts to invalidate: {len(contact_invalidate_ids)}\n"
            f"{prefix}places (company URL) to invalidate: {len(place_invalidate_ids)}\n"
            f"{prefix}places to re-queue (clear linkedin_processed_at): "
            f"{len(affected_place_ids)}"
        )
        # Show a few sample slugs so the operator can sanity-check.
        for c in contacts:
            if _is_weak_person(c.linkedin_url, c.linkedin_match_confidence):
                print(
                    f"  contact #{c.id} {c.full_name!r} "
                    f"slug={_slug_of(c.linkedin_url)!r} "
                    f"host={_host_of(c.linkedin_url)!r} "
                    f"conf={c.linkedin_match_confidence}"
                )
        for p in places:
            host = _host_of(p.linkedin_company_url)
            if host and host not in _ALLOWED_HOSTS:
                print(
                    f"  place   #{p.id} {p.name!r} "
                    f"host={host!r}"
                )

        if dry_run:
            return

        if contact_invalidate_ids:
            await db.execute(
                update(LeadgenContact)
                .where(LeadgenContact.id.in_(contact_invalidate_ids))
                .values(
                    linkedin_url=None,
                    linkedin_match_method=None,
                    linkedin_match_confidence=None,
                )
            )
        if place_invalidate_ids:
            await db.execute(
                update(LeadgenPlace)
                .where(LeadgenPlace.id.in_(place_invalidate_ids))
                .values(
                    linkedin_company_url=None,
                    linkedin_company_match_method=None,
                )
            )
        # Clear the processed-at flag on every affected place so the worker
        # re-runs them with the new rules. We update each place individually
        # to avoid the JSONB minus-key portability issue across PG/SQLite.
        if affected_place_ids:
            for place_id in affected_place_ids:
                p = (
                    await db.execute(
                        select(LeadgenPlace).where(LeadgenPlace.id == place_id)
                    )
                ).scalar_one()
                flags = dict(p.enrichment_flags or {})
                flags.pop("linkedin_processed_at", None)
                p.enrichment_flags = flags
        await db.commit()
        print(
            f"✅ invalidated {len(contact_invalidate_ids)} contact URLs, "
            f"{len(place_invalidate_ids)} company URLs, "
            f"re-queued {len(affected_place_ids)} places."
        )


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--campaign", type=int, help="Limit to one campaign id")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    asyncio.run(run(campaign_id=args.campaign, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
