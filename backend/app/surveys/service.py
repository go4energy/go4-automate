"""Surveys module business logic."""

import re
import secrets
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import AppError, NotFoundError
from app.surveys.models import (
    NpsCategory,
    QuestionType,
    ResponseStatus,
    Survey,
    SurveyAnswer,
    SurveyQuestion,
    SurveyResponse,
    SurveyStatus,
)
from app.surveys.schemas import (
    AnswerSubmit,
    NpsStats,
    QuestionCreate,
    QuestionStats,
    QuestionUpdate,
    SurveyCreate,
    SurveyStats,
    SurveyUpdate,
)


def slugify(text: str, max_length: int = 100) -> str:
    """Generate a URL-safe slug from text."""
    slug = text.lower().strip()
    slug = re.sub(r"[äÄ]", "ae", slug)
    slug = re.sub(r"[öÖ]", "oe", slug)
    slug = re.sub(r"[üÜ]", "ue", slug)
    slug = re.sub(r"[ß]", "ss", slug)
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug[:max_length]


class SurveyService:
    """Service for survey management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_surveys(
        self,
        tenant_id: str,
        status: str | None = None,
        survey_type: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Survey]:
        """List all surveys for a tenant."""
        query = select(Survey).where(Survey.tenant_id == tenant_id)

        if status:
            query = query.where(Survey.status == status)
        if survey_type:
            query = query.where(Survey.survey_type == survey_type)

        query = query.order_by(Survey.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_survey(self, tenant_id: str, survey_id: int) -> Survey:
        """Get a survey by ID."""
        query = (
            select(Survey)
            .where(Survey.tenant_id == tenant_id, Survey.id == survey_id)
            .options(selectinload(Survey.questions))
        )
        result = await self.db.execute(query)
        survey = result.scalar_one_or_none()
        if not survey:
            raise NotFoundError("Survey", survey_id)
        return survey

    async def get_survey_by_slug(self, tenant_id: str, slug: str) -> Survey:
        """Get a survey by slug."""
        query = (
            select(Survey)
            .where(Survey.tenant_id == tenant_id, Survey.slug == slug)
            .options(selectinload(Survey.questions))
        )
        result = await self.db.execute(query)
        survey = result.scalar_one_or_none()
        if not survey:
            raise NotFoundError("Survey", slug)
        return survey

    async def create_survey(
        self, tenant_id: str, owner_id: int, data: SurveyCreate
    ) -> Survey:
        """Create a new survey."""
        # Generate unique slug
        base_slug = slugify(data.title, max_length=80)
        slug = base_slug
        counter = 1

        while True:
            existing = await self.db.execute(
                select(Survey).where(Survey.tenant_id == tenant_id, Survey.slug == slug)
            )
            if not existing.scalar_one_or_none():
                break
            slug = f"{base_slug}-{counter}"
            counter += 1

        survey = Survey(
            tenant_id=tenant_id,
            owner_id=owner_id,
            slug=slug,
            **data.model_dump(),
        )
        self.db.add(survey)
        await self.db.flush()
        await self.db.refresh(survey)
        return survey

    async def update_survey(
        self, tenant_id: str, survey_id: int, data: SurveyUpdate
    ) -> Survey:
        """Update a survey."""
        survey = await self.get_survey(tenant_id, survey_id)
        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(survey, field, value)

        await self.db.flush()
        await self.db.refresh(survey)
        return survey

    async def delete_survey(self, tenant_id: str, survey_id: int) -> None:
        """Delete a survey."""
        survey = await self.get_survey(tenant_id, survey_id)
        await self.db.delete(survey)

    async def update_status(
        self, tenant_id: str, survey_id: int, status: str
    ) -> Survey:
        """Update survey status."""
        survey = await self.get_survey(tenant_id, survey_id)
        survey.status = status
        await self.db.flush()
        await self.db.refresh(survey)
        return survey

    async def duplicate_survey(
        self, tenant_id: str, survey_id: int, owner_id: int
    ) -> Survey:
        """Duplicate a survey with all questions."""
        original = await self.get_survey(tenant_id, survey_id)

        # Create new survey
        new_survey = Survey(
            tenant_id=tenant_id,
            owner_id=owner_id,
            title=f"{original.title} (Kopie)",
            description=original.description,
            slug=f"{original.slug}-copy-{secrets.token_hex(4)}",
            status=SurveyStatus.DRAFT.value,
            survey_type=original.survey_type,
            anonymous=original.anonymous,
            show_progress=original.show_progress,
            one_response_per_contact=original.one_response_per_contact,
            allow_multiple_submissions=original.allow_multiple_submissions,
            logo_url=original.logo_url,
            primary_color=original.primary_color,
            background_color=original.background_color,
            thank_you_title=original.thank_you_title,
            thank_you_message=original.thank_you_message,
            redirect_url=original.redirect_url,
            webhook_url=original.webhook_url,
            webhook_on_complete=original.webhook_on_complete,
        )
        self.db.add(new_survey)
        await self.db.flush()

        # Copy questions
        for q in original.questions:
            new_question = SurveyQuestion(
                tenant_id=tenant_id,
                survey_id=new_survey.id,
                question_type=q.question_type,
                title=q.title,
                description=q.description,
                required=q.required,
                position=q.position,
                page=q.page,
                options=q.options,
                settings=q.settings,
            )
            self.db.add(new_question)

        await self.db.flush()
        await self.db.refresh(new_survey)
        return new_survey


class QuestionService:
    """Service for survey questions."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_question(
        self, tenant_id: str, survey_id: int, data: QuestionCreate
    ) -> SurveyQuestion:
        """Add a question to a survey."""
        # Get max position if not specified
        if data.position is None:
            result = await self.db.execute(
                select(func.max(SurveyQuestion.position)).where(
                    SurveyQuestion.survey_id == survey_id
                )
            )
            max_pos = result.scalar() or -1
            data.position = max_pos + 1

        question = SurveyQuestion(
            tenant_id=tenant_id,
            survey_id=survey_id,
            question_type=data.question_type.value,
            title=data.title,
            description=data.description,
            required=data.required,
            position=data.position,
            page=data.page,
            options=data.options,
            settings=data.settings.model_dump() if data.settings else None,
            show_if_question_id=data.show_if_question_id,
            show_if_value=data.show_if_value,
        )
        self.db.add(question)
        await self.db.flush()
        await self.db.refresh(question)
        return question

    async def get_question(self, tenant_id: str, question_id: int) -> SurveyQuestion:
        """Get a question by ID."""
        query = select(SurveyQuestion).where(
            SurveyQuestion.tenant_id == tenant_id,
            SurveyQuestion.id == question_id,
        )
        result = await self.db.execute(query)
        question = result.scalar_one_or_none()
        if not question:
            raise NotFoundError("Question", question_id)
        return question

    async def update_question(
        self, tenant_id: str, question_id: int, data: QuestionUpdate
    ) -> SurveyQuestion:
        """Update a question."""
        question = await self.get_question(tenant_id, question_id)
        update_data = data.model_dump(exclude_unset=True)

        if "question_type" in update_data:
            update_data["question_type"] = update_data["question_type"].value
        if update_data.get("settings"):
            update_data["settings"] = update_data["settings"].model_dump()

        for field, value in update_data.items():
            setattr(question, field, value)

        await self.db.flush()
        await self.db.refresh(question)
        return question

    async def delete_question(self, tenant_id: str, question_id: int) -> None:
        """Delete a question."""
        question = await self.get_question(tenant_id, question_id)
        await self.db.delete(question)

    async def reorder_questions(
        self, tenant_id: str, survey_id: int, question_ids: list[int]
    ) -> list[SurveyQuestion]:
        """Reorder questions."""
        for position, question_id in enumerate(question_ids):
            await self.db.execute(
                update(SurveyQuestion)
                .where(
                    SurveyQuestion.tenant_id == tenant_id,
                    SurveyQuestion.survey_id == survey_id,
                    SurveyQuestion.id == question_id,
                )
                .values(position=position)
            )

        # Return updated questions
        result = await self.db.execute(
            select(SurveyQuestion)
            .where(
                SurveyQuestion.tenant_id == tenant_id,
                SurveyQuestion.survey_id == survey_id,
            )
            .order_by(SurveyQuestion.position)
        )
        return list(result.scalars().all())


class ResponseService:
    """Service for survey responses."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def start_response(
        self,
        tenant_id: str,
        survey_id: int,
        email: str | None = None,
        name: str | None = None,
        contact_id: int | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> SurveyResponse:
        """Start a new survey response."""
        token = secrets.token_urlsafe(32)

        response = SurveyResponse(
            tenant_id=tenant_id,
            survey_id=survey_id,
            email=email,
            name=name,
            contact_id=contact_id,
            token=token,
            status=ResponseStatus.STARTED.value,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(response)
        await self.db.flush()
        await self.db.refresh(response)
        return response

    async def get_response_by_token(self, token: str) -> SurveyResponse:
        """Get a response by token."""
        query = (
            select(SurveyResponse)
            .where(SurveyResponse.token == token)
            .options(selectinload(SurveyResponse.answers))
        )
        result = await self.db.execute(query)
        response = result.scalar_one_or_none()
        if not response:
            raise NotFoundError("Response", token)
        return response

    async def get_response(self, tenant_id: str, response_id: int) -> SurveyResponse:
        """Get a response by ID."""
        query = (
            select(SurveyResponse)
            .where(
                SurveyResponse.tenant_id == tenant_id,
                SurveyResponse.id == response_id,
            )
            .options(selectinload(SurveyResponse.answers))
        )
        result = await self.db.execute(query)
        response = result.scalar_one_or_none()
        if not response:
            raise NotFoundError("Response", response_id)
        return response

    async def list_responses(
        self,
        tenant_id: str,
        survey_id: int,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[SurveyResponse]:
        """List responses for a survey."""
        query = select(SurveyResponse).where(
            SurveyResponse.tenant_id == tenant_id,
            SurveyResponse.survey_id == survey_id,
        )

        if status:
            query = query.where(SurveyResponse.status == status)

        query = (
            query.order_by(SurveyResponse.created_at.desc()).offset(skip).limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def save_answer(
        self, tenant_id: str, response_id: int, answer: AnswerSubmit
    ) -> SurveyAnswer:
        """Save or update an answer."""
        # Check if answer already exists
        existing = await self.db.execute(
            select(SurveyAnswer).where(
                SurveyAnswer.response_id == response_id,
                SurveyAnswer.question_id == answer.question_id,
            )
        )
        survey_answer = existing.scalar_one_or_none()

        if survey_answer:
            # Update existing
            survey_answer.value_text = answer.value_text
            survey_answer.value_number = answer.value_number
            survey_answer.value_float = answer.value_float
            survey_answer.value_list = answer.value_list
            survey_answer.value_bool = answer.value_bool
        else:
            # Create new
            survey_answer = SurveyAnswer(
                tenant_id=tenant_id,
                response_id=response_id,
                question_id=answer.question_id,
                value_text=answer.value_text,
                value_number=answer.value_number,
                value_float=answer.value_float,
                value_list=answer.value_list,
                value_bool=answer.value_bool,
            )
            self.db.add(survey_answer)

        await self.db.flush()
        await self.db.refresh(survey_answer)
        return survey_answer

    async def complete_response(
        self, token: str, answers: list[AnswerSubmit] | None = None
    ) -> SurveyResponse:
        """Complete a survey response."""
        response = await self.get_response_by_token(token)

        if response.status == ResponseStatus.COMPLETED.value:
            raise AppError("Response already completed", 400)

        # Save any remaining answers
        if answers:
            for answer in answers:
                await self.save_answer(response.tenant_id, response.id, answer)

        # Calculate duration
        now = datetime.now(UTC)
        duration = int((now - response.started_at).total_seconds())

        # Calculate NPS score if applicable
        nps_score = None
        nps_category = None

        # Get survey to check type
        survey_result = await self.db.execute(
            select(Survey).where(Survey.id == response.survey_id)
        )
        survey = survey_result.scalar_one_or_none()

        if survey and survey.survey_type == "nps":
            # Find NPS question answer
            nps_answer = await self.db.execute(
                select(SurveyAnswer)
                .join(SurveyQuestion)
                .where(
                    SurveyAnswer.response_id == response.id,
                    SurveyQuestion.question_type == QuestionType.NPS.value,
                )
            )
            nps_ans = nps_answer.scalar_one_or_none()
            if nps_ans and nps_ans.value_number is not None:
                nps_score = nps_ans.value_number
                if nps_score <= 6:
                    nps_category = NpsCategory.DETRACTOR.value
                elif nps_score <= 8:
                    nps_category = NpsCategory.PASSIVE.value
                else:
                    nps_category = NpsCategory.PROMOTER.value

        # Update response
        response.status = ResponseStatus.COMPLETED.value
        response.completed_at = now
        response.duration_seconds = duration
        response.nps_score = nps_score
        response.nps_category = nps_category

        # Update survey stats
        if survey:
            survey.response_count = survey.response_count + 1

            # Calculate completion rate
            total = await self.db.execute(
                select(func.count())
                .select_from(SurveyResponse)
                .where(SurveyResponse.survey_id == survey.id)
            )
            completed = await self.db.execute(
                select(func.count())
                .select_from(SurveyResponse)
                .where(
                    SurveyResponse.survey_id == survey.id,
                    SurveyResponse.status == ResponseStatus.COMPLETED.value,
                )
            )
            total_count = total.scalar() or 0
            completed_count = completed.scalar() or 0

            if total_count > 0:
                survey.completion_rate = (completed_count / total_count) * 100

            # Calculate average completion time
            avg_time = await self.db.execute(
                select(func.avg(SurveyResponse.duration_seconds)).where(
                    SurveyResponse.survey_id == survey.id,
                    SurveyResponse.status == ResponseStatus.COMPLETED.value,
                )
            )
            survey.avg_completion_time = int(avg_time.scalar() or 0)

        await self.db.flush()
        await self.db.refresh(response)
        return response

    async def delete_response(self, tenant_id: str, response_id: int) -> None:
        """Delete a response."""
        response = await self.get_response(tenant_id, response_id)
        await self.db.delete(response)


class StatsService:
    """Service for survey statistics."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_survey_stats(self, tenant_id: str, survey_id: int) -> SurveyStats:
        """Get comprehensive survey statistics."""
        # Total responses
        total_result = await self.db.execute(
            select(func.count())
            .select_from(SurveyResponse)
            .where(
                SurveyResponse.tenant_id == tenant_id,
                SurveyResponse.survey_id == survey_id,
            )
        )
        total_responses = total_result.scalar() or 0

        # Completed responses
        completed_result = await self.db.execute(
            select(func.count())
            .select_from(SurveyResponse)
            .where(
                SurveyResponse.tenant_id == tenant_id,
                SurveyResponse.survey_id == survey_id,
                SurveyResponse.status == ResponseStatus.COMPLETED.value,
            )
        )
        completed_responses = completed_result.scalar() or 0

        # Completion rate
        completion_rate = (
            (completed_responses / total_responses * 100) if total_responses > 0 else 0
        )

        # Average completion time
        avg_time_result = await self.db.execute(
            select(func.avg(SurveyResponse.duration_seconds)).where(
                SurveyResponse.tenant_id == tenant_id,
                SurveyResponse.survey_id == survey_id,
                SurveyResponse.status == ResponseStatus.COMPLETED.value,
            )
        )
        avg_completion_time = (
            int(avg_time_result.scalar() or 0) if avg_time_result.scalar() else None
        )

        # NPS stats
        nps_stats = await self._get_nps_stats(tenant_id, survey_id)

        # Question stats
        question_stats = await self._get_question_stats(tenant_id, survey_id)

        return SurveyStats(
            survey_id=survey_id,
            total_responses=total_responses,
            completed_responses=completed_responses,
            completion_rate=round(completion_rate, 1),
            avg_completion_time=avg_completion_time,
            nps=nps_stats,
            questions=question_stats,
        )

    async def _get_nps_stats(self, tenant_id: str, survey_id: int) -> NpsStats | None:
        """Calculate NPS statistics."""
        # Get all NPS scores
        result = await self.db.execute(
            select(SurveyResponse.nps_score).where(
                SurveyResponse.tenant_id == tenant_id,
                SurveyResponse.survey_id == survey_id,
                SurveyResponse.nps_score.isnot(None),
            )
        )
        scores = [r[0] for r in result.all()]

        if not scores:
            return None

        total = len(scores)
        promoters = len([s for s in scores if s >= 9])
        passives = len([s for s in scores if 7 <= s <= 8])
        detractors = len([s for s in scores if s <= 6])

        promoter_pct = (promoters / total) * 100
        passive_pct = (passives / total) * 100
        detractor_pct = (detractors / total) * 100

        nps_score = int(promoter_pct - detractor_pct)

        return NpsStats(
            score=nps_score,
            total_responses=total,
            promoters=promoters,
            passives=passives,
            detractors=detractors,
            promoter_percentage=round(promoter_pct, 1),
            passive_percentage=round(passive_pct, 1),
            detractor_percentage=round(detractor_pct, 1),
        )

    async def _get_question_stats(
        self, tenant_id: str, survey_id: int
    ) -> list[QuestionStats]:
        """Get statistics for each question."""
        # Get all questions
        questions_result = await self.db.execute(
            select(SurveyQuestion)
            .where(
                SurveyQuestion.tenant_id == tenant_id,
                SurveyQuestion.survey_id == survey_id,
            )
            .order_by(SurveyQuestion.position)
        )
        questions = questions_result.scalars().all()

        stats = []
        for q in questions:
            # Get answers for this question
            answers_result = await self.db.execute(
                select(SurveyAnswer).where(SurveyAnswer.question_id == q.id)
            )
            answers = list(answers_result.scalars().all())

            q_stat = QuestionStats(
                question_id=q.id,
                question_title=q.title,
                question_type=q.question_type,
                total_answers=len(answers),
            )

            if q.question_type in [
                QuestionType.SINGLE_CHOICE.value,
                QuestionType.MULTIPLE_CHOICE.value,
            ]:
                # Count options
                option_counts = {}
                for a in answers:
                    if a.value_text:
                        option_counts[a.value_text] = (
                            option_counts.get(a.value_text, 0) + 1
                        )
                    elif a.value_list:
                        for v in a.value_list:
                            option_counts[v] = option_counts.get(v, 0) + 1
                q_stat.option_counts = option_counts

            elif q.question_type in [
                QuestionType.SCALE.value,
                QuestionType.NPS.value,
                QuestionType.RATING.value,
            ]:
                # Numeric stats
                numbers = [
                    a.value_number for a in answers if a.value_number is not None
                ]
                if numbers:
                    q_stat.average = round(sum(numbers) / len(numbers), 2)
                    q_stat.min_value = min(numbers)
                    q_stat.max_value = max(numbers)
                    # Distribution
                    distribution = {}
                    for n in numbers:
                        distribution[n] = distribution.get(n, 0) + 1
                    q_stat.distribution = distribution

            elif q.question_type == QuestionType.YES_NO.value:
                yes_count = len([a for a in answers if a.value_bool is True])
                no_count = len([a for a in answers if a.value_bool is False])
                q_stat.option_counts = {"Ja": yes_count, "Nein": no_count}

            stats.append(q_stat)

        return stats
