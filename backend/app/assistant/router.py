"""Assistant module API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.schemas import (
    AssistantActionResponse,
    AssistantDecisionResponse,
    AssistantFeedbackCreate,
    AssistantFeedbackResponse,
    AssistantItemResponse,
    AssistantProfileResponse,
    AssistantProfileUpdate,
    AssistantRuleCreate,
    AssistantRuleResponse,
    AssistantRuleUpdate,
    AssistantSourceCreate,
    AssistantSourceResponse,
    AssistantSourceUpdate,
    BriefingRunRequest,
    BriefingRunResponse,
)
from app.assistant.service import AssistantService
from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.database import get_db
from app.exceptions import AppError
from app.utils.dependencies import get_current_tenant_id

router = APIRouter(prefix="/assistant", tags=["assistant"])


# Register module interface endpoints (config, status, metrics)
try:
    from app.assistant.config_schema import interface as assistant_interface

    assistant_interface.register_endpoints(router)
except Exception:
    pass


def _svc(db: AsyncSession) -> AssistantService:
    return AssistantService(db)


# ── Profile ──────────────────────────────────────────────────────────


@router.get("/profile", response_model=AssistantProfileResponse)
async def get_profile(
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get or create the current user's assistant profile."""
    try:
        return await _svc(db).get_or_create_profile(tenant_id, user.id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.put("/profile", response_model=AssistantProfileResponse)
async def update_profile(
    data: AssistantProfileUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the current user's assistant profile."""
    try:
        return await _svc(db).update_profile(
            tenant_id, user.id, data.model_dump(exclude_unset=True)
        )
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


# ── Sources ──────────────────────────────────────────────────────────


@router.get("/sources", response_model=list[AssistantSourceResponse])
async def list_sources(
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all connected sources for the assistant."""
    return await _svc(db).list_sources(tenant_id, user.id)


@router.post(
    "/sources",
    response_model=AssistantSourceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_source(
    data: AssistantSourceCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add an integration connection as assistant source."""
    try:
        return await _svc(db).add_source(tenant_id, user.id, data.model_dump())
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.put("/sources/{source_id}", response_model=AssistantSourceResponse)
async def update_source(
    source_id: int,
    data: AssistantSourceUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an assistant source."""
    try:
        return await _svc(db).update_source(
            tenant_id, user.id, source_id, data.model_dump(exclude_unset=True)
        )
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.delete("/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(
    source_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove an assistant source."""
    try:
        await _svc(db).delete_source(tenant_id, user.id, source_id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


# ── Items ────────────────────────────────────────────────────────────


@router.get("/items", response_model=list[AssistantItemResponse])
async def list_items(
    status_filter: str | None = Query(None, alias="status"),
    item_type: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List normalised items."""
    return await _svc(db).list_items(
        tenant_id,
        user.id,
        status=status_filter,
        item_type=item_type,
        limit=limit,
        offset=offset,
    )


@router.get("/items/{item_id}", response_model=AssistantItemResponse)
async def get_item(
    item_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single item."""
    try:
        return await _svc(db).get_item(tenant_id, user.id, item_id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get(
    "/items/{item_id}/decisions",
    response_model=list[AssistantDecisionResponse],
)
async def list_item_decisions(
    item_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List classification decisions for an item."""
    try:
        return await _svc(db).list_decisions_for_item(tenant_id, user.id, item_id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


# ── Feedback ─────────────────────────────────────────────────────────


@router.post(
    "/items/{item_id}/feedback",
    response_model=AssistantFeedbackResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_feedback(
    item_id: int,
    data: AssistantFeedbackCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record feedback on an item (for learning)."""
    try:
        return await _svc(db).add_feedback(
            tenant_id, user.id, item_id, data.model_dump()
        )
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


# ── Rules ────────────────────────────────────────────────────────────


@router.get("/rules", response_model=list[AssistantRuleResponse])
async def list_rules(
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all rules."""
    return await _svc(db).list_rules(tenant_id, user.id)


@router.post(
    "/rules",
    response_model=AssistantRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_rule(
    data: AssistantRuleCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a triage rule."""
    try:
        return await _svc(db).create_rule(tenant_id, user.id, data.model_dump())
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.put("/rules/{rule_id}", response_model=AssistantRuleResponse)
async def update_rule(
    rule_id: int,
    data: AssistantRuleUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a rule."""
    try:
        return await _svc(db).update_rule(
            tenant_id, user.id, rule_id, data.model_dump(exclude_unset=True)
        )
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    rule_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a rule."""
    try:
        await _svc(db).delete_rule(tenant_id, user.id, rule_id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


# ── Rule Suggestions / Learning ───────────────────────────────────────


@router.get("/rule-suggestions")
async def get_rule_suggestions(
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get AI-suggested rules based on user feedback patterns."""
    from app.assistant.learning import AssistantLearningService

    try:
        service = AssistantLearningService(db)
        return await service.suggest_rules(tenant_id, user.id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.post("/rule-suggestions/apply", response_model=AssistantRuleResponse)
async def apply_rule_suggestion(
    suggestion: dict,
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Apply a rule suggestion (save as learned rule)."""
    from app.assistant.learning import AssistantLearningService

    try:
        service = AssistantLearningService(db)
        return await service.apply_suggestion(tenant_id, user.id, suggestion)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


# ── Actions / Approvals ──────────────────────────────────────────────


@router.get("/actions/pending", response_model=list[AssistantActionResponse])
async def list_pending_actions(
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List actions awaiting approval."""
    return await _svc(db).list_pending_actions(tenant_id, user.id)


@router.post(
    "/actions/{action_id}/approve",
    response_model=AssistantActionResponse,
)
async def approve_action(
    action_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve a pending action."""
    try:
        return await _svc(db).approve_action(tenant_id, user.id, action_id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.post(
    "/actions/{action_id}/reject",
    response_model=AssistantActionResponse,
)
async def reject_action(
    action_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reject a pending action."""
    try:
        return await _svc(db).reject_action(tenant_id, user.id, action_id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


# ── Dashboard ────────────────────────────────────────────────────────


# ── Briefing ─────────────────────────────────────────────────────────


@router.post("/briefing/run", response_model=BriefingRunResponse)
async def run_briefing(
    data: BriefingRunRequest | None = None,
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger a briefing run."""
    try:
        max_items = data.max_items if data and data.max_items else 30
        return await _svc(db).run_briefing(tenant_id, user.id, max_items)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


# ── Dashboard ────────────────────────────────────────────────────────


@router.get("/dashboard")
async def get_dashboard(
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Quick dashboard stats."""
    try:
        return await _svc(db).get_dashboard_stats(tenant_id, user.id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
