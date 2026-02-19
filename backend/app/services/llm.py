"""LLM service - task-based model routing with tenant context."""

from collections.abc import AsyncGenerator

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

    async def generate_with_config(
        self,
        provider: str,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Generate text with explicit provider/model/temperature/max_tokens."""
        logger.info(
            "LLM config request: provider={provider} model={model} temp={temp}",
            provider=provider,
            model=model,
            temp=temperature,
        )
        try:
            if provider == "anthropic":
                return await self._call_anthropic_with_config(
                    model, system_prompt, user_prompt, temperature, max_tokens
                )
            return await self._call_openai_with_config(
                model, system_prompt, user_prompt, temperature, max_tokens
            )
        except ExternalServiceError:
            raise
        except Exception as e:
            logger.exception("LLM-Fehler: {err}", err=str(e))
            raise ExternalServiceError("LLM", str(e)) from e

    async def _call_anthropic_with_config(
        self,
        model: str,
        system: str,
        prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Call Anthropic Claude API with explicit config."""
        if not settings.anthropic_api_key:
            raise ExternalServiceError("Anthropic", "API Key nicht konfiguriert")

        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        response = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    async def _call_openai_with_config(
        self,
        model: str,
        system: str,
        prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Call OpenAI API with explicit config."""
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
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content

    async def stream_generate(
        self,
        system: str,
        messages: list[dict],
        provider: str = "anthropic",
    ) -> AsyncGenerator[str, None]:
        """Stream text generation from LLM. Yields text chunks."""
        logger.info(
            "LLM stream request: provider={provider}",
            provider=provider,
        )
        try:
            if provider == "anthropic":
                async for chunk in self._stream_anthropic(system, messages):
                    yield chunk
            else:
                async for chunk in self._stream_openai(system, messages):
                    yield chunk
        except ExternalServiceError:
            raise
        except Exception as e:
            logger.exception("LLM Stream-Fehler: {err}", err=str(e))
            raise ExternalServiceError("LLM", str(e)) from e

    async def _stream_anthropic(
        self, system: str, messages: list[dict]
    ) -> AsyncGenerator[str, None]:
        """Stream from Anthropic Claude API."""
        if not settings.anthropic_api_key:
            raise ExternalServiceError("Anthropic", "API Key nicht konfiguriert")

        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        async with client.messages.stream(
            model=settings.llm_model_content,
            max_tokens=2048,
            system=system,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def _stream_openai(
        self, system: str, messages: list[dict]
    ) -> AsyncGenerator[str, None]:
        """Stream from OpenAI API."""
        if not settings.openai_api_key:
            raise ExternalServiceError("OpenAI", "API Key nicht konfiguriert")

        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        stream = await client.chat.completions.create(
            model=settings.llm_model_analysis,
            messages=[{"role": "system", "content": system}, *messages],
            max_tokens=2048,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

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
