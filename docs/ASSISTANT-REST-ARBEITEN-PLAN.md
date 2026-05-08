# Assistant Rest-Arbeiten Plan

Stand: 2026-03-16

## Ziel

Der vorhandene Assistant soll von einem fortgeschrittenen Prototypen zu einem stabilen,
sicheren und testbaren Produktivpfad ausgebaut werden.

Dieser Plan basiert auf:

- `docs/ASSISTANT-UNIFIED-IMPLEMENTATION-PLAN.md`
- `backend/app/assistant/voice.py`
- `backend/app/assistant/service.py`
- `backend/app/assistant/router.py`
- `backend/app/assistant/models.py`
- `backend/tests/test_assistant.py`
- `frontend/src/stores/voiceChat.js`
- `frontend/src/components/assistant/VoiceChatPanel.vue`

## Aktueller Ist-Stand

Bereits vorhanden:

- persistente Tabellen fuer `assistant_pending_intents`, `assistant_drafts`,
  `assistant_conversation_turns` und `assistant_undo_logs`
- Voice-Tools fuer Mail lesen, suchen, Threads, Attachments, Cleanup, Undo und Kalender
- API-Endpunkte fuer Drafts, Pending-Intents, Undo-Logs, Voice, Conversation-Turns
- Frontend-Voice-Panel mit Draft-Review, Pending-Action-Review, Cleanup-Vorschau und Undo
- umfangreiche Backend-Tests fuer viele Voice-Werkzeuge

Wesentliche Luecken:

- `voice.py` ist weiterhin monolithisch
- Kontextzustand ist noch teilweise doppelt modelliert
- Providerpfad ist fachlich noch stark auf Microsoft Graph fixiert
- Migration `056` war bei `scopes` nicht robust genug
- Retry/Fallback/Policy/Audit sind nur teilweise als eigene Schichten vorhanden
- keine vollstaendige Assistant-E2E-Abdeckung

Seit diesem Arbeitszug zusaetzlich umgesetzt:

- `voice.py` wurde bereits in mehrere Schichten zerlegt:
  - `tool_registry.py`
  - `tool_executor.py`
  - `policy.py`
  - `provider_router.py`
  - `context_view.py`
  - `voice_runtime.py`
  - `llm_orchestrator.py`
- echter Anthropic-/Claude-Pfad fuer den Assistant statt faktischem Ollama-Fallback
- Mailbox-Policy-Setup fuer `INBOX/TODO/WARTEN/TEMP/ARCHIV`
- `move_to_status(...)` als zentrales Status-Tool
- tenant-konfigurierbare Category-Registry
- TEMP-Tracking mit Persistenz und Review-API
- `review_expired_temp(...)`, `review_waiting(...)`, `review_stale_todos(...)`
- `triage_batch(...)` mit hartem 10er-Limit
- REST-Endpunkte fuer `WARTEN`-/`TODO`-Review und `triage_batch(...)`
- Frontend-Anbindung fuer Mailbox-Policy, Kategorien, TEMP-Review,
  WARTEN-/TODO-Review und Triage-Batch
- Lern-/Vorschlagslogik erweitert auf `move_to_status`-Historie und
  kategoriebasiertes Feedback
- persistente Trust-/Autopilot-Parameter im Assistant-Profil:
  - `autopilot_min_confidence`
  - `autopilot_max_rule_risk`
  - `suggestion_min_confidence`
- Regeln-/Einstellungen-UI zeigt diese Schwellen jetzt sichtbar an

## Arbeitsbloecke

### Block 1: Zustandsmodell haerten

Ziel:

- Pending- und Draft-Zustand eindeutig ueber DB-Objekte referenzieren

Arbeiten:

- `pending_intent_id` als kanonisches Context-Feld nutzen
- `pending_draft_id` als kanonisches Context-Feld nutzen
- alte Context-Felder `pending_confirmation` und `pending_reply` nur noch als
  kompatible Darstellungs-/Prompt-Hilfe behandeln
- Service-Cleanup bei Send/Discard/Cancel/Execute auf beide Context-Ebenen anwenden

Abnahme:

- Voice-Response liefert stabile Pending-/Draft-IDs
- Cancel/Send/Discard/Execute loeschen IDs und Altkontext konsistent
- gezielte Assistant-Tests gruen

Status:

- abgeschlossen

### Block 2: Migration und Datenpfad haerten

Ziel:

- bestehende Verbindungen verlustfrei in `integration_connections` migrieren

Arbeiten:

- Migration `056` fuer `scopes` auf doppelte JSON-Serialisierung pruefen
- Legacy-Faelle mit bereits serialisiertem JSON abfangen
- Datentypen fuer `scopes` fachlich klarziehen
- Migrationspfad fuer frische und bestehende Installationen dokumentieren

Abnahme:

- keine doppelt serialisierten `scopes`
- keine Duplikate bei wiederholtem Lauf
- Downgrade bleibt kontrolliert

Status:

- weitgehend abgeschlossen
- Migration `056` wurde fuer doppelte JSON-Serialisierung von `scopes` gehaertet
- Restpunkt bleibt: gesamter Migrationspfad mit realen Upgrade-/Downgrade-Laeufen nochmals vollstaendig abnehmen

### Block 3: Voice-Service entflechten

Ziel:

- `voice.py` in verantwortbare technische Bausteine zerlegen

Arbeiten:

- Tool-Registry aus `voice.py` extrahieren
- Tool-Executor aus `voice.py` extrahieren
- Policy-/Confirmation-Entscheidungen aus `voice.py` herausloesen
- Context-Aufbereitung und LLM-Orchestrierung trennen
- Provider-Dispatch aus Tool-Logik entfernen

Zieldateien:

- `backend/app/assistant/tool_registry.py`
- `backend/app/assistant/tool_executor.py`
- `backend/app/assistant/policy.py`
- `backend/app/assistant/provider_router.py`

Abnahme:

- `voice.py` ist nur noch Orchestrierung
- Tool-Definitionen und Tool-Ausfuehrung sind getrennt testbar
- bestaetigungspflichtige Aktionen laufen nicht mehr ueber implizite Nebenlogik

Status:

- weitgehend abgeschlossen
- `voice.py` delegiert bereits an `tool_registry.py`, `tool_executor.py`,
  `policy.py`, `context_view.py`, `voice_runtime.py` und `llm_orchestrator.py`
- offener Rest: weitere innere Aufraeumarbeiten und spaetere Streaming-/E2E-Haertung

### Block 4: Provider- und Reliability-Layer

Ziel:

- robuster Live-Pfad fuer produktive Mail-Aktionen

Arbeiten:

- bestehende Graph-Retries zentral im Assistant-Pfad nutzbar machen
- fehlende Retry-/Backoff-Pfade im Assistant-Service identifizieren
- Fehler bei Providerzugriffen sauber in Assistant-Antworten und Logs abbilden
- Microsoft-spezifische Gates zentralisieren
- spaetere Provider-Paritaet fuer Google vorbereiten

Abnahme:

- Graph-Fehler fuehren nicht zu inkonsistenten Pending-/Draft-Zustaenden
- 429/503/504 werden kontrolliert behandelt
- unsupported provider liefert definierte Fachfehler statt verstreuter Sonderfaelle

Status:

- teilweise abgeschlossen
- zentrale Provider-Gates und Error-Mapping sind vorhanden
- Draft-/Pending-Status bleiben bei Providerfehlern stabil
- offener Rest: breitere produktive Retry-/Fallback-Haertung und spaetere Multi-Provider-Abstraktion

### Block 5: Audit und Undo vervollstaendigen

Ziel:

- nachvollziehbarer und rueckgaengig machbarer Aktionspfad

Arbeiten:

- bestehende `assistant_undo_logs` gegen alle relevanten Aktionen abgleichen
- Undo fuer weitere reversible Aktionen erweitern
- technische und fachliche Audit-Ereignisse sauber unterscheiden
- optional eigene Audit-Tabelle gemaess Masterplan vorbereiten

Abnahme:

- jede kritische Aktion hat nachvollziehbaren Persistenzpfad
- reversible Aktionen sind explizit gekennzeichnet
- Cleanup-Batches bleiben rueckgaengig soweit fachlich moeglich

Status:

- teilweise abgeschlossen
- Undo fuer `move_email`, `discard_draft`, `mark_read`, `mark_unread`,
  `flag_email` und `unflag_email` ist implementiert
- offener Rest: breitere Audit-Schicht und weitere reversible Aktionen

### Block 6: Frontend-Haertung

Ziel:

- Voice-/Review-UI auf den geharteten Backend-Zustand ausrichten

Arbeiten:

- `voiceChat`-Store auf kanonische Pending-/Draft-IDs ausrichten
- Review-Komponenten auf inkonsistente Altzustaende pruefen
- Fehlerdarstellung fuer Provider-/STT-/TTS-/LLM-Fehler verbessern
- Conversation-Turns und Undo-Kontext besser sichtbar machen

Abnahme:

- Voice-Panel zeigt Pending/Draft/Cleanup/Undo konsistent
- keine UI-Aktion haengt von impliziten Inlineobjekten ab

Status:

- weitgehend abgeschlossen
- Info-Button mit Modul-Doku eingebaut
- Assistant-UI zeigt jetzt:
  - Mailbox-Policy pro Quelle
  - Category-Registry im Regeln-Tab
  - TEMP-Review im Aktivitaets-Tab
  - WARTEN-Review pro Quelle
  - TODO-Review pro Quelle
  - Triage-Batch pro Quelle
- Trust-/Autopilot-Schwellen in Regeln und Einstellungen
- Voice-Panel zeigt Fehler-, Undo- und Conversation-Turn-Kontext sichtbar an
- offener Rest: keine wesentlichen lokalen UI-Restpunkte mehr; verbleibend sind breitere E2E-/Provider-Themen

### Block 7: Test- und Abnahmesuite

Ziel:

- belastbare Verifikation fuer den kompletten Assistant-Pfad

Arbeiten:

- gezielte Backend-Tests fuer neue Context-IDs
- Service-Tests fuer Clear-/Execute-/Discard-Pfade
- Migrations-Tests fuer `056`
- Assistant-API-Tests fuer Drafts/Pending/Undo
- spaeter Frontend- und E2E-Tests fuer Voice-Flows

Pflichtfaelle:

- Email lesen
- Thread lesen
- Entwurf erstellen, bearbeiten, senden
- Delete/Move nur nach serverseitiger Bestaetigung
- Cleanup-Vorschau und Cleanup-Ausfuehrung
- Undo fuer reversible Aktionen

Abnahme:

- kritische Assistant-Tests gruen
- bekannte Haenger sind eingegrenzt oder beseitigt
- produktionsrelevante Flows sind reproduzierbar testbar

Status:

- teilweise abgeschlossen
- viele gezielte Backend- und Router-/Service-Tests sind gruen
- bekannte Haenger betreffen weiterhin Teile der alten HTTP-/ASGI-Testinfra
- offener Rest: breitere API-Abnahme, Migrationslaeufe, Frontend-E2E und produktive End-to-End-Pruefung

### Block 8: Mailbox-Policy und Statusmodell

Ziel:

- das 5-Status-Modell fachlich und technisch als echten Produktpfad etablieren

Arbeiten:

- Mailbox-Policy-API und Setup fuer `TODO/WARTEN/TEMP/ARCHIV`
- `INBOX` explizit als echter Outlook-Posteingang, kein Unterordner
- `move_to_status(...)` statt freier Status-Foldermoves
- Folder-ID-Caching in `assistant_sources.settings_json`

Abnahme:

- pro Quelle ist die Mailbox-Policy sichtbar
- Status-Folder sind zugeordnet oder per Setup anlegbar
- Status-Moves laufen ueber gecachte Folder-IDs

Status:

- abgeschlossen im Backend
- erste Frontend-Anbindung im Konten-Tab vorhanden

### Block 9: Category-Registry

Ziel:

- feste und Projekt-Kategorien tenantweit sauber verwalten

Arbeiten:

- persistente Tabelle `assistant_category_registry`
- API fuer Listen/Anlegen/Aendern/Loeschen
- System-Defaults automatisch seeden
- Projekt-Kategorien auf maximal 15 aktive Kategorien begrenzen

Abnahme:

- feste Defaults sind vorhanden
- Projekt-Kategorien werden normiert als `Projekt: <Name>`
- System-Defaults sind nicht blind loeschbar

Status:

- abgeschlossen im Backend
- erste Frontend-Anbindung im Regeln-Tab vorhanden

### Block 10: TEMP-Tracking und Reviews

Ziel:

- `TEMP` als echter Zustand mit Pflichtdatum und taeglichem Review

Arbeiten:

- persistente Tabelle `assistant_temp_tracking`
- `move_to_status(status='TEMP')` speichert `expires_at`
- `set_temp_expiry(...)`
- `review_expired_temp(...)`

Abnahme:

- keine finale TEMP-Aktion ohne Datum
- abgelaufene TEMP-Mails sind serverseitig auflistbar
- TEMP-Review ist im Frontend sichtbar

Status:

- abgeschlossen fuer den Grundpfad
- offener Rest: spaetere produktive Aktionsvorschlaege aus dem TEMP-Review

### Block 11: WARTEN-/TODO-Review und Batch-Triage

Ziel:

- Review- und Triage-Logik gemaess Produktspezifikation verankern

Arbeiten:

- `review_waiting(...)`
- `review_stale_todos(...)`
- `triage_batch(...)`
- Batch-Hardlimit von 10 Mails pro Turn

Abnahme:

- WARTEN- und TODO-Reviews lesen die gemappte Mailbox-Policy
- Triage laedt pro Turn nie mehr als 10 Mails

Status:

- abgeschlossen fuer Voice-, REST- und Frontend-Grundpfad
- offener Rest: spaetere Aktionsvorschlaege direkt aus Reviews ausfuehren

## Empfohlene Reihenfolge ab jetzt

1. Reliability-/Provider-Pfad weiter haerten
2. breitere API-/E2E-Abnahme fuer den Graph-Produktpfad
3. produktive End-to-End-Pruefung gegen reale externe Provider

## Zuletzt konkret umgesetzt

- kanonische Context-Felder `pending_intent_id` und `pending_draft_id`
- Migration `056` fuer `scopes` gehaertet
- Provider-/Anthropic-Pfad fuer Assistant korrigiert
- Mailbox-Policy-Setup mit Folder-ID-Caching
- `move_to_status(...)` als Kern-Tool
- Category-Registry mit Migration `059`
- TEMP-Tracking mit Migration `060`
- Voice-/API-Pfade fuer:
  - `review_expired_temp(...)`
  - `review_waiting(...)`
  - `review_stale_todos(...)`
  - `triage_batch(...)`
- Frontend fuer:
  - Modul-Doku-Viewer
  - Mailbox-Policy im Konten-Tab
  - Kategorien im Regeln-Tab
  - TEMP-Review im Aktivitaets-Tab
  - WARTEN-/TODO-Review im Aktivitaets-Tab
  - Triage-Batch im Aktivitaets-Tab
- Lernlogik fuer:
  - `move_to_status`-basierte Regelvorschlaege
  - kategoriebasiertes Feedback in Regelvorschlaegen
- Trust-/Autopilot-Modell mit Migration `061`
- Regeln-/Settings-UI fuer:
  - Suggestion-Minimum
  - Autopilot-Minimum
  - Max Rule Risk
- Voice-UI fuer:
  - sichtbaren Fehlerstatus
  - sichtbare Conversation-Turn-Historie
  - sichtbaren Undo-Kontext

## Letzter verifizierter Stand

Gezielt gruen verifiziert:

- Mailbox-Policy
- `move_to_status(...)`
- Category-Registry
- TEMP-Tracking und TEMP-Review
- `review_waiting(...)`
- `review_stale_todos(...)`
- `triage_batch(...)`
- Assistant-REST fuer Reviews/Triage
- Lernlogik fuer Status-/Kategorie-Vorschlaege
- Trust-/Autopilot-Konfiguration im Profilpfad
- Voice-UI fuer Fehler-/Undo-/Conversation-Kontext

Zuletzt gelaufene gezielte Test-Sets:

- `11 passed` fuer Mailbox-Policy / Kategorien / TEMP
- `13 passed` fuer Reviews / Batch / Statuspfad
- `6 passed` fuer neue Router-Reviews/Triage und Lernlogik
- `5 passed` fuer Trust-/Profilpfad und Learning-Gates

Frontend:

- `vite build` erfolgreich
- `vite build` nach Voice-UI-Erweiterung erneut erfolgreich

## Naechster direkter Arbeitsblock

Wenn spaeter fortgesetzt wird, direkt hier ansetzen:

1. Reliability-/Provider-Pfad nachziehen, wo noch keine zentrale Produktabnahme existiert
2. Breitere API-/E2E-Abnahme nachziehen; HTTP-/ASGI-Haenger bleiben dabei aktueller Infra-Restpunkt
3. Produktive End-to-End-Pruefung mit realen Providerverbindungen; ohne diese bleibt die Vollabnahme extern blockiert
