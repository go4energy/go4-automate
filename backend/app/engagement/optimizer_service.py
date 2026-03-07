"""
Optimization Engine Service

KI-gestützte Analyse von Engagement-Mustern zur automatischen
Playbook-Optimierung.

Features:
- Analyse abgeschlossener Enrollments
- Pattern-Erkennung (erfolgreiche vs. nicht erfolgreiche)
- LLM-basierte Insights und Empfehlungen
- Automatische Playbook-Anpassungen

Usage:
    engine = OptimizationEngine(db, tenant_id, llm_service)
    report = await engine.analyze_pipeline(pipeline_id)
    await engine.apply_recommendations(report.id)
"""

import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.engagement.models import (
    ContactActivity,
    EngagementPipeline,
    PipelineEnrollment,
)
from app.engagement.optimizer_models import (
    InsightCategory,
    InsightType,
    OptimizationInsight,
    OptimizationReport,
    ReportType,
)
from app.services.llm import LLMService


class OptimizationEngine:
    """
    KI-gestützte Optimization Engine für Engagement-Pipelines.

    Analysiert Enrollment-Daten, erkennt Muster und generiert
    Empfehlungen zur Verbesserung der Pipeline-Performance.

    Attributes:
        MIN_ENROLLMENTS: Minimum enrollments for meaningful analysis
        ANALYSIS_PROMPT: System prompt for LLM analysis
    """

    MIN_ENROLLMENTS = 10  # Minimum for statistical significance
    MIN_COMPLETED = 5  # Minimum completed enrollments

    def __init__(
        self,
        db: AsyncSession,
        tenant_id: str,
        llm_service: LLMService | None = None,
    ):
        """
        Initialize engine.

        Args:
            db: Database session
            tenant_id: Current tenant ID
            llm_service: Optional LLM service for AI analysis
        """
        self.db = db
        self.tenant_id = tenant_id
        self.llm = llm_service

    # ============== Pipeline Analysis ==============

    async def analyze_pipeline(
        self,
        pipeline_id: int,
        report_type: str = ReportType.AD_HOC,
        days: int = 30,
    ) -> OptimizationReport:
        """
        Analyze a pipeline and generate optimization report.

        Args:
            pipeline_id: Pipeline to analyze
            report_type: Type of report (weekly, monthly, ad_hoc)
            days: Number of days to analyze

        Returns:
            OptimizationReport with patterns and recommendations

        Raises:
            ValueError: If pipeline not found or insufficient data
        """
        # Get pipeline
        pipeline = await self._get_pipeline(pipeline_id)
        if not pipeline:
            raise ValueError(f"Pipeline {pipeline_id} not found")

        # Calculate analysis period
        period_end = datetime.now(UTC)
        period_start = period_end - timedelta(days=days)

        # Create report
        report = OptimizationReport(
            tenant_id=self.tenant_id,
            pipeline_id=pipeline_id,
            report_type=report_type,
            analysis_period_start=period_start,
            analysis_period_end=period_end,
            status="analyzing",
        )
        self.db.add(report)
        await self.db.flush()

        try:
            # Collect data
            enrollments = await self._get_enrollments(
                pipeline_id, period_start, period_end
            )
            activities = await self._get_activities(
                pipeline_id, period_start, period_end
            )

            report.total_enrollments = len(enrollments)

            # Check minimum data
            if len(enrollments) < self.MIN_ENROLLMENTS:
                report.status = "completed"
                report.completed_at = datetime.now(UTC)
                report.patterns_found = []
                report.recommendations = [
                    {
                        "type": "info",
                        "message": f"Nicht genügend Daten für Analyse. Mindestens {self.MIN_ENROLLMENTS} Enrollments benötigt.",
                    }
                ]
                await self.db.commit()
                return report

            # Calculate metrics
            metrics = self._calculate_metrics(enrollments, activities)
            report.completed_enrollments = metrics["completed"]
            report.successful_enrollments = metrics["successful"]
            report.conversion_rate = Decimal(str(metrics["conversion_rate"]))
            report.avg_touches_to_conversion = (
                Decimal(str(metrics["avg_touches"])) if metrics["avg_touches"] else None
            )
            report.avg_days_to_conversion = (
                Decimal(str(metrics["avg_days"])) if metrics["avg_days"] else None
            )
            report.channel_stats = metrics["channel_stats"]
            report.stage_progression = metrics["stage_progression"]

            # Extract patterns
            patterns = self._extract_patterns(enrollments, activities, metrics)
            report.patterns_found = patterns

            # Generate AI insights if LLM available
            if self.llm:
                (
                    insights,
                    recommendations,
                    playbook_changes,
                ) = await self._generate_ai_insights(pipeline, metrics, patterns)
                report.recommendations = recommendations
                report.suggested_playbook_changes = playbook_changes

                # Create insight records
                for insight_data in insights:
                    insight = OptimizationInsight(
                        tenant_id=self.tenant_id,
                        report_id=report.id,
                        insight_type=insight_data.get("type", InsightType.PATTERN),
                        category=insight_data.get("category", InsightCategory.CHANNEL),
                        title=insight_data.get("title", "Insight"),
                        description=insight_data.get("description", ""),
                        priority=insight_data.get("priority", "medium"),
                        confidence=Decimal(str(insight_data.get("confidence", 0.8))),
                        estimated_impact=insight_data.get("impact"),
                        supporting_data=insight_data.get("data"),
                        suggested_action=insight_data.get("action"),
                        is_actionable=insight_data.get("actionable", True),
                    )
                    self.db.add(insight)
            else:
                # Generate rule-based recommendations
                report.recommendations = self._generate_rule_based_recommendations(
                    metrics, patterns
                )

            report.status = "completed"
            report.completed_at = datetime.now(UTC)

            await self.db.commit()
            await self.db.refresh(report)

            logger.info(f"Optimization report generated for pipeline {pipeline_id}")
            return report

        except Exception as e:
            report.status = "failed"
            report.error_message = str(e)
            report.completed_at = datetime.now(UTC)
            await self.db.commit()
            logger.error(f"Optimization analysis failed: {e}")
            raise

    # ============== Data Collection ==============

    async def _get_pipeline(self, pipeline_id: int) -> EngagementPipeline | None:
        """Get pipeline by ID."""
        result = await self.db.execute(
            select(EngagementPipeline).where(
                EngagementPipeline.id == pipeline_id,
                EngagementPipeline.tenant_id == self.tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def _get_enrollments(
        self,
        pipeline_id: int,
        start: datetime,
        end: datetime,
    ) -> list[PipelineEnrollment]:
        """Get enrollments for analysis period."""
        result = await self.db.execute(
            select(PipelineEnrollment)
            .options(selectinload(PipelineEnrollment.contact))
            .where(
                PipelineEnrollment.pipeline_id == pipeline_id,
                PipelineEnrollment.tenant_id == self.tenant_id,
                PipelineEnrollment.created_at >= start,
                PipelineEnrollment.created_at <= end,
            )
        )
        return list(result.scalars().all())

    async def _get_activities(
        self,
        pipeline_id: int,
        start: datetime,
        end: datetime,
    ) -> list[ContactActivity]:
        """Get activities for analysis period."""
        result = await self.db.execute(
            select(ContactActivity).where(
                ContactActivity.pipeline_id == pipeline_id,
                ContactActivity.tenant_id == self.tenant_id,
                ContactActivity.created_at >= start,
                ContactActivity.created_at <= end,
            )
        )
        return list(result.scalars().all())

    # ============== Metrics Calculation ==============

    def _calculate_metrics(
        self,
        enrollments: list[PipelineEnrollment],
        activities: list[ContactActivity],
    ) -> dict:
        """
        Calculate key metrics from enrollments and activities.

        Returns:
            Dict with calculated metrics
        """
        # Basic counts
        total = len(enrollments)
        completed = [e for e in enrollments if e.status in ("completed", "stopped")]
        successful = [e for e in enrollments if e.outcome == "converted"]

        # Conversion rate
        conversion_rate = (len(successful) / total * 100) if total > 0 else 0

        # Average touches to conversion
        touches = [e.touch_count for e in successful if e.touch_count]
        avg_touches = sum(touches) / len(touches) if touches else None

        # Average days to conversion
        days_list = []
        for e in successful:
            if e.completed_at and e.created_at:
                days = (e.completed_at - e.created_at).days
                days_list.append(days)
        avg_days = sum(days_list) / len(days_list) if days_list else None

        # Channel stats
        channel_stats = self._calculate_channel_stats(activities)

        # Stage progression
        stage_progression = self._calculate_stage_progression(enrollments)

        return {
            "total": total,
            "completed": len(completed),
            "successful": len(successful),
            "conversion_rate": round(conversion_rate, 2),
            "avg_touches": round(avg_touches, 1) if avg_touches else None,
            "avg_days": round(avg_days, 1) if avg_days else None,
            "channel_stats": channel_stats,
            "stage_progression": stage_progression,
        }

    def _calculate_channel_stats(self, activities: list[ContactActivity]) -> dict:
        """Calculate statistics per channel."""
        stats = {}

        for activity in activities:
            channel = activity.channel or "unknown"
            if channel not in stats:
                stats[channel] = {
                    "total": 0,
                    "outbound": 0,
                    "inbound": 0,
                    "positive_sentiment": 0,
                }

            stats[channel]["total"] += 1
            if activity.direction == "outbound":
                stats[channel]["outbound"] += 1
            else:
                stats[channel]["inbound"] += 1
            if activity.sentiment == "positive":
                stats[channel]["positive_sentiment"] += 1

        # Calculate response rates
        for channel in stats:
            outbound = stats[channel]["outbound"]
            inbound = stats[channel]["inbound"]
            stats[channel]["response_rate"] = (
                round(inbound / outbound * 100, 1) if outbound > 0 else 0
            )

        return stats

    def _calculate_stage_progression(
        self, enrollments: list[PipelineEnrollment]
    ) -> dict:
        """Calculate how enrollments progress through stages."""
        stage_counts = Counter(e.stage for e in enrollments)

        # Stage order
        stages = ["lead", "contacted", "engaged", "qualified", "converted", "lost"]
        progression = {}

        for stage in stages:
            count = stage_counts.get(stage, 0)
            progression[stage] = {
                "count": count,
                "percentage": round(count / len(enrollments) * 100, 1)
                if enrollments
                else 0,
            }

        return progression

    # ============== Pattern Extraction ==============

    def _extract_patterns(
        self,
        enrollments: list[PipelineEnrollment],
        activities: list[ContactActivity],
        metrics: dict,
    ) -> list[dict]:
        """
        Extract patterns from enrollment data.

        Identifies what successful enrollments have in common.
        """
        patterns = []

        successful = [e for e in enrollments if e.outcome == "converted"]
        # Note: Could analyze failed enrollments for comparison patterns in future
        # failed = [e for e in enrollments if e.outcome in ("lost", "stopped")]

        if not successful:
            return patterns

        # Pattern 1: First touch channel
        first_touches_success = self._get_first_touch_channels(successful, activities)

        if first_touches_success:
            best_channel = max(first_touches_success, key=first_touches_success.get)
            success_rate = first_touches_success[best_channel]
            patterns.append(
                {
                    "type": "first_touch",
                    "description": f"Erstkontakt über {best_channel} führt häufiger zum Erfolg",
                    "data": {
                        "channel": best_channel,
                        "success_count": success_rate,
                        "total_success": len(successful),
                    },
                }
            )

        # Pattern 2: Optimal touch count
        touch_counts = [e.touch_count for e in successful if e.touch_count]
        if touch_counts:
            avg_touches = sum(touch_counts) / len(touch_counts)
            min_touches = min(touch_counts)
            max_touches = max(touch_counts)
            patterns.append(
                {
                    "type": "touch_count",
                    "description": f"Erfolgreiche Conversions brauchen {min_touches}-{max_touches} Touches (Durchschnitt: {avg_touches:.1f})",
                    "data": {
                        "min": min_touches,
                        "max": max_touches,
                        "avg": round(avg_touches, 1),
                    },
                }
            )

        # Pattern 3: Response rate by channel
        channel_stats = metrics.get("channel_stats", {})
        if channel_stats:
            best_response_channel = max(
                channel_stats.keys(),
                key=lambda c: channel_stats[c].get("response_rate", 0),
            )
            response_rate = channel_stats[best_response_channel].get("response_rate", 0)
            if response_rate > 0:
                patterns.append(
                    {
                        "type": "response_rate",
                        "description": f"{best_response_channel} hat die höchste Response-Rate ({response_rate}%)",
                        "data": {
                            "channel": best_response_channel,
                            "response_rate": response_rate,
                        },
                    }
                )

        # Pattern 4: Stage drop-off
        progression = metrics.get("stage_progression", {})
        if progression:
            stages = ["lead", "contacted", "engaged", "qualified"]
            for i in range(len(stages) - 1):
                current = progression.get(stages[i], {}).get("count", 0)
                next_stage = progression.get(stages[i + 1], {}).get("count", 0)
                if current > 0:
                    drop_rate = (current - next_stage) / current * 100
                    if drop_rate > 50:
                        patterns.append(
                            {
                                "type": "stage_dropoff",
                                "description": f"Hoher Drop-off zwischen {stages[i]} und {stages[i+1]} ({drop_rate:.0f}%)",
                                "data": {
                                    "from_stage": stages[i],
                                    "to_stage": stages[i + 1],
                                    "drop_rate": round(drop_rate, 1),
                                },
                            }
                        )

        return patterns

    def _get_first_touch_channels(
        self,
        enrollments: list[PipelineEnrollment],
        activities: list[ContactActivity],
    ) -> dict:
        """Get first touch channel distribution for enrollments."""
        channels = Counter()

        enrollment_ids = {e.id for e in enrollments}

        for activity in activities:
            if (
                activity.enrollment_id in enrollment_ids
                and activity.direction == "outbound"
            ):
                channels[activity.channel] += 1

        return dict(channels)

    # ============== AI Analysis ==============

    async def _generate_ai_insights(
        self,
        pipeline: EngagementPipeline,
        metrics: dict,
        patterns: list[dict],
    ) -> tuple[list[dict], list[dict], str | None]:
        """
        Generate AI-powered insights using LLM.

        Returns:
            Tuple of (insights, recommendations, playbook_changes)
        """
        if not self.llm:
            return [], [], None

        # Build analysis prompt
        prompt = f"""Analysiere diese Engagement-Pipeline-Daten und generiere Insights.

PIPELINE: {pipeline.name}
Produkt: {pipeline.product_name or 'Nicht angegeben'}
Zielgruppe: {pipeline.target_audience or 'Nicht angegeben'}
Kanäle: {', '.join(pipeline.channels or [])}

METRIKEN:
- Gesamt-Enrollments: {metrics['total']}
- Abgeschlossen: {metrics['completed']}
- Erfolgreich (Converted): {metrics['successful']}
- Conversion-Rate: {metrics['conversion_rate']}%
- Durchschnittliche Touches bis Conversion: {metrics['avg_touches'] or 'N/A'}
- Durchschnittliche Tage bis Conversion: {metrics['avg_days'] or 'N/A'}

KANAL-STATISTIKEN:
{json.dumps(metrics['channel_stats'], indent=2)}

STAGE-PROGRESSION:
{json.dumps(metrics['stage_progression'], indent=2)}

ERKANNTE MUSTER:
{json.dumps(patterns, indent=2)}

Generiere eine JSON-Antwort mit:
1. "insights": Liste von Erkenntnissen (max 5)
   - type: "pattern" | "recommendation" | "warning" | "opportunity"
   - category: "channel" | "timing" | "content" | "targeting" | "sequence"
   - title: Kurzer Titel
   - description: Ausführliche Beschreibung
   - priority: "high" | "medium" | "low"
   - confidence: 0.0-1.0
   - impact: Geschätzter Impact (z.B. "+15% Response-Rate")
   - action: Konkrete Handlungsempfehlung
   - actionable: true/false

2. "recommendations": Liste von Empfehlungen (max 3)
   - title: Kurzer Titel
   - description: Was sollte geändert werden
   - expected_impact: Erwartete Verbesserung

3. "playbook_changes": Optional, Vorgeschlagene Änderungen am Playbook (als Text)

Antworte NUR mit validem JSON."""

        try:
            response = await self.llm.generate(
                prompt=prompt,
                system_prompt="Du bist ein Engagement-Optimierungs-Experte. Analysiere Daten und gib präzise, umsetzbare Empfehlungen.",
                max_tokens=2000,
                temperature=0.5,
            )

            # Parse JSON response
            result = json.loads(response)

            insights = result.get("insights", [])
            recommendations = result.get("recommendations", [])
            playbook_changes = result.get("playbook_changes")

            return insights, recommendations, playbook_changes

        except Exception as e:
            logger.warning(f"AI analysis failed: {e}")
            return [], [], None

    def _generate_rule_based_recommendations(
        self,
        metrics: dict,
        patterns: list[dict],
    ) -> list[dict]:
        """Generate recommendations without AI using rules."""
        recommendations = []

        # Low conversion rate
        if metrics["conversion_rate"] < 10:
            recommendations.append(
                {
                    "title": "Niedrige Conversion-Rate",
                    "description": "Die Conversion-Rate liegt unter 10%. Überprüfen Sie die Zielgruppen-Definition und Messaging.",
                    "priority": "high",
                }
            )

        # High drop-off
        for pattern in patterns:
            if pattern.get("type") == "stage_dropoff":
                drop_rate = pattern.get("data", {}).get("drop_rate", 0)
                if drop_rate > 60:
                    recommendations.append(
                        {
                            "title": f"Hoher Drop-off bei {pattern['data']['from_stage']}",
                            "description": f"{drop_rate}% der Kontakte fallen zwischen {pattern['data']['from_stage']} und {pattern['data']['to_stage']} ab.",
                            "priority": "high",
                        }
                    )

        # Channel recommendation
        channel_stats = metrics.get("channel_stats", {})
        if channel_stats:
            low_response = [
                c for c, s in channel_stats.items() if s.get("response_rate", 0) < 5
            ]
            if low_response:
                recommendations.append(
                    {
                        "title": "Kanäle mit niedriger Response-Rate",
                        "description": f"Diese Kanäle haben weniger als 5% Response-Rate: {', '.join(low_response)}. Messaging überprüfen oder Kanal entfernen.",
                        "priority": "medium",
                    }
                )

        return recommendations

    # ============== Report Management ==============

    async def get_report(self, report_id: int) -> OptimizationReport | None:
        """Get report by ID."""
        result = await self.db.execute(
            select(OptimizationReport)
            .options(
                selectinload(OptimizationReport.pipeline),
                selectinload(OptimizationReport.insights),
            )
            .where(
                OptimizationReport.id == report_id,
                OptimizationReport.tenant_id == self.tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_reports(
        self,
        pipeline_id: int | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[OptimizationReport], int]:
        """List optimization reports."""
        query = select(OptimizationReport).where(
            OptimizationReport.tenant_id == self.tenant_id
        )

        if pipeline_id:
            query = query.where(OptimizationReport.pipeline_id == pipeline_id)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Fetch
        query = query.options(selectinload(OptimizationReport.pipeline))
        query = query.order_by(OptimizationReport.created_at.desc())
        query = query.limit(limit).offset(offset)

        result = await self.db.execute(query)
        reports = list(result.scalars().all())

        return reports, total

    async def get_insights(
        self,
        report_id: int | None = None,
        insight_type: str | None = None,
        priority: str | None = None,
        limit: int = 50,
    ) -> list[OptimizationInsight]:
        """Get insights with optional filters."""
        query = select(OptimizationInsight).where(
            OptimizationInsight.tenant_id == self.tenant_id
        )

        if report_id:
            query = query.where(OptimizationInsight.report_id == report_id)
        if insight_type:
            query = query.where(OptimizationInsight.insight_type == insight_type)
        if priority:
            query = query.where(OptimizationInsight.priority == priority)

        query = query.order_by(
            OptimizationInsight.priority.desc(),
            OptimizationInsight.confidence.desc(),
        )
        query = query.limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ============== Apply Recommendations ==============

    async def apply_recommendations(
        self,
        report_id: int,
        user_id: int,
    ) -> EngagementPipeline:
        """
        Apply recommendations from report to pipeline.

        Args:
            report_id: Report with recommendations
            user_id: User applying the changes

        Returns:
            Updated pipeline

        Raises:
            ValueError: If report not found or no changes to apply
        """
        report = await self.get_report(report_id)
        if not report:
            raise ValueError(f"Report {report_id} not found")

        if not report.suggested_playbook_changes:
            raise ValueError("No playbook changes suggested in this report")

        # Get pipeline
        pipeline = await self._get_pipeline(report.pipeline_id)
        if not pipeline:
            raise ValueError("Pipeline not found")

        # Apply playbook changes
        if report.suggested_playbook_changes:
            # Merge with existing playbook
            existing = pipeline.playbook or ""
            pipeline.playbook = f"{existing}\n\n--- Automatisch hinzugefügt ---\n{report.suggested_playbook_changes}"

        # Mark report as applied
        report.applied_at = datetime.now(UTC)
        report.applied_by = user_id

        # Mark insights as applied
        for insight in report.insights:
            if insight.is_actionable:
                insight.is_applied = True
                insight.applied_at = datetime.now(UTC)

        await self.db.commit()
        await self.db.refresh(pipeline)

        logger.info(
            f"Applied recommendations from report {report_id} to pipeline {pipeline.id}"
        )
        return pipeline

    # ============== Scheduled Analysis ==============

    async def run_weekly_analysis(self) -> list[OptimizationReport]:
        """
        Run weekly analysis for all active pipelines.

        Called by scheduled task.

        Returns:
            List of generated reports
        """
        # Get all active pipelines
        result = await self.db.execute(
            select(EngagementPipeline).where(
                EngagementPipeline.tenant_id == self.tenant_id,
                EngagementPipeline.is_active == True,  # noqa: E712
            )
        )
        pipelines = list(result.scalars().all())

        reports = []
        for pipeline in pipelines:
            try:
                report = await self.analyze_pipeline(
                    pipeline.id,
                    report_type=ReportType.WEEKLY,
                    days=7,
                )
                reports.append(report)
            except Exception as e:
                logger.error(f"Weekly analysis failed for pipeline {pipeline.id}: {e}")

        return reports
