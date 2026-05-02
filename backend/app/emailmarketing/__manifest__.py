"""Email Marketing module manifest."""

manifest = {
    "name": "emailmarketing",
    "label": "E-Mail Marketing",
    "version": "1.0.0",
    "description": "E-Mail-Kampagnen, Sequenzen und Tracking mit Provider-Abstraktion.",
    "icon": "M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75",
    "color": "#059669",
    "category": "marketing",
    "application": True,
    "depends": ["contacts"],
    "has_frontend": True,
    "has_models": True,
    "has_config_schema": True,
    "routers": [
        "router",
        "tracking_router",
        "webhooks_router",
        "asset_router",
        "ai_chat_router",
    ],
    "router_prefix": "/emailmarketing",
    "sidebar": {"group": "MARKETING", "order": 45},
    "frontend": {
        "base_route": "/emailmarketing",
        "routes": [
            # Tab routes
            {
                "path": "",
                "name": "emailmarketing",
                "view": "EmailMarketingView",
                "meta": {
                    "title": "E-Mail Marketing",
                    "breadcrumb": {"label": "E-Mail Marketing"},
                    "tab": "sequences",
                },
            },
            {
                "path": "templates",
                "name": "emailmarketing-templates",
                "view": "EmailMarketingView",
                "meta": {
                    "title": "Vorlagen",
                    "breadcrumb": {"label": "Vorlagen", "parent": "emailmarketing"},
                    "tab": "templates",
                },
            },
            {
                "path": "sequences",
                "name": "emailmarketing-sequences",
                "view": "EmailMarketingView",
                "meta": {
                    "title": "Sequenzen",
                    "breadcrumb": {"label": "Sequenzen", "parent": "emailmarketing"},
                    "tab": "sequences",
                },
            },
            {
                "path": "providers",
                "name": "emailmarketing-providers",
                "view": "EmailMarketingView",
                "meta": {
                    "title": "Provider",
                    "breadcrumb": {"label": "Provider", "parent": "emailmarketing"},
                    "tab": "providers",
                },
            },
            {
                "path": "freigabe",
                "name": "emailmarketing-freigabe",
                "view": "EmailMarketingView",
                "meta": {
                    "title": "Freigabe",
                    "breadcrumb": {"label": "Freigabe", "parent": "emailmarketing"},
                    "tab": "freigabe",
                },
            },
            # Detail/Edit routes
            {
                "path": "campaigns/:id",
                "name": "emailmarketing-campaign-detail",
                "view": "EmailCampaignDetailView",
                "props": True,
                "meta": {
                    "title": "Kampagne",
                    "breadcrumb": {"label": "Details", "parent": "emailmarketing"},
                },
            },
            {
                "path": "campaigns/:id/edit",
                "name": "emailmarketing-campaign-edit",
                "view": "EmailCampaignEditView",
                "props": True,
                "meta": {
                    "title": "Kampagne bearbeiten",
                    "breadcrumb": {"label": "Bearbeiten", "parent": "emailmarketing"},
                },
            },
            {
                "path": "campaigns/new",
                "name": "emailmarketing-campaign-new",
                "view": "EmailCampaignEditView",
                "meta": {
                    "title": "Neue Kampagne",
                    "breadcrumb": {"label": "Neu", "parent": "emailmarketing"},
                },
            },
            {
                "path": "templates/:id/edit",
                "name": "emailmarketing-template-edit",
                "view": "EmailTemplateEditView",
                "props": True,
                "meta": {
                    "title": "Vorlage bearbeiten",
                    "breadcrumb": {"label": "Bearbeiten", "parent": "emailmarketing-templates"},
                },
            },
            {
                "path": "templates/new",
                "name": "emailmarketing-template-new",
                "view": "EmailTemplateEditView",
                "meta": {
                    "title": "Neue Vorlage",
                    "breadcrumb": {"label": "Neu", "parent": "emailmarketing-templates"},
                },
            },
            {
                "path": "sequences/:id",
                "name": "emailmarketing-sequence-detail",
                "view": "EmailSequenceDetailView",
                "props": True,
                "meta": {
                    "title": "Sequenz",
                    "breadcrumb": {"label": "Details", "parent": "emailmarketing-sequences"},
                },
            },
            {
                "path": "sequences/:id/edit",
                "name": "emailmarketing-sequence-edit",
                "view": "EmailSequenceEditView",
                "props": True,
                "meta": {
                    "title": "Sequenz bearbeiten",
                    "breadcrumb": {"label": "Bearbeiten", "parent": "emailmarketing-sequences"},
                },
            },
            {
                "path": "sequences/new",
                "name": "emailmarketing-sequence-new",
                "view": "EmailSequenceEditView",
                "meta": {
                    "title": "Neue Sequenz",
                    "breadcrumb": {"label": "Neu", "parent": "emailmarketing-sequences"},
                },
            },
            {
                "path": "providers/:id/edit",
                "name": "emailmarketing-provider-edit",
                "view": "EmailProviderEditView",
                "props": True,
                "meta": {
                    "title": "Provider bearbeiten",
                    "breadcrumb": {"label": "Bearbeiten", "parent": "emailmarketing-providers"},
                },
            },
            {
                "path": "providers/new",
                "name": "emailmarketing-provider-new",
                "view": "EmailProviderEditView",
                "meta": {
                    "title": "Neuer Provider",
                    "breadcrumb": {"label": "Neu", "parent": "emailmarketing-providers"},
                },
            },
        ],
    },
}
