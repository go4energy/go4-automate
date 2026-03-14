# Codex Context

Stand: 2026-03-14

Hinweis fuer Wiedereinstieg:

- der aktuellste Uebergabestand fuer den Block `briefing` / AI-Modulsteuerung liegt in
  - `docs/HANDOFF-2026-03-13-BRIEFING-AI-CONTROL.md`

## Zielbild

Das Projekt wird in kontrollierten Wellen professionalisiert:

- `Docker First` als kanonischer Betriebsmodus
- konsistente Ports, Proxy-Story und Setup-Skripte
- sauberes Config- und Tenant-Modell
- belastbare Testbasis fuer weitere Aenderungen

## Bereits umgesetzt

### Integrations-Architektur fuer Microsoft Graph

- gemeinsames Zielbild fuer provider-agnostische Integrationen festgelegt
- neues Paket `backend/app/integrations/` angelegt
  - gemeinsame Typen und Interfaces fuer Mail/Kalender/Versand
  - Capability-Pruefung im Integration-Layer
  - Microsoft-Graph-Auth-, Scope- und Client-Bausteine
- Architektur-Dokument angelegt:
  - `docs/INTEGRATIONS-ARCHITECTURE.md`
- Grundsatz festgelegt:
  - `briefing` bleibt lesend
  - aktive Mail-Aktionen kommen spaeter in ein separates Mail-/Inbox-Modul
  - allgemeine Mailboxen fuer CRM/Marketing werden von persoenlichen Verbindungen getrennt

### Modul-Setup fuer Chatbot-Steuerung vereinheitlicht

- `ModuleInterface` kann jetzt ein einheitliches `setup-schema` bereitstellen
- neue Metadaten auf Modul-Config-Ebene:
  - `editable_by_ai`
  - `editable_by_enduser`
  - `secret`
  - `requires_confirmation`
  - `risk_level`
- `briefing` dient als erster Referenzfall mit:
  - AI-bearbeitbaren Modul-Parametern
  - deklarativen Modul-Aktionen
  - kleinen Enduser-Controls fuer persoenliches Briefing
- neue AI-Endpunkte in `backend/app/ai/router.py`
  - `GET /api/v1/ai/modules/{module}/setup-schema`
  - `GET /api/v1/ai/modules/{module}/config`
  - `PUT /api/v1/ai/modules/{module}/config`
  - `POST /api/v1/ai/modules/{module}/actions/{action_key}`
- Zielbild:
  - Chatbot arbeitet gegen kanonische Modul-Schemas und Modul-Interfaces
  - Enduser sieht spaeter nur die wenigen freigegebenen Controls
- aktueller Sicherheitsstand im AI-Setup-Pfad:
  - `credentials` werden getrennt von normalen Parametern behandelt
  - Secret-Werte werden beim Lesen als `***configured***` redaktiert
  - Credentials mit `source = system_config` werden ueber `TenantService.write_file_updates()` persistiert
  - `setup-schema` liefert fuer Credentials zusaetzlich `value` und `configured`
- Dokumentation:
  - `docs/AI-MODULE-CONTROL.md`

### Briefing und Email Marketing als Referenzfaelle fuer AI-Modulsteuerung

- `briefing`
  - deklarative Aktionen fuer Quellenlauf, Channel-Generierung und persoenlichen Run
  - Enduser-Controls fuer persoenliches Mail-/Kalender-Briefing
  - Credential-Schema fuer Microsoft-/Google-OAuth App-Zugaenge
  - manueller API-Run ueber `POST /api/v1/briefing/personal/run`
- `emailmarketing`
  - deklarative Aktionen fuer Provider-Verifikation und Test-E-Mail
  - Credential-Schema fuer Provider-Zugaenge

### Briefing: Persoenliches Morgenbriefing Grundgeruest

- im `briefing`-Modul wurde das Backend-Grundgeruest fuer `Mein Briefing` angelegt
- neue Modelle in `backend/app/briefing/models.py`
  - `BriefingAccountConnection`
  - `BriefingPersonalSettings`
- neue Schemas in `backend/app/briefing/schemas.py`
  - Personal Settings Request/Response
  - Account Connection Response
- neue Service-Methoden in `backend/app/briefing/service.py`
  - Personal Settings lesen/initialisieren
  - Personal Settings aktualisieren
  - Personal Connections listen
  - Personal Connection upserten
  - Personal Connection disconnecten
- neue Endpunkte in `backend/app/briefing/router.py`
  - `GET/PUT /api/v1/briefing/personal/settings`
  - `GET /api/v1/briefing/personal/connections`
  - `GET /api/v1/briefing/personal/oauth/authorize`
  - `GET /api/v1/briefing/personal/oauth/callback`
  - `POST /api/v1/briefing/personal/connections/{id}/disconnect`
- OAuth-Helfer im Router vereinheitlicht fuer Scope-, URL-, Token- und E-Mail-Aufloesung
- Alembic-Migration angelegt:
  - `backend/alembic/versions/053_personal_briefing_connections.py`

### Betrieb und Doku

- `README.md` auf den kanonischen Standardpfad ausgerichtet
- `PORTS.md` vereinheitlicht
- `docs/OPERATIONS.md` neu angelegt
- `docs/CONFIGURATION.md` neu angelegt
- `docs/admin-guide.md`, `docs/DGX-SPARK-SETUP.md`, `CLAUDE.md` an den neuen Standard angepasst
- `docker/docker-compose.yml` auf kanonische Backend-URL/Ports angepasst

### Skripte

- `scripts/setup.sh`
  - kein impliziter LinkedIn-Cron mehr
  - LinkedIn nur noch manuell/optional
- `scripts/update.sh`
  - Frontend-URL auf den neuen Standard gezogen
- `scripts/add-tenant.sh`
  - Unterstuetzung fuer `BACKEND_SECRET`
  - bessere Verifikationshinweise

### Config- und Tenant-Modell

- zentrale Tenant-Config-Logik in `backend/app/services/tenant.py`
  - `load_file_config()`
  - `merge_effective_config()`
  - `write_file_updates()`
  - `clear_config_cache()`
- `backend/app/utils/dependencies.py`
  - effektive Tenant-Config wird ueber die zentrale Merge-Logik gebaut
- `backend/app/settings/service.py`
  - keine eigene `.env`-Schreiblogik mehr
- `backend/app/setup/tools.py`
  - keine eigene `.env`-Schreiblogik mehr
  - Setup schreibt ueber `TenantService`

### Historische Drift bereinigt

- `distributor` in aktiven Codepfaden durch `campaigns` ersetzt
- Legacy-Alias bleibt nur dort erhalten, wo Rueckwaertskompatibilitaet sinnvoll ist
- `backend/app/auth/service.py`
  - Permission-Module jetzt mit `campaigns`
- `backend/app/routers/modules.py`
  - Badge-Mapping auf `campaigns`
- `backend/app/campaigns/templates/pixel_snippet.py`
  - Conversion-Endpoint auf `campaigns`

### Auth und Tenant-Haertung

- `backend/app/main.py`
  - geschuetzte tenant-scoped Routen verlangen `X-Tenant-ID`
  - `auth/login` bleibt ohne Bearer moeglich, aber nicht ohne Tenant-Kontext
- `backend/app/auth/dependencies.py`
  - `X-Backend-Secret` nutzt expliziten Tenant aus `X-Tenant-ID`, sonst `active_tenant`

### Modul-Discovery

- `backend/app/postmail/__manifest__.py`
  - `has_config_schema` auf `False` gesetzt
  - behebt den falschen Discovery-Fehler fuer nicht vorhandenes `config_schema.py`

## Testinfrastruktur

### Problem

Der bisherige Testpfad mit `sqlite+aiosqlite` hing im aktuellen Environment bereits beim Verbindungsaufbau. Das war kein Produktfehler, sondern ein Laufzeitproblem des Async-SQLite-Treibers in dieser Umgebung.

### Loesung

- `backend/tests/conftest.py` nutzt jetzt:
  - synchrones SQLite
  - `AsyncSessionShim` als kleine async-kompatible Huelle
  - volles Schema statt reduziertem Teilschema

### Verifiziert

Die folgenden Tests liefen seriell erfolgreich:

- `backend/tests/test_auth.py::test_login_requires_tenant_header`
- `backend/tests/test_setup.py::test_get_setup_status`
- `backend/tests/test_briefing.py::test_create_channel`
- `backend/tests/test_briefing.py::test_get_personal_settings_defaults`
- `backend/tests/test_briefing.py::test_update_personal_settings`
- `backend/tests/test_briefing.py::test_list_personal_connections_empty`
- `backend/tests/test_briefing.py::test_personal_oauth_authorize_microsoft_email`
- `backend/tests/test_briefing.py::test_personal_oauth_callback_creates_connection`
- `backend/tests/test_briefing.py::test_disconnect_personal_connection`
- `backend/tests/test_briefing.py::test_oauth_authorize_redirect_microsoft`
- `backend/tests/test_briefing.py::test_oauth_disconnect`

Im Repo vorhanden, aber im aktuellen Environment nicht erneut ausgefuehrt:

- `backend/tests/test_briefing.py::test_ai_module_setup_schema_redacts_configured_secret`
- `backend/tests/test_briefing.py::test_ai_module_config_updates_system_credentials_via_tenant_config_path`

### Wichtige Einschränkung

Pytest-Laeufe gegen dieselbe SQLite-Datei duerfen nicht parallel gestartet werden. Parallele Prozesse fuehren zu Kollisionen und irrefuehrenden Fehlern.

## Offene Punkte

### Kurzfristig

- Pflicht-Suite seriell komplett verifizieren:
  - `backend/tests/test_health.py`
  - `backend/tests/test_tenants.py`
  - `backend/tests/test_auth.py`
  - `backend/tests/test_setup.py`
  - `backend/tests/test_briefing.py`
- Test-Runbook dokumentieren
- optional ein Standard-Testskript anlegen, z. B. `scripts/test-backend.sh`

### Danach

- `module_parameters` / `module_context` enger mit den kanonischen Modul-Schemas koppeln
- Confirmations fuer riskante Aktionen zentralisieren
- weitere Module an dasselbe Setup-/Action-Muster anbinden
- allgemeine `integration_connections` und Capabilities modellieren
- bestehende `briefing`-Personalverbindungen spaeter in den allgemeinen Integration-Layer ueberfuehren
- Microsoft-Graph-Layer fuer `emailmarketing` wiederverwenden
- Frontend-Bereich `Mein Briefing` im `briefing`-Modul bauen
- persoenliche Verbindungen im UI verbinden/trennen und Settings pflegen
- ad hoc Testlauf und spaeter Scheduler fuer das Morgenbriefing ergaenzen
- restliche historische Drift weiter bereinigen
- Config-/Security-Doku vervollstaendigen
- CI fuer die kleine Pflicht-Suite vorbereiten

## Empfohlener naechster Schritt

1. Confirmations fuer riskante Modul-Aktionen zentral modellieren
2. danach das allgemeine Datenmodell fuer `integration_connections` und Capabilities einfuehren
3. anschliessend weitere Module an das gehartete Credential-/Setup-Muster anbinden

## Wichtige Dateipfade

- `README.md`
- `PORTS.md`
- `docs/OPERATIONS.md`
- `docs/CONFIGURATION.md`
- `backend/app/services/tenant.py`
- `backend/app/settings/service.py`
- `backend/app/setup/tools.py`
- `backend/app/main.py`
- `backend/app/auth/dependencies.py`
- `backend/app/briefing/models.py`
- `backend/app/briefing/schemas.py`
- `backend/app/briefing/service.py`
- `backend/app/briefing/router.py`
- `backend/app/briefing/config_schema.py`
- `backend/app/ai/router.py`
- `backend/app/ai/service.py`
- `backend/app/utils/module_interface.py`
- `backend/app/emailmarketing/config_schema.py`
- `backend/app/integrations/types.py`
- `backend/app/integrations/interfaces.py`
- `backend/app/integrations/service.py`
- `backend/app/integrations/microsoft_graph/client.py`
- `backend/alembic/versions/053_personal_briefing_connections.py`
- `backend/tests/conftest.py`
- `backend/tests/test_briefing.py`
- `docs/AI-MODULE-CONTROL.md`
- `docs/INTEGRATIONS-ARCHITECTURE.md`
- `pytest.ini`
