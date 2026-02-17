# Roadmap

## Phase 1: Foundation (✅ Abgeschlossen – Februar 2026)

### Ziel
Projektstruktur, Technologie-Entscheidungen, Dokumentation, Meta-API-Zugang.

### Erledigt
- [x] Tech-Stack definiert (FastAPI, Vue 3, PostgreSQL, n8n, Docker)
- [x] Projektstruktur festgelegt (Multi-Tenant, Domain-basiert)
- [x] Coding-Standards dokumentiert (CLAUDE.md, .claude/rules)
- [x] Meta Business Manager eingerichtet
- [x] Meta Developer App erstellt (go4-marketing-automation)
- [x] System User + Token generiert
- [x] Facebook Page API-Zugriff verifiziert
- [x] Vollständige Projektdokumentation erstellt
- [x] Datenbank-Schema entworfen
- [x] Claude Code Prompts für Module 1+2 erstellt

### Offen
- [ ] Instagram-Login Problem lösen (alte E-Mail blockiert Zugang)
- [ ] Instagram mit Facebook Page verknüpfen (im Business Manager)
- [ ] Meta Pixel erstellen
- [ ] Ad Account ID dokumentieren

---

## Phase 2: Content-Pipeline (🔨 In Entwicklung – Feb/März 2026)

### Ziel
Automatische Content-Generierung und Veröffentlichung auf Facebook (Instagram folgt).

### Tasks
- [ ] Backend: Content-Modul (models, schemas, service, router)
- [ ] Backend: LLM Service (Python, Anthropic SDK)
- [ ] Backend: Meta Client (Facebook Page Posting)
- [ ] Alembic Migration (neue Felder content_queue)
- [ ] Frontend: Content-Dashboard (Liste, Filter, Status-Badges)
- [ ] Frontend: Content-Editor (Textarea, Zeichenzähler, Vorschau)
- [ ] n8n: Workflow 01 – Tägliche Content-Generierung
- [ ] n8n: Workflow – Scheduled Publishing (alle 15 Min)
- [ ] n8n: Workflow – Engagement Tracking (täglich)
- [ ] Tests: Service + Router
- [ ] Erster echter Post über das System veröffentlichen

### Meilenstein
**Erster automatisch generierter und veröffentlichter Facebook-Post** über die Pipeline.

---

## Phase 3: Ad-Management (🔨 In Entwicklung – März/April 2026)

### Ziel
Meta Pixel + Conversion API, automatische Budget-Optimierung mit Wetter-Boost.

### Tasks
- [ ] Backend: Ads-Modul (models, schemas, service, router)
- [ ] Backend: Meta Ads Client (Marketing API + Conversion API)
- [ ] Backend: Weather Service (OpenWeather)
- [ ] Backend: Optimizer Engine (Budget-Regeln)
- [ ] Backend: Hashing Utility (SHA256 für Meta CAPI)
- [ ] Backend: Pixel Snippet Generator
- [ ] Alembic Migration (ad_campaign_configs, conversion_events)
- [ ] Frontend: Ad-Dashboard (KPIs, Chart, Kampagnen-Tabelle)
- [ ] Frontend: Weather Widget + Boost-Indikator
- [ ] Frontend: Campaign Config Editor
- [ ] n8n: Workflow – Tägliche Ad-Optimierung
- [ ] n8n: Workflow – Performance-Sync (alle 4h)
- [ ] n8n: Workflow – Wöchentlicher KI-Report
- [ ] Meta Pixel auf go4.energy Website installieren
- [ ] Erste echte Kampagne über das System optimieren

### Meilenstein
**Erste automatische Budget-Anpassung** basierend auf CPL + Wetter.

---

## Phase 4: Server & Deployment (📋 Geplant – April 2026)

### Ziel
Produktionssystem auf Hetzner VPS, HTTPS, Backups, Monitoring.

### Tasks
- [ ] Hetzner CX31 VPS bestellen
- [ ] Ubuntu 24.04 + Docker installieren
- [ ] Caddy 2 konfigurieren (Auto-HTTPS)
- [ ] Docker Compose für Production anpassen
- [ ] DNS: automate.go4.energy → Server-IP
- [ ] PostgreSQL Backup-Cronjob (täglich 3:00)
- [ ] Firewall (UFW) + Fail2ban
- [ ] Monitoring (Uptime, Disk, Memory) – einfaches Script oder Uptime Kuma
- [ ] CI/CD: GitHub Actions → Docker Build → Deploy
- [ ] Deployment-Dokumentation (Runbook)

### Meilenstein
**System ist 24/7 erreichbar** unter automate.go4.energy.

---

## Phase 5: Lead-Nurturing (📋 Geplant – Mai/Juni 2026)

### Ziel
Automatische 6-stufige Follow-up-Sequenz für eingehende Leads.

### Tasks
- [ ] Backend: Leads-Modul erweitern (Follow-up-Status, Sequenz-Tracking)
- [ ] Backend: E-Mail Service (Brevo SMTP)
- [ ] Backend: Lead-Scoring Service (LLM-basiert)
- [ ] E-Mail Templates erstellen (6 Stufen, HTML)
- [ ] n8n: Workflow – Follow-up-Sequenz (Tag 0, 1, 3, 5, 7, 10)
- [ ] n8n: Workflow – Lead-Scoring bei Eingang
- [ ] Frontend: Lead-Dashboard (Liste, Score, Status, Timeline)
- [ ] Konfigurator-Webhook einrichten (Leads automatisch erfassen)
- [ ] SMS/WhatsApp Anbindung evaluieren

### Meilenstein
**Erste vollständige Follow-up-Sequenz** durchgelaufen mit echtem Lead.

---

## Phase 6: Reporting & Analytics (📋 Geplant – Juni/Juli 2026)

### Ziel
Automatisierte Reports und übergreifendes Analytics-Dashboard.

### Tasks
- [ ] Backend: Reporting Service (Daten aggregieren)
- [ ] LLM-basierte Report-Generierung (wöchentlich/monatlich)
- [ ] PDF-Report-Generator für Kunden
- [ ] Frontend: Analytics-Dashboard (Gesamt-Übersicht)
- [ ] Frontend: ROI-Rechner (Werbekosten vs. geschätzte Aufträge)
- [ ] n8n: Workflow – Wöchentlicher Report (E-Mail)
- [ ] n8n: Workflow – Monatlicher PDF-Report

### Meilenstein
**Erster automatischer Monatsreport** als PDF an Kunden versendet.

---

## Phase 7: Produktisierung (📋 Geplant – Q3/Q4 2026)

### Ziel
System verkaufsfähig machen: Onboarding, Billing, White-Label.

### Tasks
- [ ] Onboarding-Wizard: Neuer Tenant in 15 Minuten einrichten
- [ ] Self-Service Setup: Meta-Verknüpfung über OAuth Flow
- [ ] Multi-User: Login-System mit Rollen (Admin, Editor, Viewer)
- [ ] Billing-Integration (Stripe)
- [ ] White-Label: Logo, Farben, Domain pro Tenant/Agentur
- [ ] Landing Page für Produktverkauf
- [ ] Demo-Tenant mit Beispieldaten
- [ ] SLA-Dokumentation
- [ ] DSGVO-Dokumentation (Auftragsverarbeitung, Datenschutzerklärung)
- [ ] 2-3 Beta-Kunden aus PV-Branche gewinnen

### Meilenstein
**Erster zahlender Kunde** nutzt die Plattform produktiv.

---

## Zukünftige Ideen (2027+)

- **Echte Agent-Fähigkeiten:** System lernt aus Engagement-Daten und passt Content-Strategie automatisch an
- **Bild-Generierung:** DALL-E oder Midjourney-Integration für automatische Post-Bilder
- **Video-Content:** Automatische Reel-Scripts + Voiceover
- **Google Ads Integration:** Neben Meta auch Google Ads automatisiert verwalten
- **CRM-Integrationen:** HubSpot, Pipedrive, Zoho – bidirektionale Sync
- **Mehrsprachigkeit:** Content in DE, EN, FR, IT automatisch erstellen
- **Marketplace:** Kunden können Templates/Prompts untereinander teilen
- **Mobile App:** Push-Notifications für Content-Freigabe
