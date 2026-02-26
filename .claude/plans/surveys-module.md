# Surveys Modul - Implementierungsplan

## Übersicht

Schlankes Umfrage- und Feedback-Modul für KMU-Kunden. Deckt ab:
- Kundenzufriedenheit (CSAT)
- Net Promoter Score (NPS)
- Event-/Service-Feedback
- Mitarbeiter-Feedback (einfach)
- Lead-Qualifizierung

```
┌─────────────────────────────────────────────────────────────────┐
│                       SURVEYS MODUL                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   BUILDER    │    │  VERTEILUNG  │    │  AUSWERTUNG  │      │
│  │              │    │              │    │              │      │
│  │ Drag & Drop  │───▶│ Link / QR    │───▶│ Dashboard    │      │
│  │ Fragetypen   │    │ E-Mail       │    │ NPS Score    │      │
│  │ Logik        │    │ Embed        │    │ Export       │      │
│  │ Branding     │    │ CRM-Kontakte │    │ Charts       │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│                                                                 │
│                         ┌──────────────┐                        │
│                         │  AUTOMATION  │                        │
│                         │              │                        │
│                         │ n8n Webhook  │                        │
│                         │ Follow-up    │                        │
│                         │ Alerts       │                        │
│                         └──────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 1. Datenbank-Modelle

### Neue Tabellen

| Tabelle | Beschreibung |
|---------|-------------|
| `surveys` | Umfrage-Container |
| `survey_questions` | Fragen einer Umfrage |
| `survey_responses` | Antwort-Sessions (ein Teilnehmer) |
| `survey_answers` | Einzelne Antworten pro Frage |

### Survey Model
```python
class Survey(TimestampMixin, Base):
    __tablename__ = "surveys"

    id: int (PK)
    tenant_id: str (FK)
    owner_id: int (FK users)

    # Basics
    title: str
    description: str | None
    slug: str (unique per tenant, für URL)

    # Status
    status: enum (draft, active, paused, closed)

    # Settings
    survey_type: enum (general, nps, csat, feedback)
    anonymous: bool = True
    show_progress: bool = True
    one_response_per_contact: bool = False

    # Branding
    logo_url: str | None
    primary_color: str = "#FF6600"
    background_color: str = "#FFFFFF"

    # Zeitsteuerung
    starts_at: datetime | None
    ends_at: datetime | None

    # Thank you page
    thank_you_title: str = "Vielen Dank!"
    thank_you_message: str | None
    redirect_url: str | None

    # Stats (cached)
    response_count: int = 0
    avg_completion_time: int | None  # Sekunden

    # n8n Integration
    webhook_url: str | None
    webhook_on_complete: bool = False
```

### SurveyQuestion Model
```python
class SurveyQuestion(TimestampMixin, Base):
    __tablename__ = "survey_questions"

    id: int (PK)
    tenant_id: str
    survey_id: int (FK surveys)

    # Position
    position: int
    page: int = 1  # Für mehrseitige Umfragen

    # Frage
    question_type: enum (siehe unten)
    title: str
    description: str | None
    required: bool = False

    # Optionen (für Choice-Fragen)
    options: list[str] | None  # JSONB ["Option A", "Option B"]

    # Einstellungen je nach Typ
    settings: dict  # JSONB
    # Beispiele:
    # - scale: {min: 1, max: 5, min_label: "Schlecht", max_label: "Sehr gut"}
    # - nps: {min_label: "Unwahrscheinlich", max_label: "Sehr wahrscheinlich"}
    # - text: {multiline: true, max_length: 500}

    # Logik (einfach)
    show_if_question_id: int | None  # Zeige nur wenn...
    show_if_value: str | None        # ...diese Antwort gegeben wurde
```

### Question Types
```python
class QuestionType(str, Enum):
    SINGLE_CHOICE = "single_choice"      # Radio Buttons
    MULTIPLE_CHOICE = "multiple_choice"  # Checkboxes
    TEXT = "text"                        # Freitext (kurz)
    TEXTAREA = "textarea"                # Freitext (lang)
    SCALE = "scale"                      # 1-5 oder 1-10 Skala
    NPS = "nps"                          # 0-10 NPS Skala
    YES_NO = "yes_no"                    # Ja/Nein
    RATING = "rating"                    # Sterne (1-5)
```

### SurveyResponse Model
```python
class SurveyResponse(TimestampMixin, Base):
    __tablename__ = "survey_responses"

    id: int (PK)
    tenant_id: str
    survey_id: int (FK surveys)

    # Teilnehmer (optional, bei nicht-anonymen Umfragen)
    contact_id: int | None (FK contacts)
    email: str | None

    # Token für Teilnahme-Link
    token: str (unique)

    # Status
    status: enum (started, completed, abandoned)
    started_at: datetime
    completed_at: datetime | None

    # Meta
    ip_address: str | None
    user_agent: str | None
    duration_seconds: int | None

    # NPS Score (falls NPS-Umfrage)
    nps_score: int | None
```

### SurveyAnswer Model
```python
class SurveyAnswer(TimestampMixin, Base):
    __tablename__ = "survey_answers"

    id: int (PK)
    tenant_id: str
    response_id: int (FK survey_responses)
    question_id: int (FK survey_questions)

    # Antwort (je nach Fragetyp)
    value_text: str | None           # Freitext, Single Choice
    value_number: int | None         # Scale, NPS, Rating
    value_list: list[str] | None     # Multiple Choice (JSONB)
    value_bool: bool | None          # Yes/No
```

---

## 2. API Endpoints

### Surveys (Admin)
```
POST   /v1/surveys                     Umfrage erstellen
GET    /v1/surveys                     Alle Umfragen
GET    /v1/surveys/{id}                Umfrage mit Fragen
PUT    /v1/surveys/{id}                Umfrage bearbeiten
DELETE /v1/surveys/{id}                Umfrage löschen
POST   /v1/surveys/{id}/duplicate      Umfrage duplizieren

PATCH  /v1/surveys/{id}/status         Status ändern (activate/pause/close)
GET    /v1/surveys/{id}/stats          Statistiken
GET    /v1/surveys/{id}/export         Export CSV/PDF
```

### Questions (Admin)
```
POST   /v1/surveys/{id}/questions              Frage hinzufügen
PUT    /v1/surveys/questions/{id}              Frage bearbeiten
DELETE /v1/surveys/questions/{id}              Frage löschen
PATCH  /v1/surveys/{id}/questions/reorder      Reihenfolge ändern
```

### Responses (Admin)
```
GET    /v1/surveys/{id}/responses              Alle Antworten
GET    /v1/surveys/responses/{id}              Einzelne Antwort
DELETE /v1/surveys/responses/{id}              Antwort löschen
```

### Public (Teilnehmer - kein Auth)
```
GET    /v1/surveys/public/{slug}               Umfrage laden (für Teilnahme)
POST   /v1/surveys/public/{slug}/start         Teilnahme starten
POST   /v1/surveys/public/{slug}/answer        Antwort speichern
POST   /v1/surveys/public/{slug}/complete      Abschließen
```

### Distribution
```
GET    /v1/surveys/{id}/share-link             Teilnahme-Link generieren
GET    /v1/surveys/{id}/qr-code                QR-Code als PNG/SVG
POST   /v1/surveys/{id}/send-invites           E-Mails versenden (via n8n)
```

---

## 3. Frontend-Struktur

### Neue Dateien
```
frontend/src/
├── api/surveys.js
├── stores/surveys.js
├── views/
│   ├── SurveysView.vue              # Liste aller Umfragen
│   ├── SurveyBuilderView.vue        # Drag & Drop Builder
│   ├── SurveyResultsView.vue        # Dashboard + Antworten
│   └── SurveyPublicView.vue         # Öffentliche Teilnahme-Seite
└── components/surveys/
    ├── SurveyCard.vue               # Umfrage-Karte für Liste
    ├── QuestionEditor.vue           # Frage bearbeiten
    ├── QuestionPreview.vue          # Frage-Vorschau
    ├── QuestionTypes/
    │   ├── SingleChoice.vue
    │   ├── MultipleChoice.vue
    │   ├── TextInput.vue
    │   ├── ScaleInput.vue
    │   ├── NpsInput.vue
    │   ├── YesNoInput.vue
    │   └── RatingInput.vue
    ├── ResultsChart.vue             # ApexCharts Wrapper
    ├── NpsGauge.vue                 # NPS Anzeige
    └── ShareModal.vue               # Link/QR teilen
```

### Views

**SurveysView** - Übersicht
- Grid mit Umfrage-Cards
- Status-Filter (Entwurf, Aktiv, Beendet)
- Quick-Stats pro Umfrage
- "Neue Umfrage" Button

**SurveyBuilderView** - Editor
- Drag & Drop Fragen-Liste (links)
- Frage-Editor Panel (rechts)
- Live-Vorschau
- Einstellungen-Tab (Branding, Zeitsteuerung)
- Speichern + Aktivieren

**SurveyResultsView** - Auswertung
- Übersicht: Response Count, Completion Rate, Avg. Time
- NPS Score (falls NPS-Umfrage)
- Charts pro Frage
- Antworten-Tabelle mit Filter
- Export-Buttons

**SurveyPublicView** - Teilnahme
- Minimales Design (kein Header/Navigation)
- Branding des Kunden
- Fortschrittsbalken
- Eine Frage pro Seite oder alle
- Thank-You Page

---

## 4. Survey Builder UI

### Drag & Drop Konzept
```
┌─────────────────────────────────────────────────────────────────┐
│  Survey Builder                                    [Vorschau]   │
├────────────────────┬────────────────────────────────────────────┤
│                    │                                            │
│  FRAGEN            │  EDITOR                                    │
│                    │                                            │
│  ┌──────────────┐  │  ┌────────────────────────────────────┐   │
│  │ 1. Wie zufrieden │  │ Fragetyp: [Skala ▼]                │   │
│  │    ≡ ✎ 🗑     │  │                                        │   │
│  └──────────────┘  │  │ Frage: ________________________     │   │
│  ┌──────────────┐  │  │                                        │   │
│  │ 2. Was können │  │  │ Beschreibung: ________________     │   │
│  │    ≡ ✎ 🗑     │  │                                        │   │
│  └──────────────┘  │  │ Skala: [1] bis [5]                  │   │
│  ┌──────────────┐  │  │                                        │   │
│  │ 3. NPS Score  │  │  │ Labels:                              │   │
│  │    ≡ ✎ 🗑     │  │  │ Min: [Schlecht____]                 │   │
│  └──────────────┘  │  │ Max: [Sehr gut____]                  │   │
│                    │  │                                        │   │
│  [+ Frage]         │  │ ☑ Pflichtfeld                        │   │
│                    │  │                                        │   │
│  ──────────────    │  └────────────────────────────────────┘   │
│  FRAGETYPEN        │                                            │
│  ○ Single Choice   │                                            │
│  ○ Multiple Choice │                                            │
│  ○ Freitext        │                                            │
│  ○ Skala           │                                            │
│  ○ NPS             │                                            │
│  ○ Ja/Nein         │                                            │
│  ★ Sterne          │                                            │
│                    │                                            │
└────────────────────┴────────────────────────────────────────────┘
```

---

## 5. NPS Berechnung

```
NPS Score = % Promoter - % Detractor

0-6  = Detractor (Kritiker)
7-8  = Passive (Neutral)
9-10 = Promoter (Befürworter)

Beispiel:
100 Antworten: 50 Promoter, 30 Passive, 20 Detractor
NPS = 50% - 20% = 30

Bewertung:
-100 bis 0   = Schlecht (rot)
0 bis 30     = Okay (gelb)
30 bis 70    = Gut (grün)
70 bis 100   = Exzellent (dunkelgrün)
```

---

## 6. n8n Integration

### Webhook Payload (bei Abschluss)
```json
{
  "event": "survey.response.completed",
  "survey_id": 123,
  "survey_title": "Kundenzufriedenheit Q1",
  "response_id": 456,
  "completed_at": "2024-01-15T14:30:00Z",
  "contact": {
    "id": 789,
    "email": "kunde@firma.de",
    "name": "Max Mustermann"
  },
  "answers": [
    {"question": "Wie zufrieden sind Sie?", "value": 4},
    {"question": "Was können wir verbessern?", "value": "Schnellere Lieferung"}
  ],
  "nps_score": 8,
  "nps_category": "passive"
}
```

### Automatisierungen (Beispiele)
- **Negatives Feedback Alert**: Bei NPS < 7 → E-Mail an Support
- **Follow-up**: Nach Abschluss → Dankes-E-Mail senden
- **CRM Update**: Antworten als Aktivität beim Kontakt loggen
- **Slack/Teams**: Benachrichtigung bei neuer Antwort

---

## 7. Dateien zu erstellen

### Backend
```
backend/app/surveys/
├── __init__.py
├── __manifest__.py
├── models.py           # 4 Models
├── schemas.py          # CRUD + Public Schemas
├── service.py          # SurveyService, ResponseService
├── router.py           # Admin Endpoints
├── public_router.py    # Öffentliche Teilnahme (kein Auth)
├── stats.py            # NPS Berechnung, Statistiken
└── export.py           # CSV/PDF Export

backend/alembic/versions/
└── 026_surveys_module.py
```

### Frontend
```
frontend/src/
├── api/surveys.js
├── stores/surveys.js
├── views/
│   ├── SurveysView.vue
│   ├── SurveyBuilderView.vue
│   ├── SurveyResultsView.vue
│   └── SurveyPublicView.vue
└── components/surveys/
    └── ... (siehe oben)
```

---

## 8. Implementierungsreihenfolge

### Phase 1: Core Backend (Tag 1)
1. Migration erstellen
2. Models implementieren
3. Schemas definieren
4. Basic CRUD Service
5. Admin Router

### Phase 2: Public API (Tag 1-2)
1. Public Router (kein Auth)
2. Teilnahme-Flow (start → answer → complete)
3. Token-basierte Identifikation

### Phase 3: Builder Frontend (Tag 2)
1. API Client + Store
2. SurveysView (Liste)
3. SurveyBuilderView (Drag & Drop)
4. Question-Komponenten

### Phase 4: Teilnahme Frontend (Tag 3)
1. SurveyPublicView
2. Question-Input-Komponenten
3. Branding/Theming
4. Mobile-optimiert

### Phase 5: Auswertung (Tag 3-4)
1. Stats-Service (NPS, Completion Rate)
2. SurveyResultsView
3. Charts mit ApexCharts
4. Export CSV/PDF

### Phase 6: Integration (Tag 4)
1. n8n Webhook
2. CRM-Verknüpfung (Contact → Response)
3. QR-Code Generierung
4. E-Mail-Versand Setup

---

## 9. Verifikation

### Checkliste
- [ ] Umfrage erstellen mit allen Fragetypen
- [ ] Drag & Drop Reihenfolge ändern
- [ ] Umfrage aktivieren
- [ ] Öffentlicher Link funktioniert
- [ ] QR-Code generieren
- [ ] Antworten speichern
- [ ] NPS-Score berechnet
- [ ] Dashboard zeigt Charts
- [ ] Export CSV funktioniert
- [ ] n8n Webhook wird ausgelöst
- [ ] Mobile Teilnahme funktioniert
