# Create Feature

Erstelle ein neues Feature mit korrektem Workflow. Feature-Name wird als Argument übergeben: $ARGUMENTS

## Schritte

1. **Branch erstellen**
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/$ARGUMENTS
   ```

2. **Planung**
   - Analysiere was für das Feature "$ARGUMENTS" nötig ist
   - Identifiziere betroffene Dateien (Backend: Router, Schema, Service, Model / Frontend: View, Store, Component)
   - Erstelle einen kurzen Plan

3. **Tests zuerst (TDD)**
   - Schreibe erst die Tests für das erwartete Verhalten
   - Backend: `tests/test_<feature>.py`
   - Tests müssen zunächst fehlschlagen

4. **Implementierung**
   - Backend: Model → Schema → Service → Router (in dieser Reihenfolge)
   - Frontend: Store → API → Component → View
   - Befolge alle Regeln aus `.claude/rules/`

5. **Qualitätssicherung**
   ```bash
   # Backend
   cd backend && ruff check . && ruff format --check . && pytest -x

   # Frontend
   cd frontend && npm run lint
   ```

6. **Commit**
   - Conventional Commit Format: `feat($ARGUMENTS): <beschreibung>`
   - Nur committen wenn Lint + Tests bestehen

7. **Zusammenfassung**
   - Zeige was erstellt/geändert wurde
   - Zeige Test-Ergebnisse
   - Zeige nächste Schritte (PR erstellen etc.)
