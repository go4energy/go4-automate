# Setup Project

Richte das Projekt für lokale Entwicklung ein. Prüfe alle Voraussetzungen und starte die Services.

## Schritte

1. **Prüfe Voraussetzungen**
   - Python >= 3.12: `python3 --version`
   - Node.js >= 20: `node --version`
   - Docker + Compose: `docker --version && docker compose version`
   - Falls etwas fehlt: Stoppe und informiere den User

2. **Backend Setup**
   ```bash
   cd backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Frontend Setup**
   ```bash
   cd frontend
   npm ci
   ```

4. **Environment**
   - Prüfe ob `config/.env` existiert
   - Falls nicht: kopiere `.env.example` nach `config/.env`
   - Informiere User dass er die Werte anpassen muss

5. **Docker Services starten**
   ```bash
   docker compose -f docker/docker-compose.yml up -d
   ```

6. **Healthcheck**
   - Warte 10 Sekunden
   - Prüfe: `curl -f http://localhost:8000/health`
   - Prüfe: `docker compose -f docker/docker-compose.yml ps` (alle healthy?)

7. **Zusammenfassung**
   - Zeige Status aller Services
   - Zeige URLs: Backend http://localhost:8000, Frontend http://localhost:5173
   - Zeige nächste Schritte
