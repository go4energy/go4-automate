"""LLM service - task-based + class-based model routing with tenant context.

Class-based model routing
=========================

The application has three coarse "model classes" that any feature can ask for:

- ``premium``   — Highest quality. Used for setup-assistant, KI-designer chat,
                  strategic dialogues. Slow + expensive but best output.
- ``standard``  — Personalization workhorse. Body generation per recipient,
                  reply drafts, subject personalization. ~10x cheaper than
                  premium with negligible quality loss for these tasks.
- ``bulk``      — Classification / analysis. Sentiment, intent, lead scoring,
                  webpage scraping. ~5x cheaper than standard.

Models per class are configured per tenant in ``module_parameters``
(module='llm', variable='premium_model' / 'standard_model' / 'bulk_model').
Defaults defined here apply when no override is set.

Use::

    from app.services.llm import get_model_for_class
    model = await get_model_for_class("premium", db, tenant_id)
    # → "claude-opus-4-7" (or whatever the admin configured)
"""

from collections.abc import AsyncGenerator
from typing import Literal

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import ExternalServiceError
from app.models.module_parameter import ModuleParameter

# Task → model mapping
TASK_MODEL_MAP = {
    "content": "anthropic",
    "analysis": "openai",
    "classification": "openai",
    "scoring": "openai",
}


# Default Anthropic models per class. Overridden per tenant via Settings.
DEFAULT_MODELS: dict[str, str] = {
    "premium": "claude-opus-4-7",
    "standard": "claude-sonnet-4-6",
    "bulk": "claude-haiku-4-5-20251001",
}

ModelClass = Literal["premium", "standard", "bulk"]
LLM_MODULE = "llm"


async def get_model_for_class(
    cls: ModelClass,
    db: AsyncSession,
    tenant_id: str,
) -> str:
    """Resolve the configured Anthropic model for a model class.

    Looks up ``module_parameters`` (module='llm', variable='{cls}_model')
    for the tenant; falls back to the hard-coded default.

    Use this everywhere a feature wants to call Claude. Never hard-code
    model IDs in feature code — the admin can switch models in Settings.
    """
    if cls not in DEFAULT_MODELS:
        raise ValueError(f"Unknown model class: {cls!r}. Use one of {list(DEFAULT_MODELS)}")
    variable = f"{cls}_model"
    result = await db.execute(
        select(ModuleParameter.value).where(
            ModuleParameter.tenant_id == tenant_id,
            ModuleParameter.module == LLM_MODULE,
            ModuleParameter.variable == variable,
        )
    )
    value = result.scalar_one_or_none()
    if value:
        return value
    return DEFAULT_MODELS[cls]


def get_default_model(cls: ModelClass) -> str:
    """Synchronous default — for places without DB session (e.g. tests)."""
    return DEFAULT_MODELS[cls]


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
            if provider == "ollama":
                return await self._call_ollama(model_id, system_prompt, prompt)
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

    async def _call_ollama(self, model: str, system: str, prompt: str) -> str:
        """Call Ollama via OpenAI-compatible API."""
        from openai import AsyncOpenAI

        client = AsyncOpenAI(base_url=f"{settings.ollama_url}/v1", api_key="ollama")
        response = await client.chat.completions.create(
            model=model or settings.ollama_model,
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
        """Generate text with explicit provider/model/temperature/max_tokens.

        Backwards-compat thin wrapper around ``generate_with_usage`` that
        returns just the text — for callers that don't care about token
        counts.
        """
        text, _usage = await self.generate_with_usage(
            provider=provider,
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return text

    async def generate_with_cached_system(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> tuple[str, dict]:
        """Like ``generate_with_usage`` but marks the system prompt for
        Anthropic ephemeral caching (5-min TTL).

        Use for bulk runs where the system prompt is identical across many
        calls (e.g. 1000 personalised emails sharing the same template-prompt,
        only the user message differs per recipient).

        Anthropic-only — falls back to a non-cached call for other providers.
        """
        if not settings.anthropic_api_key:
            raise ExternalServiceError("Anthropic", "API Key nicht konfiguriert")

        text, usage = await self._call_anthropic_with_usage(
            model=model,
            system=system_prompt,
            prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            cache_system=True,
        )
        logger.info(
            "LLM cached call: model={m} cache_create={cc} cache_read={cr} input={i} output={o}",
            m=model,
            cc=usage.get("cache_creation_input_tokens", 0),
            cr=usage.get("cache_read_input_tokens", 0),
            i=usage.get("input_tokens", 0),
            o=usage.get("output_tokens", 0),
        )
        return text, usage

    async def generate_with_usage(
        self,
        provider: str,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> tuple[str, dict]:
        """Generate text + return real token usage from the provider response.

        Returns ``(text, usage)`` where usage is a dict with
        ``input_tokens``, ``output_tokens``, ``cache_read_input_tokens``,
        ``cache_creation_input_tokens``, and ``stop_reason`` (when available).

        The usage dict is provider-best-effort: Anthropic returns precise
        counts; Ollama/OpenAI fall back to character-based estimates.
        """
        logger.info(
            "LLM config request: provider={provider} model={model} temp={temp}",
            provider=provider,
            model=model,
            temp=temperature,
        )
        try:
            if provider == "anthropic":
                return await self._call_anthropic_with_usage(
                    model, system_prompt, user_prompt, temperature, max_tokens
                )
            if provider == "ollama":
                text = await self._call_ollama_with_config(
                    model, system_prompt, user_prompt, temperature, max_tokens
                )
            else:
                text = await self._call_openai_with_config(
                    model, system_prompt, user_prompt, temperature, max_tokens
                )
            usage = {
                "input_tokens": max(1, len(user_prompt) // 4),
                "output_tokens": max(1, len(text) // 4),
                "cache_read_input_tokens": 0,
                "cache_creation_input_tokens": 0,
                "stop_reason": None,
            }
            return text, usage
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
        """Backwards-compat: call Anthropic and return only text."""
        text, _ = await self._call_anthropic_with_usage(
            model, system, prompt, temperature, max_tokens
        )
        return text

    async def _call_anthropic_with_usage(
        self,
        model: str,
        system: str,
        prompt: str,
        temperature: float,
        max_tokens: int,
        cache_system: bool = False,
    ) -> tuple[str, dict]:
        """Call Anthropic Claude API and return ``(text, usage_dict)``.

        When ``cache_system=True`` the system prompt is sent as a content
        block with ``cache_control: ephemeral`` (5-min TTL). Subsequent
        identical system prompts are billed at ~10 % of normal input cost
        — meant for bulk runs (e.g. 1000 personalised emails sharing the
        same instructions, only the user message differs per recipient).
        """
        if not settings.anthropic_api_key:
            raise ExternalServiceError("Anthropic", "API Key nicht konfiguriert")

        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        if cache_system:
            system_param: str | list = [
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }
            ]
        else:
            system_param = system

        kwargs: dict = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system_param,
            "messages": [{"role": "user", "content": prompt}],
        }
        # Opus 4.7 (and later models that may follow) deprecated explicit
        # temperature in favour of internal sampling. Skip the parameter for
        # models that reject it, otherwise the API returns 400.
        if "opus-4-7" not in model.lower():
            kwargs["temperature"] = temperature
        response = await client.messages.create(**kwargs)
        u = getattr(response, "usage", None)
        usage = {
            "input_tokens": int(getattr(u, "input_tokens", 0) or 0),
            "output_tokens": int(getattr(u, "output_tokens", 0) or 0),
            "cache_read_input_tokens": int(
                getattr(u, "cache_read_input_tokens", 0) or 0
            ),
            "cache_creation_input_tokens": int(
                getattr(u, "cache_creation_input_tokens", 0) or 0
            ),
            "stop_reason": getattr(response, "stop_reason", None),
        }
        return response.content[0].text, usage

    async def _call_ollama_with_config(
        self,
        model: str,
        system: str,
        prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Call Ollama with explicit config.

        Local 30-70B models routinely need 30-90 s per response; bumping the
        client timeout to 5 minutes prevents spurious read timeouts during
        bulk Stage-3 runs.

        We use Ollama's native ``/api/chat`` endpoint instead of the OpenAI
        compat layer because reasoning models (Qwen 3, DeepSeek-R1, ...) need
        the explicit ``think: false`` flag to disable internal reasoning —
        otherwise the entire token budget is consumed by hidden thinking and
        the OpenAI-compat path returns empty content.
        """
        import httpx

        url = f"{settings.ollama_url}/api/chat"
        payload: dict = {
            "model": model or settings.ollama_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        # Reasoning models default to thinking on; explicitly disable it for
        # structured-JSON workloads where thinking just wastes tokens.
        m_lower = (model or "").lower()
        if "qwen3" in m_lower or "deepseek-r1" in m_lower or "magistral" in m_lower:
            payload["think"] = False

        async with httpx.AsyncClient(timeout=300.0) as http:
            resp = await http.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
        return data.get("message", {}).get("content", "")

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
            elif provider == "ollama":
                async for chunk in self._stream_ollama(system, messages):
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

    async def _stream_ollama(
        self, system: str, messages: list[dict]
    ) -> AsyncGenerator[str, None]:
        """Stream from Ollama via OpenAI-compatible API."""
        from openai import AsyncOpenAI

        client = AsyncOpenAI(base_url=f"{settings.ollama_url}/v1", api_key="ollama")
        stream = await client.chat.completions.create(
            model=settings.ollama_model,
            messages=[{"role": "system", "content": system}, *messages],
            max_tokens=2048,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    async def generate_with_messages(
        self,
        provider: str,
        model: str,
        system_prompt: str,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Generate text with conversation history (multiple messages)."""
        logger.info(
            "LLM messages request: provider={provider} model={model} msgs={count}",
            provider=provider,
            model=model,
            count=len(messages),
        )
        try:
            if provider == "anthropic":
                return await self._call_anthropic_messages(
                    model, system_prompt, messages, temperature, max_tokens
                )
            if provider == "ollama":
                return await self._call_ollama_messages(
                    model, system_prompt, messages, temperature, max_tokens
                )
            return await self._call_openai_messages(
                model, system_prompt, messages, temperature, max_tokens
            )
        except ExternalServiceError:
            raise
        except Exception as e:
            logger.exception("LLM-Fehler: {err}", err=str(e))
            raise ExternalServiceError("LLM", str(e)) from e

    async def _call_anthropic_messages(
        self,
        model: str,
        system: str,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Call Anthropic Claude API with message history."""
        if not settings.anthropic_api_key:
            raise ExternalServiceError("Anthropic", "API Key nicht konfiguriert")

        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        response = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=messages,
        )
        return response.content[0].text

    async def _call_openai_messages(
        self,
        model: str,
        system: str,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Call OpenAI API with message history."""
        if not settings.openai_api_key:
            raise ExternalServiceError("OpenAI", "API Key nicht konfiguriert")

        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system}, *messages],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content

    async def _call_ollama_messages(
        self,
        model: str,
        system: str,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Call Ollama with message history."""
        from openai import AsyncOpenAI

        client = AsyncOpenAI(base_url=f"{settings.ollama_url}/v1", api_key="ollama")
        response = await client.chat.completions.create(
            model=model or settings.ollama_model,
            messages=[{"role": "system", "content": system}, *messages],
            max_tokens=max_tokens,
            temperature=temperature,
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
