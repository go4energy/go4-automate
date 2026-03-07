"""LinkedIn outreach services - Templates, Connections, Messages."""

from datetime import datetime

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.engagement.activity_helper import (
    LinkedInActivityType,
    log_linkedin_activity,
)
from app.exceptions import NotFoundError, ValidationError
from app.linkedin.models import (
    LinkedInAccount,
    LinkedInConnection,
    LinkedInContact,
    LinkedInMessage,
    LinkedInMessageTemplate,
)
from app.linkedin.schemas import (
    LinkedInConnectionBulkCreate,
    LinkedInConnectionBulkResult,
    LinkedInConnectionCreate,
    LinkedInMessageCreate,
    LinkedInTemplateCreate,
    LinkedInTemplateUpdate,
)


class TemplateService:
    """Service for message template management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self, tenant_id: str, data: LinkedInTemplateCreate
    ) -> LinkedInMessageTemplate:
        """Create a new message template."""
        # Extract variables from content
        import re
        found_vars = re.findall(r"\{(\w+)\}", data.content)
        variables = data.variables or list(set(found_vars))

        template = LinkedInMessageTemplate(
            tenant_id=tenant_id,
            name=data.name,
            category=data.category,
            subject=data.subject,
            content=data.content,
            variables=variables,
            variant_of_id=data.variant_of_id,
            variant_name=data.variant_name,
        )
        self.db.add(template)
        await self.db.flush()
        await self.db.refresh(template)
        logger.info("Template erstellt: {name}", name=data.name)
        return template

    async def get_by_id(self, tenant_id: str, template_id: int) -> LinkedInMessageTemplate:
        """Get a template by ID."""
        result = await self.db.execute(
            select(LinkedInMessageTemplate)
            .options(selectinload(LinkedInMessageTemplate.variants))
            .where(
                LinkedInMessageTemplate.id == template_id,
                LinkedInMessageTemplate.tenant_id == tenant_id,
            )
        )
        template = result.scalar_one_or_none()
        if not template:
            raise NotFoundError("LinkedInMessageTemplate", template_id)
        return template

    async def list_templates(
        self,
        tenant_id: str,
        category: str | None = None,
        active_only: bool = True,
    ) -> list[LinkedInMessageTemplate]:
        """List all templates for a tenant."""
        query = select(LinkedInMessageTemplate).where(
            LinkedInMessageTemplate.tenant_id == tenant_id
        )

        if category:
            query = query.where(LinkedInMessageTemplate.category == category)
        if active_only:
            query = query.where(LinkedInMessageTemplate.is_active.is_(True))

        query = query.order_by(LinkedInMessageTemplate.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update(
        self, tenant_id: str, template_id: int, data: LinkedInTemplateUpdate
    ) -> LinkedInMessageTemplate:
        """Update a template."""
        template = await self.get_by_id(tenant_id, template_id)
        update_data = data.model_dump(exclude_unset=True)

        # Re-extract variables if content changed
        if "content" in update_data:
            import re
            found_vars = re.findall(r"\{(\w+)\}", update_data["content"])
            update_data["variables"] = list(set(found_vars))

        for key, value in update_data.items():
            setattr(template, key, value)

        await self.db.flush()
        await self.db.refresh(template)
        logger.info("Template aktualisiert: {id}", id=template_id)
        return template

    async def delete(self, tenant_id: str, template_id: int) -> None:
        """Delete a template (soft delete by deactivating)."""
        template = await self.get_by_id(tenant_id, template_id)
        template.is_active = False
        await self.db.flush()
        logger.info("Template deaktiviert: {id}", id=template_id)

    async def render(
        self, tenant_id: str, template_id: int, context: dict
    ) -> tuple[str, str | None]:
        """Render a template with context variables."""
        template = await self.get_by_id(tenant_id, template_id)
        rendered_content = template.render(context)
        rendered_subject = None
        if template.subject:
            rendered_subject = template.subject
            for key, value in context.items():
                rendered_subject = rendered_subject.replace(
                    f"{{{key}}}", str(value) if value else ""
                )
        return rendered_content, rendered_subject

    async def increment_usage(self, template_id: int) -> None:
        """Increment usage counter."""
        result = await self.db.execute(
            select(LinkedInMessageTemplate).where(LinkedInMessageTemplate.id == template_id)
        )
        template = result.scalar_one_or_none()
        if template:
            template.times_used += 1
            await self.db.flush()

    async def increment_response(self, template_id: int) -> None:
        """Increment response counter."""
        result = await self.db.execute(
            select(LinkedInMessageTemplate).where(LinkedInMessageTemplate.id == template_id)
        )
        template = result.scalar_one_or_none()
        if template:
            template.responses_received += 1
            await self.db.flush()


class ConnectionService:
    """Service for connection request management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self, tenant_id: str, data: LinkedInConnectionCreate
    ) -> LinkedInConnection:
        """Create a new connection request."""
        await self._get_account(tenant_id, data.account_id)  # Validate account exists

        # Check for existing pending/sent connection
        existing = await self.db.execute(
            select(LinkedInConnection).where(
                LinkedInConnection.tenant_id == tenant_id,
                LinkedInConnection.linkedin_url == data.linkedin_url,
                LinkedInConnection.status.in_(["pending", "sent"]),
            )
        )
        if existing.scalar_one_or_none():
            raise ValidationError("Bereits eine ausstehende Verbindungsanfrage für dieses Profil")

        # Render message from template if provided
        message = data.message
        if data.template_id and not message:
            template_service = TemplateService(self.db)
            template = await template_service.get_by_id(tenant_id, data.template_id)
            message = template.render({
                "first_name": data.profile_name.split()[0] if data.profile_name else "",
                "name": data.profile_name,
            })
            # Truncate to 300 chars (LinkedIn limit)
            if len(message) > 300:
                message = message[:297] + "..."

        connection = LinkedInConnection(
            tenant_id=tenant_id,
            account_id=data.account_id,
            contact_id=data.contact_id,
            linkedin_url=data.linkedin_url,
            profile_name=data.profile_name,
            profile_headline=data.profile_headline,
            profile_picture_url=data.profile_picture_url,
            message=message,
            template_id=data.template_id,
            campaign_id=data.campaign_id,
            status="pending",
        )
        self.db.add(connection)
        await self.db.flush()
        await self.db.refresh(connection)
        logger.info("Connection erstellt: {name}", name=data.profile_name)
        return connection

    async def create_bulk(
        self, tenant_id: str, data: LinkedInConnectionBulkCreate
    ) -> LinkedInConnectionBulkResult:
        """Create connection requests for multiple contacts."""
        await self._get_account(tenant_id, data.account_id)  # Validate account exists

        # Get contacts
        contacts_result = await self.db.execute(
            select(LinkedInContact).where(
                LinkedInContact.tenant_id == tenant_id,
                LinkedInContact.id.in_(data.contact_ids),
            )
        )
        contacts = list(contacts_result.scalars().all())

        created = 0
        skipped = 0
        errors = []

        for contact in contacts:
            try:
                # Check for existing
                existing = await self.db.execute(
                    select(LinkedInConnection).where(
                        LinkedInConnection.tenant_id == tenant_id,
                        LinkedInConnection.linkedin_url == contact.linkedin_url,
                        LinkedInConnection.status.in_(["pending", "sent", "accepted"]),
                    )
                )
                if existing.scalar_one_or_none():
                    skipped += 1
                    continue

                # Render message
                message = data.message
                if data.template_id:
                    template_service = TemplateService(self.db)
                    template = await template_service.get_by_id(tenant_id, data.template_id)
                    context = {
                        "first_name": contact.first_name or contact.name.split()[0],
                        "last_name": contact.last_name or "",
                        "name": contact.name,
                        "company": contact.company_name or "",
                        "position": contact.position or "",
                        "headline": contact.headline or "",
                    }
                    message = template.render(context)
                    if len(message) > 300:
                        message = message[:297] + "..."

                connection = LinkedInConnection(
                    tenant_id=tenant_id,
                    account_id=data.account_id,
                    contact_id=contact.id,
                    linkedin_url=contact.linkedin_url,
                    profile_name=contact.name,
                    profile_headline=contact.headline,
                    profile_picture_url=contact.profile_picture_url,
                    message=message,
                    template_id=data.template_id,
                    campaign_id=data.campaign_id,
                    status="pending",
                )
                self.db.add(connection)
                created += 1

            except Exception as e:
                errors.append(f"{contact.name}: {e!s}")

        await self.db.flush()
        logger.info(
            "Bulk connections erstellt: {created} erstellt, {skipped} übersprungen",
            created=created,
            skipped=skipped,
        )

        return LinkedInConnectionBulkResult(
            total=len(data.contact_ids),
            created=created,
            skipped=skipped,
            errors=errors[:10],
        )

    async def get_by_id(self, tenant_id: str, connection_id: int) -> LinkedInConnection:
        """Get a connection by ID."""
        result = await self.db.execute(
            select(LinkedInConnection)
            .options(
                selectinload(LinkedInConnection.account),
                selectinload(LinkedInConnection.template),
            )
            .where(
                LinkedInConnection.id == connection_id,
                LinkedInConnection.tenant_id == tenant_id,
            )
        )
        connection = result.scalar_one_or_none()
        if not connection:
            raise NotFoundError("LinkedInConnection", connection_id)
        return connection

    async def list_connections(
        self,
        tenant_id: str,
        account_id: int | None = None,
        status: str | None = None,
        campaign_id: int | None = None,
    ) -> list[LinkedInConnection]:
        """List connections."""
        query = select(LinkedInConnection).where(
            LinkedInConnection.tenant_id == tenant_id
        )

        if account_id:
            query = query.where(LinkedInConnection.account_id == account_id)
        if status:
            query = query.where(LinkedInConnection.status == status)
        if campaign_id:
            query = query.where(LinkedInConnection.campaign_id == campaign_id)

        query = query.order_by(LinkedInConnection.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def mark_sent(self, connection_id: int) -> LinkedInConnection:
        """Mark connection as sent."""
        result = await self.db.execute(
            select(LinkedInConnection).where(LinkedInConnection.id == connection_id)
        )
        connection = result.scalar_one_or_none()
        if not connection:
            raise NotFoundError("LinkedInConnection", connection_id)

        connection.status = "sent"
        connection.sent_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(connection)

        # Increment template usage
        if connection.template_id:
            template_service = TemplateService(self.db)
            await template_service.increment_usage(connection.template_id)

        # Log activity
        if connection.contact_id:
            await log_linkedin_activity(
                db=self.db,
                tenant_id=connection.tenant_id,
                contact_id=connection.contact_id,
                activity_type=LinkedInActivityType.CONNECTION_REQUEST_SENT,
                subject=f"Connection request an {connection.profile_name}",
                content=connection.message,
                metadata={"connection_id": connection.id},
                commit=False,
            )

        return connection

    async def mark_accepted(self, connection_id: int) -> LinkedInConnection:
        """Mark connection as accepted."""
        result = await self.db.execute(
            select(LinkedInConnection).where(LinkedInConnection.id == connection_id)
        )
        connection = result.scalar_one_or_none()
        if not connection:
            raise NotFoundError("LinkedInConnection", connection_id)

        connection.status = "accepted"
        connection.accepted_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(connection)

        # Log activity
        if connection.contact_id:
            await log_linkedin_activity(
                db=self.db,
                tenant_id=connection.tenant_id,
                contact_id=connection.contact_id,
                activity_type=LinkedInActivityType.CONNECTION_REQUEST_ACCEPTED,
                subject=f"{connection.profile_name} hat Anfrage akzeptiert",
                metadata={"connection_id": connection.id},
                commit=False,
            )

        return connection

    async def mark_declined(self, connection_id: int) -> LinkedInConnection:
        """Mark connection as declined."""
        result = await self.db.execute(
            select(LinkedInConnection).where(LinkedInConnection.id == connection_id)
        )
        connection = result.scalar_one_or_none()
        if not connection:
            raise NotFoundError("LinkedInConnection", connection_id)

        connection.status = "declined"
        await self.db.flush()
        await self.db.refresh(connection)

        # Log activity
        if connection.contact_id:
            await log_linkedin_activity(
                db=self.db,
                tenant_id=connection.tenant_id,
                contact_id=connection.contact_id,
                activity_type=LinkedInActivityType.CONNECTION_REQUEST_DECLINED,
                subject=f"{connection.profile_name} hat Anfrage abgelehnt",
                metadata={"connection_id": connection.id},
                commit=False,
            )

        return connection

    async def withdraw(self, tenant_id: str, connection_id: int) -> LinkedInConnection:
        """Withdraw a pending connection request."""
        connection = await self.get_by_id(tenant_id, connection_id)

        if connection.status not in ["pending", "sent"]:
            raise ValidationError(
                f"Verbindungsanfrage kann nicht zurückgezogen werden (Status: {connection.status})"
            )

        connection.status = "withdrawn"
        connection.withdrawn_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(connection)
        logger.info("Connection zurückgezogen: {id}", id=connection_id)
        return connection

    async def mark_error(self, connection_id: int, error: str) -> None:
        """Mark connection as failed with error."""
        result = await self.db.execute(
            select(LinkedInConnection).where(LinkedInConnection.id == connection_id)
        )
        connection = result.scalar_one_or_none()
        if connection:
            connection.status = "error"
            connection.error_message = error
            connection.retry_count += 1
            await self.db.flush()

    async def get_pending_for_account(
        self, account_id: int, limit: int = 10
    ) -> list[LinkedInConnection]:
        """Get pending connections to send for an account."""
        result = await self.db.execute(
            select(LinkedInConnection)
            .where(
                LinkedInConnection.account_id == account_id,
                LinkedInConnection.status == "pending",
            )
            .order_by(LinkedInConnection.created_at)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def _get_account(self, tenant_id: str, account_id: int) -> LinkedInAccount:
        """Get and validate account."""
        result = await self.db.execute(
            select(LinkedInAccount).where(
                LinkedInAccount.id == account_id,
                LinkedInAccount.tenant_id == tenant_id,
            )
        )
        account = result.scalar_one_or_none()
        if not account:
            raise NotFoundError("LinkedInAccount", account_id)
        return account


class MessageService:
    """Service for direct message management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self, tenant_id: str, data: LinkedInMessageCreate
    ) -> LinkedInMessage:
        """Create a new message."""
        # Validate account
        account_result = await self.db.execute(
            select(LinkedInAccount).where(
                LinkedInAccount.id == data.account_id,
                LinkedInAccount.tenant_id == tenant_id,
            )
        )
        if not account_result.scalar_one_or_none():
            raise NotFoundError("LinkedInAccount", data.account_id)

        # Render content from template if provided
        content = data.content
        subject = data.subject
        if data.template_id:
            template_service = TemplateService(self.db)
            # Get contact info for context
            context = {"name": data.profile_name}
            if data.contact_id:
                contact_result = await self.db.execute(
                    select(LinkedInContact).where(LinkedInContact.id == data.contact_id)
                )
                contact = contact_result.scalar_one_or_none()
                if contact:
                    context = {
                        "first_name": contact.first_name or contact.name.split()[0],
                        "last_name": contact.last_name or "",
                        "name": contact.name,
                        "company": contact.company_name or "",
                        "position": contact.position or "",
                        "headline": contact.headline or "",
                    }
            content, subject = await template_service.render(
                tenant_id, data.template_id, context
            )

        message = LinkedInMessage(
            tenant_id=tenant_id,
            account_id=data.account_id,
            contact_id=data.contact_id,
            connection_id=data.connection_id,
            linkedin_url=data.linkedin_url,
            profile_name=data.profile_name,
            message_type=data.message_type,
            subject=subject,
            content=content,
            template_id=data.template_id,
            direction="outbound",
            status="pending",
            campaign_id=data.campaign_id,
        )
        self.db.add(message)
        await self.db.flush()
        await self.db.refresh(message)
        logger.info("Message erstellt: to={name}", name=data.profile_name)
        return message

    async def get_by_id(self, tenant_id: str, message_id: int) -> LinkedInMessage:
        """Get a message by ID."""
        result = await self.db.execute(
            select(LinkedInMessage)
            .options(
                selectinload(LinkedInMessage.account),
                selectinload(LinkedInMessage.template),
            )
            .where(
                LinkedInMessage.id == message_id,
                LinkedInMessage.tenant_id == tenant_id,
            )
        )
        message = result.scalar_one_or_none()
        if not message:
            raise NotFoundError("LinkedInMessage", message_id)
        return message

    async def list_messages(
        self,
        tenant_id: str,
        account_id: int | None = None,
        direction: str | None = None,
        status: str | None = None,
        campaign_id: int | None = None,
        linkedin_url: str | None = None,
    ) -> list[LinkedInMessage]:
        """List messages."""
        query = select(LinkedInMessage).where(LinkedInMessage.tenant_id == tenant_id)

        if account_id:
            query = query.where(LinkedInMessage.account_id == account_id)
        if direction:
            query = query.where(LinkedInMessage.direction == direction)
        if status:
            query = query.where(LinkedInMessage.status == status)
        if campaign_id:
            query = query.where(LinkedInMessage.campaign_id == campaign_id)
        if linkedin_url:
            query = query.where(LinkedInMessage.linkedin_url == linkedin_url)

        query = query.order_by(LinkedInMessage.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def mark_sent(self, message_id: int) -> LinkedInMessage:
        """Mark message as sent."""
        result = await self.db.execute(
            select(LinkedInMessage).where(LinkedInMessage.id == message_id)
        )
        message = result.scalar_one_or_none()
        if not message:
            raise NotFoundError("LinkedInMessage", message_id)

        message.status = "sent"
        message.sent_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(message)

        # Increment template usage
        if message.template_id:
            template_service = TemplateService(self.db)
            await template_service.increment_usage(message.template_id)

        # Log activity
        if message.contact_id:
            await log_linkedin_activity(
                db=self.db,
                tenant_id=message.tenant_id,
                contact_id=message.contact_id,
                activity_type=LinkedInActivityType.MESSAGE_SENT,
                subject=message.subject or f"Nachricht an {message.profile_name}",
                content=message.content,
                metadata={"message_id": message.id, "message_type": message.message_type},
                commit=False,
            )

        return message

    async def mark_replied(self, message_id: int) -> LinkedInMessage:
        """Mark message as replied."""
        result = await self.db.execute(
            select(LinkedInMessage).where(LinkedInMessage.id == message_id)
        )
        message = result.scalar_one_or_none()
        if not message:
            raise NotFoundError("LinkedInMessage", message_id)

        message.status = "replied"
        message.replied_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(message)

        # Increment template response
        if message.template_id:
            template_service = TemplateService(self.db)
            await template_service.increment_response(message.template_id)

        return message

    async def mark_error(self, message_id: int, error: str) -> None:
        """Mark message as failed."""
        result = await self.db.execute(
            select(LinkedInMessage).where(LinkedInMessage.id == message_id)
        )
        message = result.scalar_one_or_none()
        if message:
            message.status = "failed"
            message.error_message = error
            message.retry_count += 1
            await self.db.flush()

    async def record_inbound(
        self,
        tenant_id: str,
        account_id: int,
        linkedin_url: str,
        profile_name: str,
        content: str,
        conversation_id: str | None = None,
    ) -> LinkedInMessage:
        """Record an inbound message (reply)."""
        # Find contact
        contact_id = None
        contact_result = await self.db.execute(
            select(LinkedInContact).where(
                LinkedInContact.tenant_id == tenant_id,
                LinkedInContact.linkedin_url == linkedin_url,
            )
        )
        contact = contact_result.scalar_one_or_none()
        if contact:
            contact_id = contact.id

        # Find connection
        connection_id = None
        conn_result = await self.db.execute(
            select(LinkedInConnection).where(
                LinkedInConnection.tenant_id == tenant_id,
                LinkedInConnection.linkedin_url == linkedin_url,
                LinkedInConnection.status == "accepted",
            )
        )
        connection = conn_result.scalar_one_or_none()
        if connection:
            connection_id = connection.id

        message = LinkedInMessage(
            tenant_id=tenant_id,
            account_id=account_id,
            contact_id=contact_id,
            connection_id=connection_id,
            conversation_id=conversation_id,
            linkedin_url=linkedin_url,
            profile_name=profile_name,
            message_type="direct",
            content=content,
            direction="inbound",
            status="received",
            sent_at=datetime.utcnow(),
        )
        self.db.add(message)
        await self.db.flush()
        await self.db.refresh(message)

        # Mark previous outbound message as replied
        prev_result = await self.db.execute(
            select(LinkedInMessage)
            .where(
                LinkedInMessage.tenant_id == tenant_id,
                LinkedInMessage.linkedin_url == linkedin_url,
                LinkedInMessage.direction == "outbound",
                LinkedInMessage.status == "sent",
            )
            .order_by(LinkedInMessage.sent_at.desc())
            .limit(1)
        )
        prev_message = prev_result.scalar_one_or_none()
        if prev_message:
            await self.mark_replied(prev_message.id)

        # Log activity
        if message.contact_id:
            await log_linkedin_activity(
                db=self.db,
                tenant_id=message.tenant_id,
                contact_id=message.contact_id,
                activity_type=LinkedInActivityType.MESSAGE_RECEIVED,
                subject=f"Nachricht von {profile_name}",
                content=content,
                metadata={"message_id": message.id, "conversation_id": conversation_id},
                commit=False,
            )

        logger.info("Inbound message recorded: from={name}", name=profile_name)
        return message

    async def get_inbox(
        self, tenant_id: str, account_id: int | None = None
    ) -> list[dict]:
        """Get inbox conversations grouped by profile."""
        query = select(LinkedInMessage).where(LinkedInMessage.tenant_id == tenant_id)
        if account_id:
            query = query.where(LinkedInMessage.account_id == account_id)
        query = query.order_by(LinkedInMessage.created_at.desc())

        result = await self.db.execute(query)
        messages = list(result.scalars().all())

        # Group by linkedin_url
        conversations: dict[str, dict] = {}
        for msg in messages:
            if msg.linkedin_url not in conversations:
                conversations[msg.linkedin_url] = {
                    "conversation_id": msg.conversation_id,
                    "linkedin_url": msg.linkedin_url,
                    "profile_name": msg.profile_name,
                    "last_message_content": msg.content[:100],
                    "last_message_direction": msg.direction,
                    "last_message_at": msg.sent_at or msg.created_at,
                    "unread_count": 0,
                    "messages": [],
                }
            conversations[msg.linkedin_url]["messages"].append(msg)
            if msg.direction == "inbound" and msg.status == "received":
                conversations[msg.linkedin_url]["unread_count"] += 1

        return list(conversations.values())

    async def get_pending_for_account(
        self, account_id: int, limit: int = 10
    ) -> list[LinkedInMessage]:
        """Get pending messages to send for an account."""
        result = await self.db.execute(
            select(LinkedInMessage)
            .where(
                LinkedInMessage.account_id == account_id,
                LinkedInMessage.status == "pending",
                LinkedInMessage.direction == "outbound",
            )
            .order_by(LinkedInMessage.created_at)
            .limit(limit)
        )
        return list(result.scalars().all())
