"""Benchmark Claude Haiku 4.5 vs local Qwen 3 32B on the same 10 places.

For each place we fetch the homepage once, then send the SAME prompt to both
models and record latency, JSON parse success, scores, and the full extracted
fields. Output is a Markdown report at /tmp/leadgen_haiku_vs_qwen.md.

Usage:
    python -m scripts.benchmark_haiku_qwen --campaign 13
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

import httpx
from sqlalchemy import select

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

MODELS = [
    {"label": "Haiku 4.5", "model": "claude-haiku-4-5", "provider": "anthropic"},
    {"label": "Qwen 3 32B", "model": "qwen3:32b", "provider": "ollama"},
]

OUTPUT_PATH = Path("/tmp/leadgen_haiku_vs_qwen.md")


async def pick_diverse_sample(db, campaign_id: int, n: int) -> list[LeadgenPlace]:
    """Pick a diverse subset (high / mid / low scoring) of llm_done places."""
    bands = [(7, 10, 4), (4, 6, 3), (1, 3, 3)]  # (lo, hi, count) → 4+3+3 = 10
    if n != 10:
        bands = [(0, 10, n)]  # fallback: top-N regardless of band

    places: list[LeadgenPlace] = []
    for lo, hi, count in bands:
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
                .order_by(LeadgenPlace.id.asc())
                .limit(count)
            )
        ).scalars().all()
        places.extend(rows)
    return places


async def run_one(
    *, place: LeadgenPlace, campaign: LeadgenCampaign, model_cfg: dict,
    llm_service: LLMService, http_client: httpx.AsyncClient,
) -> dict:
    """Run a single place through one model, time it."""
    cfg = parse_source_config(
        campaign.source or "google_places", campaign.source_config or {}
    ).llm
    prompt_template = (cfg.prompt_template or DEFAULT_PROMPT_TEMPLATE).strip()
    if "{target_profile}" not in prompt_template or "{content}" not in prompt_template:
        prompt_template = DEFAULT_PROMPT_TEMPLATE

    t0 = time.time()
    analysis = await analyze_place_with_llm(
        website=place.website,
        target_profile=cfg.target_profile,
        output_description=cfg.output_description,
        prompt_template=prompt_template,
        model=model_cfg["model"],
        provider=model_cfg["provider"],
        llm_service=llm_service,
        http_client=http_client,
        paths=tuple(cfg.paths_to_fetch) or DEFAULT_PATHS,
        user_agent=cfg.user_agent,
        timeout_s=cfg.http_timeout_s,
        max_html_chars=cfg.max_html_chars,
    )
    elapsed = time.time() - t0

    return {
        "model": model_cfg["label"],
        "elapsed_s": round(elapsed, 2),
        "score": analysis.target_match_score,
        "services": analysis.services,
        "brands": analysis.brands,
        "customer_segments": analysis.customer_segments,
        "company_size": analysis.company_size_indicator,
        "personalization_hook": analysis.personalization_hook,
        "red_flags": analysis.red_flags,
        "primary_contact": analysis.primary_contact,
        "input_tokens": analysis.input_tokens,
        "output_tokens": analysis.output_tokens,
        "cost_cents": analysis.cost_cents,
        "error": analysis.error,
    }


def render_markdown(
    campaign: LeadgenCampaign,
    pairs: list[tuple[LeadgenPlace, dict, dict]],
) -> str:
    """Side-by-side report with a summary block on top."""
    lines: list[str] = []
    lines.append(f"# Benchmark Haiku 4.5 vs Qwen 3 32B · Campaign #{campaign.id} «{campaign.name}»")
    lines.append("")
    lines.append(
        "Beide Modelle erhalten **denselben Prompt** und **dieselbe Homepage** "
        "pro Place. Latenz wird pro Call gemessen."
    )
    lines.append("")

    # Aggregate stats
    haiku_lat = [h["elapsed_s"] for _, h, _ in pairs if not h.get("error")]
    qwen_lat = [q["elapsed_s"] for _, _, q in pairs if not q.get("error")]
    haiku_fails = sum(1 for _, h, _ in pairs if h.get("error") or h.get("score") is None)
    qwen_fails = sum(1 for _, _, q in pairs if q.get("error") or q.get("score") is None)
    haiku_cost_cents = sum(h.get("cost_cents", 0) for _, h, _ in pairs)
    qwen_cost_cents = sum(q.get("cost_cents", 0) for _, _, q in pairs)

    score_deltas = [
        (q.get("score") - h.get("score"))
        for _, h, q in pairs
        if h.get("score") is not None and q.get("score") is not None
    ]
    avg_delta = sum(score_deltas) / len(score_deltas) if score_deltas else 0

    def _avg(xs):
        return f"{sum(xs)/len(xs):.1f}s" if xs else "n/a"

    def _max(xs):
        return f"{max(xs):.1f}s" if xs else "n/a"

    lines.append("## Zusammenfassung")
    lines.append("")
    lines.append("| Metrik | Haiku 4.5 | Qwen 3 32B |")
    lines.append("|---|---|---|")
    lines.append(f"| Avg. Latenz | {_avg(haiku_lat)} | {_avg(qwen_lat)} |")
    lines.append(f"| Max. Latenz | {_max(haiku_lat)} | {_max(qwen_lat)} |")
    lines.append(f"| JSON-Fails / 10 | {haiku_fails} | {qwen_fails} |")
    lines.append(f"| Kosten gesamt | ${haiku_cost_cents/100:.3f} | ${qwen_cost_cents/100:.3f} |")
    lines.append(f"| Speed-Faktor | 1× | {sum(qwen_lat)/sum(haiku_lat):.1f}× langsamer |" if haiku_lat and qwen_lat else "| Speed-Faktor | — | — |")
    lines.append("")
    lines.append(
        f"**Score-Delta (Qwen − Haiku):** Ø {avg_delta:+.1f} Punkte "
        f"über {len(score_deltas)} valide Vergleichs-Paare."
    )
    lines.append("")
    lines.append("---")
    lines.append("")

    # Per-place blocks
    for place, h, q in pairs:
        h_score = h.get("score")
        q_score = q.get("score")
        delta = (
            f" · Δ {'+' if (q_score - h_score) > 0 else ''}{q_score - h_score}"
            if h_score is not None and q_score is not None
            else ""
        )
        lines.append(
            f"## {place.name} · #{place.id}"
            f" · Haiku {h_score}/10 ({h['elapsed_s']}s)"
            f" vs Qwen {q_score}/10 ({q['elapsed_s']}s){delta}"
        )
        lines.append("")
        lines.append(f"- Adresse: {place.formatted_address or '-'}")
        lines.append(f"- Website: {place.website or '-'}")
        if h.get("error"):
            lines.append(f"- Haiku-Fehler: `{h['error']}`")
        if q.get("error"):
            lines.append(f"- Qwen-Fehler: `{q['error']}`")
        lines.append("")

        def _fmt_list(v):
            if not v:
                return "—"
            return ", ".join(str(x) for x in v[:6])

        lines.append("| Feld | Haiku 4.5 | Qwen 3 32B |")
        lines.append("|---|---|---|")
        lines.append(f"| services | {_fmt_list(h.get('services'))} | {_fmt_list(q.get('services'))} |")
        lines.append(f"| brands | {_fmt_list(h.get('brands'))} | {_fmt_list(q.get('brands'))} |")
        lines.append(f"| customer_segments | {_fmt_list(h.get('customer_segments'))} | {_fmt_list(q.get('customer_segments'))} |")
        lines.append(f"| company_size | {h.get('company_size') or '—'} | {q.get('company_size') or '—'} |")
        lines.append(f"| red_flags | {_fmt_list(h.get('red_flags'))} | {_fmt_list(q.get('red_flags'))} |")
        lines.append(f"| input/output tokens | {h.get('input_tokens')}/{h.get('output_tokens')} | {q.get('input_tokens')}/{q.get('output_tokens')} |")
        lines.append("")

        for label, data in [("Haiku 4.5", h), ("Qwen 3 32B", q)]:
            pc = data.get("primary_contact") or {}
            lines.append(f"**Primärer Kontakt · {label}:**")
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
        lines.append((h.get("personalization_hook") or "—").strip())
        lines.append("```")
        lines.append("**Pre-Pitch-Intel · Qwen:**")
        lines.append("```")
        lines.append((q.get("personalization_hook") or "—").strip())
        lines.append("```")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


async def main(campaign_id: int, n: int) -> None:
    async with async_session() as db:
        campaign = (
            await db.execute(
                select(LeadgenCampaign).where(LeadgenCampaign.id == campaign_id)
            )
        ).scalar_one()
        sample = await pick_diverse_sample(db, campaign_id, n)

    print(f"Sample: {len(sample)} Places · benchmarking Haiku 4.5 vs Qwen 3 32B …")

    llm_service = LLMService()
    pairs: list[tuple[LeadgenPlace, dict, dict]] = []

    async with httpx.AsyncClient(
        follow_redirects=True,
        limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
    ) as http_client:
        for place in sample:
            print(f"\n  · #{place.id} {place.name[:50]}")
            # Run both models in parallel for the same place — they don't share
            # resources (one external API, one local GPU).
            h_task = run_one(
                place=place, campaign=campaign, model_cfg=MODELS[0],
                llm_service=llm_service, http_client=http_client,
            )
            q_task = run_one(
                place=place, campaign=campaign, model_cfg=MODELS[1],
                llm_service=llm_service, http_client=http_client,
            )
            h_result, q_result = await asyncio.gather(
                h_task, q_task, return_exceptions=False,
            )
            print(
                f"    haiku: {h_result['elapsed_s']}s score={h_result['score']}"
                f"  |  qwen: {q_result['elapsed_s']}s score={q_result['score']}"
            )
            pairs.append((place, h_result, q_result))

    md = render_markdown(campaign, pairs)
    OUTPUT_PATH.write_text(md, encoding="utf-8")
    haiku_total = sum(p[1]["elapsed_s"] for p in pairs)
    qwen_total = sum(p[2]["elapsed_s"] for p in pairs)
    print(f"\n→ Report: {OUTPUT_PATH}")
    print(f"  Haiku-Wallclock total: {haiku_total:.1f}s")
    print(f"  Qwen-Wallclock total:  {qwen_total:.1f}s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", type=int, required=True)
    parser.add_argument("--n", type=int, default=10)
    asyncio.run(main(*[getattr(parser.parse_args(), k) for k in ("campaign", "n")]))
