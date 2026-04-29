<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { marked } from 'marked'
import { useLinkedInStore } from '@/stores/linkedin'
import api from '@/api'

// Configure marked for better rendering with heading IDs
marked.use({
  breaks: true,
  gfm: true,
  hooks: {
    postprocess(html) {
      // Add IDs to headings for anchor links
      return html.replace(/<h([1-6])>([^<]+)<\/h[1-6]>/g, (match, level, text) => {
        const slug = text
          .toLowerCase()
          .replace(/[äöüß]/g, (c) => ({ ä: 'ae', ö: 'oe', ü: 'ue', ß: 'ss' })[c] || c)
          .replace(/[^\w\s-]/g, '')
          .replace(/\s+/g, '-')
          .replace(/-+/g, '-')
          .trim()
        return `<h${level} id="${slug}">${text}</h${level}>`
      })
    }
  }
})
import { useFunnelsStore } from '@/stores/funnels'
import PageHeader from '@/components/ui/PageHeader.vue'
import SearchInput from '@/components/ui/SearchInput.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import PipelineCampaignsList from '@/components/engagement/PipelineCampaignsList.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import ModuleSetupTab from '@/components/ai/ModuleSetupTab.vue'
import SafetyLimitsModal from '@/components/linkedin/SafetyLimitsModal.vue'
import ProfileCard from '@/components/linkedin/ProfileCard.vue'

const router = useRouter()
const route = useRoute()
const store = useLinkedInStore()
const funnelsStore = useFunnelsStore()

// Read active tab from route meta
const activeTab = computed(() => route.meta?.tab || 'dashboard')

const searchQuery = ref('')
const statusFilter = ref('')
const showDeleteAccountConfirm = ref(false)
const showDeleteJobConfirm = ref(false)
const showDeleteTemplateConfirm = ref(false)
const showDeleteCampaignConfirm = ref(false)
const showDeleteContactConfirm = ref(false)
const showDeleteAllContactsConfirm = ref(false)
const contactToDelete = ref(null)
const showSafetyLimits = ref(false)
const schedulerStatus = ref([])
const schedulerLoading = ref(false)
const accountToDelete = ref(null)
const jobToDelete = ref(null)
const templateToDelete = ref(null)
const campaignToDelete = ref(null)

// === Profile Scraper Test ===
const scrapeUrl = ref('')
const scrapeLoading = ref(false)
const scrapeError = ref(null)
const scrapeResult = ref(null)

async function startScrapeTest() {
  if (!scrapeUrl.value.trim() || scrapeLoading.value) return
  scrapeLoading.value = true
  scrapeError.value = null
  scrapeResult.value = null
  try {
    const { data } = await api.post('/v1/linkedin/debug/scrape-profile', {
      url: scrapeUrl.value.trim()
    })
    if (data.success) {
      scrapeResult.value = data
    } else {
      scrapeError.value = data.error || 'Unbekannter Fehler'
      if (data.traceback) {
        scrapeError.value += '\n\n' + data.traceback
      }
    }
  } catch (err) {
    scrapeError.value = err.response?.data?.detail || err.message
  } finally {
    scrapeLoading.value = false
  }
}

// === Debug Tab State ===
const debugActive = ref(false)
const debugCurrentStep = ref(null)
const debugLogs = ref([])
const debugAutostart = ref(false)
const debugAutoDelay = ref(2000)
const debugAutoCountdown = ref(0)
const debugFinished = ref(null)
const debugLogContainer = ref(null)
let debugWs = null
let debugAutoTimer = null

function formatTime(isoStr) {
  if (!isoStr) return ''
  const d = new Date(isoStr)
  return d.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function addDebugLog(level, message, timestamp) {
  const levelTags = { info: '[INFO]', ok: '[ OK ]', warning: '[WARN]', error: '[ERR ]', debug: '[DBG ]', step: '[STEP]' }
  debugLogs.value.push({
    level,
    levelTag: levelTags[level] || `[${level.toUpperCase()}]`,
    message,
    time: formatTime(timestamp || new Date().toISOString()),
  })
  nextTick(() => {
    if (debugLogContainer.value) {
      debugLogContainer.value.scrollTop = debugLogContainer.value.scrollHeight
    }
  })
}

function toggleDebug() {
  if (debugActive.value) {
    stopDebug()
  } else {
    startDebug()
  }
}

function startDebug() {
  debugFinished.value = null
  debugCurrentStep.value = null
  debugLogs.value = []

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const apiBase = import.meta.env.VITE_API_URL || 'http://192.168.1.227:8002/api/v1'
  const host = new URL(apiBase).host
  const wsUrl = `${protocol}//${host}/api/v1/linkedin/debug/ws`

  addDebugLog('info', 'Verbinde...')
  debugWs = new WebSocket(wsUrl)

  debugWs.onopen = () => {
    debugActive.value = true
    addDebugLog('ok', 'Debug-Modus aktiviert — starte einen Job im Jobs-Tab')
  }

  debugWs.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data)

      if (msg.type === 'step') {
        debugCurrentStep.value = msg
        addDebugLog('step', `▶ ${msg.description}${msg.details ? ' — ' + msg.details : ''}`, msg.timestamp)
        if (debugAutostart.value) {
          startAutoApprove()
        }
      } else if (msg.type === 'log') {
        addDebugLog(msg.level, msg.message, msg.timestamp)
      } else if (msg.type === 'status') {
        addDebugLog('info', msg.message, msg.timestamp)
      } else if (msg.type === 'finished') {
        debugFinished.value = msg
        debugCurrentStep.value = null
        cancelAutoApprove()
        addDebugLog(msg.status === 'completed' ? 'ok' : 'error',
          `Job beendet: ${msg.status}${msg.message ? ' — ' + msg.message : ''}`)
        addDebugLog('info', 'Warte auf nächsten Job...')
      }
    } catch (e) {
      addDebugLog('error', `Parse-Fehler: ${e.message}`)
    }
  }

  debugWs.onclose = () => {
    debugActive.value = false
    addDebugLog('warning', 'Debug-Modus deaktiviert')
  }

  debugWs.onerror = () => {
    addDebugLog('error', 'WebSocket-Fehler')
  }
}

function stopDebug() {
  cancelAutoApprove()
  if (debugWs) {
    if (debugWs.readyState === WebSocket.OPEN) {
      debugWs.send(JSON.stringify({ action: 'cancel' }))
    }
    debugWs.close()
    debugWs = null
  }
  debugActive.value = false
  debugCurrentStep.value = null
}

function approveStep() {
  cancelAutoApprove()
  if (debugWs && debugWs.readyState === WebSocket.OPEN) {
    debugWs.send(JSON.stringify({ action: 'continue' }))
    debugCurrentStep.value = null
  }
}

function startAutoApprove() {
  cancelAutoApprove()
  debugAutoCountdown.value = debugAutoDelay.value
  const interval = 100
  debugAutoTimer = setInterval(() => {
    debugAutoCountdown.value -= interval
    if (debugAutoCountdown.value <= 0) {
      cancelAutoApprove()
      approveStep()
    }
  }, interval)
}

function cancelAutoApprove() {
  if (debugAutoTimer) {
    clearInterval(debugAutoTimer)
    debugAutoTimer = null
  }
  debugAutoCountdown.value = 0
}

onUnmounted(() => {
  if (debugWs) {
    debugWs.close()
    debugWs = null
  }
  cancelAutoApprove()
})

const tabs = [
  { key: 'dashboard', label: 'Dashboard', route: '/linkedin/dashboard' },
  { key: 'accounts', label: 'Accounts', route: '/linkedin/accounts' },
  { key: 'jobs', label: 'Scraper Jobs', route: '/linkedin/jobs' },
  { key: 'contacts', label: 'Kontakte', route: '/linkedin/contacts' },
  { key: 'templates', label: 'Vorlagen', route: '/linkedin/templates' },
  { key: 'campaigns', label: 'Kampagnen', route: '/linkedin/campaigns' },
  { key: 'inbox', label: 'Inbox', route: '/linkedin/inbox' },
  { key: 'freigabe', label: 'Freigabe', route: '/linkedin/freigabe' },
  { key: 'guide', label: 'Anleitung', route: '/linkedin/guide' },
  { key: 'setup', label: 'Setup', route: '/linkedin/setup' },
  { key: 'debug', label: 'Debug', route: '/linkedin/debug' }
]

const statusColors = {
  inactive: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
  active: 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300',
  suspended: 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300',
  rate_limited: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-300',
  draft: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
  queued: 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300',
  running: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300',
  paused: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-300',
  completed: 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300',
  failed: 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300',
  cancelled: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
  scraped: 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300',
  imported: 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300',
  skipped: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
  // Connection statuses
  pending: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-300',
  accepted: 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300',
  declined: 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300',
  withdrawn: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
  // Message statuses
  sent: 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300',
  delivered: 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300',
  read: 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300',
  replied: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300'
}

const statusLabels = {
  inactive: 'Inaktiv',
  active: 'Aktiv',
  suspended: 'Gesperrt',
  rate_limited: 'Rate-Limit',
  draft: 'Entwurf',
  queued: 'In Warteschlange',
  running: 'Laeuft',
  paused: 'Pausiert',
  completed: 'Abgeschlossen',
  failed: 'Fehlgeschlagen',
  cancelled: 'Abgebrochen',
  scraped: 'Gescraped',
  imported: 'Importiert',
  skipped: 'Uebersprungen',
  // Connection statuses
  pending: 'Ausstehend',
  accepted: 'Angenommen',
  declined: 'Abgelehnt',
  withdrawn: 'Zurueckgezogen',
  // Message statuses
  sent: 'Gesendet',
  delivered: 'Zugestellt',
  read: 'Gelesen',
  replied: 'Beantwortet'
}

// Template types
const templateTypes = {
  connection_note: 'Kontaktanfrage',
  message: 'Nachricht',
  follow_up: 'Follow-up',
  inmail: 'InMail'
}

const filteredAccounts = computed(() => {
  let result = store.accounts
  if (statusFilter.value) {
    result = result.filter((a) => a.status === statusFilter.value)
  }
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    result = result.filter(
      (a) => a.name.toLowerCase().includes(q) || a.email.toLowerCase().includes(q)
    )
  }
  return result
})

const filteredJobs = computed(() => {
  let result = store.jobs
  if (statusFilter.value) {
    result = result.filter((j) => j.status === statusFilter.value)
  }
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    result = result.filter((j) => j.name.toLowerCase().includes(q))
  }
  return result
})

const degreeFilter = ref(null)

const filteredContacts = computed(() => {
  let result = store.contacts
  if (degreeFilter.value) {
    result = result.filter((c) => c.contact_degree === degreeFilter.value)
  }
  if (statusFilter.value) {
    result = result.filter((c) => c.status === statusFilter.value)
  }
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    result = result.filter(
      (c) =>
        c.name.toLowerCase().includes(q) ||
        c.company_name?.toLowerCase().includes(q) ||
        c.headline?.toLowerCase().includes(q)
    )
  }
  return result
})

const contactDegreeStats = computed(() => {
  const all = store.contacts
  return {
    total: all.length,
    first: all.filter((c) => c.contact_degree === 1).length,
    second: all.filter((c) => c.contact_degree === 2).length,
    third: all.filter((c) => c.contact_degree === 3).length
  }
})

const filteredTemplates = computed(() => {
  let result = store.templates
  if (statusFilter.value) {
    result = result.filter((t) => t.type === statusFilter.value)
  }
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    result = result.filter(
      (t) => t.name.toLowerCase().includes(q) || t.content?.toLowerCase().includes(q)
    )
  }
  return result
})

const filteredCampaigns = computed(() => {
  let result = store.campaigns
  if (statusFilter.value) {
    result = result.filter((c) => c.status === statusFilter.value)
  }
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    result = result.filter((c) => c.name.toLowerCase().includes(q))
  }
  return result
})

const filteredInbox = computed(() => {
  let result = store.inbox
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    result = result.filter(
      (m) => m.contact_name?.toLowerCase().includes(q) || m.last_message?.toLowerCase().includes(q)
    )
  }
  return result
})

const renderedGuide = computed(() => {
  return marked(guideContent)
})

async function fetchSchedulerStatus() {
  try {
    schedulerLoading.value = true
    const { data } = await api.get('/linkedin/scheduler/status')
    schedulerStatus.value = data
  } catch {
    // Scheduler status is optional
  } finally {
    schedulerLoading.value = false
  }
}

const scheduledJobs = computed(() => schedulerStatus.value.filter((s) => s.in_schedule_window))

const dayNames = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']

function formatScheduleDays(days) {
  if (!days || days.length === 0) return 'Keine Tage'
  if (days.length === 7) return 'Jeden Tag'
  if (JSON.stringify(days) === JSON.stringify([0, 1, 2, 3, 4])) return 'Mo-Fr'
  return days.map((d) => dayNames[d]).join(', ')
}

onMounted(async () => {
  await Promise.all([
    store.fetchStats(),
    store.fetchAccounts(),
    store.fetchJobs(),
    store.fetchAllContacts(),
    store.fetchTemplates(),
    store.fetchCampaigns(),
    store.fetchInbox(),
    store.fetchEngagementActions(),
    funnelsStore.fetchFunnels(),
    fetchSchedulerStatus()
  ])
})

function createAccount() {
  router.push('/linkedin/accounts/new')
}

function editAccount(account) {
  router.push(`/linkedin/accounts/${account.id}/edit`)
}

function confirmDeleteAccount(account) {
  accountToDelete.value = account
  showDeleteAccountConfirm.value = true
}

async function deleteAccount() {
  if (!accountToDelete.value) return
  try {
    await store.removeAccount(accountToDelete.value.id)
    showDeleteAccountConfirm.value = false
    accountToDelete.value = null
  } catch {
    // Error in store
  }
}

function createJob() {
  router.push('/linkedin/jobs/new')
}

function createFirstDegreeJob() {
  router.push('/linkedin/jobs/new?preset=1st-degree')
}

function openJob(job) {
  router.push(`/linkedin/jobs/${job.id}`)
}

function editJob(job) {
  router.push(`/linkedin/jobs/${job.id}/edit`)
}

function confirmDeleteJob(job) {
  jobToDelete.value = job
  showDeleteJobConfirm.value = true
}

async function deleteJob() {
  if (!jobToDelete.value) return
  try {
    await store.removeJob(jobToDelete.value.id)
    showDeleteJobConfirm.value = false
    jobToDelete.value = null
  } catch {
    // Error in store
  }
}

async function startJob(job) {
  await store.runJob(job.id)
}

async function pauseJob(job) {
  await store.stopJob(job.id)
}

function openContact(contact) {
  router.push(`/linkedin/contacts/${contact.id}`)
}

function confirmDeleteContact(contact) {
  contactToDelete.value = contact
  showDeleteContactConfirm.value = true
}

async function deleteContactNow() {
  if (!contactToDelete.value) return
  try {
    await store.removeContact(contactToDelete.value.id)
    showDeleteContactConfirm.value = false
    contactToDelete.value = null
  } catch {
    // Error in store
  }
}

async function deleteAllContacts() {
  const ids = filteredContacts.value.map((c) => c.id)
  if (!ids.length) return
  try {
    await store.removeContactsBulk(ids)
    showDeleteAllContactsConfirm.value = false
  } catch {
    // Error in store
  }
}

// ============== Templates ==============

function createTemplate() {
  router.push('/linkedin/templates/new')
}

function editTemplate(template) {
  router.push(`/linkedin/templates/${template.id}/edit`)
}

function confirmDeleteTemplate(template) {
  templateToDelete.value = template
  showDeleteTemplateConfirm.value = true
}

async function deleteTemplate() {
  if (!templateToDelete.value) return
  try {
    await store.removeTemplate(templateToDelete.value.id)
    showDeleteTemplateConfirm.value = false
    templateToDelete.value = null
  } catch {
    // Error in store
  }
}

// ============== Campaigns ==============

function createCampaign() {
  router.push('/linkedin/campaigns/new')
}

function openCampaign(campaign) {
  router.push(`/linkedin/campaigns/${campaign.id}`)
}

function editCampaign(campaign) {
  router.push(`/linkedin/campaigns/${campaign.id}/edit`)
}

function confirmDeleteCampaign(campaign) {
  campaignToDelete.value = campaign
  showDeleteCampaignConfirm.value = true
}

async function deleteCampaign() {
  if (!campaignToDelete.value) return
  try {
    await store.removeCampaign(campaignToDelete.value.id)
    showDeleteCampaignConfirm.value = false
    campaignToDelete.value = null
  } catch {
    // Error in store
  }
}

async function startCampaign(campaign) {
  await store.runCampaign(campaign.id)
}

async function pauseCampaign(campaign) {
  await store.stopCampaign(campaign.id)
}

// ============== Engagement Brain Functions ==============

async function loadEngagementActions() {
  await store.fetchEngagementActions()
}

async function generateActionContent(actionId) {
  await store.generateContent(actionId)
}

async function executeAction(actionId, content) {
  await store.executeAction(actionId, content)
}

// ============== Guide Content ==============

const guideContent = `
# LinkedIn Automation - Komplette Anleitung

Das LinkedIn-Modul ist ein umfassendes Werkzeug fuer automatisiertes Sales Navigator Scraping, personalisierte Outreach-Kampagnen und systematisches Lead-Management. Diese Anleitung erklaert alle Funktionen im Detail.

---

## Modul-Uebersicht

### Was kann dieses Modul?

| Funktion | Beschreibung |
|----------|--------------|
| **Profile Scraping** | Automatisches Sammeln von LinkedIn-Profilen aus Sales Navigator Suchen |
| **Kontaktverwaltung** | Zentrale Datenbank aller gescrapten Kontakte mit Filtermoeglichkeiten |
| **Nachrichtenvorlagen** | Personalisierte Templates mit dynamischen Variablen |
| **Outreach-Kampagnen** | Mehrstufige, automatisierte Kontaktaufnahme-Workflows |
| **Inbox** | Alle LinkedIn-Konversationen an einem Ort |
| **Safety-System** | Intelligente Rate-Limits und Account-Warmup |

### Dashboard verstehen

Das Dashboard zeigt dir auf einen Blick:
- **Aktive Accounts**: Wie viele deiner LinkedIn-Accounts aktiv sind
- **Laufende Jobs**: Aktuell ausgefuehrte Scraper-Jobs mit Fortschritt
- **Profile heute**: Wie viele Profile heute gescraped wurden
- **Kontakte gesamt**: Gesamtzahl aller gesammelten Kontakte

---

## Accounts einrichten

### Warum mehrere Accounts?

LinkedIn hat strenge Limits pro Account. Mit mehreren Accounts kannst du:
- Mehr Profile pro Tag scrapen
- Mehr Kontaktanfragen senden
- Risiko auf mehrere Accounts verteilen

### Account hinzufuegen

1. Klicke auf **"Neuer Account"**
2. Gib einen **Namen** ein (z.B. "Max - Sales Navigator Premium")
3. Gib die **E-Mail-Adresse** des LinkedIn-Accounts ein
4. Aktiviere **"Sales Navigator"** wenn der Account Premium hat

### Session importieren (WICHTIG!)

Um LinkedIn nutzen zu koennen, muss die Browser-Session importiert werden:

#### Chrome:
1. Oeffne LinkedIn im Browser und logge dich ein
2. Druecke **F12** (Developer Tools)
3. Gehe zu **Application** > **Cookies** > **linkedin.com**
4. Suche den Cookie **\`li_at\`**
5. Kopiere den **Value** (langer String)
6. Fuege ihn im Account unter **"Session Data"** ein

#### Firefox:
1. Oeffne LinkedIn und logge dich ein
2. Druecke **F12** > **Storage** > **Cookies**
3. Suche **\`li_at\`** und kopiere den Wert

> **Wichtig:** Die Session kann bereits nach wenigen Tagen ablaufen (typischerweise 1 Woche). Bei Problemen die Session neu importieren!

### Account-Status

| Status | Bedeutung | Aktion |
|--------|-----------|--------|
| **Aktiv** | Account funktioniert normal | Keine |
| **Warmup** | Account ist in der Aufwaermphase | Limits werden automatisch erhoeht |
| **Rate-Limited** | LinkedIn hat temporaer geblockt | 24h warten |
| **Gesperrt** | Account wurde gesperrt | Session pruefen, ggf. neu einloggen |
| **Inaktiv** | Account ist deaktiviert | Manuell aktivieren |

### Limits pro Account

| Aktion | Free Account | Sales Navigator |
|--------|--------------|-----------------|
| Profile/Tag | 80 | 150 |
| Kontaktanfragen/Woche | 100 | 200 |
| Nachrichten/Tag | 25 | 150 |
| InMails/Monat | 0 | 50 |

---

## Scraper Jobs

### Was ist ein Scraper Job?

Ein Scraper Job sammelt automatisch LinkedIn-Profile basierend auf einer Suchanfrage. Die gesammelten Profile werden als Kontakte gespeichert und koennen fuer Kampagnen verwendet werden.

### Job erstellen

1. Gehe zu **Scraper Jobs** > **Neuer Scraper Job**
2. Waehle einen **Account** aus
3. Gib dem Job einen **Namen**
4. Fuege die **Search URL** von Sales Navigator ein
5. Setze das **Max. Profile Limit**
6. Optional: Waehle einen **Funnel** als Ziel

### Search URL finden

1. Oeffne **Sales Navigator** im Browser
2. Fuehre eine Suche mit deinen Kriterien durch
3. Kopiere die **komplette URL** aus der Adresszeile

#### Beispiel-URL:
\`\`\`
https://www.linkedin.com/sales/search/people?query=(...)&sessionId=...
\`\`\`

### Job-Typen

| Typ | Beschreibung | URL-Format |
|-----|--------------|------------|
| **search** | Normale Profilsuche | \`/sales/search/people?\` |
| **list** | Gespeicherte Lead-Liste | \`/sales/lists/people/\` |
| **company** | Mitarbeiter eines Unternehmens | \`/sales/company/\` |

### Job-Status

| Status | Bedeutung |
|--------|-----------|
| **Entwurf** | Job erstellt, aber nicht gestartet |
| **In Warteschlange** | Job wartet auf Ausfuehrung |
| **Laeuft** | Job scraped aktuell Profile |
| **Pausiert** | Job wurde manuell pausiert |
| **Abgeschlossen** | Job hat alle Profile gescraped |
| **Fehlgeschlagen** | Fehler aufgetreten (Session? Limit?) |

### Scraper-Einstellungen

| Einstellung | Empfehlung | Beschreibung |
|-------------|------------|--------------|
| **Max. Profile** | 50-100 | Pro Job nicht zu viele Profile |
| **Verzoegerung** | 5-10 Sek | Zwischen einzelnen Profilen |
| **Seiten-Limit** | 10-20 | Max. Suchergebnis-Seiten |

---

## Kontakte verwalten

### Kontakt-Informationen

Jeder gescrapte Kontakt enthaelt:
- **Name** (Vor- und Nachname)
- **Headline** (LinkedIn Tagline)
- **Position** (Aktuelle Rolle)
- **Unternehmen** (Aktueller Arbeitgeber)
- **Standort** (Stadt/Region)
- **Branche** (Industry)
- **LinkedIn URL** (Direktlink zum Profil)

### Kontakt-Status

| Status | Bedeutung |
|--------|-----------|
| **Gescraped** | Profil wurde gesammelt |
| **Importiert** | In einen Funnel/CRM uebertragen |
| **Uebersprungen** | Duplikat oder Filter-Match |

### Kontakte filtern

Du kannst Kontakte filtern nach:
- Status
- Unternehmen
- Position
- Standort
- Scraper Job

### Kontakte exportieren

1. Filtere die gewuenschten Kontakte
2. Klicke auf **"Exportieren"**
3. Waehle Format (CSV, Excel)
4. Lade die Datei herunter

---

## Nachrichtenvorlagen

### Warum Vorlagen?

Vorlagen ermoeglichen:
- **Personalisierung** durch dynamische Variablen
- **Konsistenz** ueber alle Nachrichten
- **A/B-Testing** verschiedener Ansaetze
- **Zeitersparnis** bei Kampagnen

### Vorlagen-Typen

| Typ | Verwendung | Zeichenlimit |
|-----|------------|--------------|
| **Kontaktanfrage** | Note bei Connection Request | 300 Zeichen |
| **Nachricht** | Direktnachricht an Kontakt | 8.000 Zeichen |
| **Follow-up** | Folge-Nachricht | 8.000 Zeichen |
| **InMail** | Premium InMail | 1.900 Zeichen |

### Verfuegbare Variablen

| Variable | Beispiel | Beschreibung |
|----------|----------|--------------|
| \`{first_name}\` | "Max" | Vorname des Kontakts |
| \`{last_name}\` | "Mustermann" | Nachname |
| \`{full_name}\` | "Max Mustermann" | Vollstaendiger Name |
| \`{company}\` | "Acme GmbH" | Aktuelles Unternehmen |
| \`{position}\` | "Sales Manager" | Aktuelle Position |
| \`{headline}\` | "Sales | SaaS | B2B" | LinkedIn Headline |
| \`{industry}\` | "Software" | Branche |
| \`{location}\` | "Muenchen" | Standort |

### Vorlage erstellen

1. Klicke auf **"Neue Vorlage"**
2. Gib einen **Namen** ein
3. Waehle den **Typ** (Kontaktanfrage, Nachricht, etc.)
4. Schreibe deinen **Text** mit Variablen
5. Nutze die **Vorschau** um das Ergebnis zu pruefen

### Beispiel-Vorlagen

#### Kontaktanfrage (max. 300 Zeichen):
\`\`\`
Hallo {first_name}, ich bin auf dein Profil gestossen und finde deine Arbeit bei {company} spannend. Wuerde mich freuen, wenn wir uns vernetzen!
\`\`\`

#### Erste Nachricht:
\`\`\`
Hallo {first_name},

vielen Dank fuer die Vernetzung! Ich habe gesehen, dass du als {position} bei {company} arbeitest.

Wir helfen Unternehmen in der {industry}-Branche dabei, [NUTZEN]. Waere das auch fuer euch relevant?

Falls ja, freue ich mich auf einen kurzen Austausch!

Beste Gruesse
\`\`\`

#### Follow-up nach 7 Tagen:
\`\`\`
Hallo {first_name},

ich wollte kurz nachhaken - hast du meine letzte Nachricht gesehen?

Falls gerade nicht der richtige Zeitpunkt ist, kein Problem. Ich bin auch gerne spaeter fuer einen Austausch da.

Beste Gruesse
\`\`\`

### A/B-Testing

1. Erstelle mehrere Varianten einer Vorlage
2. Markiere sie als **Varianten** der Hauptvorlage
3. In Kampagnen werden sie automatisch rotiert
4. Analysiere die **Antwortrate** jeder Variante

---

## Kampagnen erstellen

### Was ist eine Kampagne?

Eine Kampagne ist ein automatisierter, mehrstufiger Workflow fuer die Kontaktaufnahme. Sie fuehrt definierte Schritte fuer jeden Lead automatisch aus.

### Kampagnen-Workflow Beispiel

\`\`\`
Tag 1: Kontaktanfrage senden
        ↓
Tag 2-4: Warten auf Annahme
        ↓
[Wenn angenommen]
        ↓
Tag 5: Erste Nachricht senden
        ↓
Tag 5-12: Warten auf Antwort
        ↓
[Wenn keine Antwort]
        ↓
Tag 12: Follow-up Nachricht
        ↓
Ende der Kampagne
\`\`\`

### Kampagne erstellen

1. Klicke auf **"Neue Kampagne"**
2. Gib einen **Namen** und **Beschreibung** ein
3. Waehle den **Account** fuer die Ausfuehrung
4. Konfiguriere die **Schritte** (siehe unten)
5. Fuege **Leads** hinzu
6. **Starte** die Kampagne

### Schritt-Typen

| Schritt | Beschreibung | Einstellungen |
|---------|--------------|---------------|
| **Verbinden** | Kontaktanfrage senden | Vorlage fuer Note (optional) |
| **Nachricht** | Direktnachricht senden | Vorlage auswaehlen |
| **Warten** | Pause zwischen Schritten | Tage/Stunden |
| **Bedingung** | Verzweigung basierend auf Status | connected/replied |

### Kampagnen-Einstellungen

| Einstellung | Beschreibung | Empfehlung |
|-------------|--------------|------------|
| **Stop bei Antwort** | Kampagne endet wenn Lead antwortet | An |
| **Stop bei Connect** | Kampagne endet bei Annahme | Aus (normalerweise) |
| **Taegliches Limit** | Max. Aktionen pro Tag | 25-50 |
| **Zeitfenster** | Wann Aktionen ausgefuehrt werden | 9:00-18:00 |
| **Wochentage** | An welchen Tagen | Mo-Fr |

### Leads hinzufuegen

#### Einzeln:
1. Klicke auf **"Lead hinzufuegen"**
2. Gib die LinkedIn URL oder waehle aus Kontakten

#### Bulk (aus Scraper Jobs):
1. Klicke auf **"Leads importieren"**
2. Waehle einen oder mehrere Scraper Jobs
3. Optional: Filter anwenden
4. Bestaetigen

### Lead-Status in Kampagnen

| Status | Bedeutung |
|--------|-----------|
| **Ausstehend** | Lead wartet auf Kampagnenstart |
| **Aktiv** | Lead durchlaeuft Kampagne |
| **Wartend** | Lead ist in einer Wartezeit |
| **Beantwortet** | Lead hat geantwortet |
| **Verbunden** | Kontaktanfrage wurde angenommen |
| **Abgeschlossen** | Alle Schritte durchlaufen |
| **Gestoppt** | Manuell oder wegen Fehler gestoppt |

### Kampagnen-Statistiken

Fuer jede Kampagne siehst du:
- **Leads gesamt**: Anzahl aller Leads
- **Aktive Leads**: Aktuell in der Kampagne
- **Verbindungen gesendet**: Kontaktanfragen
- **Verbindungen akzeptiert**: Erfolgreiche Connects
- **Nachrichten gesendet**: Gesendete Messages
- **Antworten erhalten**: Leads die geantwortet haben
- **Antwortrate**: Prozent der Antworten

---

## Inbox & Konversationen

### Inbox verstehen

Die Inbox zeigt alle LinkedIn-Konversationen an einem Ort:
- **Ungelesene** Nachrichten werden hervorgehoben
- **Konversationen** sind nach Kontakt gruppiert
- **Schnelle Antwort** direkt aus der App

### Nachrichten verwalten

1. Klicke auf eine Konversation
2. Sieh den kompletten **Verlauf**
3. Schreibe eine **Antwort**
4. Nutze **Vorlagen** fuer schnelle Antworten

### Automatische Sync

Die Inbox synchronisiert sich automatisch:
- Neue eingehende Nachrichten
- Gesendete Nachrichten aus Kampagnen
- Status-Updates (gelesen, beantwortet)

---

## Safety & Warmup-System

### Warum ist Safety wichtig?

LinkedIn erkennt automatisierte Aktivitaeten. Zu viele Aktionen fuehren zu:
- Temporaeren Sperren (24-72h)
- Permanenten Account-Sperren
- Einschraenkungen bei Nachrichten

### Das Warmup-System

Neue Accounts starten mit reduzierten Limits und werden ueber 14 Tage aufgewaermt:

| Tag | Verbindungen | Nachrichten | Profile |
|-----|--------------|-------------|---------|
| 1 | 3 | 5 | 10 |
| 2 | 5 | 8 | 15 |
| 3 | 7 | 10 | 20 |
| 4 | 10 | 15 | 25 |
| 5 | 12 | 18 | 30 |
| 6 | 15 | 22 | 35 |
| 7 | 18 | 25 | 40 |
| 8-10 | 20-28 | 30-42 | 50-70 |
| 11-13 | 30-35 | 45-50 | 75-90 |
| 14+ | Volle Limits | Volle Limits | Volle Limits |

### Warmup aktivieren

1. Gehe zu **Account bearbeiten**
2. Aktiviere **"Warmup aktivieren"**
3. Das System beginnt automatisch am naechsten Tag

### Warmup ueberspringen

Fuer erfahrene Accounts kannst du den Warmup ueberspringen:
1. Account bearbeiten
2. Klicke auf **"Warmup ueberspringen"**

> **Achtung:** Nur fuer Accounts empfohlen, die bereits aktiv genutzt wurden!

### Rate-Limit Schutz

Das System schuetzt automatisch:
- **Verzoegerungen** zwischen Aktionen (30-120 Sekunden)
- **Adaptive Limits** basierend auf Account-Alter
- **Pause bei Warnzeichen** (ungewoehnliche Aktivitaet)
- **Taegliche Resets** um Mitternacht

### Account-Gesundheit pruefen

Im Dashboard siehst du fuer jeden Account:
- **Heutiger Verbrauch** vs. Limit
- **Warmup-Status** und verbleibende Tage
- **Letzte Aktivitaet**
- **Fehler oder Warnungen**

---

## Best Practices

### Profilsuche optimieren

1. **Spezifische Filter** nutzen (Branche, Groesse, Region)
2. **Nicht zu breit** suchen (< 1000 Ergebnisse)
3. **Keyword-Suche** fuer praezise Treffer
4. **Gespeicherte Suchen** fuer wiederkehrende Jobs

### Kontaktanfragen

- **Personalisierte Notes** erhoehen Akzeptanz um 40%
- **Kurz und relevant** (< 200 Zeichen optimal)
- **Kein Pitch** in der ersten Nachricht
- **Gemeinsame Kontakte** erwaehnen

### Nachrichtenqualitaet

- **Keine Massenmail-Sprache** ("Sehr geehrte Damen und Herren")
- **Persoenlich und direkt** schreiben
- **Klarer Call-to-Action** (eine Frage stellen)
- **Mobile-freundlich** (kurze Absaetze)

### Timing

| Aktion | Beste Zeit | Beste Tage |
|--------|------------|------------|
| Kontaktanfragen | 9-11 Uhr | Di-Do |
| Nachrichten | 10-12 Uhr | Di-Do |
| Follow-ups | 14-16 Uhr | Mi-Fr |

### Wartezeiten in Kampagnen

- **Nach Kontaktanfrage**: 2-3 Tage warten
- **Zwischen Nachrichten**: 3-5 Tage
- **Follow-up**: 5-7 Tage
- **Letzter Versuch**: Nach 14 Tagen

---

## Fehlerbehebung

### "Session abgelaufen"

**Ursache:** LinkedIn-Cookie ist nicht mehr gueltig

**Loesung:**
1. Im Browser bei LinkedIn einloggen
2. Cookie \`li_at\` neu exportieren
3. Im Account-Bereich einfuegen

### "Rate-Limit erreicht"

**Ursache:** Zu viele Aktionen in kurzer Zeit

**Loesung:**
1. 24 Stunden warten
2. Limits in Kampagnen reduzieren
3. Warmup aktivieren falls neuer Account

### "Kontaktanfrage fehlgeschlagen"

**Ursache:** Profil hat Einschraenkungen oder bereits verbunden

**Loesung:**
1. Lead wird automatisch uebersprungen
2. Pruefen ob bereits verbunden
3. Profil manuell pruefen

### "Account gesperrt"

**Ursache:** LinkedIn hat verdaechtige Aktivitaet erkannt

**Loesung:**
1. Im Browser einloggen
2. Sicherheitspruefung durchfuehren
3. Session neu importieren
4. 48h warten vor naechster Aktivitaet

### Jobs starten nicht

**Ursache:** Kein aktiver Account oder alle Limits erreicht

**Loesung:**
1. Pruefen ob Account aktiv ist
2. Taegliche Limits pruefen
3. Queue-Status pruefen

---

## Haeufige Fragen (FAQ)

### Wie viele Accounts kann ich nutzen?
> Technisch unbegrenzt. Empfohlen: 2-3 pro Sales-Person.

### Werden meine Accounts gesperrt?
> Mit korrektem Warmup und Limits ist das Risiko minimal. Das System schuetzt automatisch.

### Kann ich Kontakte in mein CRM exportieren?
> Ja, ueber die Funnel-Integration oder CSV-Export.

### Funktioniert das auch ohne Sales Navigator?
> Eingeschraenkt. Free LinkedIn hat strenge Limits und weniger Suchfilter.

### Wie oft werden Nachrichten synchronisiert?
> Alle 5 Minuten werden neue Nachrichten abgerufen.

### Kann ich Kampagnen zeitgesteuert ausfuehren?
> Ja, ueber Zeitfenster und Wochentage in den Kampagnen-Einstellungen.

---

*Letzte Aktualisierung: ${new Date().toLocaleDateString('de-DE')}*
`
</script>

<template>
  <div class="min-h-screen bg-go4-bg dark:bg-gray-900">
    <PageHeader
      title="LinkedIn"
    />

    <div class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <!-- Tabs -->
      <div class="mb-6 border-b border-gray-200 dark:border-gray-700">
        <nav class="-mb-px flex gap-6">
          <router-link
            v-for="tab in tabs"
            :key="tab.key"
            :to="tab.route"
            class="border-b-2 pb-3 text-sm font-medium transition-colors"
            :class="
              activeTab === tab.key
                ? 'border-go4-primary text-go4-primary'
                : 'border-transparent text-go4-muted hover:border-gray-300 hover:text-go4-secondary dark:text-gray-400 dark:hover:text-white'
            "
          >
            {{ tab.label }}
          </router-link>
        </nav>
      </div>

      <!-- Dashboard Tab -->
      <div v-if="activeTab === 'dashboard'">
        <div
          v-if="store.stats"
          class="grid gap-4 md:grid-cols-2 lg:grid-cols-4"
        >
          <!-- Stats Cards -->
          <div
            class="rounded-lg border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800"
          >
            <div class="text-sm text-go4-muted dark:text-gray-400">
              Aktive Accounts
            </div>
            <div class="mt-1 text-2xl font-bold text-go4-secondary dark:text-white">
              {{ store.stats.accounts_active }} / {{ store.stats.accounts_total }}
            </div>
          </div>

          <div
            class="rounded-lg border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800"
          >
            <div class="text-sm text-go4-muted dark:text-gray-400">
              Laufende Jobs
            </div>
            <div class="mt-1 text-2xl font-bold text-go4-secondary dark:text-white">
              {{ store.stats.jobs_running }}
            </div>
          </div>

          <div
            class="rounded-lg border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800"
          >
            <div class="text-sm text-go4-muted dark:text-gray-400">
              Profile heute
            </div>
            <div class="mt-1 text-2xl font-bold text-go4-secondary dark:text-white">
              {{ store.stats.profiles_today }}
            </div>
            <div class="mt-1 text-xs text-go4-muted dark:text-gray-500">
              {{ store.stats.daily_limit_remaining }} verbleibend
            </div>
          </div>

          <div
            class="rounded-lg border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800"
          >
            <div class="text-sm text-go4-muted dark:text-gray-400">
              Kontakte gescraped
            </div>
            <div class="mt-1 text-2xl font-bold text-go4-secondary dark:text-white">
              {{ store.stats.contacts_scraped }}
            </div>
            <div class="mt-1 text-xs text-go4-muted dark:text-gray-500">
              {{ store.stats.contacts_imported }} importiert
            </div>
          </div>
        </div>

        <!-- Running Jobs -->
        <div
          v-if="store.runningJobs.length > 0"
          class="mt-6"
        >
          <h3 class="mb-4 text-lg font-medium text-go4-secondary dark:text-white">
            Laufende Jobs
          </h3>
          <div class="space-y-3">
            <div
              v-for="job in store.runningJobs"
              :key="job.id"
              class="flex cursor-pointer items-center justify-between rounded-lg border border-gray-200 bg-white p-4 transition-shadow hover:shadow-md dark:border-gray-700 dark:bg-gray-800"
              @click="openJob(job)"
            >
              <div class="flex items-center gap-4">
                <div
                  class="h-10 w-10 animate-pulse rounded-full bg-indigo-100 dark:bg-indigo-900/50"
                />
                <div>
                  <div class="font-medium text-go4-secondary dark:text-white">
                    {{ job.name || 'Job #' + job.id }}
                  </div>
                  <div class="text-sm text-go4-muted dark:text-gray-400">
                    {{ job.profiles_scraped }} / {{ job.max_profiles }} Profile
                  </div>
                </div>
              </div>
              <div class="flex items-center gap-4">
                <div class="h-2 w-32 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
                  <div
                    class="h-full bg-indigo-500"
                    :style="{ width: `${job.progress_percent}%` }"
                  />
                </div>
                <span class="text-sm text-go4-muted">{{ Math.round(job.progress_percent) }}%</span>
                <button
                  class="rounded p-1 text-gray-400 hover:bg-yellow-100 hover:text-yellow-600"
                  title="Pausieren"
                  @click="pauseJob(job)"
                >
                  <svg
                    class="h-5 w-5"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fill-rule="evenodd"
                      d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z"
                      clip-rule="evenodd"
                    />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Quick Actions -->
        <div class="mt-6 grid gap-4 md:grid-cols-2">
          <div
            class="cursor-pointer rounded-lg border border-gray-200 bg-white p-5 transition-shadow hover:shadow-md dark:border-gray-700 dark:bg-gray-800"
            @click="createJob"
          >
            <h4 class="font-medium text-go4-secondary dark:text-white">
              Neuen Scraper Job starten
            </h4>
            <p class="mt-1 text-sm text-go4-muted dark:text-gray-400">
              Starte einen neuen Job um LinkedIn Profile zu scrapen
            </p>
          </div>
          <div
            class="cursor-pointer rounded-lg border border-gray-200 bg-white p-5 transition-shadow hover:shadow-md dark:border-gray-700 dark:bg-gray-800"
            @click="createAccount"
          >
            <h4 class="font-medium text-go4-secondary dark:text-white">
              LinkedIn Account hinzufuegen
            </h4>
            <p class="mt-1 text-sm text-go4-muted dark:text-gray-400">
              Verbinde einen Sales Navigator Account
            </p>
          </div>
        </div>
      </div>

      <!-- Accounts Tab -->
      <div v-else-if="activeTab === 'accounts'">
        <div class="mb-4 flex items-center gap-4">
          <SearchInput
            v-model="searchQuery"
            placeholder="Account suchen..."
            class="w-64"
          />
          <select
            v-model="statusFilter"
            class="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
          >
            <option value="">
              Alle Status
            </option>
            <option value="active">
              Aktiv
            </option>
            <option value="inactive">
              Inaktiv
            </option>
            <option value="rate_limited">
              Rate-Limit
            </option>
          </select>
          <button
            class="ml-auto flex h-9 w-9 items-center justify-center rounded-lg bg-go4-primary text-white hover:bg-go4-primary-dark"
            title="Neuer Account"
            @click="createAccount"
          >
            <svg
              class="h-5 w-5"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fill-rule="evenodd"
                d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
                clip-rule="evenodd"
              />
            </svg>
          </button>
        </div>

        <div
          v-if="store.loading"
          class="py-12 text-center text-go4-muted"
        >
          Laden...
        </div>

        <EmptyState
          v-else-if="filteredAccounts.length === 0"
          title="Keine Accounts"
        >
          <button
            class="mt-4 rounded-lg bg-go4-primary px-4 py-2 text-sm text-white hover:bg-go4-primary-dark"
            @click="createAccount"
          >
            Account hinzufuegen
          </button>
        </EmptyState>

        <div
          v-else
          class="space-y-3"
        >
          <div
            v-for="account in filteredAccounts"
            :key="account.id"
            class="flex items-center justify-between rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
          >
            <div class="flex items-center gap-4">
              <div
                class="flex h-10 w-10 items-center justify-center rounded-full bg-[#0A66C2] text-white"
              >
                <svg
                  class="h-6 w-6"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                >
                  <path
                    d="M4 3a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2V5a2 2 0 00-2-2H4zm3 5a1.5 1.5 0 100-3 1.5 1.5 0 000 3zm-1.5 2h3v9h-3v-9zm5.5 0h3v1.5s1-1.5 3-1.5c1.5 0 3 1 3 4v5h-3v-4c0-1.5-.5-2-1.5-2s-1.5 1-1.5 2v4h-3v-9z"
                  />
                </svg>
              </div>
              <div>
                <div class="font-medium text-go4-secondary dark:text-white">
                  {{ account.name }}
                </div>
                <div class="text-sm text-go4-muted dark:text-gray-400">
                  {{ account.email }}
                </div>
              </div>
            </div>

            <div class="flex items-center gap-4">
              <span
                :class="statusColors[account.status]"
                class="rounded-full px-2 py-0.5 text-xs font-medium"
              >
                {{ statusLabels[account.status] }}
              </span>

              <span
                v-if="account.is_sales_navigator"
                class="text-xs text-blue-600 dark:text-blue-400"
              >
                Sales Navigator
              </span>

              <div class="flex gap-1">
                <button
                  class="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700"
                  title="Bearbeiten"
                  @click="editAccount(account)"
                >
                  <svg
                    class="h-5 w-5"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                    />
                  </svg>
                </button>
                <button
                  class="rounded p-1 text-gray-400 hover:bg-red-100 hover:text-red-600 dark:hover:bg-red-900/30"
                  title="Loeschen"
                  @click="confirmDeleteAccount(account)"
                >
                  <svg
                    class="h-5 w-5"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                    />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Jobs Tab -->
      <div v-else-if="activeTab === 'jobs'">
        <div class="mb-4 flex items-center gap-4">
          <SearchInput
            v-model="searchQuery"
            placeholder="Job suchen..."
            class="w-64"
          />
          <select
            v-model="statusFilter"
            class="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
          >
            <option value="">
              Alle Status
            </option>
            <option value="draft">
              Entwurf
            </option>
            <option value="queued">
              In Warteschlange
            </option>
            <option value="running">
              Laeuft
            </option>
            <option value="paused">
              Pausiert
            </option>
            <option value="completed">
              Abgeschlossen
            </option>
            <option value="failed">
              Fehlgeschlagen
            </option>
          </select>
          <div class="ml-auto flex items-center gap-2">
            <button
              class="flex items-center gap-1.5 rounded-lg border border-green-300 bg-green-50 px-3 py-1.5 text-sm font-medium text-green-700 hover:bg-green-100 dark:border-green-700 dark:bg-green-900/30 dark:text-green-400 dark:hover:bg-green-900/50"
              title="1. Grad Kontakte importieren"
              @click="createFirstDegreeJob"
            >
              <svg
                class="h-4 w-4"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fill-rule="evenodd"
                  d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
                  clip-rule="evenodd"
                />
              </svg>
              1. Grad
            </button>
            <button
              class="flex h-9 w-9 items-center justify-center rounded-lg bg-go4-primary text-white hover:bg-go4-primary-dark"
              title="Neuer Job"
              @click="createJob"
            >
              <svg
                class="h-5 w-5"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fill-rule="evenodd"
                  d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
                  clip-rule="evenodd"
                />
              </svg>
            </button>
          </div>
        </div>

        <!-- Scheduler Status -->
        <div
          v-if="schedulerStatus.length > 0"
          class="mb-4 rounded-lg border border-blue-200 bg-blue-50 p-4 dark:border-blue-800 dark:bg-blue-900/20"
        >
          <div class="mb-2 flex items-center gap-2 text-sm font-medium text-blue-800 dark:text-blue-300">
            <svg
              class="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            Scheduler ({{ schedulerStatus.length }} geplante Jobs)
          </div>
          <div class="space-y-2">
            <div
              v-for="sj in schedulerStatus"
              :key="sj.job_id"
              class="flex items-center justify-between text-sm"
            >
              <div class="flex items-center gap-2">
                <span
                  class="inline-block h-2 w-2 rounded-full"
                  :class="sj.job_status === 'running' ? 'bg-green-500 animate-pulse' : sj.in_schedule_window ? 'bg-blue-500' : 'bg-gray-400'"
                />
                <span class="font-medium text-gray-800 dark:text-gray-200">{{ sj.job_name }}</span>
              </div>
              <div class="flex items-center gap-4 text-go4-muted dark:text-gray-400">
                <span>{{ formatScheduleDays(sj.schedule_days) }} {{ sj.schedule_start_time }}-{{ sj.schedule_end_time }}</span>
                <span>{{ sj.profiles_scraped }}/{{ sj.daily_limit }} heute</span>
                <span
                  :class="statusColors[sj.job_status]"
                  class="rounded-full px-2 py-0.5 text-xs font-medium"
                >
                  {{ statusLabels[sj.job_status] }}
                </span>
                <span
                  v-if="sj.ran_today"
                  class="text-xs text-green-600 dark:text-green-400"
                >Lief heute</span>
                <span
                  v-else-if="sj.in_schedule_window"
                  class="text-xs text-blue-600 dark:text-blue-400"
                >Wartet auf Queue</span>
              </div>
            </div>
          </div>
        </div>

        <div
          v-if="store.loading"
          class="py-12 text-center text-go4-muted"
        >
          Laden...
        </div>

        <EmptyState
          v-else-if="filteredJobs.length === 0"
          title="Keine Jobs"
        >
          <button
            class="mt-4 rounded-lg bg-go4-primary px-4 py-2 text-sm text-white hover:bg-go4-primary-dark"
            @click="createJob"
          >
            Job erstellen
          </button>
        </EmptyState>

        <div
          v-else
          class="space-y-3"
        >
          <div
            v-for="job in filteredJobs"
            :key="job.id"
            class="cursor-pointer rounded-lg border border-gray-200 bg-white p-4 transition-shadow hover:shadow-md dark:border-gray-700 dark:bg-gray-800"
            @click="openJob(job)"
          >
            <div class="flex items-center justify-between">
              <div>
                <div class="font-medium text-go4-secondary dark:text-white">
                  {{ job.name || 'Job #' + job.id }}
                </div>
                <div class="mt-1 flex items-center gap-3 text-sm text-go4-muted dark:text-gray-400">
                  <span>{{ job.account_name }}</span>
                  <span
                    v-if="job.schedule_enabled"
                    class="flex items-center gap-1 text-go4-primary"
                  >
                    <svg
                      class="h-3.5 w-3.5"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                      />
                    </svg>
                    Geplant
                  </span>
                </div>
              </div>

              <div class="flex items-center gap-4">
                <span
                  :class="statusColors[job.status]"
                  class="rounded-full px-2 py-0.5 text-xs font-medium"
                >
                  {{ statusLabels[job.status] }}
                </span>

                <div
                  v-if="job.status === 'running' || job.status === 'queued'"
                  class="flex items-center gap-2"
                >
                  <div class="h-2 w-24 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
                    <div
                      class="h-full bg-indigo-500"
                      :style="{ width: `${job.progress_percent}%` }"
                    />
                  </div>
                  <span class="text-sm">{{ Math.round(job.progress_percent) }}%</span>
                </div>

                <span
                  v-else
                  class="text-sm text-go4-muted"
                >
                  {{ job.profiles_scraped }} Profile
                </span>

                <div
                  class="flex gap-1"
                  @click.stop
                >
                  <button
                    v-if="
                      ['draft', 'paused', 'failed', 'cancelled', 'completed'].includes(job.status)
                    "
                    class="rounded p-1 text-gray-400 hover:bg-green-100 hover:text-green-600"
                    :title="
                      job.status === 'draft'
                        ? 'Starten'
                        : job.status === 'completed'
                          ? 'Neu starten'
                          : 'Fortsetzen'
                    "
                    @click="startJob(job)"
                  >
                    <svg
                      class="h-5 w-5"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fill-rule="evenodd"
                        d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z"
                        clip-rule="evenodd"
                      />
                    </svg>
                  </button>
                  <button
                    v-if="job.status === 'running'"
                    class="rounded p-1 text-gray-400 hover:bg-yellow-100 hover:text-yellow-600"
                    title="Pausieren"
                    @click="pauseJob(job)"
                  >
                    <svg
                      class="h-5 w-5"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fill-rule="evenodd"
                        d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z"
                        clip-rule="evenodd"
                      />
                    </svg>
                  </button>
                  <button
                    class="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700"
                    title="Bearbeiten"
                    @click="editJob(job)"
                  >
                    <svg
                      class="h-5 w-5"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                      />
                    </svg>
                  </button>
                  <button
                    v-if="job.status !== 'running'"
                    class="rounded p-1 text-gray-400 hover:bg-red-100 hover:text-red-600 dark:hover:bg-red-900/30"
                    title="Loeschen"
                    @click="confirmDeleteJob(job)"
                  >
                    <svg
                      class="h-5 w-5"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                      />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Contacts Tab -->
      <div v-else-if="activeTab === 'contacts'">
        <div class="mb-4 flex items-center gap-4">
          <SearchInput
            v-model="searchQuery"
            placeholder="Kontakt suchen..."
            class="w-64"
          />
          <select
            v-model="statusFilter"
            class="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
          >
            <option value="">
              Alle Status
            </option>
            <option value="scraped">
              Gescraped
            </option>
            <option value="imported">
              Importiert
            </option>
            <option value="skipped">
              Uebersprungen
            </option>
          </select>
          <div class="flex gap-1">
            <button
              :class="[
                'rounded-full px-3 py-1 text-sm font-medium transition-colors',
                !degreeFilter ? 'bg-go4-primary text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300'
              ]"
              @click="degreeFilter = null"
            >
              Alle
            </button>
            <button
              :class="[
                'rounded-full px-3 py-1 text-sm font-medium transition-colors',
                degreeFilter === 1 ? 'bg-green-600 text-white' : 'bg-green-50 text-green-700 hover:bg-green-100 dark:bg-green-900/30 dark:text-green-300'
              ]"
              @click="degreeFilter = degreeFilter === 1 ? null : 1"
            >
              1. Grad
            </button>
          </div>
          <span class="ml-auto text-sm text-go4-muted">{{ filteredContacts.length }} Kontakte</span>
          <button
            v-if="filteredContacts.length > 0"
            class="rounded-lg border border-red-300 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 dark:border-red-700 dark:text-red-400 dark:hover:bg-red-900/20"
            @click="showDeleteAllContactsConfirm = true"
          >
            Alle loeschen
          </button>
        </div>

        <div
          v-if="store.loading"
          class="py-12 text-center text-go4-muted"
        >
          Laden...
        </div>

        <EmptyState
          v-else-if="filteredContacts.length === 0"
          title="Keine Kontakte"
        />

        <div
          v-else
          class="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700"
        >
          <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead class="bg-gray-50 dark:bg-gray-800">
              <tr>
                <th
                  class="px-4 py-3 text-left text-xs font-medium uppercase text-go4-muted dark:text-gray-400"
                >
                  Name
                </th>
                <th
                  class="px-4 py-3 text-center text-xs font-medium uppercase text-go4-muted dark:text-gray-400"
                >
                  Grad
                </th>
                <th
                  class="px-4 py-3 text-left text-xs font-medium uppercase text-go4-muted dark:text-gray-400"
                >
                  Position
                </th>
                <th
                  class="px-4 py-3 text-left text-xs font-medium uppercase text-go4-muted dark:text-gray-400"
                >
                  Unternehmen
                </th>
                <th
                  class="px-4 py-3 text-center text-xs font-medium uppercase text-go4-muted dark:text-gray-400"
                >
                  Pipelines
                </th>
                <th
                  class="px-4 py-3 text-left text-xs font-medium uppercase text-go4-muted dark:text-gray-400"
                >
                  Status
                </th>
                <th
                  class="px-4 py-3 text-center text-xs font-medium uppercase text-go4-muted dark:text-gray-400"
                >
                  Aktiv
                </th>
                <th class="px-4 py-3 text-center text-xs font-medium uppercase text-go4-muted dark:text-gray-400" />
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-200 bg-white dark:divide-gray-700 dark:bg-gray-800">
              <tr
                v-for="contact in filteredContacts.slice(0, 50)"
                :key="contact.id"
                class="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700"
                @click="openContact(contact)"
              >
                <td class="whitespace-nowrap px-4 py-3">
                  <div class="font-medium text-go4-secondary dark:text-white">
                    {{ contact.name }}
                  </div>
                  <div
                    v-if="contact.headline"
                    class="max-w-xs truncate text-xs text-go4-muted dark:text-gray-400"
                  >
                    {{ contact.headline }}
                  </div>
                </td>
                <td class="whitespace-nowrap px-4 py-3 text-center">
                  <span
                    v-if="contact.contact_degree"
                    :class="{
                      'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300': contact.contact_degree === 1,
                      'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300': contact.contact_degree === 2,
                      'bg-orange-100 text-orange-700 dark:bg-orange-900/50 dark:text-orange-300': contact.contact_degree === 3
                    }"
                    class="rounded-full px-2 py-0.5 text-xs font-medium"
                  >
                    {{ contact.contact_degree }}.
                  </span>
                  <span
                    v-else
                    class="text-xs text-go4-muted"
                  >-</span>
                </td>
                <td class="whitespace-nowrap px-4 py-3 text-sm text-go4-muted dark:text-gray-400">
                  {{ contact.position || '-' }}
                </td>
                <td class="whitespace-nowrap px-4 py-3 text-sm text-go4-muted dark:text-gray-400">
                  {{ contact.company_name || '-' }}
                </td>
                <td class="whitespace-nowrap px-4 py-3 text-center">
                  <span
                    v-if="contact.pipeline_count"
                    class="inline-flex h-5 min-w-[20px] items-center justify-center rounded-full bg-indigo-100 px-1.5 text-xs font-medium text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300"
                  >
                    {{ contact.pipeline_count }}
                  </span>
                  <span
                    v-else
                    class="text-xs text-go4-muted"
                  >-</span>
                </td>
                <td class="whitespace-nowrap px-4 py-3">
                  <span
                    :class="statusColors[contact.status]"
                    class="rounded-full px-2 py-0.5 text-xs font-medium"
                  >
                    {{ statusLabels[contact.status] }}
                  </span>
                </td>
                <td
                  class="whitespace-nowrap px-4 py-3 text-center"
                  @click.stop
                >
                  <button
                    :class="contact.excluded
                      ? 'text-red-500 hover:text-red-700 dark:text-red-400'
                      : 'text-green-500 hover:text-green-700 dark:text-green-400'"
                    class="text-lg"
                    :title="contact.excluded ? 'Deaktiviert – klicken zum Aktivieren' : 'Aktiv – klicken zum Deaktivieren'"
                    @click="store.toggleExclude(contact.id)"
                  >
                    {{ contact.excluded ? '⊘' : '✓' }}
                  </button>
                </td>
                <td
                  class="whitespace-nowrap px-4 py-3 text-center"
                  @click.stop
                >
                  <button
                    class="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/20"
                    title="Kontakt loeschen"
                    @click="confirmDeleteContact(contact)"
                  >
                    <svg
                      class="h-4 w-4"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                      />
                    </svg>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Templates Tab -->
      <div v-else-if="activeTab === 'templates'">
        <div class="mb-4 flex items-center gap-4">
          <SearchInput
            v-model="searchQuery"
            placeholder="Vorlage suchen..."
            class="w-64"
          />
          <select
            v-model="statusFilter"
            class="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
          >
            <option value="">
              Alle Typen
            </option>
            <option value="connection_note">
              Kontaktanfrage
            </option>
            <option value="message">
              Nachricht
            </option>
            <option value="follow_up">
              Follow-up
            </option>
            <option value="inmail">
              InMail
            </option>
          </select>
          <button
            class="ml-auto flex h-9 w-9 items-center justify-center rounded-lg bg-go4-primary text-white hover:bg-go4-primary-dark"
            title="Neue Vorlage"
            @click="createTemplate"
          >
            <svg
              class="h-5 w-5"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fill-rule="evenodd"
                d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
                clip-rule="evenodd"
              />
            </svg>
          </button>
        </div>

        <div
          v-if="store.loading"
          class="py-12 text-center text-go4-muted"
        >
          Laden...
        </div>

        <EmptyState
          v-else-if="filteredTemplates.length === 0"
          title="Keine Vorlagen"
        />

        <div
          v-else
          class="grid gap-4 md:grid-cols-2 lg:grid-cols-3"
        >
          <div
            v-for="template in filteredTemplates"
            :key="template.id"
            class="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
          >
            <div class="mb-2 flex items-start justify-between">
              <div>
                <h3 class="font-medium text-go4-secondary dark:text-white">
                  {{ template.name }}
                </h3>
                <span class="text-xs text-go4-muted">
                  {{ templateTypes[template.type] || template.type }}
                </span>
              </div>
              <div class="flex gap-1">
                <button
                  class="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700"
                  title="Bearbeiten"
                  @click="editTemplate(template)"
                >
                  <svg
                    class="h-4 w-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                    />
                  </svg>
                </button>
                <button
                  class="rounded p-1 text-gray-400 hover:bg-red-100 hover:text-red-600 dark:hover:bg-red-900/30"
                  title="Loeschen"
                  @click="confirmDeleteTemplate(template)"
                >
                  <svg
                    class="h-4 w-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                    />
                  </svg>
                </button>
              </div>
            </div>
            <p class="line-clamp-3 text-sm text-go4-muted dark:text-gray-400">
              {{ template.content }}
            </p>
            <div class="mt-3 flex items-center justify-between text-xs text-go4-muted">
              <span>{{ template.times_used || 0 }}x verwendet</span>
              <span v-if="template.response_rate">
                {{ (template.response_rate * 100).toFixed(1) }}% Antwortrate
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Campaigns Tab -->
      <div v-else-if="activeTab === 'campaigns'">
        <!-- Central engagement pipelines (channel=linkedin) — same list every module shows -->
        <PipelineCampaignsList
          channel-filter="linkedin"
          class="mb-8"
        />

        <div class="mb-4 mt-8 border-t border-gray-200 pt-6 dark:border-gray-700">
          <h3 class="mb-3 text-base font-semibold text-gray-700 dark:text-gray-300">
            LinkedIn-eigene Sequenzen
          </h3>
          <p class="mb-3 text-xs text-gray-500 dark:text-gray-400">
            Veraltete LinkedIn-spezifische Campaigns (vor der zentralen Pipeline-Architektur).
            Werden langfristig in zentrale Engagement-Pipelines migriert.
          </p>
        </div>
        <div class="mb-4 flex items-center gap-4">
          <SearchInput
            v-model="searchQuery"
            placeholder="Kampagne suchen..."
            class="w-64"
          />
          <select
            v-model="statusFilter"
            class="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
          >
            <option value="">
              Alle Status
            </option>
            <option value="draft">
              Entwurf
            </option>
            <option value="active">
              Aktiv
            </option>
            <option value="paused">
              Pausiert
            </option>
            <option value="completed">
              Abgeschlossen
            </option>
          </select>
          <button
            class="ml-auto flex h-9 w-9 items-center justify-center rounded-lg bg-go4-primary text-white hover:bg-go4-primary-dark"
            title="Neue Kampagne"
            @click="createCampaign"
          >
            <svg
              class="h-5 w-5"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fill-rule="evenodd"
                d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
                clip-rule="evenodd"
              />
            </svg>
          </button>
        </div>

        <div
          v-if="store.loading"
          class="py-12 text-center text-go4-muted"
        >
          Laden...
        </div>

        <EmptyState
          v-else-if="filteredCampaigns.length === 0"
          title="Keine Kampagnen"
        />

        <div
          v-else
          class="space-y-3"
        >
          <div
            v-for="campaign in filteredCampaigns"
            :key="campaign.id"
            class="cursor-pointer rounded-lg border border-gray-200 bg-white p-4 transition-shadow hover:shadow-md dark:border-gray-700 dark:bg-gray-800"
            @click="openCampaign(campaign)"
          >
            <div class="flex items-center justify-between">
              <div>
                <div class="font-medium text-go4-secondary dark:text-white">
                  {{ campaign.name }}
                </div>
                <div class="mt-1 flex items-center gap-4 text-sm text-go4-muted dark:text-gray-400">
                  <span>{{ campaign.steps_count || 0 }} Schritte</span>
                  <span>{{ campaign.leads_count || 0 }} Leads</span>
                </div>
              </div>

              <div class="flex items-center gap-4">
                <span
                  :class="statusColors[campaign.status]"
                  class="rounded-full px-2 py-0.5 text-xs font-medium"
                >
                  {{ statusLabels[campaign.status] }}
                </span>

                <div class="text-right text-sm">
                  <div class="text-go4-muted">
                    {{ campaign.completed_leads || 0 }} / {{ campaign.leads_count || 0 }}
                  </div>
                  <div class="text-xs text-go4-muted">
                    {{ campaign.replied_leads || 0 }} Antworten
                  </div>
                </div>

                <div
                  class="flex gap-1"
                  @click.stop
                >
                  <button
                    v-if="campaign.status === 'draft' || campaign.status === 'paused'"
                    class="rounded p-1 text-gray-400 hover:bg-green-100 hover:text-green-600"
                    title="Starten"
                    @click="startCampaign(campaign)"
                  >
                    <svg
                      class="h-5 w-5"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fill-rule="evenodd"
                        d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z"
                        clip-rule="evenodd"
                      />
                    </svg>
                  </button>
                  <button
                    v-if="campaign.status === 'active'"
                    class="rounded p-1 text-gray-400 hover:bg-yellow-100 hover:text-yellow-600"
                    title="Pausieren"
                    @click="pauseCampaign(campaign)"
                  >
                    <svg
                      class="h-5 w-5"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fill-rule="evenodd"
                        d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z"
                        clip-rule="evenodd"
                      />
                    </svg>
                  </button>
                  <button
                    class="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700"
                    title="Bearbeiten"
                    @click="editCampaign(campaign)"
                  >
                    <svg
                      class="h-5 w-5"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                      />
                    </svg>
                  </button>
                  <button
                    v-if="campaign.status !== 'active'"
                    class="rounded p-1 text-gray-400 hover:bg-red-100 hover:text-red-600 dark:hover:bg-red-900/30"
                    title="Loeschen"
                    @click="confirmDeleteCampaign(campaign)"
                  >
                    <svg
                      class="h-5 w-5"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                      />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Inbox Tab -->
      <div v-else-if="activeTab === 'inbox'">
        <div class="mb-4 flex items-center gap-4">
          <SearchInput
            v-model="searchQuery"
            placeholder="Konversation suchen..."
            class="w-64"
          />
          <span class="ml-auto text-sm text-go4-muted">
            {{ store.unreadMessages.length }} ungelesen
          </span>
        </div>

        <div
          v-if="store.loading"
          class="py-12 text-center text-go4-muted"
        >
          Laden...
        </div>

        <EmptyState
          v-else-if="filteredInbox.length === 0"
          title="Keine Nachrichten"
        />

        <div
          v-else
          class="space-y-2"
        >
          <div
            v-for="conversation in filteredInbox"
            :key="conversation.contact_id"
            class="flex cursor-pointer items-center gap-4 rounded-lg border border-gray-200 bg-white p-4 transition-shadow hover:shadow-md dark:border-gray-700 dark:bg-gray-800"
            :class="{ 'border-l-4 border-l-go4-primary': !conversation.read_at }"
          >
            <div
              class="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-gray-200 text-sm font-medium text-gray-600 dark:bg-gray-700 dark:text-gray-300"
            >
              {{ conversation.contact_name?.charAt(0) || '?' }}
            </div>
            <div class="min-w-0 flex-1">
              <div class="flex items-center justify-between">
                <span
                  class="font-medium text-go4-secondary dark:text-white"
                  :class="{ 'font-bold': !conversation.read_at }"
                >
                  {{ conversation.contact_name }}
                </span>
                <span class="text-xs text-go4-muted">
                  {{ conversation.last_message_at }}
                </span>
              </div>
              <p class="mt-1 truncate text-sm text-go4-muted dark:text-gray-400">
                {{ conversation.last_message }}
              </p>
            </div>
            <span
              v-if="conversation.unread_count > 0"
              class="flex h-5 w-5 items-center justify-center rounded-full bg-go4-primary text-xs text-white"
            >
              {{ conversation.unread_count }}
            </span>
          </div>
        </div>
      </div>

      <!-- Freigabe Tab (Engagement Brain Actions) -->
      <div v-else-if="activeTab === 'freigabe'">
        <div class="mb-6 flex items-center justify-between">
          <div>
            <h2 class="text-lg font-semibold text-go4-secondary dark:text-white">
              Freigabe-Queue
            </h2>
            <p class="text-sm text-go4-muted dark:text-gray-400">
              Vom Engagement Brain generierte Aktionen zur Freigabe
            </p>
          </div>
          <button
            class="flex items-center gap-2 rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark"
            @click="loadEngagementActions"
          >
            <svg
              class="h-4 w-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            Aktualisieren
          </button>
        </div>

        <!-- Loading State -->
        <div
          v-if="store.loading"
          class="flex items-center justify-center py-12"
        >
          <span class="text-go4-muted dark:text-gray-400">Laden...</span>
        </div>

        <!-- Empty State -->
        <EmptyState
          v-else-if="store.engagementActions.length === 0"
          title="Keine Aktionen"
          icon="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
        />

        <!-- Actions List -->
        <div
          v-else
          class="space-y-4"
        >
          <div
            v-for="action in store.engagementActions"
            :key="action.id"
            class="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
          >
            <div class="flex items-start justify-between">
              <div class="flex-1">
                <!-- Contact Info -->
                <div class="mb-2 flex items-center gap-3">
                  <div class="flex h-10 w-10 items-center justify-center rounded-full bg-go4-primary/10 text-go4-primary">
                    <svg
                      class="h-5 w-5"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                      />
                    </svg>
                  </div>
                  <div>
                    <h4 class="font-medium text-go4-secondary dark:text-white">
                      {{ action.context?.contact_name || 'Unbekannter Kontakt' }}
                    </h4>
                    <p class="text-sm text-go4-muted dark:text-gray-400">
                      {{ action.context?.contact_position }} bei {{ action.context?.contact_company }}
                    </p>
                  </div>
                </div>

                <!-- Action Type & Pipeline -->
                <div class="mb-3 flex flex-wrap items-center gap-2">
                  <span class="rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-900/50 dark:text-blue-300">
                    {{ action.action_type }}
                  </span>
                  <span
                    v-if="action.context?.pipeline_name"
                    class="rounded-full bg-purple-100 px-2.5 py-0.5 text-xs font-medium text-purple-700 dark:bg-purple-900/50 dark:text-purple-300"
                  >
                    {{ action.context.pipeline_name }}
                  </span>
                  <span
                    :class="[
                      'rounded-full px-2.5 py-0.5 text-xs font-medium',
                      action.priority === 'urgent' ? 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300' :
                      action.priority === 'high' ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/50 dark:text-orange-300' :
                      'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                    ]"
                  >
                    {{ action.priority }}
                  </span>
                </div>

                <!-- Suggested Content -->
                <div
                  v-if="action.suggested_content || action.generated_content"
                  class="rounded-lg bg-gray-50 p-3 dark:bg-gray-700/50"
                >
                  <p class="mb-1 text-xs font-medium text-go4-muted dark:text-gray-400">
                    {{ action.generated_content ? 'Generierter Inhalt' : 'Vorgeschlagener Inhalt' }}
                  </p>
                  <p class="whitespace-pre-wrap text-sm text-go4-secondary dark:text-gray-200">
                    {{ action.generated_content || action.suggested_content }}
                  </p>
                </div>
              </div>

              <!-- Actions -->
              <div class="ml-4 flex flex-col gap-2">
                <button
                  v-if="!action.generated_content"
                  :disabled="store.actionLoading[action.id]"
                  class="flex items-center gap-1.5 rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-100 disabled:opacity-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
                  @click="generateActionContent(action.id)"
                >
                  <svg
                    class="h-4 w-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M13 10V3L4 14h7v7l9-11h-7z"
                    />
                  </svg>
                  Generieren
                </button>
                <button
                  :disabled="store.actionLoading[action.id]"
                  class="flex items-center gap-1.5 rounded-lg bg-go4-primary px-3 py-1.5 text-sm font-medium text-white hover:bg-go4-primary-dark disabled:opacity-50"
                  @click="executeAction(action.id, action.generated_content)"
                >
                  <svg
                    class="h-4 w-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  Freigeben
                </button>
              </div>
            </div>

            <!-- Due Date -->
            <div
              v-if="action.due_at"
              class="mt-3 flex items-center gap-1 text-xs text-go4-muted dark:text-gray-400"
            >
              <svg
                class="h-3.5 w-3.5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              Faellig: {{ new Date(action.due_at).toLocaleDateString('de-DE') }}
            </div>
          </div>
        </div>
      </div>

      <!-- Guide Tab -->
      <div v-else-if="activeTab === 'guide'">
        <div class="grid gap-6 lg:grid-cols-4">
          <!-- Sidebar TOC -->
          <aside class="hidden lg:block">
            <div
              class="sticky top-24 rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
            >
              <h3 class="mb-3 text-sm font-semibold text-go4-secondary dark:text-white">
                Inhaltsverzeichnis
              </h3>
              <nav class="space-y-1 text-sm">
                <a
                  href="#modul-uebersicht"
                  class="block rounded px-2 py-1 text-go4-muted hover:bg-gray-100 hover:text-go4-secondary dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-white"
                >Modul-Uebersicht</a>
                <a
                  href="#accounts-einrichten"
                  class="block rounded px-2 py-1 text-go4-muted hover:bg-gray-100 hover:text-go4-secondary dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-white"
                >Accounts einrichten</a>
                <a
                  href="#scraper-jobs"
                  class="block rounded px-2 py-1 text-go4-muted hover:bg-gray-100 hover:text-go4-secondary dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-white"
                >Scraper Jobs</a>
                <a
                  href="#kontakte-verwalten"
                  class="block rounded px-2 py-1 text-go4-muted hover:bg-gray-100 hover:text-go4-secondary dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-white"
                >Kontakte verwalten</a>
                <a
                  href="#nachrichtenvorlagen"
                  class="block rounded px-2 py-1 text-go4-muted hover:bg-gray-100 hover:text-go4-secondary dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-white"
                >Nachrichtenvorlagen</a>
                <a
                  href="#kampagnen-erstellen"
                  class="block rounded px-2 py-1 text-go4-muted hover:bg-gray-100 hover:text-go4-secondary dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-white"
                >Kampagnen erstellen</a>
                <a
                  href="#inbox--konversationen"
                  class="block rounded px-2 py-1 text-go4-muted hover:bg-gray-100 hover:text-go4-secondary dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-white"
                >Inbox & Konversationen</a>
                <a
                  href="#safety--warmup-system"
                  class="block rounded px-2 py-1 text-go4-muted hover:bg-gray-100 hover:text-go4-secondary dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-white"
                >Safety & Warmup</a>
                <a
                  href="#best-practices"
                  class="block rounded px-2 py-1 text-go4-muted hover:bg-gray-100 hover:text-go4-secondary dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-white"
                >Best Practices</a>
                <a
                  href="#fehlerbehebung"
                  class="block rounded px-2 py-1 text-go4-muted hover:bg-gray-100 hover:text-go4-secondary dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-white"
                >Fehlerbehebung</a>
                <a
                  href="#haeufige-fragen-faq"
                  class="block rounded px-2 py-1 text-go4-muted hover:bg-gray-100 hover:text-go4-secondary dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-white"
                >FAQ</a>
              </nav>
            </div>
          </aside>

          <!-- Main Content -->
          <div class="lg:col-span-3">
            <div
              class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800 sm:p-8"
            >
              <article
                class="guide-content prose prose-slate max-w-none dark:prose-invert"
                v-html="renderedGuide"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Setup Tab -->
      <div v-else-if="activeTab === 'setup'">
        <!-- Safety Limits Info Button -->
        <div class="mb-6 flex items-center justify-between rounded-lg border border-blue-200 bg-blue-50 p-4 dark:border-blue-800 dark:bg-blue-900/20">
          <div class="flex items-center gap-3">
            <div class="flex h-10 w-10 items-center justify-center rounded-full bg-blue-100 text-blue-600 dark:bg-blue-800 dark:text-blue-300">
              <svg
                class="h-5 w-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                />
              </svg>
            </div>
            <div>
              <h4 class="font-medium text-blue-900 dark:text-blue-100">
                Safety Limits
              </h4>
              <p class="text-sm text-blue-700 dark:text-blue-300">
                Automatische Randomisierung fuer menschenaehnliches Verhalten
              </p>
            </div>
          </div>
          <button
            class="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            @click="showSafetyLimits = true"
          >
            <svg
              class="h-4 w-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            Limits anzeigen
          </button>
        </div>

        <ModuleSetupTab
          module="linkedin"
          module-label="LinkedIn"
        />
      </div>

      <!-- Debug Tab -->
      <div v-else-if="activeTab === 'debug'">
        <!-- === Profile Scraper Test === -->
        <div class="mb-6 rounded-lg border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800">
          <h3 class="mb-3 text-lg font-semibold text-gray-900 dark:text-white">
            Profil-Scraper Test
          </h3>
          <p class="mb-4 text-sm text-gray-500 dark:text-gray-400">
            LinkedIn-Profil-URL eingeben, um den Extractor zu testen.
          </p>

          <div class="flex gap-3">
            <input
              v-model="scrapeUrl"
              type="text"
              placeholder="https://www.linkedin.com/in/username/"
              class="flex-1 rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              :disabled="scrapeLoading"
              @keydown.enter="startScrapeTest"
            >
            <button
              class="rounded-lg bg-blue-600 px-6 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
              :disabled="scrapeLoading || !scrapeUrl.trim()"
              @click="startScrapeTest"
            >
              <span
                v-if="scrapeLoading"
                class="flex items-center gap-2"
              >
                <svg
                  class="h-4 w-4 animate-spin"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    class="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    stroke-width="4"
                  />
                  <path
                    class="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                  />
                </svg>
                Scraping...
              </span>
              <span v-else>Start</span>
            </button>
          </div>

          <!-- Error -->
          <div
            v-if="scrapeError"
            class="mt-4 rounded-lg border border-red-300 bg-red-50 p-4 dark:border-red-700 dark:bg-red-900/20"
          >
            <p class="font-medium text-red-700 dark:text-red-300">
              Fehler
            </p>
            <pre class="mt-2 whitespace-pre-wrap text-sm text-red-600 dark:text-red-400">{{ scrapeError }}</pre>
          </div>

          <!-- Result -->
          <div
            v-if="scrapeResult"
            class="mt-4 space-y-4"
          >
            <!-- Steps Log -->
            <div
              v-if="scrapeResult.steps?.length"
              class="rounded-lg border border-gray-200 bg-gray-900 p-3 dark:border-gray-700"
            >
              <div
                v-for="(s, i) in scrapeResult.steps"
                :key="i"
                class="font-mono text-xs leading-relaxed"
                :class="{
                  'text-green-400': s.status === 'ok',
                  'text-yellow-400': s.status === 'warn',
                  'text-red-400': s.status === 'fail',
                  'text-gray-400': s.status === 'start',
                }"
              >
                [{{ s.status.toUpperCase().padEnd(5) }}] {{ s.step }}: {{ s.detail }}
              </div>
            </div>

            <!-- Profile via shared component -->
            <ProfileCard :profile="scrapeResult.profile" />

            <!-- Raw Sections HTML (debug-only) -->
            <details class="rounded-lg border border-gray-200 dark:border-gray-700">
              <summary class="cursor-pointer rounded-t-lg bg-gray-50 px-4 py-3 text-sm font-medium text-gray-700 dark:bg-gray-800 dark:text-gray-300">
                Raw Sections HTML ({{ scrapeResult.found_sections?.length || 0 }})
              </summary>
              <pre class="max-h-96 overflow-auto p-4 font-mono text-xs text-gray-800 dark:text-gray-200">{{ JSON.stringify(scrapeResult.raw_sections, null, 2) }}</pre>
            </details>
          </div>
        </div>

        <hr class="mb-6 border-gray-200 dark:border-gray-700">

        <!-- Debug Toggle -->
        <div class="mb-4 flex items-center gap-4">
          <button
            class="rounded-lg px-5 py-2.5 text-sm font-medium text-white shadow-sm"
            :class="debugActive
              ? 'bg-red-600 hover:bg-red-700'
              : 'bg-green-600 hover:bg-green-700'"
            @click="toggleDebug"
          >
            {{ debugActive ? 'Debug deaktivieren' : 'Debug aktivieren' }}
          </button>
          <span
            v-if="debugActive"
            class="flex items-center gap-2 text-sm text-green-600 dark:text-green-400"
          >
            <span class="inline-block h-2.5 w-2.5 rounded-full bg-green-500 animate-pulse" />
            Aktiv — starte einen Job im Jobs-Tab
          </span>
        </div>

        <!-- Aktueller Schritt -->
        <div
          v-if="debugActive"
          class="mb-4 rounded-lg border-2 border-blue-300 bg-blue-50 p-4 dark:border-blue-700 dark:bg-blue-900/20"
        >
          <div class="mb-2 text-xs font-medium uppercase tracking-wide text-blue-600 dark:text-blue-400">
            Aktueller Schritt
          </div>
          <div
            v-if="debugCurrentStep"
            class="flex items-center justify-between"
          >
            <div>
              <p class="text-lg font-semibold text-gray-900 dark:text-white">
                {{ debugCurrentStep.description }}
              </p>
              <p
                v-if="debugCurrentStep.details"
                class="mt-1 text-sm text-gray-600 dark:text-gray-400"
              >
                {{ debugCurrentStep.details }}
              </p>
            </div>
            <button
              class="ml-4 flex h-12 w-12 items-center justify-center rounded-full bg-green-600 text-white shadow-lg hover:bg-green-700"
              title="Freigeben"
              @click="approveStep"
            >
              <svg
                class="h-6 w-6"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
                />
              </svg>
            </button>
          </div>
          <div
            v-else
            class="text-sm text-gray-500 dark:text-gray-400"
          >
            Warte auf nächsten Schritt...
          </div>
        </div>

        <!-- Autostart -->
        <div
          v-if="debugActive"
          class="mb-4 flex items-center gap-4 rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800"
        >
          <label class="flex items-center gap-2 text-sm">
            <input
              v-model="debugAutostart"
              type="checkbox"
              class="h-4 w-4 rounded border-gray-300 text-blue-600"
            >
            Autostart
          </label>
          <div
            v-if="debugAutostart"
            class="flex items-center gap-2"
          >
            <input
              v-model.number="debugAutoDelay"
              type="number"
              min="100"
              max="30000"
              step="100"
              class="w-24 rounded border border-gray-300 px-2 py-1 text-sm dark:border-gray-600 dark:bg-gray-700"
            >
            <span class="text-sm text-gray-500">ms</span>
          </div>
          <div
            v-if="debugAutostart && debugAutoCountdown > 0"
            class="text-sm text-blue-600 dark:text-blue-400"
          >
            Auto-Freigabe in {{ debugAutoCountdown }}ms...
          </div>
        </div>

        <!-- Finished banner -->
        <div
          v-if="debugFinished"
          class="mb-4 rounded-lg border p-4"
          :class="debugFinished.status === 'completed' ? 'border-green-300 bg-green-50 dark:border-green-700 dark:bg-green-900/20' : 'border-red-300 bg-red-50 dark:border-red-700 dark:bg-red-900/20'"
        >
          <p
            class="font-semibold"
            :class="debugFinished.status === 'completed' ? 'text-green-700 dark:text-green-300' : 'text-red-700 dark:text-red-300'"
          >
            {{ debugFinished.status === 'completed' ? 'Abgeschlossen' : debugFinished.status === 'cancelled' ? 'Abgebrochen' : 'Fehler' }}
          </p>
          <p
            v-if="debugFinished.message"
            class="mt-1 text-sm"
          >
            {{ debugFinished.message }}
          </p>
          <p
            v-if="debugFinished.profiles_scraped !== undefined"
            class="mt-1 text-sm"
          >
            {{ debugFinished.profiles_found || 0 }} gefunden, {{ debugFinished.profiles_scraped }} gespeichert
          </p>
        </div>

        <!-- Log-Fenster -->
        <div class="rounded-lg border border-gray-200 bg-gray-900 dark:border-gray-700">
          <div class="flex items-center justify-between border-b border-gray-700 px-4 py-2">
            <span class="text-sm font-medium text-gray-300">Log</span>
            <button
              class="text-xs text-gray-500 hover:text-gray-300"
              @click="debugLogs = []"
            >
              Löschen
            </button>
          </div>
          <div
            ref="debugLogContainer"
            class="h-96 overflow-y-auto p-4 font-mono text-xs leading-relaxed"
          >
            <div
              v-for="(log, idx) in debugLogs"
              :key="idx"
              class="whitespace-pre-wrap"
              :class="{
                'text-gray-400': log.level === 'info',
                'text-green-400': log.level === 'ok',
                'text-yellow-400': log.level === 'warning',
                'text-red-400': log.level === 'error',
                'text-blue-400': log.level === 'debug',
                'text-cyan-400': log.level === 'step',
              }"
            >
              <span class="text-gray-600">{{ log.time }}</span> <span class="font-bold">{{ log.levelTag }}</span> {{ log.message }}
            </div>
            <div
              v-if="debugLogs.length === 0"
              class="text-gray-600"
            >
              Noch keine Logs...
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Delete Account Confirmation -->
    <ConfirmDialog
      :open="showDeleteAccountConfirm"
      title="Account loeschen?"
      :message="`Moechtest du den Account '${accountToDelete?.name}' wirklich loeschen? Alle zugehoerigen Jobs werden ebenfalls geloescht.`"
      confirm-text="Loeschen"
      variant="danger"
      @confirm="deleteAccount"
      @cancel="showDeleteAccountConfirm = false"
    />

    <!-- Delete Job Confirmation -->
    <ConfirmDialog
      :open="showDeleteJobConfirm"
      title="Job loeschen?"
      :message="`Moechtest du den Job '${jobToDelete?.name}' wirklich loeschen? Alle gescrapten Kontakte werden ebenfalls geloescht.`"
      confirm-text="Loeschen"
      variant="danger"
      @confirm="deleteJob"
      @cancel="showDeleteJobConfirm = false"
    />

    <!-- Delete Template Confirmation -->
    <ConfirmDialog
      :open="showDeleteTemplateConfirm"
      title="Vorlage loeschen?"
      :message="`Moechtest du die Vorlage '${templateToDelete?.name}' wirklich loeschen?`"
      confirm-text="Loeschen"
      variant="danger"
      @confirm="deleteTemplate"
      @cancel="showDeleteTemplateConfirm = false"
    />

    <!-- Delete Campaign Confirmation -->
    <ConfirmDialog
      :open="showDeleteCampaignConfirm"
      title="Kampagne loeschen?"
      :message="`Moechtest du die Kampagne '${campaignToDelete?.name}' wirklich loeschen? Alle zugehoerigen Leads und Aktionen werden ebenfalls geloescht.`"
      confirm-text="Loeschen"
      variant="danger"
      @confirm="deleteCampaign"
      @cancel="showDeleteCampaignConfirm = false"
    />

    <!-- Delete Contact Confirmation -->
    <ConfirmDialog
      :open="showDeleteContactConfirm"
      title="Kontakt loeschen?"
      :message="`Moechtest du den Kontakt '${contactToDelete?.name || 'Unbekannt'}' wirklich loeschen?`"
      confirm-text="Loeschen"
      variant="danger"
      @confirm="deleteContactNow"
      @cancel="showDeleteContactConfirm = false"
    />

    <!-- Delete All Contacts Confirmation -->
    <ConfirmDialog
      :open="showDeleteAllContactsConfirm"
      title="Alle Kontakte loeschen?"
      :message="`Moechtest du wirklich ${filteredContacts.length} Kontakte loeschen? Diese Aktion kann nicht rueckgaengig gemacht werden.`"
      confirm-text="Alle loeschen"
      variant="danger"
      @confirm="deleteAllContacts"
      @cancel="showDeleteAllContactsConfirm = false"
    />

    <!-- Safety Limits Modal -->
    <SafetyLimitsModal
      :open="showSafetyLimits"
      @close="showSafetyLimits = false"
    />
  </div>
</template>

<style scoped>
/* Guide Content Styling */
.guide-content :deep(h1) {
  @apply text-2xl font-bold text-gray-900 dark:text-white border-b border-gray-200 dark:border-gray-700 pb-4 mb-6;
  scroll-margin-top: 120px;
}

.guide-content :deep(h2) {
  @apply text-xl font-semibold text-gray-800 dark:text-gray-100 border-b border-gray-100 dark:border-gray-700 pb-2 mt-10 mb-4;
  scroll-margin-top: 120px;
}

.guide-content :deep(h3) {
  @apply text-lg font-semibold text-gray-800 dark:text-gray-200 mt-6 mb-3;
  scroll-margin-top: 120px;
}

.guide-content :deep(h4) {
  @apply text-base font-medium text-gray-700 dark:text-gray-300 mt-4 mb-2;
  scroll-margin-top: 120px;
}

.guide-content :deep(p) {
  @apply text-gray-600 dark:text-gray-400 leading-relaxed mb-4;
}

.guide-content :deep(ul),
.guide-content :deep(ol) {
  @apply text-gray-600 dark:text-gray-400 mb-4 pl-6;
}

.guide-content :deep(li) {
  @apply mb-1;
}

.guide-content :deep(table) {
  @apply w-full text-sm border-collapse mb-6 rounded-lg overflow-hidden;
}

.guide-content :deep(thead) {
  @apply bg-gray-50 dark:bg-gray-700;
}

.guide-content :deep(th) {
  @apply px-4 py-3 text-left font-semibold text-gray-700 dark:text-gray-200 border-b border-gray-200 dark:border-gray-600;
}

.guide-content :deep(td) {
  @apply px-4 py-3 text-gray-600 dark:text-gray-400 border-b border-gray-100 dark:border-gray-700;
}

.guide-content :deep(tbody tr:hover) {
  @apply bg-gray-50 dark:bg-gray-800/50;
}

.guide-content :deep(code) {
  @apply bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200 px-1.5 py-0.5 rounded text-sm font-mono;
}

.guide-content :deep(pre) {
  @apply bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto mb-4;
}

.guide-content :deep(pre code) {
  @apply bg-transparent p-0 text-inherit;
}

.guide-content :deep(blockquote) {
  @apply border-l-4 border-go4-primary bg-orange-50 dark:bg-orange-900/20 pl-4 py-2 pr-4 my-4 text-gray-700 dark:text-gray-300 rounded-r;
}

.guide-content :deep(hr) {
  @apply border-gray-200 dark:border-gray-700 my-8;
}

.guide-content :deep(a) {
  @apply text-go4-primary hover:underline;
}

.guide-content :deep(strong) {
  @apply font-semibold text-gray-800 dark:text-gray-200;
}
</style>
