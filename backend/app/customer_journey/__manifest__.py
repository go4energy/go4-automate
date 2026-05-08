"""Customer Journey module manifest."""

manifest = {
    "name": "customer_journey",
    "label": "Customer Journey",
    "version": "1.0.0",
    "description": "Lead-Tracking, Ref-Codes und Kampagnen-Attribution über alle Kanäle.",
    "icon": "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z",
    "color": "#059669",
    "category": "marketing",
    "application": True,
    "depends": ["contacts"],
    "has_frontend": True,
    "has_models": True,
    "has_config_schema": True,
    "routers": ["router", "tracking_router"],
    "router_prefix": "/customer-journey",
    "sidebar": {"group": "MARKETING", "order": 5},
    "frontend": {
        "base_route": "/customer-journey",
        "routes": [
            {
                "path": "",
                "name": "customer-journey",
                "view": "CustomerJourneyView",
                "meta": {
                    "title": "Customer Journey",
                    "breadcrumb": {"label": "Customer Journey"},
                    "tab": "dashboard",
                },
            },
            {
                "path": "leads",
                "name": "customer-journey-leads",
                "view": "CustomerJourneyView",
                "meta": {
                    "title": "Leads",
                    "breadcrumb": {
                        "label": "Leads",
                        "parent": "customer-journey",
                    },
                    "tab": "dashboard",
                },
            },
            {
                "path": "ref-codes",
                "name": "customer-journey-refs",
                "view": "CustomerJourneyView",
                "meta": {
                    "title": "Ref-Codes",
                    "breadcrumb": {
                        "label": "Ref-Codes",
                        "parent": "customer-journey",
                    },
                    "tab": "refs",
                },
            },
            {
                "path": "campaigns",
                "name": "customer-journey-campaigns",
                "view": "CustomerJourneyView",
                "meta": {
                    "title": "Kampagnen",
                    "breadcrumb": {
                        "label": "Kampagnen",
                        "parent": "customer-journey",
                    },
                    "tab": "campaigns",
                },
            },
            {
                "path": "einstellungen",
                "name": "customer-journey-einstellungen",
                "view": "CustomerJourneyView",
                "meta": {
                    "title": "Einstellungen",
                    "breadcrumb": {
                        "label": "Einstellungen",
                        "parent": "customer-journey",
                    },
                    "tab": "einstellungen",
                },
            },
            {
                "path": "leads/:id",
                "name": "customer-journey-lead-detail",
                "view": "CustomerJourneyLeadDetailView",
                "props": True,
                "meta": {
                    "title": "Lead-Detail",
                    "breadcrumb": {
                        "label": "Details",
                        "parent": "customer-journey-leads",
                    },
                },
            },
        ],
    },
}
