"""Assistant module API endpoints."""

import base64

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.schemas import (
    AssistantActionResponse,
    AssistantCategoryCreate,
    AssistantCategoryResponse,
    AssistantCategoryUpdate,
    AssistantConversationTurnResponse,
    AssistantDecisionResponse,
    AssistantDraftResponse,
    AssistantDraftUpdate,
    AssistantFeedbackCreate,
    AssistantFeedbackResponse,
    AssistantItemResponse,
    AssistantMailboxHealthResponse,
    AssistantMailboxPolicyResponse,
    AssistantMailboxPolicySetupRequest,
    AssistantMailboxReviewItemResponse,
    AssistantPendingIntentResponse,
    AssistantProfileResponse,
    AssistantProfileUpdate,
    AssistantRuleCreate,
    AssistantRuleResponse,
    AssistantRuleUpdate,
    AssistantSourceCreate,
    AssistantSourceResponse,
    AssistantSourceUpdate,
    AssistantTempTrackingResponse,
    AssistantUndoLogResponse,
    BriefingRunRequest,
    BriefingRunResponse,
    TranscribeResponse,
    VoiceChatResponse,
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


@router.get(
    "/sources/{source_id}/mailbox-policy",
    response_model=AssistantMailboxPolicyResponse,
)
async def get_source_mailbox_policy(
    source_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the configured status-folder policy for one source."""
    try:
        return await _svc(db).get_mailbox_policy(tenant_id, user.id, source_id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.post(
    "/sources/{source_id}/mailbox-policy/setup",
    response_model=AssistantMailboxPolicyResponse,
)
async def setup_source_mailbox_policy(
    source_id: int,
    data: AssistantMailboxPolicySetupRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Ensure TODO/WARTEN/TEMP/ARCHIV folders exist and cache their IDs."""
    try:
        result = await _svc(db).setup_mailbox_policy(
            tenant_id,
            user.id,
            source_id,
            create_missing=data.create_missing,
            folder_names=data.folder_names,
        )
        await db.commit()
        return result
    except AppError as e:
        await db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


# ── Category Registry ────────────────────────────────────────────────


@router.get("/categories", response_model=list[AssistantCategoryResponse])
async def list_categories(
    include_inactive: bool = Query(False),
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List configured assistant categories for this tenant."""
    try:
        return await _svc(db).list_categories(
            tenant_id, user.id, include_inactive=include_inactive
        )
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.post(
    "/categories",
    response_model=AssistantCategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_category(
    data: AssistantCategoryCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new assistant category."""
    try:
        result = await _svc(db).create_category(tenant_id, user.id, data.model_dump())
        await db.commit()
        return result
    except AppError as e:
        await db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.put("/categories/{category_id}", response_model=AssistantCategoryResponse)
async def update_category(
    category_id: int,
    data: AssistantCategoryUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a configured assistant category."""
    try:
        result = await _svc(db).update_category(
            tenant_id, user.id, category_id, data.model_dump(exclude_unset=True)
        )
        await db.commit()
        return result
    except AppError as e:
        await db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a configured assistant category."""
    try:
        await _svc(db).delete_category(tenant_id, user.id, category_id)
        await db.commit()
    except AppError as e:
        await db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


# ── TEMP Review ──────────────────────────────────────────────────────


@router.get("/temp/review", response_model=list[AssistantTempTrackingResponse])
async def review_expired_temp(
    mailbox: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List unresolved TEMP emails whose expiry date has passed."""
    try:
        result = await _svc(db).review_expired_temp(
            tenant_id, user.id, mailbox=mailbox, limit=limit
        )
        await db.commit()
        return result
    except AppError as e:
        await db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get(
    "/reviews/waiting",
    response_model=list[AssistantMailboxReviewItemResponse],
)
async def review_waiting(
    source_id: int | None = Query(None),
    mailbox: str | None = Query(None),
    older_than_days: int = Query(5, ge=1, le=365),
    limit: int = Query(10, ge=1, le=10),
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List older messages from the configured WARTEN folder."""
    try:
        return await _svc(db).review_waiting(
            tenant_id,
            user.id,
            source_id=source_id,
            mailbox=mailbox,
            older_than_days=older_than_days,
            limit=limit,
        )
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get(
    "/reviews/todos",
    response_model=list[AssistantMailboxReviewItemResponse],
)
async def review_stale_todos(
    source_id: int | None = Query(None),
    mailbox: str | None = Query(None),
    older_than_days: int = Query(7, ge=1, le=365),
    limit: int = Query(10, ge=1, le=10),
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List older messages from the configured TODO folder."""
    try:
        return await _svc(db).review_stale_todos(
            tenant_id,
            user.id,
            source_id=source_id,
            mailbox=mailbox,
            older_than_days=older_than_days,
            limit=limit,
        )
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get(
    "/triage/batch",
    response_model=list[AssistantMailboxReviewItemResponse],
)
async def triage_batch(
    source_id: int | None = Query(None),
    mailbox: str | None = Query(None),
    limit: int = Query(10, ge=1, le=10),
    unread_only: bool = Query(False),
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Load the next bounded triage batch from INBOX."""
    try:
        return await _svc(db).triage_batch(
            tenant_id,
            user.id,
            source_id=source_id,
            mailbox=mailbox,
            limit=limit,
            unread_only=unread_only,
        )
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


# ── Autopilot ─────────────────────────────────────────────────────────


@router.get("/autopilot/report")
async def get_autopilot_report(
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the latest autopilot daily report."""
    from app.assistant.autopilot_report import AutopilotReportService

    try:
        svc = AutopilotReportService(db)
        report = await svc.get_latest_report(tenant_id, user.id)
        if not report:
            return {"text": "Kein Autopilot-Bericht vorhanden.", "data": None}
        return report
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.post("/autopilot/run")
async def run_autopilot_manual(
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger an autopilot cycle for the current user."""
    from app.assistant.autopilot import AutopilotService
    from app.assistant.autopilot_report import AutopilotReportService

    try:
        svc = AutopilotService(db)
        stats = await svc.run_autopilot_cycle(tenant_id, user.id)

        # Also generate/update report
        report_svc = AutopilotReportService(db)
        await report_svc.generate_daily_report(tenant_id, user.id)

        await db.commit()
        return stats
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        await db.rollback()
        logger.exception("Autopilot manual run failed")
        raise HTTPException(
            status_code=500, detail="Autopilot-Zyklus fehlgeschlagen"
        ) from e


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


# ── Drafts ───────────────────────────────────────────────────────────


@router.get("/drafts", response_model=list[AssistantDraftResponse])
async def list_drafts(
    status_filter: str | None = Query(None, alias="status"),
    conversation_id: int | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List drafts for the current user."""
    return await _svc(db).list_drafts(
        tenant_id,
        user.id,
        status=status_filter,
        conversation_id=conversation_id,
        limit=limit,
    )


@router.get("/drafts/{draft_id}", response_model=AssistantDraftResponse)
async def get_draft(
    draft_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single draft."""
    try:
        return await _svc(db).get_draft(tenant_id, user.id, draft_id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.put("/drafts/{draft_id}", response_model=AssistantDraftResponse)
async def update_draft(
    draft_id: int,
    data: AssistantDraftUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a draft before sending."""
    try:
        result = await _svc(db).update_draft(
            tenant_id, user.id, draft_id, data.model_dump(exclude_unset=True)
        )
        await db.commit()
        return result
    except AppError as e:
        await db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.post("/drafts/{draft_id}/send", response_model=AssistantDraftResponse)
async def send_draft(
    draft_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a persisted draft."""
    try:
        result = await _svc(db).send_draft(tenant_id, user.id, draft_id)
        await db.commit()
        return result
    except AppError as e:
        await db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.post("/drafts/{draft_id}/discard", response_model=AssistantDraftResponse)
async def discard_draft(
    draft_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Discard a draft."""
    try:
        result = await _svc(db).discard_draft(tenant_id, user.id, draft_id)
        await db.commit()
        return result
    except AppError as e:
        await db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


# ── Pending Intents ──────────────────────────────────────────────────


@router.get("/pending-intents", response_model=list[AssistantPendingIntentResponse])
async def list_pending_intents(
    status_filter: str | None = Query(None, alias="status"),
    conversation_id: int | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List pending assistant intents."""
    return await _svc(db).list_pending_intents(
        tenant_id,
        user.id,
        status=status_filter,
        conversation_id=conversation_id,
        limit=limit,
    )


@router.get(
    "/pending-intents/{intent_id}",
    response_model=AssistantPendingIntentResponse,
)
async def get_pending_intent(
    intent_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single pending intent."""
    try:
        return await _svc(db).get_pending_intent(tenant_id, user.id, intent_id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.post(
    "/pending-intents/{intent_id}/execute",
    response_model=AssistantPendingIntentResponse,
)
async def execute_pending_intent(
    intent_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Execute a pending intent after explicit confirmation."""
    try:
        result = await _svc(db).execute_pending_intent(tenant_id, user.id, intent_id)
        await db.commit()
        return result
    except AppError as e:
        await db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.post(
    "/pending-intents/{intent_id}/cancel",
    response_model=AssistantPendingIntentResponse,
)
async def cancel_pending_intent(
    intent_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a pending intent."""
    try:
        result = await _svc(db).cancel_pending_intent(tenant_id, user.id, intent_id)
        await db.commit()
        return result
    except AppError as e:
        await db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


# ── Conversations ────────────────────────────────────────────────────


@router.get(
    "/conversations/{conversation_id}/turns",
    response_model=list[AssistantConversationTurnResponse],
)
async def list_conversation_turns(
    conversation_id: int,
    limit: int = Query(100, ge=1, le=500),
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List persisted turns for a conversation."""
    try:
        return await _svc(db).list_conversation_turns(
            tenant_id, user.id, conversation_id, limit=limit
        )
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


# ── Undo Logs ────────────────────────────────────────────────────────


@router.get("/undo-logs", response_model=list[AssistantUndoLogResponse])
async def list_undo_logs(
    limit: int = Query(50, ge=1, le=200),
    undoable_only: bool = Query(False),
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List recent undo/audit records."""
    return await _svc(db).list_undo_logs(
        tenant_id,
        user.id,
        limit=limit,
        undoable_only=undoable_only,
    )


@router.post("/undo-logs/{undo_log_id}/undo", response_model=AssistantUndoLogResponse)
async def undo_action(
    undo_log_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Undo a reversible assistant action."""
    try:
        result = await _svc(db).undo_action(tenant_id, user.id, undo_log_id)
        await db.commit()
        return result
    except AppError as e:
        await db.rollback()
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


# ── Test / Manual Triggers ────────────────────────────────────────────


@router.post("/intake/run")
async def run_intake(
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger mail/calendar intake."""
    from app.assistant.intake import AssistantIntakeService

    try:
        intake = AssistantIntakeService(db)
        result = await intake.run_intake(tenant_id, user.id)
        await db.commit()
        return result
    except AppError as e:
        await db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        await db.rollback()
        logger.exception("Intake error")
        raise HTTPException(status_code=500, detail=str(e)[:200]) from e


@router.post("/classify/run")
async def run_classify(
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually classify unprocessed items."""
    from app.assistant.classifier import AssistantClassifier

    try:
        svc = _svc(db)
        items = await svc.list_items(tenant_id, user.id, status="new", limit=100)
        classifier = AssistantClassifier(db)
        decisions = await classifier.classify_items(tenant_id, user.id, items)
        await db.commit()
        return {
            "items_classified": len(items),
            "decisions_created": len(decisions),
        }
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.post("/rules/apply")
async def run_rules(
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually apply rules to classified items."""
    from app.assistant.rules import AssistantRuleEngine

    try:
        svc = _svc(db)
        items = await svc.list_items(tenant_id, user.id, status="classified", limit=100)
        engine = AssistantRuleEngine(db)
        actions = await engine.apply_rules(tenant_id, user.id, items)
        await db.commit()
        return {
            "items_processed": len(items),
            "actions_created": len(actions),
        }
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


@router.get("/mailbox-health", response_model=list[AssistantMailboxHealthResponse])
async def get_mailbox_health(
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Live mailbox health snapshots for connected accounts."""
    try:
        return await _svc(db).get_mailbox_health(tenant_id, user.id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


# ── Model / Voice Lists ─────────────────────────────────────────────


@router.get("/ollama-models")
async def list_ollama_models(
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
):
    """Return available Ollama models (filtered: no embeddings/vision)."""
    import httpx

    from app.config import settings

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{settings.ollama_url}/api/tags")
            response.raise_for_status()
    except Exception as e:
        logger.warning("Ollama model list unavailable: {err}", err=str(e))
        return {"models": []}

    models = response.json().get("models", [])
    excluded = (
        "embed",
        "embedding",
        "bge",
        "mxbai",
        "vision",
        "llava",
        "minicpm-v",
        "vde",
    )
    names = []
    for item in models:
        name = item.get("name", "")
        if name and not any(kw in name.lower() for kw in excluded):
            names.append(name)
    return {"models": sorted(set(names))}


@router.get("/piper-voices")
async def list_piper_voices(
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
):
    """Return available Piper TTS voices."""
    import httpx

    from app.config import settings

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{settings.tts_url}/api/voices")
            response.raise_for_status()
    except Exception as e:
        logger.warning("Piper voice list unavailable: {err}", err=str(e))
        return {"voices": []}

    voices = response.json()
    if isinstance(voices, list):
        return {"voices": sorted(voices)}
    if isinstance(voices, dict):
        return {"voices": sorted(voices.keys())}
    return {"voices": []}


# ── Speaker Voices ──────────────────────────────────────────────────


@router.get("/speaker-voices")
async def list_speaker_voices(
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
):
    """List saved speaker WAV files for XTTS voice cloning."""
    from pathlib import Path

    from app.config import settings

    speaker_dir = Path(settings.speaker_upload_dir) / tenant_id
    if not speaker_dir.exists():
        return {"voices": []}

    voices = []
    for wav in sorted(speaker_dir.glob("*.wav")):
        voices.append(
            {
                "name": wav.stem,
                "filename": wav.name,
                "size_bytes": wav.stat().st_size,
                "url": f"/uploads/speakers/{tenant_id}/{wav.name}",
            }
        )
    return {"voices": voices}


@router.post("/speaker-voices")
async def upload_speaker_voice(
    name: str = Form(...),
    audio: UploadFile = File(...),
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a WAV file as speaker voice for XTTS."""
    import re
    import struct
    import wave
    from io import BytesIO
    from pathlib import Path

    from app.config import settings

    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Keine Audiodaten empfangen")

    if len(audio_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Datei zu gross (max 10 MB)")

    # Validate WAV
    try:
        bio = BytesIO(audio_bytes)
        with wave.open(bio, "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            duration = frames // rate if rate > 0 else 0
    except (wave.Error, struct.error, EOFError) as e:
        raise HTTPException(status_code=400, detail="Ungueltige WAV-Datei") from e

    if duration < 3:
        raise HTTPException(
            status_code=400,
            detail=f"Audio zu kurz ({duration}s). Minimum: 3 Sekunden.",
        )
    if duration > 30:
        raise HTTPException(
            status_code=400,
            detail=f"Audio zu lang ({duration}s). Maximum: 30 Sekunden.",
        )

    # Save file
    safe_name = re.sub(r"[^a-z0-9]+", "-", name.lower().strip()).strip("-") or "stimme"

    tenant_dir = Path(settings.speaker_upload_dir) / tenant_id
    tenant_dir.mkdir(parents=True, exist_ok=True)
    wav_path = tenant_dir / f"{safe_name}.wav"

    # Avoid overwriting — add suffix
    counter = 1
    while wav_path.exists():
        wav_path = tenant_dir / f"{safe_name}-{counter}.wav"
        counter += 1

    wav_path.write_bytes(audio_bytes)

    # Also save XTTS copy
    xtts_dir = Path(settings.speaker_upload_dir) / "xtts"
    xtts_dir.mkdir(parents=True, exist_ok=True)
    xtts_name = f"{tenant_id}_{wav_path.stem}"
    xtts_path = xtts_dir / f"{xtts_name}.wav"
    xtts_path.write_bytes(audio_bytes)

    logger.info(
        "Speaker voice saved: {name} ({dur}s) → {path}",
        name=safe_name,
        dur=duration,
        path=str(wav_path),
    )

    return {
        "name": wav_path.stem,
        "filename": wav_path.name,
        "duration_seconds": duration,
        "sample_rate": rate,
        "size_bytes": len(audio_bytes),
        "url": f"/uploads/speakers/{tenant_id}/{wav_path.name}",
        "xtts_speaker_name": xtts_name,
    }


@router.delete("/speaker-voices/{voice_name}")
async def delete_speaker_voice(
    voice_name: str,
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
):
    """Delete a speaker voice WAV file."""
    import re
    from pathlib import Path

    from app.config import settings

    # Sanitize name to prevent path traversal
    if not re.match(r"^[a-z0-9-]+$", voice_name):
        raise HTTPException(status_code=400, detail="Ungueltiger Stimmenname")

    wav_path = Path(settings.speaker_upload_dir) / tenant_id / f"{voice_name}.wav"
    if not wav_path.exists():
        raise HTTPException(status_code=404, detail="Stimme nicht gefunden")

    wav_path.unlink()

    # Also remove XTTS copy
    xtts_path = (
        Path(settings.speaker_upload_dir) / "xtts" / f"{tenant_id}_{voice_name}.wav"
    )
    if xtts_path.exists():
        xtts_path.unlink()

    return {"deleted": voice_name}


# ── Voice Chat ──────────────────────────────────────────────────────


@router.post("/voice/chat", response_model=VoiceChatResponse)
async def voice_chat(
    text: str = Form(None),
    conversation_id: int | None = Form(None),
    tts_enabled: bool = Form(True),
    audio: UploadFile | None = File(None),
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Voice chat endpoint - accepts text or audio, returns text + optional TTS audio."""
    from app.assistant.voice import VoiceService

    try:
        transcribed_text = None

        # If audio uploaded, transcribe first
        if audio and audio.filename:
            from app.assistant.stt import STTService

            audio_bytes = await audio.read()
            if audio_bytes:
                profile = await _svc(db).get_or_create_profile(tenant_id, user.id)
                stt = STTService(provider=profile.stt_provider)
                text = await stt.transcribe(audio_bytes)
                transcribed_text = text
                if not text:
                    raise HTTPException(
                        status_code=400, detail="Konnte Audio nicht transkribieren"
                    )

        if not text:
            raise HTTPException(status_code=400, detail="Kein Text oder Audio gesendet")

        # Process through voice service
        voice_svc = VoiceService(db)
        result = await voice_svc.process_message(
            tenant_id, user.id, text, conversation_id
        )

        # TTS synthesis
        audio_base64 = None
        if tts_enabled and result.get("text"):
            try:
                profile = await _svc(db).get_or_create_profile(tenant_id, user.id)
                from app.briefing.tts import TTSService

                tts = TTSService(engine_override=profile.tts_provider)
                if tts.is_available():
                    wav_bytes = await tts.synthesize(
                        result["text"],
                        voice=profile.tts_voice or "de_DE-thorsten-high",
                    )
                    audio_base64 = base64.b64encode(wav_bytes).decode()
            except Exception as e:
                logger.warning("TTS failed, returning text only: {err}", err=str(e))

        await db.commit()

        return VoiceChatResponse(
            text=result["text"],
            audio_base64=audio_base64,
            conversation_id=result["conversation_id"],
            context=result["context"],
            transcribed_text=transcribed_text,
        )
    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        await db.rollback()
        logger.exception("Voice chat error")
        raise HTTPException(status_code=500, detail=str(e)[:200]) from e


@router.post("/voice/transcribe", response_model=TranscribeResponse)
async def voice_transcribe(
    audio: UploadFile = File(...),
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Transcribe audio to text (STT only)."""
    from app.assistant.stt import STTService

    try:
        audio_bytes = await audio.read()
        profile = await _svc(db).get_or_create_profile(tenant_id, user.id)
        stt = STTService(provider=profile.stt_provider)
        text = await stt.transcribe(audio_bytes)
        return TranscribeResponse(text=text)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Transcribe error")
        raise HTTPException(status_code=500, detail=str(e)[:200]) from e


@router.post("/voice/tts")
async def voice_tts(
    data: dict,
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Text-to-Speech: convert text to WAV audio."""
    from fastapi.responses import Response

    from app.briefing.tts import TTSService

    try:
        text = data.get("text", "")
        if not text:
            raise HTTPException(status_code=400, detail="Kein Text angegeben")

        profile = await _svc(db).get_or_create_profile(tenant_id, user.id)
        tts = TTSService(engine_override=profile.tts_provider)
        wav_bytes = await tts.synthesize(
            text, voice=profile.tts_voice or "de_DE-thorsten-high"
        )
        return Response(content=wav_bytes, media_type="audio/wav")
    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("TTS error")
        raise HTTPException(status_code=500, detail=str(e)[:200]) from e


# ── OAuth / Konto verbinden ──────────────────────────────────────────

OAUTH_CALLBACK_HTML = """<!DOCTYPE html>
<html><body><script>
window.opener?.postMessage({type:'oauth_success'}, '*');
window.close();
</script><p>Verbindung erfolgreich. Dieses Fenster kann geschlossen werden.</p></body></html>"""

OAUTH_ERROR_HTML = """<!DOCTYPE html>
<html><body><script>
window.opener?.postMessage({type:'oauth_error', error:'%s'}, '*');
window.close();
</script><p>Fehler: %s</p></body></html>"""


@router.get("/oauth/authorize")
async def oauth_authorize(
    provider: str = Query(..., pattern=r"^(microsoft|google)$"),
    shared_mailbox: str | None = Query(None),
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Return OAuth URL for connecting a mail/calendar account."""
    from urllib.parse import quote, urlencode

    from app.config import settings
    from app.integrations.oauth import encrypt_token

    state_data = {
        "tenant_id": tenant_id,
        "user_id": user.id,
        "provider": provider,
        "flow": "assistant",
    }
    if shared_mailbox:
        state_data["shared_mailbox"] = shared_mailbox
    state = encrypt_token(state_data)
    callback_url = f"{settings.app_url}/api/v1/assistant/oauth/callback"

    # Request mail + calendar + user scopes
    if provider == "microsoft":
        scope = "Mail.ReadWrite Mail.Send Calendars.Read User.Read offline_access"
        tid = settings.microsoft_tenant_id or "common"
        params = urlencode(
            {
                "client_id": settings.microsoft_client_id,
                "response_type": "code",
                "redirect_uri": callback_url,
                "scope": scope,
                "state": state,
            },
            quote_via=quote,
        )
        auth_url = (
            f"https://login.microsoftonline.com/{tid}/oauth2/v2.0/authorize?{params}"
        )
    else:
        scope = (
            "https://www.googleapis.com/auth/gmail.readonly "
            "https://www.googleapis.com/auth/calendar.readonly "
            "openid email"
        )
        params = urlencode(
            {
                "client_id": settings.google_client_id,
                "response_type": "code",
                "redirect_uri": callback_url,
                "scope": scope,
                "access_type": "offline",
                "prompt": "consent",
                "state": state,
            },
            quote_via=quote,
        )
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{params}"

    return {"auth_url": auth_url}


@router.get("/oauth/callback")
async def oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """OAuth callback - creates integration_connection + assistant_source."""
    from fastapi.responses import HTMLResponse

    from app.config import settings
    from app.integrations.oauth import (
        decrypt_token,
        encrypt_token,
        exchange_oauth_code,
        fetch_oauth_email,
    )

    try:
        state_data = decrypt_token(state)
        tenant_id = state_data["tenant_id"]
        user_id = state_data["user_id"]
        provider = state_data["provider"]
        shared_mailbox = state_data.get("shared_mailbox")

        callback_url = f"{settings.app_url}/api/v1/assistant/oauth/callback"
        tokens = await exchange_oauth_code(code, provider, callback_url)
        email = await fetch_oauth_email(tokens["access_token"], provider)

        from datetime import UTC, datetime

        token_data = {
            "access_token": tokens["access_token"],
            "refresh_token": tokens.get("refresh_token", ""),
            "expires_at": datetime.now(UTC).timestamp()
            + tokens.get("expires_in", 3600),
        }

        # Map provider name to integration provider
        provider_name = (
            "microsoft_graph" if provider == "microsoft" else "google_workspace"
        )

        # For shared mailboxes: store the shared address as mailbox_address,
        # the authenticating user's email as connected_email
        scope = "shared_mailbox" if shared_mailbox else "personal"

        svc = AssistantService(db)
        conn, source = await svc.create_connection_and_source(
            tenant_id=tenant_id,
            user_id=user_id,
            provider=provider_name,
            connected_email=email,
            encrypted_token=encrypt_token(token_data),
            mailbox_address=shared_mailbox,
            scope=scope,
        )
        await db.commit()

        logger.info(
            "Assistant OAuth: conn={cid} source={sid} email={e} shared={s}",
            cid=conn.id,
            sid=source.id,
            e=email,
            s=shared_mailbox or "none",
        )
        return HTMLResponse(OAUTH_CALLBACK_HTML)
    except Exception as e:
        logger.exception("Assistant OAuth callback Fehler")
        error_msg = str(e)[:200]
        return HTMLResponse(OAUTH_ERROR_HTML % (error_msg, error_msg), status_code=400)
