"""Assistant module manifest."""

manifest = {
    "name": "assistant",
    "label": "Assistant",
    "version": "1.0.0",
    "description": "Persoenlicher KI-Assistent: Multi-Account Mail/Kalender, Briefing, Voice, Regeln.",
    "icon": "M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z",
    "color": "#8B5CF6",
    "category": "productivity",
    "application": True,
    "depends": [],
    "has_frontend": True,
    "has_models": True,
    "has_config_schema": True,
    "routers": ["router"],
    "router_prefix": "/assistant",
    "sidebar": {"group": "TOOLS", "order": 10},
    "frontend": {
        "base_route": "/assistant",
        "routes": [
            {
                "path": "",
                "name": "assistant",
                "view": "AssistantView",
                "meta": {
                    "title": "Assistant",
                    "breadcrumb": {"label": "Assistant"},
                    "tab": "dashboard",
                },
            },
            {
                "path": "dashboard",
                "name": "assistant-dashboard",
                "view": "AssistantView",
                "meta": {
                    "title": "Mein Assistant",
                    "breadcrumb": {"label": "Dashboard", "parent": "assistant"},
                    "tab": "dashboard",
                },
            },
            {
                "path": "accounts",
                "name": "assistant-accounts",
                "view": "AssistantView",
                "meta": {
                    "title": "Konten",
                    "breadcrumb": {"label": "Konten", "parent": "assistant"},
                    "tab": "accounts",
                },
            },
            {
                "path": "rules",
                "name": "assistant-rules",
                "view": "AssistantView",
                "meta": {
                    "title": "Regeln",
                    "breadcrumb": {"label": "Regeln", "parent": "assistant"},
                    "tab": "rules",
                },
            },
            {
                "path": "activity",
                "name": "assistant-activity",
                "view": "AssistantView",
                "meta": {
                    "title": "Aktivitaet",
                    "breadcrumb": {"label": "Aktivitaet", "parent": "assistant"},
                    "tab": "activity",
                },
            },
            {
                "path": "approvals",
                "name": "assistant-approvals",
                "view": "AssistantView",
                "meta": {
                    "title": "Freigaben",
                    "breadcrumb": {"label": "Freigaben", "parent": "assistant"},
                    "tab": "approvals",
                },
            },
            {
                "path": "settings",
                "name": "assistant-settings",
                "view": "AssistantView",
                "meta": {
                    "title": "Einstellungen",
                    "breadcrumb": {"label": "Einstellungen", "parent": "assistant"},
                    "tab": "settings",
                },
            },
        ],
    },
}
