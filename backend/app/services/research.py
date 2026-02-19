"""Research service - source fetching, finding analysis, topic management."""

import json
from datetime import datetime

import feedparser
import httpx
from bs4 import BeautifulSoup
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ExternalServiceError, NotFoundError, ValidationError
from app.models.research_finding import ResearchFinding
from app.models.research_source import ResearchSource
from app.models.topic_suggestion import TopicSuggestion
from app.schemas.research import (
    ResearchSourceCreate,
    ResearchSourceUpdate,
    TopicSuggestionCreate,
    TopicSuggestionUpdate,
)


class ResearchService:
    """Service for research sources, findings, and topic suggestions."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # --- Source CRUD ---

    async def create_source(
        self, tenant_id: str, data: ResearchSourceCreate
    ) -> ResearchSource:
        """Create a new research source."""
        source = ResearchSource(
            tenant_id=tenant_id,
            name=data.name,
            url=data.url,
            source_type=data.source_type,
            keywords=data.keywords,
            fetch_interval_hours=data.fetch_interval_hours,
            config=data.config,
        )
        self.db.add(source)
        await self.db.flush()
        await self.db.refresh(source)
        logger.info(
            "Research Source erstellt: {name} (Tenant: {tenant})",
            name=data.name,
            tenant=tenant_id,
        )
        return source

    async def list_sources(
        self,
        tenant_id: str,
        source_type: str | None = None,
        active: bool | None = None,
    ) -> list[ResearchSource]:
        """List research sources for a tenant."""
        query = select(ResearchSource).where(ResearchSource.tenant_id == tenant_id)
        if source_type:
            query = query.where(ResearchSource.source_type == source_type)
        if active is not None:
            query = query.where(ResearchSource.active == active)
        query = query.order_by(ResearchSource.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_source(self, tenant_id: str, source_id: int) -> ResearchSource:
        """Get a single research source."""
        result = await self.db.execute(
            select(ResearchSource).where(
                ResearchSource.id == source_id,
                ResearchSource.tenant_id == tenant_id,
            )
        )
        source = result.scalar_one_or_none()
        if not source:
            raise NotFoundError("ResearchSource", source_id)
        return source

    async def update_source(
        self, tenant_id: str, source_id: int, data: ResearchSourceUpdate
    ) -> ResearchSource:
        """Update a research source."""
        source = await self.get_source(tenant_id, source_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(source, field, value)
        await self.db.flush()
        await self.db.refresh(source)
        logger.info(
            "Research Source aktualisiert: {id} (Tenant: {tenant})",
            id=source_id,
            tenant=tenant_id,
        )
        return source

    async def delete_source(self, tenant_id: str, source_id: int) -> None:
        """Delete a research source."""
        source = await self.get_source(tenant_id, source_id)
        await self.db.delete(source)
        await self.db.flush()
        logger.info(
            "Research Source gelöscht: {id} (Tenant: {tenant})",
            id=source_id,
            tenant=tenant_id,
        )

    # --- Fetch & Analyze ---

    async def run_research(
        self,
        tenant_id: str,
        source_id: int | None,
        tenant_config: dict,
    ) -> dict:
        """Run research: fetch sources, deduplicate, analyze findings."""
        errors: list[str] = []
        all_new_findings: list[ResearchFinding] = []

        if source_id:
            sources = [await self.get_source(tenant_id, source_id)]
        else:
            sources = await self.list_sources(tenant_id, active=True)

        for source in sources:
            try:
                raw_items = await self._fetch_source(source)
                new_findings = await self._deduplicate_and_save(
                    tenant_id, source.id, raw_items
                )
                all_new_findings.extend(new_findings)
                source.last_fetched_at = datetime.utcnow()
            except Exception as e:
                msg = f"Fehler bei Source '{source.name}': {e}"
                logger.error(msg)
                errors.append(msg)

        suggestions: list[TopicSuggestion] = []
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
        return {
            "findings_count": len(all_new_findings),
            "suggestions_count": len(suggestions),
            "errors": errors,
        }

    async def _fetch_source(self, source: ResearchSource) -> list[dict]:
        """Dispatch to the right fetcher based on source type."""
        if source.source_type == "rss":
            return await self._fetch_rss(source)
        elif source.source_type == "website":
            return await self._fetch_website(source)
        elif source.source_type == "websearch":
            return await self._fetch_websearch(source)
        raise ValidationError(f"Unbekannter Source-Typ: {source.source_type}")

    async def _fetch_rss(self, source: ResearchSource) -> list[dict]:
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

    async def _fetch_website(self, source: ResearchSource) -> list[dict]:
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

    async def _fetch_websearch(self, source: ResearchSource) -> list[dict]:
        """Search via Serper API (or similar)."""
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
        source_id: int,
        raw_items: list[dict],
    ) -> list[ResearchFinding]:
        """Save findings, skip duplicates by URL."""
        new_findings: list[ResearchFinding] = []

        for item in raw_items:
            url = item.get("url", "")
            if not url:
                continue

            existing = await self.db.execute(
                select(ResearchFinding).where(
                    ResearchFinding.tenant_id == tenant_id,
                    ResearchFinding.url == url,
                )
            )
            if existing.scalar_one_or_none():
                continue

            finding = ResearchFinding(
                tenant_id=tenant_id,
                source_id=source_id,
                title=item["title"],
                summary=item.get("summary"),
                url=url,
                content_snippet=item.get("content_snippet"),
                found_at=item.get("found_at", datetime.utcnow()),
                status="new",
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
        findings: list[ResearchFinding],
        tenant_config: dict,
    ) -> list[TopicSuggestion]:
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
                logger.error("Topic-Analyse JSON ungültig")
                return []

        if not isinstance(result, list):
            result = [result]

        suggestions: list[TopicSuggestion] = []
        for item in result[:5]:
            suggestion = TopicSuggestion(
                tenant_id=tenant_id,
                finding_id=findings[0].id if findings else None,
                title=str(item.get("title", ""))[:300],
                description=str(item.get("description", "")),
                category=str(item.get("category", "general")),
                platforms=item.get("platforms"),
                priority=int(item.get("priority", 3)),
                source_type="research",
                status="suggested",
            )
            self.db.add(suggestion)
            suggestions.append(suggestion)

        if suggestions:
            await self.db.flush()
            for s in suggestions:
                await self.db.refresh(s)

        return suggestions

    # --- Findings CRUD ---

    async def list_findings(
        self,
        tenant_id: str,
        status: str | None = None,
        source_id: int | None = None,
    ) -> list[ResearchFinding]:
        """List findings for a tenant."""
        query = select(ResearchFinding).where(ResearchFinding.tenant_id == tenant_id)
        if status:
            query = query.where(ResearchFinding.status == status)
        if source_id:
            query = query.where(ResearchFinding.source_id == source_id)
        query = query.order_by(ResearchFinding.found_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_finding_status(
        self, tenant_id: str, finding_id: int, status: str
    ) -> ResearchFinding:
        """Update the status of a finding."""
        result = await self.db.execute(
            select(ResearchFinding).where(
                ResearchFinding.id == finding_id,
                ResearchFinding.tenant_id == tenant_id,
            )
        )
        finding = result.scalar_one_or_none()
        if not finding:
            raise NotFoundError("ResearchFinding", finding_id)
        finding.status = status
        await self.db.flush()
        await self.db.refresh(finding)
        return finding

    # --- Topic Suggestions CRUD ---

    async def create_topic(
        self, tenant_id: str, data: TopicSuggestionCreate
    ) -> TopicSuggestion:
        """Create a topic suggestion (manual / eigene Themen)."""
        topic = TopicSuggestion(
            tenant_id=tenant_id,
            title=data.title,
            description=data.description,
            category=data.category,
            platforms=data.platforms,
            priority=data.priority,
            source_type=data.source_type,
            image_url=data.image_url,
            status="suggested",
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
    ) -> list[TopicSuggestion]:
        """List topic suggestions for a tenant."""
        query = select(TopicSuggestion).where(TopicSuggestion.tenant_id == tenant_id)
        if status:
            query = query.where(TopicSuggestion.status == status)
        if source_type:
            query = query.where(TopicSuggestion.source_type == source_type)
        query = query.order_by(
            TopicSuggestion.priority.asc(), TopicSuggestion.created_at.desc()
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_topic(self, tenant_id: str, topic_id: int) -> TopicSuggestion:
        """Get a single topic suggestion."""
        result = await self.db.execute(
            select(TopicSuggestion).where(
                TopicSuggestion.id == topic_id,
                TopicSuggestion.tenant_id == tenant_id,
            )
        )
        topic = result.scalar_one_or_none()
        if not topic:
            raise NotFoundError("TopicSuggestion", topic_id)
        return topic

    async def update_topic(
        self, tenant_id: str, topic_id: int, data: TopicSuggestionUpdate
    ) -> TopicSuggestion:
        """Update a topic suggestion."""
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
        """Delete a topic suggestion."""
        topic = await self.get_topic(tenant_id, topic_id)
        await self.db.delete(topic)
        await self.db.flush()
        logger.info(
            "Topic gelöscht: {id} (Tenant: {tenant})",
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
        """Generate content from a topic suggestion."""
        from app.schemas.content import ContentGenerate
        from app.services.content import ContentService

        topic = await self.get_topic(tenant_id, topic_id)
        topic.status = "generating"
        await self.db.flush()

        content_service = ContentService(self.db)
        data = ContentGenerate(
            topic=topic.title,
            platform=platform,
            content_type=content_type,
            additional_instructions=topic.description,
        )

        piece = await content_service.generate_content(tenant_id, data, tenant_config)

        if topic.image_url and piece.media_urls is None:
            piece.media_urls = [topic.image_url]
        elif topic.image_url:
            piece.media_urls = [topic.image_url] + (piece.media_urls or [])

        topic.status = "generated"
        topic.content_piece_id = piece.id
        await self.db.flush()
        await self.db.refresh(topic)
        await self.db.refresh(piece)

        logger.info(
            "Content aus Topic generiert: topic={tid} piece={pid}",
            tid=topic_id,
            pid=piece.id,
        )
        return piece

    # --- Helpers ---

    @staticmethod
    def _matches_keywords(title: str, text: str, keywords: list[str]) -> bool:
        """Check if title or text contains any of the keywords."""
        combined = f"{title} {text}".lower()
        return any(kw in combined for kw in keywords)
