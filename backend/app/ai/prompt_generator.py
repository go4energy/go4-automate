"""
Prompt Generator - Generiert produktive Prompts basierend auf Onboarding-Variablen.
"""

from typing import Any

from loguru import logger

from app.services.llm import LLMService

# LinkedIn Prompt Meta-Templates
LINKEDIN_PROMPT_TEMPLATES = {
    "connection_request": {
        "slug": "connection_request",
        "name": "Kontaktanfrage",
        "type": "connection_note",
        "max_chars": 300,
        "instructions": """Erstelle eine LinkedIn Kontaktanfrage-Note (MAXIMAL 300 Zeichen!).

KONTEXT:
- Unternehmen: {company_name}
- Branche: {industry}
- Produkt/Service: {product_service}
- Absender: {sender_name}, {sender_position}
- Tonalität: {tone}
- Zielgruppe: {target_positions}

REGELN:
- Persönlich, nicht generisch
- KEIN Sales-Pitch, keine Produktwerbung
- Bezug zu {{{{first_name}}}} oder {{{{company}}}} oder {{{{position}}}}
- Grund für Vernetzung andeuten (gemeinsame Branche, Interesse)
- MAXIMAL 300 Zeichen inklusive Leerzeichen!
- Keine Emojis

VERFÜGBARE VARIABLEN (mit doppelten geschweiften Klammern):
{{{{first_name}}}}, {{{{last_name}}}}, {{{{company}}}}, {{{{position}}}}, {{{{industry}}}}

OUTPUT: NUR der fertige Text, keine Erklärung, kein Markdown.""",
    },
    "first_message": {
        "slug": "first_message",
        "name": "Erste Nachricht",
        "type": "message",
        "instructions": """Erstelle die erste Nachricht nach einer LinkedIn-Vernetzung.

KONTEXT:
- Unternehmen: {company_name}
- Produkt/Service: {product_service}
- Kundennutzen: {customer_benefit}
- USP: {usp}
- Pain Points der Zielgruppe: {pain_points}
- Absender: {sender_name}, {sender_position}
- Tonalität: {tone}
- Call-to-Action Typ: {cta_type}
- Call-to-Action Text: {cta_text}

STRUKTUR:
1. Kurzer Dank für Vernetzung (1 Satz)
2. Relevanter Hook - Bezug zu Position/Branche des Empfängers
3. Problem ansprechen (ein pain point, nicht alle)
4. Lösung kurz andeuten (NICHT verkaufen!)
5. Weicher CTA als offene Frage

REGELN:
- Maximal 800 Zeichen
- Natürlich und persönlich klingen
- Keine Bullet-Points oder Listen
- Keine Emojis
- Nicht aufdringlich

VERFÜGBARE VARIABLEN:
{{{{first_name}}}}, {{{{last_name}}}}, {{{{company}}}}, {{{{position}}}}, {{{{industry}}}}, {{{{headline}}}}

OUTPUT: NUR der fertige Text.""",
    },
    "follow_up_1": {
        "slug": "follow_up_1",
        "name": "Follow-up 1",
        "type": "follow_up",
        "instructions": """Erstelle einen ersten Follow-up (wird 5-7 Tage nach erster Nachricht ohne Antwort gesendet).

KONTEXT:
- Unternehmen: {company_name}
- USP: {usp}
- Pain Points: {pain_points}
- Kundennutzen: {customer_benefit}
- Absender: {sender_name}
- Tonalität: {tone}
- CTA: {cta_text}

STRUKTUR:
1. Kurze, freundliche Erinnerung an vorherige Nachricht
2. NEUEN Aspekt oder Mehrwert bringen (anderen Pain Point oder andere Perspektive)
3. Direkter aber nicht drängender CTA

REGELN:
- Maximal 500 Zeichen
- Nicht vorwurfsvoll ("du hast nicht geantwortet")
- Neuen Mehrwert bieten, nicht wiederholen
- Keine Emojis

VERFÜGBARE VARIABLEN:
{{{{first_name}}}}, {{{{company}}}}, {{{{position}}}}

OUTPUT: NUR der fertige Text.""",
    },
    "follow_up_2": {
        "slug": "follow_up_2",
        "name": "Follow-up 2 (Letzter)",
        "type": "follow_up",
        "instructions": """Erstelle einen letzten, respektvollen Follow-up (wird 7-10 Tage nach Follow-up 1 gesendet).

KONTEXT:
- Unternehmen: {company_name}
- Kernnutzen: {customer_benefit}
- Absender: {sender_name}
- Tonalität: {tone}

STRUKTUR:
1. Anerkennen dass jetzt vielleicht nicht der richtige Zeitpunkt ist
2. Ein Satz zum Kernnutzen
3. Tür offen lassen für später

REGELN:
- Maximal 300 Zeichen
- Respektvoll, keine Schuldzuweisung
- Kein Druck
- Zeigt Verständnis
- Keine Emojis

VERFÜGBARE VARIABLEN:
{{{{first_name}}}}

OUTPUT: NUR der fertige Text.""",
    },
    "congratulation_job": {
        "slug": "congratulation_job",
        "name": "Gratulation Jobwechsel",
        "type": "message",
        "instructions": """Erstelle eine authentische Gratulation für einen Jobwechsel.

KONTEXT:
- Absender: {sender_name}
- Tonalität: {tone}

STRUKTUR:
1. Herzliche Gratulation
2. Kurzer positiver Kommentar zur neuen Position/Firma
3. Erfolg wünschen

REGELN:
- Maximal 200 Zeichen
- Authentisch und kurz
- KEIN Sales-Pitch, keine Produkterwähnung!
- Echte Freude ausdrücken
- Keine Emojis

VERFÜGBARE VARIABLEN:
{{{{first_name}}}}, {{{{company}}}}, {{{{position}}}}

OUTPUT: NUR der fertige Text.""",
    },
    "congratulation_promotion": {
        "slug": "congratulation_promotion",
        "name": "Gratulation Beförderung",
        "type": "message",
        "instructions": """Erstelle eine authentische Gratulation für eine Beförderung.

KONTEXT:
- Absender: {sender_name}
- Tonalität: {tone}

STRUKTUR:
1. Gratulation zur Beförderung
2. Anerkennung der Leistung
3. Erfolg wünschen

REGELN:
- Maximal 200 Zeichen
- Authentisch
- KEIN Sales-Pitch!
- Keine Emojis

VERFÜGBARE VARIABLEN:
{{{{first_name}}}}, {{{{position}}}}

OUTPUT: NUR der fertige Text.""",
    },
    # ============================================================
    # EVENT-BASIERTE NACHRICHTEN
    # ============================================================
    "congratulation_anniversary": {
        "slug": "congratulation_anniversary",
        "name": "Gratulation Firmenjubiläum",
        "type": "message",
        "instructions": """Erstelle eine Gratulation zum Firmenjubiläum.

KONTEXT:
- Absender: {sender_name}
- Tonalität: {tone}

STRUKTUR:
1. Gratulation zum Jubiläum
2. Anerkennung der Treue/des Engagements
3. Weiterhin viel Erfolg wünschen

REGELN:
- Maximal 200 Zeichen
- Authentisch und warm
- KEIN Sales-Pitch!
- Keine Emojis

VERFÜGBARE VARIABLEN:
{{{{first_name}}}}, {{{{company}}}}, {{{{years}}}} (Anzahl Jahre)

OUTPUT: NUR der fertige Text.""",
    },
    "congratulation_birthday": {
        "slug": "congratulation_birthday",
        "name": "Gratulation Geburtstag",
        "type": "message",
        "instructions": """Erstelle eine kurze, professionelle Geburtstagsgrüße.

KONTEXT:
- Absender: {sender_name}
- Tonalität: {tone}

REGELN:
- Maximal 100 Zeichen
- Kurz und herzlich
- Professionell bleiben
- KEIN Sales-Pitch!
- Keine Emojis

VERFÜGBARE VARIABLEN:
{{{{first_name}}}}

OUTPUT: NUR der fertige Text.""",
    },
    "comment_on_post": {
        "slug": "comment_on_post",
        "name": "Kommentar auf Beitrag",
        "type": "comment",
        "instructions": """Erstelle einen authentischen Kommentar auf einen LinkedIn-Beitrag.

KONTEXT:
- Absender: {sender_name}
- Tonalität: {tone}
- Branche des Absenders: {industry}

STRUKTUR:
1. Bezug zum Inhalt des Beitrags nehmen
2. Eigene Perspektive/Erfahrung kurz einbringen
3. Optional: Weiterführende Frage stellen

REGELN:
- Maximal 300 Zeichen
- Authentisch und inhaltlich relevant
- Mehrwert für die Diskussion bieten
- KEIN Sales-Pitch oder Eigenwerbung!
- Keine generischen Kommentare ("Toller Beitrag!")
- Keine Emojis

VERFÜGBARE VARIABLEN:
{{{{first_name}}}}, {{{{post_topic}}}} (Thema des Beitrags), {{{{post_snippet}}}} (Auszug)

OUTPUT: NUR der fertige Kommentar-Text.""",
    },
    "endorsement_thanks": {
        "slug": "endorsement_thanks",
        "name": "Danke für Skill-Bestätigung",
        "type": "message",
        "instructions": """Erstelle eine kurze Dankes-Nachricht für eine Skill-Bestätigung auf LinkedIn.

KONTEXT:
- Absender: {sender_name}
- Tonalität: {tone}

STRUKTUR:
1. Kurzer Dank für die Bestätigung
2. Freude über die Vernetzung ausdrücken

REGELN:
- Maximal 150 Zeichen
- Authentisch und kurz
- KEIN Sales-Pitch!
- Keine Emojis

VERFÜGBARE VARIABLEN:
{{{{first_name}}}}, {{{{skill}}}} (der bestätigte Skill)

OUTPUT: NUR der fertige Text.""",
    },
    # ============================================================
    # RE-ENGAGEMENT
    # ============================================================
    "reactivation": {
        "slug": "reactivation",
        "name": "Reaktivierung kalter Kontakt",
        "type": "message",
        "instructions": """Erstelle eine Nachricht zur Reaktivierung eines Kontakts, mit dem lange kein Austausch war.

KONTEXT:
- Unternehmen: {company_name}
- USP: {usp}
- Absender: {sender_name}
- Tonalität: {tone}
- Kundennutzen: {customer_benefit}

STRUKTUR:
1. Bezug auf frühere Vernetzung/Kontakt
2. Aktuellen Anlass oder News als Aufhänger
3. Neuen Mehrwert bieten
4. Leichte Frage oder Einladung zum Austausch

REGELN:
- Maximal 500 Zeichen
- Nicht aufdringlich
- Echten Mehrwert bieten
- Keine Emojis

VERFÜGBARE VARIABLEN:
{{{{first_name}}}}, {{{{company}}}}, {{{{position}}}}, {{{{last_contact}}}} (wann letzter Kontakt)

OUTPUT: NUR der fertige Text.""",
    },
    "check_in": {
        "slug": "check_in",
        "name": "Check-in Nachricht",
        "type": "message",
        "instructions": """Erstelle eine freundliche Check-in Nachricht nach längerer Zeit ohne Kontakt.

KONTEXT:
- Absender: {sender_name}
- Tonalität: {tone}
- Branche: {industry}

STRUKTUR:
1. Freundliche Begrüßung mit Bezug auf frühere Verbindung
2. Interesse an aktuellen Entwicklungen zeigen
3. Offene Frage stellen

REGELN:
- Maximal 300 Zeichen
- Authentisch und interessiert
- KEIN Sales-Pitch!
- Keine Emojis

VERFÜGBARE VARIABLEN:
{{{{first_name}}}}, {{{{company}}}}, {{{{position}}}}

OUTPUT: NUR der fertige Text.""",
    },
    # ============================================================
    # CONTENT & EVENTS
    # ============================================================
    "share_content": {
        "slug": "share_content",
        "name": "Content teilen",
        "type": "message",
        "instructions": """Erstelle eine Nachricht, um relevanten Content mit einem Kontakt zu teilen.

KONTEXT:
- Unternehmen: {company_name}
- Absender: {sender_name}
- Tonalität: {tone}
- Zielgruppe Pain Points: {pain_points}

STRUKTUR:
1. Kurze persönliche Einleitung
2. Warum dieser Content für den Empfänger relevant ist
3. Kurze Beschreibung des Contents
4. Einladung zur Diskussion

REGELN:
- Maximal 400 Zeichen
- Mehrwert-orientiert, nicht werblich
- Content muss zum Empfänger passen
- Keine Emojis

VERFÜGBARE VARIABLEN:
{{{{first_name}}}}, {{{{position}}}}, {{{{content_title}}}}, {{{{content_type}}}} (Artikel, Video, Whitepaper), {{{{content_url}}}}

OUTPUT: NUR der fertige Text.""",
    },
    "invite_to_event": {
        "slug": "invite_to_event",
        "name": "Event-Einladung",
        "type": "message",
        "instructions": """Erstelle eine persönliche Einladung zu einem Event (Webinar, Workshop, Konferenz).

KONTEXT:
- Unternehmen: {company_name}
- Absender: {sender_name}
- Tonalität: {tone}
- Zielgruppe: {target_positions}
- Pain Points: {pain_points}

STRUKTUR:
1. Persönliche Ansprache
2. Kurze Beschreibung des Events und warum es relevant ist
3. Key-Takeaways oder Speaker erwähnen
4. Klarer CTA zur Anmeldung

REGELN:
- Maximal 500 Zeichen
- Fokus auf Mehrwert für den Empfänger
- Keine generische Masseneinladung
- Keine Emojis

VERFÜGBARE VARIABLEN:
{{{{first_name}}}}, {{{{position}}}}, {{{{event_name}}}}, {{{{event_date}}}}, {{{{event_type}}}} (Webinar, Workshop), {{{{event_url}}}}

OUTPUT: NUR der fertige Text.""",
    },
    # ============================================================
    # MEETING-FLOW
    # ============================================================
    "meeting_request": {
        "slug": "meeting_request",
        "name": "Terminanfrage",
        "type": "message",
        "instructions": """Erstelle eine Anfrage für ein Meeting/Call.

KONTEXT:
- Unternehmen: {company_name}
- USP: {usp}
- Absender: {sender_name}, {sender_position}
- Tonalität: {tone}
- CTA: {cta_type}

STRUKTUR:
1. Bezug auf vorherige Kommunikation/Interesse
2. Konkreter Vorschlag was besprochen werden soll
3. Mehrere Terminoptionen anbieten oder Calendly-Link
4. Dauer angeben (15-30 Min)

REGELN:
- Maximal 400 Zeichen
- Konkret und respektvoll
- Nicht aufdringlich
- Keine Emojis

VERFÜGBARE VARIABLEN:
{{{{first_name}}}}, {{{{company}}}}, {{{{calendly_link}}}} (optional)

OUTPUT: NUR der fertige Text.""",
    },
    "meeting_confirmation": {
        "slug": "meeting_confirmation",
        "name": "Terminbestätigung",
        "type": "message",
        "instructions": """Erstelle eine Bestätigung für ein vereinbartes Meeting.

KONTEXT:
- Absender: {sender_name}
- Tonalität: {tone}

STRUKTUR:
1. Freude über den Termin ausdrücken
2. Datum/Uhrzeit bestätigen
3. Kurz erwähnen was besprochen wird
4. Link zum Meeting teilen

REGELN:
- Maximal 250 Zeichen
- Professionell und freundlich
- Alle wichtigen Infos enthalten
- Keine Emojis

VERFÜGBARE VARIABLEN:
{{{{first_name}}}}, {{{{meeting_date}}}}, {{{{meeting_time}}}}, {{{{meeting_link}}}}, {{{{meeting_topic}}}}

OUTPUT: NUR der fertige Text.""",
    },
    "meeting_reminder": {
        "slug": "meeting_reminder",
        "name": "Terminerinnerung",
        "type": "message",
        "instructions": """Erstelle eine freundliche Erinnerung an ein bevorstehendes Meeting.

KONTEXT:
- Absender: {sender_name}
- Tonalität: {tone}

STRUKTUR:
1. Freundliche Erinnerung
2. Datum/Uhrzeit
3. Link zum Meeting
4. Vorfreude ausdrücken

REGELN:
- Maximal 200 Zeichen
- Freundlich, nicht aufdringlich
- Alle wichtigen Infos
- Keine Emojis

VERFÜGBARE VARIABLEN:
{{{{first_name}}}}, {{{{meeting_date}}}}, {{{{meeting_time}}}}, {{{{meeting_link}}}}

OUTPUT: NUR der fertige Text.""",
    },
    "no_show_follow_up": {
        "slug": "no_show_follow_up",
        "name": "No-Show Follow-up",
        "type": "message",
        "instructions": """Erstelle eine Nachricht falls jemand nicht zum vereinbarten Termin erschienen ist.

KONTEXT:
- Absender: {sender_name}
- Tonalität: {tone}

STRUKTUR:
1. Verständnis zeigen (wahrscheinlich etwas dazwischengekommen)
2. Neuen Termin anbieten
3. Tür offen halten

REGELN:
- Maximal 250 Zeichen
- KEINE Vorwürfe oder passive Aggressivität
- Verständnisvoll und professionell
- Keine Emojis

VERFÜGBARE VARIABLEN:
{{{{first_name}}}}, {{{{original_date}}}}, {{{{calendly_link}}}} (optional)

OUTPUT: NUR der fertige Text.""",
    },
    "post_meeting": {
        "slug": "post_meeting",
        "name": "Nach dem Meeting",
        "type": "message",
        "instructions": """Erstelle eine Follow-up Nachricht nach einem Meeting.

KONTEXT:
- Unternehmen: {company_name}
- Absender: {sender_name}
- Tonalität: {tone}
- CTA: {cta_text}

STRUKTUR:
1. Dank für das Gespräch
2. Zusammenfassung der wichtigsten Punkte/nächsten Schritte
3. Angebot weiterer Unterstützung
4. Konkreter nächster Schritt

REGELN:
- Maximal 400 Zeichen
- Professionell und verbindlich
- Klare Action Items
- Keine Emojis

VERFÜGBARE VARIABLEN:
{{{{first_name}}}}, {{{{meeting_topic}}}}, {{{{next_steps}}}}, {{{{attachments}}}} (falls Dokumente geteilt)

OUTPUT: NUR der fertige Text.""",
    },
    # ============================================================
    # REFERRALS & INTRODUCTIONS
    # ============================================================
    "referral_request": {
        "slug": "referral_request",
        "name": "Empfehlungs-Anfrage",
        "type": "message",
        "instructions": """Erstelle eine Anfrage um eine Empfehlung/Weiterleitung.

KONTEXT:
- Unternehmen: {company_name}
- USP: {usp}
- Absender: {sender_name}
- Tonalität: {tone}
- Zielgruppe: {target_positions}

STRUKTUR:
1. Wertschätzung für die bisherige Beziehung
2. Erklärung wen du suchst
3. Warum du fragst (Vertrauen, gute Erfahrung)
4. Klare, einfache Bitte

REGELN:
- Maximal 400 Zeichen
- Nicht fordernd
- Einfach zu erfüllen machen
- Keine Emojis

VERFÜGBARE VARIABLEN:
{{{{first_name}}}}, {{{{company}}}}, {{{{target_profile}}}} (wen du suchst)

OUTPUT: NUR der fertige Text.""",
    },
    "introduction_request": {
        "slug": "introduction_request",
        "name": "Vorstellungs-Anfrage",
        "type": "message",
        "instructions": """Erstelle eine Anfrage um eine Vorstellung zu einer bestimmten Person.

KONTEXT:
- Unternehmen: {company_name}
- USP: {usp}
- Absender: {sender_name}
- Tonalität: {tone}

STRUKTUR:
1. Bezug auf gemeinsame Verbindung
2. Warum du vorgestellt werden möchtest
3. Was du der Zielperson bieten kannst
4. Einfache Bitte (optional: fertigen Text zum Weiterleiten)

REGELN:
- Maximal 450 Zeichen
- Respektvoll
- Mehrwert für alle Seiten zeigen
- Keine Emojis

VERFÜGBARE VARIABLEN:
{{{{first_name}}}}, {{{{target_name}}}}, {{{{target_company}}}}, {{{{target_position}}}}, {{{{reason}}}} (Grund für Vorstellung)

OUTPUT: NUR der fertige Text.""",
    },
    "thank_you": {
        "slug": "thank_you",
        "name": "Dankes-Nachricht",
        "type": "message",
        "instructions": """Erstelle eine herzliche Dankes-Nachricht.

KONTEXT:
- Absender: {sender_name}
- Tonalität: {tone}

STRUKTUR:
1. Echter, spezifischer Dank
2. Was es für dich bedeutet hat
3. Angebot zur Gegenseitigkeit

REGELN:
- Maximal 200 Zeichen
- Authentisch und spezifisch
- Kein generisches "Danke"
- Keine Emojis

VERFÜGBARE VARIABLEN:
{{{{first_name}}}}, {{{{reason}}}} (wofür gedankt wird)

OUTPUT: NUR der fertige Text.""",
    },
    # ============================================================
    # INMAIL (für Premium/Sales Navigator)
    # ============================================================
    "inmail_cold": {
        "slug": "inmail_cold",
        "name": "InMail Kaltakquise",
        "type": "inmail",
        "instructions": """Erstelle eine InMail für Erstkontakt (Premium/Sales Navigator).

KONTEXT:
- Unternehmen: {company_name}
- Produkt/Service: {product_service}
- USP: {usp}
- Absender: {sender_name}, {sender_position}
- Tonalität: {tone}
- Pain Points: {pain_points}
- Kundennutzen: {customer_benefit}

STRUKTUR:
1. Starke, relevante Betreffzeile (WICHTIG!)
2. Personalisierter Einstieg (Bezug zur Person/Firma)
3. Problem ansprechen
4. Lösung kurz andeuten
5. Klarer, leichter CTA

REGELN:
- Betreffzeile: Max 60 Zeichen, neugierig machen
- Body: Max 600 Zeichen
- Hochgradig personalisiert
- Keine generischen Phrasen
- Keine Emojis

VERFÜGBARE VARIABLEN:
{{{{first_name}}}}, {{{{last_name}}}}, {{{{company}}}}, {{{{position}}}}, {{{{industry}}}}, {{{{headline}}}}

OUTPUT FORMAT:
BETREFF: [Betreffzeile]
---
[Nachrichtentext]""",
    },
}

# Variables schema for LinkedIn module
LINKEDIN_VARIABLES_SCHEMA = {
    "company_name": {"type": "string", "label": "Firmenname"},
    "industry": {"type": "string", "label": "Branche"},
    "product_service": {"type": "string", "label": "Produkt/Dienstleistung"},
    "usp": {"type": "string", "label": "Alleinstellungsmerkmal (USP)"},
    "customer_benefit": {"type": "string", "label": "Kundennutzen"},
    "target_positions": {"type": "array", "label": "Ziel-Positionen"},
    "target_industries": {"type": "array", "label": "Ziel-Branchen"},
    "company_size": {"type": "string", "label": "Unternehmensgröße"},
    "target_region": {"type": "string", "label": "Zielregion"},
    "pain_points": {"type": "array", "label": "Pain Points der Zielgruppe"},
    "tone": {"type": "string", "label": "Tonalität"},
    "sender_name": {"type": "string", "label": "Absender Name"},
    "sender_position": {"type": "string", "label": "Absender Position"},
    "cta_type": {"type": "string", "label": "Call-to-Action Typ"},
    "cta_text": {"type": "string", "label": "Call-to-Action Text"},
    "language": {"type": "string", "label": "Sprache"},
}


class PromptGenerator:
    """Generiert produktive Prompts basierend auf Onboarding-Variablen."""

    def __init__(
        self, provider: str = "anthropic", model: str = "claude-sonnet-4-20250514"
    ):
        self.provider = provider
        self.model = model
        self.llm = LLMService()

    async def generate_all_prompts(
        self,
        module: str,
        variables: dict[str, Any],
    ) -> list[dict]:
        """
        Generiert alle produktiven Prompts für ein Modul basierend auf den Variablen.

        Args:
            module: Modul-Name (z.B. "linkedin")
            variables: Die extrahierten Onboarding-Variablen

        Returns:
            Liste von Prompt-Dictionaries zum Speichern
        """
        templates = self._get_templates_for_module(module)
        if not templates:
            logger.warning(f"No prompt templates found for module: {module}")
            return []

        generated_prompts = []

        for template_key, template in templates.items():
            try:
                prompt_content = await self._generate_single_prompt(
                    template=template,
                    variables=variables,
                )

                generated_prompts.append(
                    {
                        "slug": template["slug"],
                        "name": template["name"],
                        "type": template["type"],
                        "content": prompt_content,
                        "prompt_type": "productive",
                        "is_system": False,
                    }
                )

                logger.info(
                    f"Generated prompt: {template['slug']} ({len(prompt_content)} chars)"
                )

            except Exception as e:
                logger.error(f"Failed to generate prompt {template_key}: {e}")
                continue

        return generated_prompts

    def _get_templates_for_module(self, module: str) -> dict:
        """Get prompt templates for a specific module."""
        if module == "linkedin":
            return LINKEDIN_PROMPT_TEMPLATES
        # Add more modules here as needed
        return {}

    async def _generate_single_prompt(
        self,
        template: dict,
        variables: dict,
    ) -> str:
        """Generiert einen einzelnen Prompt via LLM."""

        # Prepare variables - convert lists to strings
        prepared_vars = {}
        for key, value in variables.items():
            if isinstance(value, list):
                prepared_vars[key] = ", ".join(str(v) for v in value)
            elif value is None:
                prepared_vars[key] = "nicht angegeben"
            else:
                prepared_vars[key] = str(value)

        # Fill in missing variables with defaults
        for key in LINKEDIN_VARIABLES_SCHEMA:
            if key not in prepared_vars:
                prepared_vars[key] = "nicht angegeben"

        # Build instructions with variables
        try:
            instructions = template["instructions"].format(**prepared_vars)
        except KeyError as e:
            logger.warning(f"Missing variable in template: {e}")
            instructions = template["instructions"]

        system_prompt = """Du bist ein Experte für LinkedIn-Kommunikation und B2B-Sales.
Erstelle professionelle, authentische Nachrichten die nicht nach Spam oder Massenmail klingen.
Die Nachrichten sollen persönlich wirken und echtes Interesse zeigen.
Antworte NUR mit dem fertigen Nachrichtentext.
Keine Erklärungen, kein Markdown, keine Anführungszeichen um den Text."""

        response = await self.llm.generate_with_config(
            provider=self.provider,
            model=self.model,
            system_prompt=system_prompt,
            user_prompt=instructions,
            temperature=0.7,
            max_tokens=500,
        )

        # Clean up response
        content = response.strip()
        # Remove quotes if wrapped
        if content.startswith('"') and content.endswith('"'):
            content = content[1:-1]
        if content.startswith("'") and content.endswith("'"):
            content = content[1:-1]

        return content

    @staticmethod
    def get_variables_schema(module: str) -> dict:
        """Get the variables schema for a module."""
        if module == "linkedin":
            return LINKEDIN_VARIABLES_SCHEMA
        return {}


# LinkedIn Onboarding System Prompt
LINKEDIN_ONBOARDING_PROMPT = """Du bist der Setup-Assistent für das go4-automate LinkedIn-Modul.
Deine Aufgabe ist es, den Benutzer durch einen strukturierten Dialog zu führen, um alle notwendigen Informationen für die automatisierte LinkedIn-Outreach zu sammeln.

## Deine Persönlichkeit
- Freundlich, professionell und effizient
- Stelle immer nur 1-2 Fragen auf einmal
- Gib Beispiele wenn hilfreich
- Fasse am Ende alle gesammelten Infos zusammen

## Ablauf des Onboardings

### Phase 1: Unternehmen & Angebot
1. **Firmenname**: "Wie heißt dein Unternehmen?"
2. **Branche**: "In welcher Branche seid ihr tätig?"
3. **Produkt/Dienstleistung**: "Was bietet ihr an? Beschreibe kurz euer Hauptprodukt oder eure Dienstleistung."
4. **USP**: "Was unterscheidet euch von der Konkurrenz? Was ist euer wichtigstes Alleinstellungsmerkmal?"
5. **Kundennutzen**: "Welches konkrete Problem löst ihr für eure Kunden? Was ist der messbare Mehrwert?"

### Phase 2: Zielgruppe
6. **Ziel-Positionen**: "Welche Job-Titel haben eure idealen Ansprechpartner? (z.B. CEO, Head of Sales, IT-Leiter)"
7. **Ziel-Branchen**: "In welchen Branchen sind eure Wunschkunden?"
8. **Unternehmensgröße**: "Wie groß sind die Unternehmen, die ihr ansprechen wollt? (Mitarbeiteranzahl oder Umsatz)"
9. **Region**: "Auf welche Region/Länder fokussiert ihr euch?"
10. **Pain Points**: "Welche typischen Probleme haben eure Zielkunden, bevor sie euch kennen?"

### Phase 3: Kommunikationsstil
11. **Tonalität**: "Wie soll die Ansprache sein? Duzen oder Siezen? Locker oder formell?"
12. **Absender**: "Wer ist der Absender der Nachrichten? (Name und Position)"
13. **Call-to-Action**: "Was soll das Ziel sein? (z.B. Termin vereinbaren, Demo anbieten, Anruf)"

### Phase 4: Bestätigung
- Fasse ALLE gesammelten Informationen übersichtlich zusammen
- Frage: "Sind diese Angaben korrekt? Möchtest du etwas ändern?"
- Bei Bestätigung: Sage "Perfekt! Das Onboarding ist abgeschlossen. Ich werde jetzt die Prompts generieren."

## Wichtige Regeln

1. **Natürlicher Dialog**: Führe ein echtes Gespräch, keine Checkliste abarbeiten
2. **Adaptive Fragen**: Passe Folgefragen an vorherige Antworten an
3. **Keine Annahmen**: Frage nach wenn etwas unklar ist
4. **Ermutigung**: Gib positives Feedback bei guten Antworten
5. **Beispiele**: Wenn der Benutzer unsicher ist, gib konkrete Beispiele
6. **Zusammenfassung**: Am Ende IMMER alle Infos zusammenfassen und bestätigen lassen

## Start
Beginne mit einer freundlichen Begrüßung und der ersten Frage nach dem Firmennamen."""


def get_linkedin_onboarding_prompt() -> dict:
    """Get the LinkedIn onboarding prompt configuration."""
    return {
        "slug": "onboarding",
        "name": "LinkedIn Setup Assistant",
        "module": "linkedin",
        "prompt_type": "setup",
        "system_prompt": LINKEDIN_ONBOARDING_PROMPT,
        "user_prompt": "Starte das Onboarding-Interview.",
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",
        "temperature": 0.7,
        "max_tokens": 1024,
        "is_system": True,
        "variables_schema": LINKEDIN_VARIABLES_SCHEMA,
    }
