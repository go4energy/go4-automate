"""Purge synthetic ``skip:no_website`` LLM-Insights rows for a campaign.

Background: the worker historically created a max-score (=10) ``LLMInsights``
row for every place without a website, on the assumption that the campaign
sells homepages. This polluted scoring for *normal* lead-gen campaigns where
the LLM is the only legitimate scoring authority.

This script removes those synth-rows for **one specific campaign** and resets
the affected places to a dedicated ``status='no_website'`` so they stay out
of LLM-scored exports without being silently re-scored by accident.

Usage::

    python -m scripts.leadgen_purge_no_website_synth --campaign 13 --dry-run
    python -m scripts.leadgen_purge_no_website_synth --campaign 13

Cost: zero — deletes rows the worker generated, no API calls.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from sqlalchemy import delete, select, update

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import async_session  # noqa: E402
from app.leadgen.models import (  # noqa: E402
    LeadgenCampaign,
    LeadgenLLMInsights,
    LeadgenPlace,
)


async def run(*, campaign_id: int, dry_run: bool) -> None:
    async with async_session() as db:
        campaign = (
            await db.execute(
                select(LeadgenCampaign).where(LeadgenCampaign.id == campaign_id)
            )
        ).scalar_one_or_none()
        if campaign is None:
            print(f"❌ Kampagne {campaign_id} nicht gefunden")
            return

        # IDs of places in this campaign that carry a synth-row.
        place_ids = (
            await db.execute(
                select(LeadgenPlace.id)
                .join(
                    LeadgenLLMInsights,
                    LeadgenLLMInsights.place_id == LeadgenPlace.id,
                )
                .where(
                    LeadgenPlace.campaign_id == campaign_id,
                    LeadgenLLMInsights.model_used == "skip:no_website",
                )
            )
        ).scalars().all()
        n = len(place_ids)
        prefix = "[dry-run] " if dry_run else ""
        print(
            f"{prefix}Kampagne #{campaign.id} {campaign.slug!r}: "
            f"{n} synth-no-website Rows gefunden."
        )
        if n == 0 or dry_run:
            return

        # Delete the synth insights rows.
        await db.execute(
            delete(LeadgenLLMInsights).where(
                LeadgenLLMInsights.place_id.in_(place_ids),
                LeadgenLLMInsights.model_used == "skip:no_website",
            )
        )
        # Reset the affected places to the dedicated status. They're no longer
        # ``llm_done`` (which is the export filter), so they won't pollute
        # downstream Apollo / Sales-Nav / Handoff outputs.
        await db.execute(
            update(LeadgenPlace)
            .where(LeadgenPlace.id.in_(place_ids))
            .values(status="no_website")
        )
        await db.commit()
        print(f"✅ {n} Rows gelöscht, {n} Places auf status='no_website' gesetzt.")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--campaign", type=int, required=True, help="Campaign id to purge")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    asyncio.run(run(campaign_id=args.campaign, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
