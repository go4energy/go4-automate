"""Surveys module manifest."""

manifest = {
    "name": "surveys",
    "label": "Surveys",
    "version": "1.0.0",
    "description": "Feedback- und NPS-Umfragen für Kundenbefragungen.",
    "icon": "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01",
    "color": "#10B981",
    "category": "sales",
    "application": True,
    "depends": ["contacts"],
    "has_frontend": True,
    "has_models": True,
    "has_config_schema": False,
    "routers": ["router", "public_router"],
    "router_prefix": "/surveys",
    "sidebar": {"group": "SALES", "order": 40},
    "frontend": {
        "base_route": "/surveys",
        "routes": [
            {
                "path": "",
                "name": "surveys",
                "view": "SurveysView",
                "meta": {"title": "Umfragen"},
            },
            {
                "path": "einstellungen",
                "name": "surveys-einstellungen",
                "view": "ModuleSettingsPageView",
                "meta": {
                    "title": "Umfragen — Einstellungen",
                    "moduleName": "surveys",
                    "breadcrumb": {"label": "Einstellungen", "parent": "surveys"},
                },
            },
            {
                "path": ":id",
                "name": "survey-detail",
                "view": "SurveyDetailView",
                "props": True,
                "meta": {"title": "Umfrage"},
            },
            {
                "path": ":id/edit",
                "name": "survey-edit",
                "view": "SurveyEditView",
                "props": True,
                "meta": {"title": "Umfrage bearbeiten"},
            },
            {
                "path": ":id/results",
                "name": "survey-results",
                "view": "SurveyResultsView",
                "props": True,
                "meta": {"title": "Ergebnisse"},
            },
        ],
    },
}
