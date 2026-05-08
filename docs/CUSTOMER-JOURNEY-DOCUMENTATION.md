# Customer Journey Tracking — Vollständige Dokumentation

## Systemübersicht

```
┌─────────────────────────────────────────────────────────────┐
│                  go4.automate (Source of Truth)              │
│                                                             │
│  Customer Journey Modul:                                    │
│  - Kontakte (contacts-Tabelle, zentral für alle Module)     │
│  - Journey Events (Seitenaufrufe, Interaktionen, etc.)      │
│  - Ref-Codes (personalisierte Tracking-Links)               │
│  - Kampagnen (Gruppierung von Ref-Codes)                    │
│                                                             │
│  Dashboard:                                                 │
│  - Live-Feed (Echtzeit-Events mit Auto-Refresh)             │
│  - Lead-Liste (alle identifizierten + anonymen Kontakte)    │
│  - Lead-Detail mit Journey-Timeline                         │
│  - Ref-Code Verwaltung (CRUD + Bulk-Generierung + CSV)      │
│  - Kampagnen-Verwaltung                                     │
│                                                             │
│  API (extern, API-Key Auth):                                │
│  POST /tracking/identify       ← Lead erstellen/finden      │
│  POST /tracking/prepare-link   ← All-in-one für Odoo        │
│  POST /tracking/event          ← Event loggen               │
│  POST /tracking/event/batch    ← Batch-Events               │
│  GET  /tracking/ref/{code}     ← Ref-Code auflösen + Merge  │
│  GET  /tracking/campaigns      ← Kampagnen auflisten        │
│  POST /tracking/campaigns      ← Kampagne erstellen         │
│  GET  /tracking/campaigns/resolve ← Kampagne per Name       │
│  POST /tracking/refs           ← Ref-Code erstellen         │
└──────────┬──────────────────────────────┬───────────────────┘
           │ HTTPS + API Key              │ HTTPS + API Key
           │                              │
┌──────────▼──────────┐        ┌──────────▼──────────┐
│  go4.energy         │        │  Odoo               │
│  (Website)          │        │  (CRM)              │
│                     │        │                     │
│  Backend: Proxy     │        │  Bei Lead-Anlage:   │
│  /api/t/* ──────────┤        │  POST /identify     │
│                     │        │                     │
│  Frontend:          │        │  Bei E-Mail:        │
│  Cookie go4_lead    │        │  POST /prepare-link │
│  useJourneyTracking │        │                     │
│  useTracking Bridge │        │  Bei Angebot-View:  │
│                     │        │  POST /event        │
│  Parallel:          │        │                     │
│  Umami (Aggregate)  │        │  Kampagnen-Sync:    │
│  Meta Pixel (Ads)   │        │  GET /campaigns/    │
│                     │        │      resolve        │
└─────────────────────┘        └─────────────────────┘
```

---

## Cookie

| Eigenschaft | Wert |
|---|---|
| **Name** | `go4_lead` |
| **Wert** | Tracking-Hash (12 Zeichen, alphanumerisch, z.B. `aB3xK9mQ2wL7`) |
| **Domain** | `.go4.energy` (First-Party) |
| **Max-Age** | 180 Tage (15.552.000 Sekunden) |
| **SameSite** | `Lax` |
| **Secure** | `true` |
| **HttpOnly** | `false` (Frontend muss ihn lesen können) |
| **DSGVO** | Funktionaler Cookie, kein Marketing-Consent nötig |

### Wann wird der Cookie gesetzt?

| Auslöser | Wie |
|---|---|
| **Ref-Link Klick** (`?ref=CODE`) | Sofort beim ersten Seitenaufruf |
| **Interest-Detection** (2+ Seitenaufrufe) | Automatisch nach der 2. Seite |
| **Formular-Submit** (identifyLead) | Beim Absenden von Kontaktdaten |

### Was steht im Cookie?

Nur der `tracking_hash` — ein 12-stelliger alphanumerischer String. Dieser Hash ist der Foreign Key zum Kontakt in der go4.automate Datenbank. Er enthält keine personenbezogenen Daten.

---

## Datenmodell

### Verknüpfungen

```
Kontakt (contacts-Tabelle)
  ├── tracking_hash (12 Zeichen) ── Cookie-Wert, 1:1 pro Kontakt
  ├── journey_status (new/active/converted/lost)
  ├── odoo_id (Odoo Lead/Contact ID)
  │
  ├── Journey Events (1:n)
  │     ├── event (z.B. "page_visit", "konfigurator_complete")
  │     ├── category (awareness/engagement/conversion/retention)
  │     ├── page_path, utm_source, utm_medium, utm_campaign
  │     └── metadata (JSONB, event-spezifische Daten)
  │
  └── Ref-Codes (1:n)
        ├── ref_code (6 Zeichen, z.B. "xK9mQ2")
        ├── target_url, utm_source, utm_medium, utm_campaign
        └── campaign_id → Kampagne (n:1)
                            ├── name
                            ├── channel (linkedin/email/whatsapp/...)
                            └── status (active/paused)
```

### Wichtige Unterscheidungen

| | tracking_hash | ref_code |
|---|---|---|
| **Zweck** | Cookie / Lead-Identität | Kampagnen-Link in URL |
| **Sichtbar für** | Nur im Cookie | Nutzer (in der URL) |
| **Lebensdauer** | Permanent pro Lead | Einmalig oder pro Kampagne |
| **Zuordnung** | 1 Kontakt = 1 tracking_hash | 1 Kontakt → viele ref_codes |
| **Länge** | 12 Zeichen | 6 Zeichen (+ optionales Prefix) |

---

## Tracking-Architektur auf go4.energy

### Drei parallele Systeme

```
Besucher auf go4.energy
  │
  ├── Umami (IMMER, ohne Consent)
  │   → Aggregierte Statistiken, keine Einzelpersonen
  │   → "Wie viele Besucher hatte /photovoltaik diese Woche?"
  │
  ├── Meta Pixel (NUR nach Cookie-Consent)
  │   → Facebook/Instagram Retargeting + Custom Audiences
  │   → Nutzt utm_* Parameter für Kampagnen-Attribution
  │
  └── Customer Journey (nach Identifikation ODER Interest-Detection)
      → go4_lead Cookie (funktional, ohne Marketing-Consent)
      → Individuelle Journey pro Lead
      → "Was hat Max Müller auf der Seite gemacht?"
```

### Technische Umsetzung

**Plugin** (`plugins/tracking.client.ts`):
- Nuxt Client-Plugin, läuft bei jeder Seitennavigation
- Ruft `useJourneyTracking().initFromUrl()` auf
- Reagiert auf `page:finish` Hook (SPA-Navigation)

**Composable** (`composables/useJourneyTracking.ts`):
- `initFromUrl()` — Ref-Code auflösen, Interest-Detection, page_visit senden
- `trackJourney(event, metadata)` — Event an go4.automate senden
- `identifyLead(data)` — Kontakt mit echten Daten verknüpfen
- `getLeadHash()` / `setLeadHash()` — Cookie lesen/schreiben

**Bridge** (`composables/useTracking.ts`):
- Jeder `trackEvent()` Aufruf (für Umami) wird automatisch auch als Journey-Event gesendet
- Nur wenn Cookie existiert (identifizierter/interest-detected Besucher)
- Keine zusätzliche Implementierung pro Seite nötig

**Proxy** (`backend/routers/tracking_proxy.py`):
- Frontend spricht nie direkt mit go4.automate
- `/api/t/event` → `automate_client.send_event()`
- `/api/t/identify` → `automate_client.identify()`
- `/api/t/ref/{code}` → `automate_client.resolve_ref()`
- `/api/t/batch` → `automate_client.send_batch()`

### Was automatisch getrackt wird (ohne Code pro Seite)

- Seitenaufrufe (jede Navigation, auch SPA)
- Ref-Link Resolution (`?ref=` Parameter)
- Interest-Detection (ab 2 Seitenaufrufen)
- Alle bestehenden Umami-Events (via useTracking Bridge)

### Was manuell eingebaut ist

| Seite | Was | Funktion |
|---|---|---|
| Konfigurator | `identifyLead()` nach Anfrage-Submit | Kontakt identifizieren |
| Kontaktformular | `identifyLead()` nach Submit | Kontakt identifizieren |
| EMS Showcase | `identifyLead()` nach Lead-Gate | Kontakt identifizieren |
| Spotpreis-Simulator | `trackJourney()` nach Simulation | Event loggen |

### Neue Seiten anlegen

**Nichts zu tun** für Seitenaufrufe und Interest-Detection. Nur bei:
- **Neues Formular** → `identifyLead()` nach Submit aufrufen
- **Neue Interaktionen** → `trackEvent()` (für Umami) reicht, Journey wird automatisch mitgetrackt

---

## Events

### Event-Taxonomie

| Event | Wann | Kategorie | Metadata |
|---|---|---|---|
| `page_visit` | Seitenaufruf (nur mit Cookie) | awareness | `{ path, referrer }` |
| `ref_link_click` | Aufruf via `?ref=` Link | awareness | `{ ref_code, utm_* }` |
| `interest_detected` | Anonymer Besucher, 2+ Seiten | awareness | `{ source_detail: "N_pages" }` |
| `identify` | Echte Kontaktdaten hinterlassen | conversion | `{ source, source_detail }` |
| `konfigurator_start` | Konfigurator geöffnet | engagement | `{ mode }` |
| `konfigurator_step` | Schrittwechsel im Konfigurator | engagement | `{ step_id }` |
| `konfigurator_mode_sunfi` | Sunfi-Modus gewählt | engagement | |
| `konfigurator_mode_manual` | Manueller Modus gewählt | engagement | |
| `konfigurator_complete` | Anfrage abgeschickt | conversion | `{ kwp, price, modules }` |
| `config_link_visit` | Gespeicherte Config aufgerufen | retention | `{ config_hash }` |
| `quote_pdf_download` | PV-Angebot PDF | conversion | `{ kwp, price }` |
| `ems_step_pv` | EMS: PV-Anlage Schritt | engagement | |
| `ems_step_battery` | EMS: Batterie Schritt | engagement | |
| `ems_step_running` | EMS: Simulation läuft | engagement | |
| `ems_simulation_complete` | EMS Simulation abgeschlossen | engagement | |
| `ems_tab_*` | EMS: Tab gewechselt | engagement | |
| `ems_save_config` | EMS: Config gespeichert | engagement | |
| `ems_lead_verified` | EMS: Lead verifiziert | conversion | |
| `ems_pdf_download` | EMS Report PDF | conversion | `{ company }` |
| `contact_form` | Kontaktformular abgeschickt | conversion | `{ subject }` |
| `spot_simulation_start` | Spotpreis-Simulator gestartet | engagement | `{ source }` |
| `spot_simulation_complete` | Spotpreis-Simulator fertig | engagement | |
| `chat_started` | Chatwoot Widget geöffnet | engagement | |
| `quote_viewed` | Angebot im Odoo-Portal eingesehen | engagement | `{ order_name, amount_total }` |

### Event-Kategorien

- **awareness** — Erster Kontakt, Seitenaufrufe, Link-Klicks
- **engagement** — Aktive Nutzung (Konfigurator, Simulationen, Chat)
- **conversion** — Daten hinterlassen (Anfrage, Formular, PDF-Download, Identifizierung)
- **retention** — Wiederkehr, gespeicherte Configs

### Auto-Kategorisierung

Unbekannte Events werden automatisch kategorisiert:
- Events mit Prefix `ems_step_`, `ems_tab_`, `konfigurator_`, `spot_`, `chat_` → engagement
- Events mit Prefix `ems_lead_`, `ems_pdf_` → conversion
- Alles andere → engagement (default)

---

## Szenarien

### Szenario 1: Persönliche LinkedIn-Nachricht

**Setup:** Ref-Code erstellen (mit oder ohne Kontakt), Link per DM senden.

```
1. Du erstellst Ref-Code "xK9mQ2" für "Florian Müller"
   (mit Kontakt verknüpft, oder ohne — beides funktioniert)

2. Du sendest: go4.energy/photovoltaik?ref=xK9mQ2&utm_source=linkedin&utm_medium=messaging

3. Florian klickt:
   → Plugin liest ?ref=xK9mQ2
   → go4.automate: Ref-Code auflösen, tracking_hash zurück
   → Cookie go4_lead wird gesetzt
   → ref_link_click Event

4. Florian surft weiter:
   → page_visit Events fließen
   → Konfigurator-Schritte, EMS-Tabs etc. werden getrackt

5. Florian schickt Anfrage ab:
   → identifyLead() mit Name, E-Mail
   → Platzhalter wird upgraded ODER bestehender Kontakt bestätigt
   → identify Event (conversion)
```

**Im Dashboard:** Komplette Timeline von Klick bis Conversion, mit Kampagnen-Zuordnung.

### Szenario 2: Öffentlicher LinkedIn-Post (UTM, kein Ref-Code)

**Setup:** Link mit UTM-Parametern im Post, kein individueller Ref-Code.

```
1. Link im Post: go4.energy/photovoltaik?utm_source=linkedin&utm_campaign=speicher_maerz

2. Besucher A klickt:
   → Kein ?ref=, kein Cookie
   → Seite 1: Zähler = 1 (nur Umami)
   → Seite 2: Zähler = 2 → Interest-Detection
   → Anonymer Kontakt erstellt, Cookie gesetzt
   → page_visit Events ab Seite 2, mit utm_campaign=speicher_maerz

3. Besucher A identifiziert sich (Formular):
   → existing_hash → Platzhalter upgraded
   → In der Timeline: utm_campaign=speicher_maerz beim ersten Event sichtbar
   → Kampagnen-Attribution: "Kam über LinkedIn Speicher-Aktion"

4. Besucher B klickt den gleichen Link:
   → Eigener anonymer Kontakt, eigener Cookie
   → Komplett getrennte Journey
```

**Im Dashboard:** Pro Besucher eine eigene Timeline. UTM-Parameter zeigen die Kampagne.

### Szenario 3: Odoo Massen-Mailing

**Setup:** 500 E-Mails mit individuellem Ref-Code pro Empfänger via `prepare-link`.

```
1. Odoo Server Action pro Empfänger:
   POST /tracking/prepare-link
   { name, email, campaign_name: "Mailing April", target_url: "..." }
   → Kontakt angelegt/gefunden
   → Kampagne angelegt/gefunden (Name-Match)
   → Ref-Code erstellt + Link zurück

2. Empfänger klickt Link in E-Mail:
   → Ref-Code resolve → Cookie gesetzt
   → Kontakt ist bereits identifiziert (von Odoo angelegt)
   → Alle Events sofort dem echten Kontakt zugeordnet

3. Im Dashboard:
   → Kampagne "Mailing April": 500 Ref-Codes, 87 Klicks, 12 Conversions
   → Pro Lead: "Kam über Mailing April, hat 5 Seiten besucht, Konfigurator gestartet"
```

### Szenario 4: Bulk Ref-Codes für LinkedIn-Kampagne

**Setup:** 800 Ref-Codes generieren (ohne Kontakt-Zuordnung), in CSV exportieren, über externe Plattform versenden.

```
1. Im Dashboard: "Generieren + CSV"
   → 800 Codes, Kampagne "LinkedIn Q2", utm_source=linkedin
   → CSV Download: ref_code;link

2. Codes werden über Plattform an LinkedIn-Kontakte versendet

3. Empfänger klickt:
   → Ref-Code hat keinen Kontakt → Platzhalter wird erstellt
   → Cookie gesetzt, Events fließen
   → Im Dashboard: "Ref LI_xK9mQ2 hat 3 Seiten besucht"

4. Empfänger identifiziert sich (Formular, Anruf + Odoo-Angebot):
   → Platzhalter wird upgraded oder mit bestehendem Kontakt gemerged
   → Komplette Historie bleibt erhalten
```

### Szenario 5: Anonymer Besucher → Wiederkehr → Identifizierung

**Setup:** Kein Ref-Code, keine Kampagne. Besucher findet Seite über Google.

```
1. Erster Besuch (Google):
   → Seite 1: nur Umami
   → Seite 2: Interest-Detection → anonymer Kontakt + Cookie
   → Events fließen (page_visit, Konfigurator-Schritte etc.)

2. Woche später, Wiederkehr:
   → Cookie ist noch da (180 Tage)
   → Events gehen an gleichen anonymen Kontakt
   → Timeline wächst

3. LinkedIn-Post mit UTM:
   → Cookie existiert → Events werden mit UTM-Parametern geloggt
   → utm_campaign im Event gespeichert

4. Telefonischer Kontakt → Odoo-Angebot mit Ref-Code:
   → Empfänger klickt Link
   → Alter Cookie-Hash wird an go4.automate gesendet (existing_hash)
   → go4.automate merged: anonyme Journey → echter Kontakt
   → EINE Timeline mit kompletter Historie

   Im Dashboard:
   ── 15.03.2026 ──
     10:00  Interesse erkannt (website_interest)     ← Schritt 1
     10:01  Seitenaufruf /photovoltaik
     10:05  Konfigurator gestartet
   ── 22.03.2026 ──
     14:30  Seitenaufruf /ems/showcase               ← Schritt 2
     14:32  EMS: Simulation abgeschlossen
   ── 23.03.2026 ──
     09:15  Seitenaufruf /photovoltaik (linkedin)    ← Schritt 3
   ── 25.03.2026 ──
     11:00  Ref-Link Klick                           ← Schritt 4
     11:01  Seitenaufruf /photovoltaik/konfigurator
     11:10  Anfrage abgeschickt ← CONVERSION
```

### Szenario 6: Cross-Device (Handy → Desktop)

```
1. Handy: Klickt LinkedIn-Link → Cookie auf Handy
2. Desktop: Surft go4.energy → eigener Cookie auf Desktop
3. Zwei getrennte Journeys (kein Cross-Device-Cookie möglich)
4. Identifiziert sich auf Desktop (Formular mit gleicher E-Mail):
   → go4.automate matched per E-Mail
   → Desktop-Journey gehört jetzt zum Kontakt
   → Handy-Journey ist separat (anderer Cookie)
5. Identifiziert sich auch auf Handy:
   → existing_hash → Merge beider Journeys in einen Kontakt
```

### Szenario 7: Odoo Portal (crm.go4.energy)

```
1. Kunde öffnet Angebot im Portal (crm.go4.energy)
   → Odoo Controller: POST /tracking/event
     { tracking_hash: "...", event: "quote_viewed", source_site: "crm.go4.energy" }
   → Server-side getrackt (kein Browser-Cookie auf crm.go4.energy)

2. Kunde klickt Link in Angebots-E-Mail (go4.energy/...?ref=...)
   → Cookie wird auf go4.energy gesetzt
   → Ab jetzt: Browser-Tracking auf go4.energy

Kein Cross-Domain-Cookie zwischen crm.go4.energy und go4.energy.
Portal-Events werden server-side via tracking_hash getrackt.
```

---

## Merge-Logik

### Wann wird gemerged?

| Auslöser | Was passiert |
|---|---|
| `identifyLead()` mit `existing_hash` | Platzhalter wird upgraded oder mit bestehendem Kontakt zusammengeführt |
| Ref-Code-Resolve mit `existing_hash` | Anonyme Journey wird zum Ref-Code-Kontakt verschoben |
| E-Mail-Match bei Identifizierung | Wenn Platzhalter-E-Mail und echte E-Mail verschiedene Kontakte sind → Merge |

### Was wird gemerged?

- Alle `journey_events` werden vom alten zum neuen Kontakt verschoben
- Alle `journey_ref_codes` werden vom alten zum neuen Kontakt verschoben
- Der alte Platzhalter-Kontakt bleibt bestehen (Events sind weg, aber Kontakt existiert noch)

### Platzhalter-Erkennung

Platzhalter-Kontakte haben E-Mails mit dem Pattern:
- `anon-XXXXXXXX@journey.placeholder` (Interest-Detection)
- `ref-XXXXXX@journey.placeholder` (Ref-Code ohne Kontakt)

Bei Identifizierung mit echter E-Mail wird der Platzhalter upgraded (E-Mail, Name, Phone überschrieben).

---

## API-Referenz

### Authentifizierung

Alle externen Endpoints (`/api/v1/tracking/*`) nutzen API-Key Auth:
```
Authorization: Bearer <api-key>
```

#### Mehrere Keys (pro Anwendung)

Pro tracking-anbindender Anwendung wird ein eigener Key vergeben. Das Label
des Keys wird automatisch als `source_site` auf alle erzeugten Events
geschrieben (vom Client gesendete `source_site`-Werte werden ignoriert,
um Spoofing zu verhindern). Im Live-Feed lässt sich nach `source_site`
filtern (`GET /customer-journey/dashboard/feed?source_site=...`).

Konfiguration via Environment-Variable in `backend/.env`:

```
TRACKING_API_KEYS={"go4.energy":"ga_live_...","smartladen.de":"sl_live_..."}
```

**Backwards-Kompatibilität:** Wenn `TRACKING_API_KEYS` leer und der alte
`TRACKING_API_KEY=...` gesetzt ist, wird dieser automatisch auf das Label
`go4.energy` gemappt — bestehende Integrationen funktionieren unverändert
weiter.

#### IP-Blocklist

Tracking-Aufrufe von definierten IPs werden auf den **Browser-getriebenen**
Schreib-Endpunkten (`/identify`, `/event`, `/event/batch`) verworfen — der
Aufrufer bekommt eine reguläre 200er-Antwort mit Sentinel-Werten
(`tracking_hash=""`, `lead_id=0`, etc.), es entsteht aber **kein** Contact
und **kein** Event in der Datenbank. Nutzungsfälle: eigene Büro-IPs raushalten,
Mail-Preview-Bots blocken die Mailing-Links nachklicken.

```
TRACKING_BLOCKED_IPS=["34.52.252.219","<deine-büro-ip>"]
```

`34.52.252.219` ist die GCP-Egress-IP, von der u.a. Mail-Preview-Bots Links
nachklicken — immer drin lassen. Der Client erkennt den Block nicht —
ideal fürs unauffällige Eigen-Browsing.

**Ausnahme `/prepare-link`**: Dieser Endpoint ist explizit **NICHT** vom
Block betroffen, da er nur server-zu-server (z.B. von Odoo) aufgerufen wird
und sich die Outbound-IP von Odoo mit der Preview-Bot-IP teilt. Würde der
Block hier greifen, könnten Odoo-Massenmailings keine Ref-Codes mehr
erzeugen.

Interne Endpoints (`/api/v1/customer-journey/*`) nutzen Session-Auth + X-Tenant-ID Header.

### POST /tracking/identify

Lead erstellen oder finden. Primärer Match-Key: E-Mail. Sekundär: Phone. Tertiär: existing_hash.

```json
// Request
{
    "name": "Max Mustermann",
    "email": "max@example.com",
    "phone": "+491701234567",
    "company": "Mustermann GmbH",
    "source": "konfigurator",
    "source_detail": "inquiry_submit",
    "existing_hash": "alterCookieHash",
    "utm_source": "google",
    "utm_medium": "organic",
    "utm_campaign": null,
    "metadata": { "system_kwp": 12.5 }
}

// Response
{
    "ok": true,
    "tracking_hash": "aB3xK9mQ2wL7",
    "lead_id": 42,
    "is_new": true,
    "merged": false
}
```

### POST /tracking/prepare-link

All-in-one: Kontakt + Kampagne + Ref-Code + fertiger Link. Designed für Odoo Massen-Mailings.

```json
// Request
{
    "name": "Hans Huber",
    "email": "hans@huber.at",
    "phone": "+43664123456",
    "company": "Huber GmbH",
    "source": "odoo",
    "campaign_name": "Newsletter April 2026",
    "campaign_channel": "email",
    "target_url": "https://go4.energy/photovoltaik",
    "utm_source": "email",
    "utm_medium": "newsletter",
    "utm_campaign": "newsletter_april_2026"
}

// Response
{
    "ok": true,
    "tracking_hash": "cdiUubhvZipd",
    "ref_code": "oamzjc",
    "link": "https://go4.energy/photovoltaik?ref=oamzjc&utm_source=email&utm_medium=newsletter&utm_campaign=newsletter_april_2026",
    "contact_id": 13,
    "is_new_contact": false,
    "is_new_ref": true
}
```

### POST /tracking/event

Event loggen. Fire-and-forget.

```json
// Request
{
    "tracking_hash": "aB3xK9mQ2wL7",
    "ref_code": null,
    "event": "page_visit",
    "page_path": "/photovoltaik/konfigurator",
    "utm_source": "linkedin",
    "utm_medium": "social",
    "utm_campaign": "march2026",
    "metadata": {},
    "timestamp": null
}

// Response
{ "ok": true, "tracking_hash": "aB3xK9mQ2wL7" }
```

> **Hinweis:** Das Feld `source_site` im Request wird **ignoriert**. Der
> `source_site`-Wert auf dem gespeicherten Event wird automatisch aus dem
> Label des verwendeten API-Keys übernommen (siehe [Mehrere Keys](#mehrere-keys-pro-anwendung)) — verhindert Spoofing.

#### Block bei geblockter IP

Stammt der Aufruf von einer IP in `TRACKING_BLOCKED_IPS` (siehe [IP-Blocklist](#ip-blocklist)),
liefert der Endpoint regulär 200 zurück, aber mit `tracking_hash: null` —
es wird kein Event geschrieben. Gilt analog für `/identify` (Sentinel
`lead_id: 0`, `tracking_hash: ""`) und `/event/batch` (`processed: 0`).
**Nicht betroffen:** `/prepare-link` (Server-zu-Server, z.B. Odoo).

### POST /tracking/event/batch

Queued Events nachholen (nach Offline-Phase).

```json
// Request
{ "events": [ { ... Event 1 ... }, { ... Event 2 ... } ] }

// Response
{ "ok": true, "processed": 5, "errors": 0 }
```

### GET /tracking/ref/{ref_code}?existing_hash=...

Ref-Code auflösen. Gibt tracking_hash zurück. Optional: merged alte Journey wenn existing_hash angegeben.

```json
// Response
{
    "ok": true,
    "tracking_hash": "aB3xK9mQ2wL7",
    "ref_code": "xK9mQ2",
    "lead_name": "Florian Mueller"
}
```

### GET /tracking/campaigns/resolve?name=...&channel=...

Kampagne per Name finden oder erstellen.

```json
// Response
{
    "id": 7,
    "tenant_id": "go4energy",
    "name": "Mailing Mai 2026",
    "channel": "email",
    "status": "active",
    "description": null,
    "created_at": "2026-03-26T12:00:00"
}
```

### GET /tracking/campaigns

Alle Kampagnen auflisten.

### POST /tracking/campaigns

Kampagne erstellen.

### POST /tracking/refs

Einzelnen Ref-Code erstellen (mit optionaler Kontakt/Kampagnen-Zuordnung).

### GET /customer-journey/dashboard/feed

Live-Feed für das Dashboard. Session-Auth + `X-Tenant-ID`.

| Query-Param | Typ | Default | Beschreibung |
|---|---|---|---|
| `limit` | int | 50 | max. 200 |
| `offset` | int | 0 | Pagination |
| `source_site` | string | — | Filtert auf eine Quelle (z.B. `smartladen.de`) |

### GET /customer-journey/dashboard/sources

Liefert die Liste aller `source_site`-Werte, für die im aktuellen Tenant
mindestens ein Event existiert. Wird vom Frontend genutzt um das
Quelle-Dropdown zu befüllen.

```json
// Response
["go4.energy", "smartladen.de"]
```

---

## go4.automate Dashboard

### Tabs

1. **Dashboard** — Stat-Cards (Leads, Events, Conversions, Ref-Codes) + Live-Feed
   - Auto-Refresh alle 30 Sekunden (Timer-Visualisierung)
   - Neue Events werden oben eingefügt (kein Reload)
   - Infinite Scroll für ältere Events
   - Klick auf Event → Lead-Detail Timeline
   - **Quelle-Filter** im Feed-Header: Dropdown mit allen vorhandenen
     `source_site`-Werten (z.B. `go4.energy`, `smartladen.de`); erscheint
     automatisch sobald ≥2 Quellen Events haben. Filter wird auch beim
     Nachladen via Infinite Scroll respektiert.
   - **Quelle-Spalte** in der Event-Tabelle zeigt den `source_site`-Wert
     pro Event.

2. **Leads** — Tabelle aller Kontakte mit tracking_hash
   - Spalten: Name, E-Mail, Quelle, Status, Events, Letztes Event, Erstellt
   - Klick → Lead-Detail

3. **Ref-Codes** — CRUD + Bulk
   - Erstellen: mit Kontakt-Suche, Kampagne, Ziel-URL, UTM-Parameter
   - Bulk-Import: Name;Kontext pro Zeile
   - Generieren + CSV: N Codes ohne Kontakt, mit Kampagne/UTM
   - Link kopieren (inkl. UTM-Parameter)
   - Bearbeiten, Löschen

4. **Kampagnen** — CRUD
   - Name, Kanal, Status, Beschreibung

### Lead-Detail View

- Header: Name, E-Mail, Status-Badge
- Info-Cards: Quelle, Telefon, Event-Anzahl, Tracking-Hash
- Journey Timeline: gruppiert nach Tag, farbcodierte Kategorien
  - Blau: awareness
  - Gelb: engagement
  - Grün: conversion
  - Lila: retention

---

## UTM-Parameter

### Bedeutung

| Parameter | Was | Beispiele |
|---|---|---|
| `utm_source` | Wer/Wo (Plattform) | linkedin, email, google, whatsapp, flyer |
| `utm_medium` | Wie (Kanal-Typ) | social, messaging, paid, organic, cpc, email, print, event |
| `utm_campaign` | Welche Kampagne | speicher_maerz, newsletter_april, messe_q2 |

### Typische Kombinationen

| Szenario | utm_source | utm_medium | utm_campaign |
|---|---|---|---|
| LinkedIn DM | linkedin | messaging | (Kampagnenname) |
| LinkedIn Post | linkedin | social | (Kampagnenname) |
| LinkedIn Ad | linkedin | paid | (Kampagnenname) |
| Newsletter | email | newsletter | (Kampagnenname) |
| Google Organic | google | organic | — |
| Google Ads | google | cpc | (Kampagnenname) |
| WhatsApp | whatsapp | messaging | (Kampagnenname) |
| Messe QR-Code | messe | event | (Kampagnenname) |
| Flyer | flyer | print | (Kampagnenname) |

### Wo werden UTM-Parameter gespeichert?

1. **Auf jedem Journey-Event** — `utm_source`, `utm_medium`, `utm_campaign` Felder
2. **Auf Ref-Codes** — für den "Link kopieren" Button
3. **Umami** wertet sie automatisch aus
4. **Meta Pixel** wertet sie automatisch aus

Für go4.automate sind UTM-Parameter **redundant** wenn ein Ref-Code vorhanden ist (Kampagnen-Zuordnung läuft über den Ref-Code). Für Umami und Meta Pixel sind sie **essentiell**.

---

## Odoo-Integration

### Übersicht der API-Calls

| # | Endpoint | Odoo-Trigger | Zweck |
|---|---|---|---|
| 1 | `POST /identify` | Lead-Erstellung | Kontakt in go4.automate registrieren |
| 2 | `GET /campaigns/resolve` | Kampagne auf Angebot | Kampagnen-ID holen |
| 3 | `POST /prepare-link` | E-Mail-Template | Personalisierter Tracking-Link |
| 4 | `POST /event` | Portal-Angebot | "Angebot eingesehen" tracken |

### Fehlerverhalten

Alle Odoo → go4.automate Calls sind non-blocking. Bei Timeout/Fehler wird geloggt, aber der Odoo-Prozess läuft normal weiter.

### Detaillierte Odoo-Dokumentation

Siehe `/var/www/go4energy/docs/ODOO-CUSTOMER-JOURNEY-INTEGRATION.md` auf dem VPS.

---

## Interest-Detection

### Funktionsweise

- **Zähler** in `localStorage` (`go4_page_count`), überlebt Browser-Neustarts
- **Schwelle** aktuell: 2 Seitenaufrufe
- **Bei Schwelle:** `POST /api/t/identify` mit `source: "website_interest"`
- **Ergebnis:** Anonymer Kontakt (`anon-XXX@journey.placeholder`), Cookie gesetzt

### Konfigurierbar

Schwelle (`INTEREST_THRESHOLD`) ist im Composable definiert. Aktuell `2`.

---

## Koexistenz der drei Tracking-Systeme

| System | Consent nötig | Cookies | Einzelpersonen | Zweck |
|---|---|---|---|---|
| **Umami** | Nein | Keine | Nein | Aggregierte Statistiken |
| **Meta Pixel** | Ja (Cookie-Consent) | Ja (Third-Party) | Nein (Custom Audiences) | Retargeting, Ads |
| **Customer Journey** | Nein (funktional) | Ja (First-Party) | Ja | Individuelle Lead-Timeline |

Keine Konflikte: Alle drei laufen parallel, nutzen dieselben UTM-Parameter, speichern Daten unabhängig.
