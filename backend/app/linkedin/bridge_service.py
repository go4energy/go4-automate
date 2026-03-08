"""Bridge service: LinkedIn contacts → Central contacts + conversation import."""

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contacts.models import Contact
from app.engagement.activity_helper import log_linkedin_activity
from app.exceptions import NotFoundError
from app.linkedin.models import LinkedInContact, LinkedInMessage


class LinkedInBridgeService:
    """Bridges LinkedIn contacts to central Contact model."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def link_to_contact(
        self,
        tenant_id: str,
        linkedin_contact_id: int,
        contact_id: int,
    ) -> LinkedInContact:
        """Link an existing LinkedIn contact to an existing central contact."""
        li_contact = await self._get_linkedin_contact(tenant_id, linkedin_contact_id)

        # Validate central contact exists
        result = await self.db.execute(
            select(Contact).where(
                Contact.id == contact_id,
                Contact.tenant_id == tenant_id,
            )
        )
        if not result.scalar_one_or_none():
            raise NotFoundError("Contact", contact_id)

        li_contact.central_contact_id = contact_id
        await self.db.flush()
        await self.db.refresh(li_contact)
        logger.info(
            "Linked LinkedIn contact {li} → central contact {c}",
            li=linkedin_contact_id,
            c=contact_id,
        )
        return li_contact

    async def import_as_contact(
        self,
        tenant_id: str,
        linkedin_contact_id: int,
    ) -> Contact:
        """Create a central Contact from a LinkedIn contact and link them."""
        li_contact = await self._get_linkedin_contact(tenant_id, linkedin_contact_id)

        # Check if already linked
        if li_contact.central_contact_id:
            result = await self.db.execute(
                select(Contact).where(Contact.id == li_contact.central_contact_id)
            )
            existing = result.scalar_one_or_none()
            if existing:
                return existing

        # Check for existing contact by email or linkedin URL
        if li_contact.email:
            result = await self.db.execute(
                select(Contact).where(
                    Contact.tenant_id == tenant_id,
                    Contact.email == li_contact.email,
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                li_contact.central_contact_id = existing.id
                await self.db.flush()
                return existing

        # Create new central contact
        email = li_contact.email or f"li-{li_contact.id}@linkedin.placeholder"
        contact = Contact(
            tenant_id=tenant_id,
            email=email,
            name=li_contact.name,
            phone=li_contact.phone,
            position=li_contact.position,
            avatar_url=li_contact.profile_picture_url,
            source="linkedin",
            linkedin=li_contact.linkedin_url,
            notes=li_contact.headline,
            tags=["linkedin-import"],
            custom_fields={
                "linkedin_id": li_contact.linkedin_id,
                "company_name": li_contact.company_name,
                "location": li_contact.location,
            },
        )
        self.db.add(contact)
        await self.db.flush()
        await self.db.refresh(contact)

        # Link back
        li_contact.central_contact_id = contact.id
        await self.db.flush()

        logger.info(
            "Imported LinkedIn contact {li} as central contact {c}",
            li=linkedin_contact_id,
            c=contact.id,
        )
        return contact

    async def bulk_import_as_contacts(
        self,
        tenant_id: str,
        linkedin_contact_ids: list[int],
    ) -> dict:
        """Import multiple LinkedIn contacts as central contacts."""
        imported = 0
        skipped = 0
        contact_ids = []

        for li_id in linkedin_contact_ids:
            try:
                contact = await self.import_as_contact(tenant_id, li_id)
                contact_ids.append(contact.id)
                imported += 1
            except NotFoundError:
                skipped += 1
            except Exception as e:
                logger.warning("Failed to import LinkedIn contact {id}: {e}", id=li_id, e=str(e))
                skipped += 1

        return {
            "imported": imported,
            "skipped": skipped,
            "contact_ids": contact_ids,
        }

    async def import_conversations(
        self,
        tenant_id: str,
        linkedin_contact_id: int,
        contact_id: int,
    ) -> int:
        """Import LinkedIn messages for a contact as ContactActivities."""
        # Fetch all messages for this LinkedIn contact
        result = await self.db.execute(
            select(LinkedInMessage)
            .where(
                LinkedInMessage.tenant_id == tenant_id,
                LinkedInMessage.contact_id == linkedin_contact_id,
            )
            .order_by(LinkedInMessage.created_at)
        )
        messages = list(result.scalars().all())

        if not messages:
            return 0

        count = 0
        for msg in messages:
            activity_type = (
                "message_received" if msg.direction == "inbound" else "message_sent"
            )
            if msg.message_type == "inmail":
                activity_type = (
                    "inmail_received" if msg.direction == "inbound" else "inmail_sent"
                )

            await log_linkedin_activity(
                db=self.db,
                tenant_id=tenant_id,
                contact_id=contact_id,
                activity_type=activity_type,
                content=msg.content,
                subject=msg.subject,
                direction=msg.direction,
                external_id=str(msg.id),
                performed_at=msg.sent_at or msg.created_at,
                metadata={
                    "linkedin_message_id": msg.id,
                    "conversation_id": msg.conversation_id,
                    "message_type": msg.message_type,
                    "status": msg.status,
                    "profile_name": msg.profile_name,
                },
                commit=False,
            )
            count += 1

        logger.info(
            "Imported {count} LinkedIn messages as activities for contact {c}",
            count=count,
            c=contact_id,
        )
        return count

    async def _get_linkedin_contact(
        self, tenant_id: str, linkedin_contact_id: int
    ) -> LinkedInContact:
        """Get a LinkedIn contact by ID."""
        result = await self.db.execute(
            select(LinkedInContact).where(
                LinkedInContact.id == linkedin_contact_id,
                LinkedInContact.tenant_id == tenant_id,
            )
        )
        contact = result.scalar_one_or_none()
        if not contact:
            raise NotFoundError("LinkedInContact", linkedin_contact_id)
        return contact
