# go4-automate

> Marketing Automation Platform powered by n8n, FastAPI und Vue 3.

## Stack
Python 3.12 / FastAPI / Vue 3 (Composition API, JS) / Tailwind CSS / PostgreSQL 16 / Redis 7 / Docker + Caddy / n8n
Design System: https://github.com/go4energy/go4-design-system.git

## Commands
```bash
# Backend
cd backend && uvicorn app.main:app --reload --port 8000
pytest -x --tb=short
ruff check . && ruff format .

# Frontend
cd frontend && npm run dev
npm run build && npm run lint

# Docker
docker compose -f docker/docker-compose.yml up -d
docker compose -f docker/docker-compose.yml logs -f
```

## Project Structure
```
backend/app/    → FastAPI: routers/ schemas/ services/ models/ utils/
frontend/src/   → Vue 3: components/ views/ composables/ stores/ api/
docker/         → docker-compose.yml + Caddyfile
config/         → .env files
scripts/        → setup.sh, backup.sh, update.sh
```

## Rules
1. **Branch**: Niemals direkt auf `main` arbeiten. Immer `feature/`, `fix/`, `hotfix/`.
2. **Lint**: Code muss `ruff check` (Python) und `eslint` (Vue) bestehen vor Commit.
3. **Tests**: Neue Features brauchen Tests. `pytest -x` muss grün sein.
4. **Error-Handling**: Jeder API-Call braucht try/catch. Loading+Error States in Vue.
5. **Keine neuen Deps** ohne triftigen Grund. Erst Bordmittel prüfen.
6. **Business-Logik** gehört in `services/`, NIEMALS in `routers/`.

## Decision Guide
- Unsicher über Architektur? → Lies bestehenden Code, folge dem Pattern.
- Neues Package nötig? → Prüfe erst ob FastAPI/Vue/stdlib es kann.
- DB-Änderung? → Alembic Migration, nie manuell.
- Styling? → Nur Tailwind-Klassen, kein eigenes CSS. Design System nutzen.
