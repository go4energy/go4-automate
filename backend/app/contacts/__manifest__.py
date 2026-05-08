"""Contacts module manifest."""

manifest = {
    "name": "contacts",
    "label": "Kontakte",
    "version": "1.0.0",
    "description": "Kontakte und Firmen verwalten.",
    "icon": "M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z",
    "color": "#6366F1",
    "category": "sales",
    "application": True,
    "depends": [],
    "has_frontend": True,
    "has_models": True,
    "has_config_schema": True,
    "routers": ["router"],
    "router_prefix": "/contacts",
    "sidebar": {"group": "SALES", "order": 10},
    "frontend": {
        "base_route": "/contacts",
        "routes": [
            # Tab routes
            {
                "path": "",
                "name": "contacts",
                "view": "ContactsView",
                "meta": {
                    "title": "Kontakte",
                    "breadcrumb": {"label": "Kontakte"},
                    "tab": "contacts",
                },
            },
            {
                "path": "people",
                "name": "contacts-people",
                "view": "ContactsView",
                "meta": {
                    "title": "Personen",
                    "breadcrumb": {"label": "Personen", "parent": "contacts"},
                    "tab": "contacts",
                },
            },
            {
                "path": "companies",
                "name": "contacts-companies",
                "view": "ContactsView",
                "meta": {
                    "title": "Firmen",
                    "breadcrumb": {"label": "Firmen", "parent": "contacts"},
                    "tab": "companies",
                },
            },
            {
                "path": "einstellungen",
                "name": "contacts-einstellungen",
                "view": "ContactsView",
                "meta": {
                    "title": "Einstellungen",
                    "breadcrumb": {"label": "Einstellungen", "parent": "contacts"},
                    "tab": "einstellungen",
                },
            },
            # Detail routes
            {
                "path": "people/:id",
                "name": "contact-detail",
                "view": "ContactDetailView",
                "props": True,
                "meta": {
                    "title": "Kontakt",
                    "breadcrumb": {"label": "Details", "parent": "contacts-people"},
                },
            },
            {
                "path": "companies/:id",
                "name": "company-detail",
                "view": "CompanyDetailView",
                "props": True,
                "meta": {
                    "title": "Firma",
                    "breadcrumb": {"label": "Details", "parent": "contacts-companies"},
                },
            },
        ],
    },
}
