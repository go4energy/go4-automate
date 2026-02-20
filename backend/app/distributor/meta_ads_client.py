"""Meta Marketing API + Conversion API client."""

import uuid

import httpx
from loguru import logger

from app.config import settings
from app.distributor.hashing import hash_for_meta, hash_phone
from app.distributor.schemas import ConversionEventCreate
from app.exceptions import ExternalServiceError

BASE_URL = f"https://graph.facebook.com/{settings.meta_api_version}"


# --- Conversion API ---


async def send_event(
    pixel_id: str, access_token: str, event: ConversionEventCreate
) -> dict:
    """Send a server-side event to Meta Conversion API."""
    event_id = str(uuid.uuid4())
    user_data: dict = {}

    if event.fbc:
        user_data["fbc"] = event.fbc
    if event.fbp:
        user_data["fbp"] = event.fbp

    if event.user_data:
        if event.user_data.email:
            user_data["em"] = [hash_for_meta(event.user_data.email)]
        if event.user_data.phone:
            user_data["ph"] = [hash_phone(event.user_data.phone)]
        if event.user_data.client_ip:
            user_data["client_ip_address"] = event.user_data.client_ip
        if event.user_data.client_user_agent:
            user_data["client_user_agent"] = event.user_data.client_user_agent

    event_data = {
        "event_name": event.event_name,
        "event_time": int(event.event_time.timestamp()),
        "event_id": event_id,
        "action_source": "website",
        "user_data": user_data,
    }
    if event.source_url:
        event_data["event_source_url"] = event.source_url
    if event.custom_data:
        event_data["custom_data"] = event.custom_data

    url = f"{BASE_URL}/{pixel_id}/events"
    payload = {"data": [event_data], "access_token": access_token}

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            result = resp.json()
            logger.info(
                "Meta Conversion Event gesendet: {event} (id={eid})",
                event=event.event_name,
                eid=event_id,
            )
            return result
        except httpx.HTTPStatusError as e:
            detail = e.response.text if e.response else str(e)
            logger.error("Meta Conversion API Fehler: {err}", err=detail)
            raise ExternalServiceError("Meta Conversion API", detail) from e
        except httpx.RequestError as e:
            logger.error("Meta Conversion Verbindungsfehler: {err}", err=str(e))
            raise ExternalServiceError("Meta Conversion API", str(e)) from e


# --- Marketing API ---


async def get_campaigns(ad_account_id: str, access_token: str) -> list[dict]:
    """Fetch campaigns from Meta Marketing API."""
    url = f"{BASE_URL}/{ad_account_id}/campaigns"
    params = {
        "fields": "id,name,status,daily_budget,lifetime_budget,objective",
        "access_token": access_token,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json().get("data", [])
        except httpx.HTTPStatusError as e:
            detail = e.response.text if e.response else str(e)
            logger.error("Meta Campaigns Fehler: {err}", err=detail)
            raise ExternalServiceError("Meta Marketing API", detail) from e
        except httpx.RequestError as e:
            logger.error("Meta Campaigns Verbindungsfehler: {err}", err=str(e))
            raise ExternalServiceError("Meta Marketing API", str(e)) from e


async def get_campaign_insights(
    campaign_id: str,
    access_token: str,
    date_from: str,
    date_to: str,
) -> dict:
    """Fetch campaign insights (performance metrics) from Meta."""
    url = f"{BASE_URL}/{campaign_id}/insights"
    params = {
        "fields": (
            "impressions,clicks,spend,actions,cost_per_action_type,"
            "cpc,ctr,frequency,reach"
        ),
        "time_range": f'{{"since":"{date_from}","until":"{date_to}"}}',
        "access_token": access_token,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data_list = resp.json().get("data", [])
            if not data_list:
                return {}
            raw = data_list[0]
            # Extract leads from actions
            leads = 0
            conversions = 0
            for action in raw.get("actions", []):
                if action.get("action_type") == "lead":
                    leads = int(action.get("value", 0))
                if action.get("action_type") in (
                    "offsite_conversion.fb_pixel_lead",
                    "lead",
                ):
                    conversions += int(action.get("value", 0))
            return {
                "impressions": int(raw.get("impressions", 0)),
                "clicks": int(raw.get("clicks", 0)),
                "spend": float(raw.get("spend", 0)),
                "leads": leads,
                "conversions": conversions,
                "cpc": float(raw.get("cpc", 0)),
                "ctr": float(raw.get("ctr", 0)),
                "frequency": float(raw.get("frequency", 0)),
                "reach": int(raw.get("reach", 0)),
            }
        except httpx.HTTPStatusError as e:
            detail = e.response.text if e.response else str(e)
            logger.error("Meta Insights Fehler: {err}", err=detail)
            raise ExternalServiceError("Meta Marketing API", detail) from e
        except httpx.RequestError as e:
            logger.error("Meta Insights Verbindungsfehler: {err}", err=str(e))
            raise ExternalServiceError("Meta Marketing API", str(e)) from e


async def update_campaign_budget(
    campaign_id: str, access_token: str, daily_budget_cents: int
) -> dict:
    """Update a campaign's daily budget. Budget in CENTS (20.00 = 2000)."""
    url = f"{BASE_URL}/{campaign_id}"

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.post(
                url,
                data={
                    "daily_budget": str(daily_budget_cents),
                    "access_token": access_token,
                },
            )
            resp.raise_for_status()
            logger.info(
                "Budget aktualisiert: {id} -> {budget} Cents",
                id=campaign_id,
                budget=daily_budget_cents,
            )
            return resp.json()
        except httpx.HTTPStatusError as e:
            detail = e.response.text if e.response else str(e)
            logger.error("Meta Budget-Update Fehler: {err}", err=detail)
            raise ExternalServiceError("Meta Marketing API", detail) from e
        except httpx.RequestError as e:
            raise ExternalServiceError("Meta Marketing API", str(e)) from e


async def pause_campaign(campaign_id: str, access_token: str) -> dict:
    """Pause a campaign."""
    return await _set_campaign_status(campaign_id, access_token, "PAUSED")


async def resume_campaign(campaign_id: str, access_token: str) -> dict:
    """Resume a paused campaign."""
    return await _set_campaign_status(campaign_id, access_token, "ACTIVE")


async def _set_campaign_status(
    campaign_id: str, access_token: str, status: str
) -> dict:
    """Set campaign status (ACTIVE/PAUSED)."""
    url = f"{BASE_URL}/{campaign_id}"

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.post(
                url,
                data={"status": status, "access_token": access_token},
            )
            resp.raise_for_status()
            logger.info(
                "Kampagne {id} Status -> {status}",
                id=campaign_id,
                status=status,
            )
            return resp.json()
        except httpx.HTTPStatusError as e:
            detail = e.response.text if e.response else str(e)
            logger.error("Meta Status-Update Fehler: {err}", err=detail)
            raise ExternalServiceError("Meta Marketing API", detail) from e
        except httpx.RequestError as e:
            raise ExternalServiceError("Meta Marketing API", str(e)) from e
