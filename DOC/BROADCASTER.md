# Broadcaster — Ihr persoenlicher Nachrichtensprecher

## Vision

Stellen Sie sich vor: Jeden Morgen auf dem Arbeitsweg erhalten Sie ein massgeschneidertes Audio-Briefing — genau die Informationen, die fuer Ihre Rolle relevant sind. Kein Scrollen, kein Lesen, kein Suchen. Einfach zuhoeren.

**Broadcaster** verwandelt Ihre gesammelten Informationen automatisch in professionelle Audio-Briefings — personalisiert fuer jede Zielgruppe in Ihrem Unternehmen.

## Problem

- Mitarbeiter haben keine Zeit, taeglich Branchennews, interne Updates und E-Mails zu lesen
- Wichtige Informationen gehen im Tagesgeschaeft unter
- Jede Abteilung braucht andere Informationen
- Bestehende Newsletter werden nicht gelesen (Oeffnungsrate < 20%)

## Loesung

```
Collector-Findings + Interne Daten
         │
         ▼
    ┌─────────┐
    │   LLM   │  Script generieren
    └────┬────┘
         │
         ▼
    ┌─────────┐
    │   TTS   │  Text-to-Speech
    └────┬────┘
         │
         ▼
    ┌─────────┐
    │  Audio  │  WAV/MP3 Datei
    └────┬────┘
         │
         ▼
    ┌─────────┐
    │  PWA    │  Hoeren auf jedem Geraet
    └─────────┘
```

## Zielgruppen-Beispiele

### Krankenhaus
- **Management-Briefing**: Gesundheitspolitik, Foerderungen, Wettbewerber
- **Pflege-Briefing**: Neue Leitlinien, Fortbildungen, Personalthemen
- **IT-Briefing**: Cybersecurity, eHealth-Trends, Datenschutz

### Behoerde
- **Amtsleitung**: Gesetzesaenderungen, Digitalisierung, Best Practices
- **Sachbearbeiter**: Verfahrensaenderungen, neue Formulare, IT-Updates

### Unternehmen (z.B. Energiebranche)
- **Geschaeftsfuehrung**: Marktentwicklung, Regulierung, Wettbewerb
- **Vertrieb**: Neue Produkte, Kundenfeedback, Preisaenderungen
- **Technik**: Normen, Innovationen, Lieferkettenthemen

## Channel-Konzept

### Team-Channels (Zielgruppen-Briefings)
- Admin erstellt Channel mit Kategoriefilter
- Alle Abonnenten hoeren dasselbe Briefing
- Beispiel: "Management Briefing" filtert auf `social_media` + `competitor`

### Persoenliche Briefings (Phase 2)
- Integration persoenlicher Daten via n8n-Webhook
- Kalendertermine, wichtige E-Mails, individuelle RSS-Feeds
- Jeder Listener hoert ein einzigartiges Briefing

## Feedback-Loop

```
Listener hoert Episode
       │
       ▼
  Daumen hoch / runter
       │
       ▼
  Preferences werden gelernt
       │
       ▼
  Naechste Episode ist besser zugeschnitten
```

- `interesting` → Mehr von diesem Thema
- `irrelevant` → Weniger von diesem Thema
- `more` → Ausfuehrlicher berichten
- Algorithmus lernt Kategorie- und Keyword-Gewichte pro User

## Technische Architektur

```
┌─────────────────────────────────────────────────────────────────┐
│                    go4-automate Server                          │
│                                                                 │
│  ┌──────────────┐    ┌──────────────────────────────────────┐   │
│  │   Admin UI    │    │         Backend (FastAPI)             │   │
│  │  (frontend/)  │───▶│                                      │   │
│  │  Port 5173    │    │  /api/v1/broadcaster/*  (Admin-API)  │   │
│  └──────────────┘    │  /api/v1/listen/*       (Listener-API)│   │
│                      │  Port 8001                            │   │
│  ┌──────────────┐    │                                      │   │
│  │ Listener PWA │───▶│  ┌────────┐ ┌─────┐ ┌────────────┐  │   │
│  │  (listener/) │    │  │Ollama/ │ │Piper│ │ PostgreSQL │  │   │
│  │  Port 5174   │    │  │Anthro. │ │ TTS │ │   Redis    │  │   │
│  └──────────────┘    │  └────────┘ └─────┘ └────────────┘  │   │
│                      └──────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Baukastenprinzip — Alles austauschbar

| Komponente | Aktuell | Alternative |
|-----------|---------|-------------|
| LLM | Anthropic Claude | Ollama (lokal) |
| TTS | Piper (Remote) | Edge TTS, Bark |
| Listener | PWA | Native App, Podcast-App |
| Audio | WAV | MP3, OGG |

## Datenschutz

- **100% On-Premise**: Kein Byte verlaesst den Server (bei Ollama + Piper)
- **DSGVO-konform**: Alle Daten bleiben im Unternehmensnetzwerk
- **Kein Cloud-Zwang**: LLM und TTS koennen vollstaendig lokal laufen
- **Nutzerdaten**: Nur E-Mail + Praeferenzen, keine Tracking-Cookies

## Onboarding-Flow

```
1. Admin erstellt Channel im Dashboard     (30 Sekunden)
2. QR-Code wird generiert                  (automatisch)
3. Mitarbeiter scannt QR-Code              (5 Sekunden)
4. PWA oeffnet sich, Registrierung         (20 Sekunden)
5. Channel abonnieren, erste Episode hoeren (5 Sekunden)
```

**Gesamtzeit: 1 Minute vom QR-Code zum ersten Briefing.**

## RSS/Podcast-Kompatibilitaet

Jeder Channel generiert einen Standard-RSS-Feed mit iTunes Podcast Namespace.
Das bedeutet: Episoden koennen auch in jeder Podcast-App gehoert werden
(Apple Podcasts, Spotify, Google Podcasts, etc.).

## Roadmap

- [x] Phase 1: Channel CRUD + Episode-Generierung + Admin UI
- [x] Phase 2: Listener PWA + Auth + Subscriptions + Feedback
- [ ] Phase 3: Persoenliche Briefings (n8n-Webhooks, Kalender, E-Mail)
- [ ] Phase 4: Ollama + Piper On-Premise (kein externer API-Call)
- [ ] Phase 5: Multi-Tenant + White-Label
