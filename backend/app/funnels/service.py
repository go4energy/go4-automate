"""Funnels service - CRUD and business logic for funnels, prospects, companies."""

from datetime import datetime

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import NotFoundError, ValidationError
from app.funnels.dedup import (
    DeduplicationService,
    compute_company_dedup_key,
    compute_dedup_keys,
)
from app.funnels.models import (
    Funnel,
    FunnelActivity,
    FunnelCompany,
    FunnelProspect,
    FunnelStage,
)
from app.funnels.schemas import (
    FunnelActivityCreate,
    FunnelCompanyCreate,
    FunnelCompanyUpdate,
    FunnelCreate,
    FunnelProspectCreate,
    FunnelProspectUpdate,
    FunnelStageCreate,
    FunnelStageUpdate,
    FunnelUpdate,
    ProspectMoveRequest,
)

# Default funnel stages
DEFAULT_STAGES = [
    {"name": "Imported", "position": 0, "color": "#6B7280"},
    {"name": "Verified", "position": 1, "color": "#3B82F6"},
    {"name": "Enriched", "position": 2, "color": "#8B5CF6"},
    {"name": "Contacted", "position": 3, "color": "#F59E0B"},
    {"name": "Engaged", "position": 4, "color": "#10B981"},
    {"name": "Qualified", "position": 5, "color": "#059669", "is_handoff": True},
    {"name": "Disqualified", "position": 6, "color": "#EF4444", "is_disqualified": True},
]


class FunnelService:
    """Service for funnel management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self, tenant_id: str, data: FunnelCreate, owner_id: int | None = None
    ) -> Funnel:
        """Create a new funnel with optional stages."""
        funnel = Funnel(
            tenant_id=tenant_id,
            owner_id=owner_id,
            name=data.name,
            description=data.description,
            status=data.status,
            color=data.color,
            tags=data.tags,
            target_criteria=data.target_criteria,
            handoff_pipeline_id=data.handoff_pipeline_id,
            handoff_stage_id=data.handoff_stage_id,
            external_crm_config=data.external_crm_config,
        )
        self.db.add(funnel)
        await self.db.flush()

        # Create stages (use provided or defaults)
        stages_data = data.stages if data.stages else DEFAULT_STAGES
        for i, stage_data in enumerate(stages_data):
            if isinstance(stage_data, FunnelStageCreate):
                stage = FunnelStage(
                    tenant_id=tenant_id,
                    funnel_id=funnel.id,
                    name=stage_data.name,
                    position=stage_data.position,
                    color=stage_data.color,
                    is_handoff=stage_data.is_handoff,
                    is_disqualified=stage_data.is_disqualified,
                    auto_actions=stage_data.auto_actions,
                )
            else:
                # Dict from DEFAULT_STAGES
                stage = FunnelStage(
                    tenant_id=tenant_id,
                    funnel_id=funnel.id,
                    name=stage_data["name"],
                    position=stage_data.get("position", i),
                    color=stage_data.get("color", "#6B7280"),
                    is_handoff=stage_data.get("is_handoff", False),
                    is_disqualified=stage_data.get("is_disqualified", False),
                )
            self.db.add(stage)

        await self.db.flush()
        await self.db.refresh(funnel)
        logger.info("Funnel erstellt: {name}", name=data.name)
        return funnel

    async def get_by_id(self, tenant_id: str, funnel_id: int) -> Funnel:
        """Get a funnel by ID with stages."""
        result = await self.db.execute(
            select(Funnel)
            .options(selectinload(Funnel.stages))
            .where(Funnel.id == funnel_id, Funnel.tenant_id == tenant_id)
        )
        funnel = result.scalar_one_or_none()
        if not funnel:
            raise NotFoundError("Funnel", funnel_id)
        return funnel

    async def list_funnels(
        self, tenant_id: str, status: str | None = None
    ) -> list[Funnel]:
        """List all funnels for a tenant."""
        query = (
            select(Funnel)
            .options(selectinload(Funnel.stages))
            .where(Funnel.tenant_id == tenant_id)
        )

        if status:
            query = query.where(Funnel.status == status)

        query = query.order_by(Funnel.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update(
        self, tenant_id: str, funnel_id: int, data: FunnelUpdate
    ) -> Funnel:
        """Update a funnel."""
        funnel = await self.get_by_id(tenant_id, funnel_id)

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(funnel, key, value)

        await self.db.flush()
        await self.db.refresh(funnel)
        logger.info("Funnel aktualisiert: {id}", id=funnel_id)
        return funnel

    async def delete(self, tenant_id: str, funnel_id: int) -> None:
        """Delete a funnel."""
        funnel = await self.get_by_id(tenant_id, funnel_id)
        await self.db.delete(funnel)
        await self.db.flush()
        logger.info("Funnel gelöscht: {id}", id=funnel_id)

    async def get_stats(self, tenant_id: str, funnel_id: int) -> dict:
        """Get funnel statistics."""
        # Prospect count
        prospect_result = await self.db.execute(
            select(func.count(FunnelProspect.id)).where(
                FunnelProspect.funnel_id == funnel_id,
                FunnelProspect.tenant_id == tenant_id,
            )
        )
        prospect_count = prospect_result.scalar() or 0

        # Company count
        company_result = await self.db.execute(
            select(func.count(FunnelCompany.id)).where(
                FunnelCompany.funnel_id == funnel_id,
                FunnelCompany.tenant_id == tenant_id,
            )
        )
        company_count = company_result.scalar() or 0

        # Stage counts
        stage_result = await self.db.execute(
            select(
                FunnelStage.id,
                FunnelStage.name,
                func.count(FunnelProspect.id).label("count"),
            )
            .outerjoin(FunnelProspect, FunnelProspect.stage_id == FunnelStage.id)
            .where(FunnelStage.funnel_id == funnel_id)
            .group_by(FunnelStage.id, FunnelStage.name)
            .order_by(FunnelStage.position)
        )
        stages = [
            {"id": r.id, "name": r.name, "count": r.count} for r in stage_result.all()
        ]

        return {
            "prospect_count": prospect_count,
            "company_count": company_count,
            "stages": stages,
        }

    # Stage management
    async def add_stage(
        self, tenant_id: str, funnel_id: int, data: FunnelStageCreate
    ) -> FunnelStage:
        """Add a stage to a funnel."""
        await self.get_by_id(tenant_id, funnel_id)

        stage = FunnelStage(
            tenant_id=tenant_id,
            funnel_id=funnel_id,
            name=data.name,
            position=data.position,
            color=data.color,
            is_handoff=data.is_handoff,
            is_disqualified=data.is_disqualified,
            auto_actions=data.auto_actions,
        )
        self.db.add(stage)
        await self.db.flush()
        await self.db.refresh(stage)
        logger.info("Stage hinzugefügt: {name}", name=data.name)
        return stage

    async def update_stage(
        self, tenant_id: str, stage_id: int, data: FunnelStageUpdate
    ) -> FunnelStage:
        """Update a funnel stage."""
        result = await self.db.execute(
            select(FunnelStage).where(
                FunnelStage.id == stage_id, FunnelStage.tenant_id == tenant_id
            )
        )
        stage = result.scalar_one_or_none()
        if not stage:
            raise NotFoundError("Stage", stage_id)

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(stage, key, value)

        await self.db.flush()
        await self.db.refresh(stage)
        logger.info("Stage aktualisiert: {id}", id=stage_id)
        return stage

    async def delete_stage(self, tenant_id: str, stage_id: int) -> None:
        """Delete a funnel stage."""
        result = await self.db.execute(
            select(FunnelStage).where(
                FunnelStage.id == stage_id, FunnelStage.tenant_id == tenant_id
            )
        )
        stage = result.scalar_one_or_none()
        if not stage:
            raise NotFoundError("Stage", stage_id)

        # Check if there are prospects in this stage
        prospect_count = await self.db.execute(
            select(func.count(FunnelProspect.id)).where(
                FunnelProspect.stage_id == stage_id
            )
        )
        if prospect_count.scalar() > 0:
            raise ValidationError(
                "Stage kann nicht gelöscht werden, da noch Prospects vorhanden sind"
            )

        await self.db.delete(stage)
        await self.db.flush()
        logger.info("Stage gelöscht: {id}", id=stage_id)

    async def reorder_stages(
        self, tenant_id: str, funnel_id: int, stage_ids: list[int]
    ) -> list[FunnelStage]:
        """Reorder stages in a funnel."""
        await self.get_by_id(tenant_id, funnel_id)

        # Fetch all stages
        result = await self.db.execute(
            select(FunnelStage).where(
                FunnelStage.funnel_id == funnel_id, FunnelStage.tenant_id == tenant_id
            )
        )
        stages = {s.id: s for s in result.scalars().all()}

        # Update positions
        for position, stage_id in enumerate(stage_ids):
            if stage_id in stages:
                stages[stage_id].position = position

        await self.db.flush()
        logger.info("Stages neu sortiert für Funnel {id}", id=funnel_id)
        return list(stages.values())


class CompanyService:
    """Service for funnel company management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self, tenant_id: str, funnel_id: int, data: FunnelCompanyCreate
    ) -> FunnelCompany:
        """Create a new company in a funnel."""
        # Compute dedup key
        dedup_key = compute_company_dedup_key(data.domain)

        company = FunnelCompany(
            tenant_id=tenant_id,
            funnel_id=funnel_id,
            name=data.name,
            domain=data.domain,
            website=data.website,
            industry=data.industry,
            size=data.size,
            address=data.address,
            phone=data.phone,
            email=data.email,
            source=data.source,
            source_id=data.source_id,
            dedup_key=dedup_key,
            tags=data.tags,
            custom_fields=data.custom_fields,
        )
        self.db.add(company)
        await self.db.flush()
        await self.db.refresh(company)
        logger.info("Funnel Company erstellt: {name}", name=data.name)
        return company

    async def get_by_id(self, tenant_id: str, company_id: int) -> FunnelCompany:
        """Get a company by ID."""
        result = await self.db.execute(
            select(FunnelCompany)
            .options(selectinload(FunnelCompany.prospects))
            .where(FunnelCompany.id == company_id, FunnelCompany.tenant_id == tenant_id)
        )
        company = result.scalar_one_or_none()
        if not company:
            raise NotFoundError("FunnelCompany", company_id)
        return company

    async def list_companies(
        self,
        tenant_id: str,
        funnel_id: int,
        verified: bool | None = None,
        industry: str | None = None,
    ) -> list[FunnelCompany]:
        """List companies in a funnel."""
        query = select(FunnelCompany).where(
            FunnelCompany.tenant_id == tenant_id, FunnelCompany.funnel_id == funnel_id
        )

        if verified is not None:
            query = query.where(FunnelCompany.verified == verified)
        if industry:
            query = query.where(FunnelCompany.industry == industry)

        query = query.order_by(FunnelCompany.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update(
        self, tenant_id: str, company_id: int, data: FunnelCompanyUpdate
    ) -> FunnelCompany:
        """Update a funnel company."""
        company = await self.get_by_id(tenant_id, company_id)

        update_data = data.model_dump(exclude_unset=True)

        # Update dedup key if domain changed
        if "domain" in update_data:
            update_data["dedup_key"] = compute_company_dedup_key(update_data["domain"])

        # Update verified_at if verified changed to True
        if update_data.get("verified") and not company.verified:
            update_data["verified_at"] = datetime.utcnow()

        for key, value in update_data.items():
            setattr(company, key, value)

        await self.db.flush()
        await self.db.refresh(company)
        logger.info("Funnel Company aktualisiert: {id}", id=company_id)
        return company

    async def delete(self, tenant_id: str, company_id: int) -> None:
        """Delete a funnel company."""
        company = await self.get_by_id(tenant_id, company_id)
        await self.db.delete(company)
        await self.db.flush()
        logger.info("Funnel Company gelöscht: {id}", id=company_id)

    async def find_or_create_by_domain(
        self, tenant_id: str, funnel_id: int, name: str, domain: str | None
    ) -> FunnelCompany | None:
        """Find existing company by domain or create new one."""
        if not domain:
            return None

        dedup_key = compute_company_dedup_key(domain)
        if not dedup_key:
            return None

        # Check for existing
        result = await self.db.execute(
            select(FunnelCompany).where(
                FunnelCompany.tenant_id == tenant_id,
                FunnelCompany.funnel_id == funnel_id,
                FunnelCompany.dedup_key == dedup_key,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        # Create new
        company = FunnelCompany(
            tenant_id=tenant_id,
            funnel_id=funnel_id,
            name=name,
            domain=domain,
            dedup_key=dedup_key,
        )
        self.db.add(company)
        await self.db.flush()
        return company


class ProspectService:
    """Service for funnel prospect management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.dedup_service = DeduplicationService(db)

    async def create(
        self,
        tenant_id: str,
        funnel_id: int,
        data: FunnelProspectCreate,
        check_duplicates: bool = True,
    ) -> FunnelProspect:
        """Create a new prospect in a funnel."""
        # Compute dedup keys
        dedup_keys = compute_dedup_keys(
            email=data.email,
            linkedin_url=data.linkedin_url,
            phone=data.phone or data.mobile,
        )

        # Check for CRM duplicates
        duplicate_of_crm_contact = None
        if check_duplicates and (data.email or data.linkedin_url):
            dup_check = await self.dedup_service.check_duplicates(
                tenant_id=tenant_id,
                email=data.email,
                linkedin_url=data.linkedin_url,
                phone=data.phone or data.mobile,
            )
            # Mark as duplicate if CRM contact exists
            for match in dup_check.matches:
                if match.match_type == "crm_contact" and match.contact_id:
                    duplicate_of_crm_contact = match.contact_id
                    break

        # Get first stage if not specified
        stage_id = data.stage_id
        if not stage_id:
            result = await self.db.execute(
                select(FunnelStage)
                .where(FunnelStage.funnel_id == funnel_id)
                .order_by(FunnelStage.position)
                .limit(1)
            )
            first_stage = result.scalar_one_or_none()
            if first_stage:
                stage_id = first_stage.id

        prospect = FunnelProspect(
            tenant_id=tenant_id,
            funnel_id=funnel_id,
            company_id=data.company_id,
            stage_id=stage_id,
            owner_id=data.owner_id,
            email=data.email,
            name=data.name,
            first_name=data.first_name,
            last_name=data.last_name,
            phone=data.phone,
            mobile=data.mobile,
            position=data.position,
            department=data.department,
            seniority=data.seniority,
            linkedin_url=data.linkedin_url,
            twitter_url=data.twitter_url,
            source=data.source,
            source_id=data.source_id,
            score=data.score,
            tags=data.tags,
            custom_fields=data.custom_fields,
            duplicate_of_crm_contact=duplicate_of_crm_contact,
            is_duplicate=duplicate_of_crm_contact is not None,
            **dedup_keys,
        )
        self.db.add(prospect)
        await self.db.flush()
        await self.db.refresh(prospect)
        logger.info("Prospect erstellt: {name}", name=data.name)
        return prospect

    async def get_by_id(self, tenant_id: str, prospect_id: int) -> FunnelProspect:
        """Get a prospect by ID with related data."""
        result = await self.db.execute(
            select(FunnelProspect)
            .options(
                selectinload(FunnelProspect.company),
                selectinload(FunnelProspect.stage),
                selectinload(FunnelProspect.owner),
                selectinload(FunnelProspect.activities),
            )
            .where(
                FunnelProspect.id == prospect_id, FunnelProspect.tenant_id == tenant_id
            )
        )
        prospect = result.scalar_one_or_none()
        if not prospect:
            raise NotFoundError("Prospect", prospect_id)
        return prospect

    async def list_prospects(
        self,
        tenant_id: str,
        funnel_id: int,
        stage_id: int | None = None,
        status: str | None = None,
        owner_id: int | None = None,
        company_id: int | None = None,
        is_duplicate: bool | None = None,
    ) -> list[FunnelProspect]:
        """List prospects in a funnel."""
        query = (
            select(FunnelProspect)
            .options(
                selectinload(FunnelProspect.company),
                selectinload(FunnelProspect.stage),
            )
            .where(
                FunnelProspect.tenant_id == tenant_id,
                FunnelProspect.funnel_id == funnel_id,
            )
        )

        if stage_id:
            query = query.where(FunnelProspect.stage_id == stage_id)
        if status:
            query = query.where(FunnelProspect.status == status)
        if owner_id:
            query = query.where(FunnelProspect.owner_id == owner_id)
        if company_id:
            query = query.where(FunnelProspect.company_id == company_id)
        if is_duplicate is not None:
            query = query.where(FunnelProspect.is_duplicate == is_duplicate)

        query = query.order_by(FunnelProspect.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update(
        self, tenant_id: str, prospect_id: int, data: FunnelProspectUpdate
    ) -> FunnelProspect:
        """Update a prospect."""
        prospect = await self.get_by_id(tenant_id, prospect_id)

        update_data = data.model_dump(exclude_unset=True)

        # Update dedup keys if relevant fields changed
        if any(k in update_data for k in ["email", "linkedin_url", "phone", "mobile"]):
            new_dedup = compute_dedup_keys(
                email=update_data.get("email", prospect.email),
                linkedin_url=update_data.get("linkedin_url", prospect.linkedin_url),
                phone=update_data.get("phone", prospect.phone)
                or update_data.get("mobile", prospect.mobile),
            )
            update_data.update(new_dedup)

        # Update email_verified_at if email_verified changed to True
        if update_data.get("email_verified") and not prospect.email_verified:
            update_data["email_verified_at"] = datetime.utcnow()

        for key, value in update_data.items():
            setattr(prospect, key, value)

        await self.db.flush()
        await self.db.refresh(prospect)
        logger.info("Prospect aktualisiert: {id}", id=prospect_id)
        return prospect

    async def move_to_stage(
        self, tenant_id: str, prospect_id: int, data: ProspectMoveRequest
    ) -> FunnelProspect:
        """Move a prospect to a different stage."""
        prospect = await self.get_by_id(tenant_id, prospect_id)
        old_stage_id = prospect.stage_id

        # Validate new stage
        result = await self.db.execute(
            select(FunnelStage).where(
                FunnelStage.id == data.stage_id,
                FunnelStage.funnel_id == prospect.funnel_id,
            )
        )
        new_stage = result.scalar_one_or_none()
        if not new_stage:
            raise ValidationError("Stage gehört nicht zum Funnel des Prospects")

        # Update stage
        prospect.stage_id = data.stage_id

        # Handle special stages
        if new_stage.is_disqualified:
            prospect.status = "do_not_contact"
        elif new_stage.is_handoff:
            prospect.status = "qualified"

        await self.db.flush()

        # Log stage change activity
        if old_stage_id != data.stage_id:
            activity = FunnelActivity(
                tenant_id=tenant_id,
                prospect_id=prospect_id,
                activity_type="stage_changed",
                subject=f"Stage geändert zu {new_stage.name}",
                activity_date=datetime.utcnow(),
                metadata_={"old_stage_id": old_stage_id, "new_stage_id": data.stage_id},
            )
            self.db.add(activity)
            await self.db.flush()

        await self.db.refresh(prospect)
        logger.info(
            "Prospect verschoben: {id} -> Stage {stage}",
            id=prospect_id,
            stage=new_stage.name,
        )
        return prospect

    async def delete(self, tenant_id: str, prospect_id: int) -> None:
        """Delete a prospect."""
        prospect = await self.get_by_id(tenant_id, prospect_id)
        await self.db.delete(prospect)
        await self.db.flush()
        logger.info("Prospect gelöscht: {id}", id=prospect_id)

    async def get_kanban_board(self, tenant_id: str, funnel_id: int) -> dict:
        """Get prospects organized by stage for Kanban view."""
        # Get funnel with stages
        funnel_result = await self.db.execute(
            select(Funnel)
            .options(selectinload(Funnel.stages))
            .where(Funnel.id == funnel_id, Funnel.tenant_id == tenant_id)
        )
        funnel = funnel_result.scalar_one_or_none()
        if not funnel:
            raise NotFoundError("Funnel", funnel_id)

        # Get all active prospects
        prospects_result = await self.db.execute(
            select(FunnelProspect)
            .options(
                selectinload(FunnelProspect.company),
                selectinload(FunnelProspect.stage),
            )
            .where(
                FunnelProspect.funnel_id == funnel_id,
                FunnelProspect.tenant_id == tenant_id,
                FunnelProspect.status.notin_(["handed_off", "do_not_contact"]),
            )
            .order_by(FunnelProspect.score.desc(), FunnelProspect.created_at.desc())
        )
        prospects = list(prospects_result.scalars().all())

        # Organize by stage
        stages_data = []
        for stage in sorted(funnel.stages, key=lambda s: s.position):
            stage_prospects = [p for p in prospects if p.stage_id == stage.id]
            stages_data.append({
                "id": stage.id,
                "name": stage.name,
                "position": stage.position,
                "color": stage.color,
                "is_handoff": stage.is_handoff,
                "is_disqualified": stage.is_disqualified,
                "prospects": stage_prospects,
                "prospect_count": len(stage_prospects),
            })

        return {
            "funnel": funnel,
            "stages": stages_data,
        }


class ActivityService:
    """Service for funnel activity management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        tenant_id: str,
        prospect_id: int,
        data: FunnelActivityCreate,
        user_id: int | None = None,
    ) -> FunnelActivity:
        """Create a new activity for a prospect."""
        activity = FunnelActivity(
            tenant_id=tenant_id,
            prospect_id=prospect_id,
            user_id=user_id,
            activity_type=data.activity_type,
            subject=data.subject,
            content=data.content,
            channel=data.channel,
            external_id=data.external_id,
            external_url=data.external_url,
            status=data.status,
            activity_date=data.activity_date or datetime.utcnow(),
            metadata_=data.metadata,
        )
        self.db.add(activity)
        await self.db.flush()
        await self.db.refresh(activity)
        logger.info("Funnel Activity erstellt: {type}", type=data.activity_type)
        return activity

    async def list_for_prospect(
        self, tenant_id: str, prospect_id: int
    ) -> list[FunnelActivity]:
        """List activities for a prospect (timeline)."""
        result = await self.db.execute(
            select(FunnelActivity)
            .options(selectinload(FunnelActivity.user))
            .where(
                FunnelActivity.tenant_id == tenant_id,
                FunnelActivity.prospect_id == prospect_id,
            )
            .order_by(FunnelActivity.activity_date.desc())
        )
        return list(result.scalars().all())
