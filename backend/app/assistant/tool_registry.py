"""Assistant voice tool registry and system prompt."""

SYSTEM_PROMPT = """Du bist ein persoenlicher E-Mail-Assistent der per Sprache bedient wird.

KERNREGELN:
- Antworte IMMER auf Deutsch, kurz und klar (deine Antworten werden vorgelesen)
- Nutze IMMER die Tools. Erfinde NIEMALS E-Mail-Inhalte oder Absender
- "diese Email", "die Email", "die aktuelle" = die Email auf der wir gerade stehen
- Bei generischen Folgeaktionen ohne explizite Nummer immer die AKTUELL geoeffnete Email verwenden
- Bei "naechste"/"weiter" IMMER next_email aufrufen. Entscheide NIE selbst ob es noch Emails gibt
- Du weisst NICHT wie viele Emails es insgesamt gibt. Nur das Tool weiss das.

NATUERLICHE BEFEHLE:
- "naechste" / "weiter" / "und weiter" / "skip" -> next_email
- "zurueck" / "vorherige" / "nochmal die davor" -> previous_email
- "lies die nochmal" / "wiederhole" -> read_email
- "gib mir einen Ueberblick" / "fass den Posteingang zusammen" -> summarize_inbox
- "verarbeite die neuesten Mails" / "triagiere meinen Eingang" -> triage_batch
- "lies die ganz vor" / "komplett" / "den ganzen Text" -> read_email_full
- "lies den Termin vor" / "was ist Termin 2?" -> read_event
- "naechster Termin" / "weiter im Kalender" -> next_event
- "vorheriger Termin" / "zurueck im Kalender" -> previous_event
- "gib mir einen Terminueberblick" / "fass den Kalender zusammen" -> summarize_schedule
- "loesch die" / "weg damit" / "brauche ich nicht" -> delete_email
- "archivieren" / "ab ins Archiv" -> move_to_status mit status=ARCHIV
- "todo" / "muss ich noch machen" -> move_to_status mit status=TODO
- "nachverfolgen" / "warte auf Antwort" -> move_to_status mit status=WARTEN
- "temp 5 tage" / "temp bis Freitag" -> move_to_status mit status=TEMP und expires_in_days (du berechnest NUR die Anzahl Tage, der Server berechnet das Datum)
- "setze Temp auf 10 Tage" -> set_temp_expiry mit expires_in_days
- WICHTIG: Du kennst das aktuelle Datum NICHT. Gib bei TEMP immer nur die Anzahl Tage an, NIE ein konkretes Datum. "bis Freitag" = berechne die Tage bis Freitag relativ zu heute.
- "falsche Email" / "du verwechselst das" / "nicht diese" -> cancel_pending_action
- "raeum TEMP auf" / "welche TEMP Mails sind abgelaufen?" -> review_expired_temp
- "pruefe WARTEN" / "worauf warte ich noch?" -> review_waiting
- "zeig vergessene TODOs" / "was liegt noch auf TODO?" -> review_stale_todos
- "verschieben nach X" -> move_email
- "antworten" / "schreib zurueck" -> reply_to_email
- "weiterleiten an X" / "leite das an X weiter" / "forward an X" -> forward_email (fragt ob kommentarlos oder mit Kommentar)
- "schreibe eine neue Email" / "neue Mail an X" -> compose_email
- "lies den Entwurf vor" / "zeige den Entwurf" -> preview_draft
- "aendere den Entwurf" / "formuliere um" -> revise_draft
- "verwirf den Entwurf" -> discard_draft
- "als gelesen markieren" -> mark_read
- "markieren" / "wichtig markieren" -> flag_email
- "Markierung entfernen" -> unflag_email
- "Termin zusagen" / "Termin absagen" / "vielleicht zusagen" -> accept_event, decline_event oder tentative_event
- "rueckgaengig" / "undo" -> undo_last_action
- "abbrechen" / "doch nicht" / "falsche Mail" / "du verwechselst" / "nicht diese" -> cancel_pending_action oder discard_draft, je nach Kontext
- "mache das Cleanup rueckgaengig" -> undo_last_cleanup
- "warum passt diese Email zu einer Regel?" -> explain_email_rules
- "welche Regeln schlaegst du vor?" -> list_rule_suggestions
- "lies den Autopilot-Bericht vor" / "was hat der Autopilot gemacht?" -> read_autopilot_report
- "uebernehme Vorschlag 1" -> apply_rule_suggestion
- "nutze das Postfach XY" -> set_active_mailbox
- "wieder alle Postfaecher" -> clear_active_mailbox
- "nutze den Ordner Archiv" / "geh in Unwichtig" -> set_active_folder
- "wieder alle Ordner" -> clear_active_folder
- "ist da ein Anhang?" -> list_attachments
- Der User kann ALLES frei formulieren. Mappe es auf das richtige Tool.

WORKFLOW:
Wenn der User Emails durchgeht, lies jede Email kurz vor (2-3 Saetze) und frage:
"Was soll ich damit tun?"
Nach jeder Aktion zeigt das Tool-Ergebnis automatisch die naechste Email. Lies sie vor.
Mach weiter bis der User "stopp", "genug" oder "fertig" sagt.

SICHERHEIT:
- Loeschen, Verschieben, Senden: Die Tools fragen automatisch nach Bestaetigung
- Antworten: Erstellt einen Entwurf. Lies ihn vor, frage "Soll ich absenden?"
- Fuehre destruktive Aktionen NIE ohne Bestaetigung aus"""

AI_SUGGESTIONS_PROMPT = """

KI-AKTIONSVORSCHLAEGE (aktiv):
Wenn der User sagt "bearbeite das Postfach", "neue Emails", "pruefe neue Emails", "lies vor", "triagiere":

ABLAUF — STRIKT Email fuer Email:
1. Rufe next_email auf (NICHT list_emails, NICHT triage_batch). Das laedt genau EINE Email.
2. Lies sie dem User kurz vor: Absender, Betreff, 1 Satz Inhalt.
3. Mache GENAU EINEN konkreten Vorschlag. KEINE Alternativen anbieten. Entscheide dich:
   - Newsletter/Benachrichtigung/Marketing → "Archivieren?"
   - Automatische System-Mail (LinkedIn, GitHub, etc.) → "Archivieren?"
   - Spam/Werbung → "Loeschen?"
   - Persoenlich/geschaeftlich → "Auf TODO setzen?"
   - Wartet auf Antwort → "Auf WARTEN setzen?"
4. Warte auf Antwort. Bei "ja"/"ok"/"mach das" → fuehre GENAU diesen Vorschlag aus.
   Bei anderer Anweisung → fuehre die Anweisung des Users aus.
5. Nach der Aktion zeigt das Tool-Ergebnis automatisch die naechste Email. Lies sie vor und mache wieder EINEN Vorschlag.
6. Wiederhole bis der User "stopp"/"genug"/"fertig" sagt.

REGELN:
- IMMER nur EINE Email auf einmal. Nie mehrere laden oder auflisten.
- IMMER genau EINEN Vorschlag. Nie "archivieren oder loeschen?" — entscheide dich fuer das Wahrscheinlichste.
- Der User hat das letzte Wort. Du fuehrst NICHTS eigenmaechtig aus.
- Bei Unsicherheit ueber die richtige Aktion: "Was soll ich damit tun?" ohne Vorschlag.
- Halte dich kurz. Kein "Ich habe X Emails geladen". Einfach vorlesen und vorschlagen."""

TOOLS = [
    {"type": "function", "function": {"name": "archive_email", "description": "Kompatibilitaetsalias fuer move_to_status mit status=ARCHIV. Ohne email_index gilt die aktuell geoeffnete Email.", "parameters": {"type": "object", "properties": {"email_index": {"type": "integer", "description": "Optional: Nummer der Email. Ohne Angabe wird die aktuelle Email verwendet."}, "confirmed": {"type": "boolean", "description": "true wenn der User bereits bestaetigt hat", "default": False}}}}},
    {"type": "function", "function": {"name": "mark_read", "description": "Markiere eine Email als gelesen", "parameters": {"type": "object", "properties": {"email_index": {"type": "integer", "description": "Nummer der Email"}}, "required": ["email_index"]}}},
    {"type": "function", "function": {"name": "mark_unread", "description": "Markiere eine Email als ungelesen", "parameters": {"type": "object", "properties": {"email_index": {"type": "integer", "description": "Nummer der Email"}}, "required": ["email_index"]}}},
    {"type": "function", "function": {"name": "read_event", "description": "Lies einen Termin aus der aktuellen Terminliste mit Details vor", "parameters": {"type": "object", "properties": {"event_index": {"type": "integer", "description": "Nummer des Events aus der aktuellen Terminliste"}}, "required": ["event_index"]}}},
    {"type": "function", "function": {"name": "undo_last_action", "description": "Mache die letzte rueckgaengig machbare Aktion rueckgaengig", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "cancel_pending_action", "description": "Brich die aktuell offene bestaetigungspflichtige Aktion ab", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "undo_last_cleanup", "description": "Mache den letzten Cleanup-Batch soweit moeglich rueckgaengig", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "explain_email_rules", "description": "Erklaere, welche aktiven Regeln auf eine Email passen und welche Aktion daraus folgen wuerde", "parameters": {"type": "object", "properties": {"email_index": {"type": "integer", "description": "Nummer der Email in der aktuellen Liste"}}}}},
    {"type": "function", "function": {"name": "set_active_mailbox", "description": "Setze ein verbundenes Postfach als Standard fuer Folgeaktionen", "parameters": {"type": "object", "properties": {"mailbox": {"type": "string", "description": "Email-Adresse des verbundenen Postfachs"}}, "required": ["mailbox"]}}},
    {"type": "function", "function": {"name": "clear_active_mailbox", "description": "Entferne das aktuell gesetzte Standard-Postfach und arbeite wieder ohne festen Mailbox-Scope", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "set_active_folder", "description": "Setze einen Mailordner als Standard fuer Folgeaktionen", "parameters": {"type": "object", "properties": {"folder": {"type": "string", "description": "Name des Ordners, z.B. Archiv oder Unwichtig"}}, "required": ["folder"]}}},
    {"type": "function", "function": {"name": "clear_active_folder", "description": "Entferne den aktuell gesetzten Standard-Ordner", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "list_rule_suggestions", "description": "Liste automatisch gelernte Regelvorschlaege auf", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "apply_rule_suggestion", "description": "Uebernehme einen Regelvorschlag aus der aktuellen Vorschlagsliste", "parameters": {"type": "object", "properties": {"suggestion_index": {"type": "integer", "description": "Nummer des Vorschlags aus list_rule_suggestions"}}, "required": ["suggestion_index"]}}},
    {"type": "function", "function": {"name": "flag_email", "description": "Markiere eine Email als wichtig oder zur Wiedervorlage", "parameters": {"type": "object", "properties": {"email_index": {"type": "integer", "description": "Nummer der Email"}}, "required": ["email_index"]}}},
    {"type": "function", "function": {"name": "unflag_email", "description": "Entferne die Markierung einer Email", "parameters": {"type": "object", "properties": {"email_index": {"type": "integer", "description": "Nummer der Email"}}, "required": ["email_index"]}}},
    {"type": "function", "function": {"name": "next_event", "description": "Gehe zum naechsten Termin in der aktuellen Terminliste", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "previous_event", "description": "Gehe zum vorherigen Termin in der aktuellen Terminliste", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "accept_event", "description": "Nimm einen Kalendertermin an. Erfordert Bestaetigung.", "parameters": {"type": "object", "properties": {"event_index": {"type": "integer", "description": "Nummer des Events aus der aktuellen Terminliste"}, "comment": {"type": "string", "description": "Optionale Nachricht zur Zusage"}, "confirmed": {"type": "boolean", "description": "true wenn der User bereits bestaetigt hat", "default": False}}, "required": ["event_index"]}}},
    {"type": "function", "function": {"name": "decline_event", "description": "Lehne einen Kalendertermin ab. Erfordert Bestaetigung.", "parameters": {"type": "object", "properties": {"event_index": {"type": "integer", "description": "Nummer des Events aus der aktuellen Terminliste"}, "comment": {"type": "string", "description": "Optionale Nachricht zur Absage"}, "confirmed": {"type": "boolean", "description": "true wenn der User bereits bestaetigt hat", "default": False}}, "required": ["event_index"]}}},
    {"type": "function", "function": {"name": "tentative_event", "description": "Sage einen Kalendertermin unter Vorbehalt zu. Erfordert Bestaetigung.", "parameters": {"type": "object", "properties": {"event_index": {"type": "integer", "description": "Nummer des Events aus der aktuellen Terminliste"}, "comment": {"type": "string", "description": "Optionale Nachricht zur vorlaeufigen Zusage"}, "confirmed": {"type": "boolean", "description": "true wenn der User bereits bestaetigt hat", "default": False}}, "required": ["event_index"]}}},
    {"type": "function", "function": {"name": "list_events", "description": "Liste bevorstehende oder letzte Kalendertermine auf", "parameters": {"type": "object", "properties": {"mailbox": {"type": "string", "description": "Optionales Postfach fuer den Kalender"}, "limit": {"type": "integer", "description": "Maximale Anzahl Events", "default": 5}}}}},
    {"type": "function", "function": {"name": "summarize_schedule", "description": "Gib einen kompakten Ueberblick ueber die naechsten Termine", "parameters": {"type": "object", "properties": {"mailbox": {"type": "string", "description": "Optionales Postfach fuer den Kalender"}, "limit": {"type": "integer", "description": "Maximale Anzahl Termine", "default": 5}, "refresh": {"type": "boolean", "description": "Wenn true, die Terminliste vorher live neu laden", "default": False}}}}},
    {"type": "function", "function": {"name": "search_emails", "description": "Suche Emails nach Freitext in Betreff oder Vorschau", "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "Suchbegriff fuer Betreff oder Vorschau"}, "mailbox": {"type": "string", "description": "Optionales Postfach fuer die Suche"}, "folder": {"type": "string", "description": "Optionaler Ordnername fuer die Suche"}, "sender": {"type": "string", "description": "Optionaler Absender oder Domain-Teil fuer die Suche"}, "all_mailboxes": {"type": "boolean", "description": "Wenn true, alle verbundenen Postfaecher durchsuchen", "default": False}, "unread_only": {"type": "boolean", "description": "Nur ungelesene Emails durchsuchen", "default": False}, "since": {"type": "string", "description": "Optionaler ISO-Zeitstempel oder Ausdruck wie 'gestern', 'freitag frueh'"}, "since_last_meeting_with": {"type": "string", "description": "Optionaler Name oder Email fuer 'seit dem letzten Meeting mit X'"}, "limit": {"type": "integer", "description": "Maximale Trefferzahl", "default": 10}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "analyze_mailbox", "description": "Bewerte, ob ein Postfach bereinigt werden sollte", "parameters": {"type": "object", "properties": {"mailbox": {"type": "string", "description": "Optionales Postfach fuer die Analyse"}, "all_mailboxes": {"type": "boolean", "description": "Wenn true, alle verbundenen Postfaecher analysieren", "default": False}, "unread_only": {"type": "boolean", "description": "Nur ungelesene Emails bewerten", "default": True}}}}},
    {"type": "function", "function": {"name": "preview_cleanup", "description": "Pruefe ungelesene Emails gegen vorhandene Regeln und zeige, was bereinigt werden koennte", "parameters": {"type": "object", "properties": {"mailbox": {"type": "string", "description": "Optionales Postfach fuer die Vorschau"}, "all_mailboxes": {"type": "boolean", "description": "Wenn true, alle verbundenen Postfaecher pruefen", "default": False}, "unread_only": {"type": "boolean", "description": "Nur ungelesene Emails beruecksichtigen", "default": True}, "limit_per_mailbox": {"type": "integer", "description": "Maximale Anzahl pro Postfach", "default": 30}}}}},
    {"type": "function", "function": {"name": "execute_cleanup", "description": "Fuehre die zuletzt erzeugte Cleanup-Vorschau nach ausdruecklicher Bestaetigung aus", "parameters": {"type": "object", "properties": {"confirmed": {"type": "boolean", "description": "true wenn der User die Bulk-Bereinigung bestaetigt hat", "default": False}}}}},
    {"type": "function", "function": {"name": "list_mailboxes", "description": "Liste die verbundenen Postfaecher auf", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "count_emails", "description": "Zaehle Emails im aktuellen, einem bestimmten oder allen Postfaechern", "parameters": {"type": "object", "properties": {"mailbox": {"type": "string", "description": "Optionale Mailbox-Adresse fuer ein bestimmtes Postfach"}, "folder": {"type": "string", "description": "Optionaler Ordnername fuer die Zaehkung"}, "all_mailboxes": {"type": "boolean", "description": "Wenn true, alle verbundenen Postfaecher zaehlen", "default": False}, "unread_only": {"type": "boolean", "description": "Nur ungelesene Emails zaehlen", "default": False}, "since": {"type": "string", "description": "Optionaler ISO-Zeitstempel oder Ausdruck wie 'heute', 'gestern', 'freitag frueh'"}, "since_last_meeting_with": {"type": "string", "description": "Optionaler Name oder Email fuer 'seit dem letzten Meeting mit X'"}}}}},
    {"type": "function", "function": {"name": "list_emails", "description": "Liste die neuesten oder ungelesenen Emails auf", "parameters": {"type": "object", "properties": {"unread_only": {"type": "boolean", "description": "Nur ungelesene Emails", "default": False}, "limit": {"type": "integer", "description": "Maximale Anzahl (1-20)", "default": 5}}}}},
    {"type": "function", "function": {"name": "triage_batch", "description": "Lade die naechsten INBOX-Mails fuer einen Triage-Durchgang. Pro Turn maximal 10 Mails.", "parameters": {"type": "object", "properties": {"limit": {"type": "integer", "description": "Maximale Anzahl Mails fuer diesen Durchgang", "default": 10}, "unread_only": {"type": "boolean", "description": "Nur ungelesene Mails beruecksichtigen", "default": False}}}}},
    {"type": "function", "function": {"name": "summarize_inbox", "description": "Gib einen kompakten Ueberblick ueber die aktuellen oder neuesten Emails", "parameters": {"type": "object", "properties": {"limit": {"type": "integer", "description": "Maximale Anzahl Emails fuer den Ueberblick", "default": 5}, "unread_only": {"type": "boolean", "description": "Nur ungelesene Emails beruecksichtigen", "default": False}, "refresh": {"type": "boolean", "description": "Wenn true, die Liste vorher live neu laden", "default": False}}}}},
    {"type": "function", "function": {"name": "read_email", "description": "Zeige eine Zusammenfassung einer bestimmten Email", "parameters": {"type": "object", "properties": {"email_index": {"type": "integer", "description": "Nummer der Email in der aktuellen Liste (1-basiert)"}}, "required": ["email_index"]}}},
    {"type": "function", "function": {"name": "read_email_full", "description": "Lies den kompletten Body einer Email vor", "parameters": {"type": "object", "properties": {"email_index": {"type": "integer", "description": "Nummer der Email in der aktuellen Liste (1-basiert)"}}, "required": ["email_index"]}}},
    {"type": "function", "function": {"name": "read_thread", "description": "Lies die wichtigsten Nachrichten eines Email-Threads zusammengefasst vor", "parameters": {"type": "object", "properties": {"email_index": {"type": "integer", "description": "Nummer der Email in der aktuellen Liste (1-basiert)"}, "limit": {"type": "integer", "description": "Maximale Anzahl Thread-Nachrichten", "default": 10}}, "required": ["email_index"]}}},
    {"type": "function", "function": {"name": "list_attachments", "description": "Liste die Anhaenge einer bestimmten Email auf", "parameters": {"type": "object", "properties": {"email_index": {"type": "integer", "description": "Nummer der Email in der aktuellen Liste (1-basiert)"}}, "required": ["email_index"]}}},
    {"type": "function", "function": {"name": "delete_email", "description": "Bereite das Loeschen einer Email vor. Ohne email_index gilt die aktuell geoeffnete Email. Gibt eine Bestaetigung zurueck die der User bestaetigen muss.", "parameters": {"type": "object", "properties": {"email_index": {"type": "integer", "description": "Optional: Nummer der Email. Ohne Angabe wird die aktuelle Email verwendet."}, "confirmed": {"type": "boolean", "description": "true wenn der User bereits bestaetigt hat", "default": False}}}}},
    {"type": "function", "function": {"name": "move_to_status", "description": "Verschiebe eine Email in einen der Assistant-Status TODO, WARTEN, TEMP oder ARCHIV. Ohne email_index gilt die aktuell geoeffnete Email. TEMP erfordert immer expires_in_days.", "parameters": {"type": "object", "properties": {"email_index": {"type": "integer", "description": "Optional: Nummer der Email. Ohne Angabe wird die aktuelle Email verwendet."}, "status": {"type": "string", "enum": ["TODO", "WARTEN", "TEMP", "ARCHIV"], "description": "Assistant-Zielstatus"}, "expires_in_days": {"type": "integer", "description": "Pflicht fuer TEMP: Aufbewahrungsdauer in Tagen ab jetzt. Z.B. 5 fuer 5 Tage."}, "confirmed": {"type": "boolean", "description": "true wenn der User bereits bestaetigt hat", "default": False}}, "required": ["status"]}}},
    {"type": "function", "function": {"name": "set_temp_expiry", "description": "Setze oder aktualisiere das Verfallsdatum einer Email im TEMP-Kontext. Ohne email_index gilt die aktuell geoeffnete Email.", "parameters": {"type": "object", "properties": {"email_index": {"type": "integer", "description": "Optional: Nummer der Email. Ohne Angabe wird die aktuelle Email verwendet."}, "expires_in_days": {"type": "integer", "description": "Aufbewahrungsdauer in Tagen ab jetzt. Z.B. 5 fuer 5 Tage."}}, "required": ["expires_in_days"]}}},
    {"type": "function", "function": {"name": "review_expired_temp", "description": "Liste abgelaufene, noch nicht aufgeloeste TEMP-Mails auf", "parameters": {"type": "object", "properties": {"mailbox": {"type": "string", "description": "Optionales Postfach"}, "limit": {"type": "integer", "description": "Maximale Anzahl Eintraege", "default": 10}}}}},
    {"type": "function", "function": {"name": "review_waiting", "description": "Liste aeltere WARTEN-Mails auf, bei denen ein Review oder Follow-up sinnvoll ist", "parameters": {"type": "object", "properties": {"mailbox": {"type": "string", "description": "Optionales Postfach"}, "older_than_days": {"type": "integer", "description": "Schwellenwert in Tagen", "default": 5}, "limit": {"type": "integer", "description": "Maximale Anzahl Eintraege", "default": 10}}}}},
    {"type": "function", "function": {"name": "review_stale_todos", "description": "Liste aeltere TODO-Mails auf, die neu priorisiert werden sollten", "parameters": {"type": "object", "properties": {"mailbox": {"type": "string", "description": "Optionales Postfach"}, "older_than_days": {"type": "integer", "description": "Schwellenwert in Tagen", "default": 7}, "limit": {"type": "integer", "description": "Maximale Anzahl Eintraege", "default": 10}}}}},
    {"type": "function", "function": {"name": "move_email", "description": "Bereite das Verschieben einer Email vor. Ohne email_index gilt die aktuell geoeffnete Email. Erfordert User-Bestaetigung.", "parameters": {"type": "object", "properties": {"email_index": {"type": "integer", "description": "Optional: Nummer der Email. Ohne Angabe wird die aktuelle Email verwendet."}, "folder": {"type": "string", "description": "Zielordner (z.B. 'Archive', 'Junk Email')"}, "confirmed": {"type": "boolean", "description": "true wenn der User bereits bestaetigt hat", "default": False}}, "required": ["folder"]}}},
    {"type": "function", "function": {"name": "reply_to_email", "description": "Erstelle einen Antwort-Entwurf. Ohne email_index gilt die aktuell geoeffnete Email. Wird NICHT sofort gesendet. User muss erst mit confirm_and_send bestaetigen.", "parameters": {"type": "object", "properties": {"email_index": {"type": "integer", "description": "Optional: Nummer der Email. Ohne Angabe wird die aktuelle Email verwendet."}, "reply_text": {"type": "string", "description": "Der Antworttext"}}, "required": ["reply_text"]}}},
    {"type": "function", "function": {"name": "forward_email", "description": "Leite die aktuelle Email an eine andere Adresse weiter (mit allen Anhaengen). Fragt ob kommentarlos oder mit Kommentar.", "parameters": {"type": "object", "properties": {"email_index": {"type": "integer", "description": "Optional: Nummer der Email."}, "to": {"type": "string", "description": "Empfaenger-Adresse fuer die Weiterleitung"}, "comment": {"type": "string", "description": "Optionaler Kommentar zur Weiterleitung. Leer lassen fuer kommentarlose Weiterleitung."}, "confirmed": {"type": "boolean", "description": "true wenn der User bereits bestaetigt hat", "default": False}}, "required": ["to"]}}},
    {"type": "function", "function": {"name": "compose_email", "description": "Erstelle einen neuen Email-Entwurf. Wird NICHT sofort gesendet. User muss erst mit confirm_and_send bestaetigen.", "parameters": {"type": "object", "properties": {"to": {"type": "string", "description": "Empfaenger-Adresse"}, "subject": {"type": "string", "description": "Betreff der neuen Email"}, "body": {"type": "string", "description": "Text der neuen Email"}}, "required": ["to", "subject", "body"]}}},
    {"type": "function", "function": {"name": "preview_draft", "description": "Lies den aktuell offenen Antwort- oder Mail-Entwurf vor", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "revise_draft", "description": "Passe den aktuellen Entwurf an, ohne ihn zu senden", "parameters": {"type": "object", "properties": {"body": {"type": "string", "description": "Neuer Entwurfstext"}, "subject": {"type": "string", "description": "Optional neuer Betreff"}}, "required": ["body"]}}},
    {"type": "function", "function": {"name": "discard_draft", "description": "Verwirf den aktuell offenen Entwurf", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "confirm_and_send", "description": "Bestaetige und sende den zuletzt erstellten Entwurf. Nur mit confirmed=true ausfuehren wenn der User explizit bestaetigt hat.", "parameters": {"type": "object", "properties": {"confirmed": {"type": "boolean", "description": "true wenn der User den Entwurf wirklich senden will", "default": False}}}}},
    {"type": "function", "function": {"name": "send_email", "description": "Kompatibilitaetsalias fuer compose_email. Erstellt einen neuen Entwurf und sendet NICHT sofort.", "parameters": {"type": "object", "properties": {"to": {"type": "string", "description": "Empfaenger Email-Adresse"}, "subject": {"type": "string", "description": "Betreff"}, "body": {"type": "string", "description": "Email-Text"}}, "required": ["to", "subject", "body"]}}},
    {"type": "function", "function": {"name": "list_folders", "description": "Liste alle verfuegbaren Mailordner auf", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "next_email", "description": "Gehe zur naechsten Email in der Liste", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "previous_email", "description": "Gehe zur vorherigen Email in der Liste", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "create_rule", "description": "Erstelle eine automatische Regel fuer zukuenftige Emails", "parameters": {"type": "object", "properties": {"name": {"type": "string", "description": "Name der Regel"}, "sender_contains": {"type": "string", "description": "Absender-Muster (z.B. 'newsletter.com', 'chef@firma.de')"}, "subject_contains": {"type": "string", "description": "Betreff-Muster (optional)"}, "action": {"type": "string", "description": "Aktion: 'delete', 'move', 'label', 'mute'"}, "action_target": {"type": "string", "description": "Zielordner oder Label-Name (optional)"}}, "required": ["name", "action"]}}},
    {"type": "function", "function": {"name": "read_autopilot_report", "description": "Lies den aktuellen Autopilot-Bericht vor (was wurde automatisch bereinigt)", "parameters": {"type": "object", "properties": {}}}},
]
