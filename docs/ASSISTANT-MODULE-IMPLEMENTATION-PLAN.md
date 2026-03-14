# Assistant Module Implementation Plan

Stand: 2026-03-14

## Ziel

Dieses Dokument beschreibt die konkrete technische Umsetzung fuer das neue nachladbare Modul `assistant`.

Es ist das Delivery-Dokument zum Architekturkonzept aus:

- [ASSISTANT-MODULE-ARCHITECTURE.md](/opt/go4-automate/docs/ASSISTANT-MODULE-ARCHITECTURE.md)
- [ASSISTANT-MODULE-FULL-ROADMAP.md](/opt/go4-automate/docs/ASSISTANT-MODULE-FULL-ROADMAP.md)

Es geht hier nicht um Vision, sondern um:

- konkrete Pakete
- konkrete Tabellen
- konkrete APIs
- konkrete Frontend-Bereiche
- konkrete Reihenfolge

## Dokumentstatus

Dieses Dokument ist die Single Source of Truth fuer die technische Umsetzung.

Die folgenden Dokumente bleiben Kontext- und Zielbilddokumente:

- [ASSISTANT-MODULE-ARCHITECTURE.md](/opt/go4-automate/docs/ASSISTANT-MODULE-ARCHITECTURE.md)
- [ASSISTANT-MODULE-FULL-ROADMAP.md](/opt/go4-automate/docs/ASSISTANT-MODULE-FULL-ROADMAP.md)

## Modulname

Arbeitsname:

- `assistant`

## Lieferprinzip

Der Assistant wird als neues Plattform-Modul gebaut:

- nachladbar
- lizenzierbar
- deaktivierbar
- nicht Teil der Standardauslieferung

## Delivery-Grundsaetze

1. Nicht im `briefing` aufbauen, sondern eigenes Modul.
2. Integrationen zentral ueber den gemeinsamen Integrations-Layer.
3. Rule Engine vor LLM.
4. Keine riskanten Mail-Aktionen im ersten produktiven Release.
5. Alles auditierbar.
6. Feedback strukturiert speichern.
7. Local-first auf GB10 ist der Standard.
8. Externe LLM-/STT-/TTS-Provider nur als Fallback.

## Bereits vorhandene Basis

Der Plan startet nicht auf der gruenen Wiese.

Bereits vorhanden:

- `backend/app/integrations/`
- Provider-Interfaces:
  - `MailReadProvider`
  - `CalendarReadProvider`
  - `MailSendProvider`
  - `MailActionProvider`
- Microsoft Graph Implementierung fuer OAuth, Token-Refresh, Mail, Kalender und Mail-Aktionen
- bestehende Token-Verschluesselung
- `briefing_account_connections` aus Migration `053`

Konsequenz:

- der Assistant baut auf vorhandener Plattform-Infrastruktur auf
- das Delivery-Ziel ist Verallgemeinerung und Migration, nicht Neuaufbau

## Zielstruktur im Backend

Neues Paket:

- `backend/app/assistant/`

Anfangs vorgesehene Dateien:

- `__init__.py`
- `__manifest__.py`
- `config_schema.py`
- `models.py`
- `schemas.py`
- `router.py`
- `service.py`
- `intake.py`
- `rules.py`
- `classifier.py`
- `actions.py`
- `voice.py`
- `learning.py`
- `scheduler.py`

## Zielstruktur im Frontend

Neue Frontend-Bereiche:

- `frontend/src/views/AssistantView.vue`
- `frontend/src/stores/assistant.js`
- `frontend/src/api/assistant.js`

Moegliche Unterkomponenten:

- `AssistantConnectionsPanel.vue`
- `AssistantRulesPanel.vue`
- `AssistantActivityPanel.vue`
- `AssistantBriefingPanel.vue`
- `AssistantVoicePanel.vue`
- `AssistantApprovalsPanel.vue`

## Gemeinsame Abhaengigkeiten

Der Assistant soll diese bestehenden Plattform-Bausteine nutzen:

- `auth`
- `tenant`
- `ModuleInterface`
- `AI Setup / ai router`
- `integrations`
- `services/llm.py`
- `briefing/tts.py` oder spaeter gemeinsamer TTS-Service

## Datenmodell

## A. Allgemeiner Integrations-Layer

Vorbedingung:

- das allgemeine Integrationsmodell muss zuerst geschaffen oder finalisiert werden

Wichtige Korrektur:

- `briefing_account_connections` ist bereits ein funktionierender Vorlaeufer
- `integration_connections` wird deshalb nicht aus dem Nichts neu erfunden
- stattdessen wird ein konkreter Migrationspfad benoetigt

Zieltabellen:

### `integration_connections`

Felder:

- `id`
- `tenant_id`
- `user_id` nullable
- `provider`
- `integration_type`
- `auth_mode`
- `external_account_id`
- `mailbox_address`
- `connected_email`
- `account_label`
- `encrypted_token`
- `status`
- `last_error`
- `metadata`
- `created_at`
- `updated_at`

### `integration_connection_capabilities`

Felder:

- `id`
- `connection_id`
- `capability`
- `granted`

Capabilities:

- `read_mail`
- `read_calendar`
- `send_mail`
- `mail_actions`

## Migrationspfad von `briefing_account_connections`

Ausgangslage:

- `BriefingAccountConnection` besitzt bereits weite Teile der benoetigten Struktur

Empfehlung:

1. neue allgemeine Tabelle `integration_connections` anlegen
2. bestehende Daten aus `briefing_account_connections` migrieren
3. `integration_connection_capabilities` aus bisherigen Verbindungstypen ableiten
4. `briefing` schrittweise auf `integration_connections` umstellen
5. `briefing_account_connections` erst nach produktiver Umstellung entfernen

Nicht empfohlen:

- harter Neuaufbau ohne Datenmigration
- parallele Dauerhaltung identischer Fachdaten in zwei Tabellen

## B. Assistant-spezifische Tabellen

### `assistant_profiles`

Zweck:

- User-spezifische Modulkonfiguration

Felder:

- `id`
- `tenant_id`
- `user_id`
- `active`
- `briefing_enabled`
- `voice_enabled`
- `autopilot_enabled`
- `timezone`
- `delivery_time`
- `llm_provider`
- `llm_model`
- `tts_provider`
- `tts_voice`
- `stt_provider`
- `max_items_per_run`
- `default_reply_mode`
- `created_at`
- `updated_at`

### `assistant_sources`

Zweck:

- fachliche Aktivierung einzelner Konten fuer den Assistant

Felder:

- `id`
- `tenant_id`
- `user_id`
- `connection_id`
- `briefing_enabled`
- `voice_enabled`
- `reply_enabled`
- `autopilot_enabled`
- `priority`
- `settings_json`
- `created_at`
- `updated_at`

### `assistant_items`

Zweck:

- normalisierte Assistant-Objekte

Felder:

- `id`
- `tenant_id`
- `user_id`
- `connection_id`
- `item_type`
- `external_id`
- `thread_id`
- `mailbox_address`
- `title`
- `summary`
- `content_snippet`
- `sender`
- `recipients_json`
- `occurred_at`
- `raw_metadata_json`
- `raw_payload_hash`
- `status`
- `created_at`
- `updated_at`

`item_type`:

- `email`
- `calendar`

### `assistant_events`

Zweck:

- normalisierte Rohereignisse vor der Item-Erzeugung
- Idempotenz und Dedup bei Polling oder spaeteren Webhooks

Felder:

- `id`
- `tenant_id`
- `user_id`
- `connection_id`
- `event_type`
- `external_id`
- `thread_id`
- `raw_payload_hash`
- `payload_json`
- `occurred_at`
- `processed_at`
- `created_at`

Entscheidung:

- `assistant_events` bleibt Teil des Delivery-Plans
- `assistant_items` ist nicht die einzige Dedup-Schicht
- Events werden zuerst dedupliziert, danach in `assistant_items` ueberfuehrt oder aktualisiert

### `assistant_decisions`

Zweck:

- Klassifikation und Bewertung

Felder:

- `id`
- `tenant_id`
- `user_id`
- `item_id`
- `decision_type`
- `decision_value`
- `confidence`
- `reason`
- `source`
- `metadata_json`
- `created_at`

### `assistant_rules`

Zweck:

- explizite und gelernte Regeln

Felder:

- `id`
- `tenant_id`
- `user_id`
- `name`
- `enabled`
- `scope`
- `priority`
- `match_criteria_json`
- `action_type`
- `action_payload_json`
- `risk_level`
- `origin`
- `confidence`
- `created_at`
- `updated_at`

### `assistant_actions`

Zweck:

- vorgeschlagene oder ausgefuehrte Aktionen

Felder:

- `id`
- `tenant_id`
- `user_id`
- `item_id`
- `action_type`
- `status`
- `risk_level`
- `requires_confirmation`
- `executed_at`
- `error_message`
- `metadata_json`
- `created_at`

### `assistant_feedback`

Zweck:

- User-Rueckmeldungen fuer Lernlogik

Felder:

- `id`
- `tenant_id`
- `user_id`
- `item_id`
- `feedback_type`
- `feedback_payload_json`
- `created_at`

### `assistant_conversations`

Zweck:

- Zustand fuer Voice-/Dialog-Interaktionen

Felder:

- `id`
- `tenant_id`
- `user_id`
- `channel`
- `state`
- `context_json`
- `created_at`
- `updated_at`

## Migrationsreihenfolge

1. `integration_connections`
2. `integration_connection_capabilities`
3. `assistant_profiles`
4. `assistant_sources`
5. `assistant_events`
6. `assistant_items`
7. `assistant_decisions`
8. `assistant_rules`
9. `assistant_actions`
10. `assistant_feedback`
11. `assistant_conversations`

## Scheduler- und Worker-Architektur

Der Assistant bekommt einen eigenen Worker-Prozess analog zu den bestehenden Worker-Patterns.

Geplante Datei:

- `backend/run_assistant_worker.py`

Aufgaben:

- Polling fuer aktive Assistant-Quellen
- Event-Erzeugung
- Event-Verarbeitung
- geplante Briefing-Laeufe
- spaeter Rule Suggestions und Lernjobs

Phase-1-Strategie:

- konfigurierbares Polling
- keine Webhook-Pflicht im ersten produktiven Schritt

Phase-2-Strategie:

- Microsoft Graph Change Notifications / Subscriptions pruefen und optional ergaenzen

Wichtige technische Regel:

- Worker muss OAuth-Refresh automatisch behandeln
- bei Refresh-Fehlern Verbindung auf Fehlerstatus setzen
- `last_error` sauber schreiben
- spaetere automatische Wiederaufnahme ermoeglichen

## Backend-Schnittstellen

## 1. Modulsteuerung

Ueber `ModuleInterface`:

- `GET /api/v1/ai/modules/assistant/setup-schema`
- `GET /api/v1/ai/modules/assistant/config`
- `PUT /api/v1/ai/modules/assistant/config`
- `POST /api/v1/ai/modules/assistant/actions/{action}`

Erste Modulparameter:

- `llm_provider`
- `llm_model`
- `tts_provider`
- `tts_voice`
- `stt_provider`
- `autopilot_enabled`

## 2. Assistant API

Vorgesehene Endpunkte:

### Profil

- `GET /api/v1/assistant/profile`
- `PUT /api/v1/assistant/profile`

### Konten / Quellen

- `GET /api/v1/assistant/sources`
- `POST /api/v1/assistant/sources`
- `PUT /api/v1/assistant/sources/{id}`
- `DELETE /api/v1/assistant/sources/{id}`

### Briefing

- `POST /api/v1/assistant/briefing/run`
- `GET /api/v1/assistant/briefing/history`
- `GET /api/v1/assistant/briefing/{id}`

### Items / Aktivitaet

- `GET /api/v1/assistant/items`
- `GET /api/v1/assistant/items/{id}`
- `POST /api/v1/assistant/items/{id}/read-aloud`

### Regeln

- `GET /api/v1/assistant/rules`
- `POST /api/v1/assistant/rules`
- `PUT /api/v1/assistant/rules/{id}`
- `DELETE /api/v1/assistant/rules/{id}`

### Feedback / Lernen

- `POST /api/v1/assistant/items/{id}/feedback`
- `GET /api/v1/assistant/rule-suggestions`
- `POST /api/v1/assistant/rule-suggestions/{id}/apply`

### Reply Assistant

- `POST /api/v1/assistant/replies/draft`
- `POST /api/v1/assistant/replies/{id}/speak-preview`
- `POST /api/v1/assistant/replies/{id}/approve`
- `POST /api/v1/assistant/replies/{id}/save-draft`

### Voice

- `POST /api/v1/assistant/voice/command`
- `POST /api/v1/assistant/voice/transcribe`
- `POST /api/v1/assistant/voice/respond`

### Mobile / Audio Entry

- `POST /api/v1/assistant/mobile/briefing/latest`
- `POST /api/v1/assistant/mobile/reply/start`

### Freigaben / Aktionen

- `GET /api/v1/assistant/actions/pending`
- `POST /api/v1/assistant/actions/{id}/approve`
- `POST /api/v1/assistant/actions/{id}/reject`

## Service-Zuschnitt

## `AssistantService`

Orchestriert:

- Profil
- Quellen
- Briefing-Ausloesung
- Zugriff auf Teilservices

## `AssistantIntakeService`

Zustaendig fuer:

- Mail-/Kalenderdaten laden
- `assistant_events` schreiben
- Event-Dedup
- Normalisierung
- Upsert in `assistant_items`

## `AssistantRuleEngine`

Zustaendig fuer:

- Regelabgleich
- Prioritaeten
- Ableitung von Aktionen

## `AssistantDecisionService`

Zustaendig fuer:

- LLM-Klassifikation
- Relevanz
- Reply-Bedarf
- Briefing-Selektion

## `AssistantActionService`

Zustaendig fuer:

- Move / Archive / Label / Draft
- spaeter Delete/Spam nur mit Schutzlogik

## `AssistantVoiceService`

Zustaendig fuer:

- STT
- Intent Parsing
- TTS
- Dialogzustand

Default-Strategie:

- local-first auf GB10
- STT standardmaessig via `faster-whisper`
- TTS standardmaessig via Piper oder XTTS
- externer STT/TTS-Provider nur als Fallback

## `AssistantLearningService`

Zustaendig fuer:

- Feedback auswerten
- Rule Suggestions erzeugen
- spaeter implizite Praeferenzvorschlaege

## Frontend-Zuschnitt

## View `AssistantView`

Tab-Struktur:

- `Mein Assistant`
- `Konten`
- `Regeln`
- `Aktivitaet`
- `Freigaben`
- `Einstellungen`

## `Mein Assistant`

Zeigt:

- kurzer Status
- letztes Briefing
- Button `Jetzt Updates vorlesen`
- Antwort-Shortcut

## `Konten`

Zeigt:

- verbundene Mail-/Kalenderkonten
- Aktivierung fuer:
  - Briefing
  - Voice
  - Reply
  - Autopilot
- Prioritaet
- Status

## `Regeln`

Zeigt:

- alle Assistant-Regeln
- Vorschlagsregeln
- Risikostufe
- letzte Nutzung

## `Aktivitaet`

Zeigt:

- relevante Items
- Klassifikation
- Entscheidungen
- Erklaerung

## `Freigaben`

Zeigt:

- Draft Replies
- Pending Actions
- Quarantaene

## `Einstellungen`

Zeigt:

- LLM
- TTS
- STT
- Delivery-Zeit
- Audio-Optionen

## Voice-Flows

## Flow A: `Gib mir die letzten Updates`

1. Mobile App sendet Voice-Command
2. STT transkribiert
3. Intent `briefing_latest`
4. Assistant sammelt aktuelle relevante Items
5. LLM erstellt Kurzlage
6. TTS liest vor
7. Verlauf wird gespeichert

## Flow B: `Antworte auf die Mail von X`

1. Intent `reply_to_item`
2. relevantes Item oder Thread wird gesucht
3. Kontext wird zusammengefasst
4. User diktiert Antwort
5. STT erzeugt Text
6. LLM erstellt polierten Entwurf
7. TTS liest vor
8. User bestaetigt
9. Draft speichern oder senden

## Flow C: `Solche Mails kuenftig archivieren`

1. Intent `create_rule_from_item`
2. aktuelles Item als Referenz
3. User-Kommandotext als Action-Wunsch
4. Regelvorschlag erzeugen
5. User bestaetigt
6. `assistant_rule` wird gespeichert

## Voice-Integrationsentscheidung

Der eigentliche Sprachdialog findet in der eigenen Assistant-App bzw. PWA statt.

Native Assistenten wie:

- Siri
- Apple Shortcuts / App Intents
- Android App Actions

koennen spaeter genutzt werden fuer:

- App oeffnen
- Voice-Modus starten
- Schnellaktionen ausloesen

Sie sind aber nicht die Kern-Gespraechsengine.

## Sicherheitsregeln

Erster produktiver Release:

- kein automatisches finales Loeschen
- kein automatischer Versand ohne Freigabe
- keine Spam-Markierung ohne Review
- Archive/Move nur fuer niedrige oder mittlere Risiken

## Token-Refresh und Fehlerbehandlung

Der Assistant muss das bestehende OAuth-Refresh-Muster aus dem aktuellen Briefing-/Microsoft-Pfad wiederverwenden und verallgemeinern.

Pflichtverhalten:

1. vor API-Zugriff Token-Gültigkeit pruefen
2. bei Bedarf Refresh ausfuehren
3. neuen Token persistieren
4. bei Fehler:
   - Status auf Fehler setzen
   - `last_error` schreiben
   - Event/Run nicht still verwerfen

Das ist Teil des produktiven Grundpfads.

## Open-Source-Einbindung

## Zulässige Nutzung

Open Source kann fuer drei Dinge genutzt werden:

1. Referenz / Abschauen
2. Teilkomponenten
3. optionale Sidecar-Services

## Bevorzugte Referenzprojekte

- Inbox Zero
- Mail0 / Zero
- Khoj
- Voice-Agent-Referenzen fuer STT/TTS/Realtime

## Nicht empfohlen

- komplettes Fremdprojekt als Kernmodul zu uebernehmen

Grund:

- Modulfit
- Tenantfit
- Lizenzfit
- Securityfit
- langfristige Wartbarkeit

## Konkrete Delivery-Reihenfolge

## Sprint 1

- Integrationsmodell finalisieren
- Assistant-Modulgeruest anlegen
- Alembic-Migrationen fuer:
  - `integration_connections`
  - `integration_connection_capabilities`
- Basis-Manifest + Config Schema

Abnahme:

- Modul technisch vorhanden und aktivierbar

## Sprint 2

- Alembic-Migrationen fuer:
  - `assistant_profiles`
  - `assistant_sources`
- Kontoverwaltung im Frontend
- Basis-API fuer Profil und Quellen

Abnahme:

- mehrere Konten pro User konfigurierbar

## Sprint 3

- Intake-Service
- Alembic-Migrationen fuer:
  - `assistant_events`
  - `assistant_items`
  - `assistant_decisions`
- erste Relevanzklassifikation
- `briefing/run`

Abnahme:

- Text-Briefing ueber mehrere Konten

## Sprint 4

- Audio-Briefing
- TTS-Integration
- Briefing-Historie
- mobile-first PWA Audio-Flow

Abnahme:

- Audio-Briefing on demand lauffaehig

## Sprint 5

- Rule Engine
- Alembic-Migrationen fuer:
  - `assistant_rules`
  - `assistant_actions`
- Quarantaene / Pending Actions

Abnahme:

- erste reproduzierbare Inbox-Regeln

## Sprint 6

- STT-Pipeline mit `faster-whisper` als Default
- Reply Drafting
- Freigabe-Flow

Abnahme:

- Sprachbasierter Draft-Reply nutzbar

## Sprint 7

- Learning Layer
- Alembic-Migrationen fuer:
  - `assistant_feedback`
  - `assistant_conversations`
- Rule Suggestions

Abnahme:

- aus User-Feedback ableitbare Regeln

## Sprint 8

- mobile-first PWA Ausbaustufe
- Voice UX
- Notifications

Abnahme:

- alltagstauglicher mobiler Einsatz moeglich

## Definition of Done fuer Release 1

Release 1 gilt als marktfähig, wenn:

- mehrere Konten pro User funktionieren
- Briefing als Text und Audio funktioniert
- Regeln fuer Priorisierung / Move / Archive funktionieren
- Voice Reply als Draft-by-default funktioniert
- User-Regeln gespeichert und wiederverwendet werden
- Aktionen nachvollziehbar im Audit auftauchen
- keine riskanten stillen Aktionen passieren

## Naechster technischer Startpunkt

Sofort umsetzbar:

1. allgemeines `integration_connections`-Modell implementieren
2. `backend/app/assistant/` als Modul anlegen
3. `assistant_profiles` und `assistant_sources` einziehen
4. Web-Frontend fuer Konto-/Profilverwaltung bereitstellen

Damit beginnt der Bau an der richtigen Basis und nicht mit provisorischer Sonderlogik im bestehenden `briefing`.
