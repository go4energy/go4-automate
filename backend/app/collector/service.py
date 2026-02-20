"""Collector service - source fetching, finding analysis, topic management, change detection."""

import difflib
import hashlib
import json
from datetime import datetime, timedelta

import feedparser
import httpx
from bs4 import BeautifulSoup
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.collector.categories import get_all_categories
from app.collector.models import (
    CollectorFinding,
    CollectorSource,
    CollectorTopic,
    PageSnapshot,
)
from app.collector.schemas import (
    CollectorSourceCreate,
    CollectorSourceUpdate,
    CollectorTopicCreate,
    CollectorTopicUpdate,
    InboxItemCreate,
)
from app.exceptions import ExternalServiceError, NotFoundError, ValidationError


class CollectorService:
    """Service for collector sources, findings, topics, and change detection."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # --- Categories ---

    async def get_categories(self, tenant_id: str) -> list[dict]:
        """Get all categories (default + tenant custom)."""
        from app.models.tenant import Tenant

        result = await self.db.execute(
            select(Tenant).where(Tenant.tenant_id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        custom = (tenant.config or {}).get("custom_categories", []) if tenant else []
        return get_all_categories(custom)

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
            categories=data.categories,
            change_detection_enabled=data.change_detection_enabled,
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
        category: str | None = None,
    ) -> list[CollectorSource]:
        """List collector sources for a tenant."""
        query = select(CollectorSource).where(CollectorSource.tenant_id == tenant_id)
        if source_type:
            query = query.where(CollectorSource.source_type == source_type)
        if active is not None:
            query = query.where(CollectorSource.active == active)
        if category:
            query = query.where(
                CollectorSource.categories.op("@>")(json.dumps([category]))
            )
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
        """Fetch and filter RSS feed entries."""
        feed = feedparser.parse(source.url)
        keywords = [k.lower() for k in (source.keywords or [])]
        items: list[dict] = []

        for entry in feed.entries[:50]:
            title = entry.get("title", "")
            summary = entry.get("summary", "")
            link = entry.get("link", "")

            if keywords and not self._matches_keywords(title, summary, keywords):
                continue

            published = entry.get("published_parsed")
            found_at = datetime(*published[:6]) if published else datetime.utcnow()

            items.append(
                {
                    "title": title[:500],
                    "summary": summary[:1000] if summary else None,
                    "url": link,
                    "found_at": found_at,
                }
            )

        return items

    async def _fetch_website(self, source: CollectorSource) -> list[dict]:
        """Scrape a website for articles matching keywords."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(source.url)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        keywords = [k.lower() for k in (source.keywords or [])]
        items: list[dict] = []

        cfg = source.config or {}
        selector = cfg.get("selector", "article, .post, .entry")
        articles = soup.select(selector)

        if not articles:
            articles = soup.find_all(["article", "h2", "h3"])

        for article in articles[:30]:
            title_el = article.find(["h1", "h2", "h3", "a"])
            title = title_el.get_text(strip=True) if title_el else ""
            if not title:
                continue

            link_el = article.find("a", href=True)
            link = link_el["href"] if link_el else source.url
            if link.startswith("/"):
                from urllib.parse import urljoin

                link = urljoin(source.url, link)

            snippet_el = article.find("p")
            snippet = snippet_el.get_text(strip=True)[:500] if snippet_el else None

            if keywords and not self._matches_keywords(title, snippet or "", keywords):
                continue

            items.append(
                {
                    "title": title[:500],
                    "summary": snippet,
                    "url": link,
                    "content_snippet": snippet,
                    "found_at": datetime.utcnow(),
                }
            )

        return items

    async def _fetch_websearch(self, source: CollectorSource) -> list[dict]:
        """Search via Serper API."""
        from app.config import settings

        if not settings.serper_api_key:
            raise ExternalServiceError("Serper", "API Key nicht konfiguriert")

        query = " ".join(source.keywords or [source.url])
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://google.serper.dev/search",
                headers={
                    "X-API-KEY": settings.serper_api_key,
                    "Content-Type": "application/json",
                },
                json={"q": query, "num": 10},
            )
            resp.raise_for_status()

        data = resp.json()
        items: list[dict] = []

        for result in data.get("organic", [])[:10]:
            items.append(
                {
                    "title": result.get("title", "")[:500],
                    "summary": result.get("snippet", "")[:1000],
                    "url": result.get("link", ""),
                    "found_at": datetime.utcnow(),
                }
            )

        return items

    async def _deduplicate_and_save(
        self,
        tenant_id: str,
        source: CollectorSource,
        raw_items: list[dict],
    ) -> list[CollectorFinding]:
        """Save findings, skip duplicates by URL. Inherit categories from source."""
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
                title=item["title"],
                summary=item.get("summary"),
                url=url,
                content_snippet=item.get("content_snippet"),
                found_at=item.get("found_at", datetime.utcnow()),
                status="new",
                categories=source.categories or [],
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
        """Use LLM to analyze findings and generate topic suggestions."""
        from app.schemas.prompt import PromptExecuteRequest
        from app.services.prompt import PromptService

        findings_json = json.dumps(
            [
                {
                    "title": f.title,
                    "summary": f.summary or "",
                    "url": f.url,
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
                    prompt_slug="research-topic-analyzer",
                    variables={
                        "findings_json": findings_json,
                        "keywords": keywords_str,
                    },
                ),
                tenant_config,
            )
        except NotFoundError:
            logger.warning("Prompt 'research-topic-analyzer' nicht gefunden, skip")
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

        # Collect categories from the findings
        all_categories: list[str] = []
        for f in findings:
            all_categories.extend(f.categories or [])
        unique_categories = list(set(all_categories)) or ["social_media"]

        suggestions: list[CollectorTopic] = []
        for item in result[:5]:
            suggestion = CollectorTopic(
                tenant_id=tenant_id,
                finding_id=findings[0].id if findings else None,
                title=str(item.get("title", ""))[:300],
                description=str(item.get("description", "")),
                category=str(item.get("category", "general")),
                platforms=item.get("platforms"),
                priority=int(item.get("priority", 3)),
                source_type="research",
                status="suggested",
                categories=unique_categories,
                target_modules=["creator"],
            )
            self.db.add(suggestion)
            suggestions.append(suggestion)

        if suggestions:
            await self.db.flush()
            for s in suggestions:
                await self.db.refresh(s)

        return suggestions

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
            categories=data.categories,
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
                title=f"Aenderung erkannt: {source.name}",
                summary=summary or f"Signifikante Aenderung auf {source.url}",
                url=source.url,
                found_at=datetime.utcnow(),
                status="new",
                categories=source.categories or [],
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
        category: str | None = None,
    ) -> list[CollectorFinding]:
        """List findings for a tenant."""
        query = select(CollectorFinding).where(CollectorFinding.tenant_id == tenant_id)
        if status:
            query = query.where(CollectorFinding.status == status)
        if source_id:
            query = query.where(CollectorFinding.source_id == source_id)
        if category:
            query = query.where(
                CollectorFinding.categories.op("@>")(json.dumps([category]))
            )
        query = query.order_by(CollectorFinding.found_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_finding_status(
        self, tenant_id: str, finding_id: int, status: str
    ) -> CollectorFinding:
        """Update the status of a finding."""
        result = await self.db.execute(
            select(CollectorFinding).where(
                CollectorFinding.id == finding_id,
                CollectorFinding.tenant_id == tenant_id,
            )
        )
        finding = result.scalar_one_or_none()
        if not finding:
            raise NotFoundError("CollectorFinding", finding_id)
        finding.status = status
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
            category=data.category,
            platforms=data.platforms,
            priority=data.priority,
            source_type=data.source_type,
            image_url=data.image_url,
            status="suggested",
            categories=data.categories,
            target_modules=["creator"],
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
        category: str | None = None,
    ) -> list[CollectorTopic]:
        """List topics for a tenant."""
        query = select(CollectorTopic).where(CollectorTopic.tenant_id == tenant_id)
        if status:
            query = query.where(CollectorTopic.status == status)
        if source_type:
            query = query.where(CollectorTopic.source_type == source_type)
        if category:
            query = query.where(
                CollectorTopic.categories.op("@>")(json.dumps([category]))
            )
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

    # --- Helpers ---

    @staticmethod
    def _matches_keywords(title: str, text: str, keywords: list[str]) -> bool:
        """Check if title or text contains any of the keywords."""
        combined = f"{title} {text}".lower()
        return any(kw in combined for kw in keywords)
