# go4-automate

> Marketing Automation Platform powered by n8n, FastAPI und Vue 3.

## ABSOLUT VERBOTEN ohne explizites GO vom User
1. **Keine LinkedIn-Aktionen starten** — kein Scheduler, kein Worker, kein Browser öffnen ohne Freigabe
2. **Keine Software-Änderungen** — kein Code schreiben/editieren ohne explizites GO
3. **Kein Debugging ausführen** — jeden einzelnen Schritt vorher beschreiben und auf Freigabe warten
4. **Keine Endlos-Schleifen** — niemals Retry-Loops ohne Abbruchbedingung und User-Kontrolle
5. **Cron-Jobs** — niemals automatisch aktivieren, immer manuell und mit Freigabe

## Stack
Python 3.12 / FastAPI / Vue 3 (Composition API, JS) / Tailwind CSS / PostgreSQL 16 / Redis 7 / Docker + Caddy / n8n
Design System: https://github.com/go4energy/go4-design-system.git

## Offizieller Betriebsmodus
Standard für Doku, Skripte und Support ist `Docker First`.

## Ports (WICHTIG!)
| Service  | Port | Host              |
|----------|------|-------------------|
| Backend  | 8000 | localhost         |
| Frontend | 8081 | localhost         |
| n8n      | 5678 | localhost         |

**Login:** team@go4.energy / Tenant: go4energy

## Commands
```bash
# Backend (Docker-Standard: 8000)
cd backend && source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pytest tests/ -v --tb=short
ruff check . && ruff format .

# Background Workers
python run_engagement_worker.py   # Engagement Brain (alle 15 Min)
python run_email_worker.py        # Email-Kampagnen (alle 5 Sek)

# LinkedIn Scheduler (nur manuell, niemals Standardbetrieb)
# Kein automatisches Cron-Setup via scripts/setup.sh
python run_linkedin_scheduler.py  # Einmal-Check + Worker

# Frontend
cd frontend && npm run dev -- --host 0.0.0.0 --port 8081
npm run build && npm run lint
npm run test              # Vitest einmalig
npm run test:watch        # Vitest im Watch-Modus
npm run test:coverage     # Mit Coverage-Report
npm run e2e               # Playwright E2E-Tests
npm run e2e:headed        # E2E mit sichtbarem Browser
npm run e2e:ui            # Playwright UI-Modus
npm run e2e:report        # Letzten Report anzeigen

# Docker
docker compose -f docker/docker-compose.yml up -d
docker compose -f docker/docker-compose.yml logs -f
```

## Native/DGX
- Native/DGX ist ein Sondermodus und wird getrennt dokumentiert.
- Abweichende Ports wie `8002` sind dort erlaubt, aber nicht der Standardpfad dieser Repo-Doku.

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

## Testing ist PFLICHT
- Schreibe für JEDE neue Funktion automatisch Unit-Tests
- Führe ALLE Tests aus, BEVOR du sagst, dass du fertig bist
- Wenn ein Test fehlschlägt, behebe den Bug selbstständig
- Frage NICHT nach Erlaubnis zum Testen – tu es einfach

## Workflow
1. Code schreiben
2. Tests schreiben
3. Tests ausführen
4. Bugs fixen
5. Tests erneut ausführen
6. Erst wenn ALLE Tests grün sind → fertig melden

---

## E2E-Tests für Module (WICHTIG!)

### Teststruktur
```
frontend/e2e/
├── login.spec.js           # Auth-Tests
├── navigation.spec.js      # Navigation
├── comprehensive/          # UMFASSENDE MODULTESTS
│   ├── contacts.spec.js
│   ├── crm.spec.js
│   ├── funnels.spec.js
│   ├── collector.spec.js
│   ├── creator.spec.js
│   ├── briefing.spec.js
│   ├── surveys.spec.js
│   └── settings.spec.js
└── modules/                # Basis-Tests
```

### Wann Tests anpassen?
**PFLICHT: Testskripte MÜSSEN aktualisiert werden, wenn:**
1. Neue Buttons/Aktionen hinzugefügt werden
2. Formulare geändert werden (neue Felder, andere Validierung)
3. Navigation/Routing sich ändert
4. CRUD-Operationen geändert werden
5. UI-Elemente umbenannt oder verschoben werden

### Wann Tests ausführen?
**PFLICHT: E2E-Tests für betroffene Module MÜSSEN laufen, wenn:**
1. Ein Modul implementiert oder geändert wird
2. Der User explizit "teste das Modul" oder "E2E-Tests" anfordert
3. Vor einem Merge/Release

### Wie Tests ausführen?
```bash
# Einzelnes Modul testen
npx playwright test e2e/comprehensive/contacts.spec.js

# Alle Module testen
npx playwright test e2e/comprehensive/

# Mit Video (für Review)
npx playwright test --video=on

# Mit sichtbarem Browser
npx playwright test --headed --slowmo=500

# Report anzeigen
npx playwright show-report
```

### Test-Checkliste pro Modul
Jeder comprehensive Test deckt ab:
- [ ] Seite lädt korrekt
- [ ] Alle Tabs/Navigation funktionieren
- [ ] Alle CRUD-Operationen (Create, Read, Update, Delete)
- [ ] Alle Buttons und Aktionen
- [ ] Alle Formulare mit Validierung
- [ ] Filter und Suche
- [ ] Bulk-Aktionen (falls vorhanden)
- [ ] Detail-Ansichten
- [ ] Cleanup: Test-Daten werden gelöscht

### Bei User-Anfrage "teste Modul X"
1. Comprehensive Test für Modul X ausführen:
   ```bash
   npx playwright test e2e/comprehensive/[modul].spec.js --headed
   ```
2. Bei Fehlern: Fehler analysieren und fixen
3. Tests erneut ausführen bis grün
4. Report zeigen oder Videos bereitstellen

### Module ↔ Testdateien
| Modul | Testdatei |
|-------|-----------|
| Contacts | `e2e/comprehensive/contacts.spec.js` |
| CRM (Deals, Pipelines, Tasks) | `e2e/comprehensive/crm.spec.js` |
| Funnels | `e2e/comprehensive/funnels.spec.js` |
| Collector | `e2e/comprehensive/collector.spec.js` |
| Creator | `e2e/comprehensive/creator.spec.js` |
| Briefing | `e2e/comprehensive/briefing.spec.js` |
| Surveys | `e2e/comprehensive/surveys.spec.js` |
| Settings | `e2e/comprehensive/settings.spec.js` |

---

## Keine unnötigen Rückfragen
- Triff eigenständige Entscheidungen bei Implementierungsdetails
- Frage nur bei echten Unklarheiten in der Anforderung
- Teste selbstständig, ohne auf Bestätigung zu warten

## Realitätscheck vor Implementierung
- **Erst prüfen, dann planen**: Vor jedem Plan prüfen was wirklich existiert (Dateien lesen, nicht annehmen)
- **Kleinere Schritte**: Ein Feature → testen → nächstes Feature. Nicht 10 Dateien auf einmal
- **API-First**: Backend-Endpoint mit curl testen BEVOR Frontend gebaut wird
- **Smoke Test nach jeder Änderung**: Nach Code-Änderung prüfen ob Server noch startet
- **"Fertig" heißt getestet**: Nicht "Code geschrieben" sondern "funktioniert im Browser/API"

## Post-Implementierung Checkliste
Nach jedem neuen Modul oder Feature mit DB-Änderungen IMMER:
1. **Migration ausführen**: `cd backend && alembic upgrade head`
2. **Backend neustarten**: Backend-Prozess killen und neu starten
3. **Login testen**: Sicherstellen dass Auth noch funktioniert
4. **Frontend lint**: `cd frontend && npm run lint`

## WICHTIG: Lint-Sicherheit

Das `npm run lint` Kommando kann Dateien beschädigen wenn der Vite Dev-Server läuft.

### Sichere Vorgehensweise:
1. Frontend Dev-Server stoppen: `pkill -f 'vite.*8081'`
2. Lint ausführen: `npm run lint`
3. Frontend neu starten: `npm run dev -- --host 0.0.0.0 --port 8081`

### Alternative: Nur Check ohne Write
```bash
eslint . --ext .vue,.js  # ohne --fix
prettier --check 'src/**/*.{vue,js,json}'  # ohne --write
```
