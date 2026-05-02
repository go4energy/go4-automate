# E-Mail Marketing Module

Multi-Provider E-Mail-Versand für Cold-Outreach + transaktionale Mails. Visueller Drag-&-Drop-Editor (Unlayer), HTML-Editor mit KI-Designer-Assistenten (Claude), persistente Asset-Library, Engagement-Brain-Anbindung.

Nachladbares Plattform-Modul. DSGVO-konform durch EU-Provider und konfigurierbares Encryption-Setup.

## Architektur

```
┌─ ENGAGEMENT BRAIN ────────────┐    ┌─ EMAIL MARKETING ────────────────────┐
│ Lead in Pipeline mit          │    │ Worker: process_scheduled_campaigns  │
│ channels=email                │    │         + process_sequence_enrollm.  │
│       ↓                       │    │       ↓                              │
│ LLM generiert personalisierten│    │ render_template(html, contact)       │
│ Body-Text  →  PendingAction:  │ →  │  - {{first_name}} → "Max"            │
│   module="email"              │    │  - {{llm_body}}   → suggested_content│
│   suggested_content = body    │    │  - {{tracking_link "/x"}} → URL+ref  │
│   context = {template_id, ...}│    │  - {{unsubscribe_url}} → token-URL   │
└───────────────────────────────┘    │       ↓                              │
                                     │ Provider.send_email():               │
                                     │  - Brevo (EU, Cold-Outreach)         │
                                     │  - O365 (Transactional + Replies)    │
                                     │  - AWS SES (Transactional)           │
                                     │  - SendGrid / Mailgun                │
                                     │       ↓                              │
                                     │ recipient.message_id =               │
                                     │   "<rcpt-{id}-{tok}@smartladen.de>"  │
                                     │   ← für In-Reply-To Matching         │
                                     │       ↓                              │
                                     │ log_email_activity(channel='email')  │
                                     └──────────────────────────────────────┘
```

## Dateien

| Datei | Funktion |
|---|---|
| `__manifest__.py` | Modul-Registrierung, Routes, Sidebar, AI-Prompts |
| `models.py` | 11 SQLAlchemy-Models (s.u. Datenmodell) |
| `schemas.py` | Pydantic Request/Response-Schemas |
| `router.py` | CRUD-Endpoints für Provider/Templates/Campaigns/Sequences |
| `service.py` | Business-Logik (CRUD, Recipient-Generation) |
| `worker.py` | Background-Worker für Scheduled Sends + Sequence-Steps |
| `tracking.py` | Open-Pixel, Click-Rewriting, legacy `replace_merge_tags` |
| `tracking_router.py` | Endpoints für `/t/o/{token}.gif` (Pixel) + `/t/c/{token}/{url}` (Click-Redirect) + `/t/u/{token}` (Unsubscribe) |
| `webhooks_router.py` | Provider-Callbacks (SendGrid, Mailgun, O365 — Bounces/Opens/Clicks) |
| `template_renderer.py` | **Neuer** Renderer mit Tag-Argumenten: `{{tracking_link "/path"}}`, `{{llm_body}}` (HTML-escaped), Helper `make_outreach_message_id` |
| `asset_service.py` | Upload/List/Delete von Bildern + Dateien, Storage in `data/email_assets/{tenant}/` |
| `asset_router.py` | REST-Endpoints für Asset-Library |
| `ai_chat_service.py` | Claude-basierter KI-Designer mit 4 Tools (`set_full_html`, `apply_diff`, `insert_image`, `list_assets`) |
| `ai_chat_router.py` | Per-Template-Chat-Endpoints (`POST/GET/DELETE /templates/{id}/ai-chat`) |
| `encryption.py` | Fernet-Verschlüsselung für Provider-Credentials |
| `providers/base.py` | Abstract `EmailProvider` + Factory |
| `providers/sendgrid.py` | SendGrid v3 API |
| `providers/mailgun.py` | Mailgun API |
| `providers/o365.py` | Microsoft Graph (für transaktional + Replies) |
| `providers/aws_ses.py` | **NEU**: AWS SES via boto3 + SendRawEmail (für Custom Message-ID) |
| `providers/brevo.py` | **NEU**: Brevo (Sendinblue) v3 API, EU-Hosting |

## Datenmodell

| Tabelle | Zweck |
|---|---|
| `email_providers` | Konfigurierte Versand-Provider pro Tenant. Credentials in `api_key_encrypted` (Fernet). Bei AWS SES JSON-Bundle `{access_key, secret_key, region, configuration_set}`. |
| `email_templates` | Wiederverwendbare Vorlagen mit Merge-Tags. Felder: `html_content`, `text_content`, `design_json` (Unlayer-State), `editor_mode` (`unlayer` / `plain` / `html`) |
| `email_campaigns` | Broadcast-Kampagne (1-zu-N) mit Empfänger-Auswahl, Scheduling, A/B-Test-Konfiguration, Stats |
| `email_recipients` | Pro Empfänger einer Campaign: tracking_token, sent_at, status, bounced_at, `message_id` (RFC822 für In-Reply-To-Matching), `provider_message_id` |
| `email_clicks` | Klick-Events auf Tracking-Links |
| `email_sequences` | Drip-Campaigns (mehrstufige Kampagnen) |
| `email_sequence_steps` | Einzelne Schritte einer Sequenz mit Delay |
| `email_sequence_enrollments` | Kontakt in Sequenz, mit `stopped_on_reply_at` + `stopped_reason` (für Auto-Stop bei Reply, kommt mit Reply-Poller) |
| `email_unsubscribes` | Pro Tenant: Adressen die sich abgemeldet haben |
| `email_assets` | **NEU**: Hochgeladene Bilder/Dateien pro Tenant (Storage: `data/email_assets/{tenant}/{uuid}.ext`) |
| `email_template_chats` | **NEU**: Persistente Claude-Chat-History pro Vorlage (KI-Designer-Assistant) |

## Provider

| Provider | Wann | DSGVO | Limits |
|---|---|---|---|
| **Brevo** (Sendinblue) | **Cold-Outreach** — toleranter als AWS, kein Approval-Prozess | ✓ EU (Paris) | Free: 300/Tag, Pay: 25€/Mo für 20k/Mo |
| **Office 365** (Microsoft Graph) | **Transactional + Reply-Auto-Antworten** — kommt aus echtem Postfach, saubere Thread-Continuity | ✓ EU-Tenant möglich | ~10k/Tag pro Postfach, max 30/Min |
| **AWS SES** | Massive Transactional, falls Trust-&-Safety durchgeht | ✓ Frankfurt-Region | $0.10/1k Mails, 200/Tag in Sandbox |
| **SendGrid** | Industrial-Standard für Marketing-Mails | ⚠️ US (EU Data Residency Add-On) | 100/Tag free, ~$15/Mo Paid |
| **Mailgun** | Dev-fokussiert, gute Webhooks | ⚠️ US oder EU-Region (Konfig) | 1k Mails free im ersten Monat |

**Empfohlenes Setup für `smartladen.de`:**
- Brevo → Cold-Outreach an Firmen
- O365 → Replies + transaktionale Mails

## Editor-Modi (pro Vorlage wählbar)

| Modus | Speichert in | UI |
|---|---|---|
| **Editor** (`unlayer`) | `design_json` + `html_content` | Drag-&-Drop visueller Editor (iframe von editor.unlayer.com) |
| **Reiner Text** (`plain`) | `text_content` | Textarea, beim Save zu `html_content` als `<pre>` gewrappt |
| **HTML** (`html`) | `html_content` | CodeMirror 6 Editor + Sub-Tabs Code/Vorschau + KI-Designer-Chat |

Mode-Switch zeigt eine Warning, wenn dadurch Inhalte verloren gehen würden. Inhalte aus dem alten Modus bleiben in der DB (z.B. `design_json` von einer Unlayer-Edit), aber nur der aktive Modus ist beim Versand "kanonisch".

## Merge-Tags

Im **`template_renderer.py`** (`render_template()`) bei Versand expandiert. Reine Text-Tags und Argument-Tags möglich.

| Tag | Wert |
|---|---|
| `{{first_name}}` / `{{last_name}}` / `{{full_name}}` | Aus `Contact.name` (Split bei Whitespace) |
| `{{company_name}}` | Aus `Contact.company.name` mit Fallback auf `Contact.company_name` |
| `{{position}}` | `Contact.position` |
| `{{llm_body}}` | Brain-LLM-Output, **HTML-escaped** + `\n→<br>` (Injection-Schutz) |
| `{{llm_subject}}` | Brain-LLM-generierter Subject (escaped) |
| `{{tracking_hash}}` | `Contact.tracking_hash` (Customer-Journey-Hash) |
| `{{tracking_link "/produkte"}}` | `https://go4.energy/produkte?ref={hash}&utm_source=outreach&utm_medium=email&utm_campaign={pipeline.slug}` |
| `{{unsubscribe_url}}` | One-Click-Opt-Out-URL |
| `{{impressum_block}}` | Aus Tenant-Settings (Roh-HTML, kein Escape) |

## Tracking — kein Pixel, nur Click

Bewusst **kein Open-Pixel** im Mail-Body (DSGVO/TTDSG-grenzwertig). Stattdessen:

- Tracking-Links nutzen `Contact.tracking_hash` als URL-Parameter
- User klickt → landet auf go4.energy (oder Customer-Journey-Tracker)
- Customer-Journey-JS-Pixel auf der Webseite (nicht im Mail!) erfasst den `?ref=…`-Parameter
- `JourneyEvent` mit `event=ref_link_click` wird angelegt
- Brain bekommt das als positives Signal (Lead hat Interesse)

## KI-Designer-Assistant

**Endpoints:**
- `POST /v1/emailmarketing/templates/{id}/ai-chat` — User-Message senden
- `GET /v1/emailmarketing/templates/{id}/ai-chat` — Verlauf abrufen
- `DELETE /v1/emailmarketing/templates/{id}/ai-chat` — Verlauf löschen

**Tools für Claude:**
- `set_full_html(html, summary)` — komplettes Template ersetzen
- `apply_diff(search, replace, summary)` — gezielte Änderung (`search` muss eindeutig sein)
- `insert_image(url, alt, anchor, width_px, summary)` — Bild aus Asset-Library einfügen
- `list_assets()` — Claude sieht hochgeladene Bilder mit URL + Mime + Größe

**System-Prompt** kennt die DSGVO-/UWG-Pflicht-Tags (`{{first_name}}`, `{{llm_body}}`, `{{unsubscribe_url}}`, `{{impressum_block}}`) und Cross-Client-HTML-Best-Practices (Inline-CSS, Tabellen-Layout, max-width 600px).

**Persistenz:** Jede Message (user/assistant/tool) wird in `email_template_chats` als eigene Row gespeichert. Verlauf bleibt beim erneuten Öffnen der Vorlage.

## Asset-Library

**Storage:** `backend/data/email_assets/{tenant_id}/{uuid}_{slug}.{ext}`  
**Static-Serving:** `/api/static/email-assets/{tenant_id}/{filename}` (FastAPI StaticFiles in `main.py`)  
**Limits:** 5 MB pro Datei, Mime-Whitelist: JPG/PNG/GIF/WebP/SVG/PDF  
**Endpoints:** `POST/GET/DELETE /v1/emailmarketing/assets`

## Reply-Verarbeitung (vorbereitet, Implementation kommt)

`email_recipients.message_id` und `email_sequence_enrollments.stopped_on_reply_at` sind bereits in der DB. Der Worker setzt beim Send einen Custom Message-ID (`<rcpt-{recipient.id}-{token}@smartladen.de>`) — daran wird der Reply-Poller später die Antwort matchen.

**Geplant:**
1. Microsoft-Graph-Polling-Worker → liest neue Mails aus `info@smartladen.de` Outlook-Inbox
2. Match per `In-Reply-To`-Header → `email_recipients` → Contact → Engagement-Pipeline
3. Brain analysiert Sentiment + Intent → setzt `pipeline_enrollment.stage = engaged`
4. `email_sequence_enrollments.stopped_on_reply_at = NOW()` → Worker skippt weitere Steps

## Konfiguration

### Umgebungsvariablen (`.env`)

```env
# Master-Encryption-Key für Provider-Credentials in DB (Fernet)
EMAIL_ENCRYPTION_KEY=<base64-32-byte-key>
REQUIRE_ENCRYPTION_KEYS=true     # Production: hart abbrechen wenn Key fehlt

# Anthropic für KI-Designer-Chat
ANTHROPIC_API_KEY=sk-ant-...

# Microsoft Graph (für O365-Provider + Reply-Polling, kommt mit Reply-Poller-Phase)
MS_GRAPH_CLIENT_ID=
MS_GRAPH_TENANT_ID=
MS_GRAPH_CLIENT_SECRET=
```

Encryption-Key generieren: `python -m app.emailmarketing.encryption`

### Provider anlegen

UI: `/emailmarketing/providers/new`. Pro Provider-Type unterschiedliche Felder; bei AWS SES werden 4 Felder (Access Key + Secret + Region + ConfigurationSet) als JSON in `api_key_encrypted` gebündelt.

## API-Endpoints

```
# Provider
GET    /v1/emailmarketing/providers
POST   /v1/emailmarketing/providers
GET    /v1/emailmarketing/providers/{id}
PUT    /v1/emailmarketing/providers/{id}
DELETE /v1/emailmarketing/providers/{id}
POST   /v1/emailmarketing/providers/{id}/verify

# Templates
GET    /v1/emailmarketing/templates
POST   /v1/emailmarketing/templates
GET    /v1/emailmarketing/templates/{id}
PUT    /v1/emailmarketing/templates/{id}
DELETE /v1/emailmarketing/templates/{id}
POST   /v1/emailmarketing/templates/preview

# KI-Chat (per Template)
GET    /v1/emailmarketing/templates/{id}/ai-chat
POST   /v1/emailmarketing/templates/{id}/ai-chat
DELETE /v1/emailmarketing/templates/{id}/ai-chat

# Assets
GET    /v1/emailmarketing/assets
POST   /v1/emailmarketing/assets   (multipart/form-data)
DELETE /v1/emailmarketing/assets/{id}

# Campaigns + Sequences (CRUD via router.py)
# Tracking + Webhooks (tracking_router.py + webhooks_router.py)
```

## Migrations

| Rev | Beschreibung |
|---|---|
| 044/045 | Initial Email-Marketing-Tabellen |
| 078 | `email_recipients.message_id` (In-Reply-To-Matching) + `email_sequence_enrollments.stopped_on_reply_at|stopped_reason` + `email_templates.design_json` |
| 079 | `email_templates.editor_mode` (`unlayer` / `plain` / `html`) |
| 080 | `email_assets` + `email_template_chats` (KI-Persistenz) |

## Tests

```bash
pytest tests/test_email_template_renderer.py    # Merge-Tag-Engine + Tracking-Link + Message-ID
pytest tests/test_aws_ses_provider.py           # AWS SES SendRawEmail mit Mock
pytest tests/test_brevo_provider.py             # Brevo v3 API mit httpx-mock
```

Aktuell: 21 + 17 + 12 = **50 grüne Tests**.

## Frontend

- `views/EmailMarketingView.vue` — Module-Übersicht mit Tabs (Sequenzen / Templates / Provider / Freigabe) + Onboarding-Karte
- `views/EmailProviderEditView.vue` — Provider-Konfig (5 Provider-Types, AWS-spezifische Felder bei aws_ses)
- `views/EmailTemplateEditView.vue` — Template-Editor mit Mode-Selector
- `components/email/UnlayerEmailEditor.vue` — Drag-&-Drop-Editor (vue-email-editor Wrapper)
- `components/email/HtmlCodeEditor.vue` — CodeMirror 6 mit HTML-Syntax-Highlighting + Dark-Mode
- `components/email/AssetLibrary.vue` — Bild-Upload mit Drag-Drop + Thumbnail-Grid
- `components/email/EmailDesignerChat.vue` — KI-Chat im HTML-Modus mit persistenter History

## DSGVO / UWG-Hinweise

- **Cold-Outreach an deutsche B2B-Empfänger** ist rechtlich heikel: § 7 UWG verlangt Einwilligung, B2B-Mutmaßlichkeitsregel begrenzt
- Pflicht in jeder Mail: Impressum, Opt-Out (One-Click), Datenschutz-Hinweis
- Tracking-Pixel im Mail bewusst vermieden (TTDSG)
- AWS Acceptable Use Policy verbietet "unsolicited mass email" — Brevo akzeptiert seriöses B2B-Outreach mit Opt-Out
- Empfänger-Listen müssen pre-qualifiziert sein, **keine purchased lists**
