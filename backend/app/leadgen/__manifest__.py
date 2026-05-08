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
            # Module entry = campaign list (no top-level tabs anymore).
            {
                "path": "",
                "name": "leadgen",
                "view": "LeadgenView",
                "meta": {
                    "title": "Leadgen",
                    "breadcrumb": {"label": "Leadgen"},
                },
            },
            {
                "path": "einstellungen",
                "name": "leadgen-einstellungen",
                "view": "ModuleSettingsPageView",
                "meta": {
                    "title": "Leadgen — Einstellungen",
                    "moduleName": "leadgen",
                    "breadcrumb": {"label": "Einstellungen", "parent": "leadgen"},
                },
            },
            {
                "path": "campaigns/new",
                "name": "leadgen-campaign-new",
                "view": "LeadgenCampaignEditView",
                "meta": {
                    "title": "Neue Kampagne",
                    "breadcrumb": {"label": "Neu", "parent": "leadgen"},
                },
            },
            # Campaign detail with sub-tabs (details + places).
            {
                "path": "campaigns/:id",
                "name": "leadgen-campaign-detail",
                "view": "LeadgenCampaignDetailView",
                "props": True,
                "meta": {
                    "title": "Kampagne",
                    "breadcrumb": {"label": "Details", "parent": "leadgen"},
                    "tab": "details",
                },
            },
            {
                "path": "campaigns/:id/details",
                "name": "leadgen-campaign-details",
                "view": "LeadgenCampaignDetailView",
                "props": True,
                "meta": {
                    "title": "Details",
                    "breadcrumb": {"label": "Details", "parent": "leadgen"},
                    "tab": "details",
                },
            },
            {
                "path": "campaigns/:id/places",
                "name": "leadgen-campaign-places",
                "view": "LeadgenCampaignDetailView",
                "props": True,
                "meta": {
                    "title": "Prospects",
                    "breadcrumb": {"label": "Prospects", "parent": "leadgen"},
                    "tab": "places",
                },
            },
            {
                "path": "campaigns/:id/map",
                "name": "leadgen-campaign-map",
                "view": "LeadgenCampaignDetailView",
                "props": True,
                "meta": {
                    "title": "Karte",
                    "breadcrumb": {"label": "Karte", "parent": "leadgen-campaign-detail"},
                    "tab": "map",
                },
            },
            {
                "path": "campaigns/:id/edit",
                "name": "leadgen-campaign-edit",
                "view": "LeadgenCampaignEditView",
                "props": True,
                "meta": {
                    "title": "Kampagne bearbeiten",
                    "breadcrumb": {"label": "Bearbeiten", "parent": "leadgen-campaign-detail"},
                },
            },
            # Place detail keeps its standalone path; breadcrumb walks back to
            # the campaign's places sub-tab.
            {
                "path": "campaigns/:campaignId/places/:id",
                "name": "leadgen-place-detail",
                "view": "LeadgenPlaceDetailView",
                "props": True,
                "meta": {
                    "title": "Prospect",
                    "breadcrumb": {
                        "label": "Prospect-Details",
                        "parent": "leadgen-campaign-places",
                    },
                },
            },
            # Legacy direct prospect URL (kept so old links don't break).
            {
                "path": "places/:id",
                "name": "leadgen-place-detail-legacy",
                "view": "LeadgenPlaceDetailView",
                "props": True,
                "meta": {
                    "title": "Prospect",
                    "breadcrumb": {"label": "Prospect-Details", "parent": "leadgen"},
                },
            },
        ],
    },
}
