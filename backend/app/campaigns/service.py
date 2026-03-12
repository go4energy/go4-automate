"""Campaigns service - business logic for ads pipeline."""

from datetime import date, timedelta
from decimal import Decimal

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.campaigns.hashing import hash_for_meta, hash_phone
from app.campaigns.meta_ads_client import get_campaign_insights, get_campaigns
from app.campaigns.models import (
    CampaignConfig,
    CampaignConversion,
    CampaignPerformance,
)
from app.campaigns.optimizer import optimize_campaign
from app.campaigns.schemas import (
    CampaignConfigCreate,
    CampaignConfigUpdate,
    CampaignDashboardStats,
    CampaignSummary,
    ConversionEventCreate,
    OptimizationResult,
    PeriodStats,
)
from app.campaigns.weather_service import get_current_weather
from app.config import settings
from app.exceptions import NotFoundError, ValidationError


class CampaignService:
    """Service for campaign management, optimization and tracking."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # --- Conversion Tracking ---

    async def track_conversion(
        self, tenant_id: str, data: ConversionEventCreate
    ) -> CampaignConversion:
        """Record a conversion event and optionally send to Meta CAPI."""
        event = CampaignConversion(
            tenant_id=tenant_id,
            event_name=data.event_name,
            event_time=data.event_time,
            source_url=data.source_url,
            user_agent=data.user_agent,
            fbc=data.fbc,
            fbp=data.fbp,
            email_hash=hash_for_meta(data.user_data.email)
            if data.user_data and data.user_data.email
            else None,
            phone_hash=hash_phone(data.user_data.phone)
            if data.user_data and data.user_data.phone
            else None,
            ip_address=data.user_data.client_ip if data.user_data else None,
            custom_data=data.custom_data,
        )
        self.db.add(event)
        await self.db.flush()

        # Send to Meta CAPI if configured
        if settings.meta_pixel_id and settings.meta_system_user_token:
            try:
                from app.campaigns.meta_ads_client import send_event

                result = await send_event(
                    settings.meta_pixel_id,
                    settings.meta_system_user_token,
                    data,
                )
                event.sent_to_meta = True
                event.meta_response = result
                await self.db.flush()
            except Exception as e:
                logger.error(
                    "CAPI-Fehler für Event {name}: {err}",
                    name=data.event_name,
                    err=str(e),
                )

        await self.db.refresh(event)
        logger.info(
            "Conversion Event: {name} (Tenant: {tenant}, Sent: {sent})",
            name=data.event_name,
            tenant=tenant_id,
            sent=event.sent_to_meta,
        )
        return event

    # --- Campaign Performance Sync ---

    async def sync_campaign_performance(
        self, tenant_id: str, date_from: str, date_to: str
    ) -> list[CampaignPerformance]:
        """Sync performance data from Meta for all configured campaigns."""
        access_token = settings.meta_system_user_token
        if not access_token or not settings.meta_ad_account_id:
            raise ValidationError("Meta API nicht konfiguriert")

        campaigns = await get_campaigns(settings.meta_ad_account_id, access_token)
        results: list[CampaignPerformance] = []

        for camp in campaigns:
            campaign_id = camp["id"]
            insights = await get_campaign_insights(
                campaign_id, access_token, date_from, date_to
            )
            if not insights:
                continue

            spend = Decimal(str(insights.get("spend", 0)))
            leads = insights.get("leads", 0)
            cpl = spend / leads if leads > 0 else Decimal("0")

            perf = CampaignPerformance(
                tenant_id=tenant_id,
                platform="meta",
                campaign_id=campaign_id,
                campaign_name=camp.get("name"),
                date=date.fromisoformat(date_from),
                impressions=insights.get("impressions", 0),
                clicks=insights.get("clicks", 0),
                spend=spend,
                leads=leads,
                cpl=cpl,
                conversions=insights.get("conversions", 0),
                cpc=Decimal(str(insights.get("cpc", 0)))
                if insights.get("cpc")
                else None,
                ctr=Decimal(str(insights.get("ctr", 0)))
                if insights.get("ctr")
                else None,
                frequency=Decimal(str(insights.get("frequency", 0)))
                if insights.get("frequency")
                else None,
                reach=insights.get("reach"),
            )
            self.db.add(perf)
            results.append(perf)

        await self.db.flush()
        for r in results:
            await self.db.refresh(r)

        logger.info(
            "Performance synchronisiert: {count} Kampagnen (Tenant: {tenant})",
            count=len(results),
            tenant=tenant_id,
        )
        return results

    # --- Dashboard Stats ---

    async def get_dashboard_stats(self, tenant_id: str) -> CampaignDashboardStats:
        """Get aggregated dashboard stats for the current tenant."""
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)

        today_stats = await self._get_period_stats(tenant_id, today, today)
        week_stats = await self._get_period_stats(tenant_id, week_start, today)
        month_stats = await self._get_period_stats(tenant_id, month_start, today)

        campaigns = await self._get_campaign_summaries(tenant_id, today)
        trend = self._calc_trend(week_stats, month_stats)

        return CampaignDashboardStats(
            today=today_stats,
            this_week=week_stats,
            this_month=month_stats,
            trend=trend,
            campaigns=campaigns,
        )

    async def _get_period_stats(
        self, tenant_id: str, from_date: date, to_date: date
    ) -> PeriodStats:
        """Aggregate stats for a date range."""
        result = await self.db.execute(
            select(
                func.coalesce(func.sum(CampaignPerformance.spend), 0),
                func.coalesce(func.sum(CampaignPerformance.leads), 0),
                func.coalesce(func.sum(CampaignPerformance.impressions), 0),
            ).where(
                CampaignPerformance.tenant_id == tenant_id,
                CampaignPerformance.date >= from_date,
                CampaignPerformance.date <= to_date,
            )
        )
        row = result.one()
        spend = Decimal(str(row[0]))
        leads = int(row[1])
        impressions = int(row[2])
        cpl = spend / leads if leads > 0 else Decimal("0")

        return PeriodStats(
            spend=spend,
            leads=leads,
            cpl=cpl.quantize(Decimal("0.01")),
            impressions=impressions,
        )

    async def _get_campaign_summaries(
        self, tenant_id: str, ref_date: date
    ) -> list[CampaignSummary]:
        """Get per-campaign summaries for the last 7 days."""
        from_date = ref_date - timedelta(days=7)
        result = await self.db.execute(
            select(
                CampaignPerformance.campaign_id,
                func.max(CampaignPerformance.campaign_name),
                func.coalesce(func.sum(CampaignPerformance.spend), 0),
                func.coalesce(func.sum(CampaignPerformance.leads), 0),
                func.avg(CampaignPerformance.ctr),
            )
            .where(
                CampaignPerformance.tenant_id == tenant_id,
                CampaignPerformance.date >= from_date,
                CampaignPerformance.date <= ref_date,
            )
            .group_by(CampaignPerformance.campaign_id)
        )
        summaries = []
        for row in result.all():
            spend = Decimal(str(row[1 + 1]))
            leads = int(row[2 + 1])
            cpl = spend / leads if leads > 0 else Decimal("0")
            summaries.append(
                CampaignSummary(
                    campaign_id=row[0],
                    campaign_name=row[1],
                    status="active",
                    spend=spend,
                    leads=leads,
                    cpl=cpl.quantize(Decimal("0.01")),
                    ctr=Decimal(str(row[4])).quantize(Decimal("0.0001"))
                    if row[4]
                    else None,
                )
            )
        return summaries

    @staticmethod
    def _calc_trend(week: PeriodStats, month: PeriodStats) -> str:
        """Calculate trend based on week vs month CPL."""
        if week.leads == 0 or month.leads == 0:
            return "stable"
        if week.cpl < month.cpl * Decimal("0.9"):
            return "improving"
        if week.cpl > month.cpl * Decimal("1.1"):
            return "declining"
        return "stable"

    # --- Performance History ---

    async def get_performance_history(
        self,
        tenant_id: str,
        days: int = 30,
        campaign_id: str | None = None,
    ) -> list[CampaignPerformance]:
        """Get daily performance history."""
        from_date = date.today() - timedelta(days=days)
        query = (
            select(CampaignPerformance)
            .where(
                CampaignPerformance.tenant_id == tenant_id,
                CampaignPerformance.date >= from_date,
            )
            .order_by(CampaignPerformance.date.asc())
        )
        if campaign_id:
            query = query.where(CampaignPerformance.campaign_id == campaign_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # --- Campaign Config ---

    async def configure_campaign(
        self, tenant_id: str, data: CampaignConfigCreate
    ) -> CampaignConfig:
        """Create a new campaign configuration."""
        existing = await self.db.execute(
            select(CampaignConfig).where(
                CampaignConfig.tenant_id == tenant_id,
                CampaignConfig.campaign_id == data.campaign_id,
            )
        )
        if existing.scalar_one_or_none():
            raise ValidationError(
                f"Kampagne {data.campaign_id} ist bereits konfiguriert"
            )

        config = CampaignConfig(
            tenant_id=tenant_id,
            campaign_id=data.campaign_id,
            campaign_name=data.campaign_name,
            platform=data.platform,
            target_cpl=data.target_cpl,
            max_cpl=data.max_cpl,
            daily_budget_min=data.daily_budget_min,
            daily_budget_max=data.daily_budget_max,
            weather_boost_enabled=data.weather_boost_enabled,
            weather_boost_factor=data.weather_boost_factor,
            auto_optimize=data.auto_optimize,
            optimization_rules=data.optimization_rules,
        )
        self.db.add(config)
        await self.db.flush()
        await self.db.refresh(config)
        logger.info(
            "Kampagne konfiguriert: {id} (Tenant: {tenant})",
            id=data.campaign_id,
            tenant=tenant_id,
        )
        return config

    async def update_campaign_config(
        self, tenant_id: str, config_id: int, data: CampaignConfigUpdate
    ) -> CampaignConfig:
        """Update an existing campaign configuration."""
        config = await self._get_config(tenant_id, config_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(config, field, value)
        await self.db.flush()
        await self.db.refresh(config)
        logger.info(
            "Kampagne aktualisiert: {id} (Tenant: {tenant})",
            id=config_id,
            tenant=tenant_id,
        )
        return config

    async def get_campaign_config(
        self, tenant_id: str, config_id: int
    ) -> CampaignConfig:
        """Get a campaign config by ID."""
        return await self._get_config(tenant_id, config_id)

    async def list_campaign_configs(
        self, tenant_id: str, pipeline_id: int | None = None
    ) -> list[CampaignConfig]:
        """List all campaign configs for a tenant."""
        query = (
            select(CampaignConfig)
            .where(CampaignConfig.tenant_id == tenant_id)
        )
        if pipeline_id is not None:
            query = query.where(CampaignConfig.pipeline_id == pipeline_id)
        query = query.order_by(CampaignConfig.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _get_config(
        self, tenant_id: str, config_id: int
    ) -> CampaignConfig:
        """Get a campaign config, raising NotFoundError if missing."""
        result = await self.db.execute(
            select(CampaignConfig).where(
                CampaignConfig.id == config_id,
                CampaignConfig.tenant_id == tenant_id,
            )
        )
        config = result.scalar_one_or_none()
        if not config:
            raise NotFoundError("CampaignConfig", config_id)
        return config

    # --- Optimization ---

    async def run_optimization(self, tenant_id: str) -> list[OptimizationResult]:
        """Run optimization for all active, auto-optimize campaigns."""
        access_token = settings.meta_system_user_token
        if not access_token:
            raise ValidationError("Meta API Token nicht konfiguriert")

        configs = await self.db.execute(
            select(CampaignConfig).where(
                CampaignConfig.tenant_id == tenant_id,
                CampaignConfig.status == "active",
                CampaignConfig.auto_optimize.is_(True),
            )
        )
        active_configs = list(configs.scalars().all())

        today = date.today()
        date_from = (today - timedelta(days=7)).isoformat()
        date_to = today.isoformat()

        results: list[OptimizationResult] = []
        for config in active_configs:
            try:
                result = await optimize_campaign(
                    config, access_token, date_from, date_to
                )
                results.append(result)
            except Exception as e:
                logger.error(
                    "Optimierung fehlgeschlagen für {id}: {err}",
                    id=config.campaign_id,
                    err=str(e),
                )
                results.append(
                    OptimizationResult(
                        campaign_id=config.campaign_id,
                        campaign_name=config.campaign_name,
                        action="error",
                        reason=str(e),
                    )
                )

        logger.info(
            "Optimierung abgeschlossen: {count} Kampagnen (Tenant: {tenant})",
            count=len(results),
            tenant=tenant_id,
        )
        return results

    # --- Weather ---

    async def get_weather(self) -> dict:
        """Get current weather data."""
        from app.campaigns.optimizer import DEFAULT_LAT, DEFAULT_LON

        if not settings.openweather_api_key:
            raise ValidationError("OpenWeather API Key nicht konfiguriert")
        weather = await get_current_weather(
            DEFAULT_LAT, DEFAULT_LON, settings.openweather_api_key
        )
        return weather.model_dump()
