"""LLM service - task-based model routing with tenant context."""

from loguru import logger

from app.config import settings
from app.exceptions import ExternalServiceError

# Task → model mapping
TASK_MODEL_MAP = {
    "content": "anthropic",
    "analysis": "openai",
    "classification": "openai",
    "scoring": "openai",
}


def _get_model_for_task(task: str) -> tuple[str, str]:
    """Return (provider, model_id) for a given task."""
    model_map = {
        "content": settings.llm_model_content,
        "analysis": settings.llm_model_analysis,
        "classification": settings.llm_model_classification,
        "scoring": settings.llm_model_scoring,
    }
    provider = TASK_MODEL_MAP.get(task, "openai")
    model_id = model_map.get(task, settings.llm_model_analysis)
    return provider, model_id


class LLMService:
    """LLM service with task-based model routing."""

    def __init__(self, tenant_config: dict | None = None) -> None:
        self.tenant_config = tenant_config or {}

    def _build_system_prompt(self, task: str) -> str:
        """Build system prompt with tenant context."""
        tenant_name = self.tenant_config.get("TENANT_NAME", "")
        company = self.tenant_config.get("COMPANY_NAME", "")
        tone = self.tenant_config.get("CONTENT_TONE", "professional")
        website = self.tenant_config.get("WEBSITE_URL", "")

        base = f"Du bist ein Marketing-Assistent für {company or tenant_name}."
        if website:
            base += f" Website: {website}."
        if task == "content":
            base += f" Tonalität: {tone}. Erstelle ansprechende Marketing-Inhalte."
        elif task == "scoring":
            base += (
                " Bewerte die Lead-Qualität basierend auf den bereitgestellten Daten."
            )
        elif task == "classification":
            base += " Klassifiziere die Anfrage in die richtige Kategorie."
        return base

    async def generate(self, task: str, prompt: str) -> str:
        """Generate text using the appropriate model for the task."""
        provider, model_id = _get_model_for_task(task)
        system_prompt = self._build_system_prompt(task)

        logger.info(
            "LLM request: task={task} provider={provider} model={model}",
            task=task,
            provider=provider,
            model=model_id,
        )

        try:
            if provider == "anthropic":
                return await self._call_anthropic(model_id, system_prompt, prompt)
            return await self._call_openai(model_id, system_prompt, prompt)
        except ExternalServiceError:
            raise
        except Exception as e:
            logger.exception("LLM-Fehler: {err}", err=str(e))
            raise ExternalServiceError("LLM", str(e)) from e

    async def _call_anthropic(self, model: str, system: str, prompt: str) -> str:
        """Call Anthropic Claude API."""
        if not settings.anthropic_api_key:
            raise ExternalServiceError("Anthropic", "API Key nicht konfiguriert")

        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        response = await client.messages.create(
            model=model,
            max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    async def _call_openai(self, model: str, system: str, prompt: str) -> str:
        """Call OpenAI API."""
        if not settings.openai_api_key:
            raise ExternalServiceError("OpenAI", "API Key nicht konfiguriert")

        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            max_tokens=2048,
        )
        return response.choices[0].message.content

    async def generate_json(self, task: str, prompt: str) -> dict:
        """Generate text and parse as JSON. Strips markdown fences."""
        import json
        import re

        raw = await self.generate(task, prompt)
        # Strip markdown code fences (```json ... ``` or ``` ... ```)
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", raw.strip())
        cleaned = re.sub(r"\n?```\s*$", "", cleaned.strip())
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error("LLM JSON Parse-Fehler: {err}", err=str(e))
            raise ExternalServiceError("LLM", f"Ungültiges JSON: {e}") from e
