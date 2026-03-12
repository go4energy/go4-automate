"""WhatsApp Business service - Business logic for accounts, templates, conversations, campaigns."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.contacts.models import Contact
from app.engagement.activity_helper import (
    WhatsAppActivityType,
    log_whatsapp_activity,
)
from app.exceptions import AppError, NotFoundError
from app.whatsapp.encryption import encrypt_access_token
from app.whatsapp.meta_client import (
    MetaAPIError,
    MetaWhatsAppClient,
    calculate_window_expiry,
    format_template_variables,
    is_window_open,
    normalize_phone_number,
)
from app.whatsapp.models import (
    WhatsAppAccount,
    WhatsAppCampaign,
    WhatsAppCampaignRecipient,
    WhatsAppConversation,
    WhatsAppMessage,
    WhatsAppTemplate,
)
from app.whatsapp.schemas import (
    WhatsAppAccountCreate,
    WhatsAppAccountUpdate,
    WhatsAppCampaignCreate,
    WhatsAppCampaignUpdate,
    WhatsAppMessageSend,
)

# ============== Account Service ==============


class WhatsAppAccountService:
    """Service for WhatsApp account management."""

    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def create(self, data: WhatsAppAccountCreate) -> WhatsAppAccount:
        """Create a new WhatsApp account."""
        # Generate webhook verify token if not provided
        webhook_token = data.webhook_verify_token or str(uuid4())

        account = WhatsAppAccount(
            tenant_id=self.tenant_id,
            name=data.name,
            phone_number=data.phone_number,
            phone_number_id=data.phone_number_id,
            waba_id=data.waba_id,
            access_token_encrypted=encrypt_access_token(data.access_token),
            webhook_verify_token=webhook_token,
            daily_limit=data.daily_limit,
        )

        self.db.add(account)
        await self.db.commit()
        await self.db.refresh(account)

        logger.info(
            "WhatsApp Account erstellt: {name} ({phone})",
            name=account.name,
            phone=account.phone_number,
        )
        return account

    async def get_by_id(self, account_id: int) -> WhatsAppAccount:
        """Get account by ID."""
        result = await self.db.execute(
            select(WhatsAppAccount).where(
                WhatsAppAccount.id == account_id,
                WhatsAppAccount.tenant_id == self.tenant_id,
            )
        )
        account = result.scalar_one_or_none()
        if not account:
            raise NotFoundError("WhatsApp Account", account_id)
        return account

    async def list_accounts(self, status: str | None = None) -> list[WhatsAppAccount]:
        """List all accounts for tenant."""
        query = select(WhatsAppAccount).where(
            WhatsAppAccount.tenant_id == self.tenant_id
        )
        if status:
            query = query.where(WhatsAppAccount.status == status)
        query = query.order_by(WhatsAppAccount.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update(
        self, account_id: int, data: WhatsAppAccountUpdate
    ) -> WhatsAppAccount:
        """Update an account."""
        account = await self.get_by_id(account_id)

        update_data = data.model_dump(exclude_unset=True)

        # Encrypt access token if provided
        if update_data.get("access_token"):
            update_data["access_token_encrypted"] = encrypt_access_token(
                update_data.pop("access_token")
            )
        elif "access_token" in update_data:
            del update_data["access_token"]

        for field, value in update_data.items():
            setattr(account, field, value)

        await self.db.commit()
        await self.db.refresh(account)

        logger.info("WhatsApp Account aktualisiert: {id}", id=account_id)
        return account

    async def delete(self, account_id: int) -> None:
        """Delete an account."""
        account = await self.get_by_id(account_id)
        await self.db.delete(account)
        await self.db.commit()
        logger.info("WhatsApp Account gelöscht: {id}", id=account_id)

    async def verify_credentials(self, account_id: int) -> dict:
        """Verify account credentials with Meta API."""
        account = await self.get_by_id(account_id)

        client = MetaWhatsAppClient(
            phone_number_id=account.phone_number_id,
            access_token_encrypted=account.access_token_encrypted,
            waba_id=account.waba_id,
        )

        try:
            result = await client.verify_credentials()
            account.status = "active"
            account.last_error = None
            account.last_verified_at = datetime.utcnow()
            await self.db.commit()

            logger.info(
                "WhatsApp Credentials verifiziert: {id}",
                id=account_id,
            )
            return result
        except MetaAPIError as e:
            account.status = "error"
            account.last_error = e.message
            await self.db.commit()
            raise AppError(f"Meta API Fehler: {e.message}", 400) from e
        finally:
            await client.close()

    def get_client(self, account: WhatsAppAccount) -> MetaWhatsAppClient:
        """Get Meta API client for account."""
        return MetaWhatsAppClient(
            phone_number_id=account.phone_number_id,
            access_token_encrypted=account.access_token_encrypted,
            waba_id=account.waba_id,
        )


# ============== Template Service ==============


class WhatsAppTemplateService:
    """Service for WhatsApp template management."""

    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def sync_templates(self, account_id: int) -> list[WhatsAppTemplate]:
        """Sync templates from Meta for an account."""
        account_service = WhatsAppAccountService(self.db, self.tenant_id)
        account = await account_service.get_by_id(account_id)

        client = account_service.get_client(account)

        try:
            meta_templates = await client.get_templates()
        finally:
            await client.close()

        synced_templates = []

        for mt in meta_templates:
            # Check if template exists
            result = await self.db.execute(
                select(WhatsAppTemplate).where(
                    WhatsAppTemplate.account_id == account_id,
                    WhatsAppTemplate.name == mt["name"],
                    WhatsAppTemplate.language == mt["language"],
                )
            )
            template = result.scalar_one_or_none()

            # Extract variables from components
            variables = self._extract_variables(mt.get("components", []))

            if template:
                # Update existing
                template.category = mt.get("category", "UTILITY")
                template.status = mt.get("status", "PENDING")
                template.components = mt.get("components", [])
                template.variables = variables
                template.last_synced_at = datetime.utcnow()
            else:
                # Create new
                template = WhatsAppTemplate(
                    tenant_id=self.tenant_id,
                    account_id=account_id,
                    name=mt["name"],
                    language=mt["language"],
                    category=mt.get("category", "UTILITY"),
                    status=mt.get("status", "PENDING"),
                    components=mt.get("components", []),
                    variables=variables,
                    last_synced_at=datetime.utcnow(),
                )
                self.db.add(template)

            synced_templates.append(template)

        await self.db.commit()

        logger.info(
            "Templates synchronisiert für Account {id}: {count}",
            id=account_id,
            count=len(synced_templates),
        )
        return synced_templates

    def _extract_variables(self, components: list[dict]) -> list[str]:
        """Extract variable names from template components."""
        variables = []
        var_count = 0

        for component in components:
            text = component.get("text", "")
            # Count {{n}} placeholders
            count = text.count("{{")
            for _ in range(count):
                var_count += 1
                variables.append(f"var{var_count}")

        return variables

    async def get_by_id(self, template_id: int) -> WhatsAppTemplate:
        """Get template by ID."""
        result = await self.db.execute(
            select(WhatsAppTemplate).where(
                WhatsAppTemplate.id == template_id,
                WhatsAppTemplate.tenant_id == self.tenant_id,
            )
        )
        template = result.scalar_one_or_none()
        if not template:
            raise NotFoundError("WhatsApp Template", template_id)
        return template

    async def list_templates(
        self,
        account_id: int | None = None,
        status: str | None = None,
    ) -> list[WhatsAppTemplate]:
        """List templates."""
        query = select(WhatsAppTemplate).where(
            WhatsAppTemplate.tenant_id == self.tenant_id
        )
        if account_id:
            query = query.where(WhatsAppTemplate.account_id == account_id)
        if status:
            query = query.where(WhatsAppTemplate.status == status)
        query = query.order_by(WhatsAppTemplate.name)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def preview_template(self, template_id: int, variables: dict) -> dict:
        """Preview template with variables."""
        template = await self.get_by_id(template_id)

        rendered_text = ""
        for component in template.components:
            if component.get("type") == "BODY":
                text = component.get("text", "")
                # Replace {{n}} with variable values
                for i, var_name in enumerate(template.variables, 1):
                    value = variables.get(var_name, f"{{{{{i}}}}}")
                    text = text.replace(f"{{{{{i}}}}}", str(value))
                rendered_text = text
                break

        return {
            "name": template.name,
            "language": template.language,
            "rendered_text": rendered_text,
            "components": template.components,
        }


# ============== Conversation Service ==============


class WhatsAppConversationService:
    """Service for WhatsApp conversation management."""

    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def get_or_create(
        self,
        account_id: int,
        phone: str,
        contact_id: int | None = None,
        contact_name: str | None = None,
    ) -> WhatsAppConversation:
        """Get existing conversation or create new one."""
        phone = normalize_phone_number(phone)

        # Try to find existing
        result = await self.db.execute(
            select(WhatsAppConversation).where(
                WhatsAppConversation.account_id == account_id,
                WhatsAppConversation.phone == phone,
            )
        )
        conversation = result.scalar_one_or_none()

        if conversation:
            # Update contact info if provided
            if contact_id and not conversation.contact_id:
                conversation.contact_id = contact_id
            if contact_name and not conversation.contact_name:
                conversation.contact_name = contact_name
            await self.db.commit()
            return conversation

        # Create new conversation
        conversation = WhatsAppConversation(
            tenant_id=self.tenant_id,
            account_id=account_id,
            phone=phone,
            contact_id=contact_id,
            contact_name=contact_name,
        )
        self.db.add(conversation)
        await self.db.commit()
        await self.db.refresh(conversation)

        logger.info(
            "Neue WhatsApp Conversation: {phone}",
            phone=phone,
        )
        return conversation

    async def get_by_id(self, conversation_id: int) -> WhatsAppConversation:
        """Get conversation by ID with messages."""
        result = await self.db.execute(
            select(WhatsAppConversation)
            .options(selectinload(WhatsAppConversation.messages))
            .where(
                WhatsAppConversation.id == conversation_id,
                WhatsAppConversation.tenant_id == self.tenant_id,
            )
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise NotFoundError("WhatsApp Conversation", conversation_id)
        return conversation

    async def list_conversations(
        self,
        account_id: int | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[WhatsAppConversation]:
        """List conversations (inbox)."""
        query = select(WhatsAppConversation).where(
            WhatsAppConversation.tenant_id == self.tenant_id
        )
        if account_id:
            query = query.where(WhatsAppConversation.account_id == account_id)
        if status:
            query = query.where(WhatsAppConversation.status == status)

        query = query.order_by(WhatsAppConversation.last_message_at.desc().nullslast())
        query = query.limit(limit).offset(offset)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def send_message(
        self,
        conversation_id: int,
        message_data: WhatsAppMessageSend,
    ) -> WhatsAppMessage:
        """Send a message in a conversation."""
        conversation = await self.get_by_id(conversation_id)

        # Get account
        account_service = WhatsAppAccountService(self.db, self.tenant_id)
        account = await account_service.get_by_id(conversation.account_id)

        # Check 24h window for non-template messages
        if message_data.message_type != "template" and not is_window_open(
            conversation.window_expires_at
        ):
            raise AppError(
                "24h-Fenster abgelaufen. Nur Template-Nachrichten erlaubt.",
                400,
            )

        # Build message content
        content: dict[str, Any] = {}
        if message_data.message_type == "text" and message_data.text:
            content = {
                "type": "text",
                "text": {"body": message_data.text.body},
            }
        elif message_data.message_type == "template" and message_data.template:
            content = {
                "type": "template",
                "template": {
                    "name": message_data.template.name,
                    "language": message_data.template.language,
                    "components": message_data.template.components or [],
                },
            }
        elif message_data.message_type in ("image", "document", "audio", "video"):
            media_data = getattr(message_data, message_data.message_type)
            if media_data:
                content = {
                    "type": message_data.message_type,
                    message_data.message_type: media_data.model_dump(exclude_none=True),
                }

        # Create message record
        message = WhatsAppMessage(
            tenant_id=self.tenant_id,
            conversation_id=conversation_id,
            direction="outbound",
            message_type=message_data.message_type,
            content=content,
            template_name=message_data.template.name if message_data.template else None,
            status="pending",
        )
        self.db.add(message)
        await self.db.flush()

        # Send via Meta API
        client = account_service.get_client(account)

        try:
            if message_data.message_type == "text" and message_data.text:
                wamid = await client.send_text_message(
                    to=conversation.phone,
                    body=message_data.text.body,
                    preview_url=message_data.text.preview_url,
                )
            elif message_data.message_type == "template" and message_data.template:
                wamid = await client.send_template_message(
                    to=conversation.phone,
                    template_name=message_data.template.name,
                    language_code=message_data.template.language,
                    components=message_data.template.components,
                )
            elif message_data.message_type in ("image", "document", "audio", "video"):
                media_data = getattr(message_data, message_data.message_type)
                wamid = await client.send_media_message(
                    to=conversation.phone,
                    media_type=message_data.message_type,
                    media_url=media_data.link if media_data else None,
                    media_id=media_data.id if media_data else None,
                    caption=media_data.caption if media_data else None,
                    filename=media_data.filename if media_data else None,
                )
            else:
                raise AppError(
                    f"Unsupported message type: {message_data.message_type}", 400
                )

            message.wamid = wamid
            message.status = "sent"
            message.sent_at = datetime.utcnow()

            # Update conversation
            conversation.last_message_at = datetime.utcnow()
            preview = ""
            if message_data.text:
                preview = message_data.text.body[:200]
            elif message_data.template:
                preview = f"[Template: {message_data.template.name}]"
            else:
                preview = f"[{message_data.message_type.title()}]"
            conversation.last_message_preview = preview

            # Increment daily counter
            account.messages_sent_today += 1

        except MetaAPIError as e:
            message.status = "failed"
            message.error_code = e.code
            message.error_message = e.message
            raise AppError(f"Fehler beim Senden: {e.message}", 400) from e
        finally:
            await client.close()

        await self.db.commit()
        await self.db.refresh(message)

        # Log activity if conversation has contact
        if conversation.contact_id and message.status == "sent":
            try:
                activity_type = (
                    WhatsAppActivityType.TEMPLATE_SENT
                    if message_data.message_type == "template"
                    else WhatsAppActivityType.MESSAGE_SENT
                )
                preview = ""
                if message_data.text:
                    preview = message_data.text.body[:200]
                elif message_data.template:
                    preview = f"[Template: {message_data.template.name}]"
                await log_whatsapp_activity(
                    db=self.db,
                    tenant_id=self.tenant_id,
                    contact_id=conversation.contact_id,
                    activity_type=activity_type,
                    content=preview,
                    template_name=message_data.template.name if message_data.template else None,
                    external_id=message.wamid,
                    metadata={"conversation_id": conversation.id, "message_id": message.id},
                )
            except Exception as e:
                logger.warning(f"Activity logging failed for WA send: {e}")

        return message

    async def mark_as_read(self, conversation_id: int) -> WhatsAppConversation:
        """Mark all messages in conversation as read."""
        conversation = await self.get_by_id(conversation_id)

        # Reset unread count
        conversation.unread_count = 0

        # Mark messages as read in Meta
        account_service = WhatsAppAccountService(self.db, self.tenant_id)
        account = await account_service.get_by_id(conversation.account_id)
        client = account_service.get_client(account)

        try:
            # Get last unread inbound message
            for message in reversed(conversation.messages):
                if message.direction == "inbound" and message.wamid:
                    await client.mark_as_read(message.wamid)
                    break
        finally:
            await client.close()

        await self.db.commit()
        return conversation

    async def handle_incoming_message(
        self,
        account: WhatsAppAccount,
        from_phone: str,
        wamid: str,
        message_type: str,
        content: dict,
        timestamp: datetime,
    ) -> WhatsAppMessage:
        """Handle incoming message from webhook."""
        phone = normalize_phone_number(from_phone)

        # Try to find contact by mobile number
        contact_result = await self.db.execute(
            select(Contact).where(
                Contact.tenant_id == self.tenant_id,
                Contact.mobile == phone,
            )
        )
        contact = contact_result.scalar_one_or_none()

        # Get or create conversation
        conversation = await self.get_or_create(
            account_id=account.id,
            phone=phone,
            contact_id=contact.id if contact else None,
            contact_name=contact.name if contact else None,
        )

        # Update 24h window
        conversation.window_expires_at = calculate_window_expiry(timestamp)
        conversation.last_message_at = timestamp
        conversation.unread_count += 1

        # Set preview
        if message_type == "text":
            conversation.last_message_preview = content.get("text", {}).get("body", "")[
                :200
            ]
        else:
            conversation.last_message_preview = f"[{message_type.title()}]"

        # Create message
        message = WhatsAppMessage(
            tenant_id=self.tenant_id,
            conversation_id=conversation.id,
            direction="inbound",
            message_type=message_type,
            content=content,
            wamid=wamid,
            status="received",
            sent_at=timestamp,
        )
        self.db.add(message)

        await self.db.commit()
        await self.db.refresh(message)

        # Log activity if contact known
        if conversation.contact_id:
            try:
                preview = ""
                if message_type == "text":
                    preview = content.get("text", {}).get("body", "")[:200]
                else:
                    preview = f"[{message_type.title()}]"
                await log_whatsapp_activity(
                    db=self.db,
                    tenant_id=self.tenant_id,
                    contact_id=conversation.contact_id,
                    activity_type=WhatsAppActivityType.MESSAGE_RECEIVED,
                    content=preview,
                    external_id=wamid,
                    metadata={"conversation_id": conversation.id, "message_id": message.id},
                )
            except Exception as e:
                logger.warning(f"Activity logging failed for WA incoming: {e}")

        logger.info(
            "Eingehende WhatsApp Nachricht: {phone} -> {type}",
            phone=phone,
            type=message_type,
        )
        return message

    async def update_message_status(
        self,
        wamid: str,
        status: str,
        timestamp: datetime,
        error_code: int | None = None,
        error_message: str | None = None,
    ) -> WhatsAppMessage | None:
        """Update message status from webhook."""
        result = await self.db.execute(
            select(WhatsAppMessage).where(WhatsAppMessage.wamid == wamid)
        )
        message = result.scalar_one_or_none()

        if not message:
            logger.warning("Message not found for status update: {wamid}", wamid=wamid)
            return None

        message.status = status

        if status == "delivered":
            message.delivered_at = timestamp
        elif status == "read":
            message.read_at = timestamp
        elif status == "failed":
            message.error_code = error_code
            message.error_message = error_message

        await self.db.commit()
        await self.db.refresh(message)

        # Log activity for delivered/read status
        if status in ("delivered", "read") and message.conversation_id:
            try:
                conv_result = await self.db.execute(
                    select(WhatsAppConversation).where(
                        WhatsAppConversation.id == message.conversation_id
                    )
                )
                conv = conv_result.scalar_one_or_none()
                if conv and conv.contact_id:
                    activity_type = (
                        WhatsAppActivityType.MESSAGE_DELIVERED
                        if status == "delivered"
                        else WhatsAppActivityType.MESSAGE_READ
                    )
                    await log_whatsapp_activity(
                        db=self.db,
                        tenant_id=self.tenant_id,
                        contact_id=conv.contact_id,
                        activity_type=activity_type,
                        external_id=wamid,
                        metadata={"status": status},
                    )
            except Exception as e:
                logger.warning(f"Activity logging failed for WA status: {e}")

        logger.info(
            "Message Status Update: {wamid} -> {status}",
            wamid=wamid,
            status=status,
        )
        return message


# ============== Campaign Service ==============


class WhatsAppCampaignService:
    """Service for WhatsApp campaign management."""

    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def create(self, data: WhatsAppCampaignCreate) -> WhatsAppCampaign:
        """Create a new campaign."""
        # Verify account exists
        account_service = WhatsAppAccountService(self.db, self.tenant_id)
        await account_service.get_by_id(data.account_id)

        # Verify template exists
        if data.template_id:
            template_service = WhatsAppTemplateService(self.db, self.tenant_id)
            await template_service.get_by_id(data.template_id)

        campaign = WhatsAppCampaign(
            tenant_id=self.tenant_id,
            account_id=data.account_id,
            template_id=data.template_id,
            name=data.name,
            segment_filters=data.segment_filters,
            contact_ids=data.contact_ids,
        )

        self.db.add(campaign)
        await self.db.commit()
        await self.db.refresh(campaign)

        logger.info("WhatsApp Kampagne erstellt: {name}", name=campaign.name)
        return campaign

    async def get_by_id(self, campaign_id: int) -> WhatsAppCampaign:
        """Get campaign by ID."""
        result = await self.db.execute(
            select(WhatsAppCampaign)
            .options(
                selectinload(WhatsAppCampaign.template),
                selectinload(WhatsAppCampaign.account),
            )
            .where(
                WhatsAppCampaign.id == campaign_id,
                WhatsAppCampaign.tenant_id == self.tenant_id,
            )
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise NotFoundError("WhatsApp Kampagne", campaign_id)
        return campaign

    async def list_campaigns(
        self,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
        pipeline_id: int | None = None,
    ) -> list[WhatsAppCampaign]:
        """List campaigns."""
        query = select(WhatsAppCampaign).where(
            WhatsAppCampaign.tenant_id == self.tenant_id
        )
        if status:
            query = query.where(WhatsAppCampaign.status == status)
        if pipeline_id is not None:
            query = query.where(WhatsAppCampaign.pipeline_id == pipeline_id)
        query = query.order_by(WhatsAppCampaign.created_at.desc())
        query = query.limit(limit).offset(offset)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update(
        self, campaign_id: int, data: WhatsAppCampaignUpdate
    ) -> WhatsAppCampaign:
        """Update a campaign."""
        campaign = await self.get_by_id(campaign_id)

        if campaign.status not in ("draft", "scheduled"):
            raise AppError(
                "Nur Draft/Scheduled Kampagnen können bearbeitet werden", 400
            )

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(campaign, field, value)

        await self.db.commit()
        await self.db.refresh(campaign)

        logger.info("WhatsApp Kampagne aktualisiert: {id}", id=campaign_id)
        return campaign

    async def delete(self, campaign_id: int) -> None:
        """Delete a campaign."""
        campaign = await self.get_by_id(campaign_id)

        if campaign.status in ("sending", "sent"):
            raise AppError("Gesendete Kampagnen können nicht gelöscht werden", 400)

        await self.db.delete(campaign)
        await self.db.commit()
        logger.info("WhatsApp Kampagne gelöscht: {id}", id=campaign_id)

    async def generate_recipients(
        self,
        campaign_id: int,
        default_variables: dict | None = None,
    ) -> int:
        """Generate recipients for a campaign."""
        campaign = await self.get_by_id(campaign_id)

        if campaign.status != "draft":
            raise AppError(
                "Empfänger können nur für Draft-Kampagnen generiert werden", 400
            )

        # Delete existing recipients
        await self.db.execute(
            select(WhatsAppCampaignRecipient).where(
                WhatsAppCampaignRecipient.campaign_id == campaign_id
            )
        )

        # Build contact query
        query = select(Contact).where(
            Contact.tenant_id == self.tenant_id,
            Contact.mobile.isnot(None),
        )

        # Apply segment filters
        if campaign.segment_filters:
            if "tags" in campaign.segment_filters:
                tags = campaign.segment_filters["tags"]
                query = query.where(Contact.tags.op("&&")(tags))
            if "source" in campaign.segment_filters:
                query = query.where(
                    Contact.source == campaign.segment_filters["source"]
                )

        # Or use explicit contact IDs
        if campaign.contact_ids:
            query = query.where(Contact.id.in_(campaign.contact_ids))

        result = await self.db.execute(query)
        contacts = result.scalars().all()

        # Create recipients
        count = 0
        for contact in contacts:
            if not contact.mobile:
                continue

            phone = normalize_phone_number(contact.mobile)

            # Build variables
            variables = {**(default_variables or {})}
            variables["name"] = contact.name
            if contact.company_id:
                variables["company"] = (
                    contact.company.name
                    if hasattr(contact, "company") and contact.company
                    else ""
                )

            recipient = WhatsAppCampaignRecipient(
                tenant_id=self.tenant_id,
                campaign_id=campaign_id,
                contact_id=contact.id,
                phone=phone,
                contact_name=contact.name,
                template_variables=variables,
            )
            self.db.add(recipient)
            count += 1

        campaign.total_recipients = count
        await self.db.commit()

        logger.info(
            "Empfänger generiert für Kampagne {id}: {count}",
            id=campaign_id,
            count=count,
        )
        return count

    async def send_campaign(self, campaign_id: int) -> WhatsAppCampaign:
        """Send a campaign immediately."""
        campaign = await self.get_by_id(campaign_id)

        if campaign.status not in ("draft", "scheduled"):
            raise AppError("Kampagne kann nicht gesendet werden", 400)

        if campaign.total_recipients == 0:
            raise AppError("Keine Empfänger generiert", 400)

        if not campaign.template_id:
            raise AppError("Kein Template ausgewählt", 400)

        # Get template
        template_service = WhatsAppTemplateService(self.db, self.tenant_id)
        template = await template_service.get_by_id(campaign.template_id)

        # Get account
        account_service = WhatsAppAccountService(self.db, self.tenant_id)
        account = await account_service.get_by_id(campaign.account_id)

        campaign.status = "sending"
        await self.db.commit()

        # Get recipients
        result = await self.db.execute(
            select(WhatsAppCampaignRecipient).where(
                WhatsAppCampaignRecipient.campaign_id == campaign_id,
                WhatsAppCampaignRecipient.status == "pending",
            )
        )
        recipients = result.scalars().all()

        client = account_service.get_client(account)

        try:
            for recipient in recipients:
                try:
                    # Format variables
                    components = format_template_variables(
                        template.components,
                        recipient.template_variables,
                    )

                    wamid = await client.send_template_message(
                        to=recipient.phone,
                        template_name=template.name,
                        language_code=template.language,
                        components=components,
                    )

                    recipient.wamid = wamid
                    recipient.status = "sent"
                    recipient.sent_at = datetime.utcnow()
                    campaign.sent_count += 1

                except MetaAPIError as e:
                    recipient.status = "failed"
                    recipient.error_message = e.message
                    campaign.failed_count += 1
                    logger.error(
                        "Fehler beim Senden an {phone}: {error}",
                        phone=recipient.phone,
                        error=e.message,
                    )

                # Commit batch
                await self.db.commit()

        finally:
            await client.close()

        campaign.status = "sent"
        campaign.sent_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(campaign)

        logger.info(
            "Kampagne gesendet: {id} - {sent}/{total}",
            id=campaign_id,
            sent=campaign.sent_count,
            total=campaign.total_recipients,
        )
        return campaign

    async def schedule_campaign(
        self, campaign_id: int, scheduled_at: datetime
    ) -> WhatsAppCampaign:
        """Schedule a campaign for later."""
        campaign = await self.get_by_id(campaign_id)

        if campaign.status != "draft":
            raise AppError("Nur Draft-Kampagnen können geplant werden", 400)

        if scheduled_at <= datetime.utcnow():
            raise AppError("Geplante Zeit muss in der Zukunft liegen", 400)

        campaign.status = "scheduled"
        campaign.scheduled_at = scheduled_at
        await self.db.commit()
        await self.db.refresh(campaign)

        logger.info(
            "Kampagne geplant: {id} für {time}",
            id=campaign_id,
            time=scheduled_at,
        )
        return campaign

    async def list_recipients(
        self,
        campaign_id: int,
        status: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[WhatsAppCampaignRecipient]:
        """List campaign recipients."""
        query = select(WhatsAppCampaignRecipient).where(
            WhatsAppCampaignRecipient.campaign_id == campaign_id
        )

        if status:
            query = query.where(WhatsAppCampaignRecipient.status == status)
        if search:
            query = query.where(
                (WhatsAppCampaignRecipient.phone.ilike(f"%{search}%"))
                | (WhatsAppCampaignRecipient.contact_name.ilike(f"%{search}%"))
            )

        query = query.order_by(WhatsAppCampaignRecipient.created_at)
        query = query.limit(limit).offset(offset)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_stats(self, campaign_id: int) -> dict:
        """Get campaign statistics."""
        campaign = await self.get_by_id(campaign_id)

        delivery_rate = 0.0
        read_rate = 0.0

        if campaign.sent_count > 0:
            delivery_rate = round(
                (campaign.delivered_count / campaign.sent_count) * 100, 2
            )
        if campaign.delivered_count > 0:
            read_rate = round((campaign.read_count / campaign.delivered_count) * 100, 2)

        return {
            "total_recipients": campaign.total_recipients,
            "sent": campaign.sent_count,
            "delivered": campaign.delivered_count,
            "read": campaign.read_count,
            "failed": campaign.failed_count,
            "delivery_rate": delivery_rate,
            "read_rate": read_rate,
        }

    async def update_recipient_status(
        self,
        wamid: str,
        status: str,
        timestamp: datetime,
    ) -> None:
        """Update recipient status from webhook."""
        result = await self.db.execute(
            select(WhatsAppCampaignRecipient).where(
                WhatsAppCampaignRecipient.wamid == wamid
            )
        )
        recipient = result.scalar_one_or_none()

        if not recipient:
            return

        # Get campaign to update counters
        campaign_result = await self.db.execute(
            select(WhatsAppCampaign).where(WhatsAppCampaign.id == recipient.campaign_id)
        )
        campaign = campaign_result.scalar_one_or_none()

        if status == "delivered" and recipient.status != "delivered":
            recipient.delivered_at = timestamp
            recipient.status = "delivered"
            if campaign:
                campaign.delivered_count += 1

        elif status == "read" and recipient.status not in ("read",):
            recipient.read_at = timestamp
            recipient.status = "read"
            if campaign:
                campaign.read_count += 1

        elif status == "failed" and recipient.status != "failed":
            recipient.status = "failed"
            if campaign:
                campaign.failed_count += 1

        await self.db.commit()
