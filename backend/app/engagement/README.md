# Engagement Modul

Multi-Channel KI-Orchestrierung. Eine **Pipeline** ist die Strategie (Ziel,
Tonalität, Kanäle, Zielgruppe, Playbook). Das **Engagement Brain** entscheidet
pro Lead in der Pipeline, was als nächstes passiert, und delegiert konkrete
Touches an die ausführenden Module (email, letter, linkedin, whatsapp, phone)
über die `pending_actions`-Tabelle.

> Pipelines sind **Orchestratoren**, keine Resource-Factories — beim Anlegen
> einer Pipeline werden keine Modul-Resources erzeugt. Die Module legen ihre
> Sachen lazy an, sobald das Brain konkrete Aktionen ausschüttet.

## Architektur

```
┌─ ENGAGEMENT BRAIN ─────────────┐    ┌─ AUSFÜHRENDE MODULE ──────────────┐
│ analyze_contact(enrollment)    │    │ Email-Worker liest pending_actions│
│ ↓ LLM (Premium-Klasse)         │    │  - render_template + body         │
│ ActionRecommendation:          │ →  │  - Provider.send_email()          │
│   channel='email'              │    │ Letter-Worker:                    │
│   action='email_send'          │    │  - HTML→PDF + Letterxpress        │
│   suggested_content=<body>     │    │ LinkedIn-Worker:                  │
│   needs_approval=true/false    │    │  - Connection-Note / DM            │
│ ↓                              │    │ Phone-Worker (geplant)            │
│ PendingAction(module=…)        │    │                                   │
└────────────────────────────────┘    └───────────────────────────────────┘
        ↑
        │ liest LLM-Prompt aus
        │ pipeline_prompts (channel + slot)
        │
[ pipeline_prompts (Tab "Kanäle" auf der Übersicht) ]
```

## Datenmodell

| Tabelle | Zweck |
|---|---|
| `engagement_pipelines` | Strategie-Container: Name, Slug, Goal, Tonalität, Channels, Playbook, Tracking-Config, auto_actions |
| `pipeline_enrollments` | Kontakt in Pipeline mit Stage (lead/contacted/engaged/qualified/converted/lost), Touch-Counter, last_touch_at |
| `pending_actions` | Vom Brain delegierte Aufgabe an ein Modul (status: pending/ready_for_approval/approved/completed/failed) |
| `contact_activities` | Outbound + inbound Logs aller Kanäle, mit Sentiment + Intent (vom Brain analysiert) |
| `pipeline_prompts` | **NEU:** LLM-Prompt scoped auf Pipeline + Channel + Slot. Wird vom Brain konsultiert wenn er einen Touch-Body generiert |
| `ab_tests`, `ab_test_variants` | A/B-Test-Konfiguration für Subject/Body-Varianten |
| `tracking_links`, `tracking_events` | Click-Tracking-Infrastruktur (resolve via `Contact.tracking_hash`) |
| `attribution_records` | Conversion-Attribution: welcher Touchpoint hat welchen Lead konvertiert |

## Pipeline-Prompts (per Pipeline + Channel + Slot)

Statt eines hartcodierten globalen Prompts hat jede Pipeline eigene Prompts.
Pro Kanal beliebig viele Slots (typisch: `initial`, `followup_1`, `followup_2`,
`reply`, `reply_positive`, `reply_negative`).

**UI:** Pipeline-Übersicht (`/engagement/pipelines/{id}/uebersicht`), rechte
Spalte „Kanäle & Prompts" → Klick auf Kanal → Slot anlegen / bearbeiten →
Drawer mit Editor + Test-Lauf.

**Backend:** `/v1/engagement/pipelines/{pipeline_id}/prompts`
- `GET` — alle Prompts der Pipeline
- `POST` — neuen Prompt anlegen
- `PUT /{id}` — Prompt aktualisieren
- `DELETE /{id}` — Prompt löschen
- `POST /{id}/test` — mit `contact_id` oder `variables` ausführen → LLM-Output

### Variablen — wer füllt was?

Variablen im Prompt-Text (Syntax `{{variable}}`) werden **vor dem LLM-Aufruf**
durch den Code ersetzt (`prompts_router._build_outreach_variables`). Das LLM
selbst sieht nur den fertig gefüllten Text.

**Automatisch befüllte Variablen** (wenn der Test-Endpoint mit `contact_id`
aufgerufen wird):

| Variable | Quelle |
|---|---|
| `{{firmenname}}` | `company.name` |
| `{{ort}}` | `address_city` (Company → Place-Fallback) |
| `{{anrede_gf}}` | `leadgen_llm_insights.primary_contact.salutation` (Fallback `"Herr/Frau"`) |
| `{{name_gf}}` | `contact.name` |
| `{{first_name}}` / `{{last_name}}` | gesplittet aus `contact.name` oder `primary_contact.*` |
| `{{position}}` | `contact.position` oder `primary_contact.role` |
| `{{personalization_hook}}` | raw `leadgen_llm_insights.personalization_hook` |
| `{{services}}` | Komma-Liste aus `leadgen_llm_insights.services` |
| `{{customer_segments}}` | Komma-Liste aus `leadgen_llm_insights.customer_segments` |
| `{{company_size_indicator}}` | raw `leadgen_llm_insights.company_size_indicator` |
| `{{target_match_score}}` | raw 0-10 |
| `{{pre_pitch_bullets}}` | **kombiniert**: hook + services + segments + size + brands |
| `{{homepage_zusammenfassung}}` | gleicher Wert wie `pre_pitch_bullets` (Backwards-Compat) |
| `{{empowerment_profil}}` | **abgeleitet**: `wallbox_erfahren` / `elektriker_neu_im_segment` / `unklar` (Heuristik aus services + hook) |
| `{{mfh_affinitaet}}` | **abgeleitet**: `hoch` / `mittel` / `niedrig` / `unklar` (Heuristik aus customer_segments + hook) |

**Heuristiken** sind in `prompts_router.py` definiert:
- `_derive_empowerment_profile(services, hook)` — sucht nach „wallbox/ladeinfra/e-mobilität" → `wallbox_erfahren`, sonst „elektriker/elektroinstallation" → `elektriker_neu_im_segment`, sonst `unklar`
- `_derive_mfh_affinity(segments, hook)` — sucht „mfh/weg/hausverwaltung" → `hoch`, „gewerbe/industrie" → `mittel`, „efh/privat" → `niedrig`, sonst `unklar`

**Override beim Testen:** Im Test-Drawer kannst du einzelne Variablen explizit
mitgeben (`variables`-Feld) — die überschreiben die Auto-Auflösung.

**Tippfehler:** Eine unbekannte Variable wie `{{firmen_name}}` wird still durch
`""` ersetzt → Claude generiert generisch. Im Editor-Drawer gibt es klickbare
Variablen-Chips, um Tippfehler zu vermeiden.

### Neue Variable hinzufügen

1. **Einmalig dauerhaft** (für alle Prompts verfügbar) → `_build_outreach_variables`
   in `prompts_router.py` erweitern, optional Heuristik daneben definieren.
2. **Ad-hoc Test** → im Drawer beim Test-Lauf das Variablen-Dict mitgeben.

## LLM-Klassen

Das Brain nutzt:
- **Premium** (Opus 4.7): `analyze_contact` (Next-Step-Entscheidung) — interaktiv, kreativ
- **Standard** (Sonnet 4.6): `analyze_response` (Sentiment/Intent), Pipeline-Prompts (Body-Gen pro Empfänger) — Default
- **Bulk** (Haiku 4.5): aktuell ungenutzt im engagement, vorgesehen für Batch-Klassifikation

Pipeline-Prompts können explizit ein Modell pinnen (Feld `model` auf der
`pipeline_prompts`-Row). Wenn `null` → Standard-Klasse aus Tenant-Settings.

## Brain — Hauptmethoden

| Methode (in `brain.py`) | Zweck |
|---|---|
| `analyze_contact(enrollment, activities)` | Entscheide nächste Aktion: channel + action_type + content. Schreibt eine `PendingAction`. |
| `analyze_response(enrollment, activity)` | Bei Inbound (Email-Reply, LinkedIn-DM, …): Sentiment + Intent + new_stage + draft_response |
| `generate_module_prompts(config)` | Wizard-Hilfe beim Pipeline-Setup — generiert Default-Prompts pro aktivem Channel |
| `get_contact_context(contact_id)` | Unified context bundle (contact + company + leadgen + linkedin); siehe `app/contacts/context_loader.py` |

Brain-Prompts hartcodiert in `brain_prompts.py` (Setup-Onboarding,
Next-Step-Analyzer, Response-Analyzer, Playbook-Generator).

## Tracking & Attribution

- `Contact.tracking_hash` — pro Kontakt (auto-generiert beim Enrollment wenn
  `pipeline.tracking_config.auto_create_tracking_hash = true`)
- Klick auf Tracking-Link → User landet auf `go4.energy/{path}?ref={hash}`
- Customer-Journey-Pixel (im Webseiten-JS, **nicht** im Mail) zeichnet auf
- `JourneyEvent` mit event=`ref_link_click` — Brain bekommt das als positives
  Signal
- Open-Pixel im Mail bewusst **nicht** vorhanden (DSGVO/TTDSG)

UTM-Parameter pro Pipeline in `tracking_config` (`utm_source`, `utm_medium`,
`utm_campaign`, …), werden vom Email-Renderer in alle ausgehenden Links
injiziert.

## Auto-Actions vs. Freigabe

`engagement_pipelines.auto_actions` ist ein dict pro `action_type`:

```json
{ "email_send": false, "letter_send": false, "linkedin_message_send": true }
```

- `false` → `PendingAction.needs_approval = true`, status=`ready_for_approval`,
  taucht im Freigabe-Tab auf
- `true` → status=`approved`, Worker führt direkt aus

Default beim Pipeline-Anlegen: leeres dict → alle Aktionen brauchen Freigabe.

## API-Endpoints (Übersicht)

```
# Pipelines
GET/POST   /v1/engagement/pipelines
GET/PUT/DELETE /v1/engagement/pipelines/{id}
GET        /v1/engagement/pipelines/{id}/stats

# Per-Pipeline Prompts (NEU)
GET/POST   /v1/engagement/pipelines/{id}/prompts
PUT/DELETE /v1/engagement/pipelines/{id}/prompts/{pid}
POST       /v1/engagement/pipelines/{id}/prompts/{pid}/test

# Enrollments
GET/POST   /v1/engagement/enrollments
POST       /v1/engagement/enrollments/bulk
PUT        /v1/engagement/enrollments/{id}

# Pending Actions (Freigabe-Queue)
GET        /v1/engagement/actions
POST       /v1/engagement/actions/{id}/approve
POST       /v1/engagement/actions/{id}/complete
POST       /v1/engagement/actions/{id}/cancel

# Brain (Setup-Wizard + manueller Trigger)
POST       /v1/engagement/brain/setup-chat
POST       /v1/engagement/brain/generate-playbook
POST       /v1/engagement/brain/generate-module-prompts
POST       /v1/engagement/brain/analyze-contact
POST       /v1/engagement/brain/analyze-response

# Aktivitäten
GET/POST   /v1/engagement/activities
```

## Migrations

| Rev | Beschreibung |
|---|---|
| 014 | Initiales Engagement-Schema (pipelines, enrollments, pending_actions, contact_activities) |
| 040 | A/B-Test-Tabellen |
| 076 | `engagement_pipelines.tracking_config` (UTM + Custom Params) |
| **083** | **`pipeline_prompts`** — per-pipeline LLM-Prompts |

## Frontend

- `views/EngagementView.vue` — Pipelines-Liste (Verwaltung)
- `views/PipelineDetailView.vue` — Sub-Tabs: Übersicht, Enrollments, Aktionen, Aktivitäten, A/B-Tests, Setup
- `views/PipelineEditView.vue` — 4 Tabs: Allgemein / Zielgruppe / Produktbeschreibung / Playbook
- `components/engagement/ChannelPromptList.vue` — rechte Spalte auf der Übersicht; aufklappbare Channels mit Slots
- `components/engagement/PromptEditorDrawer.vue` — Slide-in-Editor mit Variablen-Chips + Test-Bereich
- `components/engagement/EngagementTabs.vue` — Tab-Bar (geteilt zwischen EngagementView + PipelineDetailView)
- `components/engagement/PipelineSetupWizard.vue` — KI-Chat-Setup (Brain-gestützt)
- `components/engagement/AudiencesTab.vue` — Custom-Audience-Konfiguration

## Out of Scope (geplant)

- **Brain-Integration der pipeline_prompts**: aktuell sind die Prompts in der
  DB, aber der `analyze_contact`-Pfad nutzt sie noch nicht zur Body-Generierung
  (er nutzt den hartcodierten `CONTACT_ANALYSIS_PROMPT`). Phase 2.
- **Voice-Outreach** (`phone`-Channel hat aktuell keinen Worker — nur PendingActions, manuell auszuführen)
- **A/B-Test-Auto-Switcher** (Brain wählt Variante basierend auf Reply-Rate, nicht random)
