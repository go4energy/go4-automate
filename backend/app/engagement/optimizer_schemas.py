"""
Optimization Engine Schemas

Pydantic schemas for optimization API endpoints.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

# ============== Enums ==============


class ReportTypeEnum(str, Enum):
    """Report type options."""

    WEEKLY = "weekly"
    MONTHLY = "monthly"
    AD_HOC = "ad_hoc"


class ReportStatusEnum(str, Enum):
    """Report status options."""

    PENDING = "pending"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class InsightTypeEnum(str, Enum):
    """Insight type options."""

    PATTERN = "pattern"
    RECOMMENDATION = "recommendation"
    WARNING = "warning"
    OPPORTUNITY = "opportunity"


class InsightCategoryEnum(str, Enum):
    """Insight category options."""

    CHANNEL = "channel"
    TIMING = "timing"
    CONTENT = "content"
    TARGETING = "targeting"
    SEQUENCE = "sequence"


class PriorityEnum(str, Enum):
    """Priority options."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ============== Request Schemas ==============


class AnalyzePipelineRequest(BaseModel):
    """Request to analyze a pipeline."""

    report_type: ReportTypeEnum = Field(
        ReportTypeEnum.AD_HOC, description="Type of report to generate"
    )
    days: int = Field(30, ge=7, le=365, description="Number of days to analyze")


class ApplyRecommendationsRequest(BaseModel):
    """Request to apply recommendations."""

    # No fields needed, just triggers application


# ============== Response Schemas ==============


class ChannelStatResponse(BaseModel):
    """Statistics for a single channel."""

    total: int
    outbound: int
    inbound: int
    response_rate: float
    positive_sentiment: int


class StageProgressionResponse(BaseModel):
    """Progression statistics for a stage."""

    count: int
    percentage: float


class PatternResponse(BaseModel):
    """Pattern found in analysis."""

    type: str
    description: str
    data: dict | None = None


class RecommendationResponse(BaseModel):
    """Recommendation from analysis."""

    title: str
    description: str
    priority: str | None = None
    expected_impact: str | None = None


class OptimizationInsightResponse(BaseModel):
    """Response for an optimization insight."""

    id: int
    insight_type: str
    category: str
    title: str
    description: str
    priority: str
    confidence: float
    estimated_impact: str | None
    suggested_action: str | None
    is_actionable: bool
    is_applied: bool
    applied_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OptimizationReportResponse(BaseModel):
    """Response for an optimization report."""

    id: int
    pipeline_id: int
    pipeline_name: str | None = None
    report_type: str
    analysis_period_start: datetime
    analysis_period_end: datetime

    # Metrics
    total_enrollments: int
    completed_enrollments: int
    successful_enrollments: int
    conversion_rate: float
    avg_touches_to_conversion: float | None
    avg_days_to_conversion: float | None

    # Analysis Results
    channel_stats: dict
    stage_progression: dict
    patterns_found: list
    recommendations: list

    # Status
    status: str
    error_message: str | None

    # Application
    applied_at: datetime | None
    applied_by: int | None
    suggested_playbook_changes: str | None

    # Lifecycle
    created_at: datetime
    completed_at: datetime | None

    # Insights count
    insights_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class OptimizationReportDetail(OptimizationReportResponse):
    """Detailed report response including insights."""

    insights: list[OptimizationInsightResponse] = []


class OptimizationReportList(BaseModel):
    """Paginated list of reports."""

    items: list[OptimizationReportResponse]
    total: int


class OptimizationInsightList(BaseModel):
    """List of insights."""

    items: list[OptimizationInsightResponse]
    total: int


# ============== Dashboard Stats ==============


class OptimizationStats(BaseModel):
    """Statistics for optimization dashboard."""

    total_reports: int
    reports_this_month: int
    avg_conversion_rate: float
    best_performing_pipeline: str | None
    worst_performing_pipeline: str | None
    total_recommendations: int
    applied_recommendations: int
    high_priority_insights: int


class PipelinePerformance(BaseModel):
    """Performance summary for a pipeline."""

    pipeline_id: int
    pipeline_name: str
    conversion_rate: float
    trend: str  # up, down, stable
    last_analysis_at: datetime | None
    insights_count: int
