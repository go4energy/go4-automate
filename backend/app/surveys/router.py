"""Surveys module API router (Admin endpoints)."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.config import settings
from app.database import get_db
from app.exceptions import NotFoundError
from app.surveys.models import SurveyStatus
from app.surveys.schemas import (
    ParticipantResponse,
    ParticipantResponseList,
    QuestionCreate,
    QuestionReorder,
    QuestionResponse,
    QuestionUpdate,
    SendInvites,
    ShareLink,
    SurveyCreate,
    SurveyResponse,
    SurveyStats,
    SurveyStatusUpdate,
    SurveyUpdate,
    SurveyWithQuestions,
)
from app.surveys.service import (
    QuestionService,
    ResponseService,
    StatsService,
    SurveyService,
)
from app.utils.dependencies import get_current_tenant_id

router = APIRouter(prefix="/surveys", tags=["surveys"])


# ============== Surveys ==============


@router.get("", response_model=list[SurveyResponse])
async def list_surveys(
    status: str | None = Query(None),
    survey_type: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """List all surveys."""
    service = SurveyService(db)
    return await service.list_surveys(tenant_id, status, survey_type, skip, limit)


@router.post(
    "", response_model=SurveyWithQuestions, status_code=status.HTTP_201_CREATED
)
async def create_survey(
    data: SurveyCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new survey."""
    service = SurveyService(db)
    survey = await service.create_survey(tenant_id, user.id, data)
    await db.commit()
    # Re-fetch with questions loaded to avoid lazy loading issues
    return await service.get_survey(tenant_id, survey.id)


@router.get("/{survey_id}", response_model=SurveyWithQuestions)
async def get_survey(
    survey_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Get a survey by ID with questions."""
    service = SurveyService(db)
    try:
        return await service.get_survey(tenant_id, survey_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from None


@router.put("/{survey_id}", response_model=SurveyResponse)
async def update_survey(
    survey_id: int,
    data: SurveyUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Update a survey."""
    service = SurveyService(db)
    try:
        survey = await service.update_survey(tenant_id, survey_id, data)
        await db.commit()
        return survey
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from None


@router.delete("/{survey_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_survey(
    survey_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete a survey."""
    service = SurveyService(db)
    try:
        await service.delete_survey(tenant_id, survey_id)
        await db.commit()
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from None


@router.patch("/{survey_id}/status", response_model=SurveyResponse)
async def update_survey_status(
    survey_id: int,
    data: SurveyStatusUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Update survey status (activate, pause, close)."""
    service = SurveyService(db)
    try:
        survey = await service.update_status(tenant_id, survey_id, data.status.value)
        await db.commit()
        return survey
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from None


@router.post("/{survey_id}/duplicate", response_model=SurveyWithQuestions)
async def duplicate_survey(
    survey_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Duplicate a survey with all questions."""
    service = SurveyService(db)
    try:
        survey = await service.duplicate_survey(tenant_id, survey_id, user.id)
        await db.commit()
        # Re-fetch with questions loaded to avoid lazy loading issues
        return await service.get_survey(tenant_id, survey.id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from None


# ============== Questions ==============


@router.post(
    "/{survey_id}/questions",
    response_model=QuestionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_question(
    survey_id: int,
    data: QuestionCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Add a question to a survey."""
    # Verify survey exists
    survey_service = SurveyService(db)
    try:
        await survey_service.get_survey(tenant_id, survey_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from None

    service = QuestionService(db)
    question = await service.add_question(tenant_id, survey_id, data)
    await db.commit()
    return question


@router.put("/questions/{question_id}", response_model=QuestionResponse)
async def update_question(
    question_id: int,
    data: QuestionUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Update a question."""
    service = QuestionService(db)
    try:
        question = await service.update_question(tenant_id, question_id, data)
        await db.commit()
        return question
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from None


@router.delete("/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(
    question_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete a question."""
    service = QuestionService(db)
    try:
        await service.delete_question(tenant_id, question_id)
        await db.commit()
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from None


@router.patch("/{survey_id}/questions/reorder", response_model=list[QuestionResponse])
async def reorder_questions(
    survey_id: int,
    data: QuestionReorder,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Reorder questions."""
    service = QuestionService(db)
    questions = await service.reorder_questions(tenant_id, survey_id, data.question_ids)
    await db.commit()
    return questions


# ============== Responses ==============


@router.get("/{survey_id}/responses", response_model=list[ParticipantResponseList])
async def list_responses(
    survey_id: int,
    status: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """List all responses for a survey."""
    service = ResponseService(db)
    return await service.list_responses(tenant_id, survey_id, status, skip, limit)


@router.get("/responses/{response_id}", response_model=ParticipantResponse)
async def get_response(
    response_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Get a single response with answers."""
    service = ResponseService(db)
    try:
        return await service.get_response(tenant_id, response_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from None


@router.delete("/responses/{response_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_response(
    response_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete a response."""
    service = ResponseService(db)
    try:
        await service.delete_response(tenant_id, response_id)
        await db.commit()
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from None


# ============== Stats ==============


@router.get("/{survey_id}/stats", response_model=SurveyStats)
async def get_survey_stats(
    survey_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Get survey statistics."""
    # Verify survey exists
    survey_service = SurveyService(db)
    try:
        await survey_service.get_survey(tenant_id, survey_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from None

    stats_service = StatsService(db)
    return await stats_service.get_survey_stats(tenant_id, survey_id)


# ============== Share / Distribution ==============


@router.get("/{survey_id}/share-link", response_model=ShareLink)
async def get_share_link(
    survey_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Get share link for a survey."""
    service = SurveyService(db)
    try:
        survey = await service.get_survey(tenant_id, survey_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from None

    # Build URL (adjust base URL as needed)
    base_url = settings.app_url.rstrip("/")
    url = f"{base_url}/s/{survey.slug}"

    return ShareLink(
        url=url,
        slug=survey.slug,
        qr_code_url=f"/api/v1/surveys/{survey_id}/qr-code",
    )


@router.get("/{survey_id}/qr-code")
async def get_qr_code(
    survey_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Generate QR code for survey link."""
    import io

    import qrcode
    from fastapi.responses import StreamingResponse

    service = SurveyService(db)
    try:
        survey = await service.get_survey(tenant_id, survey_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from None

    # Build URL
    base_url = settings.app_url.rstrip("/")
    url = f"{base_url}/s/{survey.slug}"

    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    # Return as PNG
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return StreamingResponse(buffer, media_type="image/png")


@router.post("/{survey_id}/send-invites")
async def send_invites(
    survey_id: int,
    data: SendInvites,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Send email invitations (triggers n8n webhook)."""

    service = SurveyService(db)
    try:
        survey = await service.get_survey(tenant_id, survey_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from None

    if survey.status != SurveyStatus.ACTIVE.value:
        raise HTTPException(
            status_code=400, detail="Survey must be active to send invites"
        )

    # TODO: Implement actual email sending via n8n webhook
    # For now, just return success
    return {
        "success": True,
        "message": f"Invitations queued for {len(data.contact_ids) + len(data.emails)} recipients",
    }
