# go4-automate – Configuration Model

## Zielbild

Das Projekt nutzt drei Konfigurationsebenen mit klarer Verantwortung:

- `config/.env`
  - globale Infrastruktur- und Integrationswerte
  - Beispiele: Datenbank, Redis, Backend-Secret, API-Keys, Basis-URLs
- `config/tenants/<tenant>.env`
  - tenant-spezifische fachliche Defaults
  - Beispiele: Company Name, Tonalität, Zielgruppe, Ads-Parameter
- `tenant.config` in der Datenbank
  - runtime-seitige Overrides und UI-Änderungen pro Tenant
  - überschreibt die Werte aus `config/tenants/<tenant>.env`

## Priorität der Auflösung

Für tenant-spezifische Laufzeitkonfiguration gilt:

1. Datei `config/tenants/<tenant>.env`
2. DB-Overrides aus `tenant.config`

Für globale Plattformwerte gilt:

1. `config/.env`
2. Defaults aus `backend/app/config.py`

## Schreibregeln

- Globale Secrets und Infrastrukturwerte gehören in `config/.env`.
- Tenant-Fachwerte gehören in `config/tenants/<tenant>.env`.
- Änderungen aus UI/Setup werden in `tenant.config` abgelegt und zusätzlich in die Tenant-Datei geschrieben, damit Dateisystem und Runtime nicht auseinanderlaufen.
- Tenant-scoped API-Requests müssen explizit `X-Tenant-ID` senden.

## Sensitive Werte

Nicht im Chat oder UI im Klartext spiegeln:

- API-Keys
- Tokens
- Passwörter
- `BACKEND_SECRET`
- `JWT_SECRET`

## Betriebsrelevante Hinweise

- `X-Backend-Secret` ist nur für interne Service-Aufrufe gedacht.
- LinkedIn-Automation ist kein Teil des Standardbetriebs.
- Native/DGX kann abweichende Ports verwenden, ändert aber nichts am Config-Modell.
