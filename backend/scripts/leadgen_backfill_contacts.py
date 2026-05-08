"""Backfill leadgen_contacts from existing leadgen_impressum + leadgen_llm_insights.

For every place we already enriched, this script materialises one
``LeadgenContact`` row per discovered person (managing director or primary
contact). It runs the offline ``gender_guesser`` library on the first names so
salutations are populated without extra API cost, and honours any gender that
a previous LLM run already wrote into ``LeadgenLLMInsights.primary_contact``.

The script is **idempotent**: it relies on the
``uq_leadgen_contacts_place_name`` unique constraint and a SELECT-then-INSERT
pattern, so running it twice never produces duplicates and never overwrites
fields that were edited manually after the first run.

Usage::

    cd backend && source .venv/bin/activate
    python -m scripts.leadgen_backfill_contacts            # all tenants
    python -m scripts.leadgen_backfill_contacts --tenant go4energy
    python -m scripts.leadgen_backfill_contacts --campaign 13
    python -m scripts.leadgen_backfill_contacts --dry-run

Cost: zero — fully offline.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import selectinload

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import async_session  # noqa: E402
from app.leadgen.contact_normalize import (  # noqa: E402
    from_managing_director_string,
    from_primary_contact_dict,
    normalize_full_name,
)
from app.leadgen.gender import guess_gender_from_first_name  # noqa: E402
from app.leadgen.models import (  # noqa: E402
    LeadgenContact,
    LeadgenImpressum,
    LeadgenLLMInsights,
    LeadgenPlace,
)


def _enrich_with_library_gender(payload: dict) -> dict:
    """Fill gender from gender_guesser when the payload doesn't have one yet."""
    if payload.get("gender"):
        return payload
    gender, confidence, method = guess_gender_from_first_name(
        payload.get("first_name")
    )
    if gender is not None:
        payload["gender"] = gender
        payload["gender_confidence"] = confidence
        payload["gender_method"] = method
    return payload


async def _existing_full_names(db, place_id: int) -> set[str]:
    rows = await db.execute(
        select(LeadgenContact.full_name).where(LeadgenContact.place_id == place_id)
    )
    return {(r[0] or "").lower() for r in rows.all()}


async def _backfill_place(
    db, place: LeadgenPlace, *, dry_run: bool
) -> tuple[int, int]:
    """Return (created, skipped_duplicates) counters for a single place."""
    candidates: list[dict] = []

    # 1) Primary contact from LLM insights (carries gender if set).
    if place.llm_insights and place.llm_insights.primary_contact:
        payload = from_primary_contact_dict(place.llm_insights.primary_contact)
        if payload:
            candidates.append(payload)

    # 2) Managing directors from Impressum (raw name strings).
    if place.impressum and place.impressum.managing_directors:
        for raw in place.impressum.managing_directors:
            if not isinstance(raw, str):
                continue
            payload = from_managing_director_string(raw)
            if payload:
                candidates.append(payload)

    if not candidates:
        return 0, 0

    # Email + phone come from impressum (one per place, applied to all rows).
    email = place.impressum.email if place.impressum else None
    phone = place.impressum.phone if place.impressum else None

    existing = await _existing_full_names(db, place.id)
    created = 0
    skipped = 0
    seen_in_batch: set[str] = set()
    for payload in candidates:
        normalised = normalize_full_name(payload["full_name"])
        key = normalised.lower()
        if key in existing or key in seen_in_batch:
            skipped += 1
            continue
        seen_in_batch.add(key)

        payload = _enrich_with_library_gender(payload)
        payload.setdefault("email", email)
        payload.setdefault("phone", phone)

        if dry_run:
            created += 1
            continue

        # Truncate to column lengths so legacy rows with a paragraph-long
        # ``role`` (e.g. the LLM occasionally returns a full sentence) still
        # backfill cleanly.
        def _trim(v: str | None, n: int) -> str | None:
            if v is None:
                return None
            return str(v)[:n]

        row = LeadgenContact(
            tenant_id=place.tenant_id,
            place_id=place.id,
            first_name=_trim(payload.get("first_name"), 100),
            last_name=_trim(payload.get("last_name"), 100),
            full_name=_trim(normalised, 200) or normalised[:200],
            role=_trim(payload.get("role"), 100),
            email=_trim(payload.get("email"), 320),
            phone=_trim(payload.get("phone"), 50),
            gender=payload.get("gender"),
            gender_confidence=payload.get("gender_confidence"),
            gender_method=payload.get("gender_method"),
            source=payload["source"],
        )
        db.add(row)
        created += 1
    return created, skipped


async def run(
    *, tenant: str | None, campaign_id: int | None, dry_run: bool
) -> None:
    async with async_session() as db:
        stmt = (
            select(LeadgenPlace)
            .options(
                selectinload(LeadgenPlace.impressum),
                selectinload(LeadgenPlace.llm_insights),
            )
            .order_by(LeadgenPlace.id)
        )
        if tenant:
            stmt = stmt.where(LeadgenPlace.tenant_id == tenant)
        if campaign_id is not None:
            stmt = stmt.where(LeadgenPlace.campaign_id == campaign_id)

        result = await db.execute(stmt)
        places = list(result.scalars())

        total_created = 0
        total_skipped = 0
        places_touched = 0
        for place in places:
            created, skipped = await _backfill_place(db, place, dry_run=dry_run)
            if created or skipped:
                places_touched += 1
            total_created += created
            total_skipped += skipped

        if not dry_run:
            await db.commit()

        prefix = "[dry-run] " if dry_run else ""
        print(
            f"{prefix}places scanned: {len(places)}, "
            f"places with new contacts: {places_touched}, "
            f"contacts created: {total_created}, "
            f"duplicates skipped: {total_skipped}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tenant", help="Limit to one tenant_id")
    parser.add_argument(
        "--campaign", type=int, help="Limit to one campaign id"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count what would be inserted without writing.",
    )
    args = parser.parse_args()
    asyncio.run(
        run(
            tenant=args.tenant,
            campaign_id=args.campaign,
            dry_run=args.dry_run,
        )
    )


if __name__ == "__main__":
    main()
