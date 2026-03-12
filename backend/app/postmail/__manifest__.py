"""Post-Mail Module Manifest."""

manifest = {
    "name": "postmail",
    "label": "Post-Mail",
    "display_name": "Post-Mail",
    "description": "Physische Briefe als Engagement-Kanal",
    "icon": "M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z",
    "color": "#10B981",
    "category": "engagement",
    "version": "1.0.0",
    "application": True,
    "is_core": False,
    "depends": ["contacts", "engagement"],
    "has_frontend": True,
    "has_models": True,
    "has_config_schema": False,
    "routers": ["router"],
    "router_prefix": "/postmail",
    "sidebar": {"group": "MARKETING", "order": 56},
    "config_schema": {
        "lettershop_api_url": {
            "type": "string",
            "label": "Lettershop API URL",
            "required": False,
            "description": "URL des externen Lettershop-Dienstes",
        },
        "lettershop_api_key": {
            "type": "password",
            "label": "Lettershop API Key",
            "required": False,
            "description": "API-Schlüssel für den Lettershop",
        },
        "default_sender_company": {
            "type": "string",
            "label": "Absender Firma",
            "required": False,
            "default": "",
        },
        "default_sender_street": {
            "type": "string",
            "label": "Absender Straße",
            "required": False,
            "default": "",
        },
        "default_sender_zip": {
            "type": "string",
            "label": "Absender PLZ",
            "required": False,
            "default": "",
        },
        "default_sender_city": {
            "type": "string",
            "label": "Absender Stadt",
            "required": False,
            "default": "",
        },
    },
    "frontend": {
        "base_route": "/postmail",
        "icon": "mdi-email-outline",
        "nav_label": "Post-Mail",
        "nav_position": 55,
        "routes": [
            {
                "path": "",
                "name": "postmail",
                "view": "PostmailView",
                "meta": {
                    "title": "Post-Mail",
                    "breadcrumb": {"label": "Post-Mail"},
                    "tab": "letters",
                },
            },
            {
                "path": "templates",
                "name": "postmail-templates",
                "view": "PostmailView",
                "meta": {
                    "title": "Templates",
                    "breadcrumb": {"label": "Templates", "parent": "postmail"},
                    "tab": "templates",
                },
            },
            {
                "path": "templates/:id/edit",
                "name": "postmail-template-edit",
                "view": "PostmailTemplateEditView",
                "props": True,
                "meta": {
                    "title": "Template bearbeiten",
                    "breadcrumb": {
                        "label": "Bearbeiten",
                        "parent": "postmail-templates",
                    },
                },
            },
            {
                "path": "batches",
                "name": "postmail-batches",
                "view": "PostmailView",
                "meta": {
                    "title": "Batches",
                    "breadcrumb": {"label": "Batches", "parent": "postmail"},
                    "tab": "batches",
                },
            },
            {
                "path": "letters/:id",
                "name": "postmail-letter-detail",
                "view": "PostmailLetterDetailView",
                "props": True,
                "meta": {
                    "title": "Brief-Details",
                    "breadcrumb": {"label": "Details", "parent": "postmail"},
                },
            },
        ],
    },
}
