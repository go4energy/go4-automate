# Assistant Module Architecture

Stand: 2026-03-14

Status:

- Kontext- und Zieldokument
- operative technische Entscheidungen stehen im Implementation Plan

## Ziel

Das Vorhaben soll nicht als Erweiterung des bestehenden `briefing`-Moduls umgesetzt werden, sondern als neues nachladbares, lizenzierbares Plattform-Modul.

Arbeitsname:

- `assistant`

Alternativen:

- `mailagent`
- `inboxassistant`

Empfehlung:

- `assistant`

Grund:

- der erste Fokus liegt auf E-Mail, Kalender und Voice
- spaeter kann das Modul aber auch Aufgaben, CRM, Kontakte, Notizen oder Freigaben integrieren
- der Name bleibt damit produktstrategisch offen

## Produktgedanke

Die Plattform bleibt der gemeinsame Kern.
Der `assistant` ist ein separates Modul, das:

- nicht standardmaessig ausgeliefert werden muss
- spaeter nachgeladen, nachlizenziert oder nachgekauft werden kann
- sich in die gemeinsame Plattformarchitektur integriert
- aber fachlich eine eigene, klar abgegrenzte Domäne bildet

Das Modul soll den persoenlichen digitalen Arbeitsassistenten fuer einen User bereitstellen.

Zielbild:

- mehrere E-Mail- und Kalenderkonten verbinden
- relevante Inhalte laufend beobachten
- wichtige Inhalte priorisieren
- unwichtige Inhalte ausblenden, labeln, verschieben oder spaeter automatisiert behandeln
- Audio-/Text-Briefings erzeugen
- Voice-Interaktion im Auto oder mobil ermoeglichen
- Antwortentwuerfe per STT + LLM + TTS unterstuetzen
- aus explizitem User-Feedback lernen

## Warum nicht im Briefing-Modul

Das bestehende `briefing`-Modul bleibt fachlich schlank und primär lesend:

- Inhalte sammeln
- priorisieren
- Zusammenfassungen erzeugen
- Audio erzeugen

Der geplante Assistant geht deutlich weiter:

- Inbox-Triage
- Regeln
- lernende Praeferenzen
- Reply-Assistance
- spaeter Mail-Aktionen
- Voice-Dialog

Das ist eine eigene Produktdomäne und sollte deshalb als separates Modul umgesetzt werden.

## Einordnung in die Plattform

Der `assistant` ist:

- ein eigenes nachladbares Modul
- mit eigenem Manifest
- eigener `config_schema.py`
- eigenem `ModuleInterface`
- eigenen Datenmodellen
- eigenen API-Endpunkten
- eigener Frontend-App / View
- optional eigener Mobile-App als Client

Der Assistant nutzt aber gemeinsame Plattform-Bausteine:

- Auth
- Tenant-Kontext
- Rollen und Berechtigungen
- Integrations-Layer
- LLM/TTS/STT
- AI-Modulsteuerung
- Audit / Confirmations
- Notification- und Scheduling-Infrastruktur

## Local-First Prinzip

Der Assistant soll auf der vorhandenen GB10-Hardware moeglichst viel lokal ausfuehren.

Primärpfad:

- lokales LLM
- lokales STT
- lokales TTS
- lokale Regel- und Entscheidungslogik

Externe Dienste:

- nur wenn lokal kein geeigneter Pfad verfuegbar ist
- oder als expliziter Fallback

Das gilt besonders fuer:

- LLM-Generierung
- STT
- TTS

Bevorzugte Zielarchitektur:

- Ollama fuer lokale LLMs
- lokale Whisper-/faster-whisper-Variante fuer STT
- Piper oder XTTS fuer TTS

Externe Provider wie OpenAI oder Anthropic bleiben erhalten, aber nur als Fallback oder optionaler Premium-Pfad.

## Zentrales Use Case Bild

### Mobile / Auto

User-Szenario:

1. Der User oeffnet die mobile Assistant-App.
2. Er sagt: `Gib mir die letzten Updates`.
3. Das Modul aggregiert relevante Inhalte aus allen aktivierten E-Mail- und Kalenderkonten.
4. Das LLM erzeugt eine kurze Lage.
5. TTS liest diese Lage als kurzes Audio-Briefing vor.

Danach:

1. Der User sagt: `Antworte auf die Mail von X`.
2. Das Modul findet den relevanten Thread.
3. Es liest kurz Kontext oder Zusammenfassung vor.
4. Der User diktiert die Antwort.
5. STT transkribiert den Text.
6. Das LLM erzeugt daraus eine saubere Antwort-Mail.
7. TTS liest den Entwurf zur Freigabe vor.
8. Der User bestaetigt, verwirft oder aendert.

Wichtig:

- anfangs nur Draft oder explizit freigegebener Versand
- kein stilles automatisches Senden in Phase 1

### Rolle von Siri / nativen Assistenten

Siri, Apple Shortcuts oder Android App Actions sollen nicht die eigentliche Gespraechsengine des Assistant sein.

Sie koennen spaeter sinnvoll genutzt werden fuer:

- App oeffnen
- Voice-Modus starten
- bestimmte Schnellaktionen antriggern

Beispiele:

- `Starte Assistant`
- `Hole meine letzten Updates`

Die eigentliche Unterhaltungslogik bleibt aber in der eigenen App und im eigenen Backend:

- Audio aufnehmen
- STT transkribieren
- Intent / Dialog im Assistant auswerten
- Antwort mit LLM erzeugen
- TTS wiedergeben

Grund:

- volle Kontrolle ueber Dialog, Regeln, Audit und Freigaben
- identisches Verhalten auf iOS und Android
- keine Abhaengigkeit von Limitierungen externer nativer Assistenten

### Laufender Service

Parallel dazu laeuft der Assistant als Hintergrundservice:

- Mails und Termine werden regelmaessig geholt
- Inhalte werden klassifiziert
- Regeln und Nutzerpraeferenzen werden angewendet
- definierte Aktionen werden vorbereitet oder ausgefuehrt
- das Audio-/Text-Briefing kann on demand oder geplant erzeugt werden

## Architekturprinzipien

## 1. Regelengine vor LLM

Gefaehrliche oder teure Entscheidungen sollen nicht primär dem LLM ueberlassen werden.

Reihenfolge:

1. harte Regeln
2. bekannte Signale
3. ML/LLM fuer Grauzonen
4. Action Policy Layer

Beispiele fuer harte Regeln:

- bestimmter Absender immer stumm
- bestimmtes Newsletter-Muster immer archivieren
- bestimmte Rechnungs- oder Systemmails nie loeschen
- Antworten nie ohne Freigabe senden

## 2. Lernverhalten strukturiert speichern

Der Assistant soll nicht nur freien Prompt-Kontext `merken`.

Stattdessen wird User-Feedback strukturiert gespeichert:

- explizite Regeln
- Praeferenzen
- Confidence-Werte
- Geltungsbereich
- Herkunft der Regel

Beispiel:

- `Mails wie diese kuenftig in Ordner X verschieben`

Speicherung:

- betroffener Account oder global
- Trigger-Merkmale
- Aktion
- Prioritaet
- Confidence
- Quelle: `user_confirmed`

## 3. Risk Layer

Aktionen bekommen Risikostufen:

- `low`
  - labeln
  - priorisieren
  - zusammenfassen
  - vorlesen
- `medium`
  - verschieben
  - archivieren
  - als unwichtig markieren
- `high`
  - senden
  - loeschen
  - Spam markieren

Regel:

- `high` niemals ungeprueft in Phase 1
- zuerst Quarantaene, Draft oder explizite Freigabe

## 4. Auditierbarkeit

Jede Entscheidung und jede Aktion muss nachvollziehbar sein:

- welche Mail wurde wie bewertet
- welche Regel oder welches Modell war ausschlaggebend
- welche Aktion wurde vorgeschlagen oder ausgefuehrt
- wie lautete die Rueckmeldung des Users

## Modulgrenzen

### Assistant

Zustaendig fuer:

- persoenliche Mail- und Kalenderaggregation
- Priorisierung
- Voice-Dialog
- Regeln und Lernmuster
- Reply-Assist
- persoenliche Briefings
- spaeter teilautomatische Inbox-Aktionen

### Briefing

Bleibt zustaendig fuer:

- klassische Briefing-Logik
- Channel-/Finding-basierte Zusammenfassungen
- Audio-Ausgabe fuer Briefings

Der Assistant kann spaeter `briefing`-Funktionen mitnutzen, aber nicht umgekehrt zur Hauptdomäne werden.

### Integrations-Layer

Zustaendig fuer:

- OAuth / Verbindungen
- Provider-Abstraktion
- Capabilities wie `read_mail`, `read_calendar`, `send_mail`, `mail_actions`

### Settings / AI Module Control

Zustaendig fuer:

- Modulkonfiguration
- Credential-Verwaltung
- Provider-/Model-Auswahl
- spaeter Confirmations fuer riskante Aktionen

## Datenmodell

Der Assistant sollte nicht auf den aktuellen `briefing_account_connections` aufbauen, sondern auf dem geplanten allgemeinen Integrationsmodell.

### 1. `integration_connections`

Allgemeine technische Verbindungen:

- `tenant_id`
- `user_id` optional
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

### 2. `integration_connection_capabilities`

Explizit vergebene Faehigkeiten je Verbindung:

- `read_mail`
- `read_calendar`
- `send_mail`
- `mail_actions`

### 3. `assistant_profiles`

Persoenliche Assistant-Konfiguration pro User:

- `tenant_id`
- `user_id`
- `active`
- `briefing_enabled`
- `voice_enabled`
- `delivery_time`
- `timezone`
- `stt_provider`
- `tts_provider`
- `llm_provider`
- `llm_model`
- `max_items_per_run`
- `default_reply_mode`

### 4. `assistant_rules`

Explizite Regeln und spaeter auch gelernte Regeln:

- `tenant_id`
- `user_id`
- `scope`
- `name`
- `enabled`
- `priority`
- `source_type`
- `match_criteria` JSON
- `action_type`
- `action_payload` JSON
- `risk_level`
- `origin`
  - `manual`
  - `learned`
  - `system`
- `confidence`

Beispiele fuer `match_criteria`:

- Absender
- Domain
- Betreffmuster
- Klassifikation
- Keywords
- aehnlicher Inhalt
- Thread-Typ
- Sprache

### 5. `assistant_events`

Normalisierte Rohereignisse fuer Idempotenz und Dedup:

- `tenant_id`
- `user_id`
- `connection_id`
- `event_type`
  - `mail_received`
  - `mail_updated`
  - `calendar_event`
- `external_id`
- `thread_id`
- `raw_payload_hash`
- `payload` JSON
- `occurred_at`
- `processed_at`

### 6. `assistant_items`

Normalisierte, verarbeitbare Objekte:

- `tenant_id`
- `user_id`
- `connection_id`
- `item_type`
  - `email`
  - `calendar`
- `external_id`
- `thread_id`
- `title`
- `summary`
- `content_snippet`
- `sender`
- `recipients`
- `occurred_at`
- `raw_metadata`
- `status`

### 7. `assistant_decisions`

Ergebnisse aus Regeln / Modellen:

- `tenant_id`
- `user_id`
- `item_id`
- `decision_type`
  - `importance`
  - `needs_reply`
  - `autopilot_action`
  - `read_aloud`
- `decision_value`
- `confidence`
- `reason`
- `source`
  - `rule`
  - `llm`
  - `hybrid`

### 8. `assistant_actions`

Tatsaechlich ausgefuehrte oder vorgeschlagene Aktionen:

- `tenant_id`
- `user_id`
- `item_id`
- `action_type`
- `status`
  - `suggested`
  - `queued`
  - `executed`
  - `rejected`
  - `failed`
- `risk_level`
- `requires_confirmation`
- `executed_at`
- `error_message`
- `metadata`

### 9. `assistant_feedback`

Lernbare User-Rueckmeldungen:

- `tenant_id`
- `user_id`
- `item_id`
- `feedback_type`
  - `keep`
  - `ignore`
  - `move`
  - `delete`
  - `always_like_this`
- `feedback_payload`
- `created_at`

## Capability-Modell

Innerhalb des Moduls sollte es Capabilities geben, die lizenz- oder rolloutfaehig getrennt aktiviert werden koennen.

### Capability `briefing`

- Text-Briefing
- Audio-Briefing
- On-demand oder geplant

### Capability `inbox`

- Priorisierung
- Labeling
- Filterung
- Lese-/Vorleselogik

### Capability `reply`

- Antwortentwuerfe
- STT -> Entwurf
- Freigabe -> Senden / Draft

### Capability `autopilot`

- automatische Move/Archive/Quarantaene-Aktionen
- spaeter streng kontrollierte Delete-/Spam-Aktionen

### Capability `voice`

- Mobile Voice UI
- Vorlesen
- Sprachbefehle
- Freigabedialoge

## API- und Service-Schnitt

### Backend-Modul

Neues Paket:

- `backend/app/assistant/`

Vorgeschlagene Struktur:

- `__manifest__.py`
- `config_schema.py`
- `models.py`
- `schemas.py`
- `router.py`
- `service.py`
- `rules.py`
- `classifier.py`
- `voice.py`
- `scheduler.py`

### Zentrale Dienste

Zusatzdienste:

- `AssistantService`
- `AssistantRuleEngine`
- `AssistantDecisionService`
- `AssistantVoiceService`
- `AssistantLearningService`

## Voice-Architekturentscheidung

Es gibt drei moegliche Betriebsarten:

### 1. Native App mit eigener Voice-Pipeline

Pfad:

- Audio in App
- STT
- Intent/LLM
- TTS

Das ist der bevorzugte Standardpfad.

### 2. Native Assistenten als Launcher

Pfad:

- Siri / App Shortcut / App Action
- Assistant-App wird geoeffnet oder konkrete Aktion gestartet

Das ist ein Zusatzpfad, nicht die Kernlogik.

### 3. Externe Realtime-Voice-APIs

Moeglich als spaetere Option fuer sehr fluessige Sprachdialoge.

Aber:

- nicht der Default
- nicht die Kernarchitektur
- nur optional oder als Fallback

### Frontend-Web

Neue View:

- `AssistantView`

Zustaendig fuer:

- Konto-Setup
- Regeln
- Verlauf
- Audit
- Freigaben
- Modell-/Voice-Konfiguration

### Mobile-App

Kein separater Backend-Stack, sondern eigener Client:

- Mobile Assistant App

Sie spricht mit denselben Plattform-APIs und nutzt dieselben User-/Tenant-Kontexte.

## Voice-Interaktion

### TTS

Kurzfristig ueber vorhandene Plattform-Bausteine:

- Piper
- XTTS

### STT

Neu einzufuehren:

- lokaler oder externer STT-Service
- spaeter eigener abstrakter STT-Provider-Layer

Vorgeschlagene Provider-Abstraktion:

- `faster-whisper`
- `whisper.cpp`
- OpenAI STT optional

### Sprachdialog

Flow:

1. System liest kurze Lage vor
2. User gibt Sprachkommando
3. STT transkribiert
4. Intent-/Command-Parser erkennt Aktion
5. LLM baut bei Bedarf Entwurf oder Antwort
6. TTS liest Rueckfrage oder Ergebnis
7. User bestaetigt oder verwirft

## Lernlogik

Der Assistant lernt nicht nur ueber Prompting, sondern ueber gespeicherte Feedback-Muster.

Beispiele:

- `Mails von diesem Absender nie vorlesen`
- `Aehnliche Mails kuenftig in Ordner X`
- `Newsletter dieser Art automatisch archivieren`
- `Rechnungen immer priorisieren`

Umsetzung:

1. Feedback wird als `assistant_feedback` gespeichert
2. eine Lernkomponente erzeugt daraus strukturierte Regeln
3. Regeln werden vom Rule Engine Layer kuenftig vor dem LLM angewendet

## Sicherheits- und Freigabemodell

### Phase 1

- kein automatisches Senden
- kein automatisches finales Loeschen
- keine stillen Spam-Markierungen ohne Review

### Phase 2

- Move/Archive mit Regeln moeglich
- Delete nur in Quarantaene oder mit Verzugsfenster

### Phase 3

- fein granularer Confirmation-Layer pro Aktion
- Confidence-Schwellen
- Voice-Freigaben mit sicherem Bestätigungsdialog

## Lizenz- und Produktmodell

Das Modul kann als lizenzierbares Add-on eingefuehrt werden.

Beispielhaft:

### Assistant Basic

- mehrere Konten verbinden
- Text-Briefing
- Audio-Briefing
- einfache Voice-Wiedergabe

### Assistant Pro

- Multi-Account
- Regelengine
- Priorisierung
- Entwurfsantworten

### Assistant Auto

- Autopilot
- Quarantaene
- Move/Archive-Automationen
- lernende Regeln

## Schrittweise Umsetzung

## Phase 0: Architektur-Fundament

Ziel:

- den Assistant nicht schnell als Sonderlogik im Briefing verstecken

Umsetzung:

1. allgemeines `integration_connections`-Modell finalisieren
2. Capability-Modell einfuehren
3. bestehende `briefing`-Personal-Connections perspektivisch migrierbar machen
4. Confirmations-Modell fuer riskante Aktionen vorbereiten

Ergebnis:

- gemeinsame Grundlage fuer Assistant, Briefing und spaetere Inbox-/Mail-Workflows

## Phase 1: MVP Assistant Briefing

Ziel:

- persoenliche Lage aus mehreren Mail- und Kalenderkonten

Umsetzung:

1. neues Modul `assistant` anlegen
2. mehrere Mail-/Kalenderkonten pro User erlauben
3. Mail- und Kalenderdaten normalisieren
4. relevante Inhalte priorisieren
5. Text-Briefing erzeugen
6. Audio-Briefing mit TTS erzeugen
7. mobile API fuer `Gib mir die letzten Updates`

Ergebnis:

- Assistant liest relevante Inhalte vor
- User bekommt unterwegs eine kurze Lage

## Phase 2: Regelengine und Lernbasis

Ziel:

- User kann sagen, was kuenftig ignoriert, verschoben oder priorisiert werden soll

Umsetzung:

1. `assistant_rules` und `assistant_feedback` einfuehren
2. Rule Engine implementieren
3. UI fuer Regeln und Feedback schaffen
4. erste Lernlogik:
   - aus explizitem Feedback abgeleitete Regeln
5. Audit und Verlauf bereitstellen

Ergebnis:

- das System beginnt reproduzierbar aus User-Wuenschen zu lernen

## Phase 3: Voice Reply Assistant

Ziel:

- Antworten per Sprache diktieren und als Mail-Entwurf oder Versand vorbereiten

Umsetzung:

1. STT-Layer einfuehren
2. Thread-Kontext abrufen
3. LLM-Antwortgenerator bauen
4. TTS-Freigabedialog implementieren
5. Draft-by-default
6. Versand nur nach expliziter Freigabe

Ergebnis:

- produktiver mobiler Antwortworkflow

## Phase 4: Autopilot fuer Low-/Medium-Risk-Aktionen

Ziel:

- Teile der Inbox-Bearbeitung automatisieren

Umsetzung:

1. automatische Label-/Move-/Archive-Aktionen
2. Quarantaene fuer zweifelhafte Inhalte
3. Confidence-Schwellen
4. regelbasierte Priorisierung vor LLM

Ergebnis:

- Inbox wird ohne hohe Risiken deutlich entlastet

## Phase 5: Erweiterter Assistant

Moegliche Ausbaustufen:

- Kontakte / CRM-Kontext einbeziehen
- Aufgaben aus Mails erzeugen
- Meeting-Prep-Briefings
- Tagesagenda plus Follow-up-Vorschlaege
- Team-/Shared-Mailbox-Modi
- spaeter kontrollierte High-Risk-Aktionen

## Empfehlung fuer die naechste konkrete Umsetzung

Pragmatischer naechster Schritt:

1. `integration_connections` + Capabilities sauber finalisieren
2. neues Modul `assistant` als leeres nachladbares Modul anlegen
3. MVP auf `multi-account read + text/audio briefing` beschraenken
4. noch keine Delete-/Send-Automation im ersten Release

Damit bleibt der erste Schritt fachlich fokussiert, sicher und marktreif erweiterbar.
