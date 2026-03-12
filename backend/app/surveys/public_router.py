"""Surveys public API router (no auth required for survey participation)."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import AppError, NotFoundError
from app.surveys.models import SurveyStatus
from app.surveys.schemas import (
    AnswerSubmit,
    PublicStartResponse,
    PublicSurvey,
    ResponseComplete,
    ResponseStart,
)
from app.surveys.service import ResponseService, SurveyService

public_router = APIRouter(prefix="/surveys/public", tags=["surveys-public"])

# Alias for auto-discovery
router = public_router


def get_tenant_from_request(request: Request) -> str:
    """Extract tenant from request headers or use default."""
    from app.config import settings
    return request.headers.get("X-Tenant-ID", settings.default_tenant_id)


@public_router.get("/{slug}", response_model=PublicSurvey)
async def get_public_survey(
    slug: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Get a public survey for participation (no auth)."""
    tenant_id = get_tenant_from_request(request)
    service = SurveyService(db)

    try:
        survey = await service.get_survey_by_slug(tenant_id, slug)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Umfrage nicht gefunden") from None

    # Check if survey is active
    if survey.status != SurveyStatus.ACTIVE.value:
        raise HTTPException(status_code=404, detail="Umfrage ist nicht verfügbar")

    # Check time constraints
    now = datetime.now(UTC)
    if survey.starts_at and now < survey.starts_at:
        raise HTTPException(status_code=404, detail="Umfrage hat noch nicht begonnen")
    if survey.ends_at and now > survey.ends_at:
        raise HTTPException(status_code=404, detail="Umfrage ist beendet")

    return survey


@public_router.post("/{slug}/start", response_model=PublicStartResponse)
async def start_survey(
    slug: str,
    data: ResponseStart | None = None,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    """Start a new survey response."""
    tenant_id = get_tenant_from_request(request)
    survey_service = SurveyService(db)

    try:
        survey = await survey_service.get_survey_by_slug(tenant_id, slug)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Umfrage nicht gefunden") from None

    # Check if survey is active
    if survey.status != SurveyStatus.ACTIVE.value:
        raise HTTPException(status_code=400, detail="Umfrage ist nicht aktiv")

    # Check time constraints
    now = datetime.now(UTC)
    if survey.starts_at and now < survey.starts_at:
        raise HTTPException(status_code=400, detail="Umfrage hat noch nicht begonnen")
    if survey.ends_at and now > survey.ends_at:
        raise HTTPException(status_code=400, detail="Umfrage ist beendet")

    # Get client info
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent", "")[:500]

    # Start response
    response_service = ResponseService(db)
    response = await response_service.start_response(
        tenant_id=tenant_id,
        survey_id=survey.id,
        email=data.email if data else None,
        name=data.name if data else None,
        contact_id=data.contact_id if data else None,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await db.commit()

    return PublicStartResponse(response_id=response.id, token=response.token)


@public_router.post("/{slug}/answer")
async def save_answer(
    slug: str,
    token: str,
    answer: AnswerSubmit,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    """Save a single answer (for progressive saving)."""
    tenant_id = get_tenant_from_request(request)

    # Verify token and get response
    response_service = ResponseService(db)
    try:
        response = await response_service.get_response_by_token(token)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Ungültiger Token") from None

    # Check if already completed
    if response.status == "completed":
        raise HTTPException(status_code=400, detail="Umfrage bereits abgeschlossen")

    # Save answer
    await response_service.save_answer(tenant_id, response.id, answer)
    await db.commit()

    return {"success": True}


@public_router.post("/{slug}/complete")
async def complete_survey(
    slug: str,
    token: str,
    data: ResponseComplete | None = None,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    """Complete a survey response."""
    tenant_id = get_tenant_from_request(request)
    response_service = ResponseService(db)

    try:
        response = await response_service.complete_response(
            token=token,
            answers=data.answers if data else None,
        )
        await db.commit()
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Ungültiger Token") from None
    except AppError as e:
        raise HTTPException(status_code=400, detail=e.message) from None

    # Trigger webhook if configured
    survey_service = SurveyService(db)
    try:
        survey = await survey_service.get_survey_by_slug(tenant_id, slug)
        if survey.webhook_url and survey.webhook_on_complete:
            await _trigger_webhook(survey, response, db)
    except Exception:
        pass  # Don't fail if webhook fails

    return {
        "success": True,
        "thank_you_title": survey.thank_you_title if survey else "Vielen Dank!",
        "thank_you_message": survey.thank_you_message if survey else None,
        "redirect_url": survey.redirect_url if survey else None,
    }


async def _trigger_webhook(survey, response, db: AsyncSession):
    """Trigger n8n webhook with response data."""
    import httpx
    from sqlalchemy import select

    from app.surveys.models import SurveyQuestion

    # Build payload
    answers_data = []
    for answer in response.answers:
        # Get question title
        q_result = await db.execute(
            select(SurveyQuestion).where(SurveyQuestion.id == answer.question_id)
        )
        question = q_result.scalar_one_or_none()

        value = (
            answer.value_text
            or answer.value_number
            or answer.value_float
            or answer.value_list
            or answer.value_bool
        )

        answers_data.append(
            {
                "question_id": answer.question_id,
                "question": question.title if question else None,
                "value": value,
            }
        )

    payload = {
        "event": "survey.response.completed",
        "survey_id": survey.id,
        "survey_title": survey.title,
        "response_id": response.id,
        "completed_at": response.completed_at.isoformat()
        if response.completed_at
        else None,
        "contact": {
            "id": response.contact_id,
            "email": response.email,
            "name": response.name,
        }
        if response.contact_id or response.email
        else None,
        "answers": answers_data,
        "nps_score": response.nps_score,
        "nps_category": response.nps_category,
        "duration_seconds": response.duration_seconds,
    }

    # Send webhook
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(survey.webhook_url, json=payload)
    except Exception:
        pass  # Log but don't fail
