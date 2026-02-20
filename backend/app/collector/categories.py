"""Default category definitions with inline prompts."""

DEFAULT_CATEGORIES = [
    {
        "id": "social_media",
        "label": "Social Media",
        "icon": "share",
        "generate_topics": True,
        "prompt": {
            "system": "Du bist ein Social Media Experte fuer B2B-Unternehmen im Bereich Energie und Gebaeudetechnik.",
            "user": (
                "Erstelle aus folgendem Topic einen Social Media Post:\n"
                "Titel: {{topic_title}}\n"
                "Beschreibung: {{topic_description}}\n\n"
                "Format: Caption + Hashtags + CTA\n"
                "Antworte als JSON."
            ),
            "output_format": "json",
            "output_schema": {
                "caption": "string",
                "hashtags": "list[string]",
                "cta": "string",
                "platform_notes": "string",
            },
        },
    },
    {
        "id": "podcast",
        "label": "Podcast",
        "icon": "microphone",
        "generate_topics": True,
        "prompt": {
            "system": "Du bist ein Podcast-Redakteur fuer technische Themen im Energiebereich.",
            "user": (
                "Erstelle ein Podcast-Segment:\n"
                "Titel: {{topic_title}}\n"
                "Beschreibung: {{topic_description}}\n\n"
                "Antworte als JSON."
            ),
            "output_format": "json",
            "output_schema": {
                "episode_title": "string",
                "intro": "string",
                "script": "string",
                "outro": "string",
                "shownotes": "string",
            },
        },
    },
    {
        "id": "blog",
        "label": "Homepage Blog",
        "icon": "document",
        "generate_topics": True,
        "prompt": {
            "system": "Du bist ein technischer Blog-Autor fuer Energieeffizienz und Gebaeudetechnik.",
            "user": (
                "Erstelle einen Blog-Artikel:\n"
                "Titel: {{topic_title}}\n"
                "Beschreibung: {{topic_description}}\n\n"
                "Antworte als JSON."
            ),
            "output_format": "json",
            "output_schema": {
                "title": "string",
                "intro": "string",
                "body": "string",
                "conclusion": "string",
                "meta_description": "string",
            },
        },
    },
    {
        "id": "reporting",
        "label": "Reporting",
        "icon": "chart",
        "generate_topics": False,
        "prompt": {
            "system": "Du bist ein Analyst fuer Energiedaten und Marktberichte.",
            "user": (
                "Erstelle eine Zusammenfassung:\n"
                "Titel: {{topic_title}}\n"
                "Beschreibung: {{topic_description}}\n\n"
                "Antworte als JSON."
            ),
            "output_format": "json",
            "output_schema": {
                "title": "string",
                "summary": "string",
                "key_findings": "list[string]",
                "recommendations": "list[string]",
            },
        },
    },
    {
        "id": "competitor",
        "label": "Wettbewerbsanalyse",
        "icon": "eye",
        "generate_topics": False,
        "prompt": {
            "system": "Du bist ein Wettbewerbsanalyst im Bereich Energieeffizienz.",
            "user": (
                "Analysiere die Wettbewerbsinformation:\n"
                "Titel: {{topic_title}}\n"
                "Beschreibung: {{topic_description}}\n\n"
                "Antworte als JSON."
            ),
            "output_format": "json",
            "output_schema": {
                "competitor": "string",
                "analysis": "string",
                "strengths": "list[string]",
                "opportunities": "list[string]",
            },
        },
    },
    {
        "id": "email",
        "label": "Weekly Customer Email",
        "icon": "envelope",
        "generate_topics": True,
        "prompt": {
            "system": "Du bist ein Email-Marketing-Spezialist fuer B2B im Energiebereich.",
            "user": (
                "Erstelle einen Newsletter-Abschnitt:\n"
                "Titel: {{topic_title}}\n"
                "Beschreibung: {{topic_description}}\n\n"
                "Antworte als JSON."
            ),
            "output_format": "json",
            "output_schema": {
                "subject_line": "string",
                "preview_text": "string",
                "body": "string",
                "cta": "string",
            },
        },
    },
    {
        "id": "education",
        "label": "Weiterbildung",
        "icon": "academic",
        "generate_topics": False,
        "prompt": {
            "system": "Du bist ein Experte fuer Wissensvermittlung im Bereich Energieeffizienz.",
            "user": (
                "Erstelle eine Lernzusammenfassung:\n"
                "Titel: {{topic_title}}\n"
                "Beschreibung: {{topic_description}}\n\n"
                "Antworte als JSON."
            ),
            "output_format": "json",
            "output_schema": {
                "title": "string",
                "key_learnings": "list[string]",
                "summary": "string",
                "relevance": "string",
            },
        },
    },
]


def get_all_categories(custom_categories: list[dict] | None = None) -> list[dict]:
    """Return default categories plus any custom ones."""
    categories = list(DEFAULT_CATEGORIES)
    if custom_categories:
        existing_ids = {c["id"] for c in categories}
        for custom in custom_categories:
            if custom.get("id") not in existing_ids:
                categories.append(custom)
    return categories


def get_category_by_id(
    category_id: str, custom_categories: list[dict] | None = None
) -> dict | None:
    """Get a specific category by its ID."""
    for cat in get_all_categories(custom_categories):
        if cat["id"] == category_id:
            return cat
    return None
