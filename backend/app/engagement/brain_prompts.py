"""LLM Prompts for the Engagement Brain."""

# System prompt for pipeline setup chat
PIPELINE_SETUP_SYSTEM = """Du bist der Pipeline-Setup-Assistent von go4-automate.

Deine Aufgabe ist es, durch einen Dialog alle Informationen zu sammeln, die für
eine effektive Multi-Channel-Engagement-Pipeline benötigt werden.

## Informationen die du sammeln musst:

1. **Produkt/Service**: Was wird beworben oder verkauft?
2. **Zielgruppe**: Wer soll angesprochen werden? (Branche, Unternehmensgröße, Position)
3. **Kanäle**: Welche Kanäle sollen genutzt werden? (LinkedIn, Email, Telefon, WhatsApp, Post)
4. **Ziel**: Was ist das Konversionsziel? (Termin, Demo, Angebot, Verkauf)
5. **Tonalität**: Wie soll kommuniziert werden? (professionell, locker, technisch, persönlich)
6. **Besonderheiten**: Gibt es spezielle Anforderungen?

## Verhaltensregeln:

- Stelle EINE Frage nach der anderen
- Fasse wichtige Punkte kurz zusammen bevor du zur nächsten Frage gehst
- Sei freundlich und professionell
- Wenn alle Informationen gesammelt sind, gib eine Zusammenfassung und frage nach Bestätigung
- Bei Bestätigung: Antworte mit [PIPELINE_READY] gefolgt von einem JSON-Objekt

## JSON-Format bei Abschluss:

[PIPELINE_READY]
```json
{
    "name": "Pipeline Name",
    "slug": "pipeline-slug",
    "product_name": "Produktname",
    "product_description": "Ausführliche Beschreibung",
    "target_audience": "Zielgruppen-Beschreibung",
    "channels": ["linkedin", "email"],
    "goal": "vor_ort_termin",
    "tone_of_voice": "professionell",
    "playbook_notes": "Besondere Hinweise für das Playbook"
}
```

Beginne mit einer freundlichen Begrüßung und der ersten Frage nach dem Produkt/Service.
"""

# Template for generating playbook
PLAYBOOK_GENERATION_PROMPT = """Erstelle ein Playbook für eine Engagement-Pipeline.

## Pipeline-Konfiguration:
- **Name**: {name}
- **Produkt**: {product_name}
- **Beschreibung**: {product_description}
- **Zielgruppe**: {target_audience}
- **Kanäle**: {channels}
- **Ziel**: {goal}
- **Tonalität**: {tone_of_voice}
- **Besondere Hinweise**: {playbook_notes}

## Erstelle ein Playbook mit folgender Struktur:

1. **Überblick**: Kurze Zusammenfassung der Pipeline-Strategie
2. **Timing-Richtlinien**: Wann welchen Kanal nutzen, Abstände zwischen Kontakten
3. **Eskalationspfad**: Wenn keine Reaktion, was ist der nächste Schritt?
4. **Reaktionsregeln**: Wie bei positiver/negativer Antwort reagieren
5. **Qualifizierungskriterien**: Wann ist ein Lead qualifiziert?
6. **Red Flags**: Wann soll die Pipeline gestoppt werden?
7. **Erfolgsmetriken**: Was definiert Erfolg?

Schreibe das Playbook in deutscher Sprache, klar und prägnant.
"""

# Template for generating module-specific prompts
MODULE_PROMPT_GENERATION = """Erstelle einen LLM-Prompt für das {module}-Modul.

## Pipeline-Kontext:
- **Produkt**: {product_name}
- **Beschreibung**: {product_description}
- **Zielgruppe**: {target_audience}
- **Ziel**: {goal}
- **Tonalität**: {tone_of_voice}

## Spezifische Anforderungen für {module}:
{module_requirements}

## Der generierte Prompt soll:
- Dem {module}-Modul erklären, wie es personalisierte Nachrichten erstellt
- Die Tonalität und Zielgruppe berücksichtigen
- Konkrete Beispiele oder Templates enthalten
- Maximallängen und Formatierungsregeln beachten

Generiere den Prompt auf Deutsch.
"""

# Module-specific requirements
MODULE_REQUIREMENTS = {
    "linkedin": """
- Nachrichten müssen unter 300 Zeichen sein (LinkedIn Limit)
- Personalisierung basierend auf Profil-Informationen
- Keine Verkaufs-Pitches in der ersten Nachricht
- Professioneller aber persönlicher Ton
- Call-to-Action am Ende
""",
    "email": """
- Betreffzeile: Max 60 Zeichen, Neugier wecken
- Body: Kurz und prägnant, max 150 Wörter
- Personalisierung mit Namen und Unternehmen
- Klarer Call-to-Action
- Mobile-optimiert
""",
    "phone": """
- Gesprächsleitfaden für Kaltakquise
- Eröffnung: Wer anruft und warum
- Elevator Pitch: 30 Sekunden max
- Qualifizierungsfragen
- Umgang mit Einwänden
- Terminvereinbarung
""",
    "whatsapp": """
- Kurze, informelle Nachrichten
- Max 160 Zeichen für erste Nachricht
- Emojis sparsam einsetzen
- Schnelle Antwort-Templates
- Opt-in beachten
""",
    "letter": """
- Anschreiben für physischen Versand (DIN A4, Letterxpress)
- Formelle Anrede ("Sehr geehrte Frau …", "Sehr geehrter Herr …")
- 250-350 Wörter: Anlass → Problem → Lösung → Nutzen → CTA
- Konkretes Personalisierungs-Element aus den Lead-Insights nutzen
  (Branche, Standort, Hook), nicht nur generische Argumente
- Briefkopf/Adresse nicht selbst rendern — kommt vom Briefpapier-Template
- Tracking via Ref-Code-URL erwähnen (kein QR-Code im V1)
- Mit "Mit freundlichen Grüßen" + Name + Position abschließen
- KEIN Datum, KEIN Adressblock, KEIN Briefkopf — nur den Body-Text liefern
""",
}

# Prompt for contact analysis (next step decision).
# All "## Insights"-Felder sind optional — wenn der Kontakt aus dem
# Leadgen kommt, ist da der Reichtum an LLM-aufbereiteten Daten drin
# (personalization_hook, services, customer_segments, …). Wenn der
# Kontakt aus einem anderen Kanal kommt (CSV-Import, manuell), bleibt
# der Block einfach leer und der Brain entscheidet auf Basis der
# Pipeline + Aktivitätenhistorie wie zuvor.
CONTACT_ANALYSIS_PROMPT = """Analysiere den Kontakt und empfehle den nächsten Schritt.

## Pipeline:
- **Name**: {pipeline_name}
- **Produkt**: {product_name}
- **Ziel**: {goal}
- **Verfügbare Kanäle**: {channels}
- **Playbook**: {playbook}

## Kontakt:
- **Name**: {contact_name}
- **Position**: {contact_position}
- **Unternehmen**: {contact_company}
- **Stage**: {current_stage}
- **Touch-Count**: {touch_count}
- **Letzte Interaktion**: {last_touch}
- **Letzte Antwort**: {last_response}

## Insights (optional, aus Leadgen):
- **Personalisierungs-Hook**: {personalization_hook}
- **Services / Produkte**: {services}
- **Marken / Hersteller**: {brands}
- **Kundengruppen**: {customer_segments}
- **Unternehmensgröße**: {company_size_indicator}
- **Match-Score (0-10)**: {target_match_score}
- **Branche (Google)**: {google_categories}
- **Red Flags**: {red_flags}

## Bisherige Aktivitäten:
{activities}

## Entscheide:
1. Welcher Kanal soll als nächstes genutzt werden?
2. Welche Art von Aktion? (z.B. connection_request, message, call, email)
3. Was ist der empfohlene Inhalt/Ansatz? (Nutze die Insights für echte
   Personalisierung — kein generisches Template-Geblubber.)
4. Soll die Stage geändert werden?
5. Benötigt diese Aktion eine Freigabe?

Antworte im JSON-Format:
```json
{
    "channel": "linkedin|email|phone|whatsapp|letter",
    "action": "action_type",
    "content_suggestion": "Vorgeschlagener Inhalt oder Gesprächseinstieg",
    "new_stage": "neue_stage oder null",
    "needs_approval": true|false,
    "reasoning": "Kurze Begründung"
}
```
"""

# Prompt for response analysis
RESPONSE_ANALYSIS_PROMPT = """Analysiere die eingehende Antwort eines Kontakts.

## Kontext:
- **Pipeline**: {pipeline_name}
- **Kontakt**: {contact_name} ({contact_position} bei {contact_company})
- **Bisherige Stage**: {current_stage}
- **Kanal**: {channel}

## Letzte ausgehende Nachricht:
{last_outbound}

## Eingehende Antwort:
{incoming_message}

## Analysiere:
1. **Sentiment**: Ist die Antwort positiv, neutral oder negativ?
2. **Intent**: Was will der Kontakt? (interessiert, Frage, Einwand, Absage, Weiterleitung)
3. **Dringlichkeit**: Wie schnell sollte reagiert werden?
4. **Stage-Änderung**: Sollte die Pipeline-Stage geändert werden?
5. **Empfohlene Reaktion**: Was sollte als nächstes passieren?

Antworte im JSON-Format:
```json
{
    "sentiment": "positive|neutral|negative",
    "intent": "interested|question|objection|not_interested|referral|meeting_request|other",
    "urgency": "immediate|same_day|next_day|normal",
    "new_stage": "engaged|qualified|converted|lost|null",
    "recommended_action": "Beschreibung der empfohlenen Reaktion",
    "draft_response": "Optionaler Antwort-Entwurf",
    "needs_human": true|false,
    "reasoning": "Kurze Begründung der Analyse"
}
```
"""
