# Codex Context

Stand: 2026-03-12

## Zielbild

Das Projekt wird in kontrollierten Wellen professionalisiert:

- `Docker First` als kanonischer Betriebsmodus
- konsistente Ports, Proxy-Story und Setup-Skripte
- sauberes Config- und Tenant-Modell
- belastbare Testbasis fuer weitere Aenderungen

## Bereits umgesetzt

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

- restliche historische Drift weiter bereinigen
- Config-/Security-Doku vervollstaendigen
- CI fuer die kleine Pflicht-Suite vorbereiten

## Empfohlener naechster Schritt

1. Standard-Testbefehl dokumentieren
2. Pflicht-Suite seriell verifizieren
3. eigenes Testskript oder CI-Job fuer diese Suite einfuehren

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
- `backend/tests/conftest.py`
- `pytest.ini`
