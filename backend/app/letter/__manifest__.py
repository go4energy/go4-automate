"""Letter Module Manifest."""

manifest = {
    "name": "letter",
    "label": "Letter",
    "display_name": "Letter",
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
    "router_prefix": "/letter",
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
        "base_route": "/letter",
        "icon": "mdi-email-outline",
        "nav_label": "Letter",
        "nav_position": 55,
        "routes": [
            {
                "path": "",
                "name": "letter",
                "view": "LetterView",
                "meta": {
                    "title": "Letter",
                    "breadcrumb": {"label": "Letter"},
                    "tab": "dashboard",
                },
            },
            {
                "path": "dashboard",
                "name": "letter-dashboard",
                "view": "LetterView",
                "meta": {
                    "title": "Dashboard",
                    "breadcrumb": {"label": "Dashboard", "parent": "letter"},
                    "tab": "dashboard",
                },
            },
            {
                "path": "letters",
                "name": "letter-letters",
                "view": "LetterView",
                "meta": {
                    "title": "Briefe",
                    "breadcrumb": {"label": "Briefe", "parent": "letter"},
                    "tab": "letters",
                },
            },
            {
                "path": "templates",
                "name": "letter-templates",
                "view": "LetterView",
                "meta": {
                    "title": "Templates",
                    "breadcrumb": {"label": "Templates", "parent": "letter"},
                    "tab": "templates",
                },
            },
            {
                "path": "templates/:id/edit",
                "name": "letter-template-edit",
                "view": "LetterTemplateEditView",
                "props": True,
                "meta": {
                    "title": "Template bearbeiten",
                    "breadcrumb": {
                        "label": "Bearbeiten",
                        "parent": "letter-templates",
                    },
                },
            },
            {
                "path": "batches",
                "name": "letter-batches",
                "view": "LetterView",
                "meta": {
                    "title": "Batches",
                    "breadcrumb": {"label": "Batches", "parent": "letter"},
                    "tab": "batches",
                },
            },
            {
                "path": "setup",
                "name": "letter-setup",
                "view": "LetterView",
                "meta": {
                    "title": "Setup",
                    "breadcrumb": {"label": "Setup", "parent": "letter"},
                    "tab": "settings",
                },
            },
            {
                "path": "letters/:id",
                "name": "letter-detail",
                "view": "LetterDetailView",
                "props": True,
                "meta": {
                    "title": "Brief-Details",
                    "breadcrumb": {"label": "Details", "parent": "letter"},
                },
            },
        ],
    },
}
