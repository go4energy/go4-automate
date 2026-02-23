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
            {
                "path": "",
                "name": "collector",
                "view": "CollectorView",
                "meta": {"title": "Collector"},
            },
            {
                "path": "sources/new",
                "name": "collector-source-new",
                "view": "CollectorSourceEditView",
                "meta": {"title": "Neue Quelle", "parent": "collector"},
            },
            {
                "path": "sources/:id",
                "name": "collector-source-edit",
                "view": "CollectorSourceEditView",
                "props": True,
                "meta": {"title": "Quelle bearbeiten", "parent": "collector"},
            },
            {
                "path": "topics/new",
                "name": "collector-topic-new",
                "view": "CollectorTopicCreateView",
                "meta": {"title": "Eigenes Thema", "parent": "collector"},
            },
            {
                "path": "topics/:id",
                "name": "collector-topic-detail",
                "view": "CollectorTopicDetailView",
                "props": True,
                "meta": {"title": "Thema", "parent": "collector"},
            },
        ],
    },
}
