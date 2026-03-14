# Handoff 2026-03-13

Stand: 2026-03-14

## Worum es in diesem Arbeitsblock ging

Ziel war, die Plattform so auszurichten, dass komplexe Modul-Konfigurationen spaeter primär ueber den Chatbot erfolgen koennen, waehrend Enduser im Frontend nur sehr einfache Schalter sehen.

Referenzmodul fuer diese Arbeit war zuerst `briefing`, danach wurde dasselbe Muster auf `emailmarketing` ausgeweitet.

## Fachliche Entscheidungen

### 1. Chatbot statt grosser Konfigurations-UI

Beschlossen wurde:

- komplexe Modul-Konfiguration soll der Chatbot steuern
- der Chatbot soll Module, Parameter, Actions und Credentials kennen
- der Chatbot soll fehlende Informationen gezielt abfragen koennen
- der Chatbot soll Konfigurationen ueber kanonische Modul-Schnittstellen setzen
- der Chatbot soll Testlaeufe und Modul-Aktionen ausloesen koennen

Nicht beschlossen wurde:

- freie, unkontrollierte Dateimanipulation durch den Chatbot

Stattdessen gilt:

- Modul-Discovery + Modul-Interfaces bleiben die Wahrheit
- der Chatbot arbeitet gegen standardisierte API-/Service-Pfade

### 2. Enduser-UI bewusst klein halten

Fuer das spaetere Produkt gilt:

- Enduser sollen nur sehr wenige Controls sehen
- beim `briefing`-Modul sind das vor allem:
  - E-Mail-Briefing an/aus
  - Kalender-Briefing an/aus
  - Uhrzeit

Alles Komplexere bleibt fuer Admin/Operator/Chatbot.

### 3. Microsoft Graph als gemeinsame Integrationsbasis

Beschlossen wurde:

- Microsoft Graph soll nicht nur fuer `briefing`, sondern plattformweit wiederverwendbar werden
- persoenliche Verbindungen und allgemeine Versand-/Service-Mailboxen muessen fachlich getrennt bleiben
- `briefing` bleibt zunaechst lesend
- aktive Mail-Aktionen wie Reply/Delete gehoeren spaeter in ein separates Mail-/Inbox-/CRM-Modul

### 4. IMAP vorerst zurueckstellen

Beschlossen wurde:

- IMAP ist aktuell nicht Prioritaet
- zuerst Microsoft Graph / Google sauber modellieren

## Was konkret implementiert wurde

### A. Frontend `Mein Briefing`

Im `briefing`-Frontend wurde ein neuer Personal-Bereich gebaut:

- eigener Tab `Mein Briefing`
- persoenliche Settings
- Connect/Disconnect fuer Mail und Kalender
- Microsoft und Google als Provider

Betroffene Dateien:

- `frontend/src/views/BriefingView.vue`
- `frontend/src/stores/briefing.js`
- `frontend/src/api/briefing.js`
- `backend/app/briefing/__manifest__.py`

### B. Backend fuer persoenliches Briefing

Es gibt jetzt Backend-Grundlagen fuer persoenliche Briefing-Verbindungen:

- `BriefingAccountConnection`
- `BriefingPersonalSettings`
- Endpunkte fuer Settings, Connection-Liste, OAuth und Disconnect
- Migration und Tests

Wichtige Dateien:

- `backend/app/briefing/models.py`
- `backend/app/briefing/schemas.py`
- `backend/app/briefing/service.py`
- `backend/app/briefing/router.py`
- `backend/alembic/versions/053_personal_briefing_connections.py`
- `backend/tests/test_briefing.py`

### C. Gemeinsame Integrations-Architektur

Es wurde ein neues Paket eingefuehrt:

- `backend/app/integrations/`

Enthaelt:

- provider-agnostische Typen
- gemeinsame Interfaces fuer Mail/Kalender/Actions
- Microsoft-Graph-Bausteine

Wichtige Dateien:

- `backend/app/integrations/types.py`
- `backend/app/integrations/interfaces.py`
- `backend/app/integrations/service.py`
- `backend/app/integrations/microsoft_graph/*`

Dokumentation:

- `docs/INTEGRATIONS-ARCHITECTURE.md`

### D. Einheitliche Chatbot-Steuerung fuer Module

Das bestehende Modul-System wurde erweitert, damit der Chatbot kanonisch mit Modulen arbeiten kann.

Neu:

- `setup-schema` pro Modul
- deklarative `actions`
- deklarative `enduser_controls`
- deklarative `credentials`

Kernidee:

- Modul bleibt ueber Manifest + `config_schema` + `ModuleInterface` definiert
- der Chatbot liest und schreibt nicht "irgendwo", sondern ueber diese Modul-Schnittstellen

Wichtige Dateien:

- `backend/app/utils/module_interface.py`
- `backend/app/ai/router.py`
- `backend/app/ai/service.py`

Dokumentation:

- `docs/AI-MODULE-CONTROL.md`

## Referenzfall `briefing`

`briefing` ist aktuell das wichtigste Referenzmodul fuer die neue Chatbot-Steuerung.

### Im Setup-Schema enthalten

- modulweite Config-Parameter
- Actions
  - `run_sources_now`
  - `generate_channel_episode`
  - `run_personal_briefing`
- Enduser-Controls
  - `email_enabled`
  - `calendar_enabled`
  - `delivery_time`
- Credentials
  - `microsoft_client_id`
  - `microsoft_client_secret`
  - `google_client_id`
  - `google_client_secret`

### Bereits real funktionierend

- AI kann `briefing`-Config lesen
- AI kann `briefing`-Config schreiben
- AI kann `run_sources_now` ausfuehren
- AI kann `generate_channel_episode` ausfuehren
- AI kann `run_personal_briefing` ausfuehren
- normaler API-Endpoint fuer manuellen Personal-Run:
  - `POST /api/v1/briefing/personal/run`

### Technische Umsetzung Personal-Run

Der manuelle Personal-Run:

- liest `BriefingPersonalSettings`
- sucht passende persoenliche `email`- und `calendar`-Connections
- refresht Tokens falls noetig
- holt E-Mails und Termine
- respektiert `unread_only`, `days_back`, `max_items`
- liefert strukturierte Sections und Fehler zurueck

## Referenzfall `emailmarketing`

`emailmarketing` wurde als zweiter Referenzfall an dasselbe Muster angebunden.

### Im Setup-Schema enthalten

- modulweite Config-Parameter
- Actions
  - `verify_provider`
  - `send_single_test_email`
- Credential-Schema
  - `provider_api_key`

### Bereits real funktionierend

- AI kann `emailmarketing`-Config lesen
- AI kann `emailmarketing`-Config schreiben
- AI kann Provider-Pruefung anstossen
- AI kann eine einzelne Test-E-Mail ueber einen angegebenen Provider senden

## Wichtige Endpunkte

### Modulbezogene AI-Steuerung

- `GET /api/v1/ai/modules/{module}/setup-schema`
- `GET /api/v1/ai/modules/{module}/config`
- `PUT /api/v1/ai/modules/{module}/config`
- `POST /api/v1/ai/modules/{module}/actions/{action_key}`

### Briefing speziell

- `GET /api/v1/briefing/personal/settings`
- `PUT /api/v1/briefing/personal/settings`
- `GET /api/v1/briefing/personal/connections`
- `GET /api/v1/briefing/personal/oauth/authorize`
- `GET /api/v1/briefing/personal/oauth/callback`
- `POST /api/v1/briefing/personal/connections/{id}/disconnect`
- `POST /api/v1/briefing/personal/run`

## Was verifiziert wurde

Verifiziert:

- Frontend-Build fuer `Mein Briefing` lief erfolgreich
- Python-Syntax-Checks via `python3 -m compileall` liefen fuer die geaenderten Backend-Bereiche erfolgreich
- gezielte Briefing-Tests fuer den AI-Credential-Pfad sind im Repo vorhanden:
  - Secret-Redaction im `setup-schema`
  - Persistierung von `system_config`-Credentials ueber den Tenant-Config-Pfad

Nicht verifiziert:

- erneuter Pytest-Lauf im aktuellen Environment

Grund:

- im aktuellen Environment ist `pytest` nicht installiert
- `python3 -m pytest ...` schlug mit `No module named pytest` fehl

## Nachtrag 2026-03-14: Secret-Haertung im AI-Setup

Der im letzten Block noch als naechster Schritt genannte Secret-Pfad ist inzwischen umgesetzt.

Aktueller Stand:

- `ModuleInterface` behandelt `credentials` getrennt von normalen Modulparametern
- Secret-Credentials werden beim Lesen nicht mehr im Klartext ausgegeben
- konfigurierte Secrets erscheinen fuer AI/Admin nur noch als Platzhalter `***configured***`
- Credentials mit `source = system_config` werden beim Schreiben nicht mehr als freie Modulparameter behandelt
- diese Werte laufen stattdessen ueber `TenantService.write_file_updates(...)` in den Tenant-Config-Pfad
- das `setup-schema` liefert fuer Credentials jetzt zusaetzlich:
  - `value`
  - `configured`

Fuer den Referenzfall `briefing` gibt es dazu gezielte Tests in `backend/tests/test_briefing.py`:

- Redaction eines bereits gesetzten `microsoft_client_secret`
- Persistierung von `microsoft_client_id` und `microsoft_client_secret` ueber `PUT /api/v1/ai/modules/briefing/config`

## Offene Punkte / naechste Schritte

### Unmittelbar als naechstes

1. Confirmations fuer riskante Modul-Aktionen zentral modellieren
2. allgemeines Datenmodell fuer `integration_connections` und Capabilities einfuehren
3. weitere Module an das gehartete Credential-/Setup-Muster anbinden

### Danach

4. `briefing`-Personalverbindungen an den allgemeinen Integration-Layer anbinden
5. spaeter `emailmarketing`-O365-Nutzung auf den gemeinsamen Graph-Layer umstellen
6. ein separates Mail-/Inbox-/CRM-Modul fuer Reply/Delete/Move planen

## Wichtige Arbeitsannahmen fuer die Fortsetzung

- `briefing` bleibt fachlich lesend
- aktive Mail-Aktionen kommen nicht in Phase 1 von `briefing`
- Chatbot-Konfiguration soll kanonisch ueber Modul-Schemas laufen
- Enduser-UI bleibt klein
- persoenliche Verbindungen und allgemeine Mailboxen bleiben getrennt

## Dateien, die beim Wiedereinstieg zuerst gelesen werden sollten

- `docs/HANDOFF-2026-03-13-BRIEFING-AI-CONTROL.md`
- `docs/CODEX-CONTEXT.md`
- `docs/AI-MODULE-CONTROL.md`
- `docs/INTEGRATIONS-ARCHITECTURE.md`
- `backend/app/utils/module_interface.py`
- `backend/app/ai/router.py`
- `backend/app/ai/service.py`
- `backend/app/briefing/config_schema.py`
- `backend/app/briefing/service.py`
- `backend/app/briefing/router.py`
- `backend/app/emailmarketing/config_schema.py`
