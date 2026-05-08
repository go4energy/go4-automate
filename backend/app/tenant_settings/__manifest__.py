"""Tenant-Stammdaten module manifest.

Dieses Modul liefert nur Backend-API + Datenmodell. Die UI ist als Tab
in ``/settings/stammdaten`` (SettingsView.vue) integriert — kein eigener
Sidebar-Eintrag, weil Stammdaten konzeptuell zu den globalen Einstellungen
gehören.
"""

manifest = {
    "name": "tenant_settings",
    "label": "Tenant-Stammdaten",
    "version": "1.0.0",
    "description": (
        "Rechtskonforme Pflichtangaben pro Mandant: Firma, Adresse, "
        "Geschäftsführung, HRB, USt-ID, Datenschutz. Quelle für "
        "{{impressum_block}} und {{disclaimer_block}} im Email-Renderer. "
        "UI als Tab in /settings."
    ),
    "category": "system",
    "application": False,  # kein Sidebar-Eintrag — UI in SettingsView
    "depends": [],
    "has_frontend": False,  # Frontend in SettingsView statt eigener View
    "has_models": True,
    "has_config_schema": False,
    "routers": ["router"],
    "router_prefix": "/tenant-settings",
}
