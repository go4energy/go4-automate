# Review Code

Führe ein Code-Review der aktuellen Änderungen durch.

## Schritte

1. **Änderungen anzeigen**
   ```bash
   git diff --stat
   git diff
   ```

2. **Prüfungen durchführen**
   Gehe jede geänderte Datei durch und prüfe auf:
   - [ ] Fehlendes Error-Handling (try/catch, Loading/Error States)
   - [ ] Hardcoded Values (URLs, Credentials, Magic Numbers)
   - [ ] `console.log` / `print()` Statements (müssen entfernt werden)
   - [ ] `any` Types oder fehlende Type Hints
   - [ ] SQL ohne Parameter (String-Concatenation)
   - [ ] Business-Logik in Routern (gehört in Services)
   - [ ] Fehlende Input-Validation
   - [ ] Neue Dependencies ohne Begründung
   - [ ] Sicherheitsprobleme (OWASP Top 10)

3. **Automatische Checks**
   ```bash
   # Backend
   cd backend && ruff check . && pytest -x --tb=short

   # Frontend
   cd frontend && npm run lint
   ```

4. **Bewertung**
   Gib eine Gesamtbewertung:
   - ✅ **Bereit für Merge** – Code ist sauber, Tests bestehen
   - ⚠️ **Kleinigkeiten** – Kleine Issues, aber grundsätzlich OK (Liste die Issues auf)
   - ❌ **Probleme gefunden** – Muss vor Merge behoben werden (Liste die Probleme auf)

5. **Verbesserungsvorschläge**
   - Konkrete Vorschläge mit Code-Beispielen
   - Referenz auf relevante Regeln aus `.claude/rules/`
