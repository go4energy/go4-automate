<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCustomerJourneyStore } from '@/stores/customerJourney'
import { getDashboardFeed, getImportFields, importPreview, importExecute } from '@/api/customerJourney'
import PageHeader from '@/components/ui/PageHeader.vue'
import SearchInput from '@/components/ui/SearchInput.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import ModuleSettings from '@/components/settings/ModuleSettings.vue'

const route = useRoute()
const router = useRouter()
const store = useCustomerJourneyStore()

const activeTab = computed(() => route.meta?.tab || 'dashboard')

const tabs = [
  { key: 'dashboard', label: 'Dashboard', route: '/customer-journey' },
  { key: 'refs', label: 'Ref-Codes', route: '/customer-journey/ref-codes' },
  { key: 'campaigns', label: 'Kampagnen', route: '/customer-journey/campaigns' },
  { key: 'einstellungen', label: 'Einstellungen', route: '/customer-journey/einstellungen' },
]

// Activity mode: 'time' (flat live feed) or 'lead' (tree grouped by lead).
// Default 'lead' when arriving via /customer-journey/leads (legacy route)
// or when ?mode=lead is set in URL.
const initialMode = (() => {
  if (route.query?.mode === 'lead') return 'lead'
  if (route.name === 'customer-journey-leads') return 'lead'
  return 'time'
})()
store.setActivityMode(initialMode)
const activityMode = computed(() => store.activityMode)

function setMode(mode) {
  store.setActivityMode(mode)
  // Reflect mode in URL so reload + bookmarks keep state, without leaving
  // the dashboard tab.
  if (activeTab.value === 'dashboard') {
    const next = { ...route.query }
    if (mode === 'lead') next.mode = 'lead'
    else delete next.mode
    router.replace({ path: route.path, query: next })
  }
  loadActivityForMode()
}

const leadFeedFilter = ref({ category: '', journey_status: '', search: '' })

async function loadActivityForMode() {
  if (activityMode.value === 'lead') {
    await store.fetchFeedByLead({
      limit: feedPageSize,
      events_per_lead: 10,
      category: leadFeedFilter.value.category || undefined,
      journey_status: leadFeedFilter.value.journey_status || undefined,
      search: leadFeedFilter.value.search || undefined,
    })
  } else {
    feedHasMore.value = true
    await store.fetchFeed(feedPageSize)
  }
}

// Search
const searchQuery = ref('')

// Modals
const showRefModal = ref(false)
const showBulkRefModal = ref(false)
const showGenerateModal = ref(false)
const showCampaignModal = ref(false)
const showDeleteDialog = ref(false)
const deleteTarget = ref(null)
const deleteType = ref('')

// Ref-Code Form
const refForm = ref({ name: '', context: '', target_url: '', campaign_id: null, ref_code: '', contact_id: null })

// Generate form
const generateForm = ref({ count: 100, campaign_id: null, target_url: '', utm_source: '', utm_medium: '', utm_campaign: '', prefix: '' })
const generateLoading = ref(false)

async function generateAndDownload() {
  generateLoading.value = true
  try {
    const { data } = await getDashboardFeed({ limit: 0 }) // dummy to get api instance
  } catch {}
  try {
    const api = (await import('@/api')).default
    const response = await api.post('/v1/customer-journey/refs/generate', generateForm.value, { responseType: 'blob' })
    const blob = new Blob([response.data], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `ref-codes-${generateForm.value.count}.csv`
    a.click()
    window.URL.revokeObjectURL(url)
    showGenerateModal.value = false
    await store.fetchRefCodes()
    await store.fetchStats()
  } catch (err) {
    alert('Fehler beim Generieren: ' + (err.message || err))
  } finally {
    generateLoading.value = false
  }
}

// ============== CSV Import Wizard ==============
const showImportWizard = ref(false)
const importStep = ref(1) // 1=upload, 2=mapping, 3=conflicts, 4=done
const importLoading = ref(false)
const importError = ref(null)
const importCsvRaw = ref('')
const importCsvHeaders = ref([])
const importBaseUrl = ref('')
const importCampaignId = ref(null)
const importUtmSource = ref('')
const importUtmMedium = ref('')
const importUtmCampaign = ref('')
const importMapping = ref({}) // {csv_col: target_field}
const importMappableFields = ref([])
const importPreviewData = ref(null)
const importConflictResolutions = ref({}) // {row_index: "skip"|"update"|"duplicate"}

function resetImportWizard() {
  importStep.value = 1
  importLoading.value = false
  importError.value = null
  importCsvRaw.value = ''
  importCsvHeaders.value = []
  importBaseUrl.value = ''
  importCampaignId.value = null
  importUtmSource.value = ''
  importUtmMedium.value = ''
  importUtmCampaign.value = ''
  importMapping.value = {}
  importPreviewData.value = null
  importConflictResolutions.value = {}
}

async function openImportWizard() {
  resetImportWizard()
  await store.fetchCampaigns()
  try {
    const { data } = await getImportFields()
    importMappableFields.value = data
  } catch { /* use fallback */ }
  showImportWizard.value = true
}

function onImportFileSelected(e) {
  const file = e.target.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = (ev) => {
    importCsvRaw.value = ev.target.result
    // Parse headers from first line
    const firstLine = importCsvRaw.value.split('\n')[0]
    const delim = firstLine.includes(';') ? ';' : firstLine.includes('\t') ? '\t' : ','
    importCsvHeaders.value = firstLine.split(delim).map(h => h.trim().replace(/^"|"$/g, ''))
    // Auto-map known columns
    const autoMap = {
      full_name: 'name', first_name: '_first_name', last_name: '_last_name',
      email: 'email', phone: 'phone', mobile: 'mobile',
      job_position: 'position', position: 'position',
      profile_linkedin: 'linkedin', linkedin: 'linkedin',
      twitter: 'twitter', source: 'source', notes: 'notes',
    }
    const mapped = {}
    for (const h of importCsvHeaders.value) {
      const lower = h.toLowerCase().trim()
      if (autoMap[lower]) {
        mapped[h] = autoMap[lower]
      }
    }
    importMapping.value = mapped
  }
  reader.readAsText(file, 'utf-8')
}

function mappingTargetOptions() {
  const opts = [
    { value: '', label: '— Nicht importieren —' },
    { value: '_first_name', label: 'Vorname (für Namenszusammenführung)' },
    { value: '_last_name', label: 'Nachname (für Namenszusammenführung)' },
  ]
  for (const f of importMappableFields.value) {
    opts.push({ value: f.key, label: `${f.label} (${f.group})` })
  }
  opts.push({ value: 'custom:', label: 'Custom Field (Name = Spaltenname)' })
  return opts
}

function getMappingValue(header) {
  const val = importMapping.value[header]
  if (val && val.startsWith('custom:')) return 'custom:'
  return val || ''
}

function setMappingValue(header, value) {
  if (value === 'custom:') {
    importMapping.value[header] = `custom:${header}`
  } else if (value === '') {
    delete importMapping.value[header]
  } else {
    importMapping.value[header] = value
  }
}

async function runImportPreview() {
  importLoading.value = true
  importError.value = null
  try {
    const { data } = await importPreview({
      csv_raw: importCsvRaw.value,
      mapping: importMapping.value,
    })
    importPreviewData.value = data
    // Pre-set all conflicts to "skip"
    for (const c of data.conflicts) {
      importConflictResolutions.value[String(c.row_index)] = 'skip'
    }
    importStep.value = 3
  } catch (err) {
    importError.value = err.response?.data?.detail || err.message
  } finally {
    importLoading.value = false
  }
}

async function runImportExecute() {
  if (!importBaseUrl.value) {
    importError.value = 'Bitte Basis-Link eingeben'
    return
  }
  importLoading.value = true
  importError.value = null
  try {
    const response = await importExecute({
      csv_raw: importCsvRaw.value,
      mapping: importMapping.value,
      base_url: importBaseUrl.value,
      campaign_id: importCampaignId.value,
      conflict_resolutions: importConflictResolutions.value,
      utm_source: importUtmSource.value || null,
      utm_medium: importUtmMedium.value || null,
      utm_campaign: importUtmCampaign.value || null,
    })
    // Download the CSV blob
    const blob = new Blob([response.data], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'import-with-reflinks.csv'
    a.click()
    window.URL.revokeObjectURL(url)
    importStep.value = 4
    await store.fetchRefCodes()
    await store.fetchStats()
  } catch (err) {
    importError.value = err.response?.data?.detail || err.message
  } finally {
    importLoading.value = false
  }
}

// Contact search for ref-code linking
const contactSearch = ref('')
const contactResults = ref([])
const selectedContact = ref(null)
const contactSearchLoading = ref(false)
let contactSearchTimeout = null

async function searchContacts(query) {
  if (!query || query.length < 2) {
    contactResults.value = []
    return
  }
  contactSearchLoading.value = true
  try {
    const { getContacts } = await import('@/api/contacts')
    const { data } = await getContacts({ search: query, limit: 10 })
    contactResults.value = data
  } catch {
    contactResults.value = []
  } finally {
    contactSearchLoading.value = false
  }
}

function onContactSearchInput() {
  clearTimeout(contactSearchTimeout)
  contactSearchTimeout = setTimeout(() => searchContacts(contactSearch.value), 300)
}

function selectContact(contact) {
  selectedContact.value = contact
  refForm.value.contact_id = contact.id
  refForm.value.name = refForm.value.name || contact.name
  contactSearch.value = ''
  contactResults.value = []
}

function clearSelectedContact() {
  selectedContact.value = null
  refForm.value.contact_id = null
}
const bulkRefForm = ref({ lines: '', campaign_id: null, target_url: '' })

// Campaign Form
const campaignForm = ref({ name: '', channel: '', description: '' })
const editingCampaignId = ref(null)

// Feed pagination + infinite scroll
const feedPageSize = 50
const feedHasMore = ref(true)
const feedLoadingMore = ref(false)
const feedScrollContainer = ref(null)

async function loadMoreFeed() {
  if (feedLoadingMore.value || !feedHasMore.value) return
  feedLoadingMore.value = true
  try {
    const offset = store.feed.length
    const params = { limit: feedPageSize, offset }
    if (store.feedSourceFilter) params.source_site = store.feedSourceFilter
    const { data } = await getDashboardFeed(params)
    if (data.length < feedPageSize) feedHasMore.value = false
    store.feed.push(...data)
  } catch { /* ignore */ }
  finally { feedLoadingMore.value = false }
}

const feedScrolledDown = ref(false)

function onFeedScroll(e) {
  const el = e.target
  const wasScrolledDown = feedScrolledDown.value
  feedScrolledDown.value = el.scrollTop > 5

  // User scrolled back to top → refresh immediately
  if (wasScrolledDown && !feedScrolledDown.value) {
    refreshNewEvents()
    refreshCountdown.value = REFRESH_INTERVAL
  }

  if (el.scrollTop + el.clientHeight >= el.scrollHeight - 100) {
    loadMoreFeed()
  }
}

// Ref edit
const editingRefId = ref(null)

// Auto-refresh (Dashboard tab)
const REFRESH_INTERVAL = 30 // seconds
const refreshCountdown = ref(REFRESH_INTERVAL)
let refreshTimer = null
let countdownTimer = null

async function refreshNewEvents() {
  await store.fetchStats()
  if (activityMode.value === 'lead') {
    await store.fetchFeedByLead({
      limit: feedPageSize,
      events_per_lead: 10,
      category: leadFeedFilter.value.category || undefined,
      journey_status: leadFeedFilter.value.journey_status || undefined,
      search: leadFeedFilter.value.search || undefined,
    })
    return
  }
  const oldFeed = [...store.feed]
  await store.fetchFeed(feedPageSize)
  if (oldFeed.length > 0 && store.feed.length > 0) {
    // Re-append older events that were already loaded beyond first page
    const newIds = new Set(store.feed.map(e => e.id))
    const olderEvents = oldFeed.filter(e => !newIds.has(e.id))
    if (olderEvents.length > 0) {
      store.feed.push(...olderEvents)
    }
  }
}

function startAutoRefresh() {
  stopAutoRefresh()
  refreshCountdown.value = REFRESH_INTERVAL
  countdownTimer = setInterval(() => {
    if (feedScrolledDown.value) return
    refreshCountdown.value--
    if (refreshCountdown.value <= 0) {
      refreshCountdown.value = REFRESH_INTERVAL
    }
  }, 1000)
  refreshTimer = setInterval(async () => {
    if (feedScrolledDown.value) return
    await refreshNewEvents()
    refreshCountdown.value = REFRESH_INTERVAL
  }, REFRESH_INTERVAL * 1000)
}

function stopAutoRefresh() {
  if (refreshTimer) { clearInterval(refreshTimer); refreshTimer = null }
  if (countdownTimer) { clearInterval(countdownTimer); countdownTimer = null }
}

onUnmounted(() => stopAutoRefresh())

function resetRefForm() {
  refForm.value = { name: '', context: '', target_url: '', campaign_id: null, ref_code: '', contact_id: null, utm_source: '', utm_medium: '', utm_campaign: '' }
  editingRefId.value = null
  selectedContact.value = null
  contactSearch.value = ''
  contactResults.value = []
}

function resetCampaignForm() {
  campaignForm.value = { name: '', channel: '', description: '' }
  editingCampaignId.value = null
}

// Load data based on tab
async function loadTabData() {
  if (activeTab.value === 'dashboard') {
    await store.fetchStats()
    await loadActivityForMode()
  } else if (activeTab.value === 'refs') {
    await store.fetchRefCodes({ search: searchQuery.value || undefined })
  } else if (activeTab.value === 'campaigns') {
    await store.fetchCampaigns()
  }
}

watch(activeTab, () => {
  searchQuery.value = ''
  loadTabData()
  if (activeTab.value === 'dashboard') {
    startAutoRefresh()
  } else {
    stopAutoRefresh()
  }
})

watch(searchQuery, () => {
  if (activeTab.value === 'refs') {
    loadTabData()
  }
})

onMounted(() => {
  loadTabData()
  store.fetchStats()
  store.fetchFeedSources()
  if (activeTab.value === 'dashboard') {
    startAutoRefresh()
  }
})

async function onSourceFilterChange(value) {
  store.setFeedSourceFilter(value)
  feedHasMore.value = true
  if (activityMode.value === 'lead') {
    await loadActivityForMode()
  } else {
    await store.fetchFeed(feedPageSize)
  }
}

let leadFilterTimer = null
function onLeadFilterChange() {
  clearTimeout(leadFilterTimer)
  leadFilterTimer = setTimeout(() => loadActivityForMode(), 300)
}

function relativeFromNow(iso) {
  if (!iso) return '-'
  const then = new Date(iso.endsWith('Z') ? iso : iso + 'Z').getTime()
  const diff = Math.max(0, Date.now() - then)
  const min = Math.round(diff / 60000)
  if (min < 1) return 'jetzt'
  if (min < 60) return `vor ${min}m`
  const h = Math.round(min / 60)
  if (h < 24) return `vor ${h}h`
  const d = Math.round(h / 24)
  return `vor ${d}d`
}

// Ref-Code actions
async function saveRef() {
  if (editingRefId.value) {
    await store.editRefCode(editingRefId.value, refForm.value)
  } else {
    await store.addRefCode(refForm.value)
  }
  showRefModal.value = false
  resetRefForm()
  await store.fetchStats()
}

async function saveBulkRefs() {
  await store.addBulkRefCodes(bulkRefForm.value)
  showBulkRefModal.value = false
  bulkRefForm.value = { lines: '', campaign_id: null, target_url: '' }
  await store.fetchStats()
}

function editRef(ref) {
  refForm.value = { name: ref.name, context: ref.context, target_url: ref.target_url, campaign_id: ref.campaign_id, ref_code: ref.ref_code }
  editingRefId.value = ref.id
  showRefModal.value = true
}

function copyRefLink(ref) {
  const base = ref.target_url || 'https://go4.energy'
  const sep = base.includes('?') ? '&' : '?'
  const params = [`ref=${ref.ref_code}`]
  if (ref.utm_source) params.push(`utm_source=${ref.utm_source}`)
  if (ref.utm_medium) params.push(`utm_medium=${ref.utm_medium}`)
  if (ref.utm_campaign) params.push(`utm_campaign=${ref.utm_campaign}`)
  navigator.clipboard.writeText(`${base}${sep}${params.join('&')}`)
}

// Campaign actions
async function saveCampaign() {
  if (editingCampaignId.value) {
    await store.editCampaign(editingCampaignId.value, campaignForm.value)
  } else {
    await store.addCampaign(campaignForm.value)
  }
  showCampaignModal.value = false
  resetCampaignForm()
  await store.fetchStats()
}

function editCampaign(campaign) {
  campaignForm.value = { name: campaign.name, channel: campaign.channel || '', description: campaign.description || '' }
  editingCampaignId.value = campaign.id
  showCampaignModal.value = true
}

// Delete
function confirmDelete(item, type) {
  deleteTarget.value = item
  deleteType.value = type
  showDeleteDialog.value = true
}

async function executeDelete() {
  if (deleteType.value === 'ref') {
    await store.removeRefCode(deleteTarget.value.id)
  } else if (deleteType.value === 'campaign') {
    await store.removeCampaign(deleteTarget.value.id)
  }
  showDeleteDialog.value = false
  deleteTarget.value = null
  await store.fetchStats()
}

// Helpers
function toLocal(dateStr) {
  if (!dateStr) return null
  // Server returns naive UTC timestamps — append Z so browser converts to local
  return new Date(dateStr.endsWith('Z') ? dateStr : dateStr + 'Z')
}

function formatDate(dateStr) {
  const d = toLocal(dateStr)
  if (!d) return '-'
  return d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function formatDateShort(dateStr) {
  const d = toLocal(dateStr)
  if (!d) return '-'
  return d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: '2-digit' })
}

function eventLabel(event) {
  const map = {
    page_visit: 'Seitenaufruf',
    ref_link_click: 'Ref-Link Klick',
    return_visit: 'Wiederkehr',
    konfigurator_start: 'Konfigurator gestartet',
    konfigurator_step: 'Konfigurator Schritt',
    konfigurator_complete: 'Anfrage abgeschickt',
    konfigurator_mode_sunfi: 'Konfigurator: Sunfi-Modus',
    konfigurator_mode_manual: 'Konfigurator: Manuell',
    config_link_visit: 'Config-Link besucht',
    quote_pdf_download: 'Angebot PDF',
    ems_simulation: 'EMS Simulation',
    ems_simulation_complete: 'EMS Simulation abgeschlossen',
    ems_step_pv: 'EMS: PV-Anlage',
    ems_step_battery: 'EMS: Batterie',
    ems_step_running: 'EMS: Simulation läuft',
    ems_tab_simulation: 'EMS: Tab Simulation',
    ems_tab_ergebnisse: 'EMS: Tab Ergebnisse',
    ems_tab_parameter: 'EMS: Tab Parameter',
    ems_tab_zeitreihen: 'EMS: Tab Zeitreihen',
    ems_tab_empfehlungen: 'EMS: Tab Empfehlungen',
    ems_save_config: 'EMS: Config gespeichert',
    ems_lead_verified: 'EMS: Lead verifiziert',
    ems_pdf_download: 'EMS PDF',
    contact_form: 'Kontaktformular',
    spot_simulation: 'Spotpreis-Simulator',
    spot_simulation_start: 'Spot: Simulation gestartet',
    spot_simulation_complete: 'Spot: Simulation fertig',
    chat_started: 'Chat gestartet',
    quote_viewed: 'Angebot eingesehen',
    identify: 'Identifiziert',
    interest_detected: 'Interesse erkannt',
  }
  return map[event] || event
}

function returnVisitColor(days) {
  if (!days || days <= 1) return null
  if (days <= 7) return 'text-emerald-600 bg-emerald-50 dark:text-emerald-400 dark:bg-emerald-900/30'
  if (days <= 14) return 'text-yellow-600 bg-yellow-50 dark:text-yellow-400 dark:bg-yellow-900/30'
  if (days <= 30) return 'text-amber-600 bg-amber-50 dark:text-amber-400 dark:bg-amber-900/30'
  if (days <= 60) return 'text-orange-600 bg-orange-50 dark:text-orange-400 dark:bg-orange-900/30'
  return 'text-red-600 bg-red-50 dark:text-red-400 dark:bg-red-900/30'
}

function categoryColor(category) {
  const map = {
    awareness: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    engagement: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
    conversion: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    retention: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  }
  return map[category] || 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
}

function statusColor(status) {
  const map = {
    new: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    active: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    converted: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
    lost: 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400',
  }
  return map[status] || 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
}
</script>

<template>
  <div class="space-y-6">
    <PageHeader
      title="Customer Journey"
    />

    <!-- Tabs + Search -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <nav class="flex gap-1 border-b border-gray-200 dark:border-gray-700">
        <router-link
          v-for="tab in tabs"
          :key="tab.key"
          :to="tab.route"
          class="px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors"
          :class="activeTab === tab.key
            ? 'border-go4-primary text-go4-primary'
            : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'"
        >
          {{ tab.label }}
        </router-link>
      </nav>

      <div class="flex items-center gap-3">
        <SearchInput
          v-if="activeTab === 'leads' || activeTab === 'refs'"
          v-model="searchQuery"
          placeholder="Suchen..."
          class="w-64"
        />
        <button
          v-if="activeTab === 'refs'"
          class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark"
          @click="resetRefForm(); store.fetchCampaigns(); showRefModal = true"
        >
          + Ref-Code
        </button>
        <button
          v-if="activeTab === 'refs'"
          class="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
          @click="showBulkRefModal = true"
        >
          Bulk-Import
        </button>
        <button
          v-if="activeTab === 'refs'"
          class="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
          @click="store.fetchCampaigns(); showGenerateModal = true"
        >
          Generieren + CSV
        </button>
        <button
          v-if="activeTab === 'refs'"
          class="rounded-lg border border-emerald-500 px-4 py-2 text-sm font-medium text-emerald-600 dark:text-emerald-400 hover:bg-emerald-50 dark:hover:bg-emerald-900/20"
          @click="openImportWizard"
        >
          CSV Import + Ref-Links
        </button>
        <button
          v-if="activeTab === 'campaigns'"
          class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark"
          @click="resetCampaignForm(); showCampaignModal = true"
        >
          + Kampagne
        </button>
      </div>
    </div>

    <!-- Loading (not for dashboard — it has its own loading states) -->
    <div
      v-if="store.loading && activeTab !== 'dashboard'"
      class="flex items-center justify-center p-12"
    >
      <span class="text-go4-muted dark:text-gray-400">Laden...</span>
    </div>

    <!-- Error -->
    <div
      v-else-if="store.error"
      class="rounded-lg bg-red-50 dark:bg-red-900/20 p-4 text-red-700 dark:text-red-400"
    >
      {{ store.error }}
    </div>

    <!-- ============ DASHBOARD TAB ============ -->
    <template v-else-if="activeTab === 'dashboard'">
      <!-- Stats Cards -->
      <div
        v-if="store.stats"
        class="grid grid-cols-2 md:grid-cols-4 gap-4"
      >
        <div class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
          <div class="text-2xl font-bold text-gray-900 dark:text-white">
            {{ store.stats.leads_total }}
          </div>
          <div class="text-sm text-gray-500 dark:text-gray-400">
            Leads gesamt
          </div>
          <div class="mt-1 text-xs text-green-600">
            +{{ store.stats.leads_new_week }} diese Woche
          </div>
        </div>
        <div class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
          <div class="text-2xl font-bold text-gray-900 dark:text-white">
            {{ store.stats.events_today }}
          </div>
          <div class="text-sm text-gray-500 dark:text-gray-400">
            Events heute
          </div>
          <div class="mt-1 text-xs text-gray-400">
            {{ store.stats.events_week }} diese Woche
          </div>
        </div>
        <div class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
          <div class="text-2xl font-bold text-green-600">
            {{ store.stats.conversions_week }}
          </div>
          <div class="text-sm text-gray-500 dark:text-gray-400">
            Conversions
          </div>
          <div class="mt-1 text-xs text-gray-400">
            diese Woche
          </div>
        </div>
        <div class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
          <div class="text-2xl font-bold text-gray-900 dark:text-white">
            {{ store.stats.ref_codes_total }}
          </div>
          <div class="text-sm text-gray-500 dark:text-gray-400">
            Ref-Codes
          </div>
          <div class="mt-1 text-xs text-gray-400">
            {{ store.stats.campaigns_active }} Kampagnen aktiv
          </div>
        </div>
      </div>

      <!-- Activity Panel -->
      <div
        class="flex flex-col rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
        style="min-height: calc(100vh - 360px)"
      >
        <div class="flex flex-wrap items-center justify-between gap-3 border-b border-gray-200 dark:border-gray-700 px-4 py-3 shrink-0">
          <div class="flex items-center gap-3">
            <!-- Mode Toggle -->
            <div class="inline-flex rounded-md border border-gray-200 dark:border-gray-700 p-0.5">
              <button
                type="button"
                class="px-3 py-1 text-xs font-medium rounded transition-colors"
                :class="activityMode === 'time'
                  ? 'bg-go4-primary text-white'
                  : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'"
                @click="setMode('time')"
              >
                Zeitlich
              </button>
              <button
                type="button"
                class="px-3 py-1 text-xs font-medium rounded transition-colors"
                :class="activityMode === 'lead'
                  ? 'bg-go4-primary text-white'
                  : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'"
                @click="setMode('lead')"
              >
                Pro Lead
              </button>
            </div>
            <span
              v-if="activityMode === 'time'"
              class="text-xs text-gray-400"
            >{{ store.feed.length }} Events</span>
            <span
              v-else
              class="text-xs text-gray-400"
            >{{ store.feedByLead.length }} Leads</span>
          </div>
          <div class="flex flex-wrap items-center gap-3">
            <!-- Lead-mode filters -->
            <template v-if="activityMode === 'lead'">
              <input
                v-model="leadFeedFilter.search"
                type="text"
                placeholder="Name / E-Mail"
                class="rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-2 py-1 text-xs text-gray-700 dark:text-gray-200 w-40"
                @input="onLeadFilterChange"
              >
              <select
                v-model="leadFeedFilter.category"
                class="rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-2 py-1 text-xs text-gray-700 dark:text-gray-200"
                @change="onLeadFilterChange"
              >
                <option value="">
                  Alle Kategorien
                </option>
                <option value="awareness">
                  Awareness
                </option>
                <option value="engagement">
                  Engagement
                </option>
                <option value="conversion">
                  Conversion
                </option>
                <option value="retention">
                  Retention
                </option>
              </select>
              <select
                v-model="leadFeedFilter.journey_status"
                class="rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-2 py-1 text-xs text-gray-700 dark:text-gray-200"
                @change="onLeadFilterChange"
              >
                <option value="">
                  Alle Status
                </option>
                <option value="new">
                  Neu
                </option>
                <option value="active">
                  Aktiv
                </option>
                <option value="converted">
                  Converted
                </option>
                <option value="lost">
                  Lost
                </option>
              </select>
              <button
                type="button"
                class="text-xs text-gray-500 hover:text-go4-primary"
                @click="store.expandAllLeads()"
              >
                Alle aufklappen
              </button>
              <button
                type="button"
                class="text-xs text-gray-500 hover:text-go4-primary"
                @click="store.collapseAllLeads()"
              >
                Alle einklappen
              </button>
            </template>
            <select
              v-if="store.feedSources.length > 1"
              :value="store.feedSourceFilter || ''"
              class="rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-2 py-1 text-xs text-gray-700 dark:text-gray-200"
              @change="onSourceFilterChange($event.target.value)"
            >
              <option value="">
                Alle Quellen
              </option>
              <option
                v-for="src in store.feedSources"
                :key="src"
                :value="src"
              >
                {{ src }}
              </option>
            </select>
            <div class="relative h-5 w-5">
              <svg
                class="h-5 w-5 -rotate-90"
                viewBox="0 0 20 20"
              >
                <circle
                  cx="10"
                  cy="10"
                  r="8"
                  fill="none"
                  stroke="currentColor"
                  class="text-gray-200 dark:text-gray-700"
                  stroke-width="2"
                />
                <circle
                  cx="10"
                  cy="10"
                  r="8"
                  fill="none"
                  stroke="currentColor"
                  class="text-go4-primary transition-all duration-1000 ease-linear"
                  stroke-width="2"
                  stroke-dasharray="50.27"
                  :stroke-dashoffset="50.27 * (1 - refreshCountdown / REFRESH_INTERVAL)"
                  stroke-linecap="round"
                />
              </svg>
            </div>
            <span class="text-xs text-gray-400 tabular-nums">{{ refreshCountdown }}s</span>
          </div>
        </div>
        <div
          v-if="store.feedLoading"
          class="flex-1 flex items-center justify-center text-gray-500 dark:text-gray-400"
        >
          Laden...
        </div>
        <div
          v-else-if="store.feed.length === 0"
          class="flex-1 flex items-center justify-center text-gray-500 dark:text-gray-400"
        >
          Noch keine Events
        </div>
        <!-- TIME MODE: flat live feed -->
        <div
          v-else-if="activityMode === 'time'"
          ref="feedScrollContainer"
          class="overflow-y-auto"
          style="max-height: calc(100vh - 360px)"
          @scroll="onFeedScroll"
        >
          <table class="min-w-full">
            <thead class="bg-gray-50 dark:bg-gray-700/50 sticky top-0 z-10">
              <tr>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase w-36">
                  Zeit
                </th>
                <th
                  class="px-2 py-2 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase w-10"
                  title="Tage seit letztem Besuch"
                >
                  ↻
                </th>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase w-24">
                  Kategorie
                </th>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase w-48">
                  Event
                </th>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase w-28">
                  Quelle
                </th>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  Lead
                </th>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  Seite
                </th>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  UTM
                </th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100 dark:divide-gray-700">
              <tr
                v-for="event in store.feed"
                :key="event.id"
                class="hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer"
                @click="event.contact_id && router.push(`/customer-journey/leads/${event.contact_id}`)"
              >
                <td class="px-4 py-2 text-xs text-gray-400 tabular-nums whitespace-nowrap">
                  {{ formatDate(event.created_at) }}
                </td>
                <td class="px-2 py-2 text-center">
                  <span
                    v-if="event.days_since_last_visit"
                    class="inline-flex items-center justify-center rounded-full min-w-[1.25rem] h-5 px-1 text-[10px] font-bold tabular-nums"
                    :class="returnVisitColor(event.days_since_last_visit)"
                    :title="`${event.days_since_last_visit} Tage seit letztem Besuch`"
                  >
                    {{ event.days_since_last_visit }}
                  </span>
                </td>
                <td class="px-4 py-2">
                  <span
                    class="inline-flex rounded-full px-2 py-0.5 text-xs font-medium"
                    :class="categoryColor(event.category)"
                  >
                    {{ event.category }}
                  </span>
                </td>
                <td class="px-4 py-2 text-sm text-gray-900 dark:text-white whitespace-nowrap">
                  {{ eventLabel(event.event) }}
                  <span
                    v-if="event.metadata_ && event.metadata_.config_hash"
                    class="ml-1 text-xs font-mono text-go4-primary"
                  >{{ event.metadata_.config_hash }}</span>
                </td>
                <td class="px-4 py-2 text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">
                  {{ event.source_site || '—' }}
                </td>
                <td class="px-4 py-2 text-sm text-gray-500 dark:text-gray-400 truncate max-w-xs">
                  <template v-if="event.contact_name">
                    {{ event.contact_name }}
                    <span
                      v-if="event.contact_email"
                      class="text-xs text-gray-400 ml-1"
                    >{{ event.contact_email }}</span>
                  </template>
                  <span
                    v-else
                    class="text-gray-300 dark:text-gray-600"
                  >—</span>
                </td>
                <td class="px-4 py-2 text-xs text-gray-400 truncate max-w-xs">
                  {{ event.page_path || '—' }}
                </td>
                <td class="px-4 py-2 text-xs text-gray-400 whitespace-nowrap">
                  <template v-if="event.utm_source || event.utm_campaign">
                    <span
                      v-if="event.utm_source"
                      class="text-gray-500"
                    >{{ event.utm_source }}</span>
                    <span
                      v-if="event.utm_medium"
                      class="text-gray-400"
                    > / {{ event.utm_medium }}</span>
                    <span
                      v-if="event.utm_campaign"
                      class="ml-1 text-go4-primary"
                    >{{ event.utm_campaign }}</span>
                  </template>
                  <span
                    v-else
                    class="text-gray-300 dark:text-gray-600"
                  >—</span>
                </td>
              </tr>
            </tbody>
          </table>
          <!-- Infinite scroll indicator -->
          <div
            v-if="feedLoadingMore"
            class="p-3 text-center text-xs text-gray-400"
          >
            Laden...
          </div>
          <div
            v-else-if="!feedHasMore && store.feed.length > 0"
            class="p-3 text-center text-xs text-gray-400"
          >
            Alle Events geladen
          </div>
        </div>

        <!-- LEAD MODE: tree grouped by lead, ordered by most recent event -->
        <div
          v-else-if="activityMode === 'lead'"
          class="overflow-y-auto"
          style="max-height: calc(100vh - 360px)"
        >
          <div
            v-if="store.feedByLead.length === 0"
            class="flex items-center justify-center p-8 text-gray-500 dark:text-gray-400"
          >
            Keine Leads im aktuellen Filter
          </div>
          <div
            v-else
            class="divide-y divide-gray-100 dark:divide-gray-700"
          >
            <div
              v-for="leadRow in store.feedByLead"
              :key="leadRow.id"
            >
              <!-- Lead header row -->
              <div
                class="flex items-center gap-3 px-4 py-2 hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer"
                @click="store.toggleLead(leadRow.id)"
              >
                <button
                  type="button"
                  class="text-gray-400 hover:text-go4-primary shrink-0"
                  :title="store.isLeadExpanded(leadRow.id) ? 'Einklappen' : 'Aufklappen'"
                >
                  <svg
                    class="h-4 w-4 transition-transform"
                    :class="store.isLeadExpanded(leadRow.id) ? 'rotate-90' : ''"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M9 5l7 7-7 7"
                    />
                  </svg>
                </button>
                <span
                  class="text-sm font-medium text-gray-900 dark:text-white hover:text-go4-primary"
                  @click.stop="router.push(`/customer-journey/leads/${leadRow.id}`)"
                >
                  {{ leadRow.name }}
                </span>
                <span class="text-xs text-gray-500 dark:text-gray-400">{{ leadRow.email }}</span>
                <span
                  class="inline-flex rounded-full px-2 py-0.5 text-xs font-medium"
                  :class="statusColor(leadRow.journey_status)"
                >
                  {{ leadRow.journey_status || 'new' }}
                </span>
                <span class="text-xs text-gray-400 tabular-nums">{{ leadRow.event_count }} Events</span>
                <span class="ml-auto text-xs text-gray-400 tabular-nums">{{ relativeFromNow(leadRow.last_event_at) }}</span>
              </div>

              <!-- Expanded events -->
              <div
                v-if="store.isLeadExpanded(leadRow.id)"
                class="bg-gray-50 dark:bg-gray-900/30 pl-12 pr-4 py-2"
              >
                <table class="min-w-full">
                  <tbody class="divide-y divide-gray-200/50 dark:divide-gray-700/50">
                    <tr
                      v-for="event in leadRow.events"
                      :key="event.id"
                      class="text-xs"
                    >
                      <td class="py-1 pr-3 text-gray-400 tabular-nums whitespace-nowrap w-32">
                        {{ formatDate(event.created_at) }}
                      </td>
                      <td class="py-1 pr-3 w-24">
                        <span
                          class="inline-flex rounded-full px-2 py-0.5 font-medium"
                          :class="categoryColor(event.category)"
                        >
                          {{ event.category }}
                        </span>
                      </td>
                      <td class="py-1 pr-3 text-gray-900 dark:text-gray-100 whitespace-nowrap">
                        {{ eventLabel(event.event) }}
                      </td>
                      <td class="py-1 pr-3 text-gray-400 truncate">
                        {{ event.page_path || '—' }}
                      </td>
                      <td class="py-1 text-gray-400 whitespace-nowrap">
                        <template v-if="event.utm_source || event.utm_campaign">
                          <span
                            v-if="event.utm_source"
                            class="text-gray-500"
                          >{{ event.utm_source }}</span>
                          <span
                            v-if="event.utm_campaign"
                            class="ml-1 text-go4-primary"
                          >{{ event.utm_campaign }}</span>
                        </template>
                      </td>
                    </tr>
                  </tbody>
                </table>
                <div
                  v-if="leadRow.event_count > leadRow.events.length"
                  class="mt-2 text-xs text-gray-400"
                >
                  + {{ leadRow.event_count - leadRow.events.length }} weitere Events —
                  <button
                    type="button"
                    class="text-go4-primary hover:underline"
                    @click.stop="router.push(`/customer-journey/leads/${leadRow.id}`)"
                  >
                    auf Detailseite zeigen
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- ============ REF-CODES TAB ============ -->
    <template v-else-if="activeTab === 'refs'">
      <EmptyState
        v-if="store.refCodes.length === 0"
        title="Keine Ref-Codes"
        description="Erstelle Ref-Codes für personalisierte Kampagnen-Links."
      />
      <div
        v-else
        class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden"
      >
        <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead class="bg-gray-50 dark:bg-gray-700/50">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                Code
              </th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                Name
              </th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                Kontext
              </th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                Besuche
              </th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                Erstellt
              </th>
              <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                Aktionen
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
            <tr
              v-for="ref in store.refCodes"
              :key="ref.id"
              class="hover:bg-gray-50 dark:hover:bg-gray-700/50"
            >
              <td class="px-4 py-3">
                <code class="rounded bg-gray-100 dark:bg-gray-700 px-2 py-0.5 text-sm font-mono text-go4-primary">{{ ref.ref_code }}</code>
              </td>
              <td class="px-4 py-3 text-sm text-gray-900 dark:text-white">
                {{ ref.name || '-' }}
              </td>
              <td class="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                {{ ref.context || '-' }}
              </td>
              <td class="px-4 py-3 text-sm font-medium text-gray-900 dark:text-white">
                {{ ref.visit_count }}
              </td>
              <td class="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                {{ formatDateShort(ref.created_at) }}
              </td>
              <td class="px-4 py-3 text-right">
                <div class="flex items-center justify-end gap-2">
                  <button
                    class="text-gray-400 hover:text-go4-primary"
                    title="Link kopieren"
                    @click="copyRefLink(ref)"
                  >
                    <svg
                      class="h-4 w-4"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    ><path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                    /></svg>
                  </button>
                  <button
                    class="text-gray-400 hover:text-go4-primary"
                    title="Bearbeiten"
                    @click="editRef(ref)"
                  >
                    <svg
                      class="h-4 w-4"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    ><path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                    /></svg>
                  </button>
                  <button
                    class="text-gray-400 hover:text-red-500"
                    title="Löschen"
                    @click="confirmDelete(ref, 'ref')"
                  >
                    <svg
                      class="h-4 w-4"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    ><path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                    /></svg>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <!-- ============ CAMPAIGNS TAB ============ -->
    <template v-else-if="activeTab === 'campaigns'">
      <EmptyState
        v-if="store.campaigns.length === 0"
        title="Keine Kampagnen"
        description="Erstelle Kampagnen um Ref-Codes zu gruppieren."
      />
      <div
        v-else
        class="grid gap-4 md:grid-cols-2 lg:grid-cols-3"
      >
        <div
          v-for="campaign in store.campaigns"
          :key="campaign.id"
          class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
        >
          <div class="flex items-start justify-between">
            <div>
              <h3 class="font-medium text-gray-900 dark:text-white">
                {{ campaign.name }}
              </h3>
              <p
                v-if="campaign.channel"
                class="mt-1 text-sm text-gray-500 dark:text-gray-400"
              >
                {{ campaign.channel }}
              </p>
            </div>
            <span
              class="inline-flex rounded-full px-2 py-0.5 text-xs font-medium"
              :class="campaign.status === 'active' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' : 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400'"
            >
              {{ campaign.status }}
            </span>
          </div>
          <p
            v-if="campaign.description"
            class="mt-2 text-sm text-gray-500 dark:text-gray-400"
          >
            {{ campaign.description }}
          </p>
          <div class="mt-3 flex items-center justify-between">
            <span class="text-xs text-gray-400">{{ formatDateShort(campaign.created_at) }}</span>
            <div class="flex items-center gap-2">
              <button
                class="text-sm text-go4-primary hover:underline"
                @click="editCampaign(campaign)"
              >
                Bearbeiten
              </button>
              <button
                class="text-sm text-red-500 hover:underline"
                @click="confirmDelete(campaign, 'campaign')"
              >
                Löschen
              </button>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- ============ EINSTELLUNGEN TAB ============ -->
    <template v-else-if="activeTab === 'einstellungen'">
      <ModuleSettings module-name="customer_journey" />
    </template>

    <!-- ============ MODALS ============ -->

    <!-- Ref-Code Modal -->
    <Teleport to="body">
      <div
        v-if="showRefModal"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
        @click.self="showRefModal = false"
      >
        <div class="w-full max-w-md rounded-lg bg-white dark:bg-gray-800 p-6 shadow-xl">
          <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4">
            {{ editingRefId ? 'Ref-Code bearbeiten' : 'Neuer Ref-Code' }}
          </h3>
          <div class="space-y-3">
            <!-- Contact Search -->
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Kontakt verknüpfen</label>
              <div
                v-if="selectedContact"
                class="flex items-center gap-2 rounded-lg border border-go4-primary/30 bg-go4-primary/5 dark:bg-go4-primary/10 px-3 py-2"
              >
                <div class="flex-1">
                  <div class="text-sm font-medium text-gray-900 dark:text-white">
                    {{ selectedContact.name }}
                  </div>
                  <div class="text-xs text-gray-500 dark:text-gray-400">
                    {{ selectedContact.email }}
                  </div>
                </div>
                <button
                  class="text-gray-400 hover:text-red-500"
                  @click="clearSelectedContact"
                >
                  <svg
                    class="h-4 w-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  ><path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M6 18L18 6M6 6l12 12"
                  /></svg>
                </button>
              </div>
              <div
                v-else
                class="relative"
              >
                <input
                  v-model="contactSearch"
                  type="text"
                  placeholder="Kontakt suchen (Name oder E-Mail)..."
                  class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white"
                  @input="onContactSearchInput"
                >
                <div
                  v-if="contactSearchLoading"
                  class="absolute right-3 top-2.5 text-xs text-gray-400"
                >
                  ...
                </div>
                <div
                  v-if="contactResults.length > 0"
                  class="absolute z-10 mt-1 w-full rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 shadow-lg max-h-48 overflow-y-auto"
                >
                  <button
                    v-for="c in contactResults"
                    :key="c.id"
                    class="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-gray-50 dark:hover:bg-gray-700"
                    @click="selectContact(c)"
                  >
                    <div>
                      <div class="text-sm font-medium text-gray-900 dark:text-white">
                        {{ c.name }}
                      </div>
                      <div class="text-xs text-gray-500 dark:text-gray-400">
                        {{ c.email }}
                      </div>
                    </div>
                  </button>
                </div>
              </div>
              <p class="mt-1 text-xs text-gray-400">
                Optional — ohne Kontakt wird der Code beim ersten Klick zugeordnet
              </p>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Name / Label</label>
              <input
                v-model="refForm.name"
                type="text"
                placeholder="z.B. Florian Müller"
                class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white"
              >
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Kontext</label>
              <input
                v-model="refForm.context"
                type="text"
                placeholder="z.B. Newsletter März"
                class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white"
              >
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Ziel-URL (optional)</label>
              <input
                v-model="refForm.target_url"
                type="url"
                placeholder="https://go4.energy/photovoltaik"
                class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white"
              >
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Kampagne (optional)</label>
              <select
                v-model="refForm.campaign_id"
                class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white"
              >
                <option :value="null">
                  -- Keine Kampagne --
                </option>
                <option
                  v-for="c in store.campaigns"
                  :key="c.id"
                  :value="c.id"
                >
                  {{ c.name }}
                </option>
              </select>
            </div>
            <details class="text-sm">
              <summary class="cursor-pointer text-gray-500 dark:text-gray-400 hover:text-gray-700">
                UTM-Parameter (optional)
              </summary>
              <div class="mt-2 space-y-2">
                <input
                  v-model="refForm.utm_source"
                  type="text"
                  placeholder="utm_source (z.B. linkedin)"
                  class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white"
                >
                <input
                  v-model="refForm.utm_medium"
                  type="text"
                  placeholder="utm_medium (z.B. messaging)"
                  class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white"
                >
                <input
                  v-model="refForm.utm_campaign"
                  type="text"
                  placeholder="utm_campaign (z.B. speicher_maerz)"
                  class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white"
                >
              </div>
            </details>
          </div>
          <div class="mt-4 flex justify-end gap-3">
            <button
              class="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm text-gray-700 dark:text-gray-300"
              @click="showRefModal = false"
            >
              Abbrechen
            </button>
            <button
              class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark"
              @click="saveRef"
            >
              Speichern
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Bulk Ref Import Modal -->
    <Teleport to="body">
      <div
        v-if="showBulkRefModal"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
        @click.self="showBulkRefModal = false"
      >
        <div class="w-full max-w-md rounded-lg bg-white dark:bg-gray-800 p-6 shadow-xl">
          <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Bulk-Import
          </h3>
          <p class="text-sm text-gray-500 dark:text-gray-400 mb-3">
            Eine Zeile pro Ref-Code. Format: <code>Name;Kontext</code>
          </p>
          <textarea
            v-model="bulkRefForm.lines"
            rows="8"
            placeholder="Florian Müller;LinkedIn Post&#10;Anna Schmidt;Newsletter März&#10;Max Huber"
            class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white font-mono"
          />
          <div class="mt-4 flex justify-end gap-3">
            <button
              class="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm text-gray-700 dark:text-gray-300"
              @click="showBulkRefModal = false"
            >
              Abbrechen
            </button>
            <button
              class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark"
              @click="saveBulkRefs"
            >
              Importieren
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Campaign Modal -->
    <Teleport to="body">
      <div
        v-if="showCampaignModal"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
        @click.self="showCampaignModal = false"
      >
        <div class="w-full max-w-md rounded-lg bg-white dark:bg-gray-800 p-6 shadow-xl">
          <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4">
            {{ editingCampaignId ? 'Kampagne bearbeiten' : 'Neue Kampagne' }}
          </h3>
          <div class="space-y-3">
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Name</label>
              <input
                v-model="campaignForm.name"
                type="text"
                placeholder="z.B. LinkedIn März 2026"
                class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white"
              >
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Kanal</label>
              <select
                v-model="campaignForm.channel"
                class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white"
              >
                <option value="">
                  -- Kein Kanal --
                </option>
                <option value="linkedin">
                  LinkedIn
                </option>
                <option value="email">
                  E-Mail
                </option>
                <option value="whatsapp">
                  WhatsApp
                </option>
                <option value="website">
                  Website
                </option>
                <option value="other">
                  Sonstiges
                </option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Beschreibung</label>
              <textarea
                v-model="campaignForm.description"
                rows="3"
                class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white"
              />
            </div>
          </div>
          <div class="mt-4 flex justify-end gap-3">
            <button
              class="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm text-gray-700 dark:text-gray-300"
              @click="showCampaignModal = false"
            >
              Abbrechen
            </button>
            <button
              class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark"
              @click="saveCampaign"
            >
              Speichern
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Generate Ref-Codes Modal -->
    <Teleport to="body">
      <div
        v-if="showGenerateModal"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
        @click.self="showGenerateModal = false"
      >
        <div class="w-full max-w-md rounded-lg bg-white dark:bg-gray-800 p-6 shadow-xl">
          <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Ref-Codes generieren + CSV
          </h3>
          <div class="space-y-3">
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Anzahl</label>
              <input
                v-model.number="generateForm.count"
                type="number"
                min="1"
                max="5000"
                class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white"
              >
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Kampagne (optional)</label>
              <select
                v-model="generateForm.campaign_id"
                class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white"
              >
                <option :value="null">
                  -- Keine Kampagne --
                </option>
                <option
                  v-for="c in store.campaigns"
                  :key="c.id"
                  :value="c.id"
                >
                  {{ c.name }}
                </option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Ziel-URL</label>
              <input
                v-model="generateForm.target_url"
                type="url"
                placeholder="https://go4.energy/photovoltaik"
                class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white"
              >
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Prefix (optional)</label>
              <input
                v-model="generateForm.prefix"
                type="text"
                placeholder="z.B. LI_"
                class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white"
              >
              <p class="mt-1 text-xs text-gray-400">
                Wird dem Code vorangestellt, z.B. LI_xK9mQ2
              </p>
            </div>
            <details class="text-sm">
              <summary class="cursor-pointer text-gray-500 dark:text-gray-400 hover:text-gray-700">
                UTM-Parameter (optional)
              </summary>
              <div class="mt-2 space-y-2">
                <input
                  v-model="generateForm.utm_source"
                  type="text"
                  placeholder="utm_source (z.B. linkedin)"
                  class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white"
                >
                <input
                  v-model="generateForm.utm_medium"
                  type="text"
                  placeholder="utm_medium (z.B. social)"
                  class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white"
                >
                <input
                  v-model="generateForm.utm_campaign"
                  type="text"
                  placeholder="utm_campaign (z.B. speicher_maerz)"
                  class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white"
                >
              </div>
            </details>
          </div>
          <div class="mt-4 flex justify-end gap-3">
            <button
              class="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm text-gray-700 dark:text-gray-300"
              @click="showGenerateModal = false"
            >
              Abbrechen
            </button>
            <button
              class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark disabled:opacity-50"
              :disabled="generateLoading || !generateForm.count"
              @click="generateAndDownload"
            >
              {{ generateLoading ? 'Generiere...' : `${generateForm.count} Codes generieren` }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Delete Confirm -->
    <ConfirmDialog
      :open="showDeleteDialog"
      title="Löschen bestätigen"
      :message="`Möchtest du ${deleteType === 'ref' ? 'diesen Ref-Code' : 'diese Kampagne'} wirklich löschen?`"
      confirm-text="Löschen"
      variant="danger"
      @confirm="executeDelete"
      @cancel="showDeleteDialog = false"
    />

    <!-- ============ CSV Import Wizard ============ -->
    <Teleport to="body">
      <div
        v-if="showImportWizard"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
        @click.self="showImportWizard = false"
      >
        <div class="bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-3xl max-h-[85vh] overflow-y-auto p-6">
          <!-- Header -->
          <div class="flex items-center justify-between mb-6">
            <h3 class="text-lg font-medium text-gray-900 dark:text-white">
              CSV Import + Ref-Links
              <span class="ml-2 text-sm text-gray-400">Schritt {{ importStep }}/4</span>
            </h3>
            <button
              class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              @click="showImportWizard = false"
            >
              &times;
            </button>
          </div>

          <!-- Error -->
          <div
            v-if="importError"
            class="mb-4 rounded-lg bg-red-50 dark:bg-red-900/20 p-3 text-sm text-red-700 dark:text-red-400"
          >
            {{ importError }}
          </div>

          <!-- Step 1: Upload + Config -->
          <div
            v-if="importStep === 1"
            class="space-y-4"
          >
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">CSV-Datei</label>
              <input
                type="file"
                accept=".csv,.txt"
                class="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-go4-primary file:text-white hover:file:bg-go4-primary-dark"
                @change="onImportFileSelected"
              >
            </div>
            <div
              v-if="importCsvHeaders.length > 0"
              class="text-sm text-gray-500 dark:text-gray-400"
            >
              {{ importCsvHeaders.length }} Spalten erkannt, {{ importCsvRaw.split('\n').length - 1 }} Zeilen
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Kampagne</label>
              <select
                v-model="importCampaignId"
                class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white"
              >
                <option :value="null">
                  — Keine —
                </option>
                <option
                  v-for="c in store.campaigns"
                  :key="c.id"
                  :value="c.id"
                >
                  {{ c.name }}
                </option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Basis-Link</label>
              <input
                v-model="importBaseUrl"
                type="text"
                placeholder="https://go4.energy/angebot?utm_campaign=..."
                class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white"
              >
              <p class="mt-1 text-xs text-gray-400">
                Ref-Code wird als ?ref=XXXXXX angehängt
              </p>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">UTM-Parameter <span class="text-gray-400 font-normal">(optional, für Pixel/Analytics)</span></label>
              <div class="grid grid-cols-3 gap-2">
                <input
                  v-model="importUtmSource"
                  type="text"
                  placeholder="utm_source"
                  class="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white"
                >
                <input
                  v-model="importUtmMedium"
                  type="text"
                  placeholder="utm_medium"
                  class="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white"
                >
                <input
                  v-model="importUtmCampaign"
                  type="text"
                  placeholder="utm_campaign"
                  class="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white"
                >
              </div>
              <p class="mt-1 text-xs text-gray-400">
                Werden nicht in den Link geschrieben, aber beim Klick via Tracking-API an das Website-Script übergeben
              </p>
            </div>
            <div class="flex justify-end">
              <button
                class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark disabled:opacity-50"
                :disabled="!importCsvHeaders.length || !importBaseUrl"
                @click="importStep = 2"
              >
                Weiter: Spalten zuordnen
              </button>
            </div>
          </div>

          <!-- Step 2: Column Mapping -->
          <div
            v-if="importStep === 2"
            class="space-y-4"
          >
            <p class="text-sm text-gray-500 dark:text-gray-400">
              Ordne die CSV-Spalten den Kontakt-Feldern zu:
            </p>
            <div class="space-y-2 max-h-96 overflow-y-auto">
              <div
                v-for="header in importCsvHeaders"
                :key="header"
                class="flex items-center gap-3"
              >
                <span
                  class="w-44 text-sm font-mono text-gray-700 dark:text-gray-300 truncate"
                  :title="header"
                >{{ header }}</span>
                <span class="text-gray-400">→</span>
                <select
                  :value="getMappingValue(header)"
                  class="flex-1 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-1.5 text-sm text-gray-900 dark:text-white"
                  @change="setMappingValue(header, $event.target.value)"
                >
                  <option
                    v-for="opt in mappingTargetOptions()"
                    :key="opt.value"
                    :value="opt.value"
                  >
                    {{ opt.label }}
                  </option>
                </select>
              </div>
            </div>
            <div class="flex justify-between">
              <button
                class="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm text-gray-700 dark:text-gray-300"
                @click="importStep = 1"
              >
                Zurück
              </button>
              <button
                class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark disabled:opacity-50"
                :disabled="importLoading || Object.keys(importMapping).length === 0"
                @click="runImportPreview"
              >
                {{ importLoading ? 'Prüfe...' : 'Weiter: Vorschau + Konflikte' }}
              </button>
            </div>
          </div>

          <!-- Step 3: Preview + Conflicts -->
          <div
            v-if="importStep === 3 && importPreviewData"
            class="space-y-4"
          >
            <!-- Stats -->
            <div class="grid grid-cols-3 gap-3">
              <div class="rounded-lg bg-green-50 dark:bg-green-900/20 p-3 text-center">
                <div class="text-2xl font-bold text-green-600 dark:text-green-400">
                  {{ importPreviewData.new_count }}
                </div>
                <div class="text-xs text-green-700 dark:text-green-300">
                  Neue Kontakte
                </div>
              </div>
              <div class="rounded-lg bg-yellow-50 dark:bg-yellow-900/20 p-3 text-center">
                <div class="text-2xl font-bold text-yellow-600 dark:text-yellow-400">
                  {{ importPreviewData.conflict_count }}
                </div>
                <div class="text-xs text-yellow-700 dark:text-yellow-300">
                  Konflikte
                </div>
              </div>
              <div class="rounded-lg bg-gray-50 dark:bg-gray-700/50 p-3 text-center">
                <div class="text-2xl font-bold text-gray-600 dark:text-gray-300">
                  {{ importPreviewData.row_count }}
                </div>
                <div class="text-xs text-gray-500 dark:text-gray-400">
                  Zeilen gesamt
                </div>
              </div>
            </div>

            <!-- Conflicts -->
            <div v-if="importPreviewData.conflicts.length > 0">
              <h4 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Konflikte (LinkedIn-URL bereits vorhanden)
              </h4>
              <div class="space-y-2 max-h-64 overflow-y-auto">
                <div
                  v-for="conflict in importPreviewData.conflicts"
                  :key="conflict.row_index"
                  class="rounded-lg border border-yellow-200 dark:border-yellow-800 bg-yellow-50/50 dark:bg-yellow-900/10 p-3"
                >
                  <div class="flex items-start justify-between gap-3">
                    <div class="flex-1 min-w-0">
                      <div class="text-sm font-medium text-gray-900 dark:text-white">
                        CSV: {{ conflict.mapped_data.name || '—' }}
                      </div>
                      <div class="text-xs text-gray-500 dark:text-gray-400 truncate">
                        {{ conflict.mapped_data.linkedin || '' }}
                      </div>
                      <div class="mt-1 text-xs text-yellow-700 dark:text-yellow-400">
                        Existiert: {{ conflict.existing_contact.name }} ({{ conflict.existing_contact.email }})
                      </div>
                    </div>
                    <select
                      :value="importConflictResolutions[String(conflict.row_index)]"
                      class="w-36 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-2 py-1 text-xs text-gray-900 dark:text-white"
                      @change="importConflictResolutions[String(conflict.row_index)] = $event.target.value"
                    >
                      <option value="skip">
                        Überspringen
                      </option>
                      <option value="update">
                        Aktualisieren
                      </option>
                      <option value="duplicate">
                        Duplikat anlegen
                      </option>
                    </select>
                  </div>
                </div>
              </div>
              <!-- Bulk actions for conflicts -->
              <div class="mt-2 flex gap-2">
                <button
                  class="text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 underline"
                  @click="importPreviewData.conflicts.forEach(c => importConflictResolutions[String(c.row_index)] = 'skip')"
                >
                  Alle überspringen
                </button>
                <button
                  class="text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 underline"
                  @click="importPreviewData.conflicts.forEach(c => importConflictResolutions[String(c.row_index)] = 'update')"
                >
                  Alle aktualisieren
                </button>
                <button
                  class="text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 underline"
                  @click="importPreviewData.conflicts.forEach(c => importConflictResolutions[String(c.row_index)] = 'duplicate')"
                >
                  Alle als Duplikat
                </button>
              </div>
            </div>

            <div class="flex justify-between">
              <button
                class="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm text-gray-700 dark:text-gray-300"
                @click="importStep = 2"
              >
                Zurück
              </button>
              <button
                class="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
                :disabled="importLoading"
                @click="runImportExecute"
              >
                {{ importLoading ? 'Importiere...' : `Import starten + CSV herunterladen` }}
              </button>
            </div>
          </div>

          <!-- Step 4: Done -->
          <div
            v-if="importStep === 4"
            class="text-center py-8 space-y-4"
          >
            <div class="text-4xl">
              &#10003;
            </div>
            <h4 class="text-lg font-medium text-gray-900 dark:text-white">
              Import abgeschlossen!
            </h4>
            <p class="text-sm text-gray-500 dark:text-gray-400">
              Die CSV mit Ref-Links wurde heruntergeladen.
            </p>
            <button
              class="rounded-lg bg-go4-primary px-6 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark"
              @click="showImportWizard = false"
            >
              Schließen
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
