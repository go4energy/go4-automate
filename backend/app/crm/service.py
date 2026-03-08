"""CRM service - CRUD and business logic for contacts, pipelines, deals."""

from datetime import UTC, datetime
from decimal import Decimal

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crm.models import (
    CrmActivity,
    CrmContact,
    CrmDeal,
    CrmPipeline,
    CrmPipelineStage,
    CrmTask,
)
from app.crm.schemas import (
    ActivityCreate,
    CallLogRequest,
    CrmContactCreate,
    DealCreate,
    DealMoveRequest,
    DealUpdate,
    PipelineCreate,
    PipelineStageCreate,
    PipelineStageUpdate,
    PipelineUpdate,
    TaskCreate,
    TaskUpdate,
)
from app.engagement import (
    CrmActivityType,
    log_crm_activity,
)
from app.exceptions import DuplicateError, NotFoundError, ValidationError


class CrmService:
    """Service for contact management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, tenant_id: str, data: CrmContactCreate) -> CrmContact:
        """Create a new contact for a tenant."""
        existing = await self.db.execute(
            select(CrmContact).where(
                CrmContact.tenant_id == tenant_id,
                CrmContact.email == data.email,
            )
        )
        if existing.scalar_one_or_none():
            raise DuplicateError("Contact", "email")

        contact = CrmContact(
            tenant_id=tenant_id,
            email=data.email,
            name=data.name,
            phone=data.phone,
            source=data.source,
            konfigurator_data=data.konfigurator_data,
            notes=data.notes,
        )
        self.db.add(contact)
        await self.db.flush()
        await self.db.refresh(contact)
        logger.info(
            "Contact erstellt: {email} (Tenant: {tenant})",
            email=data.email,
            tenant=tenant_id,
        )
        return contact

    async def list_contacts(
        self,
        tenant_id: str,
        status: str | None = None,
        source: str | None = None,
    ) -> list[CrmContact]:
        """List contacts for a tenant with optional filters."""
        query = select(CrmContact).where(CrmContact.tenant_id == tenant_id)
        if status:
            query = query.where(CrmContact.status == status)
        if source:
            query = query.where(CrmContact.source == source)
        query = query.order_by(CrmContact.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, tenant_id: str, contact_id: int) -> CrmContact:
        """Get a single contact by ID (scoped to tenant)."""
        result = await self.db.execute(
            select(CrmContact).where(
                CrmContact.id == contact_id,
                CrmContact.tenant_id == tenant_id,
            )
        )
        contact = result.scalar_one_or_none()
        if not contact:
            raise NotFoundError("Contact", contact_id)
        return contact

    async def update_status(
        self, tenant_id: str, contact_id: int, status: str
    ) -> CrmContact:
        """Update contact status."""
        contact = await self.get_by_id(tenant_id, contact_id)
        contact.status = status
        await self.db.flush()
        await self.db.refresh(contact)
        logger.info(
            "Contact-Status aktualisiert: {id} -> {status}",
            id=contact_id,
            status=status,
        )
        return contact

    async def toggle_followup_pause(
        self, tenant_id: str, contact_id: int, paused: bool
    ) -> CrmContact:
        """Pause or resume follow-up for a contact."""
        contact = await self.get_by_id(tenant_id, contact_id)
        contact.followup_paused = paused
        await self.db.flush()
        await self.db.refresh(contact)
        action = "pausiert" if paused else "fortgesetzt"
        logger.info(
            "Follow-up {action}: Contact {id}",
            action=action,
            id=contact_id,
        )
        return contact


# Default pipeline configuration
DEFAULT_PIPELINE = {
    "name": "Sales Pipeline",
    "is_default": True,
    "stages": [
        {"name": "New", "position": 0, "probability": 10, "color": "#6B7280"},
        {"name": "Qualified", "position": 1, "probability": 25, "color": "#3B82F6"},
        {"name": "Proposal", "position": 2, "probability": 50, "color": "#8B5CF6"},
        {"name": "Negotiation", "position": 3, "probability": 75, "color": "#F59E0B"},
        {"name": "Won", "position": 4, "probability": 100, "color": "#10B981", "is_won": True},
        {"name": "Lost", "position": 5, "probability": 0, "color": "#EF4444", "is_lost": True},
    ],
}


class PipelineService:
    """Service for pipeline management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def ensure_default_pipeline(self, tenant_id: str) -> CrmPipeline:
        """Ensure a default pipeline exists for the tenant."""
        result = await self.db.execute(
            select(CrmPipeline).where(
                CrmPipeline.tenant_id == tenant_id,
                CrmPipeline.is_default.is_(True),
            )
        )
        pipeline = result.scalar_one_or_none()
        if pipeline:
            return pipeline

        # Create default pipeline
        return await self.create(
            tenant_id,
            PipelineCreate(
                name=DEFAULT_PIPELINE["name"],
                is_default=True,
                stages=[PipelineStageCreate(**s) for s in DEFAULT_PIPELINE["stages"]],
            ),
        )

    async def create(self, tenant_id: str, data: PipelineCreate) -> CrmPipeline:
        """Create a new pipeline with stages."""
        pipeline = CrmPipeline(
            tenant_id=tenant_id,
            name=data.name,
            is_default=data.is_default,
            color=data.color,
            description=data.description,
        )
        self.db.add(pipeline)
        await self.db.flush()

        # Create stages
        for stage_data in data.stages:
            stage = CrmPipelineStage(
                tenant_id=tenant_id,
                pipeline_id=pipeline.id,
                name=stage_data.name,
                position=stage_data.position,
                probability=stage_data.probability,
                color=stage_data.color,
                is_won=stage_data.is_won,
                is_lost=stage_data.is_lost,
            )
            self.db.add(stage)

        await self.db.flush()
        await self.db.refresh(pipeline)
        logger.info("Pipeline erstellt: {name}", name=data.name)
        return pipeline

    async def get_by_id(self, tenant_id: str, pipeline_id: int) -> CrmPipeline:
        """Get a pipeline by ID with stages."""
        result = await self.db.execute(
            select(CrmPipeline)
            .options(selectinload(CrmPipeline.stages))
            .where(
                CrmPipeline.id == pipeline_id,
                CrmPipeline.tenant_id == tenant_id,
            )
        )
        pipeline = result.scalar_one_or_none()
        if not pipeline:
            raise NotFoundError("Pipeline", pipeline_id)
        return pipeline

    async def list_pipelines(self, tenant_id: str) -> list[CrmPipeline]:
        """List all pipelines for a tenant."""
        result = await self.db.execute(
            select(CrmPipeline)
            .options(selectinload(CrmPipeline.stages))
            .where(CrmPipeline.tenant_id == tenant_id)
            .order_by(CrmPipeline.is_default.desc(), CrmPipeline.name)
        )
        return list(result.scalars().all())

    async def update(
        self, tenant_id: str, pipeline_id: int, data: PipelineUpdate
    ) -> CrmPipeline:
        """Update a pipeline."""
        pipeline = await self.get_by_id(tenant_id, pipeline_id)

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(pipeline, key, value)

        await self.db.flush()
        await self.db.refresh(pipeline)
        logger.info("Pipeline aktualisiert: {id}", id=pipeline_id)
        return pipeline

    async def delete(self, tenant_id: str, pipeline_id: int) -> None:
        """Delete a pipeline."""
        pipeline = await self.get_by_id(tenant_id, pipeline_id)

        # Check if there are deals
        deal_count = await self.db.execute(
            select(func.count(CrmDeal.id)).where(CrmDeal.pipeline_id == pipeline_id)
        )
        if deal_count.scalar() > 0:
            raise ValidationError(
                "Pipeline kann nicht gelöscht werden, da noch Deals vorhanden sind"
            )

        await self.db.delete(pipeline)
        await self.db.flush()
        logger.info("Pipeline gelöscht: {id}", id=pipeline_id)

    async def get_deal_count(self, pipeline_id: int) -> int:
        """Get the number of deals in a pipeline."""
        result = await self.db.execute(
            select(func.count(CrmDeal.id)).where(CrmDeal.pipeline_id == pipeline_id)
        )
        return result.scalar() or 0

    # Stage management
    async def add_stage(
        self, tenant_id: str, pipeline_id: int, data: PipelineStageCreate
    ) -> CrmPipelineStage:
        """Add a stage to a pipeline."""
        await self.get_by_id(tenant_id, pipeline_id)  # Validate pipeline exists

        stage = CrmPipelineStage(
            tenant_id=tenant_id,
            pipeline_id=pipeline_id,
            name=data.name,
            position=data.position,
            probability=data.probability,
            color=data.color,
            is_won=data.is_won,
            is_lost=data.is_lost,
        )
        self.db.add(stage)
        await self.db.flush()
        await self.db.refresh(stage)
        logger.info("Stage hinzugefügt: {name}", name=data.name)
        return stage

    async def update_stage(
        self, tenant_id: str, stage_id: int, data: PipelineStageUpdate
    ) -> CrmPipelineStage:
        """Update a pipeline stage."""
        result = await self.db.execute(
            select(CrmPipelineStage).where(
                CrmPipelineStage.id == stage_id,
                CrmPipelineStage.tenant_id == tenant_id,
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
        """Delete a pipeline stage."""
        result = await self.db.execute(
            select(CrmPipelineStage).where(
                CrmPipelineStage.id == stage_id,
                CrmPipelineStage.tenant_id == tenant_id,
            )
        )
        stage = result.scalar_one_or_none()
        if not stage:
            raise NotFoundError("Stage", stage_id)

        # Check if there are deals in this stage
        deal_count = await self.db.execute(
            select(func.count(CrmDeal.id)).where(CrmDeal.stage_id == stage_id)
        )
        if deal_count.scalar() > 0:
            raise ValidationError(
                "Stage kann nicht gelöscht werden, da noch Deals vorhanden sind"
            )

        await self.db.delete(stage)
        await self.db.flush()
        logger.info("Stage gelöscht: {id}", id=stage_id)


class DealService:
    """Service for deal management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, tenant_id: str, data: DealCreate) -> CrmDeal:
        """Create a new deal."""
        # Validate stage belongs to pipeline
        result = await self.db.execute(
            select(CrmPipelineStage).where(
                CrmPipelineStage.id == data.stage_id,
                CrmPipelineStage.pipeline_id == data.pipeline_id,
            )
        )
        stage = result.scalar_one_or_none()
        if not stage:
            raise ValidationError("Stage gehört nicht zur gewählten Pipeline")

        deal = CrmDeal(
            tenant_id=tenant_id,
            title=data.title,
            pipeline_id=data.pipeline_id,
            stage_id=data.stage_id,
            contact_id=data.contact_id,
            company_id=data.company_id,
            owner_id=data.owner_id,
            value=data.value,
            currency=data.currency,
            probability=stage.probability,
            expected_close=data.expected_close,
            priority=data.priority,
            tags=data.tags,
            description=data.description,
            custom_fields=data.custom_fields,
        )
        self.db.add(deal)
        await self.db.flush()
        await self.db.refresh(deal)

        # Log activity if contact is linked
        if deal.contact_id:
            try:
                await log_crm_activity(
                    db=self.db,
                    tenant_id=tenant_id,
                    contact_id=deal.contact_id,
                    activity_type=CrmActivityType.DEAL_CREATED,
                    subject=f"Deal erstellt: {deal.title}",
                    deal_id=deal.id,
                    metadata={
                        "pipeline_id": deal.pipeline_id,
                        "stage_id": deal.stage_id,
                        "value": str(deal.value) if deal.value else None,
                    },
                    commit=False,
                )
                await self.db.flush()
            except Exception as e:
                logger.warning(f"Activity logging failed for deal creation: {e}")

        logger.info("Deal erstellt: {title}", title=data.title)
        return deal

    async def get_by_id(self, tenant_id: str, deal_id: int) -> CrmDeal:
        """Get a deal by ID with related data."""
        result = await self.db.execute(
            select(CrmDeal)
            .options(
                selectinload(CrmDeal.contact),
                selectinload(CrmDeal.company),
                selectinload(CrmDeal.stage),
                selectinload(CrmDeal.owner),
            )
            .where(CrmDeal.id == deal_id, CrmDeal.tenant_id == tenant_id)
        )
        deal = result.scalar_one_or_none()
        if not deal:
            raise NotFoundError("Deal", deal_id)
        return deal

    async def list_deals(
        self,
        tenant_id: str,
        pipeline_id: int | None = None,
        stage_id: int | None = None,
        status: str | None = None,
    ) -> list[CrmDeal]:
        """List deals with optional filters."""
        query = (
            select(CrmDeal)
            .options(
                selectinload(CrmDeal.contact),
                selectinload(CrmDeal.company),
                selectinload(CrmDeal.stage),
            )
            .where(CrmDeal.tenant_id == tenant_id)
        )

        if pipeline_id:
            query = query.where(CrmDeal.pipeline_id == pipeline_id)
        if stage_id:
            query = query.where(CrmDeal.stage_id == stage_id)
        if status:
            query = query.where(CrmDeal.status == status)

        query = query.order_by(CrmDeal.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_kanban_board(self, tenant_id: str, pipeline_id: int) -> dict:
        """Get deals organized by stage for Kanban view."""
        # Get pipeline with stages
        pipeline_result = await self.db.execute(
            select(CrmPipeline)
            .options(selectinload(CrmPipeline.stages))
            .where(CrmPipeline.id == pipeline_id, CrmPipeline.tenant_id == tenant_id)
        )
        pipeline = pipeline_result.scalar_one_or_none()
        if not pipeline:
            raise NotFoundError("Pipeline", pipeline_id)

        # Get all open deals for this pipeline
        deals_result = await self.db.execute(
            select(CrmDeal)
            .options(
                selectinload(CrmDeal.contact),
                selectinload(CrmDeal.company),
                selectinload(CrmDeal.stage),
            )
            .where(
                CrmDeal.pipeline_id == pipeline_id,
                CrmDeal.tenant_id == tenant_id,
                CrmDeal.status == "open",
            )
            .order_by(CrmDeal.created_at.desc())
        )
        deals = list(deals_result.scalars().all())

        # Organize by stage
        stages_data = []
        for stage in sorted(pipeline.stages, key=lambda s: s.position):
            stage_deals = [d for d in deals if d.stage_id == stage.id]
            total_value = sum(d.value or Decimal("0") for d in stage_deals)
            stages_data.append({
                "id": stage.id,
                "name": stage.name,
                "position": stage.position,
                "probability": stage.probability,
                "color": stage.color,
                "is_won": stage.is_won,
                "is_lost": stage.is_lost,
                "deals": stage_deals,
                "total_value": total_value,
                "deal_count": len(stage_deals),
            })

        return {
            "pipeline": pipeline,
            "stages": stages_data,
        }

    async def update(
        self, tenant_id: str, deal_id: int, data: DealUpdate
    ) -> CrmDeal:
        """Update a deal."""
        deal = await self.get_by_id(tenant_id, deal_id)

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(deal, key, value)

        await self.db.flush()
        await self.db.refresh(deal)
        logger.info("Deal aktualisiert: {id}", id=deal_id)
        return deal

    async def move(
        self, tenant_id: str, deal_id: int, data: DealMoveRequest
    ) -> CrmDeal:
        """Move a deal to a different stage."""
        deal = await self.get_by_id(tenant_id, deal_id)

        # Get the new stage
        result = await self.db.execute(
            select(CrmPipelineStage).where(
                CrmPipelineStage.id == data.stage_id,
                CrmPipelineStage.pipeline_id == deal.pipeline_id,
            )
        )
        stage = result.scalar_one_or_none()
        if not stage:
            raise ValidationError("Stage gehört nicht zur Pipeline des Deals")

        deal.stage_id = data.stage_id
        deal.probability = stage.probability

        # Handle won/lost status
        if stage.is_won:
            deal.status = "won"
            deal.won_at = datetime.utcnow()
        elif stage.is_lost:
            deal.status = "lost"
            deal.lost_at = datetime.utcnow()
        else:
            deal.status = "open"

        await self.db.flush()
        await self.db.refresh(deal)

        # Log activity if contact is linked
        if deal.contact_id:
            try:
                # Determine activity type based on stage
                if stage.is_won:
                    activity_type = CrmActivityType.DEAL_WON
                    subject = f"Deal gewonnen: {deal.title}"
                elif stage.is_lost:
                    activity_type = CrmActivityType.DEAL_LOST
                    subject = f"Deal verloren: {deal.title}"
                else:
                    activity_type = CrmActivityType.DEAL_STAGE_CHANGED
                    subject = f"Deal nach {stage.name} verschoben"

                await log_crm_activity(
                    db=self.db,
                    tenant_id=tenant_id,
                    contact_id=deal.contact_id,
                    activity_type=activity_type,
                    subject=subject,
                    deal_id=deal.id,
                    metadata={
                        "stage_name": stage.name,
                        "stage_id": stage.id,
                        "probability": stage.probability,
                    },
                    commit=False,
                )
                await self.db.flush()
            except Exception as e:
                logger.warning(f"Activity logging failed for deal move: {e}")

        logger.info("Deal verschoben: {id} -> Stage {stage}", id=deal_id, stage=stage.name)
        return deal

    async def delete(self, tenant_id: str, deal_id: int) -> None:
        """Delete a deal."""
        deal = await self.get_by_id(tenant_id, deal_id)
        await self.db.delete(deal)
        await self.db.flush()
        logger.info("Deal gelöscht: {id}", id=deal_id)


class ActivityService:
    """Service for activity management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self, tenant_id: str, user_id: int | None, data: ActivityCreate
    ) -> CrmActivity:
        """Create a new activity."""
        activity = CrmActivity(
            tenant_id=tenant_id,
            user_id=user_id,
            activity_type=data.activity_type,
            subject=data.subject,
            description=data.description,
            activity_date=data.activity_date or datetime.utcnow(),
            contact_id=data.contact_id,
            company_id=data.company_id,
            deal_id=data.deal_id,
            metadata_=data.metadata,
        )
        self.db.add(activity)
        await self.db.flush()
        await self.db.refresh(activity)

        # Log to engagement activities if contact is linked
        if activity.contact_id:
            try:
                # Map CRM activity types to engagement activity types
                activity_type_map = {
                    "note": CrmActivityType.NOTE_ADDED,
                    "call": CrmActivityType.MEETING_COMPLETED,  # Use meeting for calls
                    "meeting": CrmActivityType.MEETING_COMPLETED,
                    "email": CrmActivityType.NOTE_ADDED,  # Emails logged separately
                }
                engagement_type = activity_type_map.get(
                    data.activity_type, CrmActivityType.NOTE_ADDED
                )

                await log_crm_activity(
                    db=self.db,
                    tenant_id=tenant_id,
                    contact_id=activity.contact_id,
                    activity_type=engagement_type,
                    subject=data.subject,
                    content=data.description,
                    deal_id=data.deal_id,
                    performed_by=user_id,
                    metadata={
                        "crm_activity_id": activity.id,
                        "activity_type": data.activity_type,
                    },
                    commit=False,
                )
                await self.db.flush()
            except Exception as e:
                logger.warning(f"Activity logging failed for CRM activity: {e}")

        logger.info("Activity erstellt: {type}", type=data.activity_type)
        return activity

    async def list_for_contact(
        self, tenant_id: str, contact_id: int
    ) -> list[CrmActivity]:
        """List activities for a contact."""
        result = await self.db.execute(
            select(CrmActivity)
            .options(selectinload(CrmActivity.user))
            .where(
                CrmActivity.tenant_id == tenant_id,
                CrmActivity.contact_id == contact_id,
            )
            .order_by(CrmActivity.activity_date.desc())
        )
        return list(result.scalars().all())

    async def list_for_deal(self, tenant_id: str, deal_id: int) -> list[CrmActivity]:
        """List activities for a deal."""
        result = await self.db.execute(
            select(CrmActivity)
            .options(selectinload(CrmActivity.user))
            .where(
                CrmActivity.tenant_id == tenant_id,
                CrmActivity.deal_id == deal_id,
            )
            .order_by(CrmActivity.activity_date.desc())
        )
        return list(result.scalars().all())


class TaskService:
    """Service for task management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self, tenant_id: str, user_id: int | None, data: TaskCreate
    ) -> CrmTask:
        """Create a new task."""
        task = CrmTask(
            tenant_id=tenant_id,
            created_by=user_id,
            assigned_to=data.assigned_to or user_id,
            title=data.title,
            description=data.description,
            due_date=data.due_date,
            priority=data.priority,
            contact_id=data.contact_id,
            company_id=data.company_id,
            deal_id=data.deal_id,
        )
        self.db.add(task)
        await self.db.flush()
        await self.db.refresh(task)

        # Log to engagement activities if contact is linked
        if task.contact_id:
            try:
                await log_crm_activity(
                    db=self.db,
                    tenant_id=tenant_id,
                    contact_id=task.contact_id,
                    activity_type=CrmActivityType.TASK_CREATED,
                    subject=f"Task erstellt: {data.title}",
                    content=data.description,
                    deal_id=data.deal_id,
                    task_id=task.id,
                    performed_by=user_id,
                    metadata={
                        "due_date": str(data.due_date) if data.due_date else None,
                        "priority": data.priority,
                    },
                    commit=False,
                )
                await self.db.flush()
            except Exception as e:
                logger.warning(f"Activity logging failed for task creation: {e}")

        logger.info("Task erstellt: {title}", title=data.title)
        return task

    async def get_by_id(self, tenant_id: str, task_id: int) -> CrmTask:
        """Get a task by ID."""
        result = await self.db.execute(
            select(CrmTask)
            .options(selectinload(CrmTask.assignee), selectinload(CrmTask.creator))
            .where(CrmTask.id == task_id, CrmTask.tenant_id == tenant_id)
        )
        task = result.scalar_one_or_none()
        if not task:
            raise NotFoundError("Task", task_id)
        return task

    async def list_tasks(
        self,
        tenant_id: str,
        assigned_to: int | None = None,
        status: str | None = None,
    ) -> list[CrmTask]:
        """List tasks with optional filters."""
        query = (
            select(CrmTask)
            .options(selectinload(CrmTask.assignee), selectinload(CrmTask.creator))
            .where(CrmTask.tenant_id == tenant_id)
        )

        if assigned_to:
            query = query.where(CrmTask.assigned_to == assigned_to)
        if status:
            query = query.where(CrmTask.status == status)

        query = query.order_by(CrmTask.due_date.asc().nullslast(), CrmTask.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update(
        self, tenant_id: str, task_id: int, data: TaskUpdate
    ) -> CrmTask:
        """Update a task."""
        task = await self.get_by_id(tenant_id, task_id)

        update_data = data.model_dump(exclude_unset=True)

        # Handle completion
        if update_data.get("status") == "completed" and task.status != "completed":
            update_data["completed_at"] = datetime.utcnow()

        # Check if task is being completed
        is_completing = (
            update_data.get("status") == "completed" and task.status != "completed"
        )

        for key, value in update_data.items():
            setattr(task, key, value)

        await self.db.flush()
        await self.db.refresh(task)

        # Log activity if task was just completed and contact is linked
        if is_completing and task.contact_id:
            try:
                await log_crm_activity(
                    db=self.db,
                    tenant_id=tenant_id,
                    contact_id=task.contact_id,
                    activity_type=CrmActivityType.TASK_COMPLETED,
                    subject=f"Task abgeschlossen: {task.title}",
                    task_id=task.id,
                    deal_id=task.deal_id,
                    metadata={
                        "completed_at": str(task.completed_at),
                    },
                    commit=False,
                )
                await self.db.flush()
            except Exception as e:
                logger.warning(f"Activity logging failed for task completion: {e}")

        logger.info("Task aktualisiert: {id}", id=task_id)
        return task

    async def delete(self, tenant_id: str, task_id: int) -> None:
        """Delete a task."""
        task = await self.get_by_id(tenant_id, task_id)
        await self.db.delete(task)
        await self.db.flush()
        logger.info("Task gelöscht: {id}", id=task_id)


class CallQueueService:
    """Service for phone call queue from engagement pending actions."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_calls(
        self,
        tenant_id: str,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """List phone pending actions with enriched contact data."""
        from app.contacts.models import Contact
        from app.engagement.models import EngagementPipeline, PendingAction

        query = (
            select(PendingAction)
            .where(
                PendingAction.tenant_id == tenant_id,
                PendingAction.module == "phone",
            )
        )

        if status:
            query = query.where(PendingAction.status == status)
        else:
            query = query.where(
                PendingAction.status.in_(["pending", "ready_for_approval", "approved"])
            )

        query = query.order_by(
            PendingAction.priority.desc(),
            PendingAction.due_at.asc().nullslast(),
            PendingAction.created_at.asc(),
        ).limit(limit)

        result = await self.db.execute(query)
        actions = list(result.scalars().all())

        # Enrich with contact and pipeline data
        enriched = []
        for action in actions:
            item = {
                "id": action.id,
                "contact_id": action.contact_id,
                "pipeline_id": action.pipeline_id,
                "enrollment_id": action.enrollment_id,
                "action_type": action.action_type,
                "suggested_content": action.suggested_content,
                "priority": action.priority,
                "due_at": action.due_at,
                "status": action.status,
                "created_at": action.created_at,
                "context": action.context,
                "contact_name": None,
                "contact_company": None,
                "contact_phone": None,
                "contact_email": None,
                "pipeline_name": None,
            }

            if action.contact_id:
                contact = await self.db.get(Contact, action.contact_id)
                if contact:
                    item["contact_name"] = f"{contact.first_name or ''} {contact.last_name or ''}".strip()
                    item["contact_company"] = contact.company
                    item["contact_phone"] = contact.phone
                    item["contact_email"] = contact.email

            if action.pipeline_id:
                pipeline = await self.db.get(EngagementPipeline, action.pipeline_id)
                if pipeline:
                    item["pipeline_name"] = pipeline.name

            enriched.append(item)

        return enriched

    async def generate_call_script(
        self, tenant_id: str, action_id: int
    ) -> str:
        """Generate a call script for a phone action via LLM."""
        from app.contacts.models import Contact
        from app.engagement.models import EngagementPipeline
        from app.services.llm import LLMService

        action = await self._get_action(tenant_id, action_id)

        # Build context
        contact_info = ""
        if action.contact_id:
            contact = await self.db.get(Contact, action.contact_id)
            if contact:
                contact_info = (
                    f"Name: {contact.first_name} {contact.last_name}\n"
                    f"Firma: {contact.company or 'unbekannt'}\n"
                    f"Position: {contact.position or 'unbekannt'}\n"
                )

        pipeline_info = ""
        if action.pipeline_id:
            pipeline = await self.db.get(EngagementPipeline, action.pipeline_id)
            if pipeline:
                pipeline_info = (
                    f"Produkt: {pipeline.product_name or pipeline.name}\n"
                    f"Zielgruppe: {pipeline.target_audience or ''}\n"
                    f"Tonalität: {pipeline.tone_of_voice or 'professionell'}\n"
                )

        context_text = ""
        if action.context:
            prev = action.context.get("previous_interactions", "")
            if prev:
                context_text = f"Bisherige Interaktionen:\n{prev}\n"

        prompt = (
            "Erstelle einen kurzen Gesprächsleitfaden für einen Telefonanruf.\n\n"
            f"KONTAKT:\n{contact_info}\n"
            f"KAMPAGNE:\n{pipeline_info}\n"
            f"{context_text}\n"
            f"Aktion: {action.action_type}\n\n"
            "Der Leitfaden soll enthalten:\n"
            "1. Begrüßung und Vorstellung (1-2 Sätze)\n"
            "2. Gesprächseinstieg / Grund des Anrufs\n"
            "3. 2-3 Qualifizierungsfragen\n"
            "4. Umgang mit häufigen Einwänden\n"
            "5. Call-to-Action (Termin, Demo, etc.)\n\n"
            "Halte den Leitfaden kurz und natürlich. Maximal 200 Wörter."
        )

        llm = LLMService(self.db)
        script = await llm.generate("phone_script", prompt)

        # Save as suggested_content
        action.suggested_content = script
        await self.db.commit()

        return script

    async def log_call(
        self, tenant_id: str, action_id: int, data: CallLogRequest
    ) -> dict:
        """Log a call result, complete the action, and create activity."""
        from app.engagement.activity_helper import Channel, Direction, log_activity
        from app.engagement.models import PipelineEnrollment

        action = await self._get_action(tenant_id, action_id)

        # Build result
        result = {
            "outcome": data.outcome,
            "duration_seconds": data.duration_seconds,
            "notes": data.notes,
        }

        # Complete the action
        is_success = data.outcome in ("answered", "qualified", "callback")
        action.status = "completed"
        action.result = result
        action.completed_at = datetime.now(UTC)
        if not is_success:
            action.error_message = f"Anruf-Ergebnis: {data.outcome}"

        # Update enrollment touch count
        if action.enrollment_id:
            enrollment = await self.db.get(PipelineEnrollment, action.enrollment_id)
            if enrollment:
                enrollment.touch_count = (enrollment.touch_count or 0) + 1
                enrollment.last_touch_at = datetime.now(UTC)
                if data.outcome == "qualified":
                    enrollment.stage = "qualified"
                elif data.outcome == "not_interested":
                    enrollment.stage = "lost"
                    enrollment.status = "stopped"
                    enrollment.outcome = "not_interested"

        # Log engagement activity
        if action.contact_id:
            outcome_labels = {
                "answered": "Gespräch geführt",
                "no_answer": "Nicht erreicht",
                "voicemail": "Mailbox",
                "wrong_number": "Falsche Nummer",
                "callback": "Rückruf vereinbart",
                "not_interested": "Kein Interesse",
                "qualified": "Qualifiziert",
            }
            subject = f"Anruf: {outcome_labels.get(data.outcome, data.outcome)}"

            try:
                await log_activity(
                    db=self.db,
                    tenant_id=tenant_id,
                    contact_id=action.contact_id,
                    channel=Channel.PHONE,
                    activity_type="call_made",
                    direction=Direction.OUTBOUND,
                    subject=subject,
                    content=data.notes,
                    source_module="crm",
                    pipeline_id=action.pipeline_id,
                    enrollment_id=action.enrollment_id,
                    metadata={
                        "outcome": data.outcome,
                        "duration_seconds": data.duration_seconds,
                        "action_id": action.id,
                    },
                    commit=False,
                )
            except Exception as e:
                logger.warning(f"Activity logging failed for call: {e}")

        # Create follow-up task if requested
        if data.follow_up_date and action.contact_id:
            task = CrmTask(
                tenant_id=tenant_id,
                title=f"Rückruf: {result.get('notes', 'Follow-up')}",
                description=data.notes,
                due_date=data.follow_up_date,
                priority="high",
                contact_id=action.contact_id,
                deal_id=data.deal_id,
            )
            self.db.add(task)

        await self.db.commit()

        return {
            "action_id": action.id,
            "status": "completed",
            "outcome": data.outcome,
        }

    async def get_stats(self, tenant_id: str) -> dict:
        """Get call queue statistics."""
        from app.engagement.models import PendingAction

        now = datetime.now(UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Total pending
        total_q = await self.db.execute(
            select(func.count(PendingAction.id)).where(
                PendingAction.tenant_id == tenant_id,
                PendingAction.module == "phone",
                PendingAction.status.in_(["pending", "ready_for_approval", "approved"]),
            )
        )
        total_pending = total_q.scalar() or 0

        # Due today
        due_q = await self.db.execute(
            select(func.count(PendingAction.id)).where(
                PendingAction.tenant_id == tenant_id,
                PendingAction.module == "phone",
                PendingAction.status.in_(["pending", "ready_for_approval", "approved"]),
                PendingAction.due_at <= now.replace(hour=23, minute=59, second=59),
                PendingAction.due_at >= today_start,
            )
        )
        due_today = due_q.scalar() or 0

        # Overdue
        overdue_q = await self.db.execute(
            select(func.count(PendingAction.id)).where(
                PendingAction.tenant_id == tenant_id,
                PendingAction.module == "phone",
                PendingAction.status.in_(["pending", "ready_for_approval", "approved"]),
                PendingAction.due_at < today_start,
            )
        )
        overdue = overdue_q.scalar() or 0

        # Completed today
        completed_q = await self.db.execute(
            select(func.count(PendingAction.id)).where(
                PendingAction.tenant_id == tenant_id,
                PendingAction.module == "phone",
                PendingAction.status == "completed",
                PendingAction.completed_at >= today_start,
            )
        )
        completed_today = completed_q.scalar() or 0

        # By priority
        priority_q = await self.db.execute(
            select(PendingAction.priority, func.count(PendingAction.id))
            .where(
                PendingAction.tenant_id == tenant_id,
                PendingAction.module == "phone",
                PendingAction.status.in_(["pending", "ready_for_approval", "approved"]),
            )
            .group_by(PendingAction.priority)
        )
        by_priority = dict(priority_q.all())

        return {
            "total_pending": total_pending,
            "due_today": due_today,
            "overdue": overdue,
            "completed_today": completed_today,
            "by_priority": by_priority,
        }

    async def _get_action(self, tenant_id: str, action_id: int):
        """Get a phone pending action or raise NotFoundError."""
        from app.engagement.models import PendingAction

        result = await self.db.execute(
            select(PendingAction).where(
                PendingAction.id == action_id,
                PendingAction.tenant_id == tenant_id,
                PendingAction.module == "phone",
            )
        )
        action = result.scalar_one_or_none()
        if not action:
            raise NotFoundError("Phone Action", action_id)
        return action
