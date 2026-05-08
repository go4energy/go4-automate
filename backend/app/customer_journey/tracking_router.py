"""Customer Journey tracking router - external API for go4.energy / Odoo.

These endpoints are authenticated via API key (Bearer token),
NOT via the normal session/tenant auth.
"""

import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.customer_journey.schemas import (
    BatchEventRequest,
    BatchEventResponse,
    CampaignCreate,
    CampaignResponse,
    IdentifyRequest,
    IdentifyResponse,
    PrepareLinkRequest,
    PrepareLinkResponse,
    RefCodeCreate,
    RefCodeResponse,
    RefResolveResponse,
    TrackEventRequest,
    TrackEventResponse,
)
from app.customer_journey.service import (
    CampaignService,
    EventService,
    IdentifyService,
    PrepareLinkService,
    RefCodeService,
)
from app.database import get_db

router = APIRouter(prefix="/tracking", tags=["tracking"])


async def _verify_api_key(
    authorization: str = Header(...),
) -> tuple[str, str]:
    """Verify Bearer API key. Returns (tenant_id, source_site label).

    Source label is derived from the matching key in settings.tracking_api_keys
    (or "go4.energy" when only the legacy single key is configured).
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization[7:]
    keys = settings.tracking_keys_resolved
    if not keys:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Constant-time compare against all configured keys
    matched_label: str | None = None
    for label, key in keys.items():
        if secrets.compare_digest(token, key):
            matched_label = label
            break

    if not matched_label:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # External API always uses default tenant
    return settings.default_tenant_id, matched_label


def _get_client_ip(request: Request) -> str:
    """Resolve real client IP from X-Forwarded-For (first hop) or peer."""
    fwd = request.headers.get("x-forwarded-for", "")
    return fwd.split(",")[0].strip() or (request.client.host if request.client else "")


def _is_blocked_ip(ip: str) -> bool:
    """Check whether the given IP is on the tracking blocklist."""
    if not ip:
        return False
    return ip in (getattr(settings, "tracking_blocked_ips", None) or [])


# ============== Identify ==============


@router.post("/identify", response_model=IdentifyResponse)
async def identify_lead(
    request: Request,
    data: IdentifyRequest,
    auth: tuple[str, str] = Depends(_verify_api_key),
    db: AsyncSession = Depends(get_db),
) -> IdentifyResponse:
    """Identify or create a lead. Called by go4.energy and Odoo."""
    tenant_id, source_site = auth

    client_ip = _get_client_ip(request)
    if _is_blocked_ip(client_ip):
        logger.info("Identify blocked from IP={ip}", ip=client_ip)
        return IdentifyResponse(
            tracking_hash="", lead_id=0, is_new=False, merged=False,
        )

    try:
        service = IdentifyService(db)
        contact, is_new, merged = await service.identify(
            tenant_id, data, source_site=source_site
        )
        await db.commit()

        logger.info(
            "Identify: {email} → {hash} (new={new}, merged={merged})",
            email=contact.email,
            hash=contact.tracking_hash,
            new=is_new,
            merged=merged,
        )

        return IdentifyResponse(
            tracking_hash=contact.tracking_hash,
            lead_id=contact.id,
            is_new=is_new,
            merged=merged,
        )
    except Exception as e:
        await db.rollback()
        logger.exception("Fehler in identify_lead")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# ============== Event ==============


# ============== Prepare Link ==============


@router.post("/prepare-link", response_model=PrepareLinkResponse)
async def prepare_link(
    data: PrepareLinkRequest,
    auth: tuple[str, str] = Depends(_verify_api_key),
    db: AsyncSession = Depends(get_db),
) -> PrepareLinkResponse:
    """One-call: identify contact + resolve campaign + create ref-code + return link.

    Designed for Odoo mass-mailing: one API call per recipient.

    NB: This endpoint is intentionally NOT subject to TRACKING_BLOCKED_IPS —
    it is server-to-server (Odoo) and shares its egress IP with mail-preview
    bots that the blocklist targets on /event.
    """
    tenant_id, source_site = auth
    try:
        service = PrepareLinkService(db)
        result = await service.prepare(tenant_id, data, source_site=source_site)
        await db.commit()

        logger.info(
            "prepare-link: {email} → {ref} ({link})",
            email=data.email,
            ref=result["ref_code"],
            link=result["link"],
        )

        return PrepareLinkResponse(**result)
    except Exception as e:
        await db.rollback()
        logger.exception("Fehler in prepare_link")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# ============== Event ==============


@router.post("/event", response_model=TrackEventResponse)
async def track_event(
    request: Request,
    data: TrackEventRequest,
    auth: tuple[str, str] = Depends(_verify_api_key),
    db: AsyncSession = Depends(get_db),
) -> TrackEventResponse:
    """Log a journey event. Called by go4.energy."""
    tenant_id, source_site = auth
    client_ip = _get_client_ip(request)
    logger.info(
        "Track event from IP={ip} UA={ua} event={event} ref={ref}",
        ip=client_ip,
        ua=request.headers.get("user-agent", ""),
        event=data.event,
        ref=data.ref_code or data.tracking_hash,
    )

    if _is_blocked_ip(client_ip):
        logger.info("Event blocked from IP={ip}", ip=client_ip)
        return TrackEventResponse(tracking_hash=None)

    try:
        service = EventService(db)
        tracking_hash = await service.track_event(
            tenant_id, data, source_site=source_site
        )
        await db.commit()
        return TrackEventResponse(tracking_hash=tracking_hash)
    except Exception as e:
        await db.rollback()
        logger.exception("Fehler in track_event")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# ============== Batch Events ==============


@router.post("/event/batch", response_model=BatchEventResponse)
async def track_events_batch(
    request: Request,
    data: BatchEventRequest,
    auth: tuple[str, str] = Depends(_verify_api_key),
    db: AsyncSession = Depends(get_db),
) -> BatchEventResponse:
    """Process queued events in batch. Called by go4.energy after reconnect."""
    tenant_id, source_site = auth

    client_ip = _get_client_ip(request)
    if _is_blocked_ip(client_ip):
        logger.info("Batch blocked from IP={ip}", ip=client_ip)
        return BatchEventResponse(processed=0, errors=0)

    try:
        service = EventService(db)
        processed, errors = await service.track_batch(
            tenant_id, data.events, source_site=source_site
        )
        await db.commit()
        return BatchEventResponse(processed=processed, errors=errors)
    except Exception as e:
        await db.rollback()
        logger.exception("Fehler in track_events_batch")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# ============== Ref-Code Resolution ==============


@router.get("/ref/{ref_code}", response_model=RefResolveResponse)
async def resolve_ref_code(
    ref_code: str,
    existing_hash: str | None = Query(None),
    auth: tuple[str, str] = Depends(_verify_api_key),
    db: AsyncSession = Depends(get_db),
) -> RefResolveResponse:
    """Resolve a ref-code to a tracking hash. Called by go4.energy.

    Auto-creates a placeholder contact if no contact is linked yet.
    If existing_hash is provided, merges the old journey into the ref-code contact.
    """
    tenant_id, _ = auth
    try:
        service = RefCodeService(db)
        ref = await service.resolve(tenant_id, ref_code)

        if not ref:
            raise HTTPException(
                status_code=404, detail=f"Ref-Code '{ref_code}' nicht gefunden"
            )

        # Merge old anonymous journey into this contact
        if existing_hash and existing_hash != ref.contact.tracking_hash:
            from app.customer_journey.service import IdentifyService

            id_service = IdentifyService(db)
            merged = await id_service._merge_journeys(
                tenant_id, existing_hash, ref.contact
            )
            if merged:
                logger.info(
                    "Ref-resolve merge: {old} → contact {id}",
                    old=existing_hash,
                    id=ref.contact.id,
                )

        await db.commit()

        return RefResolveResponse(
            tracking_hash=ref.contact.tracking_hash or "",
            ref_code=ref.ref_code,
            lead_name=ref.contact.name,
            utm_source=ref.utm_source,
            utm_medium=ref.utm_medium,
            utm_campaign=ref.utm_campaign,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Fehler in resolve_ref_code")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# ============== Campaigns (external) ==============


@router.get("/campaigns", response_model=list[CampaignResponse])
async def list_campaigns_external(
    auth: tuple[str, str] = Depends(_verify_api_key),
    db: AsyncSession = Depends(get_db),
) -> list[CampaignResponse]:
    """List all campaigns. Called by Odoo/external systems."""
    tenant_id, _ = auth
    try:
        service = CampaignService(db)
        campaigns, _ = await service.list_campaigns(tenant_id)
        return [CampaignResponse.model_validate(c) for c in campaigns]
    except Exception as e:
        logger.exception("Fehler in list_campaigns_external")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/campaigns/resolve", response_model=CampaignResponse)
async def resolve_campaign_by_name(
    name: str,
    channel: str | None = None,
    auth: tuple[str, str] = Depends(_verify_api_key),
    db: AsyncSession = Depends(get_db),
) -> CampaignResponse:
    """Find campaign by name, create if not exists. Called by Odoo."""
    tenant_id, _ = auth
    try:
        service = CampaignService(db)
        campaign, is_new = await service.get_or_create_by_name(
            tenant_id, name, channel
        )
        if is_new:
            await db.commit()
        return CampaignResponse.model_validate(campaign)
    except Exception as e:
        await db.rollback()
        logger.exception("Fehler in resolve_campaign_by_name")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/campaigns", response_model=CampaignResponse)
async def create_campaign_external(
    data: CampaignCreate,
    auth: tuple[str, str] = Depends(_verify_api_key),
    db: AsyncSession = Depends(get_db),
) -> CampaignResponse:
    """Create a campaign. Called by Odoo/external systems."""
    tenant_id, _ = auth
    try:
        service = CampaignService(db)
        campaign = await service.create(tenant_id, data)
        await db.commit()
        return CampaignResponse.model_validate(campaign)
    except Exception as e:
        await db.rollback()
        logger.exception("Fehler in create_campaign_external")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# ============== Ref-Codes (external) ==============


@router.post("/refs", response_model=RefCodeResponse)
async def create_ref_code_external(
    data: RefCodeCreate,
    auth: tuple[str, str] = Depends(_verify_api_key),
    db: AsyncSession = Depends(get_db),
) -> RefCodeResponse:
    """Create a ref-code. Called by Odoo/external systems."""
    tenant_id, _ = auth
    try:
        service = RefCodeService(db)
        ref = await service.create(tenant_id, data)
        await db.commit()
        return RefCodeResponse.model_validate(ref)
    except Exception as e:
        await db.rollback()
        logger.exception("Fehler in create_ref_code_external")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e
