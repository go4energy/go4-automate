"""Distributor module manifest."""

manifest = {
    "name": "distributor",
    "label": "Distributor",
    "version": "1.0.0",
    "description": "Kampagnen verwalten, Ads schalten, Performance tracken.",
    "icon": "M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5m.75-9l3-3 2.148 2.148A12.061 12.061 0 0116.5 7.605",
    "color": "#F59E0B",
    "category": "marketing",
    "application": True,
    "depends": [],
    "has_frontend": True,
    "has_models": True,
    "has_config_schema": True,
    "routers": ["router"],
    "router_prefix": "/distributor",
    "sidebar": {"group": "MARKETING", "order": 40},
    "frontend": {
        "base_route": "/distributor",
        "routes": [
            {
                "path": "",
                "name": "distributor",
                "view": "DistributorDashboardView",
                "meta": {"title": "Distributor"},
            },
            {
                "path": "campaigns/:id/config",
                "name": "distributor-campaign-config",
                "view": "DistributorCampaignConfigView",
                "props": True,
                "meta": {"title": "Kampagne konfigurieren", "parent": "distributor"},
            },
        ],
    },
}
