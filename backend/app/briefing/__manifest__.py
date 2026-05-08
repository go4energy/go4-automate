"""Briefing module manifest."""

manifest = {
    "name": "briefing",
    "label": "Briefing",
    "version": "1.0.0",
    "description": "Internes Briefing: Quellen sammeln, Briefings generieren, Team informieren.",
    "icon": "M19.114 5.636a9 9 0 010 12.728M16.463 8.288a5.25 5.25 0 010 7.424M6.75 8.25l4.72-4.72a.75.75 0 011.28.53v15.88a.75.75 0 01-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.01 9.01 0 012.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75z",
    "color": "#0EA5E9",
    "category": "marketing",
    "application": True,
    "depends": [],
    "has_frontend": True,
    "has_models": True,
    "has_config_schema": True,
    "routers": ["router", "listener_router"],
    "router_prefix": "/briefing",
    "sidebar": {"group": "MARKETING", "order": 35},
    "frontend": {
        "base_route": "/briefing",
        "routes": [
            # Tab routes
            {
                "path": "",
                "name": "briefing",
                "view": "BriefingView",
                "meta": {
                    "title": "Briefing",
                    "breadcrumb": {"label": "Briefing"},
                    "tab": "sources",
                },
            },
            {
                "path": "sources",
                "name": "briefing-sources",
                "view": "BriefingView",
                "meta": {
                    "title": "Quellen",
                    "breadcrumb": {"label": "Quellen", "parent": "briefing"},
                    "tab": "sources",
                },
            },
            {
                "path": "personal",
                "name": "briefing-personal",
                "view": "BriefingView",
                "meta": {
                    "title": "Mein Briefing",
                    "breadcrumb": {"label": "Mein Briefing", "parent": "briefing"},
                    "tab": "personal",
                },
            },
            {
                "path": "findings",
                "name": "briefing-findings",
                "view": "BriefingView",
                "meta": {
                    "title": "Findings",
                    "breadcrumb": {"label": "Findings", "parent": "briefing"},
                    "tab": "findings",
                },
            },
            {
                "path": "channels",
                "name": "briefing-channels",
                "view": "BriefingView",
                "meta": {
                    "title": "Channels",
                    "breadcrumb": {"label": "Channels", "parent": "briefing"},
                    "tab": "channels",
                },
            },
            {
                "path": "speakers",
                "name": "briefing-speakers",
                "view": "BriefingView",
                "meta": {
                    "title": "Sprecher",
                    "breadcrumb": {"label": "Sprecher", "parent": "briefing"},
                    "tab": "speakers",
                },
            },
            {
                "path": "einstellungen",
                "name": "briefing-einstellungen",
                "view": "BriefingView",
                "meta": {
                    "title": "Einstellungen",
                    "breadcrumb": {"label": "Einstellungen", "parent": "briefing"},
                    "tab": "einstellungen",
                },
            },
            # Detail/Edit routes
            {
                "path": "channels/new",
                "name": "briefing-channel-new",
                "view": "BriefingChannelEditView",
                "meta": {
                    "title": "Neuer Channel",
                    "breadcrumb": {"label": "Neu", "parent": "briefing-channels"},
                },
            },
            {
                "path": "channels/:id",
                "name": "briefing-channel-detail",
                "view": "BriefingChannelDetailView",
                "props": True,
                "meta": {
                    "title": "Channel Detail",
                    "breadcrumb": {"label": "Details", "parent": "briefing-channels"},
                },
            },
            {
                "path": "channels/:id/edit",
                "name": "briefing-channel-edit",
                "view": "BriefingChannelEditView",
                "props": True,
                "meta": {
                    "title": "Channel bearbeiten",
                    "breadcrumb": {"label": "Bearbeiten", "parent": "briefing-channels"},
                },
            },
            {
                "path": "sources/new",
                "name": "briefing-source-new",
                "view": "BriefingSourceEditView",
                "meta": {
                    "title": "Neue Quelle",
                    "breadcrumb": {"label": "Neu", "parent": "briefing-sources"},
                },
            },
            {
                "path": "sources/:id/edit",
                "name": "briefing-source-edit",
                "view": "BriefingSourceEditView",
                "props": True,
                "meta": {
                    "title": "Quelle bearbeiten",
                    "breadcrumb": {"label": "Bearbeiten", "parent": "briefing-sources"},
                },
            },
        ],
    },
}
