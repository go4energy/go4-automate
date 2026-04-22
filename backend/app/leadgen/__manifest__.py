"""Leadgen module manifest."""

manifest = {
    "name": "leadgen",
    "label": "Leadgen",
    "version": "0.1.0",
    "description": "B2B Lead-Discovery: Google Places Scraping, Impressum-/LLM-Enrichment, Handoff an Engagement.",
    "icon": "M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z",
    "color": "#F59E0B",
    "category": "sales",
    "application": True,
    "depends": ["contacts", "engagement"],
    "has_frontend": True,
    "has_models": True,
    "has_config_schema": True,
    "routers": ["router"],
    "router_prefix": "/leadgen",
    "sidebar": {"group": "SALES", "order": 20},
    "frontend": {
        "base_route": "/leadgen",
        "routes": [
            {
                "path": "",
                "name": "leadgen",
                "view": "LeadgenView",
                "meta": {
                    "title": "Leadgen",
                    "breadcrumb": {"label": "Leadgen"},
                    "tab": "dashboard",
                },
            },
            {
                "path": "dashboard",
                "name": "leadgen-dashboard",
                "view": "LeadgenView",
                "meta": {
                    "title": "Dashboard",
                    "breadcrumb": {"label": "Dashboard", "parent": "leadgen"},
                    "tab": "dashboard",
                },
            },
            {
                "path": "campaigns",
                "name": "leadgen-campaigns",
                "view": "LeadgenView",
                "meta": {
                    "title": "Kampagnen",
                    "breadcrumb": {"label": "Kampagnen", "parent": "leadgen"},
                    "tab": "campaigns",
                },
            },
            {
                "path": "campaigns/new",
                "name": "leadgen-campaign-new",
                "view": "LeadgenCampaignEditView",
                "meta": {
                    "title": "Neue Kampagne",
                    "breadcrumb": {"label": "Neu", "parent": "leadgen-campaigns"},
                },
            },
            {
                "path": "campaigns/:id",
                "name": "leadgen-campaign-detail",
                "view": "LeadgenCampaignDetailView",
                "props": True,
                "meta": {
                    "title": "Kampagne",
                    "breadcrumb": {"label": "Details", "parent": "leadgen-campaigns"},
                },
            },
            {
                "path": "campaigns/:id/edit",
                "name": "leadgen-campaign-edit",
                "view": "LeadgenCampaignEditView",
                "props": True,
                "meta": {
                    "title": "Kampagne bearbeiten",
                    "breadcrumb": {"label": "Bearbeiten", "parent": "leadgen-campaigns"},
                },
            },
            {
                "path": "places",
                "name": "leadgen-places",
                "view": "LeadgenView",
                "meta": {
                    "title": "Places",
                    "breadcrumb": {"label": "Places", "parent": "leadgen"},
                    "tab": "places",
                },
            },
            {
                "path": "places/:id",
                "name": "leadgen-place-detail",
                "view": "LeadgenPlaceDetailView",
                "props": True,
                "meta": {
                    "title": "Place",
                    "breadcrumb": {"label": "Details", "parent": "leadgen-places"},
                },
            },
            {
                "path": "runs",
                "name": "leadgen-runs",
                "view": "LeadgenView",
                "meta": {
                    "title": "Runs",
                    "breadcrumb": {"label": "Runs", "parent": "leadgen"},
                    "tab": "runs",
                },
            },
            {
                "path": "settings",
                "name": "leadgen-settings",
                "view": "LeadgenView",
                "meta": {
                    "title": "Einstellungen",
                    "breadcrumb": {"label": "Einstellungen", "parent": "leadgen"},
                    "tab": "settings",
                },
            },
        ],
    },
}
