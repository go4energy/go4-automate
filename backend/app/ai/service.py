"""AI Setup service - business logic for prompts, context, and onboarding."""

import json
import re
from typing import Any

from loguru import logger
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.prompt_generator import PromptGenerator
from app.ai.schemas import (
    ModuleContextUpdate,
    ModuleParameterCreate,
    ModuleParameterUpdate,
    OnboardingChatResponse,
    PromptCreate,
    PromptUpdate,
)
from app.models.chat_message import ChatMessage
from app.models.conversation import Conversation
from app.models.module_context import ModuleContext
from app.models.module_parameter import ModuleParameter
from app.models.prompt import Prompt
from app.services.llm import LLMService


class AISetupService:
    """Service for AI setup operations."""

    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    # ═══════════════════════════════════════════════════════════════════════════
    # Module Context Operations
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_module_context(self, module: str) -> ModuleContext | None:
        """Get context for a specific module."""
        result = await self.db.execute(
            select(ModuleContext).where(
                and_(
                    ModuleContext.tenant_id == self.tenant_id,
                    ModuleContext.module == module,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_or_create_module_context(self, module: str) -> ModuleContext:
        """Get or create context for a module."""
        context = await self.get_module_context(module)
        if not context:
            context = ModuleContext(
                tenant_id=self.tenant_id,
                module=module,
                context_data={},
                onboarding_completed=False,
            )
            self.db.add(context)
            await self.db.commit()
            await self.db.refresh(context)
        return context

    async def update_module_context(
        self, module: str, data: ModuleContextUpdate
    ) -> ModuleContext:
        """Update module context."""
        context = await self.get_or_create_module_context(module)

        if data.context_data is not None:
            # Merge new data with existing
            context.context_data = {**context.context_data, **data.context_data}
        if data.onboarding_completed is not None:
            context.onboarding_completed = data.onboarding_completed
        if data.onboarding_notes is not None:
            context.onboarding_notes = data.onboarding_notes

        await self.db.commit()
        await self.db.refresh(context)
        return context

    async def set_context_variable(
        self, module: str, key: str, value: Any
    ) -> ModuleContext:
        """Set a single variable in module context."""
        context = await self.get_or_create_module_context(module)
        context.set_variable(key, value)
        # Mark as modified for SQLAlchemy to detect the change
        from sqlalchemy.orm.attributes import flag_modified

        flag_modified(context, "context_data")
        await self.db.commit()
        await self.db.refresh(context)
        return context

    async def delete_context_variable(self, module: str, key: str) -> ModuleContext:
        """Delete a variable from module context."""
        context = await self.get_or_create_module_context(module)
        context.delete_variable(key)
        from sqlalchemy.orm.attributes import flag_modified

        flag_modified(context, "context_data")
        await self.db.commit()
        await self.db.refresh(context)
        return context

    async def reset_onboarding(self, module: str) -> ModuleContext:
        """Reset onboarding status for a module."""
        context = await self.get_or_create_module_context(module)
        context.onboarding_completed = False
        context.context_data = {}
        context.onboarding_notes = None

        # Also reset parameter values
        await self.reset_parameter_values(module)

        await self.db.commit()
        await self.db.refresh(context)
        return context

    # ═══════════════════════════════════════════════════════════════════════════
    # Module Parameter Operations
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_module_parameters(self, module: str) -> list[ModuleParameter]:
        """Get all parameters for a module, ordered by sort_order."""
        result = await self.db.execute(
            select(ModuleParameter)
            .where(
                and_(
                    ModuleParameter.tenant_id == self.tenant_id,
                    ModuleParameter.module == module,
                )
            )
            .order_by(ModuleParameter.sort_order, ModuleParameter.variable)
        )
        return list(result.scalars().all())

    async def get_parameter(self, module: str, variable: str) -> ModuleParameter | None:
        """Get a specific parameter by variable name."""
        result = await self.db.execute(
            select(ModuleParameter).where(
                and_(
                    ModuleParameter.tenant_id == self.tenant_id,
                    ModuleParameter.module == module,
                    ModuleParameter.variable == variable,
                )
            )
        )
        return result.scalar_one_or_none()

    async def create_parameter(
        self, module: str, data: ModuleParameterCreate
    ) -> ModuleParameter:
        """Create a new parameter for a module."""
        param = ModuleParameter(
            tenant_id=self.tenant_id,
            module=module,
            variable=data.variable,
            description=data.description,
            value=data.value,
            var_type=data.var_type,
            required=data.required,
            sort_order=data.sort_order,
        )
        self.db.add(param)
        await self.db.commit()
        await self.db.refresh(param)
        return param

    async def update_parameter(
        self, module: str, variable: str, data: ModuleParameterUpdate
    ) -> ModuleParameter | None:
        """Update a parameter."""
        param = await self.get_parameter(module, variable)
        if not param:
            return None

        if data.description is not None:
            param.description = data.description
        if data.value is not None:
            param.value = data.value
        if data.var_type is not None:
            param.var_type = data.var_type
        if data.required is not None:
            param.required = data.required
        if data.sort_order is not None:
            param.sort_order = data.sort_order

        await self.db.commit()
        await self.db.refresh(param)
        return param

    async def set_parameter_value(
        self, module: str, variable: str, value: str | None
    ) -> ModuleParameter | None:
        """Set just the value of a parameter."""
        param = await self.get_parameter(module, variable)
        if not param:
            return None

        param.value = value
        await self.db.commit()
        await self.db.refresh(param)
        return param

    async def delete_parameter(self, module: str, variable: str) -> bool:
        """Delete a parameter."""
        param = await self.get_parameter(module, variable)
        if not param:
            return False

        await self.db.delete(param)
        await self.db.commit()
        return True

    async def reset_parameter_values(self, module: str) -> int:
        """Reset all parameter values to None for a module."""
        params = await self.get_module_parameters(module)
        count = 0
        for param in params:
            if param.value is not None:
                param.value = None
                count += 1
        if count > 0:
            await self.db.commit()
        return count

    async def bulk_create_parameters(
        self, module: str, parameters: list[ModuleParameterCreate]
    ) -> list[ModuleParameter]:
        """Create multiple parameters at once."""
        created = []
        for data in parameters:
            existing = await self.get_parameter(module, data.variable)
            if not existing:
                param = await self.create_parameter(module, data)
                created.append(param)
        return created

    def build_parameters_schema(
        self, parameters: list[ModuleParameter]
    ) -> dict[str, dict]:
        """Build a variables schema from parameters for extraction."""
        schema = {}
        for param in parameters:
            schema[param.variable] = {
                "type": param.var_type,
                "label": param.description,
                "required": param.required,
            }
        return schema

    # ═══════════════════════════════════════════════════════════════════════════
    # Prompt Operations
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_module_prompts(
        self, module: str, prompt_type: str | None = None
    ) -> list[Prompt]:
        """Get all prompts for a module, optionally filtered by type."""
        # Ensure default prompts exist for this module
        await self.ensure_default_prompts(module)

        query = select(Prompt).where(
            and_(
                Prompt.tenant_id == self.tenant_id,
                Prompt.module == module,
                Prompt.is_active == True,  # noqa: E712
            )
        )
        if prompt_type:
            query = query.where(Prompt.prompt_type == prompt_type)

        result = await self.db.execute(query.order_by(Prompt.sort_order, Prompt.name))
        return list(result.scalars().all())

    async def get_prompt_by_slug(self, module: str, slug: str) -> Prompt | None:
        """Get a specific prompt by module and slug."""
        result = await self.db.execute(
            select(Prompt).where(
                and_(
                    Prompt.tenant_id == self.tenant_id,
                    Prompt.module == module,
                    Prompt.slug == slug,
                    Prompt.is_active == True,  # noqa: E712
                )
            )
        )
        return result.scalar_one_or_none()

    async def create_prompt(self, data: PromptCreate) -> Prompt:
        """Create a new prompt."""
        prompt = Prompt(
            tenant_id=self.tenant_id,
            **data.model_dump(),
            is_system=False,
            version=1,
        )
        self.db.add(prompt)
        await self.db.commit()
        await self.db.refresh(prompt)
        return prompt

    async def update_prompt(self, prompt_id: int, data: PromptUpdate) -> Prompt | None:
        """Update an existing prompt."""
        result = await self.db.execute(
            select(Prompt).where(
                and_(
                    Prompt.id == prompt_id,
                    Prompt.tenant_id == self.tenant_id,
                )
            )
        )
        prompt = result.scalar_one_or_none()
        if not prompt:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(prompt, key, value)

        await self.db.commit()
        await self.db.refresh(prompt)
        return prompt

    async def delete_prompt(self, prompt_id: int) -> bool:
        """Soft delete a prompt (set is_active=False)."""
        result = await self.db.execute(
            select(Prompt).where(
                and_(
                    Prompt.id == prompt_id,
                    Prompt.tenant_id == self.tenant_id,
                    Prompt.is_system == False,  # noqa: E712 Can't delete system prompts
                )
            )
        )
        prompt = result.scalar_one_or_none()
        if not prompt:
            return False

        prompt.is_active = False
        await self.db.commit()
        return True

    async def ensure_default_prompts(self, module: str) -> int:
        """
        Ensure all default prompts exist for a module.
        Returns number of prompts created.
        """
        from app.ai.prompt_generator import LINKEDIN_PROMPT_TEMPLATES

        if module != "linkedin":
            return 0

        created = 0

        # 1. Ensure onboarding prompt exists (uses dynamic parameters now)
        onboarding = await self.ensure_onboarding_prompt(module)
        if onboarding:
            created += 1

        # 2. Ensure all productive prompts exist
        for slug, template in LINKEDIN_PROMPT_TEMPLATES.items():
            existing = await self.get_prompt_by_slug(module, slug)
            if not existing:
                # Build system prompt from template instructions
                system_prompt = """Du bist ein Experte für LinkedIn-Kommunikation und B2B-Sales.
Erstelle professionelle, authentische Nachrichten die nicht nach Spam oder Massenmail klingen.
Die Nachrichten sollen persönlich wirken und echtes Interesse zeigen.
Antworte NUR mit dem fertigen Nachrichtentext.
Keine Erklärungen, kein Markdown, keine Anführungszeichen um den Text."""

                prompt = Prompt(
                    tenant_id=self.tenant_id,
                    slug=slug,
                    name=template["name"],
                    module=module,
                    prompt_type="productive",
                    system_prompt=system_prompt,
                    user_prompt=template["instructions"],
                    provider="anthropic",
                    model="claude-sonnet-4-20250514",
                    temperature=0.7,
                    max_tokens=500,
                    is_system=True,
                    version=1,
                )
                self.db.add(prompt)
                created += 1
                logger.info(f"Created prompt: {module}/{slug}")

        if created > 0:
            await self.db.commit()

        return created

    # ═══════════════════════════════════════════════════════════════════════════
    # Prompt Rendering
    # ═══════════════════════════════════════════════════════════════════════════

    async def render_prompt(
        self, module: str, slug: str, extra_vars: dict | None = None
    ) -> tuple[str, str] | None:
        """
        Render a prompt with module context variables injected.
        Returns (system_prompt, user_prompt) tuple.
        """
        prompt = await self.get_prompt_by_slug(module, slug)
        if not prompt:
            return None

        # Get module context
        context = await self.get_module_context(module)
        variables = context.context_data if context else {}

        # Merge extra variables
        if extra_vars:
            variables = {**variables, **extra_vars}

        # Render prompts with variable substitution
        system_prompt = self._substitute_variables(prompt.system_prompt, variables)
        user_prompt = self._substitute_variables(prompt.user_prompt, variables)

        return system_prompt, user_prompt

    def _substitute_variables(self, template: str, variables: dict) -> str:
        """
        Substitute {{variable}} placeholders in template.
        Supports:
        - {{variable}} - simple substitution
        - {{variable ? "yes" : "no"}} - ternary for booleans
        - {{variable | default}} - default values
        """
        if not template:
            return template

        def replace_match(match):
            expr = match.group(1).strip()

            # Check for ternary: {{var ? "yes" : "no"}}
            ternary_match = re.match(
                r"(\w+)\s*\?\s*[\"'](.+?)[\"']\s*:\s*[\"'](.+?)[\"']", expr
            )
            if ternary_match:
                var_name = ternary_match.group(1)
                true_val = ternary_match.group(2)
                false_val = ternary_match.group(3)
                return true_val if variables.get(var_name) else false_val

            # Check for default: {{var | default}}
            default_match = re.match(r"(\w+)\s*\|\s*(.+)", expr)
            if default_match:
                var_name = default_match.group(1)
                default_val = default_match.group(2).strip().strip("\"'")
                return str(variables.get(var_name, default_val))

            # Simple substitution
            value = variables.get(expr, f"{{{{{expr}}}}}")
            if isinstance(value, list):
                return ", ".join(str(v) for v in value)
            return str(value)

        return re.sub(r"\{\{(.+?)\}\}", replace_match, template)

    # ═══════════════════════════════════════════════════════════════════════════
    # Onboarding Chat
    # ═══════════════════════════════════════════════════════════════════════════

    async def start_onboarding(self, module: str) -> tuple[Conversation, str]:
        """
        Start an onboarding conversation for a module.
        Returns (conversation, first_message).
        """
        # Get the onboarding prompt
        prompt = await self.get_prompt_by_slug(module, "onboarding")
        if not prompt:
            raise ValueError(f"No onboarding prompt found for module: {module}")

        # Get parameters and build dynamic system prompt
        parameters = await self.get_module_parameters(module)
        system_prompt = self._build_dynamic_onboarding_prompt(prompt, parameters)

        # Create conversation
        conversation = Conversation(
            tenant_id=self.tenant_id,
            title=f"{module} Onboarding",
            context_type="onboarding",
            context_data={"module": module, "prompt_slug": "onboarding"},
        )
        self.db.add(conversation)
        await self.db.commit()
        await self.db.refresh(conversation)

        # Generate first message using LLM
        llm_service = LLMService()
        first_message = await llm_service.generate_with_config(
            provider=prompt.provider,
            model=prompt.model,
            system_prompt=system_prompt,
            user_prompt="Starte das Interview. Stelle die erste Frage.",
            temperature=prompt.temperature,
            max_tokens=prompt.max_tokens,
        )

        # Save assistant message
        chat_msg = ChatMessage(
            conversation_id=conversation.id,
            role="assistant",
            content=first_message,
        )
        self.db.add(chat_msg)
        await self.db.commit()

        return conversation, first_message

    async def continue_onboarding(
        self, module: str, conversation_id: int, user_message: str
    ) -> OnboardingChatResponse:
        """
        Continue an onboarding conversation.
        Returns response with possible extracted data if complete.
        """
        # Get conversation
        result = await self.db.execute(
            select(Conversation).where(
                and_(
                    Conversation.id == conversation_id,
                    Conversation.tenant_id == self.tenant_id,
                )
            )
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise ValueError("Conversation not found")

        # Get prompt
        prompt_slug = (conversation.context_data or {}).get("prompt_slug", "onboarding")
        prompt = await self.get_prompt_by_slug(module, prompt_slug)
        if not prompt:
            raise ValueError(f"Prompt not found: {prompt_slug}")

        # Get parameters and build dynamic system prompt
        parameters = await self.get_module_parameters(module)
        system_prompt = self._build_dynamic_onboarding_prompt(prompt, parameters)

        # Save user message
        user_msg = ChatMessage(
            conversation_id=conversation_id,
            role="user",
            content=user_message,
        )
        self.db.add(user_msg)

        # Get conversation history
        history_result = await self.db.execute(
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.created_at)
        )
        history = list(history_result.scalars().all())

        # Build messages for LLM
        messages = [{"role": msg.role, "content": msg.content} for msg in history]
        messages.append({"role": "user", "content": user_message})

        # Call LLM with messages
        llm_service = LLMService()
        assistant_response = await llm_service.generate_with_messages(
            provider=prompt.provider,
            model=prompt.model,
            system_prompt=system_prompt,
            messages=messages,
            temperature=prompt.temperature,
            max_tokens=prompt.max_tokens,
        )

        # Save assistant message
        assistant_msg = ChatMessage(
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_response,
        )
        self.db.add(assistant_msg)
        await self.db.commit()

        # Check if onboarding is complete (look for completion markers)
        is_complete = self._check_onboarding_complete(assistant_response)
        extracted_data = None

        prompts_generated = []
        if is_complete:
            # Extract structured data from conversation
            extracted_data = await self._extract_onboarding_data(
                module, prompt, [*history, user_msg, assistant_msg]
            )
            if extracted_data:
                # Save to module context
                await self.update_module_context(
                    module,
                    ModuleContextUpdate(
                        context_data=extracted_data,
                        onboarding_completed=True,
                    ),
                )

                # Generate productive prompts
                try:
                    prompts_generated = await self.generate_productive_prompts(
                        module, extracted_data
                    )
                    logger.info(
                        f"Generated {len(prompts_generated)} productive prompts for {module}"
                    )
                except Exception as e:
                    logger.error(f"Failed to generate productive prompts: {e}")

        return OnboardingChatResponse(
            message=assistant_response,
            is_complete=is_complete,
            extracted_data=extracted_data,
            prompts_generated=prompts_generated,
        )

    def _check_onboarding_complete(self, response: str) -> bool:
        """Check if the onboarding conversation is complete."""
        completion_markers = [
            "zusammenfassung",
            "abgeschlossen",
            "fertig eingerichtet",
            "konfiguration abgeschlossen",
            "onboarding abgeschlossen",
            "alle informationen",
            "können wir loslegen",
            "setup ist fertig",
        ]
        response_lower = response.lower()
        return any(marker in response_lower for marker in completion_markers)

    async def _extract_onboarding_data(
        self, module: str, prompt: Prompt, messages: list[ChatMessage]
    ) -> dict | None:
        """Extract structured data from completed onboarding conversation."""
        # Build schema from module parameters (dynamic, not hardcoded)
        parameters = await self.get_module_parameters(module)
        if not parameters:
            logger.warning(f"No parameters defined for module {module}")
            return None

        variables_schema = self.build_parameters_schema(parameters)

        # Build conversation transcript
        transcript = "\n".join(f"{msg.role.upper()}: {msg.content}" for msg in messages)

        # Build parameter descriptions for better extraction
        param_descriptions = "\n".join(
            f"- {p.variable}: {p.description} (Typ: {p.var_type})"
            for p in parameters
        )

        # Create extraction prompt
        schema_json = json.dumps(variables_schema, indent=2)
        extraction_prompt = f"""Analysiere das folgende Interview-Gespräch und extrahiere die strukturierten Daten.

GESPRÄCH:
{transcript}

ZU EXTRAHIERENDE PARAMETER:
{param_descriptions}

ERWARTETES SCHEMA:
{schema_json}

WICHTIG:
- Gib NUR ein valides JSON-Objekt zurück
- Keine Erklärungen, kein Markdown, nur das reine JSON
- Bei Typ "array": JSON-Array verwenden, z.B. ["Wert1", "Wert2"]
- Bei Typ "boolean": true oder false (ohne Anführungszeichen)
- Bei Typ "number": Zahl ohne Anführungszeichen
- Wenn ein Wert nicht ermittelt werden konnte, verwende null
"""

        llm_service = LLMService()
        try:
            response = await llm_service.generate_with_config(
                provider=prompt.provider,
                model=prompt.model,
                system_prompt="Du bist ein Daten-Extraktor. Extrahiere strukturierte Daten aus Gesprächen. Antworte NUR mit JSON.",
                user_prompt=extraction_prompt,
                temperature=0.1,  # Low temperature for consistent extraction
                max_tokens=1024,
            )

            # Parse JSON from response
            json_match = re.search(r"\{[\s\S]*\}", response)
            if json_match:
                extracted = json.loads(json_match.group())
                logger.info(f"Extracted onboarding data: {list(extracted.keys())}")

                # Save extracted values to parameters
                await self._save_extracted_to_parameters(module, extracted)

                return extracted
        except Exception as e:
            logger.error(f"Failed to extract onboarding data: {e}")

        return None

    async def _save_extracted_to_parameters(
        self, module: str, extracted: dict[str, Any]
    ) -> int:
        """Save extracted values to the module parameters table."""
        count = 0
        for variable, value in extracted.items():
            if value is not None:
                # Convert value to string for storage
                if isinstance(value, list):
                    str_value = json.dumps(value)
                elif isinstance(value, bool):
                    str_value = "true" if value else "false"
                else:
                    str_value = str(value)

                param = await self.set_parameter_value(module, variable, str_value)
                if param:
                    count += 1
                    logger.debug(f"Set parameter {variable} = {str_value}")
        return count

    def _build_dynamic_onboarding_prompt(
        self, prompt: Prompt, parameters: list[ModuleParameter]
    ) -> str:
        """
        Build a dynamic onboarding system prompt based on the defined parameters.

        The prompt instructs the LLM to collect values for all defined parameters.
        """
        if not parameters:
            # Fallback to static prompt if no parameters defined
            return prompt.system_prompt

        # Build parameter list for the prompt
        param_list = []
        for i, p in enumerate(parameters, 1):
            required = "(Pflicht)" if p.required else "(optional)"
            param_list.append(f"{i}. **{p.variable}**: {p.description} {required}")

        params_text = "\n".join(param_list)

        # Build dynamic system prompt
        dynamic_prompt = f"""Du bist der Setup-Assistent für das go4-automate System.
Deine Aufgabe ist es, den Benutzer durch einen strukturierten Dialog zu führen, um alle notwendigen Informationen zu sammeln.

## Deine Persönlichkeit
- Freundlich, professionell und effizient
- Stelle immer nur 1-2 Fragen auf einmal
- Gib Beispiele wenn hilfreich
- Fasse am Ende alle gesammelten Infos zusammen

## Zu sammelnde Parameter

{params_text}

## Ablauf

1. Begrüße den Benutzer kurz
2. Gehe die Parameter der Reihe nach durch
3. Stelle für jeden Parameter eine klare Frage
4. Bei unklaren Antworten: nachfragen
5. Optionale Parameter können übersprungen werden, wenn der User das wünscht
6. Am Ende: Alle Werte zusammenfassen und bestätigen lassen

## Wichtige Regeln

1. **Natürlicher Dialog**: Führe ein echtes Gespräch, keine Checkliste abarbeiten
2. **Adaptive Fragen**: Passe Folgefragen an vorherige Antworten an
3. **Keine Annahmen**: Frage nach wenn etwas unklar ist
4. **Ermutigung**: Gib positives Feedback bei guten Antworten
5. **Beispiele**: Wenn der Benutzer unsicher ist, gib konkrete Beispiele
6. **Zusammenfassung**: Am Ende IMMER alle Infos zusammenfassen und bestätigen lassen
7. **Abschluss**: Wenn alles bestätigt ist, sage "Das Onboarding ist abgeschlossen."

## Start
Beginne mit einer freundlichen Begrüßung und der ersten Frage."""

        return dynamic_prompt

    # ═══════════════════════════════════════════════════════════════════════════
    # Productive Prompt Generation
    # ═══════════════════════════════════════════════════════════════════════════

    async def generate_productive_prompts(
        self, module: str, variables: dict[str, Any]
    ) -> list[str]:
        """
        Generate all productive prompts for a module using the extracted variables.

        Args:
            module: Module name (e.g., "linkedin")
            variables: Extracted onboarding variables

        Returns:
            List of generated prompt slugs
        """
        generator = PromptGenerator()
        generated_prompts = await generator.generate_all_prompts(module, variables)

        saved_slugs = []
        for prompt_data in generated_prompts:
            try:
                await self._save_generated_prompt(module, prompt_data)
                saved_slugs.append(prompt_data["slug"])
            except Exception as e:
                logger.error(f"Failed to save prompt {prompt_data['slug']}: {e}")

        return saved_slugs

    async def _save_generated_prompt(self, module: str, prompt_data: dict) -> Prompt:
        """
        Save or update a generated prompt in the database.

        If a prompt with the same slug exists, update it. Otherwise create new.
        """
        existing = await self.get_prompt_by_slug(module, prompt_data["slug"])

        if existing:
            # Update existing prompt
            existing.name = prompt_data["name"]
            existing.user_prompt = prompt_data["content"]
            existing.prompt_type = prompt_data.get("prompt_type", "productive")
            await self.db.commit()
            await self.db.refresh(existing)
            logger.info(f"Updated existing prompt: {prompt_data['slug']}")
            return existing
        else:
            # Create new prompt
            prompt = Prompt(
                tenant_id=self.tenant_id,
                module=module,
                slug=prompt_data["slug"],
                name=prompt_data["name"],
                prompt_type=prompt_data.get("prompt_type", "productive"),
                system_prompt="",  # Productive prompts don't need system prompt
                user_prompt=prompt_data["content"],
                provider="anthropic",
                model="claude-sonnet-4-20250514",
                temperature=0.7,
                max_tokens=500,
                is_system=prompt_data.get("is_system", False),
                is_active=True,
                version=1,
            )
            self.db.add(prompt)
            await self.db.commit()
            await self.db.refresh(prompt)
            logger.info(f"Created new prompt: {prompt_data['slug']}")
            return prompt

    async def ensure_onboarding_prompt(self, module: str) -> Prompt | None:
        """
        Ensure the onboarding prompt exists for a module.
        Creates a generic onboarding prompt that uses dynamic parameters.
        """
        existing = await self.get_prompt_by_slug(module, "onboarding")
        if existing:
            return existing

        # Create generic onboarding prompt - the system_prompt will be built
        # dynamically from parameters in _build_dynamic_onboarding_prompt()
        prompt = Prompt(
            tenant_id=self.tenant_id,
            module=module,
            slug="onboarding",
            name=f"{module.capitalize()} Setup Assistant",
            prompt_type="setup",
            system_prompt="",  # Will be built dynamically from parameters
            user_prompt="Starte das Onboarding-Interview.",
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            temperature=0.7,
            max_tokens=1024,
            is_system=True,
            is_active=True,
            version=1,
        )
        self.db.add(prompt)
        await self.db.commit()
        await self.db.refresh(prompt)
        logger.info(f"Created onboarding prompt for module: {module}")
        return prompt
