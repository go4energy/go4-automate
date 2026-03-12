"""WhatsApp webhook handler for Meta Cloud API.

This router handles:
1. Webhook verification (GET request from Meta)
2. Incoming messages and status updates (POST request from Meta)

The webhook URL must be publicly accessible with HTTPS.
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Request
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.whatsapp.models import WhatsAppAccount
from app.whatsapp.service import (
    WhatsAppCampaignService,
    WhatsAppConversationService,
)

router = APIRouter(prefix="/whatsapp", tags=["whatsapp-webhooks"])


@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
):
    """Verify webhook with Meta.

    Meta sends a GET request with:
    - hub.mode: should be "subscribe"
    - hub.verify_token: should match our configured token
    - hub.challenge: value to return if verification succeeds
    """
    logger.info(
        "Webhook verification: mode={mode}, token={token}",
        mode=hub_mode,
        token=hub_verify_token[:10] + "..."
        if len(hub_verify_token) > 10
        else hub_verify_token,
    )

    if hub_mode != "subscribe":
        raise HTTPException(status_code=400, detail="Invalid hub.mode")

    # Check against all accounts' verify tokens
    async with async_session() as db:
        result = await db.execute(
            select(WhatsAppAccount).where(
                WhatsAppAccount.webhook_verify_token == hub_verify_token
            )
        )
        account = result.scalar_one_or_none()

        if not account:
            logger.warning("Webhook verification failed: invalid token")
            raise HTTPException(status_code=403, detail="Invalid verify token")

    logger.info("Webhook verified successfully for account: {id}", id=account.id)
    return int(hub_challenge)


@router.post("/webhook")
async def receive_webhook(request: Request):
    """Receive webhook events from Meta.

    Events include:
    - Incoming messages (text, image, document, etc.)
    - Message status updates (sent, delivered, read, failed)
    """
    try:
        payload = await request.json()
    except Exception as e:
        logger.error("Failed to parse webhook payload: {err}", err=str(e))
        raise HTTPException(status_code=400, detail="Invalid JSON") from e

    logger.debug("Webhook payload received: {payload}", payload=payload)

    # Validate object type
    if payload.get("object") != "whatsapp_business_account":
        logger.warning("Unknown webhook object: {obj}", obj=payload.get("object"))
        return {"status": "ignored"}

    async with async_session() as db:
        for entry in payload.get("entry", []):
            await _process_entry(db, entry)

    return {"status": "ok"}


async def _process_entry(db: AsyncSession, entry: dict):
    """Process a single webhook entry."""
    # waba_id = entry.get("id")  # Could be used for logging

    for change in entry.get("changes", []):
        if change.get("field") != "messages":
            continue

        value = change.get("value", {})
        metadata = value.get("metadata", {})
        phone_number_id = metadata.get("phone_number_id")

        # Find account by phone_number_id
        result = await db.execute(
            select(WhatsAppAccount).where(
                WhatsAppAccount.phone_number_id == phone_number_id
            )
        )
        account = result.scalar_one_or_none()

        if not account:
            logger.warning(
                "Account not found for phone_number_id: {id}",
                id=phone_number_id,
            )
            continue

        # Process messages
        for message in value.get("messages", []):
            await _process_incoming_message(db, account, message)

        # Process status updates
        for status in value.get("statuses", []):
            await _process_status_update(db, account, status)


async def _process_incoming_message(
    db: AsyncSession,
    account: WhatsAppAccount,
    message: dict,
):
    """Process an incoming message."""
    from_phone = message.get("from")
    wamid = message.get("id")
    timestamp_str = message.get("timestamp")
    message_type = message.get("type")

    # Parse timestamp
    try:
        timestamp = datetime.fromtimestamp(int(timestamp_str))
    except (ValueError, TypeError):
        timestamp = datetime.utcnow()

    # Build content based on type
    content = {}
    if message_type == "text":
        content = {"text": message.get("text", {})}
    elif message_type == "image":
        content = {"image": message.get("image", {})}
    elif message_type == "document":
        content = {"document": message.get("document", {})}
    elif message_type == "audio":
        content = {"audio": message.get("audio", {})}
    elif message_type == "video":
        content = {"video": message.get("video", {})}
    elif message_type == "location":
        content = {"location": message.get("location", {})}
    elif message_type == "contacts":
        content = {"contacts": message.get("contacts", [])}
    elif message_type == "interactive":
        content = {"interactive": message.get("interactive", {})}
    elif message_type == "button":
        content = {"button": message.get("button", {})}
    else:
        content = {"raw": message}

    # Use conversation service
    service = WhatsAppConversationService(db, account.tenant_id)

    try:
        await service.handle_incoming_message(
            account=account,
            from_phone=from_phone,
            wamid=wamid,
            message_type=message_type,
            content=content,
            timestamp=timestamp,
        )
    except Exception as e:
        logger.error(
            "Failed to process incoming message: {err}",
            err=str(e),
        )


async def _process_status_update(
    db: AsyncSession,
    account: WhatsAppAccount,
    status: dict,
):
    """Process a message status update."""
    wamid = status.get("id")
    status_value = status.get("status")
    timestamp_str = status.get("timestamp")
    # recipient_id = status.get("recipient_id")  # Could be used for logging

    # Parse timestamp
    try:
        timestamp = datetime.fromtimestamp(int(timestamp_str))
    except (ValueError, TypeError):
        timestamp = datetime.utcnow()

    # Extract error info
    error_code = None
    error_message = None
    errors = status.get("errors", [])
    if errors:
        error_code = errors[0].get("code")
        error_message = errors[0].get("message") or errors[0].get("title")

    logger.info(
        "Status update: {wamid} -> {status}",
        wamid=wamid,
        status=status_value,
    )

    # Update conversation message
    conv_service = WhatsAppConversationService(db, account.tenant_id)
    await conv_service.update_message_status(
        wamid=wamid,
        status=status_value,
        timestamp=timestamp,
        error_code=error_code,
        error_message=error_message,
    )

    # Update campaign recipient if applicable
    campaign_service = WhatsAppCampaignService(db, account.tenant_id)
    await campaign_service.update_recipient_status(
        wamid=wamid,
        status=status_value,
        timestamp=timestamp,
    )
