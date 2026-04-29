"""Engagement Brain - Central AI for multi-channel engagement orchestration.

The Brain has three layers:
1. Setup-Layer: Pipeline creation via chat, prerequisites analysis, playbook generation
2. Runtime-Layer: Contact analysis, action dispatch, event handling
3. Knowledge-Layer: Pipeline/playbook storage, activity history, success patterns
"""

import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.engagement.brain_prompts import (
    CONTACT_ANALYSIS_PROMPT,
    MODULE_PROMPT_GENERATION,
    MODULE_REQUIREMENTS,
    PIPELINE_SETUP_SYSTEM,
    PLAYBOOK_GENERATION_PROMPT,
    RESPONSE_ANALYSIS_PROMPT,
)
from app.engagement.models import (
    ContactActivity,
    EngagementPipeline,
    PendingAction,
    PipelineEnrollment,
)
from app.services.llm import LLMService


class PrerequisiteStatus(str, Enum):
    """Status of a prerequisite check."""

    READY = "ready"
    WARNING = "warning"
    BLOCKER = "blocker"


@dataclass
class PrerequisiteItem:
    """Single prerequisite check result."""

    channel: str
    component: str
    status: PrerequisiteStatus
    message: str
    action_required: str | None = None


@dataclass
class PrerequisiteReport:
    """Full prerequisite check report."""

    items: list[PrerequisiteItem]

    @property
    def has_blockers(self) -> bool:
        return any(item.status == PrerequisiteStatus.BLOCKER for item in self.items)

    @property
    def has_warnings(self) -> bool:
        return any(item.status == PrerequisiteStatus.WARNING for item in self.items)

    @property
    def all_ready(self) -> bool:
        return all(item.status == PrerequisiteStatus.READY for item in self.items)

    def to_dict(self) -> dict:
        return {
            "items": [
                {
                    "channel": item.channel,
                    "component": item.component,
                    "status": item.status.value,
                    "message": item.message,
                    "action_required": item.action_required,
                }
                for item in self.items
            ],
            "has_blockers": self.has_blockers,
            "has_warnings": self.has_warnings,
            "all_ready": self.all_ready,
        }


@dataclass
class ActionRecommendation:
    """Recommendation for next action from the Brain."""

    channel: str
    action: str
    content_suggestion: str | None
    new_stage: str | None
    needs_approval: bool
    reasoning: str


@dataclass
class ResponseAnalysis:
    """Analysis of an incoming response."""

    sentiment: str
    intent: str
    urgency: str
    new_stage: str | None
    recommended_action: str
    draft_response: str | None
    needs_human: bool
    reasoning: str


class EngagementBrain:
    """Central Brain for engagement orchestration.

    Handles:
    - Pipeline setup via chat dialog
    - Prerequisites checking (modules, APIs, logins)
    - Playbook generation
    - Module prompt generation
    - Contact analysis and next-step decisions
    - Response analysis
    """

    def __init__(
        self,
        db: AsyncSession,
        tenant_id: str,
        tenant_config: dict | None = None,
    ) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self.tenant_config = tenant_config or {}
        self.llm = LLMService(tenant_config)

    # =========================================================================
    # SETUP LAYER - Pipeline Creation
    # =========================================================================

    async def process_setup_message(
        self,
        user_message: str,
        conversation_history: list[dict],
    ) -> dict:
        """Process a message in the pipeline setup chat.

        Args:
            user_message: The user's message
            conversation_history: Previous messages in the conversation

        Returns:
            Response dict with 'message' and optionally 'pipeline_config' if ready
        """
        # Add user message to history
        messages = [*conversation_history, {"role": "user", "content": user_message}]

        # Call LLM with setup system prompt
        response = await self.llm.generate_with_messages(
            provider="anthropic",
            model=settings.llm_model_content,
            system_prompt=PIPELINE_SETUP_SYSTEM,
            messages=messages,
            temperature=0.7,
            max_tokens=1024,
        )

        result = {"message": response, "pipeline_config": None}

        # Check if pipeline is ready
        if "[PIPELINE_READY]" in response:
            # Extract JSON from response
            try:
                json_match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
                if json_match:
                    config = json.loads(json_match.group(1))
                    result["pipeline_config"] = config
                    # Remove the JSON block from the displayed message
                    result["message"] = response.split("[PIPELINE_READY]")[0].strip()
            except json.JSONDecodeError as e:
                logger.warning(
                    "Failed to parse pipeline config JSON: {err}", err=str(e)
                )

        return result

    # =========================================================================
    # SETUP LAYER - Prerequisites Analysis
    # =========================================================================

    async def check_prerequisites(self, channels: list[str]) -> PrerequisiteReport:
        """Check all prerequisites for the requested channels.

        Args:
            channels: List of channels to check (linkedin, email, phone, etc.)

        Returns:
            PrerequisiteReport with all check results
        """
        items: list[PrerequisiteItem] = []

        for channel in channels:
            channel_items = await self._check_channel_prerequisites(channel)
            items.extend(channel_items)

        return PrerequisiteReport(items=items)

    async def _check_channel_prerequisites(
        self, channel: str
    ) -> list[PrerequisiteItem]:
        """Check prerequisites for a specific channel."""
        items: list[PrerequisiteItem] = []

        if channel == "linkedin":
            items.extend(await self._check_linkedin_prerequisites())
        elif channel == "email":
            items.extend(await self._check_email_prerequisites())
        elif channel == "phone":
            items.extend(await self._check_phone_prerequisites())
        elif channel == "whatsapp":
            items.extend(await self._check_whatsapp_prerequisites())
        elif channel == "letter":
            items.extend(await self._check_letter_prerequisites())

        return items

    async def _check_linkedin_prerequisites(self) -> list[PrerequisiteItem]:
        """Check LinkedIn module prerequisites."""
        items = []

        # Check if module is installed (has manifest)
        try:
            from app.linkedin import __manifest__ as linkedin_manifest  # noqa: F401

            module_installed = True
        except ImportError:
            module_installed = False

        if not module_installed:
            items.append(
                PrerequisiteItem(
                    channel="linkedin",
                    component="module",
                    status=PrerequisiteStatus.BLOCKER,
                    message="LinkedIn-Modul nicht installiert",
                    action_required="LinkedIn-Modul installieren",
                )
            )
            return items

        items.append(
            PrerequisiteItem(
                channel="linkedin",
                component="module",
                status=PrerequisiteStatus.READY,
                message="LinkedIn-Modul installiert",
            )
        )

        # Check for LinkedIn accounts
        try:
            from app.linkedin.models import LinkedInAccount

            result = await self.db.execute(
                select(LinkedInAccount).where(
                    LinkedInAccount.tenant_id == self.tenant_id,
                    LinkedInAccount.is_active.is_(True),
                )
            )
            accounts = result.scalars().all()

            if not accounts:
                items.append(
                    PrerequisiteItem(
                        channel="linkedin",
                        component="account",
                        status=PrerequisiteStatus.BLOCKER,
                        message="Kein LinkedIn-Account verbunden",
                        action_required="LinkedIn-Account in den Einstellungen verbinden",
                    )
                )
            else:
                items.append(
                    PrerequisiteItem(
                        channel="linkedin",
                        component="account",
                        status=PrerequisiteStatus.READY,
                        message=f"{len(accounts)} LinkedIn-Account(s) aktiv",
                    )
                )
        except Exception as e:
            logger.warning("LinkedIn account check failed: {err}", err=str(e))
            items.append(
                PrerequisiteItem(
                    channel="linkedin",
                    component="account",
                    status=PrerequisiteStatus.WARNING,
                    message="Account-Status konnte nicht geprüft werden",
                )
            )

        return items

    async def _check_email_prerequisites(self) -> list[PrerequisiteItem]:
        """Check Email module prerequisites."""
        items = []

        # Check if module is installed
        try:
            from app.emailmarketing import __manifest__ as email_manifest  # noqa: F401

            module_installed = True
        except ImportError:
            module_installed = False

        if not module_installed:
            items.append(
                PrerequisiteItem(
                    channel="email",
                    component="module",
                    status=PrerequisiteStatus.BLOCKER,
                    message="Email-Marketing-Modul nicht installiert",
                    action_required="Email-Marketing-Modul installieren",
                )
            )
            return items

        items.append(
            PrerequisiteItem(
                channel="email",
                component="module",
                status=PrerequisiteStatus.READY,
                message="Email-Marketing-Modul installiert",
            )
        )

        # Check for email providers
        try:
            from app.emailmarketing.models import EmailProvider

            result = await self.db.execute(
                select(EmailProvider).where(
                    EmailProvider.tenant_id == self.tenant_id,
                    EmailProvider.is_active.is_(True),
                )
            )
            providers = result.scalars().all()

            if not providers:
                items.append(
                    PrerequisiteItem(
                        channel="email",
                        component="provider",
                        status=PrerequisiteStatus.BLOCKER,
                        message="Kein Email-Provider konfiguriert",
                        action_required="SMTP-Provider in den Einstellungen konfigurieren",
                    )
                )
            else:
                items.append(
                    PrerequisiteItem(
                        channel="email",
                        component="provider",
                        status=PrerequisiteStatus.READY,
                        message=f"{len(providers)} Email-Provider aktiv",
                    )
                )
        except Exception as e:
            logger.warning("Email provider check failed: {err}", err=str(e))
            items.append(
                PrerequisiteItem(
                    channel="email",
                    component="provider",
                    status=PrerequisiteStatus.WARNING,
                    message="Provider-Status konnte nicht geprüft werden",
                )
            )

        return items

    async def _check_phone_prerequisites(self) -> list[PrerequisiteItem]:
        """Check Phone/CRM prerequisites."""
        items = []

        # Phone works via CRM module - check if CRM is available
        try:
            from app.crm import __manifest__ as crm_manifest  # noqa: F401

            items.append(
                PrerequisiteItem(
                    channel="phone",
                    component="module",
                    status=PrerequisiteStatus.READY,
                    message="Telefon-Tracking via CRM-Modul verfügbar",
                )
            )
        except ImportError:
            items.append(
                PrerequisiteItem(
                    channel="phone",
                    component="module",
                    status=PrerequisiteStatus.WARNING,
                    message="CRM-Modul nicht installiert - Telefon-Tracking eingeschränkt",
                    action_required="CRM-Modul für vollständiges Telefon-Tracking installieren",
                )
            )

        return items

    async def _check_whatsapp_prerequisites(self) -> list[PrerequisiteItem]:
        """Check WhatsApp module prerequisites."""
        items = []

        try:
            from app.whatsapp import __manifest__ as wa_manifest  # noqa: F401

            module_installed = True
        except ImportError:
            module_installed = False

        if not module_installed:
            items.append(
                PrerequisiteItem(
                    channel="whatsapp",
                    component="module",
                    status=PrerequisiteStatus.BLOCKER,
                    message="WhatsApp-Modul nicht installiert",
                    action_required="WhatsApp-Modul installieren",
                )
            )
            return items

        items.append(
            PrerequisiteItem(
                channel="whatsapp",
                component="module",
                status=PrerequisiteStatus.READY,
                message="WhatsApp-Modul installiert",
            )
        )

        # Check for WhatsApp accounts
        try:
            from app.whatsapp.models import WhatsAppAccount

            result = await self.db.execute(
                select(WhatsAppAccount).where(
                    WhatsAppAccount.tenant_id == self.tenant_id,
                    WhatsAppAccount.is_active.is_(True),
                )
            )
            accounts = result.scalars().all()

            if not accounts:
                items.append(
                    PrerequisiteItem(
                        channel="whatsapp",
                        component="account",
                        status=PrerequisiteStatus.BLOCKER,
                        message="Kein WhatsApp Business Account verbunden",
                        action_required="WhatsApp Business Account verbinden",
                    )
                )
            else:
                items.append(
                    PrerequisiteItem(
                        channel="whatsapp",
                        component="account",
                        status=PrerequisiteStatus.READY,
                        message=f"{len(accounts)} WhatsApp-Account(s) aktiv",
                    )
                )
        except Exception as e:
            logger.warning("WhatsApp account check failed: {err}", err=str(e))
            items.append(
                PrerequisiteItem(
                    channel="whatsapp",
                    component="account",
                    status=PrerequisiteStatus.WARNING,
                    message="Account-Status konnte nicht geprüft werden",
                )
            )

        return items

    async def _check_letter_prerequisites(self) -> list[PrerequisiteItem]:
        """Check Letter (Letterxpress) prerequisites for this tenant.

        Looks at three things:
        1. Letterxpress credentials configured in module_parameters
        2. At least one active letter template exists
        3. Letterxpress balance is above the warning threshold
        """
        from app.letter.letterxpress_client import LetterxpressError
        from app.letter.models import LetterTemplate
        from app.letter.settings_service import (
            LetterSettingsError,
            get_letter_settings,
            get_letterxpress_client,
        )

        items: list[PrerequisiteItem] = []

        # 1. Credentials
        try:
            settings = await get_letter_settings(self.db, self.tenant_id)
        except Exception as exc:
            return [
                PrerequisiteItem(
                    channel="letter",
                    component="settings",
                    status=PrerequisiteStatus.BLOCKER,
                    message=f"Settings nicht lesbar: {exc}",
                    action_required="Letter → Einstellungen aufrufen",
                )
            ]

        if not settings.is_complete:
            items.append(
                PrerequisiteItem(
                    channel="letter",
                    component="credentials",
                    status=PrerequisiteStatus.BLOCKER,
                    message="Letterxpress-Zugangsdaten fehlen",
                    action_required="Letter → Einstellungen → API-Key + Username eintragen",
                )
            )
        else:
            items.append(
                PrerequisiteItem(
                    channel="letter",
                    component="credentials",
                    status=PrerequisiteStatus.READY,
                    message=f"Letterxpress konfiguriert ({settings.mode}-Mode)",
                )
            )

        # 2. At least one active template
        tpl_q = (
            select(LetterTemplate)
            .where(
                LetterTemplate.tenant_id == self.tenant_id,
                LetterTemplate.is_active.is_(True),
            )
            .limit(1)
        )
        has_template = (await self.db.execute(tpl_q)).scalar_one_or_none() is not None
        if has_template:
            items.append(
                PrerequisiteItem(
                    channel="letter",
                    component="template",
                    status=PrerequisiteStatus.READY,
                    message="Mindestens ein aktives Brief-Template vorhanden",
                )
            )
        else:
            items.append(
                PrerequisiteItem(
                    channel="letter",
                    component="template",
                    status=PrerequisiteStatus.BLOCKER,
                    message="Kein aktives Brief-Template",
                    action_required="Letter → Templates → Neues Template anlegen",
                )
            )

        # 3. Balance (best-effort — only when credentials are there and live)
        if settings.is_complete:
            try:
                client = await get_letterxpress_client(self.db, self.tenant_id)
                balance = await client.get_balance()
                if balance.balance < 5:
                    items.append(
                        PrerequisiteItem(
                            channel="letter",
                            component="balance",
                            status=PrerequisiteStatus.WARNING,
                            message=(
                                f"Letterxpress-Guthaben niedrig: "
                                f"{balance.balance} {balance.currency}"
                            ),
                            action_required="Guthaben aufladen vor Live-Versand",
                        )
                    )
                else:
                    items.append(
                        PrerequisiteItem(
                            channel="letter",
                            component="balance",
                            status=PrerequisiteStatus.READY,
                            message=(f"Guthaben: {balance.balance} {balance.currency}"),
                        )
                    )
            except (LetterSettingsError, LetterxpressError) as exc:
                items.append(
                    PrerequisiteItem(
                        channel="letter",
                        component="balance",
                        status=PrerequisiteStatus.WARNING,
                        message=f"Balance-Abfrage fehlgeschlagen: {exc}",
                        action_required="Verbindung in Letter → Einstellungen testen",
                    )
                )

        return items

    # =========================================================================
    # SETUP LAYER - Playbook & Prompt Generation
    # =========================================================================

    async def generate_playbook(
        self,
        pipeline_config: dict,
    ) -> str:
        """Generate a playbook for a pipeline.

        Args:
            pipeline_config: Pipeline configuration from setup chat

        Returns:
            Generated playbook text
        """
        prompt = PLAYBOOK_GENERATION_PROMPT.format(
            name=pipeline_config.get("name", ""),
            product_name=pipeline_config.get("product_name", ""),
            product_description=pipeline_config.get("product_description", ""),
            target_audience=pipeline_config.get("target_audience", ""),
            channels=", ".join(pipeline_config.get("channels", [])),
            goal=pipeline_config.get("goal", ""),
            tone_of_voice=pipeline_config.get("tone_of_voice", "professionell"),
            playbook_notes=pipeline_config.get("playbook_notes", ""),
        )

        playbook = await self.llm.generate(task="content", prompt=prompt)
        return playbook

    async def generate_module_prompts(
        self,
        pipeline_config: dict,
    ) -> dict[str, str]:
        """Generate module-specific LLM prompts for a pipeline.

        Args:
            pipeline_config: Pipeline configuration

        Returns:
            Dict mapping module name to generated prompt
        """
        prompts: dict[str, str] = {}
        channels = pipeline_config.get("channels", [])

        for channel in channels:
            if channel in MODULE_REQUIREMENTS:
                prompt = await self._generate_single_module_prompt(
                    channel, pipeline_config
                )
                prompts[channel] = prompt

        return prompts

    async def _generate_single_module_prompt(
        self,
        module: str,
        pipeline_config: dict,
    ) -> str:
        """Generate prompt for a single module."""
        requirements = MODULE_REQUIREMENTS.get(module, "")

        prompt = MODULE_PROMPT_GENERATION.format(
            module=module,
            product_name=pipeline_config.get("product_name", ""),
            product_description=pipeline_config.get("product_description", ""),
            target_audience=pipeline_config.get("target_audience", ""),
            goal=pipeline_config.get("goal", ""),
            tone_of_voice=pipeline_config.get("tone_of_voice", "professionell"),
            module_requirements=requirements,
        )

        return await self.llm.generate(task="content", prompt=prompt)

    async def save_module_prompts(
        self,
        pipeline: EngagementPipeline,
        prompts: dict[str, str],
    ) -> None:
        """Save generated module prompts to module_parameters.

        Args:
            pipeline: The pipeline these prompts belong to
            prompts: Dict mapping module name to prompt text
        """
        from app.ai.schemas import ModuleParameterCreate, ModuleParameterUpdate
        from app.ai.service import AISetupService

        ai_service = AISetupService(self.db, self.tenant_id)

        for module, prompt_text in prompts.items():
            variable = f"pipeline_{pipeline.slug}_prompt"
            description = f"Engagement-Prompt für Pipeline '{pipeline.name}' ({module})"

            try:
                # Try to update existing, or create new
                existing = await ai_service.get_parameter(module, variable)
                if existing:
                    await ai_service.update_parameter(
                        module,
                        variable,
                        ModuleParameterUpdate(
                            description=description,
                            value=prompt_text,
                        ),
                    )
                else:
                    await ai_service.create_parameter(
                        module,
                        ModuleParameterCreate(
                            variable=variable,
                            description=description,
                            value=prompt_text,
                            var_type="text",
                        ),
                    )
                logger.info(
                    "Module prompt saved: {module}/{variable}",
                    module=module,
                    variable=variable,
                )
            except Exception as e:
                logger.error(
                    "Failed to save module prompt: {module}/{variable} - {err}",
                    module=module,
                    variable=variable,
                    err=str(e),
                )

    # =========================================================================
    # RUNTIME LAYER - Contact Analysis
    # =========================================================================

    async def analyze_contact(
        self,
        enrollment: PipelineEnrollment,
        activities: list[ContactActivity],
    ) -> ActionRecommendation:
        """Analyze a contact and recommend the next action.

        Args:
            enrollment: The pipeline enrollment
            activities: Recent activities for this contact

        Returns:
            ActionRecommendation with next step details
        """
        pipeline = enrollment.pipeline
        contact = enrollment.contact

        # Format activities for prompt
        activities_text = self._format_activities(activities)

        prompt = CONTACT_ANALYSIS_PROMPT.format(
            pipeline_name=pipeline.name,
            product_name=pipeline.product_name or "",
            goal=pipeline.goal or "",
            channels=", ".join(pipeline.channels),
            playbook=pipeline.playbook or "Kein Playbook definiert",
            contact_name=contact.name,
            contact_position=contact.position or "unbekannt",
            contact_company=contact.company_name or "unbekannt",
            current_stage=enrollment.stage,
            touch_count=enrollment.touch_count,
            last_touch=enrollment.last_touch_at.isoformat()
            if enrollment.last_touch_at
            else "nie",
            last_response=enrollment.last_response_at.isoformat()
            if enrollment.last_response_at
            else "nie",
            activities=activities_text,
        )

        try:
            response = await self.llm.generate_json(task="analysis", prompt=prompt)

            return ActionRecommendation(
                channel=response.get("channel", "email"),
                action=response.get("action", "send_message"),
                content_suggestion=response.get("content_suggestion"),
                new_stage=response.get("new_stage"),
                needs_approval=response.get("needs_approval", True),
                reasoning=response.get("reasoning", ""),
            )
        except Exception as e:
            logger.error("Contact analysis failed: {err}", err=str(e))
            # Return safe default
            return ActionRecommendation(
                channel=pipeline.channels[0] if pipeline.channels else "email",
                action="send_message",
                content_suggestion=None,
                new_stage=None,
                needs_approval=True,
                reasoning=f"Analyse fehlgeschlagen: {e}",
            )

    def _format_activities(self, activities: list[ContactActivity]) -> str:
        """Format activities for prompt inclusion."""
        if not activities:
            return "Keine bisherigen Aktivitäten"

        lines = []
        for act in activities[:10]:  # Limit to recent 10
            direction = "→" if act.direction == "outbound" else "←"
            time = act.performed_at.strftime("%d.%m.%Y %H:%M")
            lines.append(
                f"- [{time}] {direction} {act.channel}: {act.activity_type}"
                + (f" - {act.subject}" if act.subject else "")
            )

        return "\n".join(lines)

    # =========================================================================
    # RUNTIME LAYER - Response Analysis
    # =========================================================================

    async def analyze_response(
        self,
        enrollment: PipelineEnrollment,
        incoming_activity: ContactActivity,
        last_outbound: ContactActivity | None,
    ) -> ResponseAnalysis:
        """Analyze an incoming response from a contact.

        Args:
            enrollment: The pipeline enrollment
            incoming_activity: The incoming message/activity
            last_outbound: The last outbound message (if any)

        Returns:
            ResponseAnalysis with sentiment, intent, and recommendations
        """
        pipeline = enrollment.pipeline
        contact = enrollment.contact

        prompt = RESPONSE_ANALYSIS_PROMPT.format(
            pipeline_name=pipeline.name,
            contact_name=contact.name,
            contact_position=contact.position or "unbekannt",
            contact_company=contact.company_name or "unbekannt",
            current_stage=enrollment.stage,
            channel=incoming_activity.channel,
            last_outbound=last_outbound.content
            if last_outbound
            else "Keine vorherige Nachricht",
            incoming_message=incoming_activity.content
            or incoming_activity.subject
            or "Kein Inhalt",
        )

        try:
            response = await self.llm.generate_json(task="analysis", prompt=prompt)

            return ResponseAnalysis(
                sentiment=response.get("sentiment", "neutral"),
                intent=response.get("intent", "other"),
                urgency=response.get("urgency", "normal"),
                new_stage=response.get("new_stage"),
                recommended_action=response.get("recommended_action", ""),
                draft_response=response.get("draft_response"),
                needs_human=response.get("needs_human", True),
                reasoning=response.get("reasoning", ""),
            )
        except Exception as e:
            logger.error("Response analysis failed: {err}", err=str(e))
            return ResponseAnalysis(
                sentiment="neutral",
                intent="other",
                urgency="normal",
                new_stage=None,
                recommended_action="Manuelle Prüfung erforderlich",
                draft_response=None,
                needs_human=True,
                reasoning=f"Analyse fehlgeschlagen: {e}",
            )

    # =========================================================================
    # RUNTIME LAYER - Action Creation
    # =========================================================================

    async def create_action_for_enrollment(
        self,
        enrollment: PipelineEnrollment,
        recommendation: ActionRecommendation,
    ) -> PendingAction:
        """Create a pending action based on the brain's recommendation.

        Args:
            enrollment: The enrollment to create action for
            recommendation: The brain's recommendation

        Returns:
            Created PendingAction
        """
        pipeline = enrollment.pipeline
        contact = enrollment.contact

        # Build context for the module
        context = {
            "contact_id": contact.id,
            "contact_name": contact.name,
            "contact_email": contact.email,
            "contact_position": contact.position,
            "contact_company": contact.company_name,
            "pipeline_id": pipeline.id,
            "pipeline_name": pipeline.name,
            "product_name": pipeline.product_name,
            "product_description": pipeline.product_description,
            "goal": pipeline.goal,
            "tone_of_voice": pipeline.tone_of_voice,
            "touch_count": enrollment.touch_count,
            "stage": enrollment.stage,
        }

        # Check auto_actions to determine if approval is needed
        auto_actions = pipeline.auto_actions or {}
        needs_approval = recommendation.needs_approval
        if recommendation.action in auto_actions:
            needs_approval = not auto_actions[recommendation.action]

        action = PendingAction(
            tenant_id=self.tenant_id,
            contact_id=contact.id,
            pipeline_id=pipeline.id,
            enrollment_id=enrollment.id,
            module=recommendation.channel,
            action_type=recommendation.action,
            context=context,
            suggested_content=recommendation.content_suggestion,
            priority="normal",
            needs_approval=needs_approval,
            status="ready_for_approval" if needs_approval else "approved",
        )

        self.db.add(action)
        await self.db.flush()
        await self.db.refresh(action)

        logger.info(
            "Created pending action: {module}:{action} for contact {contact}",
            module=recommendation.channel,
            action=recommendation.action,
            contact=contact.id,
        )

        return action

    # =========================================================================
    # KNOWLEDGE LAYER - Module Capabilities
    # =========================================================================

    def get_available_channels(self) -> list[dict[str, Any]]:
        """Get list of available channels with their capabilities."""
        return [
            {
                "id": "linkedin",
                "name": "LinkedIn",
                "actions": [
                    "connection_request",
                    "send_message",
                    "send_inmail",
                    "profile_view",
                ],
                "requires_account": True,
                "auto_capable": True,
            },
            {
                "id": "email",
                "name": "Email",
                "actions": [
                    "send_email",
                    "send_sequence",
                ],
                "requires_account": True,
                "auto_capable": True,
            },
            {
                "id": "phone",
                "name": "Telefon",
                "actions": [
                    "schedule_call",
                    "log_call",
                ],
                "requires_account": False,
                "auto_capable": False,
            },
            {
                "id": "whatsapp",
                "name": "WhatsApp",
                "actions": [
                    "send_message",
                    "send_template",
                ],
                "requires_account": True,
                "auto_capable": True,
            },
            {
                "id": "letter",
                "name": "Brief",
                "actions": [
                    "create_letter",
                ],
                "requires_account": False,
                "auto_capable": False,
            },
        ]
