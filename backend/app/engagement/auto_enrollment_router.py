"""AutoEnrollmentRouter — generic tag/property-based pipeline matching.

Wird vom IdentifyService bei jedem ``/tracking/identify`` aufgerufen.
Lädt alle aktiven Pipelines mit ``auto_enroll_filter IS NOT NULL``,
matcht den Filter gegen ``contact.tags + contact.custom_fields`` und
erstellt für jede passende Pipeline einen ``PipelineEnrollment``
(idempotent — bestehende Enrollments werden nicht dupliziert).

Filter-Schema (``engagement_pipelines.auto_enroll_filter`` JSONB)::

    {
      "tags_any":   ["fachpartner", "elektriker"],   // OR-Match: mind. 1
      "tags_all":   ["leadgen"],                      // AND-Match: alle
      "tags_none":  ["unqualified"],                  // NOT-Match: keiner
      "custom_fields": { "region": "Bayern" }         // exact-Match
    }

Alle Felder optional. Leere Listen / fehlende Keys werden ignoriert.

Multi-Match: Lead landet in *allen* matchenden Pipelines parallel —
das Datenmodell von Pipelines erlaubt dies, da sich Sequenzen pro
Pipeline unterscheiden und Brain die Touch-Cadence pro Pipeline
verwaltet.
"""

from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contacts.models import Contact
from app.engagement.models import EngagementPipeline, PipelineEnrollment


class AutoEnrollmentRouter:
    """Match contact tags+fields against pipeline filters and enroll."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def match_and_enroll(
        self,
        contact: Contact,
        source_context: dict[str, Any] | None = None,
    ) -> list[PipelineEnrollment]:
        """Enroll contact in every active pipeline whose filter matches.

        Idempotent — skips pipelines where contact is already enrolled
        (any status, including stopped/completed) to avoid re-spamming.
        """
        pipelines = await self._load_pipelines_with_filter(contact.tenant_id)
        if not pipelines:
            return []

        enrollments: list[PipelineEnrollment] = []
        for pipeline in pipelines:
            if not self._filter_matches(pipeline.auto_enroll_filter, contact):
                continue
            if await self._already_enrolled(contact.id, pipeline.id):
                continue

            enrollment = PipelineEnrollment(
                tenant_id=contact.tenant_id,
                contact_id=contact.id,
                pipeline_id=pipeline.id,
                stage="engaged",
                status="active",
                source_module="auto_enrollment",
                source_context=source_context or {},
            )
            self.db.add(enrollment)
            enrollments.append(enrollment)
            logger.info(
                "Auto-enrolled contact {cid} in pipeline {pid} ({pname})",
                cid=contact.id,
                pid=pipeline.id,
                pname=pipeline.name,
            )

        if enrollments:
            await self.db.flush()
        return enrollments

    async def _load_pipelines_with_filter(
        self, tenant_id: str
    ) -> list[EngagementPipeline]:
        result = await self.db.execute(
            select(EngagementPipeline).where(
                EngagementPipeline.tenant_id == tenant_id,
                EngagementPipeline.is_active.is_(True),
                EngagementPipeline.auto_enroll_filter.isnot(None),
            )
        )
        return list(result.scalars().all())

    async def _already_enrolled(self, contact_id: int, pipeline_id: int) -> bool:
        result = await self.db.execute(
            select(PipelineEnrollment.id).where(
                PipelineEnrollment.contact_id == contact_id,
                PipelineEnrollment.pipeline_id == pipeline_id,
            )
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    def _filter_matches(filter_spec: dict | None, contact: Contact) -> bool:
        """Pure function — evaluate filter against contact tags+fields."""
        if not filter_spec:
            return False

        contact_tags: set[str] = set(contact.tags or [])
        contact_fields: dict = contact.custom_fields or {}

        tags_any = filter_spec.get("tags_any") or []
        if tags_any and not (contact_tags & set(tags_any)):
            return False

        tags_all = filter_spec.get("tags_all") or []
        if tags_all and not set(tags_all).issubset(contact_tags):
            return False

        tags_none = filter_spec.get("tags_none") or []
        if tags_none and (contact_tags & set(tags_none)):
            return False

        for key, val in (filter_spec.get("custom_fields") or {}).items():
            if contact_fields.get(key) != val:
                return False

        # If no constraints at all, treat as non-match (manuell only)
        return bool(
            tags_any
            or tags_all
            or tags_none
            or filter_spec.get("custom_fields")
        )
