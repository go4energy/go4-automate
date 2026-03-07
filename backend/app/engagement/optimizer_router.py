"""
Optimization Engine Router

API endpoints for pipeline optimization analysis.
Handles report generation, insights, and recommendation application.

Endpoints:
    POST /pipelines/{id}/analyze     - Analyze a pipeline
    GET  /reports                    - List reports
    GET  /reports/{id}               - Get report details
    POST /reports/{id}/apply         - Apply recommendations
    GET  /insights                   - List insights
    GET  /stats                      - Get optimization stats
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.database import get_db
from app.engagement.optimizer_schemas import (
    AnalyzePipelineRequest,
    OptimizationInsightList,
    OptimizationInsightResponse,
    OptimizationReportDetail,
    OptimizationReportList,
    OptimizationReportResponse,
    OptimizationStats,
)
from app.engagement.optimizer_service import OptimizationEngine
from app.services.llm import LLMService
from app.utils.dependencies import get_current_tenant_id

router = APIRouter(prefix="/optimization", tags=["optimization"])


# ============== Dependencies ==============


async def get_optimizer(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> OptimizationEngine:
    """Get OptimizationEngine instance."""
    import contextlib

    # Try to get LLM service if available
    llm_service = None
    with contextlib.suppress(Exception):
        llm_service = LLMService(db, tenant_id)

    return OptimizationEngine(db, tenant_id, llm_service)


# ============== Analyze Pipeline ==============


@router.post(
    "/pipelines/{pipeline_id}/analyze",
    response_model=OptimizationReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Analyze Pipeline",
    description="Run optimization analysis on a pipeline.",
)
async def analyze_pipeline(
    pipeline_id: int,
    request: AnalyzePipelineRequest,
    optimizer: OptimizationEngine = Depends(get_optimizer),
) -> OptimizationReportResponse:
    """
    Analyze a pipeline for optimization opportunities.

    Generates a report with patterns, insights, and recommendations.
    """
    try:
        report = await optimizer.analyze_pipeline(
            pipeline_id=pipeline_id,
            report_type=request.report_type.value,
            days=request.days,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    return OptimizationReportResponse(
        id=report.id,
        pipeline_id=report.pipeline_id,
        pipeline_name=report.pipeline.name if report.pipeline else None,
        report_type=report.report_type,
        analysis_period_start=report.analysis_period_start,
        analysis_period_end=report.analysis_period_end,
        total_enrollments=report.total_enrollments,
        completed_enrollments=report.completed_enrollments,
        successful_enrollments=report.successful_enrollments,
        conversion_rate=float(report.conversion_rate),
        avg_touches_to_conversion=(
            float(report.avg_touches_to_conversion)
            if report.avg_touches_to_conversion
            else None
        ),
        avg_days_to_conversion=(
            float(report.avg_days_to_conversion)
            if report.avg_days_to_conversion
            else None
        ),
        channel_stats=report.channel_stats,
        stage_progression=report.stage_progression,
        patterns_found=report.patterns_found,
        recommendations=report.recommendations,
        status=report.status,
        error_message=report.error_message,
        applied_at=report.applied_at,
        applied_by=report.applied_by,
        suggested_playbook_changes=report.suggested_playbook_changes,
        created_at=report.created_at,
        completed_at=report.completed_at,
        insights_count=len(report.insights) if report.insights else 0,
    )


# ============== Reports ==============


@router.get(
    "/reports",
    response_model=OptimizationReportList,
    summary="List Reports",
    description="Get all optimization reports.",
)
async def list_reports(
    pipeline_id: int | None = Query(None, description="Filter by pipeline"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    optimizer: OptimizationEngine = Depends(get_optimizer),
) -> OptimizationReportList:
    """
    List optimization reports.

    Returns paginated list of reports with basic info.
    """
    reports, total = await optimizer.list_reports(
        pipeline_id=pipeline_id,
        limit=limit,
        offset=offset,
    )

    items = []
    for report in reports:
        items.append(
            OptimizationReportResponse(
                id=report.id,
                pipeline_id=report.pipeline_id,
                pipeline_name=report.pipeline.name if report.pipeline else None,
                report_type=report.report_type,
                analysis_period_start=report.analysis_period_start,
                analysis_period_end=report.analysis_period_end,
                total_enrollments=report.total_enrollments,
                completed_enrollments=report.completed_enrollments,
                successful_enrollments=report.successful_enrollments,
                conversion_rate=float(report.conversion_rate),
                avg_touches_to_conversion=(
                    float(report.avg_touches_to_conversion)
                    if report.avg_touches_to_conversion
                    else None
                ),
                avg_days_to_conversion=(
                    float(report.avg_days_to_conversion)
                    if report.avg_days_to_conversion
                    else None
                ),
                channel_stats=report.channel_stats,
                stage_progression=report.stage_progression,
                patterns_found=report.patterns_found,
                recommendations=report.recommendations,
                status=report.status,
                error_message=report.error_message,
                applied_at=report.applied_at,
                applied_by=report.applied_by,
                suggested_playbook_changes=report.suggested_playbook_changes,
                created_at=report.created_at,
                completed_at=report.completed_at,
            )
        )

    return OptimizationReportList(items=items, total=total)


@router.get(
    "/reports/{report_id}",
    response_model=OptimizationReportDetail,
    summary="Get Report",
    description="Get detailed optimization report with insights.",
)
async def get_report(
    report_id: int,
    optimizer: OptimizationEngine = Depends(get_optimizer),
) -> OptimizationReportDetail:
    """
    Get a detailed optimization report.

    Includes all insights and recommendations.
    """
    report = await optimizer.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    insights = [
        OptimizationInsightResponse(
            id=i.id,
            insight_type=i.insight_type,
            category=i.category,
            title=i.title,
            description=i.description,
            priority=i.priority,
            confidence=float(i.confidence),
            estimated_impact=i.estimated_impact,
            suggested_action=i.suggested_action,
            is_actionable=i.is_actionable,
            is_applied=i.is_applied,
            applied_at=i.applied_at,
            created_at=i.created_at,
        )
        for i in (report.insights or [])
    ]

    return OptimizationReportDetail(
        id=report.id,
        pipeline_id=report.pipeline_id,
        pipeline_name=report.pipeline.name if report.pipeline else None,
        report_type=report.report_type,
        analysis_period_start=report.analysis_period_start,
        analysis_period_end=report.analysis_period_end,
        total_enrollments=report.total_enrollments,
        completed_enrollments=report.completed_enrollments,
        successful_enrollments=report.successful_enrollments,
        conversion_rate=float(report.conversion_rate),
        avg_touches_to_conversion=(
            float(report.avg_touches_to_conversion)
            if report.avg_touches_to_conversion
            else None
        ),
        avg_days_to_conversion=(
            float(report.avg_days_to_conversion)
            if report.avg_days_to_conversion
            else None
        ),
        channel_stats=report.channel_stats,
        stage_progression=report.stage_progression,
        patterns_found=report.patterns_found,
        recommendations=report.recommendations,
        status=report.status,
        error_message=report.error_message,
        applied_at=report.applied_at,
        applied_by=report.applied_by,
        suggested_playbook_changes=report.suggested_playbook_changes,
        created_at=report.created_at,
        completed_at=report.completed_at,
        insights_count=len(insights),
        insights=insights,
    )


@router.post(
    "/reports/{report_id}/apply",
    response_model=dict,
    summary="Apply Recommendations",
    description="Apply recommendations from a report to the pipeline.",
)
async def apply_recommendations(
    report_id: int,
    user: User = Depends(get_current_user),
    optimizer: OptimizationEngine = Depends(get_optimizer),
) -> dict:
    """
    Apply recommendations from a report.

    Updates the pipeline playbook with suggested changes.
    """
    try:
        pipeline = await optimizer.apply_recommendations(report_id, user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    return {
        "success": True,
        "message": f"Empfehlungen auf Pipeline '{pipeline.name}' angewendet",
        "pipeline_id": pipeline.id,
    }


# ============== Insights ==============


@router.get(
    "/insights",
    response_model=OptimizationInsightList,
    summary="List Insights",
    description="Get optimization insights across all reports.",
)
async def list_insights(
    report_id: int | None = Query(None, description="Filter by report"),
    insight_type: str | None = Query(None, description="Filter by type"),
    priority: str | None = Query(None, description="Filter by priority"),
    limit: int = Query(50, ge=1, le=200),
    optimizer: OptimizationEngine = Depends(get_optimizer),
) -> OptimizationInsightList:
    """
    List optimization insights.

    Can filter by report, type, or priority.
    """
    insights = await optimizer.get_insights(
        report_id=report_id,
        insight_type=insight_type,
        priority=priority,
        limit=limit,
    )

    items = [
        OptimizationInsightResponse(
            id=i.id,
            insight_type=i.insight_type,
            category=i.category,
            title=i.title,
            description=i.description,
            priority=i.priority,
            confidence=float(i.confidence),
            estimated_impact=i.estimated_impact,
            suggested_action=i.suggested_action,
            is_actionable=i.is_actionable,
            is_applied=i.is_applied,
            applied_at=i.applied_at,
            created_at=i.created_at,
        )
        for i in insights
    ]

    return OptimizationInsightList(items=items, total=len(items))


# ============== Stats ==============


@router.get(
    "/stats",
    response_model=OptimizationStats,
    summary="Get Stats",
    description="Get optimization statistics dashboard.",
)
async def get_stats(
    optimizer: OptimizationEngine = Depends(get_optimizer),
) -> OptimizationStats:
    """
    Get optimization statistics.

    Overview of all optimization activity.
    """
    # Get all reports
    reports, total_reports = await optimizer.list_reports(limit=1000)

    # Calculate stats
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    reports_this_month = sum(1 for r in reports if r.created_at >= month_start)

    # Average conversion rate
    rates = [float(r.conversion_rate) for r in reports if r.conversion_rate]
    avg_rate = sum(rates) / len(rates) if rates else 0

    # Best/worst pipelines
    pipeline_rates = {}
    for r in reports:
        if r.pipeline:
            name = r.pipeline.name
            if name not in pipeline_rates:
                pipeline_rates[name] = []
            pipeline_rates[name].append(float(r.conversion_rate))

    best_pipeline = None
    worst_pipeline = None
    if pipeline_rates:
        avg_by_pipeline = {
            name: sum(rates) / len(rates) for name, rates in pipeline_rates.items()
        }
        best_pipeline = max(avg_by_pipeline, key=avg_by_pipeline.get)
        worst_pipeline = min(avg_by_pipeline, key=avg_by_pipeline.get)

    # Recommendations
    total_recs = sum(len(r.recommendations or []) for r in reports)
    applied_recs = sum(1 for r in reports if r.applied_at)

    # High priority insights
    insights = await optimizer.get_insights(priority="high", limit=1000)
    high_priority = len(insights)

    return OptimizationStats(
        total_reports=total_reports,
        reports_this_month=reports_this_month,
        avg_conversion_rate=round(avg_rate, 2),
        best_performing_pipeline=best_pipeline,
        worst_performing_pipeline=worst_pipeline,
        total_recommendations=total_recs,
        applied_recommendations=applied_recs,
        high_priority_insights=high_priority,
    )
