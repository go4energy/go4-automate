"""Stratified Haiku-vs-Opus comparison for a leadgen campaign.

Picks 30 already-enriched places (10 each from score bands 7-10 / 4-6 / 0-3),
re-runs them with Opus 4.7 using the campaign's CURRENT prompt config, and
writes a side-by-side Markdown report to /tmp/leadgen_opus_comparison.md.

Usage:
    python -m scripts.compare_haiku_opus --campaign 13

Cost: ~30 * 0.015 USD = ~0.45 USD (Opus 4.7 pricing).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

import httpx
from sqlalchemy import select
from sqlalchemy.orm import selectinload

# Make the script runnable both as `python scripts/compare_haiku_opus.py` and
# `python -m scripts.compare_haiku_opus` from the backend dir.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import async_session  # noqa: E402
from app.leadgen.homepage_analyzer import (  # noqa: E402
    DEFAULT_PATHS,
    DEFAULT_PROMPT_TEMPLATE,
    analyze_place_with_llm,
)
from app.leadgen.models import (  # noqa: E402
    LeadgenCampaign,
    LeadgenLLMInsights,
    LeadgenPlace,
)
from app.leadgen.source_config import parse_source_config  # noqa: E402
from app.services.llm import LLMService  # noqa: E402

OPUS_MODEL = "claude-opus-4-7"

# Cost constants for Opus 4.7 (cents per million tokens, current price card).
OPUS_INPUT_PER_M_CENTS = 1500
OPUS_OUTPUT_PER_M_CENTS = 7500

OUTPUT_PATH = Path("/tmp/leadgen_opus_comparison.md")


async def pick_stratified_sample(
    db, campaign_id: int, per_band: int = 10
) -> list[LeadgenPlace]:
    """Pick `per_band` places from each score band (7-10, 4-6, 0-3)."""
    result: list[LeadgenPlace] = []
    bands = [
        ("hoch (7-10)", 7, 10),
        ("mittel (4-6)", 4, 6),
        ("niedrig (0-3)", 0, 3),
    ]
    for label, lo, hi in bands:
        rows = (
            await db.execute(
                select(LeadgenPlace)
                .join(
                    LeadgenLLMInsights,
                    LeadgenLLMInsights.place_id == LeadgenPlace.id,
                )
                .where(
                    LeadgenPlace.campaign_id == campaign_id,
                    LeadgenPlace.status == "llm_done",
                    LeadgenPlace.website.isnot(None),
                    LeadgenLLMInsights.target_match_score >= lo,
                    LeadgenLLMInsights.target_match_score <= hi,
                )
                .options(selectinload(LeadgenPlace.llm_insights))
                .order_by(LeadgenPlace.id.asc())
                .limit(per_band)
            )
        ).scalars().all()
        print(f"Band {label}: {len(rows)} places")
        result.extend(rows)
    return result


def render_markdown(
    campaign: LeadgenCampaign,
    pairs: list[tuple[LeadgenPlace, dict]],
) -> str:
    """Render a Markdown report comparing existing Haiku to fresh Opus output."""
    lines: list[str] = []
    lines.append(f"# Haiku-vs-Opus Vergleich · Campaign #{campaign.id} «{campaign.name}»")
    lines.append("")
    lines.append(
        "Stratifizierte Stichprobe (10 hoch / 10 mittel / 10 niedrig) aus den"
        " bereits angereicherten Places. Beide Läufe nutzen den AKTUELLEN"
        " target_profile + output_description der Kampagne — der einzige"
        " Unterschied ist das Modell."
    )
    lines.append("")

    total_opus_cost = sum(p[1].get("opus_cost_cents", 0) for p in pairs)
    total_failed = sum(1 for _, opus in pairs if opus.get("error"))
    lines.append(
        f"**{len(pairs)} Places verglichen** · Opus-Kosten: "
        f"{total_opus_cost / 100:.2f} USD · Fehler: {total_failed}"
    )
    lines.append("")
    lines.append("---")
    lines.append("")

    for place, opus in pairs:
        haiku = place.llm_insights
        h_score = getattr(haiku, "target_match_score", None) if haiku else None
        o_score = opus.get("target_match_score")
        delta = (
            (o_score - h_score)
            if (o_score is not None and h_score is not None)
            else None
        )
        delta_str = (
            f" · Δ {'+' if delta and delta > 0 else ''}{delta}"
            if delta is not None
            else ""
        )

        lines.append(
            f"## {place.name} · #{place.id}"
            f" · Haiku {h_score}/10 vs Opus {o_score}/10{delta_str}"
        )
        lines.append("")
        lines.append(
            f"- **Adresse:** {place.formatted_address or '-'}"
        )
        lines.append(f"- **Website:** {place.website or '-'}")
        if opus.get("error"):
            lines.append(f"- **Opus-Fehler:** `{opus['error']}`")
        lines.append("")

        # Side-by-side table for compact fields
        lines.append("| Feld | Haiku | Opus |")
        lines.append("|---|---|---|")

        def _fmt_list(v):
            if not v:
                return "—"
            return ", ".join(str(x) for x in v[:6])

        h_services = getattr(haiku, "services", []) if haiku else []
        h_brands = getattr(haiku, "brands", []) if haiku else []
        h_segments = getattr(haiku, "customer_segments", []) if haiku else []
        h_size = getattr(haiku, "company_size_indicator", None) if haiku else None
        h_flags = getattr(haiku, "red_flags", []) if haiku else []

        lines.append(
            f"| services | {_fmt_list(h_services)} | "
            f"{_fmt_list(opus.get('services'))} |"
        )
        lines.append(
            f"| brands | {_fmt_list(h_brands)} | "
            f"{_fmt_list(opus.get('brands'))} |"
        )
        lines.append(
            f"| customer_segments | {_fmt_list(h_segments)} | "
            f"{_fmt_list(opus.get('customer_segments'))} |"
        )
        lines.append(
            f"| company_size | {h_size or '—'} | "
            f"{opus.get('company_size_indicator') or '—'} |"
        )
        lines.append(
            f"| red_flags | {_fmt_list(h_flags)} | "
            f"{_fmt_list(opus.get('red_flags'))} |"
        )

        lines.append("")
        lines.append("**Primärer Kontakt (Opus):**")
        pc = opus.get("primary_contact") or {}
        if pc and any(pc.values()):
            parts = []
            if pc.get("salutation"):
                parts.append(pc["salutation"])
            if pc.get("first_name"):
                parts.append(pc["first_name"])
            if pc.get("last_name"):
                parts.append(pc["last_name"])
            line = " ".join(parts) if parts else "—"
            if pc.get("role"):
                line += f" · {pc['role']}"
            if pc.get("source"):
                line += f" (Quelle: {pc['source']})"
            lines.append(line)
        else:
            lines.append("— (kein klarer Kontakt gefunden)")
        lines.append("")

        lines.append("**Pre-Pitch-Intel · Haiku:**")
        lines.append("```")
        lines.append((getattr(haiku, "personalization_hook", "") or "—").strip())
        lines.append("```")
        lines.append("**Pre-Pitch-Intel · Opus:**")
        lines.append("```")
        lines.append((opus.get("personalization_hook") or "—").strip())
        lines.append("```")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


async def run_opus(place: LeadgenPlace, campaign: LeadgenCampaign, llm_service: LLMService, http_client: httpx.AsyncClient) -> dict:
    """Re-run a place's homepage analysis with Opus 4.7."""
    cfg_full = parse_source_config(
        campaign.source or "google_places",
        campaign.source_config or {},
    )
    llm_cfg = cfg_full.llm
    prompt_template = (llm_cfg.prompt_template or DEFAULT_PROMPT_TEMPLATE).strip()
    # Same sanity check as the worker: a custom template without the required
    # placeholders would be passed through verbatim and the LLM would never see
    # the campaign's target_profile / output_description.
    if "{target_profile}" not in prompt_template or "{content}" not in prompt_template:
        prompt_template = DEFAULT_PROMPT_TEMPLATE

    analysis = await analyze_place_with_llm(
        website=place.website,
        target_profile=llm_cfg.target_profile,
        output_description=llm_cfg.output_description,
        prompt_template=prompt_template,
        model=OPUS_MODEL,
        llm_service=llm_service,
        http_client=http_client,
        paths=tuple(llm_cfg.paths_to_fetch) or DEFAULT_PATHS,
        user_agent=llm_cfg.user_agent,
        timeout_s=llm_cfg.http_timeout_s,
        max_html_chars=llm_cfg.max_html_chars,
    )
    # Recompute cost with Opus pricing (analyzer assumes Haiku rates).
    opus_cost_cents = max(
        0,
        int(round(
            (
                analysis.input_tokens * OPUS_INPUT_PER_M_CENTS
                + analysis.output_tokens * OPUS_OUTPUT_PER_M_CENTS
            )
            / 1_000_000
        )),
    )

    return {
        "target_match_score": analysis.target_match_score,
        "services": analysis.services,
        "brands": analysis.brands,
        "customer_segments": analysis.customer_segments,
        "company_size_indicator": analysis.company_size_indicator,
        "personalization_hook": analysis.personalization_hook,
        "red_flags": analysis.red_flags,
        "primary_contact": analysis.primary_contact,
        "error": analysis.error,
        "opus_cost_cents": opus_cost_cents,
        "input_tokens": analysis.input_tokens,
        "output_tokens": analysis.output_tokens,
    }


async def main(campaign_id: int, per_band: int) -> None:
    async with async_session() as db:
        campaign = (
            await db.execute(
                select(LeadgenCampaign).where(LeadgenCampaign.id == campaign_id)
            )
        ).scalar_one()
        sample = await pick_stratified_sample(db, campaign_id, per_band)

    print(f"Total sample: {len(sample)} places · running through Opus 4.7…")

    llm_service = LLMService()
    pairs: list[tuple[LeadgenPlace, dict]] = []

    async with httpx.AsyncClient(
        follow_redirects=True,
        limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
    ) as http_client:
        sem = asyncio.Semaphore(5)

        async def _wrap(place: LeadgenPlace) -> tuple[LeadgenPlace, dict]:
            async with sem:
                opus = await run_opus(place, campaign, llm_service, http_client)
                score = opus.get("target_match_score")
                err = opus.get("error")
                marker = f"err={err[:60]}" if err else f"score={score}"
                print(f"  · #{place.id} {place.name[:40]:40} → {marker}")
                return place, opus

        results = await asyncio.gather(*(_wrap(p) for p in sample))
        pairs.extend(results)

    md = render_markdown(campaign, pairs)
    OUTPUT_PATH.write_text(md, encoding="utf-8")
    total_cost = sum(p[1].get("opus_cost_cents", 0) for p in pairs) / 100.0
    print(f"\nReport geschrieben: {OUTPUT_PATH}")
    print(f"Opus-Kosten: ${total_cost:.2f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", type=int, required=True)
    parser.add_argument("--per-band", type=int, default=10)
    args = parser.parse_args()
    asyncio.run(main(args.campaign, args.per_band))
