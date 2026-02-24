"""Collector service - source fetching, finding analysis, topic management, change detection."""

import difflib
import hashlib
import json
from datetime import datetime, timedelta

import httpx
from bs4 import BeautifulSoup
from loguru import logger
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.collector.models import (
    CollectorFinding,
    CollectorGroup,
    CollectorSource,
    CollectorTopic,
    PageSnapshot,
)
from app.collector.schemas import (
    CollectorGroupCreate,
    CollectorGroupUpdate,
    CollectorSourceCreate,
    CollectorSourceUpdate,
    CollectorTopicCreate,
    CollectorTopicUpdate,
    FindingImport,
    InboxItemCreate,
)
from app.exceptions import (
    DuplicateError,
    ExternalServiceError,
    NotFoundError,
    ValidationError,
)


class CollectorService:
    """Service for collector sources, findings, topics, and change detection."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # --- Group CRUD ---

    async def create_group(
        self, tenant_id: str, data: CollectorGroupCreate
    ) -> CollectorGroup:
        """Create a new collector group with auto-duplicated analysis prompt."""
        existing = await self.db.execute(
            select(CollectorGroup).where(
                CollectorGroup.tenant_id == tenant_id,
                CollectorGroup.slug == data.slug,
            )
        )
        if existing.scalar_one_or_none():
            raise DuplicateError("CollectorGroup", "slug")

        group = CollectorGroup(
            tenant_id=tenant_id,
            name=data.name,
            slug=data.slug,
            description=data.description,
            fetch_interval_hours=data.fetch_interval_hours,
            distribution_channels=data.distribution_channels,
            tags=data.tags,
            streams=data.streams,
            analysis_prompt_slugs=data.analysis_prompt_slugs or [],
        )
        self.db.add(group)
        await self.db.flush()
        await self.db.refresh(group)

        # Auto-duplicate analysis prompt if none provided
        if not group.analysis_prompt_slugs:
            prompt_slug = await self._duplicate_prompt_for_group(
                tenant_id, group, purpose="research"
            )
            if prompt_slug:
                group.analysis_prompt_slugs = [prompt_slug]
                await self.db.flush()
                await self.db.refresh(group)

        logger.info(
            "Collector Group erstellt: {name} (Tenant: {tenant})",
            name=data.name,
            tenant=tenant_id,
        )
        return group

    async def _duplicate_prompt_for_group(
        self,
        tenant_id: str,
        group: CollectorGroup,
        purpose: str = "research",
        source_slug: str | None = None,
    ) -> str | None:
        """Duplicate an existing prompt for a new group. Returns new slug."""
        from app.models.prompt import Prompt
        from app.services.prompt import PromptService

        prompt_service = PromptService(self.db)
        new_slug = f"{purpose}-{group.slug}"

        # Use explicit source or find one automatically
        if not source_slug:
            source_slug = await self._find_source_prompt_slug(tenant_id)

        try:
            source_prompt = await prompt_service.get_active_by_slug(
                tenant_id, source_slug
            )
        except NotFoundError:
            logger.warning(
                "Quell-Prompt '{slug}' nicht gefunden, kein Prompt dupliziert",
                slug=source_slug,
            )
            return None

        # Check if target slug already exists
        existing = await self.db.execute(
            select(Prompt).where(
                Prompt.tenant_id == tenant_id,
                Prompt.slug == new_slug,
                Prompt.is_active.is_(True),
            )
        )
        if existing.scalar_one_or_none():
            return new_slug

        # Create duplicated prompt
        new_prompt = Prompt(
            tenant_id=tenant_id,
            slug=new_slug,
            name=f"{source_prompt.name} ({group.name})",
            description=f"Analyse-Prompt fuer Gruppe: {group.name}",
            category=source_prompt.category,
            system_prompt=source_prompt.system_prompt,
            user_prompt=source_prompt.user_prompt,
            variables=source_prompt.variables,
            output_format=source_prompt.output_format,
            output_schema=source_prompt.output_schema,
            provider=source_prompt.provider,
            model=source_prompt.model,
            temperature=source_prompt.temperature,
            max_tokens=source_prompt.max_tokens,
            processing_mode=source_prompt.processing_mode,
            version=1,
            is_active=True,
        )
        self.db.add(new_prompt)
        await self.db.flush()

        logger.info(
            "Prompt dupliziert: {source} -> {target} (Gruppe: {group})",
            source=source_slug,
            target=new_slug,
            group=group.name,
        )
        return new_slug

    async def _find_source_prompt_slug(self, tenant_id: str) -> str:
        """Find the prompt slug to duplicate from the last active group."""
        from sqlalchemy import func as sqlfunc

        result = await self.db.execute(
            select(CollectorGroup.analysis_prompt_slugs)
            .where(
                CollectorGroup.tenant_id == tenant_id,
                CollectorGroup.active.is_(True),
                sqlfunc.jsonb_array_length(CollectorGroup.analysis_prompt_slugs) > 0,
            )
            .order_by(CollectorGroup.created_at.desc())
            .limit(1)
        )
        slugs = result.scalar_one_or_none()
        if slugs and len(slugs) > 0:
            return slugs[0]
        return "research-topic-analyzer"

    async def list_groups(self, tenant_id: str) -> list[dict]:
        """List collector groups with counts."""
        query = (
            select(
                CollectorGroup,
                func.count(func.distinct(CollectorSource.id)).label("source_count"),
                func.count(func.distinct(CollectorFinding.id)).label("finding_count"),
                func.count(func.distinct(CollectorTopic.id)).label("topic_count"),
            )
            .outerjoin(CollectorSource, CollectorSource.group_id == CollectorGroup.id)
            .outerjoin(CollectorFinding, CollectorFinding.group_id == CollectorGroup.id)
            .outerjoin(CollectorTopic, CollectorTopic.group_id == CollectorGroup.id)
            .where(CollectorGroup.tenant_id == tenant_id)
            .group_by(CollectorGroup.id)
            .order_by(CollectorGroup.created_at.asc())
        )
        result = await self.db.execute(query)
        rows = result.all()

        groups = []
        for group, src_count, find_count, topic_count in rows:
            group.source_count = src_count
            group.finding_count = find_count
            group.topic_count = topic_count
            groups.append(group)
        return groups

    async def get_group(self, tenant_id: str, group_id: int) -> CollectorGroup:
        """Get a single collector group with counts."""
        query = (
            select(
                CollectorGroup,
                func.count(func.distinct(CollectorSource.id)).label("source_count"),
                func.count(func.distinct(CollectorFinding.id)).label("finding_count"),
                func.count(func.distinct(CollectorTopic.id)).label("topic_count"),
            )
            .outerjoin(CollectorSource, CollectorSource.group_id == CollectorGroup.id)
            .outerjoin(CollectorFinding, CollectorFinding.group_id == CollectorGroup.id)
            .outerjoin(CollectorTopic, CollectorTopic.group_id == CollectorGroup.id)
            .where(
                CollectorGroup.id == group_id,
                CollectorGroup.tenant_id == tenant_id,
            )
            .group_by(CollectorGroup.id)
        )
        result = await self.db.execute(query)
        row = result.one_or_none()
        if not row:
            raise NotFoundError("CollectorGroup", group_id)
        group, src_count, find_count, topic_count = row
        group.source_count = src_count
        group.finding_count = find_count
        group.topic_count = topic_count
        return group

    async def update_group(
        self, tenant_id: str, group_id: int, data: CollectorGroupUpdate
    ) -> CollectorGroup:
        """Update a collector group."""
        result = await self.db.execute(
            select(CollectorGroup).where(
                CollectorGroup.id == group_id,
                CollectorGroup.tenant_id == tenant_id,
            )
        )
        group = result.scalar_one_or_none()
        if not group:
            raise NotFoundError("CollectorGroup", group_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(group, field, value)
        await self.db.flush()
        await self.db.refresh(group)
        logger.info(
            "Collector Group aktualisiert: {id} (Tenant: {tenant})",
            id=group_id,
            tenant=tenant_id,
        )
        return group

    async def delete_group(self, tenant_id: str, group_id: int) -> None:
        """Delete a collector group. Children get group_id=NULL (SET NULL)."""
        result = await self.db.execute(
            select(CollectorGroup).where(
                CollectorGroup.id == group_id,
                CollectorGroup.tenant_id == tenant_id,
            )
        )
        group = result.scalar_one_or_none()
        if not group:
            raise NotFoundError("CollectorGroup", group_id)
        await self.db.delete(group)
        await self.db.flush()
        logger.info(
            "Collector Group geloescht: {id} (Tenant: {tenant})",
            id=group_id,
            tenant=tenant_id,
        )

    # --- Source CRUD ---

    async def create_source(
        self, tenant_id: str, data: CollectorSourceCreate
    ) -> CollectorSource:
        """Create a new collector source."""
        source = CollectorSource(
            tenant_id=tenant_id,
            name=data.name,
            url=data.url,
            source_type=data.source_type,
            keywords=data.keywords,
            fetch_interval_hours=data.fetch_interval_hours,
            config=data.config,
            tags=data.tags,
            streams=data.streams,
            change_detection_enabled=data.change_detection_enabled,
            group_id=data.group_id,
        )
        self.db.add(source)
        await self.db.flush()
        await self.db.refresh(source)
        logger.info(
            "Collector Source erstellt: {name} (Tenant: {tenant})",
            name=data.name,
            tenant=tenant_id,
        )
        return source

    async def list_sources(
        self,
        tenant_id: str,
        source_type: str | None = None,
        active: bool | None = None,
        tag: str | None = None,
        stream: str | None = None,
        group_id: int | None = None,
    ) -> list[CollectorSource]:
        """List collector sources for a tenant."""
        query = select(CollectorSource).where(CollectorSource.tenant_id == tenant_id)
        if source_type:
            query = query.where(CollectorSource.source_type == source_type)
        if active is not None:
            query = query.where(CollectorSource.active == active)
        if tag:
            query = query.where(CollectorSource.tags.op("@>")(json.dumps([tag])))
        if stream:
            query = query.where(CollectorSource.streams.op("@>")(json.dumps([stream])))
        if group_id is not None:
            query = query.where(CollectorSource.group_id == group_id)
        query = query.order_by(CollectorSource.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_source(self, tenant_id: str, source_id: int) -> CollectorSource:
        """Get a single collector source."""
        result = await self.db.execute(
            select(CollectorSource).where(
                CollectorSource.id == source_id,
                CollectorSource.tenant_id == tenant_id,
            )
        )
        source = result.scalar_one_or_none()
        if not source:
            raise NotFoundError("CollectorSource", source_id)
        return source

    async def update_source(
        self, tenant_id: str, source_id: int, data: CollectorSourceUpdate
    ) -> CollectorSource:
        """Update a collector source."""
        source = await self.get_source(tenant_id, source_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(source, field, value)
        await self.db.flush()
        await self.db.refresh(source)
        logger.info(
            "Collector Source aktualisiert: {id} (Tenant: {tenant})",
            id=source_id,
            tenant=tenant_id,
        )
        return source

    async def delete_source(self, tenant_id: str, source_id: int) -> None:
        """Delete a collector source."""
        source = await self.get_source(tenant_id, source_id)
        await self.db.delete(source)
        await self.db.flush()
        logger.info(
            "Collector Source geloescht: {id} (Tenant: {tenant})",
            id=source_id,
            tenant=tenant_id,
        )

    # --- Intelligent Scheduling ---

    async def _get_due_sources(self, tenant_id: str) -> list[CollectorSource]:
        """Get sources that are due for fetching."""
        now = datetime.utcnow()
        result = await self.db.execute(
            select(CollectorSource).where(
                CollectorSource.tenant_id == tenant_id,
                CollectorSource.active.is_(True),
            )
        )
        sources = list(result.scalars().all())
        return [
            s
            for s in sources
            if s.last_fetched_at is None
            or s.last_fetched_at + timedelta(hours=s.fetch_interval_hours) <= now
        ]

    # --- Fetch & Analyze ---

    async def run_collector(
        self,
        tenant_id: str,
        source_id: int | None,
        tenant_config: dict,
    ) -> dict:
        """Run collector: fetch sources, deduplicate, analyze findings."""
        errors: list[str] = []
        all_new_findings: list[CollectorFinding] = []

        if source_id:
            sources = [await self.get_source(tenant_id, source_id)]
        else:
            sources = await self._get_due_sources(tenant_id)

        for source in sources:
            try:
                if source.source_type == "inbox":
                    continue
                raw_items = await self._fetch_source(source)
                new_findings = await self._deduplicate_and_save(
                    tenant_id, source, raw_items
                )
                all_new_findings.extend(new_findings)
                source.last_fetched_at = datetime.utcnow()

                if source.change_detection_enabled and source.source_type == "website":
                    try:
                        await self._run_change_detection(tenant_id, source)
                    except Exception as e:
                        logger.error(
                            "Change-Detection Fehler fuer '{name}': {err}",
                            name=source.name,
                            err=str(e),
                        )
            except Exception as e:
                msg = f"Fehler bei Source '{source.name}': {e}"
                logger.error(msg)
                errors.append(msg)

        suggestions: list[CollectorTopic] = []
        if all_new_findings:
            try:
                suggestions = await self._analyze_findings(
                    tenant_id, all_new_findings, tenant_config
                )
            except Exception as e:
                msg = f"Fehler bei Analyse: {e}"
                logger.error(msg)
                errors.append(msg)

        await self.db.flush()

        from app.services.activity import ActivityService

        await ActivityService(self.db).log(
            tenant_id,
            "collector",
            "collector.run",
            f"Collector abgeschlossen: {len(all_new_findings)} Findings, {len(suggestions)} Topics",
            severity="success" if not errors else "warning",
        )
        return {
            "findings_count": len(all_new_findings),
            "suggestions_count": len(suggestions),
            "errors": errors,
        }

    async def _fetch_source(self, source: CollectorSource) -> list[dict]:
        """Dispatch to the right fetcher based on source type."""
        if source.source_type == "rss":
            return await self._fetch_rss(source)
        elif source.source_type == "website":
            return await self._fetch_website(source)
        elif source.source_type == "websearch":
            return await self._fetch_websearch(source)
        raise ValidationError(f"Unbekannter Source-Typ: {source.source_type}")

    async def _fetch_rss(self, source: CollectorSource) -> list[dict]:
        """Fetch and filter RSS feed entries via shared fetcher."""
        from app.utils.source_fetchers import fetch_rss

        return await fetch_rss(source.url, source.keywords)

    async def _fetch_website(self, source: CollectorSource) -> list[dict]:
        """Scrape a website for articles via shared fetcher."""
        from app.utils.source_fetchers import fetch_website

        cfg = source.config or {}
        selector = cfg.get("selector", "article, .post, .entry")
        return await fetch_website(source.url, source.keywords, selector)

    async def _fetch_websearch(self, source: CollectorSource) -> list[dict]:
        """Search via Serper API using shared fetcher."""
        from app.config import settings
        from app.utils.source_fetchers import fetch_websearch

        return await fetch_websearch(
            source.keywords or [source.url], settings.serper_api_key
        )

    async def _deduplicate_and_save(
        self,
        tenant_id: str,
        source: CollectorSource,
        raw_items: list[dict],
    ) -> list[CollectorFinding]:
        """Save findings, skip duplicates by URL. Inherit tags from source."""
        new_findings: list[CollectorFinding] = []

        for item in raw_items:
            url = item.get("url", "")
            if not url:
                continue

            existing = await self.db.execute(
                select(CollectorFinding).where(
                    CollectorFinding.tenant_id == tenant_id,
                    CollectorFinding.url == url,
                )
            )
            if existing.scalar_one_or_none():
                continue

            finding = CollectorFinding(
                tenant_id=tenant_id,
                source_id=source.id,
                group_id=source.group_id,
                title=item["title"],
                summary=item.get("summary"),
                url=url,
                content_snippet=item.get("content_snippet"),
                found_at=item.get("found_at", datetime.utcnow()),
                status="new",
                tags=source.tags or [],
                streams=source.streams or [],
            )
            self.db.add(finding)
            new_findings.append(finding)

        if new_findings:
            await self.db.flush()
            for f in new_findings:
                await self.db.refresh(f)

        return new_findings

    async def _analyze_findings(
        self,
        tenant_id: str,
        findings: list[CollectorFinding],
        tenant_config: dict,
    ) -> list[CollectorTopic]:
        """Use LLM to analyze findings per group using group-specific prompts."""
        from app.services.prompt import PromptService

        # Group findings by group_id
        grouped: dict[int | None, list[CollectorFinding]] = {}
        for f in findings:
            grouped.setdefault(f.group_id, []).append(f)

        all_suggestions: list[CollectorTopic] = []
        prompt_service = PromptService(self.db)

        for group_id, group_findings in grouped.items():
            prompt_slugs = await self._get_group_prompt_slugs(tenant_id, group_id)
            for prompt_slug in prompt_slugs:
                # Load prompt to check processing_mode
                try:
                    prompt = await prompt_service.get_active_by_slug(
                        tenant_id, prompt_slug
                    )
                except NotFoundError:
                    logger.warning(
                        "Prompt '{slug}' nicht gefunden, skip",
                        slug=prompt_slug,
                    )
                    continue

                mode = getattr(prompt, "processing_mode", "batch")
                if mode == "each":
                    for finding in group_findings:
                        suggestions = await self._analyze_findings_batch(
                            tenant_id, [finding], prompt_slug, tenant_config
                        )
                        all_suggestions.extend(suggestions)
                else:
                    suggestions = await self._analyze_findings_batch(
                        tenant_id, group_findings, prompt_slug, tenant_config
                    )
                    all_suggestions.extend(suggestions)

        return all_suggestions

    async def _get_group_prompt_slugs(
        self, tenant_id: str, group_id: int | None
    ) -> list[str]:
        """Get the analysis prompt slugs for a group, with fallback."""
        if group_id is None:
            return ["research-topic-analyzer"]
        result = await self.db.execute(
            select(CollectorGroup.analysis_prompt_slugs).where(
                CollectorGroup.id == group_id,
                CollectorGroup.tenant_id == tenant_id,
            )
        )
        slugs = result.scalar_one_or_none()
        if slugs and len(slugs) > 0:
            return slugs
        return ["research-topic-analyzer"]

    async def _analyze_findings_batch(
        self,
        tenant_id: str,
        findings: list[CollectorFinding],
        prompt_slug: str,
        tenant_config: dict,
    ) -> list[CollectorTopic]:
        """Analyze a batch of findings with a specific prompt slug."""
        from app.schemas.prompt import PromptExecuteRequest
        from app.services.prompt import PromptService

        finding_map = {f.id: f for f in findings}

        findings_json = json.dumps(
            [
                {
                    "id": f.id,
                    "title": f.title,
                    "summary": f.summary or "",
                    "url": f.url,
                    "content_snippet": (f.content_snippet or "")[:500],
                }
                for f in findings
            ],
            ensure_ascii=False,
        )

        all_keywords: list[str] = []
        for f in findings:
            if f.source and hasattr(f.source, "keywords") and f.source.keywords:
                all_keywords.extend(f.source.keywords)
        keywords_str = ", ".join(set(all_keywords)) or "allgemein"

        prompt_service = PromptService(self.db)
        try:
            exec_result = await prompt_service.execute(
                tenant_id,
                PromptExecuteRequest(
                    prompt_slug=prompt_slug,
                    variables={
                        "findings_json": findings_json,
                        "keywords": keywords_str,
                    },
                ),
                tenant_config,
            )
        except NotFoundError:
            logger.warning(
                "Prompt '{slug}' nicht gefunden, skip",
                slug=prompt_slug,
            )
            return []

        result = exec_result["result"]
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except json.JSONDecodeError:
                logger.error("Topic-Analyse JSON ungueltig")
                return []

        if not isinstance(result, list):
            result = [result]

        suggestions: list[CollectorTopic] = []
        for item in result:
            fid = item.get("finding_id")
            matched_finding = finding_map.get(fid) if fid else None
            if not matched_finding:
                matched_finding = findings[0] if findings else None

            f_tags = list(matched_finding.tags or []) if matched_finding else []
            f_streams = list(matched_finding.streams or []) if matched_finding else []
            f_group_id = matched_finding.group_id if matched_finding else None
            f_finding_id = matched_finding.id if matched_finding else None

            suggestion = CollectorTopic(
                tenant_id=tenant_id,
                finding_id=f_finding_id,
                group_id=f_group_id,
                title=str(item.get("title", ""))[:300],
                description=str(item.get("description", "")),
                detail=str(item.get("detail", "")) or None,
                category=str(item.get("category", "general")),
                priority=int(item.get("priority", 3)),
                source_type="research",
                status="suggested",
                tags=f_tags,
                streams=f_streams,
                target_modules=["creator"],
                prompt_slug=prompt_slug,
            )
            self.db.add(suggestion)
            suggestions.append(suggestion)

        if suggestions:
            await self.db.flush()
            for s in suggestions:
                await self.db.refresh(s)

        return suggestions

    # --- Group Prompt Management ---

    async def _get_group_raw(self, tenant_id: str, group_id: int) -> CollectorGroup:
        """Simple group lookup without counts."""
        result = await self.db.execute(
            select(CollectorGroup).where(
                CollectorGroup.id == group_id,
                CollectorGroup.tenant_id == tenant_id,
            )
        )
        group = result.scalar_one_or_none()
        if not group:
            raise NotFoundError("CollectorGroup", group_id)
        return group

    async def add_group_prompt(
        self,
        tenant_id: str,
        group_id: int,
        purpose: str,
        source_slug: str | None = None,
    ) -> dict:
        """Add a new prompt to a group by duplicating from a source prompt."""
        group = await self._get_group_raw(tenant_id, group_id)
        new_slug = f"{purpose}-{group.slug}"

        # Check for duplicate slug in group
        if new_slug in (group.analysis_prompt_slugs or []):
            raise DuplicateError("Prompt", "slug")

        prompt_slug = await self._duplicate_prompt_for_group(
            tenant_id, group, purpose=purpose, source_slug=source_slug
        )
        if not prompt_slug:
            raise ExternalServiceError(
                "Prompt", "Kein Quell-Prompt zum Duplizieren gefunden"
            )

        slugs = list(group.analysis_prompt_slugs or [])
        slugs.append(prompt_slug)
        group.analysis_prompt_slugs = slugs
        await self.db.flush()
        await self.db.refresh(group)

        logger.info(
            "Prompt '{slug}' zu Gruppe {group} hinzugefuegt",
            slug=prompt_slug,
            group=group.name,
        )
        return {
            "prompt_slug": prompt_slug,
            "analysis_prompt_slugs": group.analysis_prompt_slugs,
        }

    async def remove_group_prompt(
        self, tenant_id: str, group_id: int, prompt_slug: str
    ) -> None:
        """Remove a prompt from a group and delete its topics + prompt record."""
        from app.models.prompt import Prompt

        group = await self._get_group_raw(tenant_id, group_id)

        slugs = list(group.analysis_prompt_slugs or [])
        if prompt_slug not in slugs:
            raise NotFoundError("Prompt", prompt_slug)

        slugs.remove(prompt_slug)
        group.analysis_prompt_slugs = slugs

        # Delete topics generated by this prompt for this group
        await self.db.execute(
            delete(CollectorTopic).where(
                CollectorTopic.tenant_id == tenant_id,
                CollectorTopic.group_id == group_id,
                CollectorTopic.prompt_slug == prompt_slug,
            )
        )

        # Delete the prompt record itself
        await self.db.execute(
            delete(Prompt).where(
                Prompt.tenant_id == tenant_id,
                Prompt.slug == prompt_slug,
            )
        )

        await self.db.flush()
        logger.info(
            "Prompt '{slug}' aus Gruppe {group} entfernt",
            slug=prompt_slug,
            group=group.name,
        )

    async def run_group_prompt(
        self,
        tenant_id: str,
        group_id: int,
        prompt_slug: str,
        tenant_config: dict,
    ) -> dict:
        """Run a specific prompt for a group's findings."""
        from app.services.prompt import PromptService

        group = await self._get_group_raw(tenant_id, group_id)
        if prompt_slug not in (group.analysis_prompt_slugs or []):
            raise NotFoundError("Prompt", prompt_slug)

        # Load prompt to check processing_mode
        prompt_service = PromptService(self.db)
        prompt = await prompt_service.get_active_by_slug(tenant_id, prompt_slug)
        mode = getattr(prompt, "processing_mode", "batch")

        # Delete existing topics for this prompt + group
        result = await self.db.execute(
            delete(CollectorTopic).where(
                CollectorTopic.tenant_id == tenant_id,
                CollectorTopic.group_id == group_id,
                CollectorTopic.prompt_slug == prompt_slug,
            )
        )
        topics_deleted = result.rowcount

        # Load findings for this group (eager-load source for keywords)
        findings_result = await self.db.execute(
            select(CollectorFinding)
            .options(selectinload(CollectorFinding.source))
            .where(
                CollectorFinding.tenant_id == tenant_id,
                CollectorFinding.group_id == group_id,
            )
        )
        findings = list(findings_result.scalars().all())

        if not findings:
            await self.db.flush()
            return {"topics_created": 0, "topics_deleted": topics_deleted}

        # Run analysis based on mode
        all_topics: list[CollectorTopic] = []
        if mode == "each":
            for finding in findings:
                topics = await self._analyze_findings_batch(
                    tenant_id, [finding], prompt_slug, tenant_config
                )
                all_topics.extend(topics)
        else:
            topics = await self._analyze_findings_batch(
                tenant_id, findings, prompt_slug, tenant_config
            )
            all_topics.extend(topics)

        logger.info(
            "Prompt '{slug}' fuer Gruppe {group} ausgefuehrt: {created} Topics",
            slug=prompt_slug,
            group=group.name,
            created=len(all_topics),
        )
        return {
            "topics_created": len(all_topics),
            "topics_deleted": topics_deleted,
        }

    # --- Generic Finding Import ---

    async def import_finding(
        self, tenant_id: str, data: FindingImport
    ) -> CollectorFinding:
        """Import a finding from an external source (n8n, webhook)."""
        # Deduplicate by URL
        existing = await self.db.execute(
            select(CollectorFinding).where(
                CollectorFinding.tenant_id == tenant_id,
                CollectorFinding.url == data.url,
            )
        )
        if existing.scalar_one_or_none():
            raise ValidationError(f"Finding mit URL '{data.url}' existiert bereits")

        finding = CollectorFinding(
            tenant_id=tenant_id,
            source_id=data.source_id,
            group_id=data.group_id,
            title=data.title[:500],
            summary=data.summary,
            url=data.url,
            content_snippet=data.content_snippet,
            found_at=datetime.utcnow(),
            status="new",
            tags=data.tags,
        )
        self.db.add(finding)
        await self.db.flush()
        await self.db.refresh(finding)
        logger.info(
            "Finding importiert: {title} (Tenant: {tenant})",
            title=data.title[:50],
            tenant=tenant_id,
        )
        return finding

    # --- Content Inbox ---

    async def create_inbox_item(
        self, tenant_id: str, data: InboxItemCreate
    ) -> CollectorFinding:
        """Create a finding from an inbox item (WhatsApp/Email)."""
        finding = CollectorFinding(
            tenant_id=tenant_id,
            source_id=None,
            title=data.text[:500],
            summary=data.text,
            url=f"inbox://{data.source_channel}/{datetime.utcnow().isoformat()}",
            found_at=datetime.utcnow(),
            status="new",
            tags=data.tags,
        )
        self.db.add(finding)
        await self.db.flush()
        await self.db.refresh(finding)
        logger.info(
            "Inbox Item erstellt: {channel} (Tenant: {tenant})",
            channel=data.source_channel,
            tenant=tenant_id,
        )
        return finding

    # --- Change Detection ---

    async def detect_changes(self, tenant_id: str, source_id: int) -> dict:
        """Run change detection for a specific website source."""
        source = await self.get_source(tenant_id, source_id)
        if source.source_type != "website":
            raise ValidationError("Change-Detection nur fuer Website-Quellen")

        return await self._run_change_detection(tenant_id, source)

    async def _run_change_detection(
        self, tenant_id: str, source: CollectorSource
    ) -> dict:
        """Fetch page, compare with last snapshot, analyze changes."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(source.url)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)

        content_hash = hashlib.sha256(text.encode()).hexdigest()

        last_snapshot = await self.db.execute(
            select(PageSnapshot)
            .where(
                PageSnapshot.source_id == source.id,
                PageSnapshot.tenant_id == tenant_id,
            )
            .order_by(PageSnapshot.snapshot_at.desc())
            .limit(1)
        )
        previous = last_snapshot.scalar_one_or_none()

        changed = previous is None or previous.content_hash != content_hash
        diff_text = None
        summary = None
        significance = "none"

        if changed and previous:
            old_lines = previous.content_text.splitlines()
            new_lines = text.splitlines()
            diff_text = "\n".join(
                difflib.unified_diff(old_lines, new_lines, lineterm="", n=3)
            )
            if diff_text:
                significance = self._estimate_significance(diff_text)

        snapshot = PageSnapshot(
            tenant_id=tenant_id,
            source_id=source.id,
            group_id=source.group_id,
            url=source.url,
            content_hash=content_hash,
            content_text=text[:50000],
            snapshot_at=datetime.utcnow(),
            diff_from_previous=diff_text[:10000] if diff_text else None,
            change_summary=summary,
            change_significance=significance if changed else "none",
        )
        self.db.add(snapshot)
        await self.db.flush()
        await self.db.refresh(snapshot)

        if changed and significance in ("high", "medium"):
            finding = CollectorFinding(
                tenant_id=tenant_id,
                source_id=source.id,
                group_id=source.group_id,
                title=f"Aenderung erkannt: {source.name}",
                summary=summary or f"Signifikante Aenderung auf {source.url}",
                url=source.url,
                found_at=datetime.utcnow(),
                status="new",
                tags=source.tags or [],
                streams=source.streams or [],
            )
            self.db.add(finding)
            await self.db.flush()

        return {
            "changed": changed,
            "significance": significance if changed else None,
            "summary": summary,
            "snapshot_id": snapshot.id,
        }

    async def list_snapshots(
        self, tenant_id: str, source_id: int
    ) -> list[PageSnapshot]:
        """List snapshots for a source."""
        result = await self.db.execute(
            select(PageSnapshot)
            .where(
                PageSnapshot.tenant_id == tenant_id,
                PageSnapshot.source_id == source_id,
            )
            .order_by(PageSnapshot.snapshot_at.desc())
            .limit(50)
        )
        return list(result.scalars().all())

    @staticmethod
    def _estimate_significance(diff_text: str) -> str:
        """Estimate significance of changes based on diff size."""
        lines = [
            line
            for line in diff_text.splitlines()
            if line.startswith("+") or line.startswith("-")
        ]
        lines = [
            line
            for line in lines
            if not line.startswith("+++") and not line.startswith("---")
        ]
        if len(lines) > 50:
            return "high"
        if len(lines) > 10:
            return "medium"
        if len(lines) > 0:
            return "low"
        return "none"

    # --- Findings CRUD ---

    async def list_findings(
        self,
        tenant_id: str,
        status: str | None = None,
        source_id: int | None = None,
        tag: str | None = None,
        stream: str | None = None,
        group_id: int | None = None,
    ) -> list[CollectorFinding]:
        """List findings for a tenant."""
        query = select(CollectorFinding).where(CollectorFinding.tenant_id == tenant_id)
        if status:
            query = query.where(CollectorFinding.status == status)
        if source_id:
            query = query.where(CollectorFinding.source_id == source_id)
        if tag:
            query = query.where(CollectorFinding.tags.op("@>")(json.dumps([tag])))
        if stream:
            query = query.where(CollectorFinding.streams.op("@>")(json.dumps([stream])))
        if group_id is not None:
            query = query.where(CollectorFinding.group_id == group_id)
        query = query.order_by(CollectorFinding.found_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_finding(
        self,
        tenant_id: str,
        finding_id: int,
        status: str | None = None,
        group_id: int | None = None,
    ) -> CollectorFinding:
        """Update a finding (status and/or group)."""
        result = await self.db.execute(
            select(CollectorFinding).where(
                CollectorFinding.id == finding_id,
                CollectorFinding.tenant_id == tenant_id,
            )
        )
        finding = result.scalar_one_or_none()
        if not finding:
            raise NotFoundError("CollectorFinding", finding_id)
        if status is not None:
            finding.status = status
        if group_id is not None:
            finding.group_id = group_id
        await self.db.flush()
        await self.db.refresh(finding)
        return finding

    # --- Topic Suggestions CRUD ---

    async def create_topic(
        self, tenant_id: str, data: CollectorTopicCreate
    ) -> CollectorTopic:
        """Create a topic (manual / eigene Themen)."""
        topic = CollectorTopic(
            tenant_id=tenant_id,
            title=data.title,
            description=data.description,
            detail=data.detail,
            category=data.category,
            platforms=data.platforms,
            priority=data.priority,
            source_type=data.source_type,
            image_url=data.image_url,
            status="suggested",
            tags=data.tags,
            streams=data.streams,
            target_modules=["creator"],
            group_id=data.group_id,
        )
        self.db.add(topic)
        await self.db.flush()
        await self.db.refresh(topic)
        logger.info(
            "Topic erstellt: {title} (Tenant: {tenant})",
            title=data.title,
            tenant=tenant_id,
        )
        return topic

    async def list_topics(
        self,
        tenant_id: str,
        status: str | None = None,
        source_type: str | None = None,
        tag: str | None = None,
        stream: str | None = None,
        group_id: int | None = None,
    ) -> list[CollectorTopic]:
        """List topics for a tenant."""
        query = select(CollectorTopic).where(CollectorTopic.tenant_id == tenant_id)
        if status:
            query = query.where(CollectorTopic.status == status)
        if source_type:
            query = query.where(CollectorTopic.source_type == source_type)
        if tag:
            query = query.where(CollectorTopic.tags.op("@>")(json.dumps([tag])))
        if stream:
            query = query.where(CollectorTopic.streams.op("@>")(json.dumps([stream])))
        if group_id is not None:
            query = query.where(CollectorTopic.group_id == group_id)
        query = query.order_by(
            CollectorTopic.priority.asc(), CollectorTopic.created_at.desc()
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_topic(self, tenant_id: str, topic_id: int) -> CollectorTopic:
        """Get a single topic."""
        result = await self.db.execute(
            select(CollectorTopic).where(
                CollectorTopic.id == topic_id,
                CollectorTopic.tenant_id == tenant_id,
            )
        )
        topic = result.scalar_one_or_none()
        if not topic:
            raise NotFoundError("CollectorTopic", topic_id)
        return topic

    async def update_topic(
        self, tenant_id: str, topic_id: int, data: CollectorTopicUpdate
    ) -> CollectorTopic:
        """Update a topic."""
        topic = await self.get_topic(tenant_id, topic_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(topic, field, value)
        await self.db.flush()
        await self.db.refresh(topic)
        logger.info(
            "Topic aktualisiert: {id} status={status} (Tenant: {tenant})",
            id=topic_id,
            status=topic.status,
            tenant=tenant_id,
        )
        return topic

    async def get_topic_detail(self, tenant_id: str, topic_id: int) -> dict:
        """Get topic with finding URL and title for detail view."""
        topic = await self.get_topic(tenant_id, topic_id)
        finding_url = None
        finding_title = None
        if topic.finding_id:
            result = await self.db.execute(
                select(CollectorFinding).where(
                    CollectorFinding.id == topic.finding_id,
                )
            )
            finding = result.scalar_one_or_none()
            if finding:
                finding_url = finding.url
                finding_title = finding.title

        # Build response dict from ORM object
        topic_dict = {c.key: getattr(topic, c.key) for c in topic.__table__.columns}
        topic_dict["finding_url"] = finding_url
        topic_dict["finding_title"] = finding_title
        return topic_dict

    async def reanalyze_topic(
        self, tenant_id: str, topic_id: int, tenant_config: dict
    ) -> CollectorTopic:
        """Re-analyze a topic using its prompt_slug."""
        from app.schemas.prompt import PromptExecuteRequest
        from app.services.prompt import PromptService

        topic = await self.get_topic(tenant_id, topic_id)
        slug = topic.prompt_slug or "research-topic-analyzer"

        # Get the finding for context
        finding = None
        if topic.finding_id:
            result = await self.db.execute(
                select(CollectorFinding).where(
                    CollectorFinding.id == topic.finding_id,
                )
            )
            finding = result.scalar_one_or_none()

        if not finding:
            raise NotFoundError("CollectorFinding", topic.finding_id or 0)

        findings_json = json.dumps(
            [
                {
                    "id": finding.id,
                    "title": finding.title,
                    "summary": finding.summary or "",
                    "url": finding.url,
                    "content_snippet": (finding.content_snippet or "")[:500],
                }
            ],
            ensure_ascii=False,
        )

        all_keywords: list[str] = []
        if finding.source and hasattr(finding.source, "keywords"):
            all_keywords = finding.source.keywords or []
        keywords_str = ", ".join(all_keywords) or "allgemein"

        prompt_service = PromptService(self.db)
        exec_result = await prompt_service.execute(
            tenant_id,
            PromptExecuteRequest(
                prompt_slug=slug,
                variables={
                    "findings_json": findings_json,
                    "keywords": keywords_str,
                },
            ),
            tenant_config,
        )

        result = exec_result["result"]
        if isinstance(result, str):
            result = json.loads(result)
        if isinstance(result, list) and len(result) > 0:
            result = result[0]

        topic.title = str(result.get("title", topic.title))[:300]
        topic.description = str(result.get("description", topic.description))
        topic.detail = str(result.get("detail", "")) or topic.detail
        await self.db.flush()
        await self.db.refresh(topic)

        logger.info(
            "Topic neu analysiert: {id} (Tenant: {tenant})",
            id=topic_id,
            tenant=tenant_id,
        )
        return topic

    async def delete_topic(self, tenant_id: str, topic_id: int) -> None:
        """Delete a topic."""
        topic = await self.get_topic(tenant_id, topic_id)
        await self.db.delete(topic)
        await self.db.flush()
        logger.info(
            "Topic geloescht: {id} (Tenant: {tenant})",
            id=topic_id,
            tenant=tenant_id,
        )

    async def generate_from_topic(
        self,
        tenant_id: str,
        topic_id: int,
        platform: str,
        content_type: str,
        tenant_config: dict,
    ) -> object:
        """Generate content from a topic via CreatorService."""
        from app.creator.schemas import CreatorGenerateFromTopic
        from app.creator.service import CreatorService

        topic = await self.get_topic(tenant_id, topic_id)
        topic.status = "generating"
        await self.db.flush()

        creator_service = CreatorService(self.db)
        data = CreatorGenerateFromTopic(
            title=topic.title,
            description=topic.description,
            platform=platform,
            content_type=content_type,
            image_url=topic.image_url,
        )

        piece = await creator_service.generate_from_topic(
            tenant_id, data, tenant_config
        )

        topic.status = "generated"
        topic.content_piece_id = piece.id
        await self.db.flush()
        await self.db.refresh(topic)

        logger.info(
            "Content aus Topic generiert: topic={tid} piece={pid}",
            tid=topic_id,
            pid=piece.id,
        )

        from app.services.activity import ActivityService

        await ActivityService(self.db).log(
            tenant_id,
            "collector",
            "collector.generated",
            f"Content aus Topic '{topic.title}' generiert",
            entity_type="collector_topic",
            entity_id=topic_id,
            severity="success",
        )
        return piece

    # --- Analyze Single Finding ---

    async def analyze_finding(
        self,
        tenant_id: str,
        finding_id: int,
        tenant_config: dict,
    ) -> list[CollectorTopic]:
        """Generate topics from a single finding, deleting existing topics first."""
        # Delete existing topics for this finding (re-analyze)
        existing_topics = await self.db.execute(
            select(CollectorTopic).where(
                CollectorTopic.tenant_id == tenant_id,
                CollectorTopic.finding_id == finding_id,
            )
        )
        for topic in existing_topics.scalars().all():
            await self.db.delete(topic)
        await self.db.flush()

        # Load the finding (eager-load source for keyword access)
        result = await self.db.execute(
            select(CollectorFinding)
            .options(selectinload(CollectorFinding.source))
            .where(
                CollectorFinding.id == finding_id,
                CollectorFinding.tenant_id == tenant_id,
            )
        )
        finding = result.scalar_one_or_none()
        if not finding:
            raise NotFoundError("CollectorFinding", finding_id)

        # Get group-specific prompt slugs and use the first one
        prompt_slugs = await self._get_group_prompt_slugs(tenant_id, finding.group_id)
        prompt_slug = prompt_slugs[0] if prompt_slugs else "research-topic-analyzer"

        # Analyze with just this one finding
        topics = await self._analyze_findings_batch(
            tenant_id, [finding], prompt_slug, tenant_config
        )

        logger.info(
            "Finding analysiert: {id} -> {count} Topics (Tenant: {tenant})",
            id=finding_id,
            count=len(topics),
            tenant=tenant_id,
        )
        return topics

    # --- Bulk Delete ---

    async def bulk_delete_findings(self, tenant_id: str, finding_ids: list[int]) -> int:
        """Delete multiple findings by IDs (and their child topics)."""
        # Delete child topics first (FK has no ondelete CASCADE)
        await self.db.execute(
            delete(CollectorTopic).where(
                CollectorTopic.tenant_id == tenant_id,
                CollectorTopic.finding_id.in_(finding_ids),
            )
        )
        result = await self.db.execute(
            delete(CollectorFinding).where(
                CollectorFinding.tenant_id == tenant_id,
                CollectorFinding.id.in_(finding_ids),
            )
        )
        await self.db.flush()
        deleted = result.rowcount
        logger.info(
            "Findings bulk-geloescht: {count} von {requested} (Tenant: {tenant})",
            count=deleted,
            requested=len(finding_ids),
            tenant=tenant_id,
        )
        return deleted

    async def bulk_delete_topics(self, tenant_id: str, topic_ids: list[int]) -> int:
        """Delete multiple topics by IDs."""
        result = await self.db.execute(
            delete(CollectorTopic).where(
                CollectorTopic.tenant_id == tenant_id,
                CollectorTopic.id.in_(topic_ids),
            )
        )
        await self.db.flush()
        deleted = result.rowcount
        logger.info(
            "Topics bulk-geloescht: {count} von {requested} (Tenant: {tenant})",
            count=deleted,
            requested=len(topic_ids),
            tenant=tenant_id,
        )
        return deleted

    # --- Helpers ---

    @staticmethod
    def _matches_keywords(title: str, text: str, keywords: list[str]) -> bool:
        """Check if title or text contains any of the keywords."""
        combined = f"{title} {text}".lower()
        return any(kw in combined for kw in keywords)
