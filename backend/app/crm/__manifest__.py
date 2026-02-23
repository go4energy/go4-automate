"""CRM module manifest."""

manifest = {
    "name": "crm",
    "label": "CRM",
    "version": "1.0.0",
    "description": "Kontakte verwalten, Lead Scoring, E-Mail Tracking.",
    "icon": "M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5",
    "color": "#10B981",
    "category": "marketing",
    "application": True,
    "depends": [],
    "has_frontend": True,
    "has_models": True,
    "has_config_schema": True,
    "routers": ["router"],
    "router_prefix": "/crm",
    "sidebar": {"group": "MARKETING", "order": 50},
    "frontend": {
        "base_route": "/crm",
        "routes": [
            {
                "path": "",
                "name": "crm",
                "view": "CrmView",
                "meta": {"title": "CRM"},
            },
        ],
    },
}
