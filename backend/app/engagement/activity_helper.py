"""
Central Activity Logging Helper.

This module provides easy-to-use functions for logging activities
from any module in the system. Activities are stored in the
contact_activities table and used by the Engagement Brain.

Usage:
    from app.engagement.activity_helper import log_activity, log_linkedin_activity

    # Generic activity
    await log_activity(
        db=db,
        tenant_id="tenant",
        contact_id=123,
        channel="linkedin",
        activity_type="message_sent",
        direction="outbound",
        subject="Intro message",
        content="Hello...",
        source_module="linkedin"
    )

    # Channel-specific helpers
    await log_linkedin_activity(
        db=db,
        tenant_id="tenant",
        contact_id=123,
        activity_type="connection_request_sent",
        content="Connection note...",
        metadata={"profile_url": "..."}
    )
"""

from datetime import datetime
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.engagement.models import ContactActivity

# ============== Channel Constants ==============

class Channel:
    """Available channels for activities."""
    LINKEDIN = "linkedin"
    EMAIL = "email"
    PHONE = "phone"
    WHATSAPP = "whatsapp"
    WEBSITE = "website"
    LETTER = "letter"
    MEETING = "meeting"
    CRM = "crm"


class Direction:
    """Activity directions."""
    OUTBOUND = "outbound"
    INBOUND = "inbound"


# ============== LinkedIn Activity Types ==============

class LinkedInActivityType:
    """LinkedIn-specific activity types."""
    CONNECTION_REQUEST_SENT = "connection_request_sent"
    CONNECTION_REQUEST_ACCEPTED = "connection_request_accepted"
    CONNECTION_REQUEST_DECLINED = "connection_request_declined"
    MESSAGE_SENT = "message_sent"
    MESSAGE_RECEIVED = "message_received"
    INMAIL_SENT = "inmail_sent"
    INMAIL_RECEIVED = "inmail_received"
    PROFILE_VIEWED = "profile_viewed"
    PROFILE_SCRAPED = "profile_scraped"
    POST_LIKED = "post_liked"
    POST_COMMENTED = "post_commented"


# ============== Email Activity Types ==============

class EmailActivityType:
    """Email-specific activity types."""
    EMAIL_SENT = "email_sent"
    EMAIL_DELIVERED = "email_delivered"
    EMAIL_OPENED = "email_opened"
    EMAIL_CLICKED = "email_clicked"
    EMAIL_REPLIED = "email_replied"
    EMAIL_BOUNCED = "email_bounced"
    EMAIL_UNSUBSCRIBED = "email_unsubscribed"
    EMAIL_COMPLAINED = "email_complained"


# ============== Phone/CRM Activity Types ==============

class PhoneActivityType:
    """Phone-specific activity types."""
    CALL_SCHEDULED = "call_scheduled"
    CALL_MADE = "call_made"
    CALL_RECEIVED = "call_received"
    CALL_MISSED = "call_missed"
    CALL_VOICEMAIL = "call_voicemail"
    CALL_COMPLETED = "call_completed"


class CrmActivityType:
    """CRM-specific activity types."""
    NOTE_ADDED = "note_added"
    TASK_CREATED = "task_created"
    TASK_COMPLETED = "task_completed"
    MEETING_SCHEDULED = "meeting_scheduled"
    MEETING_COMPLETED = "meeting_completed"
    DEAL_CREATED = "deal_created"
    DEAL_STAGE_CHANGED = "deal_stage_changed"
    DEAL_WON = "deal_won"
    DEAL_LOST = "deal_lost"


# ============== Website Activity Types ==============

class WebsiteActivityType:
    """Website-specific activity types."""
    PAGE_VIEW = "page_view"
    FORM_SUBMIT = "form_submit"
    CTA_CLICK = "cta_click"
    DOWNLOAD = "download"
    VIDEO_WATCHED = "video_watched"
    SCROLL_DEPTH = "scroll_depth"


# ============== WhatsApp Activity Types ==============

class WhatsAppActivityType:
    """WhatsApp-specific activity types."""
    MESSAGE_SENT = "whatsapp_message_sent"
    MESSAGE_RECEIVED = "whatsapp_message_received"
    MESSAGE_DELIVERED = "whatsapp_message_delivered"
    MESSAGE_READ = "whatsapp_message_read"
    TEMPLATE_SENT = "whatsapp_template_sent"


# ============== Sentiment & Intent ==============

class Sentiment:
    """Detected sentiment values."""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class Intent:
    """Detected intent values."""
    INTERESTED = "interested"
    QUESTION = "question"
    OBJECTION = "objection"
    NOT_INTERESTED = "not_interested"
    REFERRAL = "referral"
    MEETING_REQUEST = "meeting_request"
    POSTPONE = "postpone"
    UNSUBSCRIBE = "unsubscribe"


# ============== Core Logging Function ==============

async def log_activity(
    db: AsyncSession,
    tenant_id: str,
    contact_id: int,
    channel: str,
    activity_type: str,
    direction: str | None = None,
    subject: str | None = None,
    content: str | None = None,
    source_module: str | None = None,
    source_action_id: int | None = None,
    pipeline_id: int | None = None,
    enrollment_id: int | None = None,
    external_id: str | None = None,
    sentiment: str | None = None,
    detected_intent: str | None = None,
    status: str | None = None,
    performed_by: int | None = None,
    performed_at: datetime | None = None,
    metadata: dict[str, Any] | None = None,
    commit: bool = True,
) -> ContactActivity:
    """
    Log an activity for a contact.

    This is the main function for logging activities. All channel-specific
    helpers call this function internally.

    Args:
        db: Database session
        tenant_id: Tenant identifier
        contact_id: Contact ID
        channel: Channel (linkedin, email, phone, etc.)
        activity_type: Type of activity (message_sent, call_made, etc.)
        direction: outbound or inbound (optional)
        subject: Short subject/summary (optional)
        content: Full content of the activity (optional)
        source_module: Module that created this activity (optional)
        source_action_id: Reference to pending_action if applicable (optional)
        pipeline_id: Associated pipeline (optional)
        enrollment_id: Associated enrollment (optional)
        external_id: External reference ID (optional)
        sentiment: Detected sentiment (positive/neutral/negative) (optional)
        detected_intent: Detected intent (interested/question/etc.) (optional)
        status: Activity status (sent/delivered/opened/etc.) (optional)
        performed_by: User ID who performed the action (optional)
        performed_at: When the activity happened (defaults to now)
        metadata: Additional metadata as dict (optional)
        commit: Whether to commit the transaction (default True)

    Returns:
        The created ContactActivity object
    """
    activity = ContactActivity(
        tenant_id=tenant_id,
        contact_id=contact_id,
        channel=channel,
        activity_type=activity_type,
        direction=direction,
        subject=subject,
        content=content,
        source_module=source_module or channel,
        source_action_id=source_action_id,
        pipeline_id=pipeline_id,
        enrollment_id=enrollment_id,
        external_id=external_id,
        sentiment=sentiment,
        detected_intent=detected_intent,
        status=status,
        performed_by=performed_by,
        performed_at=performed_at or datetime.utcnow(),
        metadata_=metadata,
    )

    db.add(activity)

    if commit:
        await db.commit()
        await db.refresh(activity)
    else:
        await db.flush()
        await db.refresh(activity)

    logger.info(
        "Activity logged: {channel}:{type} for contact {contact_id}",
        channel=channel,
        type=activity_type,
        contact_id=contact_id,
    )

    # Trigger event handler for inbound activities
    if direction == Direction.INBOUND and enrollment_id:
        try:
            from app.engagement.worker import EventHandler

            handler = EventHandler(db)
            await handler.handle_inbound_activity(activity)
        except Exception as e:
            logger.warning(
                "Failed to trigger event handler for activity {id}: {err}",
                id=activity.id,
                err=str(e),
            )

    return activity


# ============== LinkedIn Helpers ==============

async def log_linkedin_activity(
    db: AsyncSession,
    tenant_id: str,
    contact_id: int,
    activity_type: str,
    content: str | None = None,
    subject: str | None = None,
    direction: str | None = None,
    external_id: str | None = None,
    performed_by: int | None = None,
    performed_at: datetime | None = None,
    metadata: dict[str, Any] | None = None,
    commit: bool = True,
) -> ContactActivity:
    """
    Log a LinkedIn activity.

    Args:
        activity_type: Use LinkedInActivityType constants
    """
    # Determine direction if not provided
    if direction is None:
        if activity_type in [
            LinkedInActivityType.CONNECTION_REQUEST_SENT,
            LinkedInActivityType.MESSAGE_SENT,
            LinkedInActivityType.INMAIL_SENT,
            LinkedInActivityType.POST_LIKED,
            LinkedInActivityType.POST_COMMENTED,
        ]:
            direction = Direction.OUTBOUND
        elif activity_type in [
            LinkedInActivityType.MESSAGE_RECEIVED,
            LinkedInActivityType.INMAIL_RECEIVED,
            LinkedInActivityType.CONNECTION_REQUEST_ACCEPTED,
        ]:
            direction = Direction.INBOUND

    return await log_activity(
        db=db,
        tenant_id=tenant_id,
        contact_id=contact_id,
        channel=Channel.LINKEDIN,
        activity_type=activity_type,
        direction=direction,
        subject=subject,
        content=content,
        source_module="linkedin",
        external_id=external_id,
        performed_by=performed_by,
        performed_at=performed_at,
        metadata=metadata,
        commit=commit,
    )


# ============== Email Helpers ==============

async def log_email_activity(
    db: AsyncSession,
    tenant_id: str,
    contact_id: int,
    activity_type: str,
    subject: str | None = None,
    content: str | None = None,
    external_id: str | None = None,
    campaign_id: int | None = None,
    performed_by: int | None = None,
    metadata: dict[str, Any] | None = None,
    commit: bool = True,
) -> ContactActivity:
    """
    Log an email activity.

    Args:
        activity_type: Use EmailActivityType constants
        campaign_id: Email campaign ID if applicable
    """
    direction = Direction.OUTBOUND
    if activity_type == EmailActivityType.EMAIL_REPLIED:
        direction = Direction.INBOUND

    meta = metadata or {}
    if campaign_id:
        meta["campaign_id"] = campaign_id

    return await log_activity(
        db=db,
        tenant_id=tenant_id,
        contact_id=contact_id,
        channel=Channel.EMAIL,
        activity_type=activity_type,
        direction=direction,
        subject=subject,
        content=content,
        source_module="emailmarketing",
        external_id=external_id,
        performed_by=performed_by,
        metadata=meta,
        commit=commit,
    )


# ============== Phone/CRM Helpers ==============

async def log_phone_activity(
    db: AsyncSession,
    tenant_id: str,
    contact_id: int,
    activity_type: str,
    subject: str | None = None,
    content: str | None = None,
    duration_seconds: int | None = None,
    outcome: str | None = None,
    performed_by: int | None = None,
    metadata: dict[str, Any] | None = None,
    commit: bool = True,
) -> ContactActivity:
    """
    Log a phone activity.

    Args:
        activity_type: Use PhoneActivityType constants
        duration_seconds: Call duration in seconds
        outcome: Call outcome (connected, voicemail, no_answer, etc.)
    """
    direction = Direction.OUTBOUND
    if activity_type == PhoneActivityType.CALL_RECEIVED:
        direction = Direction.INBOUND

    meta = metadata or {}
    if duration_seconds:
        meta["duration_seconds"] = duration_seconds
    if outcome:
        meta["outcome"] = outcome

    return await log_activity(
        db=db,
        tenant_id=tenant_id,
        contact_id=contact_id,
        channel=Channel.PHONE,
        activity_type=activity_type,
        direction=direction,
        subject=subject,
        content=content,
        source_module="crm",
        performed_by=performed_by,
        metadata=meta,
        commit=commit,
    )


async def log_crm_activity(
    db: AsyncSession,
    tenant_id: str,
    contact_id: int,
    activity_type: str,
    subject: str | None = None,
    content: str | None = None,
    deal_id: int | None = None,
    task_id: int | None = None,
    performed_by: int | None = None,
    metadata: dict[str, Any] | None = None,
    commit: bool = True,
) -> ContactActivity:
    """
    Log a CRM activity (notes, tasks, deals).

    Args:
        activity_type: Use CrmActivityType constants
        deal_id: Associated deal ID
        task_id: Associated task ID
    """
    meta = metadata or {}
    if deal_id:
        meta["deal_id"] = deal_id
    if task_id:
        meta["task_id"] = task_id

    return await log_activity(
        db=db,
        tenant_id=tenant_id,
        contact_id=contact_id,
        channel=Channel.CRM,
        activity_type=activity_type,
        subject=subject,
        content=content,
        source_module="crm",
        performed_by=performed_by,
        metadata=meta,
        commit=commit,
    )


# ============== Website Helpers ==============

async def log_website_activity(
    db: AsyncSession,
    tenant_id: str,
    contact_id: int,
    activity_type: str,
    url: str | None = None,
    page_title: str | None = None,
    utm_source: str | None = None,
    utm_campaign: str | None = None,
    referrer: str | None = None,
    metadata: dict[str, Any] | None = None,
    commit: bool = True,
) -> ContactActivity:
    """
    Log a website activity.

    Args:
        activity_type: Use WebsiteActivityType constants
        url: Page URL
        utm_source: UTM source parameter
        utm_campaign: UTM campaign parameter
    """
    meta = metadata or {}
    if url:
        meta["url"] = url
    if page_title:
        meta["page_title"] = page_title
    if utm_source:
        meta["utm_source"] = utm_source
    if utm_campaign:
        meta["utm_campaign"] = utm_campaign
    if referrer:
        meta["referrer"] = referrer

    return await log_activity(
        db=db,
        tenant_id=tenant_id,
        contact_id=contact_id,
        channel=Channel.WEBSITE,
        activity_type=activity_type,
        direction=Direction.INBOUND,
        subject=page_title or url,
        source_module="engagement",
        metadata=meta,
        commit=commit,
    )


# ============== WhatsApp Helpers ==============

async def log_whatsapp_activity(
    db: AsyncSession,
    tenant_id: str,
    contact_id: int,
    activity_type: str,
    content: str | None = None,
    template_name: str | None = None,
    external_id: str | None = None,
    performed_by: int | None = None,
    metadata: dict[str, Any] | None = None,
    commit: bool = True,
) -> ContactActivity:
    """
    Log a WhatsApp activity.

    Args:
        activity_type: Use WhatsAppActivityType constants
        template_name: WhatsApp template name if applicable
    """
    direction = Direction.OUTBOUND
    if activity_type == WhatsAppActivityType.MESSAGE_RECEIVED:
        direction = Direction.INBOUND

    meta = metadata or {}
    if template_name:
        meta["template_name"] = template_name

    return await log_activity(
        db=db,
        tenant_id=tenant_id,
        contact_id=contact_id,
        channel=Channel.WHATSAPP,
        activity_type=activity_type,
        direction=direction,
        content=content,
        source_module="whatsapp",
        external_id=external_id,
        performed_by=performed_by,
        metadata=meta,
        commit=commit,
    )


# ============== Bulk Logging ==============

async def log_activities_bulk(
    db: AsyncSession,
    activities: list[dict],
    commit: bool = True,
) -> list[ContactActivity]:
    """
    Log multiple activities at once.

    Args:
        activities: List of dicts with activity parameters
        commit: Whether to commit after all inserts

    Returns:
        List of created ContactActivity objects
    """
    created = []
    for activity_data in activities:
        activity = await log_activity(
            db=db,
            commit=False,
            **activity_data,
        )
        created.append(activity)

    if commit:
        await db.commit()
        for activity in created:
            await db.refresh(activity)

    logger.info("Bulk logged {count} activities", count=len(created))
    return created
