"""Ad campaign service - CRUD and business logic for ad campaigns."""

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.models.ad_campaign import AdCampaign
from app.schemas.ad_campaign import AdCampaignCreate, AdCampaignUpdate


class AdCampaignService:
    """Service for ad campaign management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, tenant_id: str, data: AdCampaignCreate) -> AdCampaign:
        """Create a new ad campaign."""
        campaign = AdCampaign(
            tenant_id=tenant_id,
            platform=data.platform,
            platform_campaign_id=data.platform_campaign_id,
            name=data.name,
            objective=data.objective,
            status=data.status,
            daily_budget=data.daily_budget,
            total_budget=data.total_budget,
            start_date=data.start_date,
            end_date=data.end_date,
        )
        self.db.add(campaign)
        await self.db.flush()
        await self.db.refresh(campaign)
        logger.info(
            "Kampagne erstellt: {name} (Tenant: {tenant})",
            name=data.name,
            tenant=tenant_id,
        )
        return campaign

    async def list_campaigns(
        self,
        tenant_id: str,
        status: str | None = None,
    ) -> list[AdCampaign]:
        """List ad campaigns for a tenant with optional status filter."""
        query = select(AdCampaign).where(AdCampaign.tenant_id == tenant_id)
        if status:
            query = query.where(AdCampaign.status == status)
        query = query.order_by(AdCampaign.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, tenant_id: str, campaign_id: int) -> AdCampaign:
        """Get a single campaign by ID (scoped to tenant)."""
        result = await self.db.execute(
            select(AdCampaign).where(
                AdCampaign.id == campaign_id,
                AdCampaign.tenant_id == tenant_id,
            )
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise NotFoundError("AdCampaign", campaign_id)
        return campaign

    async def update(
        self, tenant_id: str, campaign_id: int, data: AdCampaignUpdate
    ) -> AdCampaign:
        """Update an ad campaign."""
        campaign = await self.get_by_id(tenant_id, campaign_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(campaign, field, value)
        await self.db.flush()
        await self.db.refresh(campaign)
        logger.info(
            "Kampagne aktualisiert: {id} (Tenant: {tenant})",
            id=campaign_id,
            tenant=tenant_id,
        )
        return campaign

    async def delete(self, tenant_id: str, campaign_id: int) -> None:
        """Delete an ad campaign."""
        campaign = await self.get_by_id(tenant_id, campaign_id)
        await self.db.delete(campaign)
        await self.db.flush()
        logger.info(
            "Kampagne gelöscht: {id} (Tenant: {tenant})",
            id=campaign_id,
            tenant=tenant_id,
        )
