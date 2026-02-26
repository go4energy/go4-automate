"""Funnels module manifest."""

manifest = {
    "name": "funnels",
    "label": "Funnels",
    "version": "1.0.0",
    "description": "Prospecting & Lead-Generierung vor dem CRM. Funnels, Stages, Prospects.",
    "icon": "M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z",
    "color": "#8B5CF6",
    "category": "sales",
    "application": True,
    "depends": ["contacts", "crm"],
    "has_frontend": True,
    "has_models": True,
    "has_config_schema": True,
    "routers": ["router", "n8n_router"],
    "router_prefix": "/funnels",
    "sidebar": {"group": "SALES", "order": 15},
    "frontend": {
        "base_route": "/funnels",
        "routes": [
            {
                "path": "",
                "name": "funnels",
                "view": "FunnelsView",
                "meta": {"title": "Funnels"},
            },
            {
                "path": ":id",
                "name": "funnel-detail",
                "view": "FunnelDetailView",
                "props": True,
                "meta": {"title": "Funnel"},
            },
            {
                "path": ":id/kanban",
                "name": "funnel-kanban",
                "view": "FunnelKanbanView",
                "props": True,
                "meta": {"title": "Kanban"},
            },
            {
                "path": "prospects/:id",
                "name": "prospect-detail",
                "view": "ProspectDetailView",
                "props": True,
                "meta": {"title": "Prospect"},
            },
        ],
    },
}
