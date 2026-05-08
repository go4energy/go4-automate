# Assistant Unified Implementation Plan

Stand: 2026-03-15

## Ziel

Dieses Dokument beschreibt den detaillierten Umsetzungsplan fuer den Ausbau des bestehenden `assistant`-Moduls zu einem vollstaendigen, sicheren, lokalen AI-Assistenten.

Zielbild:

- E-Mails per Sprache und Text lesen, zusammenfassen, beantworten, loeschen, verschieben, archivieren
- E-Mails mailboxuebergreifend zaehlen, filtern, priorisieren und bereinigen
- Kalender per Sprache und Text lesen und spaeter steuern
- Regeln aus Spracheingaben ableiten
- wiederkehrende Muster aus manuellen Aktionen lernen
- mehrere Konten und Provider unterstuetzen
- lokale Ausfuehrung auf GB10 mit Qwen, faster-whisper und Piper/XTTS als Standard
- alle riskanten Aktionen kontrolliert, bestaetigt und auditierbar ausfuehren

Wichtige Leitlinie:

- Das LLM plant und formuliert
- das Backend besitzt den Zustand
- der Policy-Layer entscheidet ueber Risiko und Ausfuehrung
- Provider-Adapter fuehren konkret aus

## Ausgangslage

Bereits vorhanden:

- `backend/app/assistant/` mit Profilen, Quellen, Items, Regeln, Aktionen, Feedback, Conversations
- Intake, Klassifikation, Rule Engine, Learning, Scheduler
- `integration_connections` plus Migrationspfad von `briefing_account_connections`
- Voice-Chat mit STT, TTS und lokalem Tool Calling
- Microsoft-Graph-basierte Mail-Live-Aktionen
- Frontend-View, Assistant-Store, Voice-Panel, Speaker-Handling

Bereits gut:

- modularer Assistant-Bereich
- lokaler STT-/TTS-/LLM-Pfad
- Shared OAuth-Layer in `app/integrations/oauth.py`
- erste serverseitige Confirmation-Gates im Voice-Flow

Noch nicht auf Zielniveau:

- keine vollstaendig einheitliche Action-Architektur zwischen Voice und klassischem Assistant
- keine vollstaendige Provider-Neutralitaet
- kein vollstaendiger Safety-/Policy-Layer fuer alle riskanten Aktionen
- keine produktionsreife Testbasis
- Kalender, Kontakte, Aufgaben, Freigaben und CRM-Kontext fehlen im Assistant-Dialog

## Zielarchitektur

Die Zielarchitektur besteht aus acht Schichten.

### 1. Input Layer

Eingaenge:

- Browser Text
- Browser Audio
- spaeter Mobile App
- spaeter Car Mode

Verantwortung:

- Audio aufnehmen
- Dateiformat pruefen
- Request an Backend schicken

### 2. STT/TTS Layer

STT:

- Standard: lokaler faster-whisper Server
- Fallback: OpenAI Whisper

TTS:

- Standard: Piper
- optional XTTS fuer eigene Stimmen

Verantwortung:

- Audio zu Text
- Text zu Audio
- technische Fehlerbehandlung

### 3. Conversation Layer

Zentrale Aufgabe:

- der Server ist alleiniger Besitzer des strukturierten Konversationszustands

Der Zustand darf nicht nur aus Freitext bestehen.

Erforderliche Kontextelemente:

- `selected_source_id`
- `selected_mailbox_ids`
- `selected_provider`
- `visible_email_list`
- `visible_thread_list`
- `current_email_id`
- `current_thread_id`
- `current_item_type`
- `pending_action`
- `pending_draft`
- `pending_rule`
- `messages`
- `mode`
- `last_search_query`
- `last_time_filter`
- `cleanup_scope`
- `cleanup_preview`

### 4. LLM Orchestrator

Aufgabe:

- Nutzerintention verstehen
- Tool Calls planen
- Tool-Ergebnisse verarbeiten
- Rueckfragen formulieren
- kurze sprachgeeignete Antworten generieren

Nicht Aufgabe:

- finale Freigabe riskanter Aktionen
- direkter Providerzugriff

### 5. Tool Registry

Alle vom LLM nutzbaren Faehigkeiten werden als explizite Tools registriert.

Wichtige Regel:

- kleine, klar benannte Tools
- keine ueberladenen Super-Tools
- keine Provider-Details im Prompt

### 6. Policy / Safety Layer

Das ist die zentrale Kontrollschicht.

Sie entscheidet:

- ist die Aktion erlaubt
- ist eine Bestaetigung erforderlich
- ist der Kontext gueltig
- ist die Aktion providerseitig unterstuetzt
- darf der User diese Aktion ausfuehren
- soll die Aktion direkt, spaeter oder gar nicht laufen

### 7. Execution Layer

Bestandteile:

- provider-neutrale Service-Interfaces
- Microsoft-Graph-Adapter
- spaeter Google-Workspace-Adapter
- spaeter IMAP/SMTP-Adapter

Wichtige Erweiterung:

- Voice-Tools duerfen nicht direkt an Microsoft Graph gekoppelt bleiben
- stattdessen wird ein provider-neutraler Voice-Execution-Layer benoetigt
- bestehende Plattform-Interfaces wie `MailReadProvider`, `MailActionProvider`, `MailSendProvider` sollen dabei wiederverwendet oder erweitert werden

### 8. Audit / Learning Layer

Es muss nachvollziehbar sein:

- was der User gesagt hat
- was das LLM verstanden hat
- welche Tools vorgeschlagen wurden
- welche Policy-Entscheidung getroffen wurde
- was tatsaechlich ausgefuehrt wurde
- welches Feedback entstand

### 9. Reliability Layer

Dieses System braucht eine eigene Zuverlaessigkeitsschicht fuer produktiven Einsatz.

Aufgaben:

- Retry mit Backoff bei Providerfehlern
- Microsoft-Graph-Throttling sauber behandeln
- Teilfehler in Bulk-Operationen auffangen
- Fallback auf lokale gecachte Daten wenn Live-Zugriff ausfaellt
- Undo-Informationen fuer reversible Aktionen speichern

## Kernprinzipien

## 1. LLM ist Planer, nicht Entscheider

Das LLM darf:

- Tools vorschlagen
- Rueckfragen stellen
- Entwuerfe formulieren
- Ergebnisse zusammenfassen

Das LLM darf nicht:

- ohne serverseitige Freigabe loeschen
- ohne serverseitige Freigabe senden
- Sicherheitsstatus selbst definieren

## 2. Destruktive Aktionen laufen immer ueber Pending State

Nicht erlaubt:

- `delete_email(confirmed=true)` direkt aus dem Modell ohne gueltigen Pending-State

Erlaubt:

1. Aktion vorbereiten
2. Pending-Objekt speichern
3. User bestaetigt
4. Server validiert Pending-Objekt
5. Aktion wird ausgefuehrt

## 3. Providerlogik darf nicht im Prompt stecken

Das LLM kennt:

- fachliche Tools
- nicht Graph-Endpunkte
- nicht Gmail-REST-Details

## 4. Live gegen Provider, DB fuer Hintergrund und Gedächtnis

Live:

- aktuelle Mail lesen
- Ordner abrufen
- Thread-Inhalt abrufen
- Aktion ausfuehren

DB:

- Briefing
- Verlauf
- Suchindex
- Mailbox-Gesundheit
- Regeln
- Audits
- Learning

## 6. Mailbox Intelligence statt nur Einzelaktionen

Der Assistant soll nicht nur einzelne Mails bedienen, sondern ganze Postfaecher bewerten und steuern koennen.

Dafuer braucht er drei fachliche Ebenen:

- `Abfrage`
- `Bewertung`
- `Aktion`

Beispiele:

- `Wieviele ungelesene E-Mails habe ich im Postfach XY?`
- `Wieviele ungelesene E-Mails habe ich in allen Postfaechern seit Freitag frueh?`
- `Schau, ob das Postfach info@firma.de bereinigt werden muss`
- `Bereinige die ungelesenen E-Mails`

Das bedeutet:

- mehrere Postfaecher gleichzeitig adressieren
- Zeitraeume verstehen
- Mailbox-Zustand auswerten
- Regeln auf Mengen statt nur auf Einzelmails anwenden
- Bereinigungen als kontrollierte Bulk-Workflows behandeln

## 5. Alles auditierbar

Jede riskante oder relevante Aktion braucht einen permanenten Datensatz.

## Ziel-Datenmodell

Die bestehenden Tabellen bleiben Basis. Es werden neue Tabellen ergaenzt.

### Bestehende Tabellen weiter nutzen

- `integration_connections`
- `integration_connection_capabilities`
- `assistant_profiles`
- `assistant_sources`
- `assistant_items`
- `assistant_events`
- `assistant_rules`
- `assistant_actions`
- `assistant_feedback`
- `assistant_conversations`

### Neue Tabelle: `assistant_pending_intents`

Zweck:

- zentrale, serverseitig validierte Pending-Objekte fuer riskante Aktionen

Felder:

- `id`
- `tenant_id`
- `user_id`
- `conversation_id` nullable
- `source_id`
- `provider`
- `intent_type`
- `target_type`
- `target_id`
- `payload_json`
- `status`
- `risk_level`
- `confirmation_required`
- `confirmation_token`
- `expires_at`
- `confirmed_at`
- `cancelled_at`
- `executed_action_id` nullable
- `created_at`
- `updated_at`

Status:

- `pending`
- `confirmed`
- `cancelled`
- `expired`
- `executed`
- `failed`

### Neue Tabelle: `assistant_drafts`

Zweck:

- zentrale Draft-Verwaltung fuer Antworten, neue Mails, spaeter Termine

Felder:

- `id`
- `tenant_id`
- `user_id`
- `conversation_id` nullable
- `source_id`
- `draft_type`
- `provider`
- `target_message_id` nullable
- `to_recipients_json`
- `cc_recipients_json`
- `bcc_recipients_json`
- `subject`
- `body_text`
- `body_html`
- `status`
- `metadata_json`
- `created_at`
- `updated_at`

Status:

- `draft`
- `ready_for_confirmation`
- `approved`
- `sent`
- `discarded`
- `failed`

Wichtige Produktregel:

- Antworten und neue E-Mails leben als echte Draft-Objekte in der DB
- sie duerfen nicht nur im `context_json` existieren
- erst ein expliziter Sende-Befehl oder eine explizite Bestaetigung darf sie an den Provider schicken

### Neue Tabelle: `assistant_conversation_turns`

Zweck:

- strukturierte Speicherung jedes einzelnen Assistant-Turns statt nur `messages`-Array im JSON

Felder:

- `id`
- `tenant_id`
- `user_id`
- `conversation_id`
- `turn_index`
- `input_mode`
- `user_text`
- `transcribed_text`
- `assistant_text`
- `tool_calls_json`
- `tool_results_json`
- `latency_ms`
- `error_message`
- `created_at`

### Neue Tabelle: `assistant_audit_log`

Zweck:

- vollstaendige technische und fachliche Nachvollziehbarkeit

Felder:

- `id`
- `tenant_id`
- `user_id`
- `conversation_id` nullable
- `source`
- `event_type`
- `actor_type`
- `request_payload_json`
- `result_payload_json`
- `risk_level`
- `success`
- `error_message`
- `created_at`

Hinweis:

- dieses Audit-Log deckt auch Voice-Aktionen ab
- statt einer isolierten `voice_actions`-Sondertabelle soll eine gemeinsame Audit-Struktur fuer Voice, UI und Background-Actions entstehen

### Optionale spaetere Tabelle: `assistant_search_index`

Zweck:

- lokaler Suchindex fuer alte Mails, Threads, Termine und Regeln

### Neue Tabelle: `assistant_rule_suggestions`

Zweck:

- vom System erkannte, aber noch nicht aktivierte Regelvorschlaege

Felder:

- `id`
- `tenant_id`
- `user_id`
- `source_id` nullable
- `suggestion_type`
- `match_criteria_json`
- `action_type`
- `action_payload_json`
- `confidence`
- `support_count`
- `example_item_ids_json`
- `reason`
- `status`
- `created_at`
- `updated_at`

Status:

- `open`
- `accepted`
- `rejected`
- `expired`

### Neue Tabelle: `assistant_action_patterns`

Zweck:

- haeufig wiederkehrende manuelle User-Aktionen strukturiert sammeln

Felder:

- `id`
- `tenant_id`
- `user_id`
- `source_id` nullable
- `pattern_key`
- `features_json`
- `action_type`
- `action_payload_json`
- `occurrence_count`
- `last_seen_at`
- `created_at`
- `updated_at`

### Neue Tabelle: `assistant_mailbox_health`

Zweck:

- periodische Bewertung von Postfaechern und Bereinigungsbedarf

Felder:

- `id`
- `tenant_id`
- `user_id`
- `source_id`
- `mailbox_address`
- `snapshot_time`
- `unread_count`
- `oldest_unread_at`
- `newsletter_count`
- `systemmail_count`
- `reply_needed_count`
- `low_value_count`
- `cleanup_recommended`
- `health_score`
- `summary_json`

### Neue Tabelle: `assistant_undo_log`

Zweck:

- reversible Aktionen fuer Undo speichern

Felder:

- `id`
- `tenant_id`
- `user_id`
- `source_id`
- `provider`
- `action_id`
- `undo_type`
- `undo_payload_json`
- `expires_at`
- `used_at`
- `created_at`

## Erweiterung des Regelmodells

Das Zielmodell fuer Regeln ist nicht nur simple Senderfilterung.

Regeln sollen kombinieren koennen:

- Postfach / Quelle
- Absender exakt
- Absender enthaelt
- Absender-Domain
- Betreff enthaelt
- Betreff Regex
- Body enthaelt
- Body Regex
- Keywords
- Thread-Muster
- Prioritaet
- Klassifikation
- Zeitmuster

Regelaktionen:

- `move`
- `archive`
- `delete`
- `mute`
- `mark_read`
- `mark_unread`
- `flag`
- `label`
- `never_read_aloud`
- `always_prioritize`

Beispiel:

- LinkedIn-Mails mit Absender `linkedin.com` und Betreff/Inhalt `Sie wurden in ... Suchanfragen gefunden`
- Aktion: nach `Unwichtig` verschieben
- optional zusaetzlich nie vorlesen

## Zielstruktur im Backend

Bestehende Dateien bleiben. Neue Dateien bzw. klare neue Verantwortungen:

- `backend/app/assistant/voice.py`
- `backend/app/assistant/stt.py`
- `backend/app/assistant/policy.py`
- `backend/app/assistant/tool_registry.py`
- `backend/app/assistant/tool_executor.py`
- `backend/app/assistant/drafts.py`
- `backend/app/assistant/audit.py`
- `backend/app/assistant/provider_router.py`
- `backend/app/assistant/search.py`
- `backend/app/assistant/calendar_voice.py`

Empfehlung:

- `voice.py` nur fuer Orchestrierung
- Tool- und Providerlogik aus `voice.py` schrittweise herausziehen

## Zielstruktur im Frontend

Ergaenzungen:

- `frontend/src/components/assistant/VoiceChatPanel.vue`
- `frontend/src/components/assistant/PendingActionBar.vue`
- `frontend/src/components/assistant/DraftReviewPanel.vue`
- `frontend/src/components/assistant/ThreadPreviewPanel.vue`
- `frontend/src/components/assistant/SourceSwitcher.vue`
- `frontend/src/stores/voiceChat.js`
- `frontend/src/composables/useAudioRecording.js`
- `frontend/src/composables/useAudioPlayback.js`

## Ziel-Toolset

Die Tools sollen in vier Stufen aufgebaut werden.

### Stufe A: Inbox-Steuerung

- `list_emails`
- `count_emails`
- `search_emails`
- `read_email_summary`
- `read_email_full`
- `read_thread`
- `has_attachments`
- `list_attachments`
- `next_email`
- `previous_email`
- `select_email`
- `list_folders`

### Stufe B: Mail-Aktionen

- `prepare_delete_email`
- `prepare_move_email`
- `prepare_archive_email`
- `prepare_bulk_cleanup`
- `prepare_mark_spam`
- `mark_read`
- `mark_unread`
- `flag_email`
- `unflag_email`
- `confirm_pending_action`
- `cancel_pending_action`
- `undo_last_action`
- `undo_cleanup_batch`

### Stufe C: Reply- und Draft-System

- `create_reply_draft`
- `revise_pending_draft`
- `preview_pending_draft`
- `confirm_send_pending_draft`
- `discard_pending_draft`
- `create_new_email_draft`
- `send_pending_draft`
- `list_open_drafts`
- `load_draft`
- `edit_draft`

### Stufe D: Regeln und Personalisierung

- `create_rule`
- `update_rule`
- `disable_rule`
- `explain_rule`
- `list_rules`
- `list_rule_suggestions`
- `accept_rule_suggestion`
- `reject_rule_suggestion`
- `explain_why_email_matched_rule`

### Stufe E: Mailbox Intelligence / Cleanup

- `list_mailboxes`
- `count_unread_emails`
- `count_emails_by_timerange`
- `analyze_mailbox_health`
- `preview_cleanup`
- `execute_cleanup`
- `explain_cleanup_plan`
- `show_cleanup_candidates`
- `dry_run_cleanup`

Fachregel:

- `execute_cleanup` fuehrt nie blind alles aus
- zuerst Vorschau
- dann Policy-Bewertung
- dann Bestaetigung
- dann Ausfuehrung in Batches

### Stufe F: Voice-First-Effizienz

- `summarize_for_voice`
- `summarize_thread_for_voice`
- `read_since_last_event`
- `read_since_last_meeting`
- `batch_inbox_review`
- `switch_mode`

### Spaetere Stufe G: Kalender

- `list_events`
- `read_event`
- `create_event_draft`
- `reschedule_event`
- `accept_invite`
- `decline_invite`

### Spaetere Stufe H: Plattform-Assistent

- `find_contact`
- `create_task`
- `list_tasks`
- `create_note`
- `open_crm_context`
- `show_approvals`

## API-Zielbild

### Voice

- `POST /assistant/voice/chat`
- `POST /assistant/voice/transcribe`
- `POST /assistant/voice/tts`

### Pending Intents

- `GET /assistant/intents/pending`
- `POST /assistant/intents/{id}/confirm`
- `POST /assistant/intents/{id}/cancel`

### Drafts

- `GET /assistant/drafts/current`
- `GET /assistant/drafts`
- `POST /assistant/drafts/{id}/confirm-send`
- `POST /assistant/drafts/{id}/discard`
- `PUT /assistant/drafts/{id}`
- `POST /assistant/drafts/{id}/preview`

### Search

- `GET /assistant/search/emails`
- `GET /assistant/search/threads`
- `GET /assistant/search/events`

### Mailbox Intelligence

- `GET /assistant/mailboxes`
- `GET /assistant/mailboxes/stats`
- `GET /assistant/mailboxes/health`
- `POST /assistant/cleanup/preview`
- `POST /assistant/cleanup/execute`
- `POST /assistant/cleanup/dry-run`
- `POST /assistant/cleanup/{batch_id}/undo`

### Rule Suggestions

- `GET /assistant/rule-suggestions`
- `POST /assistant/rule-suggestions/{id}/accept`
- `POST /assistant/rule-suggestions/{id}/reject`

### Attachments

- `GET /assistant/items/{id}/attachments`
- `GET /assistant/attachments/{attachment_id}`

### Undo

- `GET /assistant/undo`
- `POST /assistant/undo/{undo_id}/execute`

### Kalender

- `GET /assistant/events`
- `GET /assistant/events/{id}`
- `POST /assistant/events/draft`
- `POST /assistant/events/{id}/accept`
- `POST /assistant/events/{id}/decline`

## Policy-Layer Design

Es gibt drei Entscheidungsebenen.

### Ebene 1: Capability-Pruefung

- ist Quelle verbunden
- ist Provider unterstuetzt
- hat Quelle benoetigte Capability

### Ebene 2: Risikopruefung

Niedrig:

- lesen
- auflisten
- zusammenfassen
- suchen

Mittel:

- archivieren
- verschieben
- markieren
- Regeln anlegen

Hoch:

- loeschen
- senden
- Spam-Markierung
- automatisch antworten

### Ebene 3: Ausfuehrungspolitik

Moegliche Entscheidungen:

- `allow_immediate`
- `require_confirmation`
- `require_draft_review`
- `allow_with_undo`
- `deny`
- `provider_not_supported`

### Ebene 4: Reliability

Die Policy-/Execution-Schicht muss zusaetzlich behandeln:

- Throttling
- Retry
- idempotente Wiederholung
- Undo-Faehigkeit
- Fallback auf Cache

## Voice-/Chat-Konversationsmodell

Empfohlenes `context_json`:

```json
{
  "messages": [],
  "selected_source_id": 1,
  "selected_mailbox_ids": [1, 2],
  "selected_provider": "microsoft_graph",
  "visible_email_list": [],
  "visible_thread_list": [],
  "current_email_id": null,
  "current_thread_id": null,
  "current_item_type": "email",
  "mode": "inbox",
  "last_search_query": null,
  "last_time_filter": null,
  "cleanup_scope": null,
  "cleanup_preview": null,
  "pending_action_id": null,
  "pending_draft_id": null,
  "last_live_failure": null,
  "fallback_mode": false
}
```

Wichtig:

- `pending_confirmation` und `pending_reply` im freien Kontext sind nur Zwischenstand
- Ziel ist ein vollstaendiger serverseitiger Verweis auf echte DB-Objekte

## LLM-Orchestrierung mit Qwen

Empfehlung fuer lokale Modelle:

- Qwen2.5:14B fuer schnellere Interaktion
- Qwen2.5:32B fuer robustere Tool-Nutzung und komplexere Anfragen

Spezifisch fuer Voice:

- rohe Graph-Previews reichen nicht fuer gute Vorlesequalitaet
- der Assistant braucht eine eigene Voice-Zusammenfassungsschicht
- Ziel ist nicht `250 Zeichen bodyPreview`, sondern semantische Kurzfassungen wie:
  - `Mail von deinem Chef: Er fragt nach dem Status von Projekt X und erwartet heute Rueckmeldung.`

### Prompt-Prinzipien

- kurz
- deterministisch
- keine providerinternen Details
- klare Regel fuer Bestaetigungen
- klare Regel fuer Mehrdeutigkeiten

### Tool-Calling-Regeln

- pro Turn maximal wenige Tool-Schritte
- bei mehreren Kandidaten zuerst Auswahl
- bei riskanten Aktionen nie direkt finalisieren
- bei fehlendem Kontext nie raten

### Modellwechsel nach Aufgabe

Empfehlung:

- Voice-Orchestrierung: lokales Qwen
- spaeter komplexe Langtexte optional ueber groesseres Modell
- Klassifikation/Briefing getrennt halten

## Provider-Strategie

### Phase 1

- `microsoft_graph` vollstaendig

### Phase 2

- `google_workspace` parity fuer:
- listen
- lesen
- verschieben
- draft
- senden
- Ordner/Labels

### Phase 3

- IMAP/SMTP mit eingeschraenkter Capability

### Phase 4

- Exchange On-Prem oder EWS falls noetig

## Attachment-Awareness

Fuer echtes E-Mail-Arbeiten per Sprache ist Anhangsverstaendnis Pflicht.

Der Assistant muss beantworten koennen:

- hat die Mail Anhaenge
- welche Anhaenge sind dabei
- ist es PDF, Bild, Dokument
- wie gross ist der Anhang

Spaeter:

- Anhaenge lokal zusammenfassen
- PDFs grob extrahieren
- Bilder beschreiben

## Kalender-Kontext im Voice-Flow

Fuer natuerliche Sprache sind Kalender und Mail eng gekoppelt.

Beispiele:

- `Lies mir die Mails seit dem letzten Meeting mit Hans`
- `Was kam seit meinem Termin heute Morgen rein?`

Dafuer braucht der Voice-Flow:

- Kalenderzugriff
- Zeitanker aus Terminen
- Referenzen auf Meetings und Teilnehmer

## Offline- und Fallback-Strategie

Wenn Live-Provider nicht erreichbar sind, soll der Assistant degradiert weiterarbeiten statt hart auszufallen.

Fallback-Modi:

- `live`
- `cache_assisted`
- `offline_readonly`

Erlaubt im Fallback:

- zaehlen aus lokalen Daten
- alte Items zusammenfassen
- Regeln erklaeren
- Drafts lokal vorbereiten

Nicht erlaubt im Fallback:

- Live-Loeschen
- Live-Verschieben
- Live-Senden ohne Provider

## Multi-Mailbox- und Zeitfilter-Faehigkeit

Der Assistant muss Scope und Zeitraum sprachlich verstehen.

Unterstuetzte Scopes:

- einzelnes Postfach
- alle Postfaecher
- mehrere konkret genannte Postfaecher
- Postfaecher mit bestimmter Rolle

Unterstuetzte Zeitfilter:

- heute
- gestern
- seit heute frueh
- seit Freitag frueh
- seit gestern Abend
- letzte 24 Stunden
- letzte 7 Tage

Empfehlung:

- Zeitfilter serverseitig normalisieren
- LLM darf nur den Ausdruck erkennen
- Umrechnung in absoluten Zeitraum erfolgt im Backend

## Cleanup-Engine

`Bereinige die ungelesenen E-Mails` ist kein Einzeltool, sondern ein Workflow.

Schritte:

1. Scope bestimmen
2. Zeitraum bestimmen
3. Kandidaten laden
4. Regeln anwenden
5. Klassifikation und Confidence berechnen
6. Bulk-Plan erzeugen
7. Vorschau anzeigen
8. nach Risiko gruppieren
9. Bestaetigung einholen
10. in Batches ausfuehren
11. Audit speichern
12. Lernsignale aktualisieren

Cleanup-Plan enthaelt:

- Anzahl zu archivieren
- Anzahl zu verschieben
- Anzahl zu loeschen
- Anzahl mit niedriger Confidence
- Anzahl mit Konflikten

Zusaetzlich:

- `dry_run`-Ergebnis
- Undo-Moeglichkeit pro Batch
- Liste der betroffenen Regel-IDs

Wichtig:

- Low-Risk kann optional in Batch nach Gesamtbestaetigung laufen
- Medium-/High-Risk muessen strenger bestaetigt werden
- Konflikte und unsichere Faelle werden nie blind ausgefuehrt
- vor produktiver Ausfuehrung muss immer ein Trockenlauf verfuegbar sein
- Bulk-Cleanup muss eine moeglichst weitgehende Rueckgaengig-Funktion haben

## Lernlogik

Das System soll aus Wiederholungen lernen.

Beispiele:

- derselbe LinkedIn-Typ wird dreimal nach `Unwichtig` verschoben
- ein bestimmter Newsletter wird mehrfach archiviert
- ein bestimmter Systemabsender wird immer als unwichtig markiert

Daraus entsteht:

1. Pattern-Erkennung
2. Clustering aehnlicher Mails
3. Regelvorschlag
4. User-Freigabe
5. Aktivierung als `origin=learned`

Lernregeln:

- keine automatische High-Risk-Regel ohne explizite Zustimmung
- `delete` und `send` nie rein aus implizitem Lernen aktivieren
- `move`, `archive`, `mute`, `never_read_aloud` sind geeignete Lernaktionen

## Effizienzfunktionen fuer echtes Voice-First-Arbeiten

Um E-Mail-Arbeit wirklich effizient per Sprache abzubilden, sollte der Assistant zusaetzlich koennen:

- kompaktes Morgenbriefing ueber alle Postfaecher
- Inbox-Zero-Ansicht fuer jedes Postfach
- Bulk-Review in Stapeln
- Schnellbefehle wie `naechste`, `archivieren`, `antworten`, `weiter`
- Antwortstile pro Kontakt lernen
- Postfach-Gesundheit bewerten
- Mails mit hoher Relevanz zuerst vorlesen
- unwichtige Mails still im Hintergrund einsortieren
- bei langen Mails automatisch Kurz- und Langfassung anbieten
- Folgefragen wie `gibt es dazu einen Thread?`, `was ist seit Freitag passiert?`
- `lies nur die wichtigen`
- `lies nur was beantwortet werden muss`
- `lies seit dem letzten Meeting mit Hans`

Weitere sinnvolle Faehigkeiten:

- Thread-Zusammenfassungen statt Einzelmails
- Antwortvorschlaege in verschiedenen Tonalitaeten
- Erkennung von `antwort noetig`, `warten auf andere`, `nur Info`
- Wiedervorlage / Follow-up
- Tageszusammenfassung mit Mail + Kalender
- Lesemodus im Auto mit sehr kurzen Antworten
- stiller Arbeitsmodus im Browser mit Text-only
- Undo-Befehle wie `doch nicht`, `rueckgaengig`, `hol die Mail zurueck`
- Batch-Kommandos wie `alles Unwichtige weg`, aber immer ueber Preview + Bestätigung

## Draft-Management

Das Draft-System ist ein eigener Kernbereich und kommt vor weiteren Komfortfeatures.

Anforderungen:

- Reply-Drafts und neue Mail-Drafts leben in DB
- Drafts sind editierbar
- Drafts koennen vorgelesen und ueberarbeitet werden
- Drafts koennen explizit verworfen werden
- Drafts koennen spaeter wieder aufgenommen werden

Das aktuelle `pending_reply` im Kontext ist nur Uebergang.

Ziel:

- `pending_reply` wird durch echte `assistant_drafts` ersetzt

## Undo-Strategie

Ein produktiver Assistant braucht Rueckgaengig-Faehigkeit.

Scope:

- delete -> Soft-Delete/Papierkorb nutzen
- move -> Ursprungsordner merken
- bulk cleanup -> Batch-Undo

Regel:

- nur reversible Aktionen bekommen `allow_with_undo`
- Undo-Fenster und Providergrenzen klar definieren

## Rate Limiting / Backoff / Retry

Microsoft Graph und spaetere Provider haben Throttling.

Deshalb braucht die Execution-Schicht:

- Retry mit exponentiellem Backoff
- 429-Erkennung
- Jitter
- providerbezogene Retry-Limits
- Circuit Breaker fuer kaputte Quellen

Fachliche Regel:

- ein Voice-Turn darf nicht unkontrolliert N Provider-Calls ausloesen
- Bulk-Faelle muessen in Batches und mit Limitierung laufen

## Frontend-Zielbild

Der Test-Tab reicht nicht als Endzustand.

Noetige UI-Bereiche:

- Voice-/Chat-Flaeche
- Kontext-Bar fuer aktuelle Mail oder Thread
- Draft-Review-Flaeche
- Pending-Action-Flaeche
- Source-Wechsel
- Activity-/Audit-Flaeche
- Rule-Suggestion-Flaeche

### Zwingend fuer produktive Bedienung

- sichtbare Anzeige offener Bestaetigungen
- sichtbare Anzeige offener Drafts
- klarer Abbrechen-Button
- klarer Senden-Button nur fuer bestaetigte Entwuerfe
- Fehlerstatus fuer STT, TTS, Provider und LLM

## Auditing

Folgende Ereignisse muessen auditiert werden:

- User Message empfangen
- STT erfolgreich/fehlgeschlagen
- LLM Request gesendet
- Tool vorgeschlagen
- Tool geblockt
- Pending Intent erstellt
- Pending Intent bestaetigt
- Pending Intent abgelehnt
- Draft erstellt
- Draft gesendet
- Provider Call erfolgreich/fehlgeschlagen

## Learning

Learning darf nie direkt Sicherheitsgrenzen umgehen.

Erlaubt:

- Vorschlaege fuer Regeln
- bessere Priorisierung
- personalisierte Zusammenfassungen

Nicht erlaubt:

- aus Feedback direkt stilles automatisches Loeschen ohne explizite Freigabelogik

## Teststrategie

## A. Stabilisierung bestehender Tests

Zuerst:

- haengenden Assistant-Testlauf reparieren
- Test-Setup deterministisch machen
- `test_get_profile_creates_default` wieder stabil zum Laufen bringen

## B. Backend-Unit-Tests

Pflichttests:

- Policy-Layer Entscheidungen
- Pending-Intent Lifecycle
- Draft Lifecycle
- Tool Registry Validation
- Provider Gating
- Migrationen
- OAuth Shared Layer
- Undo-Logik
- Retry-/Backoff-Entscheidungen
- Attachment-Metadaten

## C. Backend-Integrationstests

- Voice Chat mit Text
- Voice Chat mit Audio
- Bestaetigungspfad fuer delete/move/send
- Draft + confirm_send
- Source-Wechsel
- unsupported provider
- dry-run cleanup
- cleanup execute + undo
- fallback auf cached items bei Providerfehler

## D. Frontend-Tests

- VoiceChat Panel Interaktion
- Audio Recording Mock
- Audio Playback Mock
- Pending Action Anzeige
- Draft Review Anzeige

## E. E2E-Tests

- "Lies mir die 5 neuesten Mails vor"
- "Loesche die zweite Mail" -> Rueckfrage -> Ja -> geloescht
- "Antworte auf Mail 1" -> Entwurf -> Bestaetigung -> gesendet
- "Verschiebe diese Mail nach Archiv" -> Rueckfrage -> Ja
- "Lege eine Regel an"
- "Wieviele ungelesene E-Mails habe ich in allen Postfaechern seit Freitag frueh?"
- "Zeig mir was du bereinigen wuerdest"
- "Bereinige die ungelesenen E-Mails" -> Vorschau -> Bestätigung
- "Rueckgaengig"

## Lieferphasen

## Phase 1: Assistant-Core stabilisieren

Ziel:

- vorhandenen Assistant sicher und testbar machen

Arbeiten:

- Test-Haenger beheben
- Migration `056` scopes-verlustfrei machen
- `assistant_actions`/`assistant_pending_intents` einfuehren oder konsolidieren
- `assistant_conversation_turns` einfuehren
- `assistant_drafts` produktiv nutzen
- bestehende Voice-Confirmation-Logik auf echte DB-Objekte umstellen
- `voice.py` intern auf Tool-Registry + Policy vorbereiten
- Retry-/Backoff-Grundlage einbauen

Ergebnis:

- sicherer Kern
- stabile Tests
- keine prompt-only Sicherheitslogik

## Phase 2: Voice-Mail produktionsreif fuer Microsoft Graph

Ziel:

- Inbox- und Reply-Steuerung fuer Microsoft 365 belastbar

Arbeiten:

- Search-Tools
- Thread-Tools
- Count-/Stats-Tools
- Multi-Mailbox-Scopes
- Draft-Review
- Pending-Action-UI
- Audit Log
- Cleanup-Preview und Cleanup-Ausfuehrung
- erste Lernlogik fuer Regelvorschlaege
- Attachment-Tools
- Undo fuer Einzelaktionen und Cleanup-Batches
- semantische Voice-Zusammenfassungen
- Frontend-Konsole statt nur Test-Tab

Ergebnis:

- produktive E-Mail-Bedienung per Voice/Text fuer Microsoft 365
- mailboxuebergreifende Voice-Steuerung inklusive Cleanup

## Phase 3: Google Workspace Parity

Ziel:

- zweiter Provider auf gleichem Niveau

Arbeiten:

- Google-spezifische Mail-/Label-Adapter
- Draft-/Send-/Move-Unterstuetzung
- Provider-Router vollenden
- Tests fuer beide Provider

Ergebnis:

- Voice-/Chat-Assistent fuer Microsoft und Google

## Phase 4: Kalender

Ziel:

- Sprachsteuerung fuer Termine

Arbeiten:

- Event-Tools
- Event-Drafts
- RSVP-Flows
- Kalender-Kontext in Conversation

Ergebnis:

- echter E-Mail-und-Kalender-Assistent

## Phase 5: Plattform-Assistent

Ziel:

- Name `assistant` fachlich voll ausspielen

Arbeiten:

- Kontakte
- Aufgaben
- Notizen
- Freigaben
- CRM-Kontext
- spaeter moduluebergreifende Tools

Ergebnis:

- persoenlicher, moduluebergreifender Arbeitsassistent

## Konkrete naechste Umsetzungsschritte

Die naechsten 10 technischen Schritte sollten in genau dieser Reihenfolge erfolgen:

1. Test-Haenger im Assistant-Setup analysieren und beheben
2. Migration `056` auf verlustfreie JSON/JSONB-Uebernahme von `scopes` korrigieren
3. Tabelle `assistant_pending_intents` einfuehren
4. Tabelle `assistant_drafts` einfuehren
5. Tabelle `assistant_conversation_turns` einfuehren
6. Voice-Confirmation von `context_json`-Inlineobjekten auf `assistant_pending_intents` umstellen
7. `reply_to_email` und `confirm_and_send` auf echte Draft-Objekte umstellen
8. `voice.py` in Orchestrator, Tool-Registry, Policy und Executor aufteilen
9. Retry-/Backoff-/Rate-Limit-Basis in den Providerpfad einbauen
10. `search_emails`, `read_thread`, `archive_email`, `mark_read`, `mark_unread`, Attachment-Tools implementieren
11. `count_emails`, `analyze_mailbox_health`, `preview_cleanup`, `execute_cleanup`, `undo_cleanup_batch` implementieren
12. Lernlogik fuer wiederholte manuelle Aktionen in `assistant_rule_suggestions` aufbauen
13. Pending-Action-, Cleanup-, Undo- und Draft-Review-UI im Frontend bauen
14. Echte Backend- und E2E-Tests fuer den gesamten Voice-Pfad fertigstellen

## Abnahmekriterien

Der Ausbau ist erst dann erfolgreich, wenn folgende Faelle sicher und reproduzierbar funktionieren:

- User kann die neuesten Mails vorlesen lassen
- User kann mailboxuebergreifend zaehlen und filtern
- User kann zwischen Mails und Threads navigieren
- User kann Antworten als Entwurf formulieren und erst nach Freigabe senden
- User kann Mails loeschen oder verschieben nur nach serverseitig validierter Bestaetigung
- User kann Regeln per Sprache erstellen und diese wirken tatsaechlich
- User kann Postfaecher auf Bereinigungsbedarf pruefen
- User kann Cleanup-Vorschauen erhalten und bestaetigt ausfuehren
- das System schlaegt aus wiederholten Aktionen neue Regeln vor
- User kann `rueckgaengig` fuer geeignete Aktionen verwenden
- User kann sehen, ob eine Mail Anhaenge hat
- Voice-Zusammenfassungen sind semantisch brauchbar und nicht nur rohe Preview-Texte
- bei Live-Provider-Ausfall kann der Assistant sinnvoll degradiert weiterarbeiten
- User kann zwischen mehreren Quellen wechseln
- Microsoft und Google werden einheitlich unterstuetzt
- der komplette Flow ist auditiert
- die Test-Suite ist gruen

## Zusammenfassung

Der aktuelle Assistant ist bereits ein starker Prototyp mit echter Funktionalitaet.

Um das Ziel "alles moeglich" zu erreichen, braucht es jetzt keine unstrukturierte Feature-Menge, sondern:

- Vereinheitlichung
- Safety
- Provider-Abstraktion
- Draft-/Pending-Objekte
- Audit
- Tests
- danach erst breite Funktionsausweitung

Dieses Dokument ist der technische Masterplan fuer diesen Ausbau.
