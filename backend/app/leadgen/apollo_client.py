"""Apollo.io People Enrichment client — used by the leadgen ``apollo`` stage.

Single function: :func:`bulk_match_people` posts up to 10 people identifiers to
``/people/bulk_match`` and returns the matched profile data plus the credit
counter Apollo reports back.

Match-only design: we never set ``reveal_personal_emails`` or
``reveal_phone_number`` — both burn paid Reveal-Credits. The basic match still
costs 1 export credit per person Apollo finds (verified empirically; the API
response includes ``credits_consumed`` so we always log the actual number).

The function degrades gracefully — network errors, 4xx and 5xx responses
return an empty ``BulkMatchResult`` so the worker stage cannot crash a run.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import httpx
from loguru import logger

# Apollo's bulk endpoint accepts max 10 details per request.
MAX_BATCH_SIZE = 10

# Default request timeout — Apollo's enrichment can take a few seconds for
# uncached profiles, so we leave a generous window before giving up.
DEFAULT_TIMEOUT_SECONDS = 30.0

# Conservative pacing between calls. Apollo Pro = ~200 req/min on bulk_match,
# but we don't need to push the limit; staying < 1 req/s keeps us well below
# any rate ceiling and avoids 429 retries.
INTER_REQUEST_DELAY_SECONDS = 0.4


@dataclass
class BulkMatchResult:
    """Outcome of one Apollo bulk_match call."""

    matches: list[dict[str, Any]] = field(default_factory=list)
    credits_consumed: int = 0
    requested: int = 0
    matched: int = 0
    missing: int = 0
    raw_status: str | None = None
    error: str | None = None


def _is_valid_detail(detail: dict[str, Any]) -> bool:
    """Apollo needs at least one identifier per person to attempt a match."""
    if not detail:
        return False
    if detail.get("linkedin_url"):
        return True
    if detail.get("email"):
        return True
    if detail.get("id"):
        return True
    has_name = bool(detail.get("first_name") and detail.get("last_name")) or bool(
        detail.get("name")
    )
    has_company = bool(detail.get("organization_name") or detail.get("domain"))
    return has_name and has_company


async def bulk_match_people(
    *,
    details: list[dict[str, Any]],
    api_key: str,
    base_url: str = "https://api.apollo.io/api/v1",
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    reveal_email: bool = False,
    reveal_phone: bool = False,
    webhook_url: str | None = None,
) -> BulkMatchResult:
    """Match up to ``MAX_BATCH_SIZE`` people in a single Apollo call.

    ``details`` is a list of dicts where each dict holds at least one
    identifier (LinkedIn URL, email, Apollo ID, or first/last + organization).
    Invalid entries are dropped before the call to avoid wasted credits.

    ``reveal_email`` / ``reveal_phone`` consume additional Apollo credits on
    top of the base export credit. On Pro Monthly, email reveals are unlimited
    (fair use), but phone reveals are limited to 100/month and require a
    ``webhook_url`` because phone delivery is async.
    """
    if not api_key:
        return BulkMatchResult(error="apollo_api_key_missing")
    if reveal_phone and not webhook_url:
        return BulkMatchResult(
            error="phone_reveal_needs_webhook",
            requested=len(details),
        )
    cleaned = [d for d in details if _is_valid_detail(d)]
    if not cleaned:
        return BulkMatchResult(error="no_valid_details")
    if len(cleaned) > MAX_BATCH_SIZE:
        cleaned = cleaned[:MAX_BATCH_SIZE]

    # Reveal flags ride as query params (per Apollo docs); the rest goes in
    # the JSON body. Apollo treats absent params as ``false``, but we send
    # the explicit value anyway so the audit trail in their dashboard is
    # unambiguous.
    params: dict[str, str] = {
        "reveal_personal_emails": "true" if reveal_email else "false",
        "reveal_phone_number": "true" if reveal_phone else "false",
    }
    if reveal_phone and webhook_url:
        params["webhook_url"] = webhook_url

    url = f"{base_url.rstrip('/')}/people/bulk_match"
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
        "accept": "application/json",
        "Cache-Control": "no-cache",
    }
    body = {"details": cleaned}

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, headers=headers, params=params, json=body)
    except httpx.HTTPError as e:
        logger.warning("Apollo bulk_match network error: {e}", e=str(e))
        return BulkMatchResult(error=f"network: {e}", requested=len(cleaned))

    if resp.status_code >= 400:
        snippet = (resp.text or "")[:200]
        logger.warning(
            "Apollo bulk_match HTTP {code}: {snippet}",
            code=resp.status_code,
            snippet=snippet,
        )
        return BulkMatchResult(
            error=f"http_{resp.status_code}",
            requested=len(cleaned),
            raw_status=str(resp.status_code),
        )

    try:
        data = resp.json()
    except ValueError as e:
        logger.warning("Apollo bulk_match invalid JSON: {e}", e=str(e))
        return BulkMatchResult(error="invalid_json", requested=len(cleaned))

    matches = data.get("matches") or []
    return BulkMatchResult(
        matches=matches,
        credits_consumed=int(data.get("credits_consumed") or 0),
        requested=int(data.get("total_requested_enrichments") or len(cleaned)),
        matched=int(data.get("unique_enriched_records") or len(matches)),
        missing=int(data.get("missing_records") or max(0, len(cleaned) - len(matches))),
        raw_status=data.get("status"),
    )


async def pace() -> None:
    """Sleep between calls to stay well below Apollo's rate ceiling."""
    await asyncio.sleep(INTER_REQUEST_DELAY_SECONDS)
