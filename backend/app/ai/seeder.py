"""Seed default AI prompts from module manifests."""

from loguru import logger
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prompt import Prompt


async def seed_module_prompts(
    db: AsyncSession, tenant_id: str, manifests: list[dict]
) -> int:
    """
    Seed default prompts from module manifests for a tenant.
    Only creates prompts that don't already exist.
    Returns the number of prompts created.
    """
    created_count = 0

    for manifest in manifests:
        module_name = manifest.get("name")
        ai_config = manifest.get("ai", {})
        default_prompts = ai_config.get("default_prompts", [])

        if not default_prompts:
            continue

        for prompt_data in default_prompts:
            slug = prompt_data.get("slug")
            if not slug:
                continue

            # Check if prompt already exists
            result = await db.execute(
                select(Prompt).where(
                    and_(
                        Prompt.tenant_id == tenant_id,
                        Prompt.module == module_name,
                        Prompt.slug == slug,
                    )
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Skip - prompt already exists
                continue

            # Create new prompt
            prompt = Prompt(
                tenant_id=tenant_id,
                module=module_name,
                slug=slug,
                name=prompt_data.get("name", slug),
                description=prompt_data.get("description"),
                category=prompt_data.get("category", "general"),
                prompt_type=prompt_data.get("prompt_type", "productive"),
                is_system=prompt_data.get("is_system", True),
                system_prompt=prompt_data.get("system_prompt", ""),
                user_prompt=prompt_data.get("user_prompt", ""),
                variables=prompt_data.get("variables"),
                variables_schema=prompt_data.get("variables_schema"),
                output_format=prompt_data.get("output_format", "text"),
                output_schema=prompt_data.get("output_schema"),
                provider=prompt_data.get("provider", "anthropic"),
                model=prompt_data.get("model", "claude-sonnet-4-20250514"),
                temperature=prompt_data.get("temperature", 0.7),
                max_tokens=prompt_data.get("max_tokens", 2048),
                version=1,
                is_active=True,
            )
            db.add(prompt)
            created_count += 1
            logger.debug(
                "Created prompt {module}/{slug} for tenant {tenant}",
                module=module_name,
                slug=slug,
                tenant=tenant_id,
            )

    if created_count > 0:
        await db.commit()
        logger.info(
            "Seeded {count} AI prompts for tenant {tenant}",
            count=created_count,
            tenant=tenant_id,
        )

    return created_count
