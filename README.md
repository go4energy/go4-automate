# go4-automate

Multi-Tenant-Plattform für Marketing-, Sales- und Engagement-Automation auf Basis von FastAPI, Vue 3 und n8n.

## Betriebsstandard

Der offizielle Standardpfad ist `Docker First`.

- Backend API: `http://localhost:8000`
- Frontend: `http://localhost:8081`
- API-Doku: `http://localhost:8000/docs`
- n8n: `http://localhost:5678`

Native/DGX-Betrieb bleibt möglich, ist aber ein separater Sondermodus und nicht mehr die kanonische Startanleitung.

## Quick Start

```bash
git clone git@github.com:go4energy/go4-automate.git
cd go4-automate

cp .env.example config/.env
# config/.env mit echten Werten befüllen

docker compose -f docker/docker-compose.yml up -d
```

## Stack

| Bereich | Technologie |
|---------|-------------|
| Backend | Python 3.12 / FastAPI / SQLAlchemy 2 |
| Frontend | Vue 3 / Pinia / Vue Router / Tailwind CSS |
| Listener | Vue 3 PWA für Briefing-Konsum |
| Datenbank | PostgreSQL 16 |
| Cache | Redis 7 |
| Workflows | n8n |
| Container | Docker Compose |

## Lokale Entwicklung

```bash
# Backend
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd frontend
npm run dev -- --host 0.0.0.0 --port 8081

# Tests
cd backend
pytest -x --tb=short

# Checks ohne File-Rewrites
cd backend
ruff check .
cd ../frontend
npm run lint:check
```

## Wichtige Hinweise

- Tenant-spezifische API-Requests sollen immer einen `X-Tenant-ID`-Header senden.
- LinkedIn-Automation ist standardmäßig nicht aktiviert. Kein Setup-Skript richtet automatisch einen Scheduler ein.
- Reverse Proxy ist kein Teil des Standard-Quickstarts. Caddy/nginx sind nur für spezielle Deployments relevant.

## Doku

- [PORTS.md](./PORTS.md) – kanonische Ports und URLs
- [docs/admin-guide.md](./docs/admin-guide.md) – Docker-Standardbetrieb, Konfiguration und Integrationen
- [docs/CONFIGURATION.md](./docs/CONFIGURATION.md) – Konfigurationsebenen und Vorrangregeln
- [docs/OPERATIONS.md](./docs/OPERATIONS.md) – Start, Update, Backup, Migration, Smoke-Checks
- [docs/DGX-SPARK-SETUP.md](./docs/DGX-SPARK-SETUP.md) – Native/DGX-Sonderbetrieb
- [CLAUDE.md](./CLAUDE.md) – interne Repo-Arbeitsregeln
