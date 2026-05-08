"""LLM-driven campaign intake.

Takes a free-text description of what a user wants to find and maps it to:
- Google Place Types (for Nearby Search, precise)
- Free-text synonyms (for Text Search, broader)
- A geographic scope (germany / bundesland / circle)
- A rough API-call + cost estimate

The LLM gets the catalogue of supported Google Place Types as context so its
output can be used directly in source_config. We validate the response against
the Pydantic model and fail closed if the LLM emits anything unexpected.
"""

from __future__ import annotations

import json
import re
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field

from app.exceptions import ExternalServiceError
from app.services.llm import LLMService

# Subset of Google's Place Types catalogue covering the trades that German
# SMB leadgen typically targets. Keeping the list small keeps the prompt
# cheap and the LLM focused.
# Full reference: https://developers.google.com/maps/documentation/places/web-service/place-types
SUPPORTED_PLACE_TYPES: list[str] = [
    "electrician",
    "plumber",
    "roofing_contractor",
    "general_contractor",
    "painter",
    "locksmith",
    "car_dealer",
    "car_repair",
    "furniture_store",
    "home_goods_store",
    "hardware_store",
    "real_estate_agency",
    "moving_company",
    "storage",
    "lawyer",
    "accounting",
    "insurance_agency",
    "dentist",
    "doctor",
    "veterinary_care",
    "restaurant",
    "cafe",
    "bakery",
    "hair_care",
    "beauty_salon",
    "gym",
    "travel_agency",
]


class IntakeRequest(BaseModel):
    text: str = Field(..., min_length=3, max_length=2000)


class IntakeGeographic(BaseModel):
    mode: str
    bundesland: str | None = None
    center_lat: float | None = None
    center_lng: float | None = None
    radius_km: float | None = None


class IntakeSearchModes(BaseModel):
    nearby: bool = True
    text: bool = True


class IntakeSuggestion(BaseModel):
    # Identity
    name_suggestion: str = ""
    slug_suggestion: str = ""
    # Search params
    search_modes: IntakeSearchModes = Field(default_factory=IntakeSearchModes)
    nearby_types: list[str]
    text_synonyms: list[str]
    geographic: IntakeGeographic
    min_tile_km: float = 10.0
    max_api_calls: int = 2000
    # Pipeline auto-chain mode
    pipeline_mode: str = "smart"
    # Cost / volume estimates
    estimated_calls_low: int
    estimated_calls_high: int
    estimated_cost_usd_low: float
    estimated_cost_usd_high: float
    estimated_results_low: int
    estimated_results_high: int
    reasoning: str
    # Stage 3 analysis scaffolding - auto-generated from the same user intent
    target_profile: str = ""
    output_description: str = ""
    llm_prompt_template: str = ""
    # Quality feedback for the user. When the description is too thin to produce
    # a sharp profile, set needs_more_input=true and fill improvement_hints with
    # concrete questions the user should answer.
    needs_more_input: bool = False
    improvement_hints: str = ""


_SYSTEM_PROMPT = """Du bist ein Experte fuer B2B-Lead-Discovery mit der Google Places API
UND fuer die Vorbereitung personalisierter Akquise-Kampagnen.

Deine Aufgabe: Eine freitextliche Zielbeschreibung des Kunden in einen kompletten
Kampagnen-Vorschlag uebersetzen - Name, Suchparameter, Pipeline-Modus, plus ein
detailliertes ZIELPROFIL und eine Output-Spec fuer den LLM-Analyse-Schritt (Stage 3).

WICHTIG: Stage 3 sammelt nur strukturiertes Intel — die eigentliche Erstansprache
formuliert ein nachgelagertes Mail-/Brief-Modul. Das target_profile und die
output_description, die du erzeugst, muessen Stage 3 alle Infos liefern, die das
spaetere Modul fuer eine glaubhaft personalisierte Ansprache braucht.

Antworte AUSSCHLIESSLICH mit validem JSON, keine Erklaerung davor oder danach,
keine Code-Fences. Felder:

{
  "name_suggestion": "<knapper Kampagnen-Name (max 80 Zeichen)>",
  "slug_suggestion": "<kebab-case Slug, max 60 Zeichen, nur a-z 0-9 und Bindestrich>",
  "search_modes": {
    "nearby": <true wenn mind. ein nearby_type passt, sonst false>,
    "text": <true wenn Branche durch Synonyme besser abgedeckt ist (Default true)>
  },
  "nearby_types": [<Liste aus der erlaubten Google-Types-Liste>],
  "text_synonyms": [<2-6 deutsche Suchbegriffe, die die Branche abdecken>],
  "geographic": {
    "mode": "germany" | "austria" | "switzerland" | "bundesland" | "circle",
    "bundesland": "<nur wenn mode=bundesland>",
    "center_lat": <nur wenn mode=circle>,
    "center_lng": <nur wenn mode=circle>,
    "radius_km": <nur wenn mode=circle, 1-500>
  },
  "min_tile_km": <10 = gruendlich, 30 = guenstig, Default 10>,
  "max_api_calls": <1-10000, konservativ waehlen>,
  "pipeline_mode": "smart" | "cheap" | "legacy",
  "estimated_calls_low": <Unterer Rand>,
  "estimated_calls_high": <Oberer Rand>,
  "estimated_cost_usd_low": <low * 0.032>,
  "estimated_cost_usd_high": <high * 0.032>,
  "estimated_results_low": <erwartete Firmen min>,
  "estimated_results_high": <erwartete Firmen max>,
  "reasoning": "<1-3 Saetze: warum diese Parameter>",
  "target_profile": "<DETAILLIERTES strukturiertes Beuteschema, siehe Vorlage unten>",
  "output_description": "<DETAILLIERTE Output-Spec, siehe Vorlage unten>",
  "llm_prompt_template": "",
  "needs_more_input": <true|false>,
  "improvement_hints": "<wenn needs_more_input=true: konkrete Folgefragen an den Nutzer (max 600 Zeichen). Sonst leer.>"
}

VORLAGE FUER target_profile (immer dieser Aufbau, mit konkreten Inhalten gefuellt):
---
ZIELGRUPPE: <Branche/Betriebstyp + grobe Groesse, 1-2 Saetze>

MUSS-KRITERIEN:
- <harte Kriterien aus der Beschreibung, je 1 Bullet>
- ...

SOLL-KRITERIEN:
- <weichere Indikatoren, Spezialisierungen, Erfahrungswerte>
- ...

NICE-TO-HAVE:
- <Bonus-Indikatoren>
- ...

ROTE FLAGGEN (gegen Match):
- <konkrete Negativ-Indikatoren - z.B. eigenes Konkurrenzprodukt vorhanden,
   falsche Klientel, falsche Betriebsgroesse>
- ...

ANSPRACHE-TONALITAET: <Ton, Anrede-Stil, Empowerment-/Beratungs-/Vertriebs-Modus -
1-2 Saetze>
---

VORLAGE FUER output_description (immer dieser Aufbau):
---
Stage 3 sammelt strukturierte Infos — die eigentliche Erstansprache formuliert ein
nachgelagertes Mail-/Brief-Modul.

KONTAKTPERSON (im Feld personalization_hook als strukturierter Block am Anfang):
KONTAKT:
- Anrede: Herr / Frau / unklar
- Vorname / Nachname (sauber getrennt)
- Geschlecht: m / w / unklar
- Position: <z.B. Geschaeftsfuehrer / Inhaber / Vertrieb / Ansprechpartner ...>
- Quelle: impressum / team-seite / kontakt-seite

Bevorzugt operativer Vertriebs-/Fach-Kontakt aus Team-/Kontakt-Seite. Fallback:
Geschaeftsfuehrer/in aus Impressum.

PRE-PITCH-INTEL (im personalization_hook darunter als 3-5 Stichpunkte):
- Konkrete Projekte/Referenzen vom Webauftritt
- Erkennbare Spezialisierung im Themenbereich der Kampagne
- Hinweise auf Reife/Groesse (Bewertungen, MA-Zahlen, mehrere Standorte)
- Luecke fuer das Produkt des Kunden (was fehlt offensichtlich, was wir adressieren?)
Format: knappe Stichpunkte, keine Fliesstext-Anrede, kein Pitch.

ATOMARE FELDER:
- services: bestehende Angebote (sehr konkret aus Webauftritt)
- brands: erwaehnte Hersteller/Marken
- customer_segments: <kundenspezifische Endkunden-Typen, z.B. WEG, Hausverwaltung,
  Gewerbe, EFH, Kommune, Industrie - was die Kampagne braucht>
- company_size_indicator: Mitarbeiterzahl wenn erkennbar
- red_flags: KRITISCH - <konkrete Negativ-Indikatoren aus dem Zielprofil pruefen
  und benennen, insbesondere Wettbewerbs-Indikatoren>
- target_match_score (0-10): Match zum target_profile.
  8-10 = Top, 4-7 = mittel, 0-3 = unpassend.
---

REGELN ZUM AUSFUELLEN:
- target_profile UND output_description muessen die KONKRETEN Begriffe und
  Endkunden-Typen aus der Nutzer-Beschreibung enthalten — nicht generisch bleiben.
- Wenn der Nutzer sein Produkt erwaehnt, leite daraus ab, welche Anbieter Wettbewerb
  sind (rote Flagge) und welche Anbieter Partner sind (Match).
- Wenn der Nutzer Endkunden nennt (z.B. WEG, Hausverwaltung), uebernimm die in
  customer_segments-Vorgaben und in MUSS/SOLL.
- Anrede-Tonalitaet: leite aus dem Empowerment-/Vertriebs-/Beratungs-Charakter
  der Beschreibung ab.

QUALITAETS-CHECK (needs_more_input):
Setze needs_more_input=true und fuelle improvement_hints, wenn die Beschreibung
zu duenn ist fuer ein scharfes Profil. Konkrete Mangel-Indikatoren:
- Kein klares Produkt / keine Wertschoepfung des Kunden genannt
- Keine Endkunden-Typen genannt (wer kauft am Ende vom Lead?)
- Keine roten Flaggen ableitbar (was waere ein Wettbewerber?)
- Region nicht klar (Deutschland? Bundesland? Umkreis?)
- Betriebstyp/Branche zu generisch ("Handwerker" statt "Elektroinstallateure mit
  Wallbox-Erfahrung")
Auch wenn needs_more_input=true: trotzdem den besten moeglichen Vorschlag erzeugen.
improvement_hints: 2-4 konkrete Folgefragen, nicht generisch ("Bitte mehr Details").

REGELN ZUR SUCHE:
- nearby_types NUR aus der erlaubten Liste. Kein Match -> leeres Array und
  search_modes.nearby = false.
- text_synonyms: deutsche Begriffe wie 'Elektroinstallation'. Keine Google-Types.
- search_modes: mindestens eines muss true sein.
- pipeline_mode: 'smart' (Default, Places->LLM), 'cheap' (Places->Regex), 'legacy'
  (Places->Regex->LLM). Im Zweifel 'smart'.
- name_suggestion: knapp, ohne Slogan, idealerweise <Branche> + <Use-Case>.
- slug_suggestion: name_suggestion in kebab-case.
- Deutschland komplett produziert 800-1500 Calls bei 4 Synonymen. Bundesland ca.
  1/5 davon. Circle mit 30km Radius ca. 10-30.
- Places Pro-Tier kostet 0.032 USD pro Call. Max. 60 Treffer/Call (Text) bzw. 20
  (Nearby)."""


_USER_TEMPLATE = (
    "Zielbeschreibung: {text}\n\n"
    "Erlaubte Google Place Types (nur aus dieser Liste auswaehlen, oder "
    "leeres Array):\n{types}\n\n"
    "Antworte mit dem JSON-Objekt."
)


def _build_prompt(text: str) -> tuple[str, str]:
    types_str = ", ".join(SUPPORTED_PLACE_TYPES)
    return _SYSTEM_PROMPT, _USER_TEMPLATE.format(text=text.strip(), types=types_str)


def _strip_json_fences(raw: str) -> str:
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", raw.strip())
    cleaned = re.sub(r"\n?```\s*$", "", cleaned.strip())
    return cleaned


class LeadgenIntakeService:
    """Turn free-text intent into a validated IntakeSuggestion."""

    def __init__(self, llm: LLMService | None = None) -> None:
        self._llm = llm or LLMService()

    async def suggest(self, text: str) -> IntakeSuggestion:
        system, user = _build_prompt(text)
        try:
            from app.services.llm import get_default_model

            raw = await self._llm.generate_with_config(
                provider="anthropic",
                # Bulk-class — webpage analysis / classification, no DB context here
                model=get_default_model("bulk"),
                system_prompt=system,
                user_prompt=user,
                temperature=0.2,
                max_tokens=3000,
            )
        except ExternalServiceError:
            raise
        except Exception as e:
            logger.exception("Leadgen intake LLM call failed")
            raise ExternalServiceError("Leadgen Intake LLM", str(e)) from e

        cleaned = _strip_json_fences(raw)
        try:
            parsed: dict[str, Any] = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error("Intake LLM returned non-JSON: {raw}", raw=raw[:400])
            raise ExternalServiceError(
                "Leadgen Intake LLM",
                f"Ungueltige JSON-Antwort: {e}",
            ) from e

        # Validate types against whitelist - the LLM sometimes invents types.
        if "nearby_types" in parsed:
            parsed["nearby_types"] = [
                t for t in parsed["nearby_types"] if t in SUPPORTED_PLACE_TYPES
            ]

        # Clamp pipeline_mode to known values; LLM occasionally drifts.
        if parsed.get("pipeline_mode") not in {"smart", "cheap", "legacy"}:
            parsed["pipeline_mode"] = "smart"

        # Trim name/slug to schema limits.
        if isinstance(parsed.get("name_suggestion"), str):
            parsed["name_suggestion"] = parsed["name_suggestion"][:80].strip()
        if isinstance(parsed.get("slug_suggestion"), str):
            parsed["slug_suggestion"] = (
                re.sub(r"[^a-z0-9-]+", "-", parsed["slug_suggestion"].lower())
                .strip("-")[:60]
            )

        try:
            return IntakeSuggestion.model_validate(parsed)
        except Exception as e:  # pydantic ValidationError
            logger.error("Intake LLM response did not match schema: {raw}", raw=raw[:400])
            raise ExternalServiceError(
                "Leadgen Intake LLM",
                f"Antwort passt nicht zum Schema: {e}",
            ) from e
