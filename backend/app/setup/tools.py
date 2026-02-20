"""Setup wizard tools - Anthropic-compatible tool definitions + executor."""

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.collector.service import CollectorService
from app.config import settings
from app.services.tenant import TenantService

# Anthropic tool definitions
SETUP_TOOLS = [
    {
        "name": "get_current_config",
        "description": "Liest die aktuelle Tenant-Konfiguration. Gibt alle gesetzten Parameter als Key-Value-Paare zurueck.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "update_tenant_config",
        "description": "Aktualisiert Tenant-Konfigurationsparameter. Kann mehrere Schluessel gleichzeitig setzen. Aendert sowohl die DB als auch die Tenant-Env-Datei.",
        "input_schema": {
            "type": "object",
            "properties": {
                "updates": {
                    "type": "object",
                    "description": 'Key-Value-Paare der zu aendernden Parameter, z.B. {"COMPANY_NAME": "Firma GmbH", "TENANT_INDUSTRY": "Energie"}',
                },
            },
            "required": ["updates"],
        },
    },
    {
        "name": "list_collector_sources",
        "description": "Listet alle Collector-Quellen des Tenants auf. Zeigt Name, Typ, URL, Keywords, Kategorien und Status.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "create_collector_source",
        "description": "Legt eine neue Collector-Quelle an (RSS-Feed, Website, Web-Suche oder Inbox).",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name der Quelle, z.B. 'PV Magazine RSS'",
                },
                "url": {
                    "type": "string",
                    "description": "URL der Quelle (RSS-Feed-URL oder Website-URL). Bei websearch kann dies leer sein.",
                },
                "source_type": {
                    "type": "string",
                    "enum": ["rss", "website", "websearch", "inbox"],
                    "description": "Art der Quelle",
                },
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter-Keywords fuer die Quelle",
                },
                "fetch_interval_hours": {
                    "type": "integer",
                    "description": "Abruf-Intervall in Stunden",
                    "default": 24,
                },
                "categories": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Kategorien fuer die Quelle, z.B. ['social_media', 'podcast']",
                    "default": [],
                },
            },
            "required": ["name", "source_type"],
        },
    },
    {
        "name": "delete_collector_source",
        "description": "Loescht eine Collector-Quelle anhand ihrer ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source_id": {
                    "type": "integer",
                    "description": "ID der zu loeschenden Quelle",
                },
            },
            "required": ["source_id"],
        },
    },
    {
        "name": "update_creator_config",
        "description": "Aktualisiert Creator-Konfiguration (Plattformen, Posts/Woche, Themes, etc.).",
        "input_schema": {
            "type": "object",
            "properties": {
                "updates": {
                    "type": "object",
                    "description": 'Key-Value-Paare, z.B. {"CONTENT_PLATFORMS": "linkedin,facebook", "POSTS_PER_WEEK": "3"}',
                },
            },
            "required": ["updates"],
        },
    },
    {
        "name": "update_distributor_config",
        "description": "Aktualisiert Distributor-Konfiguration (Budget, CPL, Weather-Boost, etc.).",
        "input_schema": {
            "type": "object",
            "properties": {
                "updates": {
                    "type": "object",
                    "description": 'Key-Value-Paare, z.B. {"ADS_MONTHLY_BUDGET": "500", "ADS_TARGET_CPL": "15"}',
                },
            },
            "required": ["updates"],
        },
    },
    {
        "name": "check_integration_status",
        "description": "Prueft welche externen Integrationen konfiguriert sind (Meta API, SMTP, n8n, etc.).",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "list_prompts",
        "description": "Listet alle verfuegbaren Prompt-Templates fuer den Tenant auf.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_setup_progress",
        "description": "Zeigt den aktuellen Setup-Fortschritt: welche Module konfiguriert sind und was noch fehlt.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


class ToolExecutor:
    """Executes setup tools by routing to the appropriate service."""

    def __init__(self, db: AsyncSession, tenant_id: str, tenant_config: dict) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self.tenant_config = tenant_config

    async def execute(self, tool_name: str, tool_input: dict) -> dict:
        """Route tool call to the appropriate handler."""
        handlers = {
            "get_current_config": self._get_current_config,
            "update_tenant_config": self._update_tenant_config,
            "list_collector_sources": self._list_collector_sources,
            "create_collector_source": self._create_collector_source,
            "delete_collector_source": self._delete_collector_source,
            "update_creator_config": self._update_creator_config,
            "update_distributor_config": self._update_distributor_config,
            "check_integration_status": self._check_integration_status,
            "list_prompts": self._list_prompts,
            "get_setup_progress": self._get_setup_progress,
        }
        handler = handlers.get(tool_name)
        if not handler:
            return {"error": f"Unbekanntes Tool: {tool_name}"}

        try:
            return await handler(tool_input)
        except Exception as e:
            logger.exception("Tool-Fehler: {tool} - {err}", tool=tool_name, err=str(e))
            return {"error": str(e)}

    async def _get_current_config(self, _input: dict) -> dict:
        """Return current tenant config (redacting secrets)."""
        config = dict(self.tenant_config)
        # Redact sensitive values
        secret_keys = {
            "META_SYSTEM_USER_TOKEN",
            "ANTHROPIC_API_KEY",
            "OPENAI_API_KEY",
            "SMTP_PASSWORD",
            "N8N_API_KEY",
            "SERPER_API_KEY",
            "OPENWEATHER_API_KEY",
            "SECRET_KEY",
            "BACKEND_SECRET",
            "N8N_BASIC_AUTH_PASSWORD",
        }
        for key in secret_keys:
            if config.get(key):
                config[key] = "***configured***"
        return {"config": config}

    async def _update_tenant_config(self, tool_input: dict) -> dict:
        """Update tenant config in DB and env file."""
        updates = tool_input.get("updates", {})
        if not updates:
            return {"error": "Keine Updates angegeben"}

        service = TenantService(self.db)
        tenant = await service.get_by_id(self.tenant_id)

        # Update DB config
        current = dict(tenant.config or {})
        current.update(updates)
        tenant.config = current
        await self.db.flush()

        # Update env file
        self._update_env_file(updates)

        # Update local cache
        self.tenant_config.update(updates)

        # Clear tenant config cache
        TenantService._config_cache.pop(self.tenant_id, None)

        logger.info(
            "Tenant-Config aktualisiert: {keys} (Tenant: {tenant})",
            keys=list(updates.keys()),
            tenant=self.tenant_id,
        )
        return {"updated": list(updates.keys()), "success": True}

    def _update_env_file(self, updates: dict) -> None:
        """Write updated values to tenant env file."""
        from pathlib import Path

        env_path = Path(settings.tenant_config_dir) / f"{self.tenant_id}.env"
        env_path.parent.mkdir(parents=True, exist_ok=True)

        # Read existing
        existing = {}
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    existing[key.strip()] = value.strip()

        # Merge
        existing.update(updates)

        # Write back
        lines = [f"{k}={v}" for k, v in sorted(existing.items())]
        env_path.write_text("\n".join(lines) + "\n")

    async def _list_collector_sources(self, _input: dict) -> dict:
        """List all collector sources."""
        service = CollectorService(self.db)
        sources = await service.list_sources(self.tenant_id)
        return {
            "sources": [
                {
                    "id": s.id,
                    "name": s.name,
                    "url": s.url,
                    "source_type": s.source_type,
                    "keywords": s.keywords or [],
                    "categories": s.categories or [],
                    "active": s.active,
                    "fetch_interval_hours": s.fetch_interval_hours,
                }
                for s in sources
            ],
            "count": len(sources),
        }

    async def _create_collector_source(self, tool_input: dict) -> dict:
        """Create a new collector source."""
        from app.collector.schemas import CollectorSourceCreate

        data = CollectorSourceCreate(
            name=tool_input["name"],
            url=tool_input.get("url", ""),
            source_type=tool_input["source_type"],
            keywords=tool_input.get("keywords", []),
            fetch_interval_hours=tool_input.get("fetch_interval_hours", 24),
            categories=tool_input.get("categories", []),
        )
        service = CollectorService(self.db)
        source = await service.create_source(self.tenant_id, data)
        return {
            "id": source.id,
            "name": source.name,
            "source_type": source.source_type,
            "success": True,
        }

    async def _delete_collector_source(self, tool_input: dict) -> dict:
        """Delete a collector source."""
        service = CollectorService(self.db)
        source_id = tool_input["source_id"]
        await service.delete_source(self.tenant_id, source_id)
        return {"deleted": source_id, "success": True}

    async def _update_creator_config(self, tool_input: dict) -> dict:
        """Update creator config (delegates to update_tenant_config)."""
        return await self._update_tenant_config(tool_input)

    async def _update_distributor_config(self, tool_input: dict) -> dict:
        """Update distributor config (delegates to update_tenant_config)."""
        return await self._update_tenant_config(tool_input)

    async def _check_integration_status(self, _input: dict) -> dict:
        """Check which integrations are configured."""
        config = self.tenant_config

        def is_set(key: str) -> bool:
            val = config.get(key, "") or getattr(settings, key.lower(), "")
            return bool(val and val.strip())

        return {
            "integrations": {
                "meta_publishing": {
                    "configured": is_set("META_SYSTEM_USER_TOKEN")
                    and is_set("META_PAGE_ID"),
                    "details": {
                        "token": is_set("META_SYSTEM_USER_TOKEN"),
                        "page_id": is_set("META_PAGE_ID"),
                        "instagram_id": is_set("META_INSTAGRAM_BUSINESS_ID"),
                    },
                },
                "meta_ads": {
                    "configured": is_set("META_AD_ACCOUNT_ID"),
                    "details": {
                        "ad_account_id": is_set("META_AD_ACCOUNT_ID"),
                        "pixel_id": is_set("META_PIXEL_ID"),
                    },
                },
                "smtp": {
                    "configured": is_set("SMTP_HOST") and is_set("SMTP_USER"),
                    "details": {
                        "host": is_set("SMTP_HOST"),
                        "user": is_set("SMTP_USER"),
                    },
                },
                "openweather": {
                    "configured": is_set("OPENWEATHER_API_KEY"),
                },
                "serper": {
                    "configured": is_set("SERPER_API_KEY"),
                },
                "n8n": {
                    "configured": is_set("N8N_URL"),
                    "details": {
                        "url": config.get("N8N_URL", "") or settings.n8n_url,
                    },
                },
            }
        }

    async def _list_prompts(self, _input: dict) -> dict:
        """List available prompt templates."""
        from sqlalchemy import select

        from app.models.prompt import Prompt

        result = await self.db.execute(
            select(Prompt)
            .where(Prompt.tenant_id == self.tenant_id)
            .order_by(Prompt.slug)
        )
        prompts = result.scalars().all()
        return {
            "prompts": [
                {
                    "id": p.id,
                    "slug": p.slug,
                    "name": p.name,
                    "category": p.category,
                    "version": p.version,
                }
                for p in prompts
            ],
            "count": len(prompts),
        }

    async def _get_setup_progress(self, _input: dict) -> dict:
        """Analyze setup progress across all modules."""
        config = self.tenant_config

        # Tenant basics
        tenant_keys = ["COMPANY_NAME", "TENANT_INDUSTRY", "TARGET_AUDIENCE"]
        tenant_set = sum(1 for k in tenant_keys if config.get(k))

        # Collector sources
        service = CollectorService(self.db)
        sources = await service.list_sources(self.tenant_id, active=True)

        # Creator config
        creator_keys = ["CONTENT_PLATFORMS", "POSTS_PER_WEEK", "CONTENT_THEMES"]
        creator_set = sum(1 for k in creator_keys if config.get(k))

        # Distributor config
        distributor_keys = ["ADS_MONTHLY_BUDGET", "ADS_TARGET_CPL"]
        distributor_set = sum(1 for k in distributor_keys if config.get(k))

        # Integrations
        def is_set(key: str) -> bool:
            val = config.get(key, "") or getattr(settings, key.lower(), "")
            return bool(val and val.strip())

        integrations_configured = sum(
            [
                is_set("META_SYSTEM_USER_TOKEN") and is_set("META_PAGE_ID"),
                is_set("SMTP_HOST"),
                is_set("SERPER_API_KEY"),
                is_set("OPENWEATHER_API_KEY"),
            ]
        )

        return {
            "modules": {
                "tenant": {
                    "label": "Unternehmen",
                    "configured": tenant_set >= 2,
                    "details": f"{tenant_set}/{len(tenant_keys)} Felder",
                },
                "collector": {
                    "label": "Collector",
                    "configured": len(sources) > 0,
                    "details": f"{len(sources)} Quellen",
                },
                "creator": {
                    "label": "Creator",
                    "configured": creator_set >= 2,
                    "details": f"{creator_set}/{len(creator_keys)} Felder",
                },
                "distributor": {
                    "label": "Distributor",
                    "configured": distributor_set >= 1,
                    "details": f"{distributor_set}/{len(distributor_keys)} Felder",
                },
                "integrations": {
                    "label": "Integrationen",
                    "configured": integrations_configured > 0,
                    "details": f"{integrations_configured}/4 Dienste",
                },
            }
        }
