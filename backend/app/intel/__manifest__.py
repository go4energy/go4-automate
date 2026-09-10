"""Intel module manifest — Marketing & Competitive Intelligence.

Periodically watches competitors, regulators and market segments via
configurable sources (web pages, RSS, structured APIs, job boards).
Detects meaningful changes via content-hash + semantic-embedding diff,
triages with claude-haiku-4-5, deep-reasons with claude-sonnet-4-6.

Outputs land in ``intel_briefing`` (own table). The ``briefing`` module
can consume them read-only.

Stack constraints:
- Embeddings via host-native Ollama (``bge-m3:latest``, 1024d) on
  port 11434. Ollama is shared infrastructure (systemd, OLLAMA_HOST=
  0.0.0.0) — multi-tenant by design. Optional OpenAI fallback when
  ``settings.intel_openai_fallback_enabled`` is True.
- Vector storage in pgvector (Postgres extension), NOT qdrant.
- Playwright runs in the backend container with bundled chromium, NEVER
  mounts ``/projects/ragflow/chrome-linux64``.
"""

manifest = {
    "name": "intel",
    "label": "Intel",
    "version": "1.0.0",
    "description": "Marketing & Competitive Intelligence — Watch-Targets, Change-Detection, Briefings.",
    # Radar icon
    "icon": "M12 2v4M12 18v4M2 12h4M18 12h4M5 5l3 3M16 16l3 3M5 19l3-3M16 8l3-3",
    "color": "#0EA5E9",
    "category": "marketing",
    "application": True,
    "depends": [],
    "has_frontend": True,
    "has_models": True,
    "has_config_schema": False,
    "routers": ["router"],
    "router_prefix": "/intel",
    "sidebar": {"group": "MARKETING", "order": 25},
    "frontend": {
        "base_route": "/intel",
        "routes": [
            {
                "path": "",
                "name": "intel",
                "view": "IntelDashboardView",
                "meta": {
                    "title": "Intel",
                    "breadcrumb": {"label": "Intel"},
                    "tab": "dashboard",
                },
            },
            {
                "path": "targets",
                "name": "intel-targets",
                "view": "IntelTargetsView",
                "meta": {
                    "title": "Watch-Targets",
                    "breadcrumb": {"label": "Targets", "parent": "intel"},
                    "tab": "targets",
                },
            },
            {
                "path": "targets/:id",
                "name": "intel-target-detail",
                "view": "IntelTargetDetailView",
                "props": True,
                "meta": {
                    "title": "Target",
                    "breadcrumb": {"label": "Details", "parent": "intel-targets"},
                },
            },
            {
                "path": "briefings",
                "name": "intel-briefings",
                "view": "IntelBriefingsView",
                "meta": {
                    "title": "Briefings",
                    "breadcrumb": {"label": "Briefings", "parent": "intel"},
                    "tab": "briefings",
                },
            },
            {
                "path": "briefings/:id",
                "name": "intel-briefing-detail",
                "view": "IntelBriefingDetailView",
                "props": True,
                "meta": {
                    "title": "Briefing",
                    "breadcrumb": {"label": "Detail", "parent": "intel-briefings"},
                },
            },
            {
                "path": "events",
                "name": "intel-events",
                "view": "IntelEventsView",
                "meta": {
                    "title": "Change-Events",
                    "breadcrumb": {"label": "Events", "parent": "intel"},
                    "tab": "events",
                },
            },
        ],
    },
}
