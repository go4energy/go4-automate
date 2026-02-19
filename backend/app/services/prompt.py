"""Prompt registry service - CRUD, versioning, and execution."""

import json
import re

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import DuplicateError, NotFoundError, ValidationError
from app.models.prompt import Prompt
from app.schemas.prompt import PromptCreate, PromptExecuteRequest, PromptUpdate
from app.services.llm import LLMService


class PromptService:
    """Service for prompt template management and execution."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, tenant_id: str, data: PromptCreate) -> Prompt:
        """Create a new prompt (v1)."""
        existing = await self._get_by_slug_version(tenant_id, data.slug, 1)
        if existing:
            raise DuplicateError("Prompt", "slug")

        variables_json = None
        if data.variables:
            variables_json = [v.model_dump() for v in data.variables]

        prompt = Prompt(
            tenant_id=tenant_id,
            slug=data.slug,
            name=data.name,
            description=data.description,
            category=data.category,
            system_prompt=data.system_prompt,
            user_prompt=data.user_prompt,
            variables=variables_json,
            output_format=data.output_format,
            output_schema=data.output_schema,
            provider=data.provider,
            model=data.model,
            temperature=data.temperature,
            max_tokens=data.max_tokens,
            version=1,
            is_active=True,
        )
        self.db.add(prompt)
        await self.db.flush()
        await self.db.refresh(prompt)
        logger.info(
            "Prompt erstellt: {slug} v1 (Tenant: {tenant})",
            slug=data.slug,
            tenant=tenant_id,
        )
        return prompt

    async def list_prompts(
        self,
        tenant_id: str,
        category: str | None = None,
        is_active: bool | None = None,
        search: str | None = None,
    ) -> list[Prompt]:
        """List prompts, deduplicated to highest version per slug."""
        # Subquery: max version per slug
        max_version = (
            select(
                Prompt.slug,
                func.max(Prompt.version).label("max_version"),
            )
            .where(Prompt.tenant_id == tenant_id)
            .group_by(Prompt.slug)
            .subquery()
        )

        query = (
            select(Prompt)
            .where(Prompt.tenant_id == tenant_id)
            .join(
                max_version,
                (Prompt.slug == max_version.c.slug)
                & (Prompt.version == max_version.c.max_version),
            )
        )

        if category:
            query = query.where(Prompt.category == category)
        if is_active is not None:
            query = query.where(Prompt.is_active == is_active)
        if search:
            pattern = f"%{search}%"
            query = query.where(Prompt.name.ilike(pattern) | Prompt.slug.ilike(pattern))

        query = query.order_by(Prompt.name.asc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, tenant_id: str, prompt_id: int) -> Prompt:
        """Get a prompt by ID, scoped to tenant."""
        result = await self.db.execute(
            select(Prompt).where(
                Prompt.id == prompt_id,
                Prompt.tenant_id == tenant_id,
            )
        )
        prompt = result.scalar_one_or_none()
        if not prompt:
            raise NotFoundError("Prompt", prompt_id)
        return prompt

    async def get_active_by_slug(self, tenant_id: str, slug: str) -> Prompt:
        """Get the newest active version of a prompt by slug."""
        result = await self.db.execute(
            select(Prompt)
            .where(
                Prompt.tenant_id == tenant_id,
                Prompt.slug == slug,
                Prompt.is_active.is_(True),
            )
            .order_by(Prompt.version.desc())
            .limit(1)
        )
        prompt = result.scalar_one_or_none()
        if not prompt:
            raise NotFoundError("Prompt", slug)
        return prompt

    async def update(
        self, tenant_id: str, prompt_id: int, data: PromptUpdate
    ) -> Prompt:
        """Partial update of a prompt."""
        prompt = await self.get_by_id(tenant_id, prompt_id)
        update_data = data.model_dump(exclude_unset=True)

        if "variables" in update_data and update_data["variables"] is not None:
            update_data["variables"] = [
                v.model_dump() if hasattr(v, "model_dump") else v
                for v in update_data["variables"]
            ]

        for field, value in update_data.items():
            setattr(prompt, field, value)

        await self.db.flush()
        await self.db.refresh(prompt)
        logger.info(
            "Prompt aktualisiert: {id} (Tenant: {tenant})",
            id=prompt_id,
            tenant=tenant_id,
        )
        return prompt

    async def delete(self, tenant_id: str, prompt_id: int) -> None:
        """Delete a prompt."""
        prompt = await self.get_by_id(tenant_id, prompt_id)
        await self.db.delete(prompt)
        await self.db.flush()
        logger.info(
            "Prompt gelöscht: {id} (Tenant: {tenant})",
            id=prompt_id,
            tenant=tenant_id,
        )

    async def create_new_version(self, tenant_id: str, prompt_id: int) -> Prompt:
        """Copy a prompt and increment its version; deactivate old versions."""
        source = await self.get_by_id(tenant_id, prompt_id)

        # Get max version for this slug
        result = await self.db.execute(
            select(func.max(Prompt.version)).where(
                Prompt.tenant_id == tenant_id,
                Prompt.slug == source.slug,
            )
        )
        max_version = result.scalar() or 1
        new_version = max_version + 1

        # Deactivate all existing versions of this slug
        existing = await self.db.execute(
            select(Prompt).where(
                Prompt.tenant_id == tenant_id,
                Prompt.slug == source.slug,
            )
        )
        for old in existing.scalars().all():
            old.is_active = False

        new_prompt = Prompt(
            tenant_id=tenant_id,
            slug=source.slug,
            name=source.name,
            description=source.description,
            category=source.category,
            system_prompt=source.system_prompt,
            user_prompt=source.user_prompt,
            variables=source.variables,
            output_format=source.output_format,
            output_schema=source.output_schema,
            provider=source.provider,
            model=source.model,
            temperature=source.temperature,
            max_tokens=source.max_tokens,
            version=new_version,
            is_active=True,
        )
        self.db.add(new_prompt)
        await self.db.flush()
        await self.db.refresh(new_prompt)
        logger.info(
            "Prompt Version erstellt: {slug} v{version} (Tenant: {tenant})",
            slug=source.slug,
            version=new_version,
            tenant=tenant_id,
        )
        return new_prompt

    async def execute(
        self,
        tenant_id: str,
        data: PromptExecuteRequest,
        tenant_config: dict,
    ) -> dict:
        """Execute a prompt: load, fill variables, call LLM, return result."""
        prompt = await self.get_active_by_slug(tenant_id, data.prompt_slug)

        # Validate required variables
        if prompt.variables:
            for var_def in prompt.variables:
                var_name = var_def.get("name", "")
                is_required = var_def.get("required", True)
                has_default = var_def.get("default") is not None
                if is_required and var_name not in data.variables and not has_default:
                    raise ValidationError(f"Variable '{var_name}' ist erforderlich")

        # Merge: defaults < tenant_config < explicit variables
        merged_vars = {}
        if prompt.variables:
            for var_def in prompt.variables:
                name = var_def.get("name", "")
                default = var_def.get("default")
                if default is not None:
                    merged_vars[name] = default
        merged_vars.update(tenant_config)
        merged_vars.update(data.variables)

        # Fill {{VARIABLE}} placeholders
        system = _fill_template(prompt.system_prompt, merged_vars)
        user = _fill_template(prompt.user_prompt, merged_vars)

        # Call LLM
        llm = LLMService(tenant_config=tenant_config)
        raw = await llm.generate_with_config(
            provider=prompt.provider,
            model=prompt.model,
            system_prompt=system,
            user_prompt=user,
            temperature=prompt.temperature,
            max_tokens=prompt.max_tokens,
        )

        # Parse output
        result: str | dict = raw
        if prompt.output_format == "json":
            cleaned = re.sub(r"^```(?:json)?\s*\n?", "", raw.strip())
            cleaned = re.sub(r"\n?```\s*$", "", cleaned.strip())
            try:
                result = json.loads(cleaned)
            except json.JSONDecodeError as e:
                logger.error("Prompt JSON Parse-Fehler: {err}", err=str(e))
                result = raw

        return {
            "prompt_slug": prompt.slug,
            "provider": prompt.provider,
            "model": prompt.model,
            "output_format": prompt.output_format,
            "result": result,
            "version": prompt.version,
        }

    async def _get_by_slug_version(
        self, tenant_id: str, slug: str, version: int
    ) -> Prompt | None:
        """Get a prompt by slug and version."""
        result = await self.db.execute(
            select(Prompt).where(
                Prompt.tenant_id == tenant_id,
                Prompt.slug == slug,
                Prompt.version == version,
            )
        )
        return result.scalar_one_or_none()


def _fill_template(template: str, variables: dict) -> str:
    """Replace {{VARIABLE}} placeholders in a template string."""

    def replacer(match: re.Match) -> str:
        key = match.group(1)
        return str(variables.get(key, match.group(0)))

    return re.sub(r"\{\{(\w+)\}\}", replacer, template)
