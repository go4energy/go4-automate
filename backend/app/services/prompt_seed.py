"""Seed prompts for initial setup."""

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prompt import Prompt

SEED_PROMPTS = [
    {
        "slug": "social-media-post",
        "name": "Social Media Post Generator",
        "description": "Generiert Social-Media-Posts mit Hook, CTA und Hashtags.",
        "category": "content",
        "system_prompt": (
            "Du bist ein Social-Media-Marketing-Experte für {{COMPANY_NAME}}. "
            "Tonalität: {{CONTENT_TONE}}. Zielgruppe: {{TARGET_AUDIENCE}}."
        ),
        "user_prompt": (
            'Erstelle einen Social-Media-Post für {{platform}} zum Thema "{{topic}}".\n'
            "Content-Typ: {{content_type}} | Funnel-Stage: {{funnel_stage}}\n\n"
            "Regeln:\n"
            "- Max 2200 Zeichen für die Caption\n"
            "- Hook am Anfang (erster Satz muss Aufmerksamkeit erregen)\n"
            "- CTA am Ende (klare Handlungsaufforderung)\n"
            "- 5-8 relevante Hashtags\n"
            "- Kurze Version (max 280 Zeichen) für Twitter/X\n\n"
            "{{additional_instructions}}\n\n"
            'Antworte als JSON: {{"title": "...", "caption": "...", '
            '"short": "...", "hashtags": "...", "hook": "...", "cta": "..."}}'
        ),
        "variables": [
            {
                "name": "platform",
                "type": "string",
                "required": True,
                "default": None,
                "description": "Social-Media-Plattform (facebook, instagram, linkedin)",
            },
            {
                "name": "topic",
                "type": "string",
                "required": True,
                "default": None,
                "description": "Thema des Posts",
            },
            {
                "name": "content_type",
                "type": "string",
                "required": False,
                "default": "post",
                "description": "Art des Contents (post, story, reel)",
            },
            {
                "name": "funnel_stage",
                "type": "string",
                "required": False,
                "default": "awareness",
                "description": "Funnel-Phase (awareness, consideration, decision)",
            },
            {
                "name": "additional_instructions",
                "type": "string",
                "required": False,
                "default": "",
                "description": "Zusätzliche Anweisungen",
            },
            {
                "name": "COMPANY_NAME",
                "type": "string",
                "required": False,
                "default": "",
                "description": "Firmenname (aus Tenant-Config)",
            },
            {
                "name": "CONTENT_TONE",
                "type": "string",
                "required": False,
                "default": "professional",
                "description": "Tonalität (aus Tenant-Config)",
            },
            {
                "name": "TARGET_AUDIENCE",
                "type": "string",
                "required": False,
                "default": "B2B Entscheider",
                "description": "Zielgruppe (aus Tenant-Config)",
            },
        ],
        "output_format": "json",
        "provider": "anthropic",
        "model": "claude-sonnet-4-5-20250929",
        "temperature": 0.8,
        "max_tokens": 2048,
    },
    {
        "slug": "lead-scoring",
        "name": "Lead Scoring",
        "description": "Bewertet die Qualität eines Leads anhand seiner Daten.",
        "category": "analysis",
        "system_prompt": (
            "Du bist ein Lead-Scoring-Experte für {{COMPANY_NAME}}. "
            "Bewerte Leads auf einer Skala von 1-100 basierend auf den bereitgestellten Daten."
        ),
        "user_prompt": (
            "Bewerte den folgenden Lead:\n\n"
            "Name: {{lead_name}}\n"
            "E-Mail: {{lead_email}}\n"
            "Unternehmen: {{lead_company}}\n"
            "Position: {{lead_position}}\n"
            "Quelle: {{lead_source}}\n"
            "Nachricht: {{lead_message}}\n\n"
            "Antworte als JSON: "
            '{{"score": 0-100, "reasoning": "...", "priority": "hot|warm|cold", '
            '"recommended_action": "..."}}'
        ),
        "variables": [
            {
                "name": "lead_name",
                "type": "string",
                "required": True,
                "default": None,
                "description": "Name des Leads",
            },
            {
                "name": "lead_email",
                "type": "string",
                "required": True,
                "default": None,
                "description": "E-Mail des Leads",
            },
            {
                "name": "lead_company",
                "type": "string",
                "required": False,
                "default": "",
                "description": "Unternehmen des Leads",
            },
            {
                "name": "lead_position",
                "type": "string",
                "required": False,
                "default": "",
                "description": "Position des Leads",
            },
            {
                "name": "lead_source",
                "type": "string",
                "required": False,
                "default": "website",
                "description": "Quelle des Leads",
            },
            {
                "name": "lead_message",
                "type": "string",
                "required": False,
                "default": "",
                "description": "Nachricht des Leads",
            },
            {
                "name": "COMPANY_NAME",
                "type": "string",
                "required": False,
                "default": "",
                "description": "Firmenname (aus Tenant-Config)",
            },
        ],
        "output_format": "json",
        "provider": "openai",
        "model": "gpt-4o-mini",
        "temperature": 0.3,
        "max_tokens": 1024,
    },
    {
        "slug": "email-followup",
        "name": "Follow-Up E-Mail Generator",
        "description": "Generiert personalisierte Follow-Up E-Mails für Leads.",
        "category": "email",
        "system_prompt": (
            "Du bist ein E-Mail-Marketing-Experte für {{COMPANY_NAME}}. "
            "Tonalität: {{CONTENT_TONE}}. "
            "Schreibe professionelle, persönliche Follow-Up E-Mails."
        ),
        "user_prompt": (
            "Erstelle eine Follow-Up E-Mail für:\n\n"
            "Empfänger: {{recipient_name}}\n"
            "Unternehmen: {{recipient_company}}\n"
            "Kontext: {{context}}\n"
            "Letzter Kontakt: {{last_contact}}\n"
            "Ziel: {{goal}}\n\n"
            "Antworte als JSON: "
            '{{"subject": "...", "body": "...", "cta": "..."}}'
        ),
        "variables": [
            {
                "name": "recipient_name",
                "type": "string",
                "required": True,
                "default": None,
                "description": "Name des Empfängers",
            },
            {
                "name": "recipient_company",
                "type": "string",
                "required": False,
                "default": "",
                "description": "Unternehmen des Empfängers",
            },
            {
                "name": "context",
                "type": "string",
                "required": True,
                "default": None,
                "description": "Kontext des bisherigen Kontakts",
            },
            {
                "name": "last_contact",
                "type": "string",
                "required": False,
                "default": "",
                "description": "Datum des letzten Kontakts",
            },
            {
                "name": "goal",
                "type": "string",
                "required": False,
                "default": "Termin vereinbaren",
                "description": "Ziel der E-Mail",
            },
            {
                "name": "COMPANY_NAME",
                "type": "string",
                "required": False,
                "default": "",
                "description": "Firmenname (aus Tenant-Config)",
            },
            {
                "name": "CONTENT_TONE",
                "type": "string",
                "required": False,
                "default": "professional",
                "description": "Tonalität (aus Tenant-Config)",
            },
        ],
        "output_format": "json",
        "provider": "anthropic",
        "model": "claude-sonnet-4-5-20250929",
        "temperature": 0.6,
        "max_tokens": 2048,
    },
    {
        "slug": "research-topic-analyzer",
        "name": "Artikel-Zusammenfassung",
        "description": "Fasst einzelne Artikel-Findings zusammen (Kurzfassung + Langfassung).",
        "category": "research",
        "system_prompt": (
            "Du bist ein Recherche-Analyst fuer {{COMPANY_NAME}}. "
            "Deine Aufgabe ist es, Artikel und Nachrichten praezise zusammenzufassen. "
            "Fokussiere dich auf die Kernaussagen, relevante Fakten und den Kontext."
        ),
        "user_prompt": (
            "Fasse JEDEN der folgenden Artikel einzeln zusammen.\n\n"
            "{{findings_json}}\n\n"
            "Keywords: {{keywords}}\n\n"
            "Erstelle fuer JEDEN Artikel (identifiziert durch seine 'id') eine Zusammenfassung:\n"
            '- "finding_id": Die id des Artikels (exakt uebernehmen)\n'
            '- "title": Praegnanter Titel der Zusammenfassung\n'
            '- "description": Kurzfassung (2-5 Saetze, kompakt und informativ)\n'
            '- "detail": Langfassung (5-10 Saetze, mit Kontext, Hintergrund '
            "und warum das Thema relevant ist)\n"
            '- "category": Kategorie (content|email|social|general)\n'
            '- "priority": Relevanz 1-5 (1=sehr hoch)\n\n'
            "Antworte als JSON-Array mit genau einem Eintrag pro Artikel: "
            '[{{"finding_id": 123, "title": "...", "description": "Kurzfassung...", '
            '"detail": "Langfassung mit Kontext...", '
            '"category": "general", "priority": 3}}]'
        ),
        "variables": [
            {
                "name": "findings_json",
                "type": "string",
                "required": True,
                "default": None,
                "description": "JSON-Array der Research-Findings mit id",
            },
            {
                "name": "keywords",
                "type": "string",
                "required": False,
                "default": "allgemein",
                "description": "Komma-separierte Keywords",
            },
            {
                "name": "COMPANY_NAME",
                "type": "string",
                "required": False,
                "default": "",
                "description": "Firmenname (aus Tenant-Config)",
            },
        ],
        "output_format": "json",
        "provider": "anthropic",
        "model": "claude-sonnet-4-5-20250929",
        "temperature": 0.5,
        "max_tokens": 4096,
    },
    {
        "slug": "custom-topic-content",
        "name": "Custom Topic Content Generator",
        "description": "Generiert Content basierend auf einem benutzerdefinierten Thema.",
        "category": "content",
        "system_prompt": (
            "Du bist ein Social-Media- und E-Mail-Marketing-Experte für {{COMPANY_NAME}}. "
            "Tonalität: {{CONTENT_TONE}}."
        ),
        "user_prompt": (
            "Erstelle {{content_type}} Content für {{platform}} basierend auf:\n\n"
            "Thema: {{topic_title}}\n"
            "Beschreibung: {{topic_description}}\n\n"
            "Antworte als JSON: "
            '{{"title": "...", "caption": "...", "short": "...", '
            '"hashtags": "...", "hook": "...", "cta": "..."}}'
        ),
        "variables": [
            {
                "name": "platform",
                "type": "string",
                "required": True,
                "default": None,
                "description": "Ziel-Plattform (facebook, instagram, email)",
            },
            {
                "name": "content_type",
                "type": "string",
                "required": False,
                "default": "post",
                "description": "Art des Contents (post, story, email)",
            },
            {
                "name": "topic_title",
                "type": "string",
                "required": True,
                "default": None,
                "description": "Titel des Themas",
            },
            {
                "name": "topic_description",
                "type": "string",
                "required": True,
                "default": None,
                "description": "Beschreibung des Themas",
            },
            {
                "name": "COMPANY_NAME",
                "type": "string",
                "required": False,
                "default": "",
                "description": "Firmenname (aus Tenant-Config)",
            },
            {
                "name": "CONTENT_TONE",
                "type": "string",
                "required": False,
                "default": "professional",
                "description": "Tonalität (aus Tenant-Config)",
            },
        ],
        "output_format": "json",
        "provider": "anthropic",
        "model": "claude-sonnet-4-5-20250929",
        "temperature": 0.7,
        "max_tokens": 2048,
    },
    {
        "slug": "chat-onboarding",
        "name": "Chat: Onboarding-Berater",
        "description": (
            "System-Prompt fuer den Onboarding-Chat. "
            "Stellt Fragen zu Branche, Zielgruppe und Themen."
        ),
        "category": "chat",
        "system_prompt": (
            "Du bist ein freundlicher Marketing-Berater fuer {{COMPANY_NAME}}. "
            "Stelle Onboarding-Fragen: 1) Branche 2) Zielgruppe 3) Wichtige Themen "
            "4) Wettbewerber 5) Bevorzugte Plattformen. "
            "Gib konkrete Empfehlungen basierend auf den Antworten."
        ),
        "user_prompt": "{{user_message}}",
        "variables": [
            {
                "name": "user_message",
                "type": "string",
                "required": True,
                "default": None,
                "description": "Nachricht des Nutzers",
            },
            {
                "name": "COMPANY_NAME",
                "type": "string",
                "required": False,
                "default": "",
                "description": "Firmenname (aus Tenant-Config)",
            },
        ],
        "output_format": "text",
        "provider": "anthropic",
        "model": "claude-sonnet-4-5-20250929",
        "temperature": 0.7,
        "max_tokens": 2048,
    },
    {
        "slug": "chat-research",
        "name": "Chat: Research-Assistent",
        "description": (
            "System-Prompt fuer den Research-Chat. " "Hilft bei der Quellensuche."
        ),
        "category": "chat",
        "system_prompt": (
            "Du hilfst {{COMPANY_NAME}} relevante Informationsquellen zu finden. "
            "Schlage RSS-Feeds, Branchenportale und Keywords vor "
            "basierend auf der Branche."
        ),
        "user_prompt": "{{user_message}}",
        "variables": [
            {
                "name": "user_message",
                "type": "string",
                "required": True,
                "default": None,
                "description": "Nachricht des Nutzers",
            },
            {
                "name": "COMPANY_NAME",
                "type": "string",
                "required": False,
                "default": "",
                "description": "Firmenname (aus Tenant-Config)",
            },
        ],
        "output_format": "text",
        "provider": "anthropic",
        "model": "claude-sonnet-4-5-20250929",
        "temperature": 0.6,
        "max_tokens": 2048,
    },
    {
        "slug": "broadcaster-script",
        "name": "Broadcaster Script Generator",
        "description": "Generiert ein Briefing-Script zum Vorlesen aus Collector-Findings.",
        "category": "content",
        "system_prompt": (
            "Du bist ein professioneller Nachrichtensprecher fuer {{COMPANY_NAME}}. "
            "Zielgruppe: {{target_audience}}. Sprache: {{language}}. "
            "Erstelle ein Audio-Briefing-Script zum Vorlesen. "
            "Schreibe reinen Sprechtext — kein Markdown, keine Aufzaehlungen, "
            "keine Sonderzeichen. Natuerliche, gesprochene Sprache."
        ),
        "user_prompt": (
            "Erstelle ein Briefing-Script (max. {{max_duration}} Minuten Sprechzeit).\n\n"
            "Intro: {{intro_text}}\n\n"
            "Aktuelle Themen:\n{{findings_text}}\n\n"
            "Outro: {{outro_text}}\n\n"
            "Fasse die wichtigsten Themen zusammen und verbinde sie fliessend."
        ),
        "variables": [
            {
                "name": "target_audience",
                "type": "string",
                "required": False,
                "default": "Allgemein",
                "description": "Zielgruppe des Briefings",
            },
            {
                "name": "language",
                "type": "string",
                "required": False,
                "default": "de",
                "description": "Sprache des Briefings",
            },
            {
                "name": "max_duration",
                "type": "string",
                "required": False,
                "default": "5",
                "description": "Maximale Sprechzeit in Minuten",
            },
            {
                "name": "intro_text",
                "type": "string",
                "required": False,
                "default": "Willkommen zum Briefing.",
                "description": "Intro-Text",
            },
            {
                "name": "findings_text",
                "type": "string",
                "required": True,
                "default": None,
                "description": "Auflistung der Findings",
            },
            {
                "name": "outro_text",
                "type": "string",
                "required": False,
                "default": "Das war Ihr Briefing fuer heute.",
                "description": "Outro-Text",
            },
            {
                "name": "COMPANY_NAME",
                "type": "string",
                "required": False,
                "default": "",
                "description": "Firmenname (aus Tenant-Config)",
            },
        ],
        "output_format": "text",
        "provider": "anthropic",
        "model": "claude-sonnet-4-5-20250929",
        "temperature": 0.6,
        "max_tokens": 4096,
    },
    {
        "slug": "chat-broadcaster",
        "name": "Chat: Broadcaster-Assistent",
        "description": (
            "System-Prompt fuer den Broadcaster-Setup-Chat. "
            "Hilft bei der Einrichtung von Audio-Briefing-Channels."
        ),
        "category": "chat",
        "system_prompt": (
            "Du bist ein Audio-Briefing-Experte fuer {{COMPANY_NAME}}. "
            "Hilf bei der Einrichtung der Broadcaster-Plattform.\n\n"
            "## Deine Aufgabe\n"
            "Fuehre den Benutzer durch die Broadcaster-Konfiguration:\n"
            "1. Frage nach den Zielgruppen (Management, Pflege, IT, Vertrieb etc.)\n"
            "2. Schlage passende Channel-Strukturen vor\n"
            "3. Empfehle Kategorien basierend auf den Collector-Quellen\n"
            "4. Klaere Zeitplan und Frequenz\n"
            "5. Konfiguriere TTS und Stimme\n"
            "6. Lege erste Listener-Benutzer an\n\n"
            "## Branchenspezifische Empfehlungen\n"
            "- Krankenhaus: Channels fuer Management, Pflege, IT. Taeglich 06:00.\n"
            "- Behoerde: Channels nach Abteilung. Woechentlich montags.\n"
            "- Unternehmen: Channels nach Rolle (GF, Vertrieb, Technik). Mo-Fr 07:00.\n"
            "- Allgemein: 1 Channel zum Start, dann nach Feedback aufteilen.\n\n"
            "## Regeln\n"
            "- Antworte immer auf Deutsch\n"
            "- Schlage konkrete Channel-Namen und Slugs vor\n"
            "- Frage nach Bestaetigung bevor du Channels oder User anlegst\n"
            "- Erklaere kurz den Unterschied zwischen TTS-Engines\n"
            "- Halte Antworten kompakt und uebersichtlich"
        ),
        "user_prompt": "{{user_message}}",
        "variables": [
            {
                "name": "user_message",
                "type": "string",
                "required": True,
                "default": None,
                "description": "Nachricht des Nutzers",
            },
            {
                "name": "COMPANY_NAME",
                "type": "string",
                "required": False,
                "default": "",
                "description": "Firmenname (aus Tenant-Config)",
            },
        ],
        "output_format": "text",
        "provider": "anthropic",
        "model": "claude-sonnet-4-5-20250929",
        "temperature": 0.7,
        "max_tokens": 2048,
    },
    {
        "slug": "chat-general",
        "name": "Chat: Marketing-Assistent",
        "description": (
            "System-Prompt fuer den allgemeinen Chat. "
            "Hilft bei Content-Ideen und Strategie."
        ),
        "category": "chat",
        "system_prompt": (
            "Du bist ein Marketing-Assistent fuer {{COMPANY_NAME}}. "
            "Hilf bei Content-Ideen, Strategie und Konfiguration."
        ),
        "user_prompt": "{{user_message}}",
        "variables": [
            {
                "name": "user_message",
                "type": "string",
                "required": True,
                "default": None,
                "description": "Nachricht des Nutzers",
            },
            {
                "name": "COMPANY_NAME",
                "type": "string",
                "required": False,
                "default": "",
                "description": "Firmenname (aus Tenant-Config)",
            },
        ],
        "output_format": "text",
        "provider": "anthropic",
        "model": "claude-sonnet-4-5-20250929",
        "temperature": 0.7,
        "max_tokens": 2048,
    },
]


async def seed_prompts(db: AsyncSession, tenant_id: str) -> int:
    """Seed initial prompts. Idempotent: skips existing slugs. Returns count of created."""
    created = 0
    for seed in SEED_PROMPTS:
        result = await db.execute(
            select(Prompt).where(
                Prompt.tenant_id == tenant_id,
                Prompt.slug == seed["slug"],
            )
        )
        if result.scalar_one_or_none():
            continue

        prompt = Prompt(tenant_id=tenant_id, **seed)
        db.add(prompt)
        created += 1
        logger.info(
            "Seed Prompt erstellt: {slug} (Tenant: {tenant})",
            slug=seed["slug"],
            tenant=tenant_id,
        )

    if created > 0:
        await db.flush()
    return created


async def update_prompt_template(db: AsyncSession, tenant_id: str, slug: str) -> bool:
    """Update an existing prompt with the latest seed template. Returns True if updated."""
    seed = next((s for s in SEED_PROMPTS if s["slug"] == slug), None)
    if not seed:
        return False

    result = await db.execute(
        select(Prompt).where(
            Prompt.tenant_id == tenant_id,
            Prompt.slug == slug,
        )
    )
    prompt = result.scalar_one_or_none()
    if not prompt:
        return False

    prompt.user_prompt = seed["user_prompt"]
    prompt.system_prompt = seed["system_prompt"]
    await db.flush()
    logger.info(
        "Prompt Template aktualisiert: {slug} (Tenant: {tenant})",
        slug=slug,
        tenant=tenant_id,
    )
    return True
