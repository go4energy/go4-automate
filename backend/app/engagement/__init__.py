"""Engagement module - Multi-channel AI-driven engagement orchestration."""

# Re-export activity helper for easy imports
from app.engagement.activity_helper import (
    # Constants
    Channel,
    CrmActivityType,
    Direction,
    EmailActivityType,
    Intent,
    LinkedInActivityType,
    PhoneActivityType,
    Sentiment,
    WebsiteActivityType,
    WhatsAppActivityType,
    log_activities_bulk,
    # Core function
    log_activity,
    log_crm_activity,
    log_email_activity,
    # Channel-specific helpers
    log_linkedin_activity,
    log_phone_activity,
    log_website_activity,
    log_whatsapp_activity,
)

__all__ = [
    # Constants
    "Channel",
    "CrmActivityType",
    "Direction",
    "EmailActivityType",
    "Intent",
    "LinkedInActivityType",
    "PhoneActivityType",
    "Sentiment",
    "WebsiteActivityType",
    "WhatsAppActivityType",
    "log_activities_bulk",
    # Core function
    "log_activity",
    "log_crm_activity",
    "log_email_activity",
    # Channel-specific helpers
    "log_linkedin_activity",
    "log_phone_activity",
    "log_website_activity",
    "log_whatsapp_activity",
]
