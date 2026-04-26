"""Licensing module manifest — system module."""

manifest = {
    "name": "licensing",
    "label": "Modul-Lizenzen",
    "version": "0.1.0",
    "description": (
        "Per-Tenant Modul-Aktivierung. System-Modul; nicht über die "
        "Sidebar erreichbar, sondern aus den Settings heraus."
    ),
    "icon": "M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806",
    "category": "system",
    "application": False,
    "depends": ["auth"],
    "has_frontend": False,
    "has_models": True,
    "has_config_schema": False,
    "routers": ["router"],
    "router_prefix": "/licensing",
}
