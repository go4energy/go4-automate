"""Engagement module manifest."""

manifest = {
    "name": "engagement",
    "label": "Engagement",
    "version": "1.0.0",
    "description": "Multi-Channel AI-gesteuertes Engagement mit zentralem Brain",
    "icon": "M13 10V3L4 14h7v7l9-11h-7z",  # Lightning bolt
    "color": "#8B5CF6",
    "category": "sales",
    "application": True,
    "depends": ["contacts"],
    "has_frontend": True,
    "has_models": True,
    "has_config_schema": False,
    "routers": ["router"],
    "router_prefix": "/engagement",
    "sidebar": {"group": "SALES", "order": 15},
    "frontend": {
        "base_route": "/engagement",
        "routes": [
            # Master/Detail pattern (Leadgen-style):
            #   /engagement                       → Pipelines-Liste
            #   /engagement/pipelines             → Pipelines-Liste (alias)
            #   /engagement/pipelines/:id/...     → Pipeline-Detail mit Sub-Tabs
            {
                "path": "",
                "name": "engagement",
                "view": "EngagementView",
                "meta": {
                    "title": "Engagement",
                    "breadcrumb": {"label": "Engagement"},
                    "tab": "pipelines",
                },
            },
            # Pipelines
            {
                "path": "pipelines",
                "name": "engagement-pipelines",
                "view": "EngagementView",
                "meta": {
                    "title": "Pipelines",
                    "breadcrumb": {"label": "Pipelines", "parent": "engagement"},
                    "tab": "pipelines",
                },
            },
            {
                "path": "pipelines/new",
                "name": "engagement-pipeline-new",
                "view": "PipelineEditView",
                "meta": {
                    "title": "Neue Pipeline",
                    "breadcrumb": {"label": "Neu", "parent": "engagement-pipelines"},
                },
            },
            # Pipeline detail with sub-tabs (Leadgen-style master/detail).
            {
                "path": "pipelines/:id",
                "name": "engagement-pipeline-detail",
                "view": "PipelineDetailView",
                "props": True,
                "meta": {
                    "title": "Pipeline",
                    "breadcrumb": {"label": "Details", "parent": "engagement-pipelines"},
                    "tab": "uebersicht",
                },
            },
            {
                "path": "pipelines/:id/uebersicht",
                "name": "engagement-pipeline-uebersicht",
                "view": "PipelineDetailView",
                "props": True,
                "meta": {
                    "title": "Übersicht",
                    "breadcrumb": {"label": "Übersicht", "parent": "engagement-pipelines"},
                    "tab": "uebersicht",
                },
            },
            {
                "path": "pipelines/:id/enrollments",
                "name": "engagement-pipeline-enrollments",
                "view": "PipelineDetailView",
                "props": True,
                "meta": {
                    "title": "Enrollments",
                    "breadcrumb": {"label": "Enrollments", "parent": "engagement-pipelines"},
                    "tab": "enrollments",
                },
            },
            {
                "path": "pipelines/:id/actions",
                "name": "engagement-pipeline-actions",
                "view": "PipelineDetailView",
                "props": True,
                "meta": {
                    "title": "Aktionen",
                    "breadcrumb": {"label": "Aktionen", "parent": "engagement-pipelines"},
                    "tab": "actions",
                },
            },
            {
                "path": "pipelines/:id/activities",
                "name": "engagement-pipeline-activities",
                "view": "PipelineDetailView",
                "props": True,
                "meta": {
                    "title": "Aktivitäten",
                    "breadcrumb": {"label": "Aktivitäten", "parent": "engagement-pipelines"},
                    "tab": "activities",
                },
            },
            {
                "path": "pipelines/:id/ab-tests",
                "name": "engagement-pipeline-ab-tests",
                "view": "PipelineDetailView",
                "props": True,
                "meta": {
                    "title": "A/B Tests",
                    "breadcrumb": {"label": "A/B Tests", "parent": "engagement-pipelines"},
                    "tab": "ab-tests",
                },
            },
            {
                "path": "pipelines/:id/edit",
                "name": "engagement-pipeline-edit",
                "view": "PipelineEditView",
                "props": True,
                "meta": {
                    "title": "Pipeline bearbeiten",
                    "breadcrumb": {"label": "Bearbeiten", "parent": "engagement-pipelines"},
                },
            },
            # A/B Test edit views — kept (functional pages, not navigated by tab).
            {
                "path": "ab-tests/new",
                "name": "engagement-ab-test-new",
                "view": "ABTestEditView",
                "meta": {
                    "title": "Neuer A/B Test",
                    "breadcrumb": {"label": "Neu", "parent": "engagement-pipelines"},
                },
            },
            {
                "path": "ab-tests/:id/edit",
                "name": "engagement-ab-test-edit",
                "view": "ABTestEditView",
                "props": True,
                "meta": {
                    "title": "A/B Test bearbeiten",
                    "breadcrumb": {"label": "Bearbeiten", "parent": "engagement-pipelines"},
                },
            },
        ],
    },
    # AI Setup Configuration
    "ai": {
        "description": """
            Engagement Brain - Zentrale KI-Orchestrierung für Multi-Channel-Engagement.
            - Pipelines: Produkt-spezifische Engagement-Sequenzen
            - Enrollments: Kontakte in Pipelines einschreiben
            - Actions: Automatisch delegierte Aufgaben an Module
            - Activities: Zentrale Timeline aller Interaktionen
        """,
        "default_prompts": [
            # ═══════════════════════════════════════════════════════════════
            # SETUP PROMPTS
            # ═══════════════════════════════════════════════════════════════
            {
                "slug": "onboarding",
                "name": "Pipeline-Onboarding",
                "description": "Setup einer neuen Engagement-Pipeline via Chat-Dialog",
                "category": "onboarding",
                "prompt_type": "setup",
                "is_system": True,
                "system_prompt": """Du bist ein freundlicher Setup-Assistent für Engagement-Pipelines.
Deine Aufgabe ist es, durch einen strukturierten Dialog alle Informationen zu sammeln, um eine effektive Multi-Channel-Engagement-Pipeline aufzusetzen.

Regeln:
- Stelle immer nur EINE Frage auf einmal
- Warte auf die Antwort bevor du die nächste Frage stellst
- Sei freundlich und hilfsbereit
- Gib Beispiele wenn nötig
- Erkläre kurz warum die Information wichtig ist

Frage nacheinander:
1. **Produkt/Service**: Was wird beworben? (Name und kurze Beschreibung)
2. **Zielgruppe**: Wer soll angesprochen werden? (Branchen, Positionen, Unternehmensgröße)
3. **Kanäle**: Welche Kanäle sollen genutzt werden? (LinkedIn, Email, Brief, Telefon, WhatsApp)
4. **Reihenfolge**: In welcher Abfolge sollen die Kanäle eingesetzt werden?
5. **Ziel**: Was ist das Hauptziel? (Termin, Demo, Angebot, Verkauf)
6. **Tonalität**: Wie soll die Ansprache sein? (Professionell, locker, technisch)
7. **Timing**: Wie viele Tage Mindestabstand zwischen Kontaktversuchen?
8. **Besonderheiten**: Gibt es USPs oder wichtige Punkte die erwähnt werden sollen?

Nach der letzten Antwort:
- Fasse alle gesammelten Informationen zusammen
- Zeige eine Vorschau der Pipeline-Konfiguration
- Frage ob alles korrekt ist oder Anpassungen nötig sind""",
                "user_prompt": "Starte das Pipeline-Setup.",
                "variables_schema": {
                    "product_name": {"type": "string", "description": "Name des Produkts/Service"},
                    "product_description": {"type": "string", "description": "Beschreibung"},
                    "target_audience": {"type": "string", "description": "Zielgruppe"},
                    "channels": {"type": "list", "description": "Gewählte Kanäle"},
                    "channel_sequence": {"type": "list", "description": "Reihenfolge der Kanäle"},
                    "goal": {"type": "string", "description": "Hauptziel"},
                    "tone_of_voice": {"type": "string", "description": "Tonalität"},
                    "min_days_between_touches": {"type": "integer", "description": "Mindestabstand"},
                    "key_points": {"type": "list", "description": "USPs und wichtige Punkte"},
                },
                "model": "claude-sonnet-4-20250514",
                "temperature": 0.7,
                "max_tokens": 1500,
            },
            # ═══════════════════════════════════════════════════════════════
            # BRAIN PROMPTS
            # ═══════════════════════════════════════════════════════════════
            {
                "slug": "next-step-analyzer",
                "name": "Next-Step Analyzer",
                "description": "Analysiert einen Enrollment und entscheidet den nächsten Schritt",
                "category": "brain",
                "prompt_type": "productive",
                "is_system": True,
                "system_prompt": """Du bist das zentrale Engagement Brain.
Deine Aufgabe ist es, für einen Kontakt in einer Pipeline den optimalen nächsten Schritt zu bestimmen.

Du erhältst:
- Pipeline-Konfiguration (Produkt, Zielgruppe, Kanäle, Playbook)
- Kontakt-Informationen
- Bisherige Aktivitäten und Interaktionen
- Aktueller Stage im Funnel

Antworte im JSON-Format:
{
    "recommendation": {
        "channel": "linkedin|email|phone|letter|whatsapp",
        "action": "send_connection_request|send_message|send_email|make_call|send_letter",
        "reasoning": "Kurze Begründung",
        "suggested_content": "Vorgeschlagener Inhalt (optional)",
        "priority": "urgent|high|normal|low",
        "wait_days": 0
    },
    "stage_update": "lead|contacted|engaged|qualified|converted|lost" (optional),
    "insights": ["Erkenntnisse aus den bisherigen Interaktionen"]
}

Regeln:
- Respektiere die Pipeline-Konfiguration (verfügbare Kanäle, Timing)
- Berücksichtige bisherige Interaktionen (nicht wiederholen was schon geschickt wurde)
- Bei Antwort des Kontakts: Adaptiv reagieren, nicht stur der Sequenz folgen
- Bei negativem Sentiment: Vorsichtiger, evtl. pausieren
- Mindestabstand zwischen Touches einhalten""",
                "user_prompt": """Analysiere und empfehle den nächsten Schritt:

PIPELINE:
{{pipeline_config}}

KONTAKT:
{{contact_info}}

BISHERIGE AKTIVITÄTEN:
{{activities}}

AKTUELLER STATUS:
Stage: {{current_stage}}
Touch Count: {{touch_count}}
Letzte Interaktion: {{last_touch}}
Letzte Antwort: {{last_response}}""",
                "model": "claude-sonnet-4-20250514",
                "temperature": 0.5,
                "max_tokens": 1000,
            },
            {
                "slug": "response-analyzer",
                "name": "Response Analyzer",
                "description": "Analysiert eingehende Nachrichten und bestimmt Intent/Sentiment",
                "category": "brain",
                "prompt_type": "productive",
                "is_system": True,
                "system_prompt": """Du analysierst eingehende Nachrichten von Kontakten.

Bestimme:
1. **Sentiment**: positive, neutral, negative
2. **Intent**: Was will der Kontakt?
   - interested: Zeigt Interesse am Angebot
   - question: Hat Fragen zum Produkt/Service
   - objection: Hat Einwände oder Bedenken
   - not_interested: Kein Interesse
   - referral: Verweist auf jemand anderen
   - meeting_request: Möchte einen Termin
   - postpone: Möchte später kontaktiert werden
   - unsubscribe: Möchte nicht mehr kontaktiert werden

3. **Empfohlene Aktion**: Was sollte als nächstes passieren?

Antworte im JSON-Format:
{
    "sentiment": "positive|neutral|negative",
    "intent": "interested|question|objection|not_interested|referral|meeting_request|postpone|unsubscribe",
    "confidence": 0.0-1.0,
    "key_points": ["Wichtige Punkte aus der Nachricht"],
    "recommended_action": {
        "type": "respond|escalate|schedule|pause|stop",
        "urgency": "immediate|soon|normal",
        "notes": "Hinweise für die Antwort"
    }
}""",
                "user_prompt": """Analysiere diese eingehende Nachricht:

KANAL: {{channel}}
VON: {{contact_name}} ({{contact_position}} bei {{contact_company}})

NACHRICHT:
{{message_content}}

KONTEXT (bisherige Kommunikation):
{{conversation_history}}""",
                "model": "claude-sonnet-4-20250514",
                "temperature": 0.3,
                "max_tokens": 500,
            },
            {
                "slug": "playbook-generator",
                "name": "Playbook Generator",
                "description": "Generiert ein detailliertes Playbook für eine Pipeline",
                "category": "brain",
                "prompt_type": "productive",
                "is_system": True,
                "system_prompt": """Du erstellst detaillierte Playbooks für Engagement-Pipelines.

Ein Playbook definiert:
1. Die Gesamtstrategie
2. Kanal-spezifische Taktiken
3. Timing und Sequencing
4. Vorlagen und Frameworks für Nachrichten
5. Eskalations- und Deeskalationsstrategien
6. Best Practices

Erstelle ein strukturiertes, praktisch anwendbares Playbook.""",
                "user_prompt": """Erstelle ein Playbook für diese Pipeline:

PRODUKT: {{product_name}}
{{product_description}}

ZIELGRUPPE: {{target_audience}}

KANÄLE: {{channels}}

ZIEL: {{goal}}

TONALITÄT: {{tone_of_voice}}

TIMING: Mindestens {{min_days_between_touches}} Tage zwischen Touches

USPs: {{key_points}}""",
                "model": "claude-sonnet-4-20250514",
                "temperature": 0.6,
                "max_tokens": 2000,
            },
        ],
    },
}
