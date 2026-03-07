"""Tests for the Optimization Engine."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.engagement.optimizer_models import (
    InsightCategory,
    InsightType,
    OptimizationInsight,
    OptimizationReport,
    ReportType,
)
from app.engagement.optimizer_service import OptimizationEngine


class TestOptimizationEngine:
    """Test suite for OptimizationEngine."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        session = MagicMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.commit = AsyncMock()
        session.add = MagicMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM service."""
        llm = MagicMock()
        llm.generate_json = AsyncMock(
            return_value={
                "insights": [
                    {
                        "type": "pattern",
                        "category": "channel",
                        "title": "LinkedIn funktioniert am besten",
                        "description": "LinkedIn hat die hoechste Response-Rate",
                        "priority": "high",
                        "confidence": 0.85,
                        "estimated_impact": "20% mehr Conversions",
                        "suggested_action": "Mehr Fokus auf LinkedIn",
                    }
                ],
                "playbook_suggestions": "Fokus auf LinkedIn-Nachrichten am Vormittag.",
            }
        )
        return llm

    @pytest.fixture
    def engine(self, mock_db, mock_llm):
        """Create an OptimizationEngine instance."""
        return OptimizationEngine(mock_db, "test-tenant", mock_llm)

    @pytest.fixture
    def engine_no_llm(self, mock_db):
        """Create an OptimizationEngine instance without LLM."""
        return OptimizationEngine(mock_db, "test-tenant", None)

    # ============== Basic Tests ==============

    def test_engine_initialization(self, engine, mock_db, mock_llm):
        """Test engine initialization."""
        assert engine.db == mock_db
        assert engine.tenant_id == "test-tenant"
        assert engine.llm == mock_llm

    def test_engine_without_llm(self, engine_no_llm, mock_db):
        """Test engine can be created without LLM service."""
        assert engine_no_llm.db == mock_db
        assert engine_no_llm.llm is None

    # ============== Metric Calculation Tests ==============

    def test_calculate_metrics_empty(self, engine):
        """Test metric calculation with no data."""
        metrics = engine._calculate_metrics([], [])

        assert metrics["total"] == 0
        assert metrics["completed"] == 0
        assert metrics["successful"] == 0
        assert metrics["conversion_rate"] == 0

    def test_calculate_metrics_with_enrollments(self, engine):
        """Test metric calculation with enrollments."""
        # Create mock enrollments
        enrollments = []
        for i in range(10):
            e = MagicMock()
            e.status = "completed" if i < 7 else "active"
            e.outcome = "converted" if i < 3 else ("lost" if i < 7 else None)
            e.touch_count = i + 1
            e.stage = "converted" if i < 3 else "lead"
            e.created_at = datetime.now(UTC) - timedelta(days=30 - i)
            e.completed_at = (
                datetime.now(UTC) - timedelta(days=5) if e.outcome else None
            )
            enrollments.append(e)

        # Create mock activities
        activities = []
        for i in range(20):
            a = MagicMock()
            a.channel = "linkedin" if i < 10 else "email"
            a.direction = "outbound" if i % 2 == 0 else "inbound"
            a.sentiment = "positive" if i % 3 == 0 else "neutral"
            activities.append(a)

        metrics = engine._calculate_metrics(enrollments, activities)

        assert metrics["total"] == 10
        assert metrics["completed"] == 7  # 7 with completed status
        assert metrics["successful"] == 3  # 3 converted
        assert metrics["conversion_rate"] == 30.0  # 3/10 * 100

    def test_calculate_metrics_channel_stats(self, engine):
        """Test channel statistics calculation."""
        enrollments = []

        activities = []
        for i in range(10):
            a = MagicMock()
            a.channel = "linkedin"
            a.direction = "outbound" if i < 7 else "inbound"
            a.sentiment = "positive" if i >= 7 else "neutral"
            activities.append(a)

        metrics = engine._calculate_metrics(enrollments, activities)

        assert "linkedin" in metrics["channel_stats"]
        linkedin = metrics["channel_stats"]["linkedin"]
        assert linkedin["total"] == 10
        assert linkedin["outbound"] == 7
        assert linkedin["inbound"] == 3
        assert linkedin["positive_sentiment"] == 3

    # ============== Pattern Extraction Tests ==============

    def test_extract_patterns_empty(self, engine):
        """Test pattern extraction with no data."""
        patterns = engine._extract_patterns([], [], {})
        assert len(patterns) == 0

    def test_extract_patterns_with_conversions(self, engine):
        """Test pattern extraction with successful conversions."""
        # Create mock enrollments with some conversions
        enrollments = []
        for i in range(10):
            e = MagicMock()
            e.outcome = "converted" if i < 4 else "lost"
            e.touch_count = 3 if i < 4 else 5
            e.contact_id = i + 1
            enrollments.append(e)

        # Create mock activities
        activities = []
        for i in range(4):
            a = MagicMock()
            a.channel = "linkedin"
            a.direction = "outbound"
            a.contact_id = i + 1
            a.created_at = datetime.now(UTC) - timedelta(days=30 - i)
            activities.append(a)

        metrics = {
            "channel_stats": {
                "linkedin": {"response_rate": 25.0, "total": 10},
            },
            "stage_progression": {
                "lead": {"count": 10, "percentage": 100},
                "contacted": {"count": 8, "percentage": 80},
            },
        }

        patterns = engine._extract_patterns(enrollments, activities, metrics)

        # Should have patterns for touch count and first touch
        assert len(patterns) > 0
        pattern_types = [p["type"] for p in patterns]
        assert "touch_count" in pattern_types

    def test_extract_patterns_response_rate(self, engine):
        """Test response rate pattern detection."""
        # Create mock enrollments with conversions
        enrollments = []
        for i in range(5):
            e = MagicMock()
            e.outcome = "converted"
            e.touch_count = 3
            e.contact_id = i + 1
            enrollments.append(e)

        activities = []
        for i in range(5):
            a = MagicMock()
            a.channel = "linkedin"
            a.direction = "outbound"
            a.contact_id = i + 1
            a.created_at = datetime.now(UTC) - timedelta(days=30 - i)
            activities.append(a)

        metrics = {
            "channel_stats": {
                "linkedin": {"response_rate": 30.0, "total": 50},
                "email": {"response_rate": 10.0, "total": 50},
            },
            "stage_progression": {},
        }

        patterns = engine._extract_patterns(enrollments, activities, metrics)

        # Should detect response rate pattern
        response_patterns = [p for p in patterns if p["type"] == "response_rate"]
        assert len(response_patterns) > 0
        assert response_patterns[0]["data"]["channel"] == "linkedin"

    # ============== Rule-Based Recommendations Tests ==============

    def test_generate_rule_based_recommendations_low_conversion(self, engine_no_llm):
        """Test rule-based recommendations for low conversion."""
        metrics = {
            "conversion_rate": 5.0,  # Low conversion
            "channel_stats": {},
        }
        patterns = [{"type": "low_conversion", "description": "Test"}]

        recs = engine_no_llm._generate_rule_based_recommendations(metrics, patterns)

        # Should have recommendations
        assert isinstance(recs, list)

    def test_generate_rule_based_recommendations_channel_focus(self, engine_no_llm):
        """Test rule-based recommendations for channel focus."""
        metrics = {
            "conversion_rate": 20.0,
            "channel_stats": {
                "linkedin": {"response_rate": 30.0},
                "email": {"response_rate": 5.0},
            },
        }
        patterns = [
            {
                "type": "response_rate",
                "data": {"channel": "linkedin", "response_rate": 30.0},
                "description": "LinkedIn hat hohe Response-Rate",
            }
        ]

        recs = engine_no_llm._generate_rule_based_recommendations(metrics, patterns)

        assert isinstance(recs, list)

    # ============== Report Model Tests ==============

    def test_optimization_report_model(self):
        """Test OptimizationReport model creation."""
        report = OptimizationReport(
            tenant_id="test-tenant",
            pipeline_id=1,
            report_type=ReportType.AD_HOC,
            analysis_period_start=datetime.now(UTC) - timedelta(days=30),
            analysis_period_end=datetime.now(UTC),
            total_enrollments=100,
            completed_enrollments=80,
            successful_enrollments=20,
            conversion_rate=Decimal("0.20"),
            status="completed",
        )

        assert report.tenant_id == "test-tenant"
        assert report.pipeline_id == 1
        assert report.report_type == ReportType.AD_HOC
        assert report.total_enrollments == 100
        assert report.conversion_rate == Decimal("0.20")

    def test_optimization_insight_model(self):
        """Test OptimizationInsight model creation."""
        insight = OptimizationInsight(
            tenant_id="test-tenant",
            report_id=1,
            insight_type=InsightType.PATTERN,
            category=InsightCategory.CHANNEL,
            title="LinkedIn funktioniert am besten",
            description="LinkedIn hat die hoechste Response-Rate",
            priority="high",
            confidence=Decimal("0.85"),
            estimated_impact="20% mehr Conversions",
            suggested_action="Mehr Fokus auf LinkedIn",
            is_actionable=True,
        )

        assert insight.insight_type == InsightType.PATTERN
        assert insight.category == InsightCategory.CHANNEL
        assert insight.priority == "high"
        assert insight.confidence == Decimal("0.85")

    # ============== Enum Tests ==============

    def test_report_type_enum(self):
        """Test ReportType enum values."""
        assert ReportType.WEEKLY == "weekly"
        assert ReportType.MONTHLY == "monthly"
        assert ReportType.AD_HOC == "ad_hoc"

    def test_insight_type_enum(self):
        """Test InsightType enum values."""
        assert InsightType.PATTERN == "pattern"
        assert InsightType.RECOMMENDATION == "recommendation"
        assert InsightType.WARNING == "warning"
        assert InsightType.OPPORTUNITY == "opportunity"

    def test_insight_category_enum(self):
        """Test InsightCategory enum values."""
        assert InsightCategory.CHANNEL == "channel"
        assert InsightCategory.TIMING == "timing"
        assert InsightCategory.CONTENT == "content"
        assert InsightCategory.TARGETING == "targeting"
        assert InsightCategory.SEQUENCE == "sequence"


class TestOptimizationEngineEdgeCases:
    """Edge case tests for OptimizationEngine."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        session = MagicMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.commit = AsyncMock()
        session.add = MagicMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def engine(self, mock_db):
        """Create an OptimizationEngine instance without LLM."""
        return OptimizationEngine(mock_db, "test-tenant", None)

    def test_metrics_with_zero_completed(self, engine):
        """Test metrics calculation with no completed enrollments."""
        enrollments = []
        for i in range(5):
            e = MagicMock()
            e.status = "active"  # Not completed
            e.outcome = None  # Not completed
            e.touch_count = i + 1
            e.stage = "lead"
            e.created_at = datetime.now(UTC)
            e.completed_at = None
            enrollments.append(e)

        metrics = engine._calculate_metrics(enrollments, [])

        assert metrics["completed"] == 0
        assert metrics["conversion_rate"] == 0
        assert metrics["avg_touches"] is None

    def test_metrics_all_converted(self, engine):
        """Test metrics calculation when all enrollments converted."""
        enrollments = []
        for _ in range(10):
            e = MagicMock()
            e.status = "completed"
            e.outcome = "converted"
            e.touch_count = 3
            e.stage = "converted"
            e.created_at = datetime.now(UTC) - timedelta(days=10)
            e.completed_at = datetime.now(UTC)
            enrollments.append(e)

        metrics = engine._calculate_metrics(enrollments, [])

        assert metrics["successful"] == 10
        assert metrics["conversion_rate"] == 100.0

    def test_channel_stats_single_channel(self, engine):
        """Test channel stats with only one channel."""
        activities = []
        for _ in range(10):
            a = MagicMock()
            a.channel = "email"
            a.direction = "outbound"
            a.sentiment = "neutral"
            activities.append(a)

        metrics = engine._calculate_metrics([], activities)

        assert len(metrics["channel_stats"]) == 1
        assert "email" in metrics["channel_stats"]
        assert metrics["channel_stats"]["email"]["total"] == 10

    def test_recommendations_with_no_patterns(self, engine):
        """Test recommendations generation with no patterns."""
        metrics = {
            "conversion_rate": 50.0,  # Good conversion
            "channel_stats": {},
        }
        patterns = []

        recs = engine._generate_rule_based_recommendations(metrics, patterns)

        # Should still generate some basic recommendations
        assert isinstance(recs, list)


class TestOptimizationSchemas:
    """Tests for optimization schemas."""

    def test_report_type_enum_schema(self):
        """Test ReportTypeEnum from schemas."""
        from app.engagement.optimizer_schemas import ReportTypeEnum

        assert ReportTypeEnum.WEEKLY.value == "weekly"
        assert ReportTypeEnum.MONTHLY.value == "monthly"
        assert ReportTypeEnum.AD_HOC.value == "ad_hoc"

    def test_analyze_pipeline_request(self):
        """Test AnalyzePipelineRequest schema."""
        from app.engagement.optimizer_schemas import AnalyzePipelineRequest

        request = AnalyzePipelineRequest(report_type="weekly", days=60)
        assert request.report_type.value == "weekly"
        assert request.days == 60

    def test_analyze_pipeline_request_defaults(self):
        """Test AnalyzePipelineRequest default values."""
        from app.engagement.optimizer_schemas import AnalyzePipelineRequest

        request = AnalyzePipelineRequest()
        assert request.report_type.value == "ad_hoc"
        assert request.days == 30

    def test_optimization_stats_schema(self):
        """Test OptimizationStats schema."""
        from app.engagement.optimizer_schemas import OptimizationStats

        stats = OptimizationStats(
            total_reports=10,
            reports_this_month=3,
            avg_conversion_rate=0.25,
            best_performing_pipeline="Solar KMU",
            worst_performing_pipeline="Test Pipeline",
            total_recommendations=50,
            applied_recommendations=20,
            high_priority_insights=5,
        )

        assert stats.total_reports == 10
        assert stats.avg_conversion_rate == 0.25
        assert stats.best_performing_pipeline == "Solar KMU"

    def test_insight_response_schema(self):
        """Test OptimizationInsightResponse schema."""
        from app.engagement.optimizer_schemas import OptimizationInsightResponse

        insight = OptimizationInsightResponse(
            id=1,
            insight_type="pattern",
            category="channel",
            title="LinkedIn funktioniert gut",
            description="Hohe Response-Rate auf LinkedIn",
            priority="high",
            confidence=0.85,
            estimated_impact="20% mehr Conversions",
            suggested_action="Mehr LinkedIn-Nachrichten",
            is_actionable=True,
            is_applied=False,
            applied_at=None,
            created_at=datetime.now(UTC),
        )

        assert insight.insight_type == "pattern"
        assert insight.priority == "high"
        assert insight.confidence == 0.85
