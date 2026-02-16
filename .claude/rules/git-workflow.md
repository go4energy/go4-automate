# Git Workflow

## Branch-Strategie
- `main` – Production, immer stabil, NIEMALS direkt committen
- `feature/<name>` – Neue Features (z.B. `feature/lead-scoring`)
- `fix/<name>` – Bugfixes (z.B. `fix/email-validation`)
- `hotfix/<name>` – Kritische Production-Fixes

## Branch erstellen
```bash
git checkout main
git pull origin main
git checkout -b feature/lead-import
```

## Conventional Commits
Format: `<type>(<scope>): <description>`

### Typen
- `feat` – Neues Feature
- `fix` – Bugfix
- `refactor` – Code-Umbau ohne Funktionsänderung
- `docs` – Dokumentation
- `test` – Tests hinzufügen/ändern
- `chore` – Build, Dependencies, Config
- `style` – Formatting, kein Code-Change
- `perf` – Performance-Verbesserung

### Scopes
- `backend`, `frontend`, `docker`, `ci`, `db`
- Oder Feature-Name: `leads`, `auth`, `dashboard`

### Beispiele
```
feat(leads): add CSV import endpoint
fix(frontend): correct date format in lead table
refactor(backend): extract email service from lead service
chore(docker): update postgres to 16.4
test(leads): add integration tests for lead scoring
```

## Vor jedem Commit
```bash
# Backend
cd backend && ruff check . && ruff format --check . && pytest -x

# Frontend
cd frontend && npm run lint
```

Commit nur wenn Lint + Tests bestehen.

## Merge
- Feature-Branches werden via Pull Request in `main` gemergt
- Squash Merge bevorzugt für saubere History
- Branch nach Merge löschen
