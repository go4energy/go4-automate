"""LinkedIn module manifest."""

manifest = {
    "name": "linkedin",
    "label": "LinkedIn",
    "version": "2.0.0",
    "description": "Sales Navigator Scraping, Outreach & Kampagnen",
    "icon": "M4 3a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2V5a2 2 0 00-2-2H4zm3 5a1.5 1.5 0 100-3 1.5 1.5 0 000 3zm-1.5 2h3v9h-3v-9zm5.5 0h3v1.5s1-1.5 3-1.5c1.5 0 3 1 3 4v5h-3v-4c0-1.5-.5-2-1.5-2s-1.5 1-1.5 2v4h-3v-9z",
    "color": "#0A66C2",
    "category": "sales",
    "application": True,
    "depends": ["funnels"],
    "has_frontend": True,
    "has_models": True,
    "has_config_schema": True,
    "routers": ["router", "outreach_router"],
    "router_prefix": "/linkedin",
    "sidebar": {"group": "SALES", "order": 17},
    "frontend": {
        "base_route": "/linkedin",
        "routes": [
            # Tab routes - all use the same view but different tabs
            {
                "path": "",
                "name": "linkedin",
                "view": "LinkedInView",
                "meta": {
                    "title": "LinkedIn",
                    "breadcrumb": {"label": "LinkedIn"},
                    "tab": "dashboard",
                },
            },
            {
                "path": "dashboard",
                "name": "linkedin-dashboard",
                "view": "LinkedInView",
                "meta": {
                    "title": "Dashboard",
                    "breadcrumb": {"label": "Dashboard", "parent": "linkedin"},
                    "tab": "dashboard",
                },
            },
            {
                "path": "accounts",
                "name": "linkedin-accounts",
                "view": "LinkedInView",
                "meta": {
                    "title": "Accounts",
                    "breadcrumb": {"label": "Accounts", "parent": "linkedin"},
                    "tab": "accounts",
                },
            },
            {
                "path": "jobs",
                "name": "linkedin-jobs",
                "view": "LinkedInView",
                "meta": {
                    "title": "Scraper Jobs",
                    "breadcrumb": {"label": "Jobs", "parent": "linkedin"},
                    "tab": "jobs",
                },
            },
            {
                "path": "contacts",
                "name": "linkedin-contacts",
                "view": "LinkedInView",
                "meta": {
                    "title": "Kontakte",
                    "breadcrumb": {"label": "Kontakte", "parent": "linkedin"},
                    "tab": "contacts",
                },
            },
            # NEW: Outreach tabs
            {
                "path": "templates",
                "name": "linkedin-templates",
                "view": "LinkedInView",
                "meta": {
                    "title": "Vorlagen",
                    "breadcrumb": {"label": "Vorlagen", "parent": "linkedin"},
                    "tab": "templates",
                },
            },
            {
                "path": "outreach",
                "name": "linkedin-outreach",
                "view": "LinkedInView",
                "meta": {
                    "title": "Outreach",
                    "breadcrumb": {"label": "Outreach", "parent": "linkedin"},
                    "tab": "outreach",
                },
            },
            {
                "path": "campaigns",
                "name": "linkedin-campaigns",
                "view": "LinkedInView",
                "meta": {
                    "title": "Kampagnen",
                    "breadcrumb": {"label": "Kampagnen", "parent": "linkedin"},
                    "tab": "campaigns",
                },
            },
            {
                "path": "inbox",
                "name": "linkedin-inbox",
                "view": "LinkedInView",
                "meta": {
                    "title": "Inbox",
                    "breadcrumb": {"label": "Inbox", "parent": "linkedin"},
                    "tab": "inbox",
                },
            },
            {
                "path": "guide",
                "name": "linkedin-guide",
                "view": "LinkedInView",
                "meta": {
                    "title": "Anleitung",
                    "breadcrumb": {"label": "Anleitung", "parent": "linkedin"},
                    "tab": "guide",
                },
            },
            {
                "path": "freigabe",
                "name": "linkedin-freigabe",
                "view": "LinkedInView",
                "meta": {
                    "title": "Freigabe",
                    "breadcrumb": {"label": "Freigabe", "parent": "linkedin"},
                    "tab": "freigabe",
                },
            },
            {
                "path": "setup",
                "name": "linkedin-setup",
                "view": "LinkedInView",
                "meta": {
                    "title": "Setup",
                    "breadcrumb": {"label": "Setup", "parent": "linkedin"},
                    "tab": "setup",
                },
            },
            # Detail/Edit routes
            {
                "path": "accounts/new",
                "name": "linkedin-account-new",
                "view": "LinkedInAccountEditView",
                "meta": {
                    "title": "Neuer Account",
                    "breadcrumb": {"label": "Neu", "parent": "linkedin-accounts"},
                },
            },
            {
                "path": "accounts/:id/edit",
                "name": "linkedin-account-edit",
                "view": "LinkedInAccountEditView",
                "props": True,
                "meta": {
                    "title": "Account bearbeiten",
                    "breadcrumb": {"label": "Bearbeiten", "parent": "linkedin-accounts"},
                },
            },
            {
                "path": "jobs/new",
                "name": "linkedin-job-new",
                "view": "LinkedInJobEditView",
                "meta": {
                    "title": "Neuer Scraper-Job",
                    "breadcrumb": {"label": "Neu", "parent": "linkedin-jobs"},
                },
            },
            {
                "path": "jobs/:id/edit",
                "name": "linkedin-job-edit",
                "view": "LinkedInJobEditView",
                "props": True,
                "meta": {
                    "title": "Job bearbeiten",
                    "breadcrumb": {"label": "Bearbeiten", "parent": "linkedin-jobs"},
                },
            },
            {
                "path": "jobs/:id",
                "name": "linkedin-job-detail",
                "view": "LinkedInJobDetailView",
                "props": True,
                "meta": {
                    "title": "Job-Details",
                    "breadcrumb": {"label": "Details", "parent": "linkedin-jobs"},
                },
            },
            {
                "path": "contacts/:id",
                "name": "linkedin-contact-detail",
                "view": "LinkedInContactDetailView",
                "props": True,
                "meta": {
                    "title": "Kontakt-Details",
                    "breadcrumb": {"label": "Details", "parent": "linkedin-contacts"},
                },
            },
            # NEW: Template routes
            {
                "path": "templates/new",
                "name": "linkedin-template-new",
                "view": "LinkedInTemplateEditView",
                "meta": {
                    "title": "Neue Vorlage",
                    "breadcrumb": {"label": "Neu", "parent": "linkedin-templates"},
                },
            },
            {
                "path": "templates/:id/edit",
                "name": "linkedin-template-edit",
                "view": "LinkedInTemplateEditView",
                "props": True,
                "meta": {
                    "title": "Vorlage bearbeiten",
                    "breadcrumb": {"label": "Bearbeiten", "parent": "linkedin-templates"},
                },
            },
            # NEW: Campaign routes
            {
                "path": "campaigns/new",
                "name": "linkedin-campaign-new",
                "view": "LinkedInCampaignEditView",
                "meta": {
                    "title": "Neue Kampagne",
                    "breadcrumb": {"label": "Neu", "parent": "linkedin-campaigns"},
                },
            },
            {
                "path": "campaigns/:id",
                "name": "linkedin-campaign-detail",
                "view": "LinkedInCampaignDetailView",
                "props": True,
                "meta": {
                    "title": "Kampagne",
                    "breadcrumb": {"label": "Details", "parent": "linkedin-campaigns"},
                },
            },
            {
                "path": "campaigns/:id/edit",
                "name": "linkedin-campaign-edit",
                "view": "LinkedInCampaignEditView",
                "props": True,
                "meta": {
                    "title": "Kampagne bearbeiten",
                    "breadcrumb": {"label": "Bearbeiten", "parent": "linkedin-campaigns"},
                },
            },
        ],
    },
    # AI Setup Configuration
    "ai": {
        "description": """
            LinkedIn Automation für B2B Lead Generation.
            - Accounts: LinkedIn-Profile verbinden und verwalten
            - Scraper Jobs: Kontakte aus Sales Navigator extrahieren
            - Kontakte: Gescrapte Profile verwalten und filtern
            - Vorlagen: Nachrichtenvorlagen mit Variablen
            - Kampagnen: Automatisierte Outreach-Sequenzen
        """,
        "default_prompts": [
            # ═══════════════════════════════════════════════════════════════
            # SETUP PROMPTS
            # ═══════════════════════════════════════════════════════════════
            {
                "slug": "onboarding",
                "name": "Onboarding",
                "description": "Ersteinrichtung des LinkedIn-Moduls",
                "category": "onboarding",
                "prompt_type": "setup",
                "is_system": True,
                "system_prompt": """Du bist ein freundlicher Setup-Assistent für LinkedIn-Kampagnen.
Führe ein strukturiertes Interview, um die wichtigsten Konfigurationsparameter zu sammeln.

Regeln:
- Stelle immer nur EINE Frage auf einmal
- Warte auf die Antwort bevor du die nächste Frage stellst
- Sei freundlich und hilfsbereit
- Gib Beispiele wenn nötig
- Fasse am Ende alles zusammen

Frage nacheinander:
1. Wie heißt das Unternehmen des Users?
2. Was bietet das Unternehmen an? (kurze Beschreibung)
3. Welche Zielgruppe soll auf LinkedIn erreicht werden? (Branche, Positionen)
4. Duzt oder siezt ihr eure Leads normalerweise?
5. Was ist der typische Call-to-Action? (Termin, Demo, Whitepaper, etc.)
6. Gibt es besondere Punkte die in der Ansprache erwähnt werden sollen?

Nach der letzten Antwort: Fasse alle Informationen zusammen und bestätige die Konfiguration.""",
                "user_prompt": "Starte das Interview.",
                "variables_schema": {
                    "company_name": {"type": "string", "description": "Firmenname"},
                    "company_offering": {"type": "string", "description": "Was bietet die Firma an"},
                    "target_industry": {"type": "string", "description": "Zielbranche"},
                    "target_positions": {"type": "list", "description": "Zielpositionen"},
                    "formal_address": {"type": "boolean", "description": "Sie-Form verwenden"},
                    "default_cta": {"type": "string", "description": "Standard Call-to-Action"},
                    "key_points": {"type": "list", "description": "Wichtige Punkte für Ansprache"},
                },
                "model": "claude-sonnet-4-20250514",
                "temperature": 0.7,
                "max_tokens": 1024,
            },
            # ═══════════════════════════════════════════════════════════════
            # PRODUCTIVE PROMPTS
            # ═══════════════════════════════════════════════════════════════
            {
                "slug": "connection_request",
                "name": "Verbindungsanfrage",
                "description": "Generiert personalisierte LinkedIn-Verbindungsanfragen",
                "category": "outreach",
                "prompt_type": "productive",
                "is_system": True,
                "system_prompt": """Du schreibst kurze, persönliche LinkedIn-Verbindungsanfragen.

Kontext:
- Unternehmen: {{company_name}}
- Angebot: {{company_offering}}
- Ansprache: {{formal_address ? "Sie-Form" : "Du-Form"}}
- Call-to-Action: {{default_cta}}

Regeln:
- Maximal 300 Zeichen (LinkedIn-Limit)
- Persönlich und authentisch
- Kein Verkaufsgespräch, nur Verbindung aufbauen
- Bezug zur Person herstellen""",
                "user_prompt": """Schreibe eine Verbindungsanfrage für:
Name: {{lead_name}}
Position: {{lead_position}}
Firma: {{lead_company}}
{{#if lead_headline}}Headline: {{lead_headline}}{{/if}}""",
                "model": "claude-sonnet-4-20250514",
                "temperature": 0.8,
                "max_tokens": 200,
            },
            {
                "slug": "followup_message",
                "name": "Follow-up Nachricht",
                "description": "Generiert Follow-up Nachrichten nach Verbindung",
                "category": "outreach",
                "prompt_type": "productive",
                "is_system": True,
                "system_prompt": """Du schreibst Follow-up Nachrichten für LinkedIn.

Kontext:
- Unternehmen: {{company_name}}
- Angebot: {{company_offering}}
- Ansprache: {{formal_address ? "Sie-Form" : "Du-Form"}}
- Call-to-Action: {{default_cta}}
{{#if key_points}}- Wichtige Punkte: {{key_points}}{{/if}}

Regeln:
- Freundlich und nicht aufdringlich
- Mehrwert bieten
- Klarer nächster Schritt
- Maximal 500 Zeichen""",
                "user_prompt": """Schreibe eine Follow-up Nachricht für:
Name: {{lead_name}}
Position: {{lead_position}}
Firma: {{lead_company}}
Tage seit Verbindung: {{days_connected}}""",
                "model": "claude-sonnet-4-20250514",
                "temperature": 0.8,
                "max_tokens": 300,
            },
            {
                "slug": "profile_summary",
                "name": "Profil-Zusammenfassung",
                "description": "Fasst LinkedIn-Profile zusammen für Outreach",
                "category": "analysis",
                "prompt_type": "productive",
                "is_system": True,
                "system_prompt": """Du analysierst LinkedIn-Profile und erstellst kurze Zusammenfassungen für den Vertrieb.

Fokussiere auf:
- Relevanz für unser Angebot ({{company_offering}})
- Entscheidungsbefugnis
- Potenzielle Pain Points
- Anknüpfungspunkte für Gespräche""",
                "user_prompt": """Analysiere dieses Profil:
Name: {{lead_name}}
Position: {{lead_position}}
Firma: {{lead_company}}
{{#if lead_headline}}Headline: {{lead_headline}}{{/if}}
{{#if lead_about}}Über: {{lead_about}}{{/if}}
{{#if lead_experience}}Erfahrung: {{lead_experience}}{{/if}}""",
                "model": "claude-sonnet-4-20250514",
                "temperature": 0.5,
                "max_tokens": 500,
            },
        ],
    },
}
