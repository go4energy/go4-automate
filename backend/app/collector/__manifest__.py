"""Collector module manifest."""

manifest = {
    "name": "collector",
    "label": "Collector",
    "version": "1.0.0",
    "description": "Quellen scannen, Findings sammeln, Topics generieren.",
    "icon": "M9.348 14.652a3.75 3.75 0 010-5.304m5.304 0a3.75 3.75 0 010 5.304m-7.425 2.122a6.75 6.75 0 010-9.546m9.546 0a6.75 6.75 0 010 9.546M5.106 18.894c-3.808-3.808-3.808-9.98 0-13.788m13.788 0c3.808 3.808 3.808 9.98 0 13.788M12 12h.008v.008H12V12zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z",
    "color": "#8B5CF6",
    "category": "marketing",
    "application": True,
    "depends": [],
    "has_frontend": True,
    "has_models": True,
    "has_config_schema": True,
    "routers": ["router"],
    "router_prefix": "/collector",
    "sidebar": {"group": "MARKETING", "order": 20},
    "frontend": {
        "base_route": "/collector",
        "routes": [
            # Tab routes
            {
                "path": "",
                "name": "collector",
                "view": "CollectorView",
                "meta": {
                    "title": "Collector",
                    "breadcrumb": {"label": "Collector"},
                    "tab": "sources",
                },
            },
            {
                "path": "sources",
                "name": "collector-sources",
                "view": "CollectorView",
                "meta": {
                    "title": "Quellen",
                    "breadcrumb": {"label": "Quellen", "parent": "collector"},
                    "tab": "sources",
                },
            },
            {
                "path": "findings",
                "name": "collector-findings",
                "view": "CollectorView",
                "meta": {
                    "title": "Findings",
                    "breadcrumb": {"label": "Findings", "parent": "collector"},
                    "tab": "findings",
                },
            },
            {
                "path": "prompts",
                "name": "collector-prompts",
                "view": "CollectorView",
                "meta": {
                    "title": "KI-Analyse",
                    "breadcrumb": {"label": "KI", "parent": "collector"},
                    "tab": "prompts",
                },
            },
            {
                "path": "topics",
                "name": "collector-topics",
                "view": "CollectorView",
                "meta": {
                    "title": "Themen",
                    "breadcrumb": {"label": "Themen", "parent": "collector"},
                    "tab": "topics",
                },
            },
            {
                "path": "einstellungen",
                "name": "collector-einstellungen",
                "view": "CollectorView",
                "meta": {
                    "title": "Einstellungen",
                    "breadcrumb": {"label": "Einstellungen", "parent": "collector"},
                    "tab": "einstellungen",
                },
            },
            # Detail/Edit routes
            {
                "path": "sources/new",
                "name": "collector-source-new",
                "view": "CollectorSourceEditView",
                "meta": {
                    "title": "Neue Quelle",
                    "breadcrumb": {"label": "Neu", "parent": "collector-sources"},
                },
            },
            {
                "path": "sources/:id",
                "name": "collector-source-edit",
                "view": "CollectorSourceEditView",
                "props": True,
                "meta": {
                    "title": "Quelle bearbeiten",
                    "breadcrumb": {"label": "Bearbeiten", "parent": "collector-sources"},
                },
            },
            {
                "path": "topics/new",
                "name": "collector-topic-new",
                "view": "CollectorTopicCreateView",
                "meta": {
                    "title": "Eigenes Thema",
                    "breadcrumb": {"label": "Neu", "parent": "collector-topics"},
                },
            },
            {
                "path": "topics/:id",
                "name": "collector-topic-detail",
                "view": "CollectorTopicDetailView",
                "props": True,
                "meta": {
                    "title": "Thema",
                    "breadcrumb": {"label": "Details", "parent": "collector-topics"},
                },
            },
        ],
    },
}
