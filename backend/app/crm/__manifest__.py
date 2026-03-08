"""CRM module manifest."""

manifest = {
    "name": "crm",
    "label": "CRM",
    "version": "2.0.0",
    "description": "Deals, Pipelines, Kontakte verwalten, Lead Scoring.",
    "icon": "M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5",
    "color": "#10B981",
    "category": "sales",
    "application": True,
    "depends": ["contacts"],
    "has_frontend": True,
    "has_models": True,
    "has_config_schema": True,
    "routers": ["router"],
    "router_prefix": "/crm",
    "sidebar": {"group": "SALES", "order": 20},
    "frontend": {
        "base_route": "/crm",
        "routes": [
            {
                "path": "",
                "name": "crm",
                "view": "CrmDealsView",
                "meta": {"title": "CRM"},
            },
            {
                "path": "deals/:id",
                "name": "crm-deal-detail",
                "view": "CrmDealDetailView",
                "meta": {"title": "Deal"},
            },
            {
                "path": "pipelines",
                "name": "crm-pipelines",
                "view": "CrmPipelinesView",
                "meta": {"title": "Pipelines"},
            },
            {
                "path": "tasks",
                "name": "crm-tasks",
                "view": "CrmTasksView",
                "meta": {"title": "Aufgaben"},
            },
            {
                "path": "calls",
                "name": "crm-calls",
                "view": "CrmCallsView",
                "meta": {"title": "Anrufe"},
            },
        ],
    },
}
