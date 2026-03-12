# go4-automate – Ports und URLs

## Kanonischer Standard: Docker First

| Service | Lokal | Zweck |
|---------|-------|-------|
| Backend API | `http://localhost:8000` | FastAPI |
| API Docs | `http://localhost:8000/docs` | OpenAPI / Swagger |
| Frontend | `http://localhost:8081` | Hauptanwendung |
| n8n | `http://localhost:5678` | Workflow-UI |
| PostgreSQL | `127.0.0.1:5432` | lokale DB-Anbindung |
| Redis | `127.0.0.1:6380` | lokaler Cache/Queue-Zugriff |

## Docker Compose Mapping

| Service | Container | Host |
|---------|-----------|------|
| Backend | `8000` | `8000` |
| Frontend | `80` | `8081` |
| PostgreSQL | `5432` | `5432` |
| Redis | `6379` | `6380` |
| n8n | `5678` | `5678` |

## Lokale Startbefehle außerhalb von Docker

```bash
# Backend lokal
cd /opt/go4-automate/backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend lokal
cd /opt/go4-automate/frontend
npm run dev -- --host 0.0.0.0 --port 8081
```

## Sondermodus: DGX / Native

Der DGX-Betrieb nutzt eigene Ports und gehört nicht zum Standardpfad:

- Backend meist `8002`
- Frontend meist `8081`
- XTTS meist `8020`

Details stehen in [docs/DGX-SPARK-SETUP.md](/opt/go4-automate/docs/DGX-SPARK-SETUP.md).
