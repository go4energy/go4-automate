# go4-automate – Operations Guide

## Standardbetrieb

Der offizielle Betriebsmodus ist `Docker First`.

```bash
cp .env.example config/.env
docker compose -f docker/docker-compose.yml up -d
```

Standard-URLs:

- Frontend: `http://localhost:8081`
- Backend: `http://localhost:8000`
- API Docs: `http://localhost:8000/docs`
- n8n: `http://localhost:5678`

## Wichtige Betriebsregeln

- Tenant-spezifische API-Aufrufe sollen immer `X-Tenant-ID` senden.
- LinkedIn-Automation ist standardmäßig deaktiviert.
- Kein Standardskript richtet automatisch einen LinkedIn-Cron ein.
- Reverse Proxy ist optional und nicht Teil des lokalen Standard-Quickstarts.

## Setup

```bash
bash scripts/setup.sh
```

Das Skript:

- erstellt lokale Virtual Environments
- installiert Backend- und Frontend-Abhängigkeiten
- legt `config/.env` an, falls sie fehlt
- startet Docker Compose
- versucht eine Alembic-Migration
- richtet keinen LinkedIn-Scheduler ein

## Update

```bash
bash scripts/update.sh
```

Das Skript:

- erstellt zuerst ein DB-Backup
- zieht den neuesten Stand von `main`
- baut Compose-Services neu
- führt eine Migration im Backend-Container aus
- prüft Backend, Frontend und n8n per Smoke-Test

## Backup

```bash
bash scripts/backup.sh
```

Es werden Dumps für:

- `go4automate`
- `n8n`

unter `./backups` abgelegt.

## Tenant anlegen

```bash
BACKEND_SECRET=... bash scripts/add-tenant.sh kunde2 "Neue Firma GmbH"
```

Hinweise:

- Ohne `BACKEND_SECRET` kann der API-Call an der Auth scheitern.
- Danach Tenant-Datei unter `config/tenants/<tenant>.env` prüfen und ergänzen.

## Pflicht-Smoke-Checks nach Betriebsänderungen

```bash
curl -sf http://localhost:8000/health
curl -sf http://localhost:8081
curl -sf http://localhost:5678/healthz
```

Zusätzlich prüfen:

- Login im Hauptfrontend
- Modul-Load nach Login
- `GET /api/v1/modules` mit Auth und `X-Tenant-ID`
- Tenant-Anlage und Tenant-spezifischer Header-Pfad

## Sensitive Module

Diese Bereiche nicht blind aktivieren:

- LinkedIn Scheduler / Browser-Automation
- WhatsApp Webhooks / produktive Accounts
- E-Mail-Provider-Webhooks
- n8n-Produktivworkflows
