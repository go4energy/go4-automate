# Assistant Module

Persoenlicher KI-Assistent fuer Multi-Account Mail/Kalender, Briefing, Voice und Regeln.

Nachladbares, lizenzierbares Plattform-Modul. Nicht Teil der Standardauslieferung.

## Architektur

```
IntakeService          ClassifierService      RuleEngine
(Provider-API)    -->  (Wichtigkeit,      --> (Kriterien-
 Mail + Kalender        Reply-Bedarf)         Matching)
      |                      |                    |
      v                      v                    v
 assistant_events    assistant_decisions    assistant_actions
 assistant_items                           (suggested/queued)
      |
      v
 BriefingRun (Text-Zusammenfassung)
```

## Dateien

| Datei | Funktion |
|-------|----------|
| `__manifest__.py` | Modulregistrierung, Routen, Sidebar |
| `models.py` | 11 SQLAlchemy Models |
| `schemas.py` | Pydantic Request/Response Schemas |
| `router.py` | 22 API-Endpunkte |
| `service.py` | Orchestrierung, CRUD, Briefing-Run |
| `config_schema.py` | ModuleInterface (Config, Status, Metrics, Actions) |
| `intake.py` | Mail/Kalender-Polling, Token-Refresh, Event-Dedup |
| `classifier.py` | Regelbasierte Wichtigkeitsbewertung |
| `rules.py` | Rule Engine (Kriterien-Matching, Action-Erzeugung) |
| `learning.py` | Feedback-Analyse, Regelvorschlaege |
| `actions.py` | Queued Actions ausfuehren |
| `scheduler.py` | Worker-Loop fuer Hintergrundverarbeitung |

## Datenmodell

### Plattform-Tabellen

| Tabelle | Zweck |
|---------|-------|
| `integration_connections` | OAuth-Verbindungen (provider-agnostisch) |
| `integration_connection_capabilities` | Granulare Rechte pro Verbindung |

### Assistant-Tabellen

| Tabelle | Zweck |
|---------|-------|
| `assistant_profiles` | User-Konfiguration (LLM, TTS, STT, Zeitzone) |
| `assistant_sources` | Welche Verbindung fuer Briefing/Voice/Reply/Autopilot |
| `assistant_events` | Rohereignisse mit Dedup (SHA-256 Hash) |
| `assistant_items` | Normalisierte Mail/Kalender-Objekte |
| `assistant_decisions` | Klassifikation (Wichtigkeit, Reply-Bedarf) |
| `assistant_rules` | Explizite und gelernte Triage-Regeln |
| `assistant_actions` | Vorgeschlagene/ausgefuehrte Aktionen |
| `assistant_feedback` | User-Rueckmeldungen fuer Lernlogik |
| `assistant_conversations` | Voice/Chat-Dialogzustand |

Migration: `054_assistant_module.py`

## API-Endpunkte

Alle unter `/api/v1/assistant/`. Auth via `Bearer`-Token + `X-Tenant-ID`.

### Profil

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/profile` | Profil laden (oder Default anlegen) |
| PUT | `/profile` | Profil aktualisieren |

### Quellen

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/sources` | Alle verbundenen Quellen |
| POST | `/sources` | Verbindung als Quelle hinzufuegen |
| PUT | `/sources/{id}` | Quelle aktualisieren |
| DELETE | `/sources/{id}` | Quelle entfernen |

### Items

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/items` | Items auflisten (Filter: status, item_type) |
| GET | `/items/{id}` | Einzelnes Item |
| GET | `/items/{id}/decisions` | Klassifikationen fuer ein Item |

### Feedback

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| POST | `/items/{id}/feedback` | Feedback zu einem Item abgeben |

### Regeln

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/rules` | Alle Regeln |
| POST | `/rules` | Neue Regel anlegen |
| PUT | `/rules/{id}` | Regel aktualisieren |
| DELETE | `/rules/{id}` | Regel loeschen |

### Regelvorschlaege

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/rule-suggestions` | KI-generierte Regelvorschlaege |
| POST | `/rule-suggestions/apply` | Vorschlag als Regel uebernehmen |

### Aktionen / Freigaben

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/actions/pending` | Offene Freigaben |
| POST | `/actions/{id}/approve` | Aktion freigeben |
| POST | `/actions/{id}/reject` | Aktion ablehnen |

### Briefing

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| POST | `/briefing/run` | Briefing-Lauf starten |

### Dashboard

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/dashboard` | Schnellstatistik |

### Modulsteuerung (automatisch via ModuleInterface)

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/config` | Aktuelle Konfiguration |
| PUT | `/config` | Konfiguration aendern |
| GET | `/config/schema` | Parameter-Schema |
| GET | `/config/setup-schema` | Setup-Schema fuer AI/Admin |
| GET | `/status` | Modulgesundheit |
| GET | `/metrics?days=7` | KPIs |

## Mail-Polling (IntakeService)

### Ablauf

1. **Token entschluesseln** via `briefing/oauth.py` (Fernet)
2. **Token pruefen** — wenn < 5 Min bis Ablauf: automatisch refreshen
3. **Provider-Client erstellen** (MicrosoftGraphClient mit Access-Token)
4. **Mails holen** via `MicrosoftGraphMailReadProvider.list_messages()`
5. **Kalender holen** via `MicrosoftGraphCalendarProvider.list_events()`
6. **Dedup** — SHA-256 Hash des Payloads gegen `assistant_events` pruefen
7. **Items erzeugen** — normalisierte `assistant_items` in DB
8. **Connection-Status** — `last_synced_at` + `status=connected`

### Unterstuetzte Provider

| Provider | Mail | Kalender | Token-Refresh |
|----------|------|----------|---------------|
| Microsoft Graph | Ja | Ja | Ja |
| Google Workspace | Vorbereitet | Vorbereitet | Ja |
| IMAP | Noch nicht | - | - |

### Fehlerbehandlung

- Token-Fehler: Connection auf `status=error`, `last_error` gesetzt
- API-Fehler: geloggt, naechste Quelle wird weiter verarbeitet
- Kein Refresh-Token: Fehlerstatus, kein stilles Verwerfen

## Briefing-Run

`POST /briefing/run` fuehrt die komplette Pipeline aus:

1. **Intake** — neue Mails/Termine von allen aktiven Quellen holen
2. **Klassifikation** — Items nach Wichtigkeit bewerten (high/medium/low)
3. **Rule Engine** — User-Regeln auf Items anwenden, Aktionen erzeugen
4. **Text-Briefing** — priorisierte Zusammenfassung generieren

Klassifikation (regelbasiert):
- `high`: Kalender, dringende Betreff-Signale (dringend, urgent, deadline)
- `low`: Newsletter, no-reply, notification, digest
- `medium`: alles andere

## Rule Engine

Regeln werden vor dem LLM ausgewertet (Rule Engine vor LLM).

### Match-Kriterien

```json
{
  "sender_domain": "newsletter.example.com",
  "sender_contains": "noreply",
  "subject_contains": "Newsletter",
  "subject_regex": "Rechnung.*\\d+",
  "item_type": "email",
  "keywords": ["rechnung", "invoice", "payment"]
}
```

### Risikostufen

| Stufe | Aktionen | Bestaetigung |
|-------|----------|--------------|
| `low` | label, prioritize, mute | Nein (auto queued) |
| `medium` | archive, move | Ja (suggested) |
| `high` | delete, send | Ja (suggested) |

### Lernlogik

1. User gibt Feedback auf Items (keep, ignore, move, delete)
2. LearningService erkennt Muster (>= 3x gleicher Feedback-Typ pro Absender)
3. Regelvorschlag wird generiert
4. User kann Vorschlag uebernehmen oder verwerfen
5. Uebernommene Regel wird mit `origin=learned` gespeichert

## Worker

```bash
# Einmalig
python run_assistant_worker.py --tenant go4energy --user 1

# Mit konfigurierbarem Intervall (Standard: 300s)
python run_assistant_worker.py --tenant go4energy --user 1 --interval 60
```

Der Worker fuehrt zyklisch aus:
1. Intake (Mail/Kalender-Polling)
2. Klassifikation
3. Rule Engine
4. Queued Actions ausfuehren

## Frontend

### Tabs

| Tab | Route | Inhalt |
|-----|-------|--------|
| Mein Assistant | `/assistant/dashboard` | Stats, letztes Briefing |
| Konten | `/assistant/accounts` | Verbundene Quellen, Rollen-Flags |
| Regeln | `/assistant/rules` | CRUD, Toggle, Risikostufe |
| Aktivitaet | `/assistant/activity` | Items mit Status, Sender, Datum |
| Freigaben | `/assistant/approvals` | Pending Actions, Approve/Reject |
| Einstellungen | `/assistant/settings` | LLM, TTS, STT, Zeitzone, Delivery-Zeit |

### Dateien

| Datei | Zweck |
|-------|-------|
| `views/AssistantView.vue` | Haupt-View mit 6 Tabs |
| `stores/assistant.js` | Pinia Store |
| `api/assistant.js` | Axios API-Client |

## Tests

```bash
cd backend && source .venv/bin/activate
pytest tests/test_assistant.py -v
```

18 Tests:
- Profile: auto-create, update
- Rules: CRUD-Zyklus, ungueltige Risikostufe
- Dashboard: Stats-Struktur
- Items: leere Liste, 404
- Actions: leere Pending-Liste
- Sources: leere Liste, ungueltige Connection
- Briefing: leerer Run
- Classifier: Wichtigkeit (dringend → high, newsletter → low)
- Rule Engine: Match/No-Match
- Intake: Hash-Konsistenz, Message-Ingestion, Token-Refresh

## Konfiguration (ModuleInterface)

| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `llm_provider` | enum | ollama | LLM fuer Klassifikation/Briefing |
| `llm_model` | string | - | Modellname |
| `tts_provider` | enum | piper | TTS fuer Audio-Briefing |
| `tts_voice` | string | de_DE-thorsten-high | Stimme |
| `stt_provider` | enum | faster-whisper | STT fuer Spracheingabe |
| `autopilot_enabled` | boolean | false | Automatische Aktionen |
| `autopilot_min_confidence` | number | 0.85 | Mindest-Confidence fuer Autopilot |
| `autopilot_max_rule_risk` | enum | medium | Hoechste Risikostufe fuer Autopilot |
| `suggestion_min_confidence` | number | 0.70 | Untergrenze fuer sichtbare Regelvorschlaege |
| `max_items_per_run` | integer | 30 | Items pro Briefing-Lauf |

## Noch nicht implementiert

- Audio-Briefing (TTS-Aufruf im Briefing-Run)
- STT/Voice-Pipeline (faster-whisper)
- LLM-basierte Klassifikation (aktuell nur regelbasiert)
- Google Workspace Provider (OAuth-Flow)
- IMAP/SMTP Provider
- E2E-Tests (Playwright)
