"""WhatsApp module interface - config schema, metrics, status."""

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.module_interface import ModuleInterface
from app.utils.module_registry import register_module


class WhatsAppInterface(ModuleInterface):
    """WhatsApp module standardized interface."""

    MODULE_NAME = "whatsapp"
    PARAMS = [
        {
            "key": "default_account_id",
            "type": "integer",
            "default": None,
            "description": "Standard WhatsApp Account für neue Conversations",
            "category": "general",
        },
        {
            "key": "auto_create_contacts",
            "type": "boolean",
            "default": True,
            "description": "Kontakte automatisch aus eingehenden Nachrichten erstellen",
            "category": "contacts",
        },
        {
            "key": "mark_read_on_view",
            "type": "boolean",
            "default": True,
            "description": "Nachrichten beim Anzeigen als gelesen markieren",
            "category": "inbox",
        },
        {
            "key": "campaign_batch_size",
            "type": "integer",
            "default": 100,
            "description": "Batch-Größe für Kampagnen-Versand",
            "category": "campaigns",
        },
        {
            "key": "campaign_delay_ms",
            "type": "integer",
            "default": 100,
            "description": "Verzögerung zwischen Nachrichten (ms)",
            "category": "campaigns",
        },
    ]

    async def get_status(self, db: AsyncSession, tenant_id: str) -> dict:
        """Return WhatsApp health and operational status."""
        from app.whatsapp.models import (
            WhatsAppAccount,
            WhatsAppCampaign,
            WhatsAppConversation,
        )

        # Count active accounts
        active_accounts = await db.execute(
            select(func.count(WhatsAppAccount.id)).where(
                WhatsAppAccount.tenant_id == tenant_id,
                WhatsAppAccount.status == "active",
            )
        )

        # Count open conversations
        open_conversations = await db.execute(
            select(func.count(WhatsAppConversation.id)).where(
                WhatsAppConversation.tenant_id == tenant_id,
                WhatsAppConversation.status == "open",
            )
        )

        # Count campaigns
        total_campaigns = await db.execute(
            select(func.count(WhatsAppCampaign.id)).where(
                WhatsAppCampaign.tenant_id == tenant_id
            )
        )

        account_count = active_accounts.scalar() or 0

        return {
            "module": "whatsapp",
            "healthy": account_count > 0,
            "components": {
                "accounts": "ok" if account_count > 0 else "no_account",
                "database": "ok",
            },
            "active_accounts": account_count,
            "open_conversations": open_conversations.scalar() or 0,
            "total_campaigns": total_campaigns.scalar() or 0,
        }

    async def get_metrics(
        self, db: AsyncSession, tenant_id: str, days: int = 7
    ) -> dict:
        """Return WhatsApp KPIs."""
        from app.whatsapp.models import (
            WhatsAppCampaign,
            WhatsAppMessage,
        )

        cutoff = datetime.utcnow() - timedelta(days=days)

        # Messages sent in period
        messages_sent = await db.execute(
            select(func.count(WhatsAppMessage.id)).where(
                WhatsAppMessage.tenant_id == tenant_id,
                WhatsAppMessage.direction == "outbound",
                WhatsAppMessage.created_at >= cutoff,
            )
        )

        # Messages received
        messages_received = await db.execute(
            select(func.count(WhatsAppMessage.id)).where(
                WhatsAppMessage.tenant_id == tenant_id,
                WhatsAppMessage.direction == "inbound",
                WhatsAppMessage.created_at >= cutoff,
            )
        )

        # Delivered messages
        messages_delivered = await db.execute(
            select(func.count(WhatsAppMessage.id)).where(
                WhatsAppMessage.tenant_id == tenant_id,
                WhatsAppMessage.direction == "outbound",
                WhatsAppMessage.delivered_at.isnot(None),
                WhatsAppMessage.created_at >= cutoff,
            )
        )

        # Read messages
        messages_read = await db.execute(
            select(func.count(WhatsAppMessage.id)).where(
                WhatsAppMessage.tenant_id == tenant_id,
                WhatsAppMessage.direction == "outbound",
                WhatsAppMessage.read_at.isnot(None),
                WhatsAppMessage.created_at >= cutoff,
            )
        )

        # Campaigns sent
        campaigns_sent = await db.execute(
            select(func.count(WhatsAppCampaign.id)).where(
                WhatsAppCampaign.tenant_id == tenant_id,
                WhatsAppCampaign.sent_at >= cutoff,
            )
        )

        sent = messages_sent.scalar() or 0
        delivered = messages_delivered.scalar() or 0
        read = messages_read.scalar() or 0

        return {
            "module": "whatsapp",
            "period": f"{days}d",
            "metrics": {
                "messages_sent": sent,
                "messages_received": messages_received.scalar() or 0,
                "messages_delivered": delivered,
                "messages_read": read,
                "delivery_rate": round((delivered / sent) * 100, 2) if sent > 0 else 0,
                "read_rate": round((read / delivered) * 100, 2) if delivered > 0 else 0,
                "campaigns_sent": campaigns_sent.scalar() or 0,
            },
        }


whatsapp_interface = WhatsAppInterface()

# Auto-register for settings discovery
register_module(whatsapp_interface)
