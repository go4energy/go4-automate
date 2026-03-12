"""Campaigns module manifest."""

manifest = {
    "name": "campaigns",
    "label": "Meta Ads",
    "version": "1.0.0",
    "description": "Meta/Facebook Ads verwalten, Kampagnen schalten, Performance tracken.",
    "icon": "M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5M9 11.25v1.5M12 9v3.75m3-6v6.75",
    "color": "#0081FB",
    "category": "marketing",
    "application": True,
    "depends": [],
    "has_frontend": True,
    "has_models": True,
    "has_config_schema": True,
    "routers": ["router"],
    "router_prefix": "/campaigns",
    "sidebar": {"group": "MARKETING", "order": 40},
    "frontend": {
        "base_route": "/campaigns",
        "routes": [
            {
                "path": "",
                "name": "campaigns",
                "view": "CampaignsDashboardView",
                "meta": {"title": "Campaigns"},
            },
            {
                "path": ":id/config",
                "name": "campaigns-config",
                "view": "CampaignsConfigView",
                "props": True,
                "meta": {"title": "Kampagne konfigurieren", "parent": "campaigns"},
            },
        ],
    },
}
