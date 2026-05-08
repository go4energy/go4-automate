"""Customer Journey service - identify, events, ref-codes, campaigns."""

import secrets
import string
from datetime import datetime, timedelta

from loguru import logger
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.contacts.models import Contact
from app.contacts.utils import generate_tracking_hash as _generate_hash
from app.customer_journey.forwarded_lead_service import ForwardedLeadService
from app.customer_journey.models import (
    JourneyCampaign,
    JourneyEvent,
    JourneyRefCode,
)
from app.customer_journey.schemas import (
    BulkRefCodeCreate,
    CampaignCreate,
    CampaignUpdate,
    IdentifyRequest,
    RefCodeCreate,
    RefCodeUpdate,
    TrackEventRequest,
)
from app.engagement.auto_enrollment_router import AutoEnrollmentRouter
from app.engagement.models import PipelineEnrollment
from app.exceptions import NotFoundError


def _generate_ref_code(length: int = 6) -> str:
    """Generate a short ref code."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


class IdentifyService:
    """Handle lead identification — find or create contacts."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def identify(
        self,
        tenant_id: str,
        data: IdentifyRequest,
        *,
        skip_event: bool = False,
        source_site: str | None = None,
    ) -> tuple[Contact, bool, bool]:
        """Identify a lead — 5-step pipeline.

        1) Forward-Detection (gleiche Domain, andere Email)
        2) Standard-Identify (Hash/Email/Phone-Match oder Neuanlage)
        3) Tags + custom_fields aus data mergen (set-union)
        4) Self-Signup-Upgrade (aktive Outreach-Enrollments → engaged)
        5) Auto-Enrollment in matchende Pipelines mit auto_enroll_filter

        Returns (contact, is_new, merged).
        """
        # === Schritt 1: Forward-Detection ==========================
        fws = ForwardedLeadService(self.db)
        is_forward, original = await fws.is_forwarded_lead(
            tenant_id, data.existing_hash, data.email
        )

        if is_forward and original is not None:
            contact = await fws.process_forward(tenant_id, original, data)
            is_new = True
            merged = False
        else:
            contact, is_new, merged = await self._standard_identify(
                tenant_id, data, skip_event=skip_event, source_site=source_site
            )

        # === Schritt 3: Tags + custom_fields mergen =================
        if data.tags:
            current_tags = list(contact.tags or [])
            new_tags = sorted(set(current_tags) | set(data.tags))
            if new_tags != current_tags:
                contact.tags = new_tags
        if data.custom_fields:
            current_fields = dict(contact.custom_fields or {})
            current_fields.update(data.custom_fields)
            contact.custom_fields = current_fields

        # === Schritt 4: Self-Signup-Upgrade =========================
        # Wenn Contact sich aktiv mit Email identifiziert (kein Placeholder):
        # alle aktiven Enrollments mit stage in (lead, contacted) → engaged
        if data.email and not data.email.endswith("@journey.placeholder"):
            await self._upgrade_active_enrollments_on_signup(
                tenant_id, contact.id
            )

        # === Schritt 5: Auto-Enrollment in matchende Pipelines ======
        if data.email and not data.email.endswith("@journey.placeholder"):
            router = AutoEnrollmentRouter(self.db)
            await router.match_and_enroll(
                contact,
                source_context={
                    "identify_source": data.source,
                    "ref_code": data.ref_code,
                    "from_forward": is_forward,
                },
            )

        await self.db.flush()
        await self.db.refresh(contact)
        return contact, is_new, merged

    async def _upgrade_active_enrollments_on_signup(
        self, tenant_id: str, contact_id: int
    ) -> int:
        """Hebe aktive Enrollments mit stage<engaged auf 'engaged'.

        Brain stoppt damit automatisch laufende Cold-Mail-Sequenzen,
        weil engaged != lead/contacted die Cold-Outreach-Trigger nicht mehr
        feuern lässt.
        """
        result = await self.db.execute(
            select(PipelineEnrollment).where(
                PipelineEnrollment.tenant_id == tenant_id,
                PipelineEnrollment.contact_id == contact_id,
                PipelineEnrollment.status == "active",
                PipelineEnrollment.stage.in_(["lead", "contacted"]),
            )
        )
        enrollments = list(result.scalars().all())
        for enr in enrollments:
            enr.stage = "engaged"
            ctx = dict(enr.source_context or {})
            ctx["signed_up_via_identify"] = True
            ctx["signed_up_at"] = datetime.utcnow().isoformat()
            enr.source_context = ctx
        if enrollments:
            await self.db.flush()
            logger.info(
                "Self-signup detected: {n} enrollments upgraded to 'engaged' "
                "for contact {cid}",
                n=len(enrollments),
                cid=contact_id,
            )
        return len(enrollments)

    async def _standard_identify(
        self,
        tenant_id: str,
        data: IdentifyRequest,
        *,
        skip_event: bool = False,
        source_site: str | None = None,
    ) -> tuple[Contact, bool, bool]:
        """Standard-Identify-Pfad — Hash/Email/Phone-Match oder Neuanlage.

        Wird vom neuen identify()-Wrapper aufgerufen wenn KEIN Forward
        erkannt wurde. Enthält die ursprüngliche Identify-Logik.
        """
        contact = None
        is_new = False
        merged = False

        # 1. Match by email
        if data.email:
            result = await self.db.execute(
                select(Contact).where(
                    Contact.tenant_id == tenant_id,
                    Contact.email == data.email,
                )
            )
            contact = result.scalar_one_or_none()

        # 2. Match by phone
        if not contact and data.phone:
            result = await self.db.execute(
                select(Contact).where(
                    Contact.tenant_id == tenant_id,
                    or_(
                        Contact.phone == data.phone,
                        Contact.mobile == data.phone,
                    ),
                )
            )
            contact = result.scalar_one_or_none()

        # 3. Match by existing_hash
        # Sicherheit: wenn data.email gegeben UND Hash-Owner ist ein realer
        # Contact mit ABWEICHENDER Email (kein Placeholder), dann ignoriere
        # den Hash — sonst würden wir die fremde Identität übernehmen
        # (Cross-Domain-Forward, Hash-Hijack, geteilter Browser etc.).
        # Same-Domain-Forward wird vor diesem Pfad bereits via
        # ForwardedLeadService abgefangen.
        if not contact and data.existing_hash:
            result = await self.db.execute(
                select(Contact).where(
                    Contact.tenant_id == tenant_id,
                    Contact.tracking_hash == data.existing_hash,
                )
            )
            candidate = result.scalar_one_or_none()
            if (
                candidate
                and data.email
                and candidate.email
                and not candidate.email.endswith("@journey.placeholder")
                and candidate.email.lower() != data.email.lower()
            ):
                logger.info(
                    "Hash-mismatch: ignoring hash {h} (owner={oe}, "
                    "submitted={ne})",
                    h=data.existing_hash, oe=candidate.email, ne=data.email,
                )
                candidate = None
            contact = candidate

        # 4. Create new contact
        if not contact:
            if not data.email and not data.name:
                data.name = "Unbekannt"

            contact = Contact(
                tenant_id=tenant_id,
                email=data.email or f"anon-{_generate_hash(8)}@journey.placeholder",
                name=data.name or "Unbekannt",
                phone=data.phone,
                source=data.source,
                tracking_hash=_generate_hash(),
                journey_status="new",
                tags=[],
                custom_fields={},
            )
            self.db.add(contact)
            await self.db.flush()
            is_new = True
            logger.info(
                "Neuer Journey-Lead: {email} (Tenant: {t})",
                email=contact.email,
                t=tenant_id,
            )

        # Ensure tracking_hash exists on existing contact
        if not contact.tracking_hash:
            contact.tracking_hash = _generate_hash()
            await self.db.flush()

        # Update placeholder contacts with real data
        is_placeholder = contact.email and (
            contact.email.endswith("@journey.placeholder")
        )
        if is_placeholder and data.email:
            # Check if a real contact with this email already exists
            existing_real = await self.db.execute(
                select(Contact).where(
                    Contact.tenant_id == tenant_id,
                    Contact.email == data.email,
                )
            )
            real_contact = existing_real.scalar_one_or_none()

            if real_contact:
                # Merge placeholder journey into existing real contact
                merged = await self._merge_journeys(
                    tenant_id, contact.tracking_hash, real_contact
                )
                # Ensure real contact has tracking_hash
                if not real_contact.tracking_hash:
                    real_contact.tracking_hash = contact.tracking_hash
                contact = real_contact
                is_new = False
                logger.info(
                    "Placeholder merged into existing contact {id}",
                    id=real_contact.id,
                )
            else:
                # No existing contact — upgrade placeholder
                contact.email = data.email
                if data.name:
                    contact.name = data.name
                if data.phone:
                    contact.phone = data.phone
                if data.source:
                    contact.source = data.source
                logger.info(
                    "Placeholder upgraded: → {email}",
                    email=data.email,
                )
        else:
            # Normal update — fill in missing fields
            if data.name and contact.name == "Unbekannt":
                contact.name = data.name
            if data.phone and not contact.phone:
                contact.phone = data.phone
            if data.source and not contact.source:
                contact.source = data.source

        # Handle existing_hash merge
        if data.existing_hash and data.existing_hash != contact.tracking_hash:
            merged = await self._merge_journeys(
                tenant_id, data.existing_hash, contact
            )

        # Log event — distinguish real identification from anonymous interest
        # Skip event when called from prepare-link (no actual visit happened)
        if not skip_event:
            is_anonymous = not data.email and not data.phone
            event = JourneyEvent(
                tenant_id=tenant_id,
                contact_id=contact.id,
                event="interest_detected" if is_anonymous else "identify",
                category="awareness" if is_anonymous else "conversion",
                source_site=source_site or data.source or "unknown",
                utm_source=data.utm_source,
                utm_medium=data.utm_medium,
                utm_campaign=data.utm_campaign,
                utm_term=getattr(data, "utm_term", None),
                utm_content=getattr(data, "utm_content", None),
                metadata_=data.metadata,
            )
            self.db.add(event)

        # Update journey_status if new
        if contact.journey_status == "new" and not is_new:
            contact.journey_status = "active"

        await self.db.flush()
        await self.db.refresh(contact)

        return contact, is_new, merged

    async def _merge_journeys(
        self, tenant_id: str, old_hash: str, target: Contact
    ) -> bool:
        """Merge events from old tracking hash to target contact."""
        result = await self.db.execute(
            select(Contact).where(
                Contact.tenant_id == tenant_id,
                Contact.tracking_hash == old_hash,
            )
        )
        old_contact = result.scalar_one_or_none()
        if not old_contact or old_contact.id == target.id:
            return False

        # Move events from old contact to target
        await self.db.execute(
            update(JourneyEvent)
            .where(JourneyEvent.contact_id == old_contact.id)
            .values(contact_id=target.id)
        )
        # Move ref-codes
        await self.db.execute(
            update(JourneyRefCode)
            .where(JourneyRefCode.contact_id == old_contact.id)
            .values(contact_id=target.id)
        )

        logger.info(
            "Journey merged: {old} → {new}",
            old=old_contact.id,
            new=target.id,
        )
        return True


class EventService:
    """Handle journey event tracking."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def track_event(
        self,
        tenant_id: str,
        data: TrackEventRequest,
        *,
        source_site: str | None = None,
    ) -> str | None:
        """Log a journey event. Returns tracking_hash or None.

        If source_site is provided (e.g. derived from API key), it overrides
        the value from the request payload to prevent client-side spoofing.
        """
        contact = None

        # Resolve contact from tracking_hash
        if data.tracking_hash:
            result = await self.db.execute(
                select(Contact).where(
                    Contact.tenant_id == tenant_id,
                    Contact.tracking_hash == data.tracking_hash,
                )
            )
            contact = result.scalar_one_or_none()

        # Resolve from ref_code
        if not contact and data.ref_code:
            result = await self.db.execute(
                select(JourneyRefCode)
                .options(selectinload(JourneyRefCode.contact))
                .where(
                    JourneyRefCode.tenant_id == tenant_id,
                    JourneyRefCode.ref_code == data.ref_code,
                )
            )
            ref = result.scalar_one_or_none()
            if ref and ref.contact:
                contact = ref.contact
                # Increment visit count
                ref.visit_count = (ref.visit_count or 0) + 1

        # No contact found — skip anonymous events
        if not contact:
            return None

        # Ensure contact has a tracking_hash
        if not contact.tracking_hash:
            contact.tracking_hash = _generate_hash()
            contact.journey_status = contact.journey_status or "new"

        event = JourneyEvent(
            tenant_id=tenant_id,
            contact_id=contact.id,
            event=data.event,
            category=self._categorize_event(data.event),
            page_path=data.page_path,
            source_site=source_site or data.source_site,
            utm_source=data.utm_source,
            utm_medium=data.utm_medium,
            utm_campaign=data.utm_campaign,
            utm_term=getattr(data, "utm_term", None),
            utm_content=getattr(data, "utm_content", None),
            ref_code=data.ref_code,
            metadata_=data.metadata,
        )
        self.db.add(event)
        await self.db.flush()

        return contact.tracking_hash

    async def track_batch(
        self,
        tenant_id: str,
        events: list[TrackEventRequest],
        *,
        source_site: str | None = None,
    ) -> tuple[int, int]:
        """Track multiple events. Returns (processed, errors)."""
        processed = 0
        errors = 0
        for event_data in events:
            try:
                result = await self.track_event(
                    tenant_id, event_data, source_site=source_site
                )
                if result:
                    processed += 1
            except Exception as e:
                logger.warning("Batch event error: {err}", err=str(e))
                errors += 1
        await self.db.flush()
        return processed, errors

    async def get_timeline(
        self, tenant_id: str, contact_id: int, limit: int = 100
    ) -> list[JourneyEvent]:
        """Get journey timeline for a contact."""
        result = await self.db.execute(
            select(JourneyEvent)
            .where(
                JourneyEvent.tenant_id == tenant_id,
                JourneyEvent.contact_id == contact_id,
            )
            .order_by(JourneyEvent.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_recent_events(
        self,
        tenant_id: str,
        limit: int = 50,
        offset: int = 0,
        *,
        source_site: str | None = None,
    ) -> list[JourneyEvent]:
        """Get recent events across all contacts (feed), optional source filter."""
        stmt = (
            select(JourneyEvent)
            .options(selectinload(JourneyEvent.contact))
            .where(JourneyEvent.tenant_id == tenant_id)
        )
        if source_site:
            stmt = stmt.where(JourneyEvent.source_site == source_site)
        stmt = stmt.order_by(JourneyEvent.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_leads_with_recent_events(
        self,
        tenant_id: str,
        limit: int = 50,
        offset: int = 0,
        *,
        events_per_lead: int = 10,
        source_site: str | None = None,
        category: str | None = None,
        journey_status: str | None = None,
        search: str | None = None,
    ) -> list[dict]:
        """Return leads grouped by contact, ordered by their most recent event.

        Each entry contains the contact, the N most recent events for that
        contact, and aggregated stats. Events are filtered by the same
        criteria used to filter leads, so the inline events match the filter.
        """
        # Step 1: Aggregate per contact, ordered by last event timestamp
        last_event_at = func.max(JourneyEvent.created_at)
        agg_q = (
            select(
                JourneyEvent.contact_id,
                last_event_at.label("last_event_at"),
                func.count(JourneyEvent.id).label("event_count"),
            )
            .where(
                JourneyEvent.tenant_id == tenant_id,
                JourneyEvent.contact_id.isnot(None),
            )
        )
        if source_site:
            agg_q = agg_q.where(JourneyEvent.source_site == source_site)
        if category:
            agg_q = agg_q.where(JourneyEvent.category == category)
        if search or journey_status:
            agg_q = agg_q.join(Contact, Contact.id == JourneyEvent.contact_id)
            if search:
                term = f"%{search}%"
                agg_q = agg_q.where(
                    or_(Contact.name.ilike(term), Contact.email.ilike(term))
                )
            if journey_status:
                agg_q = agg_q.where(Contact.journey_status == journey_status)

        agg_q = (
            agg_q.group_by(JourneyEvent.contact_id)
            .order_by(last_event_at.desc())
            .offset(offset)
            .limit(limit)
        )
        rows = (await self.db.execute(agg_q)).all()
        if not rows:
            return []

        contact_ids = [r[0] for r in rows]
        meta_map = {r[0]: (r[1], r[2]) for r in rows}

        # Step 2: Fetch contacts in one query
        contacts_result = await self.db.execute(
            select(Contact).where(Contact.id.in_(contact_ids))
        )
        contacts_map = {c.id: c for c in contacts_result.scalars().all()}

        # Step 3: Fetch top-N events per contact (one query per contact)
        events_by_contact: dict[int, list[JourneyEvent]] = {}
        for cid in contact_ids:
            ev_q = (
                select(JourneyEvent)
                .where(
                    JourneyEvent.tenant_id == tenant_id,
                    JourneyEvent.contact_id == cid,
                )
            )
            if source_site:
                ev_q = ev_q.where(JourneyEvent.source_site == source_site)
            if category:
                ev_q = ev_q.where(JourneyEvent.category == category)
            ev_q = ev_q.order_by(JourneyEvent.created_at.desc()).limit(
                events_per_lead
            )
            ev_result = await self.db.execute(ev_q)
            events_by_contact[cid] = list(ev_result.scalars().all())

        # Step 4: Assemble result preserving sort order
        result = []
        for cid in contact_ids:
            contact = contacts_map.get(cid)
            if not contact:
                continue
            last_at, event_count = meta_map[cid]
            events = events_by_contact.get(cid, [])
            last_event_name = events[0].event if events else None
            result.append(
                {
                    "contact": contact,
                    "events": events,
                    "event_count": event_count,
                    "last_event_at": last_at,
                    "last_event": last_event_name,
                }
            )
        return result

    async def get_distinct_sources(self, tenant_id: str) -> list[str]:
        """Return distinct source_site values for this tenant, sorted."""
        result = await self.db.execute(
            select(JourneyEvent.source_site)
            .where(JourneyEvent.tenant_id == tenant_id)
            .distinct()
        )
        return sorted(v for v in result.scalars().all() if v)

    async def compute_days_since_last(
        self, tenant_id: str, events: list[JourneyEvent],
    ) -> dict[int, int | None]:
        """For each event, compute days since the previous event of the same contact.

        Returns dict mapping event.id -> days (int) or None if no previous event
        or gap <= 1 day.
        """
        if not events:
            return {}

        # Build lookup: for each event, find the previous event of same contact
        # Group events by contact_id to batch queries
        contact_event_map: dict[int, list[JourneyEvent]] = {}
        for ev in events:
            if ev.contact_id is not None:
                contact_event_map.setdefault(ev.contact_id, []).append(ev)

        if not contact_event_map:
            return {}

        result_map: dict[int, int | None] = {}

        for contact_id, contact_events in contact_event_map.items():
            for ev in contact_events:
                # Find the most recent event BEFORE this one for the same contact
                prev_alias = select(
                    func.max(JourneyEvent.created_at)
                ).where(
                    JourneyEvent.tenant_id == tenant_id,
                    JourneyEvent.contact_id == contact_id,
                    JourneyEvent.created_at < ev.created_at,
                ).scalar_subquery()

                prev_result = await self.db.execute(
                    select(prev_alias)
                )
                prev_ts = prev_result.scalar()

                if prev_ts is not None:
                    gap = (ev.created_at - prev_ts).days
                    if gap > 1:
                        result_map[ev.id] = gap

        return result_map

    @staticmethod
    def _categorize_event(event: str) -> str:
        """Auto-categorize event based on name.

        Uses prefix matching for granular events like ems_step_*, ems_tab_*,
        konfigurator_*, etc. so new Umami events are auto-categorized.
        """
        awareness = {"page_visit", "ref_link_click"}
        engagement = {
            "konfigurator_start",
            "konfigurator_step",
            "ems_simulation",
            "ems_simulation_complete",
            "spot_simulation",
            "chat_started",
            "quote_viewed",
        }
        conversion = {
            "konfigurator_complete",
            "quote_pdf_download",
            "ems_pdf_download",
            "contact_form",
            "identify",
        }
        retention = {"return_visit", "config_link_visit"}

        # Prefix-based categorization for granular events
        engagement_prefixes = (
            "ems_step_", "ems_tab_", "ems_save_",
            "konfigurator_mode_", "konfigurator_",
            "spot_", "chat_",
        )
        conversion_prefixes = (
            "ems_lead_", "ems_pdf_",
        )

        if event in awareness:
            return "awareness"
        if event in engagement:
            return "engagement"
        if event in conversion:
            return "conversion"
        if event in retention:
            return "retention"

        # Prefix matching for granular events
        for prefix in conversion_prefixes:
            if event.startswith(prefix):
                return "conversion"
        for prefix in engagement_prefixes:
            if event.startswith(prefix):
                return "engagement"

        return "engagement"


class RefCodeService:
    """Handle ref-code CRUD."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self, tenant_id: str, data: RefCodeCreate
    ) -> JourneyRefCode:
        """Create a ref-code."""
        code = data.ref_code or _generate_ref_code()

        ref = JourneyRefCode(
            tenant_id=tenant_id,
            ref_code=code,
            contact_id=data.contact_id,
            campaign_id=data.campaign_id,
            name=data.name,
            context=data.context,
            target_url=data.target_url,
            utm_source=data.utm_source,
            utm_medium=data.utm_medium,
            utm_campaign=data.utm_campaign,
            notify_on_visit=data.notify_on_visit,
            notify_channel=data.notify_channel,
            notify_target=data.notify_target,
        )
        self.db.add(ref)
        await self.db.flush()
        await self.db.refresh(ref)
        logger.info("RefCode erstellt: {code}", code=code)
        return ref

    async def bulk_create(
        self, tenant_id: str, data: BulkRefCodeCreate
    ) -> list[JourneyRefCode]:
        """Bulk import ref-codes from Name;Context lines."""
        refs = []
        for line in data.lines.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = line.split(";", 1)
            name = parts[0].strip()
            context = parts[1].strip() if len(parts) > 1 else None

            ref = JourneyRefCode(
                tenant_id=tenant_id,
                ref_code=_generate_ref_code(),
                name=name,
                context=context,
                campaign_id=data.campaign_id,
                target_url=data.target_url,
            )
            self.db.add(ref)
            refs.append(ref)

        await self.db.flush()
        for r in refs:
            await self.db.refresh(r)
        logger.info("RefCodes bulk erstellt: {count}", count=len(refs))
        return refs

    async def bulk_generate(
        self, tenant_id: str, count: int, campaign_id: int | None = None,
        target_url: str | None = None, prefix: str | None = None,
        utm_source: str | None = None, utm_medium: str | None = None,
        utm_campaign: str | None = None,
    ) -> list[JourneyRefCode]:
        """Generate N ref-codes without contacts."""
        refs = []
        for _ in range(count):
            code = _generate_ref_code()
            if prefix:
                code = f"{prefix}{code}"
            ref = JourneyRefCode(
                tenant_id=tenant_id,
                ref_code=code,
                campaign_id=campaign_id,
                target_url=target_url,
                utm_source=utm_source,
                utm_medium=utm_medium,
                utm_campaign=utm_campaign,
            )
            self.db.add(ref)
            refs.append(ref)

        await self.db.flush()
        for r in refs:
            await self.db.refresh(r)
        logger.info("RefCodes generiert: {count}", count=count)
        return refs

    async def get_by_id(
        self, tenant_id: str, ref_id: int
    ) -> JourneyRefCode:
        """Get ref-code by ID."""
        result = await self.db.execute(
            select(JourneyRefCode).where(
                JourneyRefCode.id == ref_id,
                JourneyRefCode.tenant_id == tenant_id,
            )
        )
        ref = result.scalar_one_or_none()
        if not ref:
            raise NotFoundError("RefCode", ref_id)
        return ref

    async def resolve(
        self, tenant_id: str, ref_code: str
    ) -> JourneyRefCode | None:
        """Resolve a ref-code string to its record.

        - If contact exists but has no tracking_hash → generate one.
        - If no contact linked → auto-create a placeholder contact
          so the journey starts immediately. When the visitor later
          identifies (form submit), the placeholder is merged via email match.
        """
        result = await self.db.execute(
            select(JourneyRefCode)
            .options(selectinload(JourneyRefCode.contact))
            .where(
                JourneyRefCode.tenant_id == tenant_id,
                JourneyRefCode.ref_code == ref_code,
            )
        )
        ref = result.scalar_one_or_none()
        if not ref:
            return None

        # Case 1: Contact exists but no tracking_hash
        if ref.contact and not ref.contact.tracking_hash:
            ref.contact.tracking_hash = _generate_hash()
            ref.contact.journey_status = ref.contact.journey_status or "new"
            await self.db.flush()
            logger.info(
                "Auto-generated tracking_hash for contact {id}",
                id=ref.contact.id,
            )

        # Case 2: No contact linked → create placeholder
        if not ref.contact:
            placeholder = Contact(
                tenant_id=tenant_id,
                email=f"ref-{ref_code}@journey.placeholder",
                name=ref.name or f"Ref {ref_code}",
                source="ref_link",
                tracking_hash=_generate_hash(),
                journey_status="new",
                tags=[],
                custom_fields={},
            )
            self.db.add(placeholder)
            await self.db.flush()
            ref.contact_id = placeholder.id
            await self.db.flush()
            await self.db.refresh(ref, ["contact"])
            logger.info(
                "Auto-created placeholder contact for ref {code} → contact {id}",
                code=ref_code,
                id=placeholder.id,
            )

        return ref

    async def ensure_ref_code(
        self,
        tenant_id: str,
        contact: Contact,
        campaign: JourneyCampaign,
        *,
        target_url: str | None = None,
        utm_source: str | None = None,
        utm_medium: str | None = None,
        utm_campaign: str | None = None,
        name: str | None = None,
    ) -> JourneyRefCode:
        """Idempotenter Lookup-or-Create für (Contact, Campaign).

        Wird vom Render-Pfad aufgerufen, damit jeder Send einen Ref-Code
        kriegt — egal ob vorab per Bulk-Run erzeugt oder erst zur Send-
        Zeit. Der UNIQUE-Index auf (contact_id, campaign_id) verhindert
        Duplikate; bei Race-Condition kommt IntegrityError → Retry mit
        SELECT.
        """
        result = await self.db.execute(
            select(JourneyRefCode)
            .where(
                JourneyRefCode.tenant_id == tenant_id,
                JourneyRefCode.contact_id == contact.id,
                JourneyRefCode.campaign_id == campaign.id,
            )
            .limit(1)
        )
        if ref := result.scalar_one_or_none():
            return ref

        ref = JourneyRefCode(
            tenant_id=tenant_id,
            ref_code=_generate_ref_code(),
            contact_id=contact.id,
            campaign_id=campaign.id,
            name=name or contact.name,
            target_url=target_url,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
        )
        self.db.add(ref)
        try:
            await self.db.flush()
        except IntegrityError:
            await self.db.rollback()
            # Anderer Worker war schneller — den existierenden Code holen.
            result = await self.db.execute(
                select(JourneyRefCode).where(
                    JourneyRefCode.tenant_id == tenant_id,
                    JourneyRefCode.contact_id == contact.id,
                    JourneyRefCode.campaign_id == campaign.id,
                )
            )
            ref = result.scalar_one()
            return ref
        logger.info(
            "RefCode auto-erstellt für contact={cid} campaign={camp}: {code}",
            cid=contact.id,
            camp=campaign.id,
            code=ref.ref_code,
        )
        return ref

    async def list_refs(
        self,
        tenant_id: str,
        campaign_id: int | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[JourneyRefCode], int]:
        """List ref-codes with optional filters."""
        query = select(JourneyRefCode).where(
            JourneyRefCode.tenant_id == tenant_id
        )

        if campaign_id:
            query = query.where(JourneyRefCode.campaign_id == campaign_id)
        if search:
            term = f"%{search}%"
            query = query.where(
                or_(
                    JourneyRefCode.name.ilike(term),
                    JourneyRefCode.ref_code.ilike(term),
                    JourneyRefCode.context.ilike(term),
                )
            )

        count_q = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0

        query = query.order_by(JourneyRefCode.created_at.desc())
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def update(
        self, tenant_id: str, ref_id: int, data: RefCodeUpdate
    ) -> JourneyRefCode:
        """Update a ref-code."""
        ref = await self.get_by_id(tenant_id, ref_id)
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(ref, key, value)
        await self.db.flush()
        await self.db.refresh(ref)
        return ref

    async def delete(self, tenant_id: str, ref_id: int) -> None:
        """Delete a ref-code."""
        ref = await self.get_by_id(tenant_id, ref_id)
        await self.db.delete(ref)
        await self.db.flush()
        logger.info("RefCode gelöscht: {id}", id=ref_id)


class CampaignService:
    """Handle campaign CRUD."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def ensure_for_pipeline(self, pipeline) -> JourneyCampaign:
        """Liefert (oder erstellt) die Customer-Journey-Kampagne, die zur
        Engagement-Pipeline gehört. Speichert die Verknüpfung idempotent
        in ``pipeline.journey_campaign_id``.

        Wird vom Render-Pfad bei jedem Send aufgerufen — beim ersten Mal
        wird die Campaign angelegt und die ID auf der Pipeline gecached,
        danach 1 SELECT pro Mail.
        """
        # Cache-Hit: Pipeline kennt schon ihre Campaign-ID
        if pipeline.journey_campaign_id is not None:
            return await self.get_by_id(
                pipeline.tenant_id, pipeline.journey_campaign_id
            )

        # Cold path: Name-Match auf bestehende Kampagne, sonst neu anlegen
        channel = (pipeline.channels[0] if pipeline.channels else None) or "email"
        campaign, _ = await self.get_or_create_by_name(
            pipeline.tenant_id, pipeline.name, channel=channel
        )
        pipeline.journey_campaign_id = campaign.id
        await self.db.flush()
        return campaign

    async def get_or_create_by_name(
        self, tenant_id: str, name: str, channel: str | None = None
    ) -> tuple[JourneyCampaign, bool]:
        """Find campaign by name or create it. Returns (campaign, is_new)."""
        result = await self.db.execute(
            select(JourneyCampaign).where(
                JourneyCampaign.tenant_id == tenant_id,
                JourneyCampaign.name == name,
            )
        )
        campaign = result.scalar_one_or_none()
        if campaign:
            return campaign, False

        campaign = JourneyCampaign(
            tenant_id=tenant_id,
            name=name,
            channel=channel,
        )
        self.db.add(campaign)
        await self.db.flush()
        await self.db.refresh(campaign)
        logger.info("Kampagne auto-erstellt: {name}", name=name)
        return campaign, True

    async def create(
        self, tenant_id: str, data: CampaignCreate
    ) -> JourneyCampaign:
        """Create a campaign."""
        campaign = JourneyCampaign(
            tenant_id=tenant_id,
            name=data.name,
            channel=data.channel,
            description=data.description,
        )
        self.db.add(campaign)
        await self.db.flush()
        await self.db.refresh(campaign)
        logger.info("Kampagne erstellt: {name}", name=data.name)
        return campaign

    async def get_by_id(
        self, tenant_id: str, campaign_id: int
    ) -> JourneyCampaign:
        """Get campaign by ID."""
        result = await self.db.execute(
            select(JourneyCampaign).where(
                JourneyCampaign.id == campaign_id,
                JourneyCampaign.tenant_id == tenant_id,
            )
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise NotFoundError("Campaign", campaign_id)
        return campaign

    async def list_campaigns(
        self,
        tenant_id: str,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[JourneyCampaign], int]:
        """List campaigns."""
        query = select(JourneyCampaign).where(
            JourneyCampaign.tenant_id == tenant_id
        )
        if status:
            query = query.where(JourneyCampaign.status == status)

        count_q = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0

        query = query.order_by(JourneyCampaign.created_at.desc())
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def update(
        self, tenant_id: str, campaign_id: int, data: CampaignUpdate
    ) -> JourneyCampaign:
        """Update a campaign."""
        campaign = await self.get_by_id(tenant_id, campaign_id)
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(campaign, key, value)
        await self.db.flush()
        await self.db.refresh(campaign)
        return campaign

    async def delete(self, tenant_id: str, campaign_id: int) -> None:
        """Delete a campaign."""
        campaign = await self.get_by_id(tenant_id, campaign_id)
        await self.db.delete(campaign)
        await self.db.flush()
        logger.info("Kampagne gelöscht: {id}", id=campaign_id)


class PrepareLinkService:
    """One-call service: identify + campaign + ref-code + link."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def prepare(
        self,
        tenant_id: str,
        data: "PrepareLinkRequest",
        *,
        source_site: str | None = None,
    ) -> dict:
        """Identify contact, resolve campaign, create ref-code, return link."""

        # 1. Identify or create contact
        identify_svc = IdentifyService(self.db)
        identify_data = IdentifyRequest(
            name=data.name,
            email=data.email,
            phone=data.phone,
            company=data.company,
            source=data.source,
        )
        contact, is_new_contact, _ = await identify_svc.identify(
            tenant_id, identify_data, skip_event=True, source_site=source_site,
        )

        # 2. Resolve campaign (optional)
        campaign_id = None
        if data.campaign_name:
            campaign_svc = CampaignService(self.db)
            campaign, _ = await campaign_svc.get_or_create_by_name(
                tenant_id, data.campaign_name, data.campaign_channel
            )
            campaign_id = campaign.id

        # 3. Find existing ref-code for this (contact, campaign) tuple, or create one.
        #    Mirrors the partial-unique index uq_journey_ref_per_contact_campaign
        #    (Migration 085) — repeating prepare-link for the same recipient+campaign
        #    must be idempotent, otherwise the second INSERT hits UniqueViolation.
        is_new_ref = False
        ref_filter = [
            JourneyRefCode.tenant_id == tenant_id,
            JourneyRefCode.contact_id == contact.id,
        ]
        if campaign_id is None:
            ref_filter.append(JourneyRefCode.campaign_id.is_(None))
        else:
            ref_filter.append(JourneyRefCode.campaign_id == campaign_id)
        existing_ref = await self.db.execute(
            select(JourneyRefCode)
            .where(*ref_filter)
            .order_by(JourneyRefCode.created_at.desc())
            .limit(1)
        )
        ref = existing_ref.scalar_one_or_none()

        if not ref:
            ref_svc = RefCodeService(self.db)
            ref_data = RefCodeCreate(
                name=data.name,
                contact_id=contact.id,
                campaign_id=campaign_id,
                target_url=data.target_url,
                utm_source=data.utm_source,
                utm_medium=data.utm_medium,
                utm_campaign=data.utm_campaign,
            )
            ref = await ref_svc.create(tenant_id, ref_data)
            is_new_ref = True

        # 4. Build link with ref (no UTM in URL — kept short)
        base_url = data.target_url or "https://go4.energy"
        separator = "&" if "?" in base_url else "?"
        link = f"{base_url}{separator}ref={ref.ref_code}"

        return {
            "ok": True,
            "tracking_hash": contact.tracking_hash,
            "ref_code": ref.ref_code,
            "link": link,
            "contact_id": contact.id,
            "is_new_contact": is_new_contact,
            "is_new_ref": is_new_ref,
        }


class DashboardService:
    """Dashboard stats and feed."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_stats(self, tenant_id: str) -> dict:
        """Get dashboard overview stats."""
        now = datetime.utcnow()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = now - timedelta(days=7)

        # Leads with tracking_hash = journey leads
        leads_total = (
            await self.db.execute(
                select(func.count(Contact.id)).where(
                    Contact.tenant_id == tenant_id,
                    Contact.tracking_hash.isnot(None),
                )
            )
        ).scalar() or 0

        leads_today = (
            await self.db.execute(
                select(func.count(Contact.id)).where(
                    Contact.tenant_id == tenant_id,
                    Contact.tracking_hash.isnot(None),
                    Contact.created_at >= today,
                )
            )
        ).scalar() or 0

        leads_week = (
            await self.db.execute(
                select(func.count(Contact.id)).where(
                    Contact.tenant_id == tenant_id,
                    Contact.tracking_hash.isnot(None),
                    Contact.created_at >= week_ago,
                )
            )
        ).scalar() or 0

        events_today = (
            await self.db.execute(
                select(func.count(JourneyEvent.id)).where(
                    JourneyEvent.tenant_id == tenant_id,
                    JourneyEvent.created_at >= today,
                )
            )
        ).scalar() or 0

        events_week = (
            await self.db.execute(
                select(func.count(JourneyEvent.id)).where(
                    JourneyEvent.tenant_id == tenant_id,
                    JourneyEvent.created_at >= week_ago,
                )
            )
        ).scalar() or 0

        conversions_week = (
            await self.db.execute(
                select(func.count(JourneyEvent.id)).where(
                    JourneyEvent.tenant_id == tenant_id,
                    JourneyEvent.category == "conversion",
                    JourneyEvent.created_at >= week_ago,
                )
            )
        ).scalar() or 0

        ref_codes_total = (
            await self.db.execute(
                select(func.count(JourneyRefCode.id)).where(
                    JourneyRefCode.tenant_id == tenant_id,
                )
            )
        ).scalar() or 0

        campaigns_active = (
            await self.db.execute(
                select(func.count(JourneyCampaign.id)).where(
                    JourneyCampaign.tenant_id == tenant_id,
                    JourneyCampaign.status == "active",
                )
            )
        ).scalar() or 0

        return {
            "leads_total": leads_total,
            "leads_new_today": leads_today,
            "leads_new_week": leads_week,
            "events_today": events_today,
            "events_week": events_week,
            "conversions_week": conversions_week,
            "ref_codes_total": ref_codes_total,
            "campaigns_active": campaigns_active,
        }
