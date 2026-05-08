"""Email provider webhooks router."""

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.emailmarketing.models import EmailProvider
from app.emailmarketing.service import TrackingService

# Webhooks router - specific auth per provider
# Named 'router' for module discovery compatibility
router = APIRouter(prefix="/emailmarketing/webhooks", tags=["emailmarketing-webhooks"])


async def _resolve_tenant_for_sendgrid_email(
    db: AsyncSession, sender_email: str | None
) -> str | None:
    """Find tenant_id by matching the sender domain to a SendGrid provider.

    SendGrid Event-Webhooks senden den 'email'-Wert (Empfänger). Um den
    Tenant zu finden nutzen wir den Sender (from-Header) — falls verfügbar
    — oder fallen zurück auf den ersten aktiven SendGrid-Provider in der
    DB. Bei Single-Tenant-Setup reicht das.
    """
    if sender_email and "@" in sender_email:
        domain = sender_email.split("@", 1)[1].lower()
        result = await db.execute(
            select(EmailProvider).where(
                EmailProvider.provider_type == "sendgrid",
                EmailProvider.status == "active",
            )
        )
        for prov in result.scalars().all():
            if prov.sender_email and prov.sender_email.endswith(f"@{domain}"):
                return prov.tenant_id
    # Fallback: first active SendGrid provider (Single-Tenant-Setup)
    result = await db.execute(
        select(EmailProvider).where(
            EmailProvider.provider_type == "sendgrid",
            EmailProvider.status == "active",
        ).limit(1)
    )
    prov = result.scalar_one_or_none()
    return prov.tenant_id if prov else None


@router.post("/sendgrid")
async def sendgrid_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Handle SendGrid event webhooks.

    SendGrid sends events as a JSON array.
    Event types: delivered, bounce, open, click, spamreport, unsubscribe
    """
    try:
        body = await request.body()
        events = json.loads(body)

        if not isinstance(events, list):
            events = [events]

        service = TrackingService(db)

        # Map SendGrid event types to our internal types
        event_mapping = {
            "delivered": "delivered",
            "bounce": "bounce",
            "dropped": "bounce",  # blocked before send
            "open": "open",
            "click": "click",
            "spamreport": "spam",
            "unsubscribe": "unsubscribe",
        }

        for event in events:
            event_type = event.get("event", "").lower()
            mapped_event = event_mapping.get(event_type)
            if not mapped_event:
                continue

            recipient_email = event.get("email")
            tracking_token = event.get("tracking_token")
            ip = event.get("ip")

            # Open / Click / Unsubscribe — historisch tracking_token-basiert
            # (klassische Email-Marketing-Kampagnen mit EmailRecipient-Records).
            if mapped_event in ("open", "click", "unsubscribe") and tracking_token:
                if mapped_event == "open":
                    await service.record_open(tracking_token)
                elif mapped_event == "click":
                    url = event.get("url", "")
                    user_agent = event.get("useragent")
                    await service.record_click(tracking_token, url, ip, user_agent)
                elif mapped_event == "unsubscribe":
                    await service.record_unsubscribe(tracking_token, ip)
                continue

            # Bounce / Spam — immer in Suppression-List, egal ob tracking_token
            # vorhanden. Engagement-Sends nutzen action.id als token; klassische
            # Kampagnen den EmailRecipient-Token. Fallback: per email + Tenant-
            # Mapping über Provider-Domain.
            if mapped_event in ("bounce", "spam"):
                # Tenant ermitteln — bei Single-Tenant-Setup reicht der erste
                # aktive SendGrid-Provider
                tenant_id = await _resolve_tenant_for_sendgrid_email(
                    db, sender_email=event.get("from") or recipient_email
                )
                if not tenant_id:
                    logger.warning(
                        "Webhook: kein Tenant für Event {ev}", ev=event_type,
                    )
                    continue

                if mapped_event == "bounce":
                    bounce_type = (
                        "soft" if event.get("type") == "blocked" else "hard"
                    )
                    await service.record_bounce(
                        tenant_id=tenant_id,
                        email=recipient_email,
                        tracking_token=tracking_token,
                        bounce_type=bounce_type,
                        reason=event.get("reason"),
                    )
                else:  # spam
                    await service.record_spam_report(
                        tenant_id=tenant_id,
                        email=recipient_email,
                        tracking_token=tracking_token,
                    )
                continue

            # delivered — informativ; aktuell nicht persistiert für Engagement-
            # Sends (klassischer Worker macht das selbst)
            if mapped_event == "delivered":
                logger.debug(
                    "Delivered: {email} (token={t})",
                    email=recipient_email, t=tracking_token,
                )

        await db.commit()
        return {"received": len(events)}

    except json.JSONDecodeError as err:
        logger.error("SendGrid webhook: Invalid JSON")
        raise HTTPException(status_code=400, detail="Invalid JSON") from err
    except Exception as e:
        logger.exception("SendGrid webhook Fehler")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/mailgun")
async def mailgun_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Handle Mailgun event webhooks.

    Mailgun sends events as form data or JSON.
    Event types: delivered, bounced, opened, clicked, complained, unsubscribed
    """
    try:
        # Mailgun can send as JSON or form data
        content_type = request.headers.get("content-type", "")

        if "application/json" in content_type:
            data = await request.json()
        else:
            form = await request.form()
            data = dict(form)

        # Mailgun wraps event data
        event_data = data.get("event-data", data)
        if isinstance(event_data, str):
            event_data = json.loads(event_data)

        event_type = event_data.get("event", "").lower()
        # recipient and message_id available for future matching without tracking_token
        # recipient = event_data.get("recipient")
        # message_id = event_data.get("message", {}).get("headers", {}).get("message-id")

        # Get tracking token from user variables
        user_vars = event_data.get("user-variables", {})
        tracking_token = user_vars.get("tracking_token")

        service = TrackingService(db)

        # Map Mailgun events
        event_mapping = {
            "delivered": "delivered",
            "bounced": "bounce",
            "failed": "bounce",
            "opened": "open",
            "clicked": "click",
            "complained": "spam",
            "unsubscribed": "unsubscribe",
        }

        mapped_event = event_mapping.get(event_type)
        if not mapped_event:
            return {"received": True}

        if tracking_token:
            if mapped_event == "open":
                await service.record_open(tracking_token)
            elif mapped_event == "click":
                url = event_data.get("url", "")
                ip = event_data.get("ip")
                user_agent = event_data.get("client-info", {}).get("user-agent")
                await service.record_click(tracking_token, url, ip, user_agent)
            elif mapped_event == "unsubscribe":
                ip = event_data.get("ip")
                await service.record_unsubscribe(tracking_token, ip)

        await db.commit()
        return {"received": True}

    except Exception as e:
        logger.exception("Mailgun webhook Fehler")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/o365")
async def o365_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Handle Microsoft Graph change notifications.

    Note: Microsoft Graph doesn't send delivery/bounce events via webhooks.
    This endpoint is a placeholder for potential future integration
    with Microsoft 365 admin APIs or custom tracking.
    """
    try:
        # Validate subscription (Microsoft Graph validation request)
        query_params = dict(request.query_params)
        if "validationToken" in query_params:
            # Return validation token as plain text
            return query_params["validationToken"]

        body = await request.json()

        # Process notifications
        notifications = body.get("value", [])

        for notification in notifications:
            change_type = notification.get("changeType")
            resource = notification.get("resource")

            logger.debug(
                "O365 notification: {type} - {resource}",
                type=change_type,
                resource=resource,
            )

        return {"received": len(notifications)}

    except Exception as e:
        logger.exception("O365 webhook Fehler")
        raise HTTPException(status_code=500, detail=str(e)) from e
