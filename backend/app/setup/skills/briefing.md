# Briefing

## Beschreibung
Internes Briefing-Modul: Eigene Quellen sammeln, per KI aufbereiten und als Text- oder Audio-Briefing an interne Zielgruppen verteilen. Komplett isoliert von der Marketing-Pipeline (Collector → Creator → Distributor).

## Konfigurierbare Parameter
| Parameter | Beschreibung | Typ | Beispiel | Default |
|-----------|-------------|-----|---------|---------|
| LLM_MODEL_BRIEFING | LLM-Provider fuer Scripts | enum | anthropic, ollama | anthropic |
| OLLAMA_URL | Ollama Server URL | string | http://localhost:11434 | http://localhost:11434 |
| OLLAMA_MODEL | Ollama Modell | string | mistral | mistral |
| TTS_ENGINE | TTS-Engine | enum | piper, disabled | piper |
| TTS_URL | Piper Server URL | string | http://remote:10200 | http://localhost:10200 |
| BRIEFING_AUDIO_DIR | Audio-Speicherort | string | uploads/briefing | uploads/briefing |
| JWT_SECRET | JWT-Secret fuer Listener-Auth | string | - | change-me-in-production |
| JWT_EXPIRY_HOURS | Token-Gueltigkeitsdauer | int | 720 | 720 |
| LISTENER_SELF_REGISTRATION | Selbstregistrierung erlauben | bool | true | true |

## Verfuegbare Tools
- `get_current_config` — Aktuelle Briefing-Konfiguration lesen
- `update_tenant_config` — Briefing-Parameter aktualisieren
- `check_integration_status` — TTS- und LLM-Verfuegbarkeit pruefen

## Workflow
1. **Channel erstellen**: Admin legt Channel mit Zielgruppe, Kategorien und Stimme an
2. **Episode generieren**: Findings werden per LLM zu Sprechtext zusammengefasst
3. **TTS**: Sprechtext wird per Piper in Audio umgewandelt
4. **Listener**: Mitarbeiter hoeren Episoden ueber die PWA oder Podcast-Apps
5. **Feedback**: Listener bewerten Inhalte → Personalisierung verbessert sich

## Typische Fragen fuer den Benutzer
1. Welche Zielgruppen sollen Briefings erhalten? (Management, Pflege, IT, etc.)
2. Wie oft sollen Briefings generiert werden? (taeglich, woechentlich)
3. Soll TTS aktiviert werden oder nur Text-Transkripte?
4. Soll die Selbstregistrierung fuer Listener erlaubt sein?
5. Welche Briefing-Quellen sind fuer welche Zielgruppe relevant?

## Branchenspezifische Empfehlungen
- **Krankenhaus**: Separate Channels fuer Management, Pflege, IT. Taeglich morgens 06:00.
- **Behoerde**: Channels nach Abteilung. Woechentlich montags.
- **Unternehmen**: Channels nach Rolle (GF, Vertrieb, Technik). Taeglich Mo-Fr 07:00.
- **Allgemein**: 1 allgemeiner Channel zum Start, dann nach Feedback aufteilen.
