# Assistant Module Full Roadmap

Stand: 2026-03-14

Status:

- Kontext- und Produktdokument
- operative technische Entscheidungen stehen im Implementation Plan

## Ziel

Dieses Dokument beschreibt nicht nur einen MVP, sondern das Zielbild fuer ein voll einsatzfaehiges, lizenzierbares Plattform-Modul `assistant`.

Der Assistant soll:

- mehrere E-Mail- und Kalenderkonten ueberwachen
- Inhalte priorisieren, filtern und klassifizieren
- ein kurzes Briefing als Text und Audio liefern
- Voice-Interaktion mobil und im Auto ermoeglichen
- Antwortentwuerfe per Sprache erzeugen
- aus explizitem User-Feedback lernen
- spaeter kontrolliert Inbox-Aktionen automatisieren

Zusaetzliche Leitlinie:

- lokale Ausfuehrung auf GB10-Hardware ist der Standard
- externe Modelle oder APIs nur als Fallback

Das Modul soll als nachladbare Funktionalitaet in die Plattform passen und nicht Teil des Standardauslieferungsumfangs sein.

## Produktdefinition

### Was der Assistant ist

Ein eigenes Plattform-Modul mit:

- eigener Lizenz
- eigener Aktivierung
- eigener UI
- eigener API
- eigener Datenhaltung
- eigener AI- und Voice-Logik

### Was der Assistant nicht ist

- keine lose Sonderfunktion im `briefing`
- keine komplett separate Nebenplattform
- kein reines Voice-Gimmick
- kein reiner E-Mail-Client

## Betriebsmodell fuer AI und Voice

Der Assistant wird local-first ausgelegt.

Primär:

- lokales LLM
- lokales STT
- lokales TTS

Sekundaer:

- externer LLM-/STT-/TTS-Provider als Fallback

Bevorzugte lokale Basis:

- Ollama
- Whisper / faster-whisper
- Piper / XTTS

Ziel:

- geringe laufende Kosten
- Datenschutz
- stabile Plattformkontrolle
- Ausnutzung der vorhandenen GB10-Hardware

## Nutzerbild

### Primärer User

Ein Geschaeftsinhaber oder Power User, der:

- mehrere Postfaecher hat
- unterwegs schnelle Lagebilder braucht
- wichtige Mails nicht verpassen will
- Unwichtiges automatisiert ausfiltern moechte
- Antworten mobil diktieren will

### Typische Situationen

- im Auto: `Gib mir die letzten Updates`
- unterwegs: `Was ist heute wichtig?`
- nach dem Vorlesen: `Antworte auf die Mail von X`
- bei wiederkehrenden Mails: `So etwas kuenftig archivieren`
- bei klaren Mustern: `Alles von diesem Absender nicht mehr vorlesen`

## Vollstaendiges Zielbild

## 1. Multi-Account Aggregation

Der Assistant kann pro User mehrere Verbindungen verwalten:

- mehrere persoenliche Mailkonten
- mehrere Kalenderkonten
- spaeter Shared Mailboxes

Der User kann fuer jedes Konto festlegen:

- aktiv fuer Briefing
- aktiv fuer Vorlesen
- aktiv fuer Klassifikation
- aktiv fuer Reply-Flows
- aktiv fuer Autopilot

## 2. Laufender Service

Der Assistant arbeitet nicht nur auf Knopfdruck, sondern permanent im Hintergrund:

- Polling oder Webhooks
- neue Mails erkennen
- Kalenderaenderungen erkennen
- Thread-Updates erfassen
- Regeln anwenden
- neue Briefing-relevante Inhalte vormerken

## 3. Priorisierung und Triage

Jede neue Mail wird bewertet:

- wichtig
- informativ
- spaeter lesen
- ignorierbar
- newsletter
- systemmail
- spam-verdaechtig
- antwort noetig
- delegierbar

## 4. Briefing

Der Assistant erzeugt:

- Kurzlage in Text
- Audio-Briefing
- optional thematisch gruppierte Zusammenfassung

Beispiele:

- `Was ist heute wichtig?`
- `Was kam seit gestern Abend rein?`
- `Welche Termine und E-Mails brauchen heute Aufmerksamkeit?`

## 5. Voice Reply

Der User kann:

- eine Mail aus dem Briefing auswaehlen
- Kontext vorlesen lassen
- Antwort diktieren
- den Entwurf gegenhoeren
- aendern
- als Draft speichern oder freigeben

Wichtige Produktentscheidung:

- der sprachliche Dialog findet in der eigenen Assistant-App statt
- Siri oder andere native Assistenten dienen spaeter nur als Einstiegspunkt oder Shortcut-Ebene
- die eigentliche Sprachverarbeitung und Gespraechslogik bleibt im Assistant selbst

## 6. Lernender Assistant

Der User kann direkt aus dem Dialog Regeln ableiten lassen:

- `Solche E-Mails immer verschieben`
- `Mails von diesem Absender nie vorlesen`
- `Aehnliche E-Mails kuenftig loeschen`
- `Alles zu Rechnungen immer priorisieren`

Wichtig:

- das Lernen wird strukturiert gespeichert
- nicht nur als freies LLM-Gedaechtnis

## 7. Kontrollierte Automatisierung

Langfristig kann der Assistant selbststaendig handeln:

- labeln
- verschieben
- archivieren
- in Quarantaene legen
- Antwortentwurf vorbereiten

Delete, Spam-Markierung und Senden bleiben besonders geschuetzt.

## Plattform-Fit

Der Assistant passt als neues nachladbares Modul in eure Plattformlogik:

- als separater `app/assistant/`-Bereich
- mit Modulmanifest
- mit Modulkonfiguration
- mit eigenen Capabilities
- mit AI-Modulsteuerung
- mit optionaler Lizenzpruefung

Der Plattformkern liefert:

- Auth
- Tenant-/User-Kontext
- Permissions
- Integrations-Layer
- LLM/TTS/STT-Services
- Scheduling
- Audit / Confirmations

## Architektur

## 1. Technische Schichten

### Schicht A: Integrations-Layer

Provider-neutraler Zugriff auf:

- Microsoft 365
- Google Workspace
- spaeter IMAP/SMTP

Capabilities:

- `read_mail`
- `read_calendar`
- `send_mail`
- `mail_actions`

### Schicht B: Assistant Intake

Neue Daten aus Verbindungen werden vereinheitlicht:

- Mails
- Threads
- Termine
- Kalenderupdates

Ziel:

- internes Normalformat

### Schicht C: Rule Engine

Deterministische Regeln zuerst.

Beispiele:

- Absender ist blockiert
- bekannte Newsletter-Domain
- Betreff passt auf Muster
- Ordnerregel vorhanden

### Schicht D: AI/Decision Layer

LLM oder andere Klassifikationslogik fuer Grauzonen:

- relevant oder nicht
- antwort noetig
- kurz zusammenfassen
- fuer Voice-Briefing geeignet

### Schicht E: Action Policy Layer

Entscheidet, ob etwas:

- nur markiert
- vorgeschlagen
- direkt ausgefuehrt
- in Quarantaene gelegt
- bestaetigt werden muss

### Schicht F: Voice Layer

- STT
- Intent Parsing
- Dialoglogik
- TTS

### Schicht G: Audit + Learning

- Entscheidungen speichern
- Feedback speichern
- Regeln daraus ableiten
- Nachvollziehbarkeit sichern

## 2. Datenmodell

Das Modul sollte auf dem allgemeinen Integrationsmodell aufbauen und folgende Assistant-spezifische Tabellen erhalten.

### `assistant_profiles`

User-spezifische Konfiguration:

- `tenant_id`
- `user_id`
- `active`
- `timezone`
- `briefing_enabled`
- `voice_enabled`
- `autopilot_enabled`
- `llm_provider`
- `llm_model`
- `tts_provider`
- `stt_provider`
- `delivery_time`
- `max_items_per_run`
- `default_reply_mode`

### `assistant_sources`

Fachliche Zuordnung der verbundenen Konten:

- `tenant_id`
- `user_id`
- `connection_id`
- `briefing_enabled`
- `voice_enabled`
- `reply_enabled`
- `autopilot_enabled`
- `priority`
- `settings_json`

### `assistant_items`

Normalisierte Objekte:

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
- `occurred_at`
- `metadata`
- `raw_payload_hash`

### `assistant_rules`

Explizite und gelernte Regeln:

- `tenant_id`
- `user_id`
- `name`
- `enabled`
- `scope`
- `priority`
- `match_criteria`
- `action_type`
- `action_payload`
- `risk_level`
- `origin`
- `confidence`

### `assistant_decisions`

- `tenant_id`
- `user_id`
- `item_id`
- `decision_type`
- `decision_value`
- `confidence`
- `reason`
- `source`

### `assistant_actions`

- `tenant_id`
- `user_id`
- `item_id`
- `action_type`
- `status`
- `risk_level`
- `requires_confirmation`
- `executed_at`
- `metadata`

### `assistant_feedback`

- `tenant_id`
- `user_id`
- `item_id`
- `feedback_type`
- `feedback_payload`
- `created_at`

### `assistant_conversations`

Fuer Voice-/Chat-Dialoge:

- `tenant_id`
- `user_id`
- `channel`
  - `mobile_voice`
  - `web_chat`
  - `api`
- `state`
- `context`

## 3. Service-Struktur

Neues Paket:

- `backend/app/assistant/`

Vorgeschlagene Dateien:

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

Wichtige Services:

- `AssistantService`
- `AssistantIntakeService`
- `AssistantRuleEngine`
- `AssistantDecisionService`
- `AssistantActionService`
- `AssistantVoiceService`
- `AssistantLearningService`

## 4. Frontend-Struktur

### Web-Frontend

Eigene Modulansicht:

- `AssistantView`

Teilbereiche:

- Konto-Setup
- Regelverwaltung
- Aktivitaetsfeed
- Briefing-Historie
- Freigaben / Quarantaene
- Voice-/LLM-/STT-/TTS-Einstellungen

### Mobile-App

Eigener Client fuer denselben Backend-Stack.

Ziele:

- schnelles Audio-Briefing
- Sprachdialog
- Freigabe von Antwortentwuerfen
- kurze Inbox-Aktionen

## Voice-Architektur

## 1. STT

Vorgeschlagene Optionen:

- lokales Whisper / faster-whisper
- Whisper.cpp
- OpenAI STT optional

Prioritaet:

1. lokal auf GB10
2. interner Plattformdienst
3. externer Provider als Fallback

## 2. TTS

Passend zu eurem Stack:

- Piper
- XTTS

Prioritaet:

1. lokal auf GB10
2. interner Plattformdienst
3. externer Provider als Fallback

## 3. Dialogzustand

Die App braucht keinen freien Endloschat, sondern gefuehrten Aufgaben-Dialog.

Beispiele:

- `Gib mir die letzten Updates`
- `Lies die Mail von X`
- `Antworte auf die letzte Mail`
- `Speichere das als Regel`
- `Solche Mails kuenftig nicht mehr vorlesen`

Die Interpretation sollte ueber:

1. Intent-Klassifikation
2. Tool-Auswahl
3. explizite Rueckfragen

erfolgen, nicht ueber vollkommen offenen Agentenbetrieb.

## 4. Einstieg ueber native Assistenten

Spaeter sinnvoll:

- iOS App Intents / Siri Shortcuts
- Android App Actions

Verwendung:

- App starten
- Voice-Modus oeffnen
- bestimmte schnelle Assistant-Aktionen starten

Nicht vorgesehen als Hauptarchitektur:

- Siri oder Google Assistant als eigentliche Gespraechsengine
- Delegation der zentralen Assistant-Dialoglogik an externe Plattformassistenten

## Sicherheitsmodell

## Risikostufen

### `low`

- zusammenfassen
- priorisieren
- labeln
- vorlesen

### `medium`

- verschieben
- archivieren
- als unwichtig markieren
- in Quarantaene legen

### `high`

- loeschen
- als Spam markieren
- senden

## Regeln

- `low` kann spaeter weitgehend automatisiert werden
- `medium` nur bei klaren Regeln / hoher Confidence
- `high` nur mit Confirmation oder Draft-by-default

## Lernmodell

Der Assistant lernt ueber:

1. explizite User-Kommandos
2. implizites Verhalten
3. spaeter statistische Muster

### Explizites Lernen

Beispiele:

- `Diese Mails kuenftig immer archivieren`
- `Diesen Absender nicht mehr vorlesen`
- `Rechnungen immer priorisieren`

### Implizites Lernen

Beispiele:

- User verwirft haeufig bestimmte Kategorie
- User beantwortet Mails bestimmter Typen immer spaet
- User ueberspringt bestimmte Newsletter immer

Wichtig:

- implizite Muster zuerst nur als Vorschlaege
- keine stillen Regeln ohne Transparenz

## Open-Source-Bausteine und Referenzen

Es ist sinnvoll, bestehende Open-Source-Projekte nicht blind zu uebernehmen, sondern gezielt als Referenz oder Teilbaustein zu nutzen.

### 1. Inbox Zero

Quelle:

- https://github.com/elie222/inbox-zero

Warum relevant:

- AI Email Assistant
- Regeln fuer Inbox-Verhalten
- Reply-Drafts
- starke fachliche Naehe zu Inbox-Triage

Moegliche Nutzung:

- Produktinspiration
- Regel-/Kategorisierungskonzepte
- UI-/UX-Muster fuer Inbox-Automation

### 2. Mail0 / Zero

Quelle:

- https://github.com/Mail-0/Zero

Warum relevant:

- Open-Source Email App
- Unified Inbox
- AI-/Agent-Gedanke

Moegliche Nutzung:

- Multi-Provider-Inbox-Muster
- Self-hosted Email-App-Konzepte

### 3. Khoj

Quelle:

- https://github.com/khoj-ai/khoj

Warum relevant:

- self-hosted Agent-Plattform
- Automationen
- Benachrichtigungen
- Voice und Agenten

Moegliche Nutzung:

- Agent- und Scheduling-Muster
- Wissens-/Memory-Konzepte

### 4. FastRTC Voice Agent

Quelle:

- https://github.com/enricollen/fastRTC-voice-agent

Warum relevant:

- modellagnostischer Voice-Agent
- STT/LLM/TTS-Pipeline

Moegliche Nutzung:

- Referenz fuer Voice-Pipeline
- Streaming-/Realtime-Muster

### 5. AgentVox

Quelle:

- https://github.com/MIMICLab/AgentVox

Warum relevant:

- lokale STT/TTS/LLM-Architektur
- privacy-orientierte Voice-Assistenz

Moegliche Nutzung:

- rein lokale Audio-Pipeline als Referenz

## Entscheidung zu Open Source

Empfehlung:

- keine Komplettuebernahme eines Fremdprojekts als Modulbasis
- gezieltes Abschauen oder Einbetten einzelner Teilkonzepte
- Kernlogik selbst in eurer Plattform halten

Grund:

- ihr braucht Tenant-/Lizenz-/Modulfit
- ihr braucht gemeinsame Integrations- und Security-Standards
- ihr wollt nicht in eine fremde Architektur eingeschlossen werden

## Vollstaendige Umsetzungsphasen

## Phase 1: Plattformfundament

Ziel:

- technische Basis fuer mehrere Konten und spaetere Assistant-Aktionen

Umsetzung:

1. `integration_connections` finalisieren
2. Capabilities einziehen
3. Confirmations-Modell vorbereiten
4. Tenant-/User-bezogene Mailboxprofile einfuehren

Abnahmekriterien:

- mehrere Mail-/Kalenderkonten pro User sauber modellierbar
- lesende und schreibende Rechte technisch trennbar

## Phase 2: Modulgeruest Assistant

Ziel:

- nachladbares Modul formal und technisch anlegen

Umsetzung:

1. `backend/app/assistant/`
2. Modulmanifest
3. `config_schema.py`
4. `ModuleInterface`
5. Basis-Frontendview
6. Lizenz-/Aktivierungsintegration

Abnahmekriterien:

- Modul aktivierbar
- modulare Konfiguration ueber AI-Modulpfad moeglich

## Phase 3: Multi-Account Briefing produktionsreif

Ziel:

- mehrere Mail- und Kalenderkonten in ein einziges persoenliches Briefing ueberfuehren

Umsetzung:

1. mehrere aktive Assistant-Sources pro User
2. Aggregation und Deduplizierung
3. Relevanzbewertung
4. Text-Briefing
5. Audio-Briefing
6. geplante und manuelle Runs

Abnahmekriterien:

- Audio-Briefing mit mehreren Konten stabil
- sinnvolle Priorisierung und kurze Lage

## Phase 4: Inbox-Triage

Ziel:

- aktive Ordnung und Filterung

Umsetzung:

1. Klassifikationen
2. Regelengine
3. Quarantaene
4. Move/Archive-Workflows
5. Inbox-Historie mit Erklaerung

Abnahmekriterien:

- User kann Regeln anlegen
- unwichtige Inhalte werden reproduzierbar behandelt

## Phase 5: Voice Reply produktionsreif

Ziel:

- Antworten diktieren, pruefen, freigeben

Umsetzung:

1. STT-Pipeline
2. Thread-Kontext-Service
3. Reply-Generator
4. TTS-Ruecklesung
5. Draft-by-default
6. Freigabedialog

Abnahmekriterien:

- mobil nutzbarer Antwortworkflow
- kein ungewollter Versand

## Phase 6: Lernender Assistant

Ziel:

- aus Nutzerfeedback belastbare Regeln ableiten

Umsetzung:

1. Feedbackmodelle
2. Rule-Suggestion-Engine
3. UI fuer Vorschlaege und Freigaben
4. implizite Verhaltensmuster als Vorschlaege

Abnahmekriterien:

- wiederkehrende Muster werden erkannt
- User kann Vorschlaege uebernehmen oder verwerfen

## Phase 7: Autopilot

Ziel:

- kontrollierte Teilautomatisierung

Umsetzung:

1. Confidence-Schwellen
2. Aktionspolicies
3. medium-risk Automationen
4. spaeter high-risk mit strenger Confirmation

Abnahmekriterien:

- merkliche Inbox-Entlastung
- keine Blackbox-Aktionen
- vollstaendiger Audit-Trail

## Phase 8: Mobile Produktreife

Ziel:

- alltagstaugliche mobile Experience, testbar am Desktop

Umsetzung:

1. mobile-first PWA auf Basis der bestehenden Vue-App
2. Audio-first UX (funktioniert auch am Desktop-Browser)
3. schnelle Kommandos
4. Offline-/Schlechtverbindungsstrategie
5. Benachrichtigungen
6. spaeter optionale native Mobile-App als separates Projekt

Abnahmekriterien:

- am Desktop-Browser vollstaendig testbar
- im Auto und unterwegs nutzbar
- kurze Interaktionszyklen
- sicherer Freigabefluss

## Empfehlung fuer die naechsten realen Schritte

1. allgemeines Integrationsmodell abschliessen
2. neues Modul `assistant` formal anlegen
3. Phase 3 zuerst priorisieren:
   - Multi-Account
   - Briefing
   - Audio
4. parallel Rule Engine vorbereiten
5. STT/Reply erst danach produktionsreif ausbauen

Diese Reihenfolge ist sinnvoll, weil sie frueh einen echten Nutzwert liefert, ohne sofort in riskante Automations- oder Versandlogik zu gehen.
