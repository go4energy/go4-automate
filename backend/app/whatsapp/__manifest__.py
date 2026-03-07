"""WhatsApp Business module manifest."""

manifest = {
    "name": "whatsapp",
    "label": "WhatsApp",
    "version": "1.0.0",
    "description": "WhatsApp Business Messaging via Meta Cloud API",
    "icon": "M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z",
    "color": "#25D366",
    "category": "communication",
    "application": True,
    "depends": ["contacts"],
    "has_frontend": True,
    "has_models": True,
    "has_config_schema": True,
    "routers": ["router", "webhooks_router"],
    "router_prefix": "/whatsapp",
    "sidebar": {"group": "KOMMUNIKATION", "order": 35},
    "frontend": {
        "base_route": "/whatsapp",
        "routes": [
            # Default route
            {
                "path": "",
                "name": "whatsapp",
                "view": "WhatsAppView",
                "meta": {
                    "title": "WhatsApp",
                    "breadcrumb": {"label": "WhatsApp"},
                    "tab": "inbox",
                },
            },
            # Tab routes
            {
                "path": "inbox",
                "name": "whatsapp-inbox",
                "view": "WhatsAppView",
                "meta": {
                    "title": "Inbox",
                    "breadcrumb": {"label": "Inbox", "parent": "whatsapp"},
                    "tab": "inbox",
                },
            },
            {
                "path": "campaigns",
                "name": "whatsapp-campaigns",
                "view": "WhatsAppView",
                "meta": {
                    "title": "Kampagnen",
                    "breadcrumb": {"label": "Kampagnen", "parent": "whatsapp"},
                    "tab": "campaigns",
                },
            },
            {
                "path": "templates",
                "name": "whatsapp-templates",
                "view": "WhatsAppView",
                "meta": {
                    "title": "Templates",
                    "breadcrumb": {"label": "Templates", "parent": "whatsapp"},
                    "tab": "templates",
                },
            },
            {
                "path": "accounts",
                "name": "whatsapp-accounts",
                "view": "WhatsAppView",
                "meta": {
                    "title": "Accounts",
                    "breadcrumb": {"label": "Accounts", "parent": "whatsapp"},
                    "tab": "accounts",
                },
            },
            {
                "path": "freigabe",
                "name": "whatsapp-freigabe",
                "view": "WhatsAppView",
                "meta": {
                    "title": "Freigabe",
                    "breadcrumb": {"label": "Freigabe", "parent": "whatsapp"},
                    "tab": "freigabe",
                },
            },
            # Detail/Edit routes - Conversations
            {
                "path": "conversations/:id",
                "name": "whatsapp-conversation",
                "view": "WhatsAppConversationView",
                "props": True,
                "meta": {
                    "title": "Conversation",
                    "breadcrumb": {"label": "Conversation", "parent": "whatsapp-inbox"},
                },
            },
            # Detail/Edit routes - Campaigns
            {
                "path": "campaigns/:id",
                "name": "whatsapp-campaign-detail",
                "view": "WhatsAppCampaignDetailView",
                "props": True,
                "meta": {
                    "title": "Kampagne",
                    "breadcrumb": {"label": "Details", "parent": "whatsapp-campaigns"},
                },
            },
            {
                "path": "campaigns/:id/edit",
                "name": "whatsapp-campaign-edit",
                "view": "WhatsAppCampaignEditView",
                "props": True,
                "meta": {
                    "title": "Kampagne bearbeiten",
                    "breadcrumb": {
                        "label": "Bearbeiten",
                        "parent": "whatsapp-campaigns",
                    },
                },
            },
            {
                "path": "campaigns/new",
                "name": "whatsapp-campaign-new",
                "view": "WhatsAppCampaignEditView",
                "meta": {
                    "title": "Neue Kampagne",
                    "breadcrumb": {"label": "Neu", "parent": "whatsapp-campaigns"},
                },
            },
            # Detail routes - Templates
            {
                "path": "templates/:id",
                "name": "whatsapp-template-detail",
                "view": "WhatsAppTemplateDetailView",
                "props": True,
                "meta": {
                    "title": "Template",
                    "breadcrumb": {"label": "Details", "parent": "whatsapp-templates"},
                },
            },
            # Detail/Edit routes - Accounts
            {
                "path": "accounts/:id/edit",
                "name": "whatsapp-account-edit",
                "view": "WhatsAppAccountEditView",
                "props": True,
                "meta": {
                    "title": "Account bearbeiten",
                    "breadcrumb": {
                        "label": "Bearbeiten",
                        "parent": "whatsapp-accounts",
                    },
                },
            },
            {
                "path": "accounts/new",
                "name": "whatsapp-account-new",
                "view": "WhatsAppAccountEditView",
                "meta": {
                    "title": "Neuer Account",
                    "breadcrumb": {"label": "Neu", "parent": "whatsapp-accounts"},
                },
            },
        ],
    },
}
