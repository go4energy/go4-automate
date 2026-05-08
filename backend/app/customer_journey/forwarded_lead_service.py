"""ForwardedLeadService — detect + handle Cold-Mail-Forwards.

Use-Case: Cold-Mail an Müller (info@elektrofirma.de) wird intern weitergeleitet
an seinen Kollegen Meier. Meier klickt den Tracking-Link (= Müllers ref_code),
füllt das Formular auf der Webseite mit eigener Email aus.

Ohne diesen Service: ``IdentifyService`` würde Meiers Daten in Müllers Contact
schreiben → Müllers Identität verschwindet, Meier hat keinen eigenen Contact,
Pipeline-Enrollments laufen falsch weiter.

Mit diesem Service: Müller bleibt unangetastet, Meier wird als eigener Contact
mit ``source_contact_id = Müller.id`` angelegt, Müllers aktive Enrollments
werden mit ``stopped_reason='forwarded_to_colleague'`` gestoppt. Die spätere
Auto-Enrollment-Logik (AutoEnrollmentRouter) routet Meier in die passenden
Inbound-Pipelines anhand seiner Tags.

Detection-Regel: gleiche Email-Domain. Cross-Domain → kein Forward (Standard-Pfad).
"""

from datetime import datetime
from typing import TYPE_CHECKING

from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.contacts.models import Contact
from app.contacts.utils import generate_tracking_hash as _generate_hash
from app.customer_journey.models import JourneyEvent
from app.engagement.models import PipelineEnrollment

if TYPE_CHECKING:
    from app.customer_journey.schemas import IdentifyRequest


class ForwardedLeadService:
    """Erkennt + verarbeitet weitergeleitete Cold-Mail-Klicks."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def is_forwarded_lead(
        self,
        tenant_id: str,
        existing_hash: str | None,
        new_email: str | None,
    ) -> tuple[bool, Contact | None]:
        """Returns (is_forward, original_contact).

        True wenn:
        - existing_hash zeigt auf realen Contact A (kein Placeholder)
        - new_email != A.email (sonst gleiche Person)
        - email-Domain von A == email-Domain von new_email (gleiche Firma)
        """
        if not existing_hash or not new_email:
            return False, None

        result = await self.db.execute(
            select(Contact).where(
                Contact.tenant_id == tenant_id,
                Contact.tracking_hash == existing_hash,
            )
        )
        hash_contact = result.scalar_one_or_none()
        if not hash_contact or not hash_contact.email:
            return False, None
        if hash_contact.email.endswith("@journey.placeholder"):
            return False, None
        if hash_contact.email.lower() == new_email.lower():
            return False, None

        try:
            domain_a = hash_contact.email.split("@", 1)[1].lower()
            domain_b = new_email.split("@", 1)[1].lower()
        except IndexError:
            return False, None
        if domain_a != domain_b:
            return False, None

        return True, hash_contact

    async def process_forward(
        self,
        tenant_id: str,
        original: Contact,
        data: "IdentifyRequest",
    ) -> Contact:
        """Erstellt Empfänger-Contact, stoppt Originals Enrollments.

        Auto-Enrollment in Folge-Pipelines passiert nicht hier, sondern
        nachgelagert über AutoEnrollmentRouter im IdentifyService.
        """
        # 1. Check: gibt's Empfänger-Email bereits als Contact?
        existing = await self.db.execute(
            select(Contact).where(
                Contact.tenant_id == tenant_id,
                Contact.email == data.email,
            )
        )
        receiver = existing.scalar_one_or_none()

        if receiver:
            # Empfänger existiert schon — nur source_contact_id setzen falls leer
            if not receiver.source_contact_id:
                receiver.source_contact_id = original.id
            if not receiver.company_id and original.company_id:
                receiver.company_id = original.company_id
        else:
            # 2. Neuer Contact für Empfänger
            receiver = Contact(
                tenant_id=tenant_id,
                email=data.email,
                name=data.name or "Unbekannt",
                phone=data.phone,
                source=data.source or "forward",
                tracking_hash=_generate_hash(),
                journey_status="active",
                tags=[],
                custom_fields={},
                source_contact_id=original.id,
                company_id=original.company_id,
            )
            self.db.add(receiver)
            await self.db.flush()
            logger.info(
                "Forward detected: new contact {rid} (source={oid}, domain={dom})",
                rid=receiver.id,
                oid=original.id,
                dom=(data.email or "").split("@", 1)[-1] if data.email else "",
            )

        # 3. Originals aktive Enrollments stoppen
        await self.db.execute(
            update(PipelineEnrollment)
            .where(
                PipelineEnrollment.contact_id == original.id,
                PipelineEnrollment.tenant_id == tenant_id,
                PipelineEnrollment.status == "active",
            )
            .values(
                status="stopped",
                stopped_reason="forwarded_to_colleague",
                completed_at=datetime.utcnow(),
            )
        )

        # 4. Audit-Events
        self.db.add(
            JourneyEvent(
                tenant_id=tenant_id,
                contact_id=original.id,
                event="lead_forwarded",
                category="conversion",
                source_site=data.source or "website_form",
                metadata_={"forwarded_to_contact_id": receiver.id},
            )
        )
        self.db.add(
            JourneyEvent(
                tenant_id=tenant_id,
                contact_id=receiver.id,
                event="identified_via_forward",
                category="conversion",
                source_site=data.source or "website_form",
                metadata_={"forwarded_from_contact_id": original.id},
            )
        )

        await self.db.flush()
        return receiver
