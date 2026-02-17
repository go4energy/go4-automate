# Systemarchitektur

## Überblick

go4.automate ist eine modulare, containerisierte Plattform die auf einem einzelnen Hetzner VPS läuft. Alle Komponenten kommunizieren über ein internes Docker-Netzwerk.

```
                    ┌─────────────────────────────────┐
                    │         INTERNET                 │
                    └──────────┬──────────────────────┘
                               │
                    ┌──────────▼──────────────────────┐
                    │     Caddy 2 (Reverse Proxy)      │
                    │     Auto-HTTPS via Let's Encrypt  │
                    │     Port 80/443                   │
                    └──┬──────────┬───────────┬────────┘
                       │          │           │
            ┌──────────▼──┐ ┌────▼─────┐ ┌───▼────────┐
            │   n8n        │ │ Backend  │ │ Frontend   │
            │   :5678      │ │ :3001    │ │ (statisch) │
            │   Workflows  │ │ FastAPI  │ │ Vue 3      │
            └──────┬───────┘ └────┬─────┘ └────────────┘
                   │              │
            ┌──────▼──────────────▼───────────────────┐
            │              Docker-Netzwerk              │
            │              (go4net)                     │
            └──────┬──────────────┬───────────────────┘
                   │              │
            ┌──────▼──────┐ ┌────▼─────┐
            │ PostgreSQL   │ │ Redis    │
            │ :5432        │ │ :6379    │
            │ 2 Datenbanken│ │ Cache    │
            └──────────────┘ └──────────┘
```

## Komponenten

### 1. Caddy 2 (Reverse Proxy)
- Automatische HTTPS-Zertifikate (Let's Encrypt)
- Routing: `/` → n8n, `/api/*` → Backend, `/admin/*` → Frontend
- Zero-Config TLS, HTTP/2

### 2. n8n (Workflow-Engine)
- Orchestriert alle automatisierten Abläufe
- Cron-basierte Trigger (Content-Generierung, Ad-Optimierung, Reporting)
- Ruft Backend-API-Endpoints auf
- Sendet Benachrichtigungen (E-Mail, Slack)
- Eigene PostgreSQL-Datenbank (`go4automate_n8n`)

### 3. FastAPI Backend (Python 3.12)
- REST-API für alle Business-Logik
- Modularer Aufbau (Domain-basiert: content, ads, leads, tenants)
- LLM-Integration (Anthropic Claude, OpenAI GPT)
- Meta Graph API Client (Posting, Conversion API, Marketing API)
- Multi-Tenant Middleware (Tenant-Kontext pro Request)
- Async überall (asyncpg, httpx)

### 4. Vue 3 Frontend
- Admin-Dashboard für Content-Freigabe, Ad-Monitoring, Lead-Übersicht
- Composition API + `<script setup>`
- Tailwind CSS für Styling
- ApexCharts für Diagramme
- Pinia für State-Management

### 5. PostgreSQL 16
- Zwei Datenbanken: `go4automate` (Business) + `go4automate_n8n` (n8n intern)
- Business-Tabellen: tenants, leads, content_queue, ad_performance, email_log, conversion_events, ad_campaign_configs
- Volltextsuche, JSONB für flexible Daten

### 6. Redis 7
- Session-Cache
- Rate-Limiting für öffentliche Endpoints (Conversion API)
- Zukünftig: Queue für Background-Jobs

## Datenfluss pro Modul

### Content-Pipeline
```
n8n Cron (Mo-Fr 8:00)
  → POST /api/content/generate
    → Backend wählt Thema (Round-Robin)
    → Backend ruft Claude API auf (Prompt mit Tenant-Kontext)
    → Claude liefert JSON: {title, text, hashtags, image_prompt}
    → Backend speichert in content_queue (status: draft)
  → Notification: "Neuer Draft zur Freigabe"

Admin öffnet Dashboard
  → GET /api/content/?status=draft
  → Prüft/editiert Post
  → PATCH /api/content/{id}/approve (scheduled_at setzen)

n8n Cron (alle 15 Min)
  → GET /api/content/?status=scheduled&due=true
  → POST /api/content/{id}/publish
    → Backend ruft Meta Graph API auf
    → Facebook Page Post erstellt
    → Status → published, meta_post_id gespeichert
```

### Ad-Management Pipeline
```
Website-Besucher
  → Meta Pixel (Browser-Side) feuert Event
  → Gleichzeitig: fetch() an POST /api/ads/conversions (Server-Side)
    → Backend hasht persönliche Daten (SHA256)
    → Backend sendet an Meta Conversion API
    → Event in conversion_events gespeichert
  → Meta dedupliziert Browser + Server Events

n8n Cron (alle 4 Stunden)
  → POST /api/ads/sync
    → Backend holt Campaign Insights von Meta Marketing API
    → Berechnet CPL, CPC, CTR
    → Speichert in ad_performance

n8n Cron (täglich 20:00)
  → POST /api/ads/optimize
    → Backend lädt Campaign-Configs
    → Holt heutige Performance + aktuelles Wetter
    → Wendet Regeln an:
      - CPL zu hoch → Budget runter oder pausieren
      - CPL gut → Budget rauf
      - Sonnig → Wetter-Boost (+50%)
    → Führt Budget-Änderungen über Meta API durch
    → Notification mit Zusammenfassung

n8n Cron (Montag 9:00)
  → Holt Performance letzte 7 + 14 Tage
  → Sendet an LLM zur Analyse
  → LLM erstellt Report mit Handlungsempfehlungen
  → Email an Admin
```

### Lead-Nurturing (geplant)
```
Neuer Lead (Konfigurator, Facebook, Website)
  → Webhook an n8n
  → POST /api/leads (Backend speichert)
  → LLM bewertet Lead (Score 0-100)
  → Follow-up-Sequenz startet:
    Tag 1: SMS "Danke für Ihre Anfrage"
    Tag 3: Email mit Case Study aus der Region
    Tag 5: Email FAQ / Einwandbehandlung
    Tag 7: Email Förderungs-Info (KfW aktuell)
    Tag 10: Vertrieb wird benachrichtigt für Anruf
  → Bei Antwort/Termin: Sequenz stoppt automatisch
```

## Verzeichnisstruktur

```
/opt/go4.automate/
├── config/                     # Zentrale Konfiguration
│   ├── .env                    # Hauptkonfiguration (Credentials, API-Keys)
│   ├── tenants/                # Multi-Tenant Kundenprofile
│   │   ├── default.env         # Template für neue Kunden
│   │   └── go4energy.env       # Go4 Energy Konfiguration
│   └── templates/              # E-Mail & Content Templates
│       ├── follow-up/
│       ├── social-media/
│       └── ads/
├── docker/                     # Container-Definitionen
│   ├── docker-compose.yml
│   ├── Caddyfile
│   └── postgres-init/
│       └── 01-init.sql         # Initiales DB-Schema
├── n8n/                        # n8n Workflow-Exports
│   └── workflows/
│       ├── 01-content-pipeline.json
│       ├── 02-follow-up-sequence.json
│       ├── 03-lead-scoring.json
│       ├── 04-ads-daily-optimization.json
│       ├── 05-ads-performance-sync.json
│       └── 06-ads-weekly-report.json
├── backend/                    # FastAPI Backend (Python)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py             # App-Einstiegspunkt
│   │   ├── config.py           # Pydantic Settings
│   │   ├── database.py         # SQLAlchemy Async Engine
│   │   ├── content/            # Content-Modul
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   ├── router.py
│   │   │   └── meta_client.py
│   │   ├── ads/                # Ad-Management-Modul
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   ├── router.py
│   │   │   ├── meta_ads_client.py
│   │   │   ├── weather_service.py
│   │   │   ├── optimizer.py
│   │   │   └── hashing.py
│   │   ├── leads/              # Lead-Management-Modul
│   │   ├── tenants/            # Tenant-Verwaltung
│   │   └── services/           # Gemeinsame Services
│   │       └── llm_service.py  # LLM-Abstraktion (Claude/GPT)
│   ├── alembic/                # DB-Migrationen
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                   # Vue 3 Dashboard
│   ├── src/
│   │   ├── views/              # Seitenkomponenten
│   │   ├── components/         # UI-Komponenten
│   │   ├── stores/             # Pinia State
│   │   ├── api/                # API-Client
│   │   └── router/
│   ├── package.json
│   └── Dockerfile
├── docs/                       # Dokumentation
├── scripts/                    # Setup & Maintenance
│   ├── setup.sh
│   ├── add-tenant.sh
│   ├── backup.sh
│   └── update.sh
├── data/                       # Persistente Daten (Docker Volumes)
└── logs/
```

## Datenbank-Schema

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   tenants    │────<│     leads         │────<│    email_log      │
│─────────────│     │──────────────────│     │──────────────────│
│ tenant_id PK│     │ id PK            │     │ id PK            │
│ tenant_name  │     │ tenant_id FK     │     │ tenant_id FK     │
│ config JSONB │     │ email            │     │ lead_id FK       │
│ active       │     │ name, phone      │     │ email_type       │
└──────┬──────┘     │ source           │     │ subject          │
       │            │ score            │     │ status           │
       │            │ status           │     │ sent_at          │
       │            │ followup_step    │     └──────────────────┘
       │            │ konfigurator_data│
       │            └──────────────────┘
       │
       ├───────<┌──────────────────┐
       │        │  content_queue    │
       │        │──────────────────│
       │        │ id PK            │
       │        │ tenant_id FK     │
       │        │ platform         │
       │        │ title, content   │
       │        │ theme, hashtags  │
       │        │ status           │
       │        │ scheduled_at     │
       │        │ meta_post_id     │
       │        │ engagement JSONB │
       │        └──────────────────┘
       │
       ├───────<┌──────────────────┐     ┌──────────────────────┐
       │        │  ad_performance   │     │ ad_campaign_configs   │
       │        │──────────────────│     │──────────────────────│
       │        │ id PK            │     │ id PK                │
       │        │ tenant_id FK     │     │ tenant_id FK         │
       │        │ campaign_id      │     │ campaign_id          │
       │        │ date             │     │ target_cpl, max_cpl  │
       │        │ impressions      │     │ budget_min, max      │
       │        │ clicks, spend    │     │ weather_boost        │
       │        │ leads, cpl       │     │ auto_optimize        │
       │        │ weather_boosted  │     └──────────────────────┘
       │        └──────────────────┘
       │
       └───────<┌──────────────────┐
                │ conversion_events │
                │──────────────────│
                │ id PK            │
                │ tenant_id FK     │
                │ event_name       │
                │ event_time       │
                │ email_hash       │
                │ phone_hash       │
                │ fbc, fbp         │
                │ custom_data JSONB│
                │ sent_to_meta     │
                └──────────────────┘
```

## Sicherheitskonzept

### Datenschutz (DSGVO)
- **Self-Hosted in Deutschland:** Server bei Hetzner (Nürnberg/Falkenstein)
- **Keine Daten an Dritte:** Außer explizit konfigurierte APIs (Meta, Anthropic)
- **Persönliche Daten gehasht:** E-Mail und Telefon werden SHA256-gehasht bevor sie an Meta gehen
- **Tenant-Isolation:** Jeder Kunde sieht nur seine eigenen Daten
- **Verschlüsselung:** HTTPS (Caddy), Datenbank-Passwörter, API-Keys in .env

### Zugriffskontrolle
- n8n: Basic Auth (geplant: SSO)
- Backend API: Tenant-Header + API-Key (geplant: JWT)
- Frontend: Login + Rollen (geplant)
- Server: SSH-Key Only, Fail2ban, UFW Firewall

### Backup
- Täglicher PostgreSQL Dump (03:00 Uhr)
- n8n-Daten und Konfiguration
- 30 Tage Aufbewahrung
- Automatisiert per Cronjob

## Externe Abhängigkeiten

| Service | Verwendung | Kosten |
|---|---|---|
| Hetzner Cloud VPS | Server-Hosting | ~€10-20/Monat |
| Anthropic Claude API | Content-Generierung, Analyse | ~€20-50/Monat (nutzungsabhängig) |
| OpenAI API | Klassifikation, Scoring | ~€5-15/Monat |
| Meta Graph API | Posting, Ads, Conversion API | Kostenlos (+ Werbebudget) |
| OpenWeather API | Wetterdaten für Ad-Boost | Kostenlos (bis 1.000 Calls/Tag) |
| Brevo (Sendinblue) | E-Mail-Versand | Kostenlos bis 300 E-Mails/Tag |
| Let's Encrypt | HTTPS-Zertifikate | Kostenlos |

**Geschätzte Gesamtkosten (ohne Werbebudget):** €35-85/Monat pro Installation
