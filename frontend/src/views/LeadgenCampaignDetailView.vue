<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useLeadgenStore } from '@/stores/leadgen'
import { previewEnrichRun } from '@/api/leadgen'
import PageHeader from '@/components/ui/PageHeader.vue'
import LeadgenRunStageTimeline from '@/components/leadgen/LeadgenRunStageTimeline.vue'
import LeadgenMap from '@/components/leadgen/LeadgenMap.vue'

const props = defineProps({
  id: { type: [String, Number], default: null }
})

const route = useRoute()
const router = useRouter()
const store = useLeadgenStore()

const campaignId = computed(() => props.id || route.params.id)
const starting = ref(false)
const statusErr = ref(null)

const activeTab = computed(() => route.meta?.tab || 'details')

// Places sub-tab state
const placesStatusFilter = ref('')
const placesPage = ref(1)
const placesPageSize = ref(50)
const placesSortBy = ref('match')
const placesSortDir = ref('desc')
const placesTotalPages = computed(() => {
  const total = store.places.total || 0
  return Math.max(1, Math.ceil(total / placesPageSize.value))
})

function toggleSort(column) {
  if (placesSortBy.value === column) {
    placesSortDir.value = placesSortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    placesSortBy.value = column
    // Sensible defaults: text columns ascending, numeric descending.
    placesSortDir.value = ['name', 'city', 'status'].includes(column)
      ? 'asc'
      : 'desc'
  }
  placesPage.value = 1
}

function sortIndicator(column) {
  if (placesSortBy.value !== column) return ''
  return placesSortDir.value === 'asc' ? '▲' : '▼'
}

function placeStatusBadge(status) {
  const base = 'inline-flex px-2 py-0.5 text-xs font-medium rounded'
  switch (status) {
    case 'discovered':
      return `${base} bg-gray-100 text-gray-700`
    case 'impressum_done':
      return `${base} bg-blue-100 text-blue-800`
    case 'impressum_failed':
      return `${base} bg-red-100 text-red-700`
    case 'llm_done':
      return `${base} bg-green-100 text-green-800`
    case 'llm_failed':
      return `${base} bg-red-100 text-red-700`
    case 'enrolled':
      return `${base} bg-purple-100 text-purple-800`
    case 'rejected':
      return `${base} bg-gray-200 text-gray-500`
    case 'no_website':
      return `${base} bg-amber-100 text-amber-800`
    default:
      return `${base} bg-gray-100 text-gray-700`
  }
}

const resumeDialog = ref({ open: false, runId: null, additionalBudget: 2000, busy: false })

// Unified Run-Modal — replaces the legacy "Run starten" + "🤖 Anreichern…"
// pair. Each stage is a separate checkbox so the operator can mix-and-match
// (e.g. "places only" for fast Apollo export, "linkedin only" for backfill,
// or full pipeline). Cost estimate updates live and is based on the
// campaign's actual eligible-pool size (clamped by the user's limit) so the
// $-figure reflects what the worker will really do, not a pauschal guess.
//
// costPerLead is in cents/lead. linkedin is ~3 Serper calls per place
// (1 company + Ø 2 contacts) × $0.0003, so ~0.09 cents/lead.
// apollo is per-contact (not per-place): 1 export credit ≈ $0.20 overage =
// 20 cents/contact at the worst case.
const STAGE_DEFS = [
  { key: 'places', label: 'Google Places (Discovery)', costPerLead: 1.7 },
  { key: 'impressum', label: 'Impressum-Scraping', costPerLead: 0 },
  { key: 'verify', label: 'Website-Verifikation (Serper)', costPerLead: 0.03 },
  { key: 'llm', label: 'LLM-Bewertung (Anthropic Haiku)', costPerLead: 1.05 },
  { key: 'linkedin', label: 'LinkedIn-Anreicherung (Serper + Gender)', costPerLead: 0.09 },
  { key: 'apollo', label: 'Apollo-Anreicherung (LinkedIn-Match)', costPerLead: 0 }
]

const runDialog = ref({
  open: false,
  selectedStages: ['places', 'impressum', 'verify', 'llm', 'linkedin'],
  limit: 100,
  sampling: 'top_rated',
  // Optional LLM-score filter. Empty string = no filter; the backend treats
  // null/empty the same way. Re-fetches the live preview count on change.
  minMatchScore: '',
  // Persons-only by default; toggle to also burn ~1 Serper call per place
  // for the company URL. The pilot showed Firmen-URLs are a much smaller
  // share of useful outreach data than per-person URLs.
  enrichCompanies: false,
  // Apollo: only enrich contacts that already have a LinkedIn URL.
  // Higher match-rate, fewer wasted credits — recommended for a pilot.
  apolloValidateExistingUrls: false,
  // Reveal-Flags — each consumes additional Apollo credits on top of the
  // base export credit. Email is unlimited on Pro Monthly so it's free;
  // phone is capped at 100/mo and requires a webhook URL configured.
  apolloRevealEmail: false,
  apolloRevealPhone: false,
  // Live preview from /runs/enrich/preview. ``previewCount`` = Firmen
  // (places), ``previewContactCount`` = Personen (leadgen_contacts),
  // ``previewApolloCount`` = Apollo-eligible Personen.
  previewCount: null,
  previewContactCount: null,
  previewApolloCount: null,
  previewLoading: false,
  busy: false,
  error: null
})

const runDialogIsEnrich = computed(
  () => runDialog.value.open && !runDialog.value.selectedStages.includes('places')
)

// Per-control visibility — only show a knob when at least one selected stage
// actually honours it. Truth table:
//   - limit  (max_override): used by llm + linkedin stages
//   - sampling (top_rated/random): used by llm stage only
//   - min_match_score: used by linkedin stage only (filters on llm output)
const showRunLimit = computed(
  () =>
    runDialogIsEnrich.value &&
    (runDialog.value.selectedStages.includes('llm') ||
      runDialog.value.selectedStages.includes('linkedin') ||
      runDialog.value.selectedStages.includes('apollo'))
)
const showRunSampling = computed(
  () => runDialogIsEnrich.value && runDialog.value.selectedStages.includes('llm')
)
const showMinMatchScore = computed(
  () =>
    runDialog.value.selectedStages.includes('linkedin') ||
    runDialog.value.selectedStages.includes('apollo')
)
const showApolloOptions = computed(
  () => runDialog.value.selectedStages.includes('apollo')
)

// How many places the run will actually touch.
// - Full run (places ON): user's limit is the *target* new-lead count.
// - Enrich run (places OFF): use the live preview-count (= eligible pool
//   after stage + min-score filter), capped by the user's limit.
const runDialogPlaceCount = computed(() => {
  const limit = Math.max(runDialog.value.limit || 0, 0)
  if (!runDialogIsEnrich.value) {
    return limit || 100
  }
  const pool =
    runDialog.value.previewCount ??
    enrichEligibleCount.value ??
    stats.value?.total_places ??
    0
  if (limit === 0) return pool
  return Math.min(limit, pool)
})

// Per-stage breakdown so the modal can show "places: $1.70, linkedin: $0.09"
// rather than a single opaque number. The linkedin stage is special: it
// scales by *contacts* (persons) plus an optional per-place company query.
//
// Apollo (Basic Plan): 2.500 free credits/month + $0.02/credit overage.
// Per-match cost depends on which reveals are enabled:
//   - Match-only         : 1 credit
//   - + Email reveal     : +1 credit  → 2 total
//   - + Phone reveal     : +8 credits → 9 total
//   - + Email + Phone    : +9 credits → 10 total
// Assumed match-rate: 70% of eligible contacts (Pilot-Hochrechnung).
const APOLLO_BASIC_FREE_CREDITS = 2500
const APOLLO_BASIC_OVERAGE_CENTS = 2  // $0.02 per overage credit
const APOLLO_PROJECTED_MATCH_RATE = 0.7
const runDialogStageCosts = computed(() => {
  const places = runDialogPlaceCount.value
  const persons = runDialog.value.previewContactCount ?? places
  const apolloPersons =
    runDialog.value.previewApolloCount ??
    (runDialog.value.apolloValidateExistingUrls ? Math.round(persons * 0.4) : persons)
  return STAGE_DEFS.filter((s) => runDialog.value.selectedStages.includes(s.key)).map((s) => {
    let cents
    if (s.key === 'linkedin') {
      // 0.03 cents per Serper call. Persons-only = 1 call/contact; +company
      // = +1 call/place.
      const callsPerPlace = runDialog.value.enrichCompanies ? 1 : 0
      cents = 0.03 * (persons + callsPerPlace * places)
    } else if (s.key === 'apollo') {
      const eligible = Math.min(apolloPersons, runDialog.value.limit || apolloPersons)
      const expectedMatches = Math.round(eligible * APOLLO_PROJECTED_MATCH_RATE)
      let creditsPerMatch = 1
      if (runDialog.value.apolloRevealEmail) creditsPerMatch += 1
      if (runDialog.value.apolloRevealPhone) creditsPerMatch += 8
      const totalCredits = expectedMatches * creditsPerMatch
      const overage = Math.max(0, totalCredits - APOLLO_BASIC_FREE_CREDITS)
      // This is best-case: assumes the entire month's free allotment is
      // available. If the operator has already burned credits today the
      // real cost is higher — but we'd need a credit-balance API to know.
      cents = overage * APOLLO_BASIC_OVERAGE_CENTS
    } else {
      cents = s.costPerLead * places
    }
    return {
      key: s.key,
      label: s.label,
      cents,
      usd: (cents / 100).toFixed(2)
    }
  })
})

const runDialogEstimatedCost = computed(() => {
  const cents = runDialogStageCosts.value.reduce((sum, s) => sum + s.cents, 0)
  return (cents / 100).toFixed(2)
})

const handoffDialog = ref({
  open: false,
  minScore: 7,
  limit: 100,
  includeWithoutEmail: true,
  busy: false,
  error: null,
  preview: null,
  result: null
})

function openHandoffDialog() {
  handoffDialog.value = {
    open: true,
    minScore: 7,
    limit: 100,
    includeWithoutEmail: true,
    busy: false,
    error: null,
    preview: null,
    result: null
  }
  refreshHandoffPreview()
}

function closeHandoffDialog() {
  if (handoffDialog.value.busy) return
  handoffDialog.value.open = false
}

async function refreshHandoffPreview() {
  handoffDialog.value.busy = true
  handoffDialog.value.error = null
  try {
    const data = await store.handoffPreview(campaignId.value, {
      min_score: handoffDialog.value.minScore,
      limit: handoffDialog.value.limit,
      include_without_email: handoffDialog.value.includeWithoutEmail
    })
    handoffDialog.value.preview = data
  } catch (e) {
    handoffDialog.value.error =
      e.response?.data?.detail || e.message || 'Vorschau fehlgeschlagen'
  } finally {
    handoffDialog.value.busy = false
  }
}

async function confirmHandoff() {
  handoffDialog.value.busy = true
  handoffDialog.value.error = null
  try {
    const data = await store.handoffExecute(campaignId.value, {
      min_score: handoffDialog.value.minScore,
      limit: handoffDialog.value.limit,
      include_without_email: handoffDialog.value.includeWithoutEmail
    })
    handoffDialog.value.result = data
    await loadAll()
  } catch (e) {
    handoffDialog.value.error =
      e.response?.data?.detail || e.message || 'Handoff fehlgeschlagen'
  } finally {
    handoffDialog.value.busy = false
  }
}

const exportDialog = ref({
  open: false,
  minScore: 7,
  limit: 10000,
  onlyEnrolled: false,
  preview: null,
  busy: false,
  busyKind: null,
  error: null
})

function openExportDialog() {
  exportDialog.value = {
    open: true,
    minScore: 7,
    limit: 10000,
    onlyEnrolled: false,
    preview: null,
    busy: false,
    busyKind: null,
    error: null
  }
  refreshExportPreview()
}

function closeExportDialog() {
  if (exportDialog.value.busy) return
  exportDialog.value.open = false
}

async function refreshExportPreview() {
  exportDialog.value.busy = true
  exportDialog.value.error = null
  try {
    const data = await store.exportPreview(campaignId.value, {
      min_score: exportDialog.value.minScore,
      limit: exportDialog.value.limit,
      only_enrolled: exportDialog.value.onlyEnrolled
    })
    exportDialog.value.preview = data
  } catch (e) {
    exportDialog.value.error =
      e.response?.data?.detail || e.message || 'Vorschau fehlgeschlagen'
  } finally {
    exportDialog.value.busy = false
  }
}

async function downloadExport(kind) {
  exportDialog.value.busy = true
  exportDialog.value.busyKind = kind
  exportDialog.value.error = null
  try {
    await store.exportDownload(campaignId.value, kind, {
      min_score: exportDialog.value.minScore,
      limit: exportDialog.value.limit,
      only_enrolled: exportDialog.value.onlyEnrolled
    })
  } catch (e) {
    exportDialog.value.error =
      e.response?.data?.detail || e.message || 'Download fehlgeschlagen'
  } finally {
    exportDialog.value.busy = false
    exportDialog.value.busyKind = null
  }
}

const enrichEligibleCount = computed(() => {
  const by = stats.value?.by_status || {}
  // status that the LLM stage will pick up (worker.py:672)
  return (
    (by.discovered || 0) + (by.impressum_done || 0) + (by.impressum_failed || 0)
  )
})

const enrichCostUsd = computed(() => {
  // Empirically observed against real Anthropic billing: 1.05 ¢ per place
  // (5200 calls / $54.50 on 2026-04-25). Update if the avg shifts.
  const cents = (enrichDialog.value.limit || 0) * 1.05
  return (cents / 100).toFixed(2)
})

// Legacy quick-shortcut helpers retained only so `enrichEligibleCount` /
// `enrichCostUsd` (referenced elsewhere) keep working. The actual UI entry
// point is now `openRunDialog` / `confirmRun`.

let pollTimer = null
const POLL_INTERVAL_MS = 3000

onMounted(async () => {
  await loadAll()
  startPolling()
})

onBeforeUnmount(() => {
  stopPolling()
})

async function loadAll() {
  await store.fetchCampaign(campaignId.value)
  await store.fetchStats(campaignId.value)
  await store.fetchRuns(campaignId.value)
  if (activeTab.value === 'places') {
    await loadPlaces()
  }
}

async function loadPlaces() {
  if (!campaignId.value) return
  await store.fetchPlaces(campaignId.value, {
    status: placesStatusFilter.value || undefined,
    page: placesPage.value,
    size: placesPageSize.value,
    order_by: placesSortBy.value,
    order_dir: placesSortDir.value
  })
}

watch(activeTab, (tab) => {
  if (tab === 'places') {
    loadPlaces()
  }
})
watch(placesStatusFilter, () => {
  placesPage.value = 1
  if (activeTab.value === 'places') loadPlaces()
})
watch(placesPage, () => {
  if (activeTab.value === 'places') loadPlaces()
})
watch(placesPageSize, () => {
  placesPage.value = 1
  if (activeTab.value === 'places') loadPlaces()
})
watch([placesSortBy, placesSortDir], () => {
  if (activeTab.value === 'places') loadPlaces()
})

function nextPlacesPage() {
  if (placesPage.value < placesTotalPages.value) placesPage.value++
}
function prevPlacesPage() {
  if (placesPage.value > 1) placesPage.value--
}

function hasLiveRun() {
  return store.runs.some((r) => r.status === 'queued' || r.status === 'running')
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(async () => {
    if (!hasLiveRun()) return
    try {
      await store.fetchRuns(campaignId.value)
      await store.fetchStats(campaignId.value)
    } catch (e) {
      // swallow polling errors so we keep trying
    }
  }, POLL_INTERVAL_MS)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

const campaign = computed(() => store.currentCampaign)
const stats = computed(() => store.currentCampaignStats)

const maxApiCalls = computed(() => {
  const sc = campaign.value?.source_config || {}
  return Number(sc.max_api_calls) || null
})

function formatCost(cents) {
  if (!cents) return '0,00 €'
  return (cents / 100).toLocaleString('de-DE', {
    style: 'currency',
    currency: 'EUR'
  })
}

function formatDate(d) {
  if (!d) return '-'
  return new Date(d).toLocaleString('de-DE')
}

function callsProgress(run) {
  const made = Number(run?.stage_state?.api_calls_made) || 0
  const budget = maxApiCalls.value || 0
  if (!budget) return null
  return Math.min(100, Math.round((made / budget) * 100))
}

function tilesInfo(run) {
  const ss = run?.stage_state || {}
  return {
    processed: Number(ss.tiles_processed) || 0,
    queued: Array.isArray(ss.tile_queue) ? ss.tile_queue.length : 0,
    apiCalls: Number(ss.api_calls_made) || 0,
    saturations: Array.isArray(ss.saturation_events) ? ss.saturation_events.length : 0
  }
}

function statusBadgeClasses(status) {
  const map = {
    queued: 'bg-blue-100 text-blue-800',
    running: 'bg-green-100 text-green-800 animate-pulse',
    stopped: 'bg-yellow-100 text-yellow-800',
    paused: 'bg-yellow-100 text-yellow-800', // legacy DB rows
    completed: 'bg-gray-100 text-gray-800',
    failed: 'bg-red-100 text-red-800'
  }
  return map[status] || 'bg-gray-100 text-gray-800'
}

function statusLabel(status) {
  // German labels for the status badge — keeps the API stable while
  // showing operator-friendly text.
  const map = {
    queued: 'In Warteschlange',
    running: 'Läuft',
    stopped: 'Gestoppt',
    paused: 'Gestoppt', // legacy
    completed: 'Fertig',
    failed: 'Fehlgeschlagen'
  }
  return map[status] || status
}

function openRunDialog() {
  // Smart defaults: when the campaign already has discovered places we treat
  // the next click as an enrich-style run (Places off, rest on); otherwise
  // we kick off the full pipeline.
  const hasPlaces = (stats.value?.total_places || 0) > 0
  runDialog.value = {
    open: true,
    selectedStages: hasPlaces
      ? ['impressum', 'verify', 'llm', 'linkedin']
      : ['places', 'impressum', 'verify', 'llm', 'linkedin'],
    limit: hasPlaces ? Math.min(100, enrichEligibleCount.value || 100) : 100,
    sampling: 'top_rated',
    minMatchScore: '',
    enrichCompanies: false,
    apolloValidateExistingUrls: false,
    apolloRevealEmail: false,
    apolloRevealPhone: false,
    previewCount: null,
    previewContactCount: null,
    previewApolloCount: null,
    previewLoading: false,
    busy: false,
    error: null
  }
  refreshRunPreview()
}

let _previewSeq = 0
async function refreshRunPreview() {
  // Debounce-via-sequence: only the latest in-flight request wins so a fast
  // operator changing min-score doesn't see stale counts.
  if (!runDialogIsEnrich.value) {
    runDialog.value.previewCount = null
    runDialog.value.previewContactCount = null
    runDialog.value.previewApolloCount = null
    return
  }
  const seq = ++_previewSeq
  runDialog.value.previewLoading = true
  try {
    const { data } = await previewEnrichRun(campaignId.value, {
      stages: runDialog.value.selectedStages,
      minMatchScore: runDialog.value.minMatchScore,
      apolloValidateExistingUrls: runDialog.value.apolloValidateExistingUrls
    })
    if (seq === _previewSeq) {
      runDialog.value.previewCount = data.eligible_count
      runDialog.value.previewContactCount = data.contact_count ?? 0
      runDialog.value.previewApolloCount = data.apollo_count ?? 0
    }
  } catch {
    if (seq === _previewSeq) {
      runDialog.value.previewCount = null
      runDialog.value.previewContactCount = null
      runDialog.value.previewApolloCount = null
    }
  } finally {
    if (seq === _previewSeq) runDialog.value.previewLoading = false
  }
}

watch(
  () => [
    runDialog.value.selectedStages.slice().sort().join(','),
    runDialog.value.minMatchScore,
    runDialog.value.apolloValidateExistingUrls
  ],
  () => {
    if (runDialog.value.open) refreshRunPreview()
  }
)

function closeRunDialog() {
  if (runDialog.value.busy) return
  runDialog.value.open = false
}

function toggleStage(key) {
  const idx = runDialog.value.selectedStages.indexOf(key)
  if (idx >= 0) runDialog.value.selectedStages.splice(idx, 1)
  else runDialog.value.selectedStages.push(key)
}

async function confirmRun() {
  if (!runDialog.value.selectedStages.length) {
    runDialog.value.error = 'Mindestens einen Schritt auswählen.'
    return
  }
  runDialog.value.busy = true
  runDialog.value.error = null
  try {
    if (runDialog.value.selectedStages.includes('places')) {
      // Full run: backend's existing /runs endpoint runs the entire pipeline.
      // The explicit-stages selection only matters for downstream chaining
      // when the operator deselects later stages — pass it through too.
      await store.launchRun(campaignId.value)
    } else {
      await store.launchEnrichRun(campaignId.value, {
        limit: runDialog.value.limit,
        sampling: runDialog.value.sampling,
        stages: runDialog.value.selectedStages,
        minMatchScore: runDialog.value.minMatchScore,
        enrichCompanies: runDialog.value.enrichCompanies,
        apolloValidateExistingUrls: runDialog.value.apolloValidateExistingUrls,
        apolloRevealEmail: runDialog.value.apolloRevealEmail,
        apolloRevealPhone: runDialog.value.apolloRevealPhone
      })
    }
    runDialog.value.open = false
    await loadAll()
  } catch (e) {
    runDialog.value.error =
      e.response?.data?.detail || e.message || 'Run-Start fehlgeschlagen'
  } finally {
    runDialog.value.busy = false
  }
}

async function startRun() {
  starting.value = true
  statusErr.value = null
  try {
    await store.launchRun(campaignId.value)
    await loadAll()
  } catch (e) {
    statusErr.value = e.response?.data?.detail || e.message
  } finally {
    starting.value = false
  }
}

function openResumeDialog(runId) {
  resumeDialog.value = { open: true, runId, additionalBudget: 2000, busy: false }
}

function closeResumeDialog() {
  resumeDialog.value = { open: false, runId: null, additionalBudget: 2000, busy: false }
}

async function confirmResume() {
  const { runId, additionalBudget } = resumeDialog.value
  resumeDialog.value.busy = true
  statusErr.value = null
  try {
    await store.resumeRunAction(runId, additionalBudget || null)
    closeResumeDialog()
    await loadAll()
  } catch (e) {
    statusErr.value = e.response?.data?.detail || e.message
    resumeDialog.value.busy = false
  }
}

async function stopRun(runId) {
  statusErr.value = null
  try {
    await store.stopRunAction(runId)
    await loadAll()
  } catch (e) {
    statusErr.value = e.response?.data?.detail || e.message
  }
}

// "Fortsetzen" only makes sense when a stopped run hasn't already
// processed everything — otherwise resuming would be a no-op.
function canResumeRun(r) {
  if (r?.status !== 'stopped') return false
  const ss = r.stage_state || {}
  const total = ss.places_total || 0
  const processed = ss.places_processed || 0
  // Show resume when there's no progress data yet (worker hasn't started),
  // or when there's still work left.
  return total === 0 || processed < total
}

async function advanceStage(runId) {
  statusErr.value = null
  try {
    await store.advanceRunStageAction(runId)
    await loadAll()
  } catch (e) {
    statusErr.value = e.response?.data?.detail || e.message
  }
}

const STAGE_LABELS = {
  places: 'Stage 1 — Discovery',
  impressum_pending: 'Stage 2 — Impressum (bereit)',
  impressum: 'Stage 2 — Impressum-Scraping',
  llm_pending: 'Stage 3 — LLM-Analyse (bereit)',
  llm: 'Stage 3 — LLM-Analyse',
  completed: 'Abgeschlossen'
}

const NEXT_STAGE_LABEL = {
  impressum_pending: 'Impressum-Scraping starten',
  llm_pending: 'LLM-Analyse starten'
}

function stageLabel(stage) {
  return STAGE_LABELS[stage] || stage
}

function nextStageLabel(stage) {
  return NEXT_STAGE_LABEL[stage] || null
}

function impressumProgress(run) {
  const ss = run?.stage_state || {}
  const total = Number(ss.places_total) || 0
  const processed = Number(ss.places_processed) || 0
  const succeeded = Number(ss.places_succeeded) || 0
  const failed = Number(ss.places_failed) || 0
  if (!total) return null
  return {
    total,
    processed,
    succeeded,
    failed,
    percent: Math.min(100, Math.round((processed / total) * 100))
  }
}

function llmProgress(run) {
  const ss = run?.stage_state || {}
  const total = Number(ss.places_total) || 0
  const processed = Number(ss.places_processed) || 0
  const succeeded = Number(ss.places_succeeded) || 0
  const failed = Number(ss.places_failed) || 0
  const llmCostCents = Number(ss.llm_cost_cents) || 0
  if (!total) return null
  return {
    total,
    processed,
    succeeded,
    failed,
    llmCostCents,
    percent: Math.min(100, Math.round((processed / total) * 100))
  }
}

function canStartRun() {
  const c = campaign.value
  if (!c) return false
  if (!c.target_engagement_pipeline_id) return false
  const hasQueries = (c.queries || []).length > 0
  const sc = c.source_config || {}
  const hasHybrid =
    (sc.nearby_types && sc.nearby_types.length > 0) ||
    (sc.text_synonyms && sc.text_synonyms.length > 0)
  return hasQueries || hasHybrid
}

function goBack() {
  router.push('/leadgen')
}
</script>

<template>
  <div class="space-y-4">
    <div v-if="campaign">
      <PageHeader
        :title="campaign.name"
      />

      <div class="flex items-center gap-3 mt-3">
        <router-link
          :to="`/leadgen/campaigns/${campaign.id}/edit`"
          class="rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-700"
        >
          Bearbeiten
        </router-link>
        <button
          :disabled="starting || !canStartRun()"
          class="rounded-lg bg-go4-primary px-3 py-1.5 text-sm font-medium text-white disabled:opacity-60"
          @click="openRunDialog"
        >
          Run starten…
        </button>
        <button
          :disabled="!campaign?.target_engagement_pipeline_id"
          class="rounded-lg border border-emerald-300 bg-emerald-50 px-3 py-1.5 text-sm font-medium text-emerald-700 hover:bg-emerald-100 disabled:opacity-60 dark:border-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-200 dark:hover:bg-emerald-900/60"
          :title="campaign?.target_engagement_pipeline_id ? '' : 'Erst eine Engagement-Pipeline verknüpfen'"
          @click="openHandoffDialog"
        >
          🚀 In Funnel kippen…
        </button>
        <button
          class="rounded-lg border border-blue-300 bg-blue-50 px-3 py-1.5 text-sm font-medium text-blue-700 hover:bg-blue-100 dark:border-blue-700 dark:bg-blue-900/40 dark:text-blue-200 dark:hover:bg-blue-900/60"
          @click="openExportDialog"
        >
          📊 Export…
        </button>
        <button
          class="ml-auto text-sm text-gray-500 hover:underline"
          @click="goBack"
        >
          ← Zur Übersicht
        </button>
      </div>

      <p
        v-if="!campaign.target_engagement_pipeline_id"
        class="mt-2 text-xs text-yellow-700"
      >
        Diese Kampagne ist keiner Engagement-Pipeline zugeordnet — Runs können nicht gestartet
        werden.
      </p>
      <p
        v-if="!canStartRun()"
        class="mt-2 text-xs text-yellow-700"
      >
        Diese Kampagne hat keine Suchkonfiguration — Runs können nicht gestartet werden.
      </p>
      <p
        v-if="statusErr"
        class="mt-2 rounded-lg bg-red-50 p-2 text-sm text-red-700"
      >
        {{ statusErr }}
      </p>

      <!-- Sub-Tabs -->
      <nav class="mt-6 border-b border-gray-200 dark:border-gray-700">
        <div class="-mb-px flex gap-6">
          <router-link
            :to="`/leadgen/campaigns/${campaign.id}/details`"
            class="border-b-2 pb-3 text-sm font-medium transition-colors"
            :class="
              activeTab === 'details'
                ? 'border-go4-primary text-go4-primary'
                : 'border-transparent text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200'
            "
          >
            Details &amp; Runs
          </router-link>
          <router-link
            :to="`/leadgen/campaigns/${campaign.id}/places`"
            class="border-b-2 pb-3 text-sm font-medium transition-colors"
            :class="
              activeTab === 'places'
                ? 'border-go4-primary text-go4-primary'
                : 'border-transparent text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200'
            "
          >
            Prospects
            <span
              v-if="stats"
              class="ml-1 text-xs text-gray-500"
            >
              ({{ stats.total_places.toLocaleString('de-DE') }})
            </span>
          </router-link>
          <router-link
            :to="`/leadgen/campaigns/${campaign.id}/map`"
            class="border-b-2 pb-3 text-sm font-medium transition-colors"
            :class="
              activeTab === 'map'
                ? 'border-go4-primary text-go4-primary'
                : 'border-transparent text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200'
            "
          >
            Karte
          </router-link>
        </div>
      </nav>

      <!-- DETAILS TAB -->
      <div
        v-if="activeTab === 'details'"
        class="mt-4 max-w-5xl"
      >
        <!-- Info-Grid -->
        <div class="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div
            class="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
          >
            <h3 class="text-sm font-semibold mb-3">
              Konfiguration
            </h3>
            <dl class="space-y-1 text-sm">
              <div class="flex justify-between">
                <dt class="text-gray-500">
                  Status
                </dt>
                <dd>{{ campaign.status }}</dd>
              </div>
              <div class="flex justify-between">
                <dt class="text-gray-500">
                  Quelle
                </dt>
                <dd>{{ campaign.source || 'google_places' }}</dd>
              </div>
              <div class="flex justify-between">
                <dt class="text-gray-500">
                  Sprache
                </dt>
                <dd>{{ campaign.language }}</dd>
              </div>
              <div class="flex justify-between">
                <dt class="text-gray-500">
                  Region
                </dt>
                <dd>{{ campaign.region }}</dd>
              </div>
              <div
                v-if="maxApiCalls"
                class="flex justify-between"
              >
                <dt class="text-gray-500">
                  Max. API Calls
                </dt>
                <dd>{{ maxApiCalls.toLocaleString('de-DE') }}</dd>
              </div>
              <div class="flex justify-between">
                <dt class="text-gray-500">
                  Match-Schwelle
                </dt>
                <dd>{{ campaign.target_match_threshold }}</dd>
              </div>
              <div class="flex justify-between">
                <dt class="text-gray-500">
                  Pipeline
                </dt>
                <dd>{{ campaign.target_engagement_pipeline_id || '—' }}</dd>
              </div>
            </dl>
          </div>

          <div
            class="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
          >
            <h3 class="text-sm font-semibold mb-3">
              Statistik
            </h3>
            <dl
              v-if="stats"
              class="space-y-1 text-sm"
            >
              <div class="flex justify-between">
                <dt class="text-gray-500">
                  Prospects gesamt
                </dt>
                <dd class="font-semibold">
                  {{ stats.total_places.toLocaleString('de-DE') }}
                </dd>
              </div>
              <div
                v-for="(count, status) in stats.by_status"
                :key="status"
                class="flex justify-between"
              >
                <dt class="text-gray-500">
&nbsp;&nbsp;{{ status }}
                </dt>
                <dd>{{ count.toLocaleString('de-DE') }}</dd>
              </div>
              <div class="flex justify-between pt-2 border-t border-gray-200 dark:border-gray-700">
                <dt class="text-gray-500">
                  Runs gesamt
                </dt>
                <dd>{{ stats.runs_total }}</dd>
              </div>
              <div class="flex justify-between">
                <dt class="text-gray-500">
                  Runs laufen
                </dt>
                <dd>{{ stats.runs_running }}</dd>
              </div>
              <div class="flex justify-between">
                <dt class="text-gray-500">
                  Kosten gesamt
                </dt>
                <dd class="font-semibold">
                  {{ formatCost(stats.total_cost_cents) }}
                </dd>
              </div>
            </dl>
          </div>
        </div>

        <!-- Runs -->
        <div
          class="mt-6 rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800"
        >
          <div
            class="flex items-center justify-between border-b border-gray-200 px-4 py-3 dark:border-gray-700"
          >
            <div class="text-sm font-semibold">
              Runs
            </div>
            <span
              v-if="hasLiveRun()"
              class="text-xs text-green-700 dark:text-green-400"
            >
              ● Live — aktualisiert alle {{ POLL_INTERVAL_MS / 1000 }}s
            </span>
          </div>
          <div
            v-if="store.runs.length === 0"
            class="p-6 text-center text-sm text-gray-500"
          >
            Noch keine Runs.
          </div>
          <ul
            v-else
            class="divide-y divide-gray-200 dark:divide-gray-700"
          >
            <li
              v-for="r in store.runs"
              :key="r.id"
              class="p-4 space-y-3"
            >
              <div class="flex flex-wrap items-center gap-3 text-sm">
                <span class="font-mono text-gray-500">#{{ r.id }}</span>
                <span class="font-medium">{{ stageLabel(r.current_stage) }}</span>
                <span
                  class="rounded-full px-2 py-0.5 text-xs font-medium"
                  :class="statusBadgeClasses(r.status)"
                >
                  {{ statusLabel(r.status) }}
                </span>
                <span class="text-gray-500">
                  {{ formatDate(r.started_at) }}
                </span>
                <span class="ml-auto flex items-center gap-2">
                  <button
                    v-if="r.status === 'stopped' && nextStageLabel(r.current_stage) && canResumeRun(r)"
                    class="rounded-lg bg-green-600 px-3 py-1 text-xs font-medium text-white hover:bg-green-700"
                    @click="advanceStage(r.id)"
                  >
                    {{ nextStageLabel(r.current_stage) }}
                  </button>
                  <button
                    v-if="r.status === 'stopped' && !nextStageLabel(r.current_stage) && canResumeRun(r)"
                    class="rounded-lg bg-go4-primary px-3 py-1 text-xs font-medium text-white"
                    @click="openResumeDialog(r.id)"
                  >
                    Fortsetzen
                  </button>
                  <button
                    v-if="r.status === 'running' || r.status === 'queued'"
                    class="rounded-lg border border-gray-300 px-3 py-1 text-xs font-medium hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-700"
                    @click="stopRun(r.id)"
                  >
                    Stoppen
                  </button>
                </span>
              </div>

              <!-- Per-stage timeline: discovery → impressum → verify → llm,
                 each with its own status, metrics, duration and cost.
                 Replaces the old static 5-tile metric grid + the three
                 stage-specific progress bars (whose metrics now live inside
                 the corresponding stage row). -->
              <LeadgenRunStageTimeline :run="r" />

              <!-- Total cost stays prominent at the bottom of the run card. -->
              <div class="flex items-center justify-between border-t border-gray-100 pt-2 text-xs text-gray-500 dark:border-gray-700">
                <span>Gesamtkosten</span>
                <span class="font-medium text-gray-900 dark:text-gray-100">
                  {{ formatCost(r.cost_cents) }}
                </span>
              </div>

              <p
                v-if="r.last_error"
                class="rounded-lg bg-red-50 p-2 text-xs text-red-700"
              >
                {{ r.last_error }}
              </p>
            </li>
          </ul>
        </div>
      </div><!-- /Details TAB -->

      <!-- PLACES TAB -->
      <div
        v-if="activeTab === 'places'"
        class="mt-4 space-y-3"
      >
        <div class="flex items-center justify-between gap-3">
          <select
            v-model="placesStatusFilter"
            class="w-56 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800"
          >
            <option value="">
              Alle Status
            </option>
            <option value="discovered">
              discovered
            </option>
            <option value="impressum_done">
              impressum_done
            </option>
            <option value="impressum_failed">
              impressum_failed
            </option>
            <option value="llm_done">
              llm_done
            </option>
            <option value="llm_failed">
              llm_failed
            </option>
            <option value="enrolled">
              enrolled
            </option>
            <option value="rejected">
              rejected
            </option>
          </select>
          <div class="text-xs text-gray-500">
            {{ store.places.total.toLocaleString('de-DE') }} Treffer
          </div>
        </div>

        <div
          v-if="store.places.items.length === 0"
          class="rounded-lg border border-dashed border-gray-300 p-8 text-center text-sm text-gray-500 dark:border-gray-600"
        >
          Keine Prospects für diesen Filter.
        </div>

        <div
          v-else
          class="overflow-hidden rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800"
        >
          <table class="w-full text-sm">
            <thead class="bg-gray-50 text-left text-xs uppercase tracking-wide text-gray-600 dark:bg-gray-900/40 dark:text-gray-300">
              <tr>
                <th
                  class="cursor-pointer select-none px-3 py-2 hover:bg-gray-100 dark:hover:bg-gray-800"
                  @click="toggleSort('name')"
                >
                  Firma {{ sortIndicator('name') }}
                </th>
                <th
                  class="cursor-pointer select-none px-3 py-2 hover:bg-gray-100 dark:hover:bg-gray-800"
                  @click="toggleSort('city')"
                >
                  Stadt {{ sortIndicator('city') }}
                </th>
                <th
                  class="cursor-pointer select-none px-3 py-2 hover:bg-gray-100 dark:hover:bg-gray-800"
                  @click="toggleSort('status')"
                >
                  Status {{ sortIndicator('status') }}
                </th>
                <th
                  class="cursor-pointer select-none px-3 py-2 text-right hover:bg-gray-100 dark:hover:bg-gray-800"
                  @click="toggleSort('match')"
                >
                  Match {{ sortIndicator('match') }}
                </th>
                <th
                  class="cursor-pointer select-none px-3 py-2 hover:bg-gray-100 dark:hover:bg-gray-800"
                  @click="toggleSort('rating')"
                >
                  Bewertung {{ sortIndicator('rating') }}
                </th>
                <th class="px-3 py-2">
                  Website
                </th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
              <tr
                v-for="p in store.places.items"
                :key="p.id"
                class="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/40"
                @click="router.push(`/leadgen/campaigns/${campaign.id}/places/${p.id}`)"
              >
                <td class="px-3 py-2">
                  <div class="font-medium text-gray-900 dark:text-gray-100">
                    {{ p.name }}
                  </div>
                </td>
                <td class="px-3 py-2 text-gray-600 dark:text-gray-400">
                  {{ p.address_city || '-' }}
                </td>
                <td class="px-3 py-2">
                  <span :class="placeStatusBadge(p.status)">{{ p.status }}</span>
                </td>
                <td class="px-3 py-2 text-right tabular-nums">
                  <span
                    v-if="p.llm_insights?.target_match_score != null"
                    class="inline-flex items-center rounded-full px-2 py-0.5 text-xs"
                    :class="p.llm_insights.target_match_score >= 7 ? 'bg-green-100 text-green-800' : p.llm_insights.target_match_score >= 4 ? 'bg-yellow-100 text-yellow-800' : 'bg-red-100 text-red-800'"
                  >{{ p.llm_insights.target_match_score }}/10</span>
                  <span
                    v-else
                    class="text-gray-400"
                  >—</span>
                </td>
                <td class="px-3 py-2 text-xs text-gray-500">
                  <span v-if="p.rating">
                    {{ p.rating }} ★ ({{ p.user_ratings_total || 0 }})
                  </span>
                  <span v-else>—</span>
                </td>
                <td class="px-3 py-2 text-xs">
                  <a
                    v-if="p.website"
                    :href="p.website"
                    target="_blank"
                    rel="noopener"
                    class="text-go4-primary hover:underline"
                    @click.stop
                  >Link</a>
                  <span
                    v-else
                    class="text-gray-400"
                  >—</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Pagination -->
        <div
          v-if="store.places.total > placesPageSize"
          class="flex items-center justify-between text-sm"
        >
          <div class="text-gray-500">
            Seite {{ placesPage }} von {{ placesTotalPages }}
          </div>
          <div class="flex items-center gap-2">
            <select
              v-model.number="placesPageSize"
              class="rounded-lg border border-gray-300 bg-white px-2 py-1 text-xs dark:border-gray-600 dark:bg-gray-800"
            >
              <option :value="25">
                25
              </option>
              <option :value="50">
                50
              </option>
              <option :value="100">
                100
              </option>
              <option :value="200">
                200
              </option>
            </select>
            <button
              :disabled="placesPage <= 1"
              class="rounded-lg border border-gray-300 px-2.5 py-1 text-xs disabled:opacity-40 hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-700"
              @click="prevPlacesPage"
            >
              ← zurück
            </button>
            <button
              :disabled="placesPage >= placesTotalPages"
              class="rounded-lg border border-gray-300 px-2.5 py-1 text-xs disabled:opacity-40 hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-700"
              @click="nextPlacesPage"
            >
              weiter →
            </button>
          </div>
        </div>
      </div>

      <!-- MAP TAB -->
      <div
        v-if="activeTab === 'map'"
        class="mt-4"
      >
        <LeadgenMap :campaign-id="campaign.id" />
      </div>
    </div>

    <!-- Export Dialog -->
    <div
      v-if="exportDialog.open"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      @click.self="closeExportDialog"
    >
      <div class="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl dark:bg-gray-800">
        <h3 class="text-lg font-semibold">
          CSV-Export
        </h3>
        <p class="mt-2 text-sm text-gray-600 dark:text-gray-400">
          Wähle das Zielformat. Alle Dateien sind UTF-8 mit BOM, direkt
          Excel-tauglich. Apollo bekommt eine Zeile pro Person inkl. LinkedIn-URL,
          sofern der LinkedIn-Stage gelaufen ist.
        </p>

        <div class="mt-4 grid grid-cols-2 gap-3">
          <label class="block text-sm">
            <span class="text-gray-700 dark:text-gray-300">Min. Match-Score</span>
            <input
              v-model.number="exportDialog.minScore"
              type="number"
              min="0"
              max="10"
              class="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900"
              @change="refreshExportPreview"
            >
          </label>
          <label class="block text-sm">
            <span class="text-gray-700 dark:text-gray-300">Max. Anzahl</span>
            <input
              v-model.number="exportDialog.limit"
              type="number"
              min="1"
              max="50000"
              class="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900"
              @change="refreshExportPreview"
            >
          </label>
        </div>

        <label class="mt-3 flex items-center gap-2 text-sm">
          <input
            v-model="exportDialog.onlyEnrolled"
            type="checkbox"
            @change="refreshExportPreview"
          >
          <span class="text-gray-700 dark:text-gray-300">
            Nur Firmen, die bereits im Funnel sind
          </span>
        </label>

        <div
          v-if="exportDialog.preview"
          class="mt-4 rounded-lg bg-gray-50 dark:bg-gray-900/50 p-3 text-sm space-y-1"
        >
          <div class="flex justify-between">
            <span>LinkedIn Sales Nav — Firmen</span>
            <b>{{ exportDialog.preview.accounts_count.toLocaleString('de-DE') }}</b>
          </div>
          <div class="flex justify-between">
            <span>LinkedIn Sales Nav — Personen</span>
            <b>{{ exportDialog.preview.leads_count.toLocaleString('de-DE') }}</b>
          </div>
          <div class="flex justify-between">
            <span>Apollo — alle Personen (Kontakt-CSV)</span>
            <b>{{ (exportDialog.preview.apollo_count ?? exportDialog.preview.leads_count).toLocaleString('de-DE') }}</b>
          </div>
          <div
            v-if="exportDialog.preview.apollo_with_linkedin !== undefined"
            class="flex justify-between text-xs text-gray-500"
          >
            <span class="pl-3">↳ davon mit LinkedIn-URL</span>
            <span>{{ exportDialog.preview.apollo_with_linkedin.toLocaleString('de-DE') }}</span>
          </div>
          <p class="pt-1 text-xs text-gray-500">
            Sales-Nav listet pro Geschäftsführer eine Zeile. Apollo bekommt
            <b>alle</b> Personen — Spalte „Contact LinkedIn URL“ ist leer wenn
            unbekannt, Apollo matcht trotzdem über Email + Firmenname.
            LinkedIn-Stage zuerst laufen lassen, um die URLs zu füllen.
          </p>
        </div>

        <p
          v-if="exportDialog.error"
          class="mt-3 rounded-lg bg-red-50 p-2 text-sm text-red-700 dark:bg-red-900/40 dark:text-red-200"
        >
          {{ exportDialog.error }}
        </p>

        <div class="mt-5 flex flex-wrap items-center justify-end gap-2">
          <button
            class="rounded-lg border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-700"
            :disabled="exportDialog.busy"
            @click="closeExportDialog"
          >
            Schließen
          </button>
          <button
            class="rounded-lg border border-blue-300 bg-blue-50 px-3 py-1.5 text-sm font-medium text-blue-700 hover:bg-blue-100 disabled:opacity-60 dark:border-blue-700 dark:bg-blue-900/40 dark:text-blue-200 dark:hover:bg-blue-900/60"
            :disabled="exportDialog.busy || !exportDialog.preview?.accounts_count"
            @click="downloadExport('accounts')"
          >
            📥 Sales Nav Firmen ({{ exportDialog.preview?.accounts_count || 0 }})
          </button>
          <button
            class="rounded-lg border border-blue-300 bg-blue-50 px-3 py-1.5 text-sm font-medium text-blue-700 hover:bg-blue-100 disabled:opacity-60 dark:border-blue-700 dark:bg-blue-900/40 dark:text-blue-200 dark:hover:bg-blue-900/60"
            :disabled="exportDialog.busy || !exportDialog.preview?.leads_count"
            @click="downloadExport('leads')"
          >
            📥 Sales Nav Personen ({{ exportDialog.preview?.leads_count || 0 }})
          </button>
          <button
            class="rounded-lg border border-emerald-300 bg-emerald-50 px-3 py-1.5 text-sm font-medium text-emerald-700 hover:bg-emerald-100 disabled:opacity-60 dark:border-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-200 dark:hover:bg-emerald-900/60"
            :disabled="
              exportDialog.busy ||
                !(exportDialog.preview?.apollo_count ?? exportDialog.preview?.leads_count)
            "
            @click="downloadExport('apollo')"
          >
            📥 Apollo ({{
              exportDialog.preview?.apollo_count ?? exportDialog.preview?.leads_count ?? 0
            }})
          </button>
        </div>
      </div>
    </div>

    <!-- Handoff Dialog -->
    <div
      v-if="handoffDialog.open"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      @click.self="closeHandoffDialog"
    >
      <div class="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl dark:bg-gray-800">
        <h3 class="text-lg font-semibold">
          Top-Leads in Funnel kippen
        </h3>
        <p class="mt-2 text-sm text-gray-600 dark:text-gray-400">
          Konvertiert qualifizierende Prospects in Contacts und reiht sie in die
          verknüpfte Engagement-Pipeline ein.
        </p>

        <div
          v-if="handoffDialog.result"
          class="mt-4 space-y-2"
        >
          <div class="rounded-lg border border-emerald-300 bg-emerald-50 p-3 text-sm dark:border-emerald-700 dark:bg-emerald-900/30">
            <div class="font-medium text-emerald-900 dark:text-emerald-100">
              ✓ Handoff erfolgreich
            </div>
            <ul class="mt-2 space-y-0.5 text-xs text-emerald-800 dark:text-emerald-200">
              <li>{{ handoffDialog.result.enrolled }} Leads in Pipeline #{{ handoffDialog.result.pipeline_id }} eingereiht</li>
              <li>{{ handoffDialog.result.contacts_created }} neue Contacts angelegt, {{ handoffDialog.result.contacts_reused }} wiederverwendet</li>
              <li v-if="handoffDialog.result.enrolled_without_email">
                davon {{ handoffDialog.result.enrolled_without_email }} ohne Email-Adresse (Brief-/Telefon-only)
              </li>
              <li v-if="handoffDialog.result.skipped_no_email">
                {{ handoffDialog.result.skipped_no_email }} ohne Email übersprungen
              </li>
              <li v-if="handoffDialog.result.skipped_existing">
                {{ handoffDialog.result.skipped_existing }} bereits zuvor enrolled
              </li>
              <li v-if="handoffDialog.result.skipped">
                {{ handoffDialog.result.skipped }} vom Engagement übersprungen
              </li>
            </ul>
          </div>
          <div class="flex justify-end">
            <button
              class="rounded-lg bg-go4-primary px-3 py-1.5 text-sm font-medium text-white"
              @click="closeHandoffDialog"
            >
              Schließen
            </button>
          </div>
        </div>

        <template v-else>
          <div class="mt-4 grid grid-cols-2 gap-3">
            <label class="block text-sm">
              <span class="text-gray-700 dark:text-gray-300">Min. Match-Score</span>
              <input
                v-model.number="handoffDialog.minScore"
                type="number"
                min="0"
                max="10"
                class="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900"
                @change="refreshHandoffPreview"
              >
            </label>
            <label class="block text-sm">
              <span class="text-gray-700 dark:text-gray-300">Max. Anzahl</span>
              <input
                v-model.number="handoffDialog.limit"
                type="number"
                min="1"
                max="10000"
                class="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900"
                @change="refreshHandoffPreview"
              >
            </label>
          </div>

          <label class="mt-3 flex cursor-pointer items-start gap-2 rounded-lg border border-gray-200 p-3 dark:border-gray-700">
            <input
              v-model="handoffDialog.includeWithoutEmail"
              type="checkbox"
              class="mt-0.5 h-4 w-4 rounded border-gray-300 text-go4-primary focus:ring-go4-primary"
              @change="refreshHandoffPreview"
            >
            <div class="text-sm">
              <div class="font-medium text-gray-800 dark:text-gray-200">
                Auch Kontakte ohne Email-Adresse mitnehmen
              </div>
              <div class="text-xs text-gray-500 dark:text-gray-400">
                Diese Leads bekommen einen Platzhalter und sind nur per Brief/Telefon
                erreichbar — sinnvoll wenn die Pipeline einen Letter-Channel hat.
              </div>
            </div>
          </label>

          <div
            v-if="handoffDialog.preview"
            class="mt-4 rounded-lg bg-gray-50 p-3 text-xs space-y-0.5 dark:bg-gray-900/50"
          >
            <div class="font-medium text-gray-800 dark:text-gray-200">
              Vorschau
            </div>
            <div>Eligible insgesamt: <b>{{ handoffDialog.preview.eligible_total }}</b></div>
            <div>Werden enrolled: <b class="text-emerald-700 dark:text-emerald-300">{{ handoffDialog.preview.would_enroll }}</b></div>
            <div
              v-if="handoffDialog.preview.would_enroll_without_email > 0"
              class="text-blue-700 dark:text-blue-300"
            >
              davon {{ handoffDialog.preview.would_enroll_without_email }} ohne Email (nur Brief/Telefon)
            </div>
            <div
              v-if="handoffDialog.preview.already_have_contact > 0"
              class="text-gray-500"
            >
              {{ handoffDialog.preview.already_have_contact }} bereits als Contact verlinkt
            </div>
            <div
              v-if="handoffDialog.preview.missing_email > 0 && !handoffDialog.includeWithoutEmail"
              class="text-yellow-700 dark:text-yellow-300"
            >
              {{ handoffDialog.preview.missing_email }} ohne Impressum-Email werden übersprungen
            </div>
          </div>

          <div class="mt-3 rounded-lg bg-blue-50 dark:bg-blue-900/30 p-3 text-xs">
            <div class="font-medium text-blue-900 dark:text-blue-100">
              Pipeline
            </div>
            <div class="text-blue-800 dark:text-blue-200">
              Engagement-Pipeline #{{ campaign?.target_engagement_pipeline_id || '—' }}
              ({{ campaign?.slug }})
            </div>
          </div>

          <p
            v-if="handoffDialog.error"
            class="mt-3 rounded-lg bg-red-50 p-2 text-sm text-red-700 dark:bg-red-900/40 dark:text-red-200"
          >
            {{ handoffDialog.error }}
          </p>

          <div class="mt-5 flex justify-end gap-2">
            <button
              class="rounded-lg border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-700"
              :disabled="handoffDialog.busy"
              @click="closeHandoffDialog"
            >
              Abbrechen
            </button>
            <button
              class="rounded-lg bg-go4-primary px-3 py-1.5 text-sm font-medium text-white disabled:opacity-60"
              :disabled="handoffDialog.busy || !handoffDialog.preview?.would_enroll"
              @click="confirmHandoff"
            >
              {{ handoffDialog.busy ? 'Wird ausgeführt…' : `${handoffDialog.preview?.would_enroll || 0} Leads enrollen` }}
            </button>
          </div>
        </template>
      </div>
    </div>

    <!-- Run Dialog (unified Run starten…) -->
    <div
      v-if="runDialog.open"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      @click.self="closeRunDialog"
    >
      <div class="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl dark:bg-gray-800">
        <h3 class="text-lg font-semibold">
          Run starten
        </h3>
        <p class="mt-2 text-sm text-gray-600 dark:text-gray-400">
          Wähle, welche Schritte gelaufen werden sollen. Wird Google Places
          deaktiviert, läuft der Run nur auf bereits gefundenen Prospects
          (Anreicherungs-Modus).
        </p>

        <fieldset class="mt-4 space-y-2 text-sm">
          <template
            v-for="stage in STAGE_DEFS"
            :key="stage.key"
          >
            <label
              class="flex items-start gap-3 rounded-lg border border-gray-200 p-2 cursor-pointer dark:border-gray-600"
            >
              <input
                type="checkbox"
                :checked="runDialog.selectedStages.includes(stage.key)"
                class="mt-0.5"
                @change="toggleStage(stage.key)"
              >
              <span class="flex-1">
                <span class="font-medium">{{ stage.label }}</span>
                <span class="block text-xs text-gray-500">
                  {{
                    stage.costPerLead === 0
                      ? 'gratis'
                      : `~$${(stage.costPerLead / 100).toFixed(4)}/Lead`
                  }}
                </span>
              </span>
            </label>
            <!-- min_match_score + enrich_companies live indented under the
                 LinkedIn checkbox because they ONLY affect that stage. -->
            <div
              v-if="stage.key === 'linkedin' && runDialog.selectedStages.includes('linkedin')"
              class="ml-7 -mt-1 space-y-2 rounded-lg border border-blue-100 bg-blue-50/50 p-2 dark:border-blue-800/40 dark:bg-blue-900/20"
            >
              <label class="block text-sm">
                <span class="text-gray-700 dark:text-gray-300">
                  Min. Match-Score (LLM)
                  <span class="text-xs font-normal text-gray-400">— optional, z.B. 7 für nur Top-Leads</span>
                </span>
                <input
                  v-model="runDialog.minMatchScore"
                  type="number"
                  min="0"
                  max="10"
                  placeholder="leer = alle"
                  class="mt-1 w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-900"
                >
              </label>
              <label class="flex items-start gap-2 text-sm cursor-pointer">
                <input
                  v-model="runDialog.enrichCompanies"
                  type="checkbox"
                  class="mt-0.5"
                >
                <span class="flex-1">
                  <span class="font-medium text-gray-700 dark:text-gray-300">
                    Auch Firmen-LinkedIn anreichern
                  </span>
                  <span class="block text-xs text-gray-500">
                    Default aus — Personen-URLs sind für Outreach wichtiger.
                    Aktivieren kostet ~1 Serper-Call zusätzlich pro Firma.
                  </span>
                </span>
              </label>
            </div>
            <!-- apollo_require_linkedin lives indented under the Apollo
                 checkbox. min_match_score is shared with linkedin and
                 rendered under whichever box is the *first* one selected. -->
            <div
              v-if="stage.key === 'apollo' && showApolloOptions"
              class="ml-7 -mt-1 space-y-2 rounded-lg border border-orange-100 bg-orange-50/50 p-2 dark:border-orange-800/40 dark:bg-orange-900/20"
            >
              <label
                v-if="!runDialog.selectedStages.includes('linkedin')"
                class="block text-sm"
              >
                <span class="text-gray-700 dark:text-gray-300">
                  Min. Match-Score (LLM)
                  <span class="text-xs font-normal text-gray-400">— optional</span>
                </span>
                <input
                  v-model="runDialog.minMatchScore"
                  type="number"
                  min="0"
                  max="10"
                  placeholder="leer = alle"
                  class="mt-1 w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-900"
                >
              </label>
              <label class="flex items-start gap-2 text-sm cursor-pointer">
                <input
                  v-model="runDialog.apolloValidateExistingUrls"
                  type="checkbox"
                  class="mt-0.5"
                >
                <span class="flex-1">
                  <span class="font-medium text-gray-700 dark:text-gray-300">
                    LinkedIn-URLs prüfen (existierende validieren)
                    <span class="ml-1 text-[10px] uppercase tracking-wide text-blue-700">+1 Credit/Match</span>
                  </span>
                  <span class="block text-xs text-gray-500">
                    Default aus — Apollo füllt nur die Lücken, die Serper nicht
                    gefunden hat. Aktivieren = Apollo prüft auch bereits
                    gefundene Serper-URLs (überschreibt bei Konflikt).
                  </span>
                </span>
              </label>
              <label class="flex items-start gap-2 text-sm cursor-pointer">
                <input
                  v-model="runDialog.apolloRevealEmail"
                  type="checkbox"
                  class="mt-0.5"
                >
                <span class="flex-1">
                  <span class="font-medium text-gray-700 dark:text-gray-300">
                    Email-Adressen anreichern
                    <span class="ml-1 text-[10px] uppercase tracking-wide text-blue-700">+1 Credit/Match</span>
                  </span>
                  <span class="block text-xs text-gray-500">
                    Holt verifizierte Geschäftsemails. Verdoppelt etwa den
                    Credit-Verbrauch (1 Match-Credit + 1 Email-Credit).
                  </span>
                </span>
              </label>
              <label class="flex items-start gap-2 text-sm cursor-pointer opacity-60">
                <input
                  v-model="runDialog.apolloRevealPhone"
                  type="checkbox"
                  class="mt-0.5"
                  disabled
                >
                <span class="flex-1">
                  <span class="font-medium text-gray-700 dark:text-gray-300">
                    Telefonnummern anreichern
                    <span class="ml-1 text-[10px] uppercase tracking-wide text-red-700">+8 Credits/Match · webhook nötig</span>
                  </span>
                  <span class="block text-xs text-gray-500">
                    Sehr teuer (8 Credits/Treffer) und Apollo liefert Nummern
                    asynchron via Webhook — Receiver noch nicht implementiert.
                  </span>
                </span>
              </label>
              <div class="rounded bg-orange-100/50 px-2 py-1 text-[11px] text-orange-900 dark:bg-orange-900/30 dark:text-orange-100">
                <b>Basic Plan:</b> 2.500 Credits/Monat inklusive · Overage = $0,02/Credit
                ($50 für 2.500). Match: 1 Credit · Email: +1 · Phone: +8.
                <br>
                Beispiel 10k Kontakte (~70% Match): Match-only ≈ <b>$90</b>,
                +Email ≈ <b>$230</b>.
              </div>
            </div>
          </template>
        </fieldset>

        <div
          v-if="showRunLimit || showRunSampling || runDialogIsEnrich"
          class="mt-4 grid grid-cols-2 gap-3 text-sm"
        >
          <label
            v-if="showRunLimit"
            class="block"
            :class="!showRunSampling ? 'col-span-2' : ''"
          >
            <span class="text-gray-700 dark:text-gray-300">Anzahl Prospects</span>
            <input
              v-model.number="runDialog.limit"
              type="number"
              min="1"
              max="10000"
              class="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900"
            >
          </label>
          <label
            v-if="showRunSampling"
            class="block"
            :class="!showRunLimit ? 'col-span-2' : ''"
          >
            <span class="text-gray-700 dark:text-gray-300">Sampling</span>
            <select
              v-model="runDialog.sampling"
              class="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900"
            >
              <option value="top_rated">Best-bewertet zuerst (Google-Rating)</option>
              <option value="random">Zufällig</option>
            </select>
          </label>
          <div
            v-if="runDialogIsEnrich"
            class="col-span-2 rounded-lg bg-blue-50 p-2 text-xs dark:bg-blue-900/30"
          >
            <div
              v-if="runDialog.previewLoading"
              class="text-blue-700 dark:text-blue-200"
            >
              Lade Filter-Vorschau…
            </div>
            <div
              v-else-if="runDialog.previewCount != null"
              class="space-y-0.5 text-blue-900 dark:text-blue-100"
            >
              <div>
                <b>{{ runDialog.previewCount.toLocaleString('de-DE') }}</b> Firmen
                matchen deine Auswahl
                <span
                  v-if="runDialog.previewContactCount != null"
                  class="text-blue-500"
                >
                  · {{ runDialog.previewContactCount.toLocaleString('de-DE') }} Personen daran
                </span>
              </div>
              <div
                v-if="runDialog.selectedStages.includes('linkedin')"
                class="text-blue-700 dark:text-blue-200"
              >
                Serper-Calls:
                <b>{{ runDialog.previewContactCount?.toLocaleString('de-DE') ?? 0 }}</b> Personen
                <span v-if="runDialog.enrichCompanies">
                  + <b>{{ runDialog.previewCount.toLocaleString('de-DE') }}</b> Firmen
                </span>
                <span
                  v-else
                  class="text-blue-500"
                >(Firmen aus, opt-in oben)</span>
              </div>
              <div
                v-if="runDialog.selectedStages.includes('apollo') && runDialog.previewApolloCount != null"
                class="text-orange-700 dark:text-orange-200"
              >
                Apollo:
                <b>{{ runDialog.previewApolloCount.toLocaleString('de-DE') }}</b>
                Personen
                <span class="text-orange-500">
                  ({{ runDialog.apolloValidateExistingUrls ? 'inkl. existierende' : 'nur Serper-Lücken' }})
                </span>
                ·
                <b>{{ Math.ceil(runDialog.previewApolloCount / 10) }}</b>
                Bulk-Calls
                ·
                ≤
                <b>{{ runDialog.previewApolloCount.toLocaleString('de-DE') }}</b>
                Credits
              </div>
              <div class="text-blue-700 dark:text-blue-200">
                Limit: bis zu
                <b>{{
                  Math.min(
                    runDialog.limit || runDialog.previewCount,
                    runDialog.previewCount
                  ).toLocaleString('de-DE')
                }}</b>
                Firmen verarbeitet
              </div>
            </div>
            <div
              v-else
              class="text-blue-700 dark:text-blue-200"
            >
              Verfügbarer Pool: {{ enrichEligibleCount.toLocaleString('de-DE') }} Prospects
            </div>
          </div>
        </div>

        <div class="mt-4 rounded-lg bg-gray-50 p-3 text-xs dark:bg-gray-900/50">
          <div class="flex items-baseline justify-between">
            <span class="font-medium">Kosten-Schätzung</span>
            <span class="text-base font-semibold">~${{ runDialogEstimatedCost }}</span>
          </div>
          <div class="mt-1 text-gray-600 dark:text-gray-400">
            Workload:
            <b>{{ runDialogPlaceCount.toLocaleString('de-DE') }}</b>
            <span v-if="runDialogIsEnrich"> Prospects (aus dem Pool)</span>
            <span v-else> erwartete neue Leads</span>
          </div>
          <ul class="mt-2 space-y-0.5">
            <li
              v-for="s in runDialogStageCosts"
              :key="s.key"
              class="flex justify-between text-gray-500"
            >
              <span>↳ {{ s.label }}</span>
              <span>${{ s.usd }}</span>
            </li>
          </ul>
        </div>

        <p
          v-if="runDialog.error"
          class="mt-3 rounded-lg bg-red-50 p-2 text-sm text-red-700 dark:bg-red-900/40 dark:text-red-200"
        >
          {{ runDialog.error }}
        </p>

        <div class="mt-5 flex justify-end gap-2">
          <button
            class="rounded-lg border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-700"
            :disabled="runDialog.busy"
            @click="closeRunDialog"
          >
            Abbrechen
          </button>
          <button
            class="rounded-lg bg-go4-primary px-3 py-1.5 text-sm font-medium text-white disabled:opacity-60"
            :disabled="runDialog.busy || !runDialog.selectedStages.length"
            @click="confirmRun"
          >
            {{ runDialog.busy ? 'Startet…' : 'Run starten' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Resume Dialog -->
    <div
      v-if="resumeDialog.open"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      @click.self="closeResumeDialog"
    >
      <div class="w-full max-w-md rounded-xl bg-white p-6 shadow-xl dark:bg-gray-800">
        <h3 class="text-lg font-semibold">
          Run fortsetzen
        </h3>
        <p class="mt-2 text-sm text-gray-600 dark:text-gray-400">
          Zusätzliches Budget in API Calls. Wird zu <b>max_api_calls</b> der Kampagne addiert, dann
          wechselt der Run von <code>stopped</code> zu <code>queued</code>.
        </p>
        <label class="mt-4 block text-sm">
          <span class="text-gray-700 dark:text-gray-300">Zusätzliche API Calls</span>
          <input
            v-model.number="resumeDialog.additionalBudget"
            type="number"
            min="1"
            max="100000"
            class="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900"
          >
        </label>
        <p class="mt-2 text-xs text-gray-500">
          Kosten-Schätzung: {{ formatCost((resumeDialog.additionalBudget || 0) * 3) }}
          (bei 3 ct/Call)
        </p>
        <div class="mt-5 flex justify-end gap-2">
          <button
            class="rounded-lg border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-700"
            :disabled="resumeDialog.busy"
            @click="closeResumeDialog"
          >
            Abbrechen
          </button>
          <button
            class="rounded-lg bg-go4-primary px-3 py-1.5 text-sm font-medium text-white disabled:opacity-60"
            :disabled="resumeDialog.busy || !resumeDialog.additionalBudget"
            @click="confirmResume"
          >
            {{ resumeDialog.busy ? 'Startet…' : 'Fortsetzen' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
