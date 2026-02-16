# go4.automate

Marketing Automation Platform powered by n8n, FastAPI und Vue 3.

## Quick Start

```bash
# 1. Repository klonen
git clone <repo-url> go4.automate
cd go4.automate

# 2. Environment konfigurieren
cp .env.example config/.env
# config/.env mit echten Werten befüllen

# 3. Starten
docker compose -f docker/docker-compose.yml up -d
```

## Stack

| Bereich | Technologie |
|---------|-------------|
| Backend | Python 3.12 / FastAPI / SQLAlchemy 2 |
| Frontend | Vue 3 (Composition API) / Tailwind CSS |
| Datenbank | PostgreSQL 16 |
| Cache | Redis 7 |
| Workflows | n8n (self-hosted) |
| Container | Docker + Docker Compose |
| Reverse Proxy | Caddy 2 |
| Hosting | Hetzner Cloud VPS |

## URLs

| Service | URL |
|---------|-----|
| Frontend | http://localhost:80 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| n8n | http://localhost:5678 |

## Development

```bash
# Backend (lokal)
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Frontend (lokal)
cd frontend && npm run dev

# Tests
cd backend && pytest -x --tb=short

# Lint
cd backend && ruff check . && ruff format .
cd frontend && npm run lint
```

Detaillierte Informationen: siehe [CLAUDE.md](./CLAUDE.md)
