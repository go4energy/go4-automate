# go4-automate: Engagement Brain System

> **Umfassende Dokumentation des Multi-Channel Engagement Systems**
>
> Version: 1.0.0
> Datum: 2026-03-07
> Status: Phase 1 implementiert, Phase 2-8 geplant

---

## Executive Summary

Das **Engagement Brain System** ist ein KI-gesteuertes Multi-Channel-Marketing-Automatisierungssystem, das Kontakte intelligent über verschiedene Kanäle anspricht und dabei:

- **Personalisiert**: Jede Nachricht wird auf den Kontakt zugeschnitten
- **Adaptiv**: Reagiert auf Antworten und passt die Strategie an
- **Kanalübergreifend**: LinkedIn, Email, Telefon, Brief, WhatsApp, Meta Ads
- **Messbar**: Vollständige Attribution von Erstkontakt bis Conversion
- **Skalierbar**: Ein System für beliebig viele Produkt-Pipelines

**Das Brain ist das "Geheimnis"** - die zentrale KI-Intelligenz, die nicht einfach nachgebaut werden kann.

---

## Inhaltsverzeichnis

1. [Vision & Problemstellung](#1-vision--problemstellung)
2. [Systemarchitektur](#2-systemarchitektur)
3. [Implementierte Komponenten (Phase 1)](#3-implementierte-komponenten-phase-1)
4. [Geplante Komponenten (Phase 2-8)](#4-geplante-komponenten-phase-2-8)
5. [Cross-Channel Attribution & Tracking](#5-cross-channel-attribution--tracking)
6. [Meta-Modul](#6-meta-modul)
7. [Technische Spezifikation](#7-technische-spezifikation)
8. [Use Cases & Beispiele](#8-use-cases--beispiele)
9. [Wettbewerbsvorteile](#9-wettbewerbsvorteile)
10. [Roadmap](#10-roadmap)

---

## 1. Vision & Problemstellung

### Das Problem

Unternehmen nutzen heute viele Kanäle für Kundenakquise:
- LinkedIn für B2B-Kontakte
- Email-Marketing für Nurturing
- Telefonakquise für Qualifizierung
- Meta/Google Ads für Reichweite
- WhatsApp für direkte Kommunikation

**Die Herausforderungen:**
- Keine zentrale Sicht auf alle Interaktionen
- Manuelle Koordination zwischen Kanälen
- Keine Personalisierung basierend auf bisherigem Verhalten
- Attribution unklar: Welcher Kanal führte zum Abschluss?
- Skalierung nur durch mehr Personal möglich

### Die Lösung: Engagement Brain

Ein **zentrales KI-Brain**, das:
1. Alle Kanäle orchestriert
2. Den optimalen nächsten Schritt pro Kontakt entscheidet
3. Automatisch personalisierte Inhalte generiert
4. Bei Antworten adaptiv reagiert
5. Vollständige Attribution ermöglicht

```
Traditionell:                    Mit Engagement Brain:

LinkedIn ───┐                    LinkedIn ───┐
Email ──────┤── Manuell ──▶     Email ──────┤
Telefon ────┤   koordiniert      Telefon ────┼──▶ BRAIN ──▶ Optimale
Ads ────────┤                    Ads ────────┤      │       Sequenz
WhatsApp ───┘                    WhatsApp ───┘      │
                                                    ▼
                                              Conversion
```

---

## 2. Systemarchitektur

### Überblick

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        ENGAGEMENT BRAIN SYSTEM                          │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                     PRODUKT-PIPELINES                              │ │
│  │                                                                    │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │ │
│  │  │ Solar KMU   │  │ Wärmepumpen │  │ Beratung    │  ...          │ │
│  │  │             │  │             │  │             │               │ │
│  │  │ Channels:   │  │ Channels:   │  │ Channels:   │               │ │
│  │  │ LI,Email,   │  │ Meta,WA,    │  │ LI,Email,   │               │ │
│  │  │ Brief,Phone │  │ Brief       │  │ Phone       │               │ │
│  │  │             │  │             │  │             │               │ │
│  │  │ Ziel:       │  │ Ziel:       │  │ Ziel:       │               │ │
│  │  │ Vor-Ort     │  │ Demo        │  │ Angebot     │               │ │
│  │  │ Termin      │  │             │  │             │               │ │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘               │ │
│  │         └────────────────┼────────────────┘                       │ │
│  └──────────────────────────┼────────────────────────────────────────┘ │
│                             ▼                                           │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                      ZENTRALES BRAIN                               │ │
│  │                                                                    │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │ │
│  │  │ Setup Layer │  │Runtime Layer│  │ Knowledge   │               │ │
│  │  │             │  │             │  │ Layer       │               │ │
│  │  │ • Pipeline  │  │ • Analyzer  │  │             │               │ │
│  │  │   Onboard   │  │ • Dispatcher│  │ • Pipelines │               │ │
│  │  │ • Prereq    │  │ • Events    │  │ • Activities│               │ │
│  │  │   Check     │  │ • Stats     │  │ • Patterns  │               │ │
│  │  │ • Prompt    │  │             │  │ • Prompts   │               │ │
│  │  │   Generator │  │             │  │             │               │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘               │ │
│  └───────────────────────────┬───────────────────────────────────────┘ │
│                              │                                          │
│         ┌────────────────────┼────────────────────┐                    │
│         ▼                    ▼                    ▼                    │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐            │
│  │  LinkedIn   │      │   Email     │      │    Meta     │            │
│  │  Modul      │      │   Modul     │      │   Modul     │            │
│  │             │      │             │      │             │            │
│  │ • Scraping  │      │ • Campaigns │      │ • Pixel     │            │
│  │ • Messages  │      │ • Templates │      │ • CAPI      │            │
│  │ • Connect   │      │ • Sequences │      │ • Audiences │            │
│  │ • Inbox     │      │ • Tracking  │      │ • Lead Ads  │            │
│  └──────┬──────┘      └──────┬──────┘      └──────┬──────┘            │
│         │                    │                    │                    │
│  ┌──────┴──────┐      ┌──────┴──────┐      ┌──────┴──────┐            │
│  │  WhatsApp   │      │   Telefon   │      │  Post-Mail  │            │
│  │  Modul      │      │   (CRM)     │      │   Modul     │            │
│  └─────────────┘      └─────────────┘      └─────────────┘            │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                     ZENTRALE DATENBANK                             │ │
│  │                                                                    │ │
│  │  contacts │ pipelines │ enrollments │ actions │ activities        │ │
│  └───────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

### Brain-Architektur (3 Layer)

#### Setup-Layer
- **Pipeline-Onboarding**: Chat-basierte Einrichtung neuer Pipelines
- **Prerequisites Analyzer**: Prüft ob alle Module/APIs konfiguriert sind
- **Prompt Generator**: Erstellt modul-spezifische KI-Prompts

#### Runtime-Layer
- **Contact Analyzer**: Entscheidet nächsten Schritt pro Kontakt
- **Action Dispatcher**: Delegiert Aufgaben an Module
- **Event Handler**: Reagiert auf eingehende Nachrichten
- **Statistics Engine**: Conversion-Tracking und Optimierung

#### Knowledge-Layer
- **Alle Pipelines + Playbooks**
- **Alle Modul-Prompts** (vom Brain selbst generiert)
- **Komplette Contact-Historie**
- **Erfolgs-Patterns** (was funktioniert?)

---

## 3. Implementierte Komponenten (Phase 1)

### Status: ✅ Vollständig implementiert

### 3.1 Datenbank-Migrationen

**engagement_pipelines** (038)
```sql
CREATE TABLE engagement_pipelines (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR NOT NULL,

    -- Basis
    name VARCHAR NOT NULL,
    slug VARCHAR NOT NULL UNIQUE,

    -- Produkt
    product_name VARCHAR,
    product_description TEXT,
    target_audience TEXT,

    -- Konfiguration
    channels JSONB DEFAULT '[]',      -- ["linkedin", "email", "phone"]
    goal VARCHAR,                      -- vor_ort_termin, demo, angebot
    playbook TEXT,                     -- Richtlinien für das Brain
    tone_of_voice VARCHAR DEFAULT 'professionell',
    min_days_between_touches INTEGER DEFAULT 3,
    auto_actions JSONB DEFAULT '{}',   -- Welche Aktionen auto-approved

    -- Status
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);
```

**pipeline_enrollments** (039)
```sql
CREATE TABLE pipeline_enrollments (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR NOT NULL,
    contact_id INTEGER REFERENCES contacts(id),
    pipeline_id INTEGER REFERENCES engagement_pipelines(id),

    -- Quelle
    source_module VARCHAR,             -- linkedin, meta, website, manual
    source_campaign VARCHAR,
    source_context JSONB,

    -- Funnel-Position
    stage VARCHAR DEFAULT 'lead',      -- lead, contacted, engaged, qualified, converted, lost
    status VARCHAR DEFAULT 'active',   -- active, paused, completed, stopped

    -- Tracking
    touch_count INTEGER DEFAULT 0,
    last_touch_at TIMESTAMP,
    last_response_at TIMESTAMP,

    -- Abschluss
    outcome VARCHAR,
    enrolled_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);
```

**pending_actions** (040)
```sql
CREATE TABLE pending_actions (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR NOT NULL,
    contact_id INTEGER REFERENCES contacts(id),
    pipeline_id INTEGER REFERENCES engagement_pipelines(id),
    enrollment_id INTEGER REFERENCES pipeline_enrollments(id),

    -- Aktion
    module VARCHAR NOT NULL,           -- linkedin, email, phone, etc.
    action_type VARCHAR NOT NULL,      -- send_message, send_email, make_call
    context JSONB,                     -- Alles was das Modul braucht
    suggested_content TEXT,            -- Vorschlag vom Brain

    -- Priorisierung
    priority VARCHAR DEFAULT 'normal', -- urgent, high, normal, low
    due_at TIMESTAMP,

    -- Workflow
    needs_approval BOOLEAN DEFAULT true,
    status VARCHAR DEFAULT 'pending',  -- pending, ready_for_approval, approved, completed, failed
    approved_by INTEGER REFERENCES users(id),
    approved_at TIMESTAMP,

    -- Ergebnis
    result JSONB,
    error_message TEXT,

    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);
```

**contact_activities** (041)
```sql
CREATE TABLE contact_activities (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR NOT NULL,
    contact_id INTEGER REFERENCES contacts(id),
    pipeline_id INTEGER REFERENCES engagement_pipelines(id),
    enrollment_id INTEGER REFERENCES pipeline_enrollments(id),

    -- Event
    channel VARCHAR NOT NULL,          -- linkedin, email, phone, website, whatsapp
    activity_type VARCHAR NOT NULL,    -- message_sent, message_received, call_made, etc.
    direction VARCHAR,                 -- outbound, inbound

    -- Inhalt
    subject VARCHAR,
    content TEXT,

    -- Referenz
    source_module VARCHAR,
    source_action_id INTEGER,

    -- KI-Analyse
    sentiment VARCHAR,                 -- positive, neutral, negative
    detected_intent VARCHAR,           -- interested, question, objection, etc.

    -- Meta
    status VARCHAR,                    -- sent, delivered, opened, replied
    performed_by INTEGER REFERENCES users(id),
    performed_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 3.2 Backend-Module

**Dateien:**
```
backend/app/engagement/
├── __init__.py
├── __manifest__.py      # Modul-Konfiguration + AI-Prompts
├── models.py            # SQLAlchemy Models
├── schemas.py           # Pydantic Schemas
├── service.py           # Business Logic (750+ Zeilen)
└── router.py            # REST API Endpoints
```

**API-Endpoints:**
```
# Dashboard
GET  /api/v1/engagement/dashboard

# Pipelines
GET  /api/v1/engagement/pipelines
POST /api/v1/engagement/pipelines
GET  /api/v1/engagement/pipelines/{id}
PUT  /api/v1/engagement/pipelines/{id}
DELETE /api/v1/engagement/pipelines/{id}
GET  /api/v1/engagement/pipelines/{id}/stats
GET  /api/v1/engagement/pipelines/{id}/funnel

# Enrollments
GET  /api/v1/engagement/enrollments
POST /api/v1/engagement/enrollments
POST /api/v1/engagement/enrollments/bulk
GET  /api/v1/engagement/enrollments/{id}
PUT  /api/v1/engagement/enrollments/{id}
POST /api/v1/engagement/enrollments/{id}/unenroll

# Actions
GET  /api/v1/engagement/actions
GET  /api/v1/engagement/actions/approval-queue
GET  /api/v1/engagement/actions/{id}
POST /api/v1/engagement/actions/{id}/approve
POST /api/v1/engagement/actions/{id}/complete
POST /api/v1/engagement/actions/{id}/cancel

# Activities
GET  /api/v1/engagement/activities/contact/{contact_id}
GET  /api/v1/engagement/activities/enrollment/{enrollment_id}
GET  /api/v1/engagement/activities/recent
POST /api/v1/engagement/activities
```

### 3.3 Frontend-Komponenten

**Dateien:**
```
frontend/src/
├── api/engagement.js           # API Client
├── stores/engagement.js        # Pinia Store
└── views/
    ├── EngagementView.vue      # Hauptview mit 6 Tabs
    ├── PipelineEditView.vue    # Pipeline erstellen/bearbeiten
    └── PipelineDetailView.vue  # Pipeline-Details + Enrollments
```

**EngagementView Tabs:**
1. **Dashboard** - KPIs, Pipeline-Performance, Recent Activities
2. **Pipelines** - Alle Pipelines mit Status und Channels
3. **Enrollments** - Kontakte in Pipelines mit Stage/Status
4. **Aktionen** - Alle pending_actions mit Filterung
5. **Freigabe** - Approval Queue mit Approve/Reject
6. **Aktivitäten** - Timeline aller Interaktionen

### 3.4 Tests

**11 Backend-Tests** (alle bestanden):
- `test_engagement_dashboard`
- `test_create_pipeline`
- `test_list_pipelines`
- `test_pipeline_crud`
- `test_pipeline_stats`
- `test_pipeline_funnel`
- `test_list_enrollments`
- `test_list_actions`
- `test_approval_queue`
- `test_recent_activities`
- `test_duplicate_pipeline_slug`

---

## 4. Geplante Komponenten (Phase 2-8)

### Phase 2: Activity-System
- Activity-Logging Service (zentral für alle Module)
- Helper: `log_activity()` für LinkedIn, Email, CRM
- ContactDetailView: Engagement-Timeline-Tab

### Phase 3: Brain Setup-Layer
- Pipeline-Onboarding via Chat-Dialog
- Prerequisites Analyzer (Module installiert? APIs konfiguriert?)
- Playbook Generator (KI erstellt Richtlinien)
- Modul-Prompt Generator (KI schreibt Prompts für Module)

### Phase 4: Brain Runtime-Layer
- Contact Analyzer (entscheidet nächsten Schritt)
- Action Dispatcher (erstellt pending_actions)
- Worker für periodische Verarbeitung
- Event-Handler für eingehende Messages

### Phase 5: Modul-Integration
- LinkedIn: Pending Actions Queue, Modul-Brain, Freigabe-UI
- Email: Analog
- CRM/Phone: Anruf-Queue + Ergebnis-Eintragung

### Phase 6: Engagement UI
- Dashboard mit KI-Insights
- Pipeline-Detail mit Funnel-Visualisierung
- Contact Engagement-Tab mit KI-Empfehlung

### Phase 7: Erweiterungen
- Post-Mail Modul (Brief-Generierung)
- Statistics Engine
- Optimization Engine
- A/B Testing

### Phase 8: Website-Tracking & Cross-Channel Attribution
- Tracking-Links mit verschlüsselten Contact-IDs
- Website-Pixel (JavaScript)
- Webhook-Endpoint für Events
- Meta Conversions API
- Custom Audience Sync
- Attribution-Dashboard

---

## 5. Cross-Channel Attribution & Tracking

### Das Problem

Wenn ein Kontakt über LinkedIn angesprochen wird und später die Website besucht:
- Wie wissen wir, dass es derselbe Kontakt ist?
- Wie messen wir, welcher Kanal zur Conversion führte?
- Wie können wir diese Person gezielt mit Ads ansprechen?

### Die Lösung: Tracking-Links + Cookie + Meta CAPI

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    CROSS-CHANNEL ATTRIBUTION FLOW                       │
│                                                                         │
│  SCHRITT 1: Outreach mit Tracking-Link                                 │
│  ════════════════════════════════════════                              │
│                                                                         │
│  LinkedIn-Nachricht an Max Müller:                                     │
│  "Schauen Sie sich unsere Lösung an: go4energy.de/solar?ref=abc123"   │
│                                                                         │
│  Der Link enthält:                                                      │
│  • ref=abc123 (verschlüsselte Contact-ID)                              │
│  • utm_source=linkedin                                                  │
│  • utm_campaign=solar-kmu                                               │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  SCHRITT 2: Website-Besuch                                              │
│  ═════════════════════════                                              │
│                                                                         │
│  Max klickt auf den Link → Website lädt                                │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  go4-pixel.js (auf der Website eingebunden)                     │   │
│  │                                                                  │   │
│  │  1. Liest ref=abc123 aus URL                                    │   │
│  │  2. Setzt Cookie: go4_cid=abc123 (1 Jahr gültig)               │   │
│  │  3. Sendet Event an Backend: { event: "page_view", ref: abc123 }│   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Meta Pixel (parallel)                                          │   │
│  │                                                                  │   │
│  │  Feuert PageView → Max ist jetzt in Retargeting-Audience       │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  SCHRITT 3: Backend-Verarbeitung                                        │
│  ═══════════════════════════════                                        │
│                                                                         │
│  POST /api/v1/engagement/pixel                                         │
│  { event: "page_view", ref: "abc123", url: "/solar", ... }            │
│                                                                         │
│  Backend:                                                               │
│  1. Dekodiert ref=abc123 → Contact ID 456 (Max Müller)                │
│  2. Loggt Activity: "Max hat /solar besucht"                           │
│  3. Updated Enrollment Stage: contacted → engaged                      │
│  4. Sendet an Meta CAPI (mit gehashter Email)                         │
│  5. Triggert Brain: "Was ist der nächste Schritt?"                    │
│                                                                         │
│  Brain entscheidet: "Max hat Interesse gezeigt → Anruf in 24h"        │
│  → Erstellt pending_action für CRM/Phone                               │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  SCHRITT 4: Wiedererkennung bei späterem Besuch                        │
│  ══════════════════════════════════════════════                        │
│                                                                         │
│  2 Wochen später: Max tippt go4energy.de direkt ein                   │
│                                                                         │
│  go4-pixel.js:                                                          │
│  1. Kein ref in URL                                                     │
│  2. ABER: Cookie go4_cid=abc123 vorhanden!                             │
│  3. Sendet Event: { event: "page_view", ref: "abc123" (aus Cookie) }  │
│                                                                         │
│  → WIR WISSEN: Das ist wieder Max Müller!                              │
│  → Activity wird geloggt                                                │
│  → Brain kann reagieren                                                 │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  SCHRITT 5: Gezielte Werbung                                           │
│  ═══════════════════════════                                           │
│                                                                         │
│  Custom Audience in Meta:                                               │
│  • Alle Contacts mit Stage "engaged" oder "qualified"                  │
│  • Emails werden gehasht hochgeladen                                    │
│  • Meta matcht gegen User-Datenbank                                    │
│                                                                         │
│  → Max sieht personalisierte Ads auf Facebook/Instagram               │
│  → Lookalike Audience erreicht ähnliche Personen                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Tracking-Link Struktur

```
https://go4energy.de/solar?ref=enc_abc123&utm_source=linkedin&utm_campaign=solar-kmu
│                    │     │              │                    │
│                    │     │              │                    └── Kampagne
│                    │     │              └── Quelle (LinkedIn, Email, etc.)
│                    │     └── Verschlüsselte Contact-ID
│                    └── Ziel-Seite
└── Domain
```

### Website-Pixel Code

```javascript
// go4-pixel.js - Einbinden auf Kunden-Website
(function() {
    const GO4_ENDPOINT = 'https://api.go4energy.de/api/v1/engagement/pixel';
    const COOKIE_NAME = 'go4_cid';
    const COOKIE_DAYS = 365;

    // Cookie-Funktionen
    function setCookie(value) {
        const expires = new Date(Date.now() + COOKIE_DAYS * 864e5).toUTCString();
        document.cookie = `${COOKIE_NAME}=${value}; expires=${expires}; path=/; SameSite=Lax`;
    }

    function getCookie() {
        const match = document.cookie.match(new RegExp('(^| )' + COOKIE_NAME + '=([^;]+)'));
        return match ? match[2] : null;
    }

    // URL-Parameter auslesen
    const params = new URLSearchParams(window.location.search);
    let ref = params.get('ref');
    const utmSource = params.get('utm_source');
    const utmCampaign = params.get('utm_campaign');

    // Wenn ref in URL → Cookie setzen
    if (ref) {
        setCookie(ref);
    } else {
        // Sonst: Cookie lesen
        ref = getCookie();
    }

    // Event senden
    function trackEvent(eventType, data = {}) {
        const payload = {
            event: eventType,
            ref: ref,
            utm_source: utmSource,
            utm_campaign: utmCampaign,
            url: window.location.href,
            path: window.location.pathname,
            referrer: document.referrer,
            timestamp: new Date().toISOString(),
            ...data
        };

        // Beacon API für zuverlässiges Tracking
        if (navigator.sendBeacon) {
            navigator.sendBeacon(GO4_ENDPOINT, JSON.stringify(payload));
        } else {
            fetch(GO4_ENDPOINT, {
                method: 'POST',
                body: JSON.stringify(payload),
                keepalive: true
            });
        }
    }

    // Automatisch Page View tracken
    trackEvent('page_view');

    // Globale Funktion für Custom Events
    window.go4Track = function(event, data) {
        trackEvent(event, data);
    };
})();
```

### Zusätzliche Events

```javascript
// Formular abgeschickt
document.querySelector('form#contact').addEventListener('submit', function() {
    go4Track('form_submit', { form: 'contact' });
});

// CTA geklickt
document.querySelector('.cta-termin').addEventListener('click', function() {
    go4Track('cta_click', { cta: 'termin' });
});

// Download
document.querySelector('.download-pdf').addEventListener('click', function() {
    go4Track('download', { file: 'produktinfo.pdf' });
});
```

---

## 6. Meta-Modul

### Übersicht

Ein dediziertes Modul für die Integration mit Meta (Facebook/Instagram):

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           META MODUL                                    │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  PIXEL & CONVERSIONS API                                        │   │
│  │                                                                  │   │
│  │  • Meta Pixel Konfiguration                                     │   │
│  │  • Server-Side Tracking (CAPI)                                  │   │
│  │  • Event-Mapping (PageView, Lead, Purchase)                     │   │
│  │  • Deduplication (Pixel + CAPI)                                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  AUDIENCES                                                       │   │
│  │                                                                  │   │
│  │  • Custom Audiences verwalten                                   │   │
│  │  • Auto-Sync mit Engagement-Pipelines                           │   │
│  │  • Lookalike Audiences erstellen                                │   │
│  │  • Segment-basierte Audiences                                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  KAMPAGNEN (Read + Optional Write)                              │   │
│  │                                                                  │   │
│  │  • Kampagnen-Übersicht                                          │   │
│  │  • Performance-Metriken (Spend, Impressions, Clicks, Leads)    │   │
│  │  • ROI-Tracking                                                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  LEAD ADS                                                        │   │
│  │                                                                  │   │
│  │  • Webhook für eingehende Leads                                 │   │
│  │  • Auto-Import in Contacts                                      │   │
│  │  • Auto-Enrollment in Pipeline                                  │   │
│  │  • Sofortige Brain-Aktivierung                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Datenmodell

```python
class MetaAccount(Base):
    """Meta Business Account."""
    id: int
    tenant_id: str
    name: str
    account_id: str        # Meta Ad Account ID
    pixel_id: str
    access_token: str      # Encrypted
    is_active: bool


class MetaAudience(Base):
    """Custom Audiences."""
    id: int
    tenant_id: str
    meta_account_id: int

    audience_id: str       # Meta's ID
    name: str
    audience_type: str     # custom, lookalike

    # Auto-Sync
    sync_source: str       # pipeline, segment
    sync_pipeline_id: int
    sync_stages: list[str] # ["engaged", "qualified"]
    auto_sync: bool
    last_synced_at: datetime

    approximate_size: int


class MetaLeadForm(Base):
    """Lead Ad Formulare."""
    id: int
    tenant_id: str
    meta_account_id: int

    form_id: str
    name: str

    # Auto-Import
    auto_import: bool
    import_to_pipeline_id: int
    import_stage: str = "lead"
```

### Meta Conversions API

```python
class MetaConversionsAPI:
    """Server-side Tracking zu Meta."""

    async def send_event(self, event_name: str, contact: Contact, data: dict = None):
        """Sendet Event mit gehashten PII."""

        user_data = {}
        if contact.email:
            user_data["em"] = sha256(contact.email.lower())
        if contact.phone:
            user_data["ph"] = sha256(contact.phone)
        if contact.first_name:
            user_data["fn"] = sha256(contact.first_name.lower())

        payload = {
            "data": [{
                "event_name": event_name,
                "event_time": int(time.time()),
                "action_source": "website",
                "user_data": user_data,
                "custom_data": data or {}
            }],
            "access_token": self.access_token
        }

        await self.client.post(self.endpoint, json=payload)
```

### Lead Ads → Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     LEAD AD → PIPELINE FLOW                             │
│                                                                         │
│  1. User sieht Ad auf Facebook/Instagram                               │
│     "Kostenlose Beratung zu Solaranlagen"                              │
│                                    │                                    │
│                                    ▼                                    │
│  2. User füllt Lead-Formular aus                                       │
│     Name: Max Müller                                                    │
│     Email: max@example.com                                              │
│     Telefon: +49 170 1234567                                           │
│                                    │                                    │
│                                    ▼                                    │
│  3. Meta sendet Webhook                                                 │
│     POST /api/v1/meta/webhooks/leads                                   │
│     { form_id: "123", lead_data: {...} }                               │
│                                    │                                    │
│                                    ▼                                    │
│  4. Backend verarbeitet                                                 │
│     • Erstellt Contact (oder findet existierenden)                     │
│     • Enrolled in konfigurierte Pipeline                               │
│     • Loggt Activity: "lead_ad_submitted"                              │
│     • Triggert Brain                                                    │
│                                    │                                    │
│                                    ▼                                    │
│  5. Brain entscheidet erste Aktion                                     │
│     "Neuer Lead von Meta Ads → Sofort anrufen (Priorität: hoch)"      │
│     → Erstellt pending_action für Telefon                              │
│                                    │                                    │
│                                    ▼                                    │
│  6. Vertrieb sieht Aufgabe in Freigabe-Queue                          │
│     "Max Müller anrufen - Lead von Solar-Kampagne"                     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Technische Spezifikation

### Tech Stack

| Komponente | Technologie |
|------------|-------------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.x |
| Frontend | Vue 3, Composition API, Pinia |
| Datenbank | PostgreSQL 16 |
| Cache | Redis 7 |
| AI/LLM | Claude API (Anthropic) |
| Pixel | Vanilla JavaScript |
| Hosting | Docker + Caddy |

### Deployment-Architektur

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         DEPLOYMENT                                      │
│                                                                         │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐              │
│  │   Caddy     │     │   Backend   │     │  PostgreSQL │              │
│  │   (Proxy)   │────▶│   FastAPI   │────▶│             │              │
│  │   :443      │     │   :8002     │     │   :5432     │              │
│  └─────────────┘     └─────────────┘     └─────────────┘              │
│         │                   │                                          │
│         │            ┌──────┴──────┐                                   │
│         │            ▼             ▼                                   │
│         │     ┌─────────────┐ ┌─────────────┐                         │
│         │     │   Redis     │ │   n8n       │                         │
│         │     │   :6379     │ │   :5678     │                         │
│         │     └─────────────┘ └─────────────┘                         │
│         │                                                              │
│         ▼                                                              │
│  ┌─────────────┐                                                       │
│  │  Frontend   │                                                       │
│  │   Vue 3     │                                                       │
│  │   :8081     │                                                       │
│  └─────────────┘                                                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### API-Design

Alle Endpoints folgen REST-Konventionen:
- `GET /resources` - Liste
- `POST /resources` - Erstellen
- `GET /resources/{id}` - Einzeln
- `PUT /resources/{id}` - Update
- `DELETE /resources/{id}` - Löschen

Spezielle Aktionen:
- `POST /resources/{id}/action` - z.B. `/approve`, `/cancel`

### Sicherheit

- **Authentication**: JWT Tokens
- **Multi-Tenancy**: Alle Daten nach `tenant_id` isoliert
- **Encryption**: Sensitive Daten (API Keys) verschlüsselt
- **CORS**: Nur erlaubte Origins
- **Rate Limiting**: Schutz vor Missbrauch
- **DSGVO**:
  - Cookie-Consent erforderlich
  - PII wird gehasht an Meta gesendet
  - Daten können gelöscht werden

---

## 8. Use Cases & Beispiele

### Use Case 1: Solar-Vertrieb für KMU

**Szenario:** Energieberater will KMU für Solaranlagen akquirieren.

**Setup:**
1. Pipeline erstellen: "Solar KMU"
2. Channels: LinkedIn, Email, Telefon
3. Ziel: Vor-Ort-Termin
4. Playbook: "Fokus auf Energiekosten-Ersparnis, ROI betonen"

**Flow:**
```
Tag 1:  LinkedIn Connection Request an Geschäftsführer
        [Automatisch, personalisiert auf Firma]

Tag 3:  Connection akzeptiert → Brain informiert
        → Nächste Aktion: LinkedIn-Nachricht

Tag 4:  LinkedIn-Nachricht mit Tracking-Link
        "Schauen Sie sich unsere Fallstudie an: [Link]"

Tag 5:  Kontakt klickt Link → Website-Besuch
        → Stage: engaged
        → Brain: "Interesse erkannt → Anruf empfohlen"

Tag 6:  Vertrieb ruft an (aus Freigabe-Queue)
        → Termin vereinbart
        → Stage: qualified

Tag 14: Vor-Ort-Termin → Angebot
        → Stage: converted
```

### Use Case 2: Meta Lead Ads + Multi-Channel Nurturing

**Szenario:** Leads von Facebook sollen systematisch nachverfolgt werden.

**Setup:**
1. Meta-Modul konfigurieren
2. Lead Form → Pipeline "Wärmepumpen" zuordnen
3. Auto-Import aktivieren

**Flow:**
```
Minute 0:   Lead füllt Facebook-Formular aus
            → Webhook an Backend
            → Contact erstellt
            → Enrolled in Pipeline
            → Brain aktiviert

Minute 1:   Brain: "Frischer Lead → WhatsApp-Nachricht"
            → pending_action erstellt
            → Vertrieb gibt frei
            → WhatsApp gesendet: "Danke für Ihr Interesse..."

Tag 2:      Keine Antwort → Brain: "Follow-up Email"
            → Email mit Produktinfo + Tracking-Link

Tag 3:      Kontakt öffnet Email, klickt Link
            → Website-Besuch getrackt
            → Stage: engaged
            → Brain: "Anruf empfohlen"

Tag 4:      Anruf → Beratungstermin gebucht
```

### Use Case 3: Retargeting mit bekannten Kontakten

**Szenario:** Kontakte die Website besucht haben, sollen Ads sehen.

**Setup:**
1. Custom Audience "Engaged Contacts" erstellen
2. Auto-Sync mit Pipeline, Stages: engaged, qualified
3. Meta Kampagne auf diese Audience

**Flow:**
```
Kontakt besucht Website (mit Tracking-Link)
        → Cookie gesetzt
        → Activity geloggt
        → Stage: engaged
        ↓
Nightly Sync: Alle "engaged" Contacts → Meta Audience
        → Emails gehasht hochgeladen
        → Meta matcht gegen User-DB
        ↓
Kontakt sieht personalisierte Ads auf Facebook/Instagram
        → "Jetzt Beratungstermin buchen"
        ↓
Kontakt klickt Ad → Landing Page (mit Cookie)
        → Wir wissen: Das ist der bekannte Kontakt
        → Activity: "ad_click"
        → Brain kann reagieren
```

---

## 9. Wettbewerbsvorteile

### Gegenüber klassischen CRM-Systemen

| Feature | Klassisches CRM | go4-automate |
|---------|-----------------|--------------|
| Multi-Channel | Manuell | ✅ Automatisiert |
| KI-Entscheidungen | ❌ | ✅ Brain entscheidet |
| Personalisierung | Manuell | ✅ KI-generiert |
| Attribution | Unklar | ✅ Vollständig |
| Website-Tracking | Separate Tools | ✅ Integriert |
| Meta-Integration | Manuell | ✅ Automatisiert |

### Gegenüber Marketing-Automation-Tools

| Feature | HubSpot/ActiveCampaign | go4-automate |
|---------|------------------------|--------------|
| LinkedIn-Integration | Limited | ✅ Vollständig |
| KI-Orchestrierung | ❌ | ✅ Zentral |
| Adaptive Sequenzen | Starre Workflows | ✅ Brain reagiert |
| Deutsche Lokalisierung | Mittel | ✅ Vollständig |
| White-Label | Teuer | ✅ Möglich |
| Eigene Infrastruktur | ❌ | ✅ Self-hosted |

### Unique Selling Points

1. **Das Brain**: Zentrale KI, die alle Kanäle orchestriert und adaptiv reagiert
2. **Cross-Channel Attribution**: Vollständige Nachverfolgung von Erstkontakt bis Conversion
3. **LinkedIn-Deep-Integration**: Automatisiertes Scraping, Messaging, Inbox-Management
4. **Modular**: Nur Module aktivieren die benötigt werden
5. **Self-Hosted**: Volle Kontrolle über Daten, DSGVO-konform
6. **Open Architecture**: Erweiterbar, integrierbar mit n8n

---

## 10. Roadmap

### Implementiert ✅

- **Phase 1**: Foundation (Datenmodell, CRUD, Frontend)

### Q2 2026

- **Phase 2**: Activity-System Integration
- **Phase 3**: Brain Setup-Layer
- **Phase 4**: Brain Runtime-Layer

### Q3 2026

- **Phase 5**: Modul-Integration (LinkedIn, Email, CRM)
- **Phase 6**: Engagement UI Erweiterungen

### Q4 2026

- **Phase 7**: Erweiterungen (Post-Mail, A/B Testing)
- **Phase 8**: Website-Tracking & Attribution
- **Meta-Modul**: Vollständige Integration

### 2027

- **Optimization Engine**: ML-basierte Empfehlungen
- **Multi-Language**: Internationalisierung
- **API für Partner**: White-Label Lösung
- **Mobile App**: Push-Notifications für Freigaben

---

## Anhang

### A. Dateistruktur (Engagement-Modul)

```
backend/app/engagement/
├── __init__.py
├── __manifest__.py          # Modul-Konfiguration
├── models.py                # SQLAlchemy Models
├── schemas.py               # Pydantic Schemas
├── service.py               # Business Logic
├── router.py                # REST API
├── brain.py                 # Brain-Logik (geplant)
├── brain_prompts.py         # LLM Prompts (geplant)
└── worker.py                # Periodische Jobs (geplant)

backend/alembic/versions/
├── 038_engagement_pipelines.py
├── 039_pipeline_enrollments.py
├── 040_pending_actions.py
└── 041_contact_activities.py

frontend/src/
├── api/engagement.js
├── stores/engagement.js
└── views/
    ├── EngagementView.vue
    ├── PipelineEditView.vue
    └── PipelineDetailView.vue
```

### B. AI-Prompts im System

Das System nutzt editierbare LLM-Prompts für verschiedene Aufgaben:

1. **Pipeline-Onboarding**: Chat-Dialog zum Setup einer neuen Pipeline
2. **Next-Step Analyzer**: Entscheidet nächsten Schritt pro Kontakt
3. **Response Analyzer**: Analysiert eingehende Nachrichten (Sentiment, Intent)
4. **Playbook Generator**: Erstellt Richtlinien für Pipelines

### C. Glossar

| Begriff | Definition |
|---------|------------|
| **Pipeline** | Produkt-spezifische Engagement-Sequenz |
| **Enrollment** | Zuordnung eines Kontakts zu einer Pipeline |
| **Stage** | Position im Funnel (lead → contacted → engaged → qualified → converted) |
| **Touch** | Jede Interaktion mit einem Kontakt |
| **Brain** | Zentrale KI die Entscheidungen trifft |
| **Pending Action** | Vom Brain delegierte Aufgabe an ein Modul |
| **Activity** | Aufgezeichnete Interaktion (eingehend oder ausgehend) |
| **Tracking-Link** | URL mit verschlüsselter Contact-ID |
| **CAPI** | Meta Conversions API (Server-Side Tracking) |
| **Custom Audience** | Zielgruppe in Meta basierend auf eigenen Daten |

---

*Dokumentation erstellt: 2026-03-07*
*Letztes Update: 2026-03-07*
*Version: 1.0.0*
