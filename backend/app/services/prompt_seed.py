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
        "name": "Research Topic Analyzer",
        "description": "Analysiert Research-Findings und schlägt Content-Themen vor.",
        "category": "research",
        "system_prompt": (
            "Du bist ein Content-Stratege für {{COMPANY_NAME}}. "
            "Deine Aufgabe ist es, aus aktuellen Branchennachrichten "
            "relevante Content-Themen für Social Media und E-Mail-Marketing abzuleiten."
        ),
        "user_prompt": (
            "Analysiere die folgenden Research-Findings und schlage 3-5 Content-Themen vor:\n\n"
            "{{findings_json}}\n\n"
            "Keywords: {{keywords}}\n\n"
            "Antworte als JSON-Array: "
            '[{{"title": "...", "description": "...", "category": "content|email|social", '
            '"platforms": ["facebook", "instagram", "email"], "priority": 1-5}}]'
        ),
        "variables": [
            {
                "name": "findings_json",
                "type": "string",
                "required": True,
                "default": None,
                "description": "JSON-Array der Research-Findings",
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
        "max_tokens": 2048,
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
