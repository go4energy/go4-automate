<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useLeadgenStore } from '@/stores/leadgen'
import PageHeader from '@/components/ui/PageHeader.vue'
import LeadgenRunStageTimeline from '@/components/leadgen/LeadgenRunStageTimeline.vue'

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
    default:
      return `${base} bg-gray-100 text-gray-700`
  }
}

const resumeDialog = ref({ open: false, runId: null, additionalBudget: 2000, busy: false })

const enrichDialog = ref({
  open: false,
  limit: 100,
  sampling: 'top_rated',
  busy: false,
  error: null
})

const handoffDialog = ref({
  open: false,
  minScore: 7,
  limit: 100,
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
      limit: handoffDialog.value.limit
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
      limit: handoffDialog.value.limit
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

function openEnrichDialog() {
  enrichDialog.value = {
    open: true,
    limit: Math.min(100, enrichEligibleCount.value || 100),
    sampling: 'top_rated',
    busy: false,
    error: null
  }
}

function closeEnrichDialog() {
  if (enrichDialog.value.busy) return
  enrichDialog.value.open = false
}

async function confirmEnrich() {
  enrichDialog.value.busy = true
  enrichDialog.value.error = null
  try {
    await store.launchEnrichRun(campaignId.value, {
      limit: enrichDialog.value.limit,
      sampling: enrichDialog.value.sampling
    })
    enrichDialog.value.open = false
    await loadAll()
  } catch (e) {
    enrichDialog.value.error =
      e.response?.data?.detail || e.message || 'Anreicherungs-Run fehlgeschlagen'
  } finally {
    enrichDialog.value.busy = false
  }
}

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
    paused: 'bg-yellow-100 text-yellow-800',
    completed: 'bg-gray-100 text-gray-800',
    failed: 'bg-red-100 text-red-800'
  }
  return map[status] || 'bg-gray-100 text-gray-800'
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

async function pauseRun(runId) {
  statusErr.value = null
  try {
    await store.pauseRunAction(runId)
    await loadAll()
  } catch (e) {
    statusErr.value = e.response?.data?.detail || e.message
  }
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
  <div class="p-6 space-y-4">
    <div v-if="campaign">
      <PageHeader :title="campaign.name" :subtitle="campaign.slug" />

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
          @click="startRun"
        >
          {{ starting ? 'Startet…' : 'Run starten' }}
        </button>
        <button
          :disabled="enrichEligibleCount === 0"
          class="rounded-lg border border-purple-300 bg-purple-50 px-3 py-1.5 text-sm font-medium text-purple-700 hover:bg-purple-100 disabled:opacity-60 dark:border-purple-700 dark:bg-purple-900/40 dark:text-purple-200 dark:hover:bg-purple-900/60"
          @click="openEnrichDialog"
        >
          🤖 Anreichern…
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
          📊 LinkedIn-Export…
        </button>
        <button class="ml-auto text-sm text-gray-500 hover:underline" @click="goBack">
          ← Zur Übersicht
        </button>
      </div>

      <p v-if="!campaign.target_engagement_pipeline_id" class="mt-2 text-xs text-yellow-700">
        Diese Kampagne ist keiner Engagement-Pipeline zugeordnet — Runs können nicht gestartet
        werden.
      </p>
      <p v-if="!canStartRun()" class="mt-2 text-xs text-yellow-700">
        Diese Kampagne hat keine Suchkonfiguration — Runs können nicht gestartet werden.
      </p>
      <p v-if="statusErr" class="mt-2 rounded-lg bg-red-50 p-2 text-sm text-red-700">
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
            <span v-if="stats" class="ml-1 text-xs text-gray-500">
              ({{ stats.total_places.toLocaleString('de-DE') }})
            </span>
          </router-link>
        </div>
      </nav>

      <!-- DETAILS TAB -->
      <div v-if="activeTab === 'details'" class="mt-4 max-w-5xl">

      <!-- Info-Grid -->
      <div class="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div
          class="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
        >
          <h3 class="text-sm font-semibold mb-3">Konfiguration</h3>
          <dl class="space-y-1 text-sm">
            <div class="flex justify-between">
              <dt class="text-gray-500">Status</dt>
              <dd>{{ campaign.status }}</dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-gray-500">Quelle</dt>
              <dd>{{ campaign.source || 'google_places' }}</dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-gray-500">Sprache</dt>
              <dd>{{ campaign.language }}</dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-gray-500">Region</dt>
              <dd>{{ campaign.region }}</dd>
            </div>
            <div v-if="maxApiCalls" class="flex justify-between">
              <dt class="text-gray-500">Max. API Calls</dt>
              <dd>{{ maxApiCalls.toLocaleString('de-DE') }}</dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-gray-500">Match-Schwelle</dt>
              <dd>{{ campaign.target_match_threshold }}</dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-gray-500">Pipeline</dt>
              <dd>{{ campaign.target_engagement_pipeline_id || '—' }}</dd>
            </div>
          </dl>
        </div>

        <div
          class="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
        >
          <h3 class="text-sm font-semibold mb-3">Statistik</h3>
          <dl v-if="stats" class="space-y-1 text-sm">
            <div class="flex justify-between">
              <dt class="text-gray-500">Prospects gesamt</dt>
              <dd class="font-semibold">{{ stats.total_places.toLocaleString('de-DE') }}</dd>
            </div>
            <div
              v-for="(count, status) in stats.by_status"
              :key="status"
              class="flex justify-between"
            >
              <dt class="text-gray-500">&nbsp;&nbsp;{{ status }}</dt>
              <dd>{{ count.toLocaleString('de-DE') }}</dd>
            </div>
            <div class="flex justify-between pt-2 border-t border-gray-200 dark:border-gray-700">
              <dt class="text-gray-500">Runs gesamt</dt>
              <dd>{{ stats.runs_total }}</dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-gray-500">Runs laufen</dt>
              <dd>{{ stats.runs_running }}</dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-gray-500">Kosten gesamt</dt>
              <dd class="font-semibold">{{ formatCost(stats.total_cost_cents) }}</dd>
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
          <div class="text-sm font-semibold">Runs</div>
          <span v-if="hasLiveRun()" class="text-xs text-green-700 dark:text-green-400">
            ● Live — aktualisiert alle {{ POLL_INTERVAL_MS / 1000 }}s
          </span>
        </div>
        <div v-if="store.runs.length === 0" class="p-6 text-center text-sm text-gray-500">
          Noch keine Runs.
        </div>
        <ul v-else class="divide-y divide-gray-200 dark:divide-gray-700">
          <li v-for="r in store.runs" :key="r.id" class="p-4 space-y-3">
            <div class="flex flex-wrap items-center gap-3 text-sm">
              <span class="font-mono text-gray-500">#{{ r.id }}</span>
              <span class="font-medium">{{ stageLabel(r.current_stage) }}</span>
              <span
                class="rounded-full px-2 py-0.5 text-xs font-medium"
                :class="statusBadgeClasses(r.status)"
              >
                {{ r.status }}
              </span>
              <span class="text-gray-500">
                {{ formatDate(r.started_at) }}
              </span>
              <span class="ml-auto flex items-center gap-2">
                <button
                  v-if="r.status === 'paused' && nextStageLabel(r.current_stage)"
                  class="rounded-lg bg-green-600 px-3 py-1 text-xs font-medium text-white hover:bg-green-700"
                  @click="advanceStage(r.id)"
                >
                  {{ nextStageLabel(r.current_stage) }}
                </button>
                <button
                  v-if="r.status === 'paused' && !nextStageLabel(r.current_stage)"
                  class="rounded-lg bg-go4-primary px-3 py-1 text-xs font-medium text-white"
                  @click="openResumeDialog(r.id)"
                >
                  Fortsetzen
                </button>
                <button
                  v-if="r.status === 'running' || r.status === 'queued'"
                  class="rounded-lg border border-gray-300 px-3 py-1 text-xs font-medium hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-700"
                  @click="pauseRun(r.id)"
                >
                  Pausieren
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

            <p v-if="r.last_error" class="rounded-lg bg-red-50 p-2 text-xs text-red-700">
              {{ r.last_error }}
            </p>
          </li>
        </ul>
      </div>
      </div><!-- /Details TAB -->

      <!-- PLACES TAB -->
      <div v-if="activeTab === 'places'" class="mt-4 space-y-3">
        <div class="flex items-center justify-between gap-3">
          <select
            v-model="placesStatusFilter"
            class="w-56 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800"
          >
            <option value="">Alle Status</option>
            <option value="discovered">discovered</option>
            <option value="impressum_done">impressum_done</option>
            <option value="impressum_failed">impressum_failed</option>
            <option value="llm_done">llm_done</option>
            <option value="llm_failed">llm_failed</option>
            <option value="enrolled">enrolled</option>
            <option value="rejected">rejected</option>
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
                <th class="cursor-pointer select-none px-3 py-2 hover:bg-gray-100 dark:hover:bg-gray-800" @click="toggleSort('name')">
                  Firma {{ sortIndicator('name') }}
                </th>
                <th class="cursor-pointer select-none px-3 py-2 hover:bg-gray-100 dark:hover:bg-gray-800" @click="toggleSort('city')">
                  Stadt {{ sortIndicator('city') }}
                </th>
                <th class="cursor-pointer select-none px-3 py-2 hover:bg-gray-100 dark:hover:bg-gray-800" @click="toggleSort('status')">
                  Status {{ sortIndicator('status') }}
                </th>
                <th class="cursor-pointer select-none px-3 py-2 text-right hover:bg-gray-100 dark:hover:bg-gray-800" @click="toggleSort('match')">
                  Match {{ sortIndicator('match') }}
                </th>
                <th class="cursor-pointer select-none px-3 py-2 hover:bg-gray-100 dark:hover:bg-gray-800" @click="toggleSort('rating')">
                  Bewertung {{ sortIndicator('rating') }}
                </th>
                <th class="px-3 py-2">Website</th>
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
                  <span v-else class="text-gray-400">—</span>
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
                  <span v-else class="text-gray-400">—</span>
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
              <option :value="25">25</option>
              <option :value="50">50</option>
              <option :value="100">100</option>
              <option :value="200">200</option>
            </select>
            <button
              :disabled="placesPage <= 1"
              class="rounded-lg border border-gray-300 px-2.5 py-1 text-xs disabled:opacity-40 hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-700"
              @click="prevPlacesPage"
            >← zurück</button>
            <button
              :disabled="placesPage >= placesTotalPages"
              class="rounded-lg border border-gray-300 px-2.5 py-1 text-xs disabled:opacity-40 hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-700"
              @click="nextPlacesPage"
            >weiter →</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Export Dialog -->
    <div
      v-if="exportDialog.open"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      @click.self="closeExportDialog"
    >
      <div class="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl dark:bg-gray-800">
        <h3 class="text-lg font-semibold">LinkedIn Sales Navigator Export</h3>
        <p class="mt-2 text-sm text-gray-600 dark:text-gray-400">
          Lädt CSV-Dateien für den Sales-Nav-Bulk-Upload — eine für Firmen
          (Account-Liste) und eine für Personen (Lead-Liste). UTF-8 mit BOM,
          direkt Excel-tauglich.
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
            />
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
            />
          </label>
        </div>

        <label class="mt-3 flex items-center gap-2 text-sm">
          <input
            v-model="exportDialog.onlyEnrolled"
            type="checkbox"
            @change="refreshExportPreview"
          />
          <span class="text-gray-700 dark:text-gray-300">
            Nur Firmen, die bereits im Funnel sind
          </span>
        </label>

        <div
          v-if="exportDialog.preview"
          class="mt-4 rounded-lg bg-gray-50 dark:bg-gray-900/50 p-3 text-sm space-y-1"
        >
          <div class="flex justify-between">
            <span>Firmen (Account-Liste)</span>
            <b>{{ exportDialog.preview.accounts_count.toLocaleString('de-DE') }}</b>
          </div>
          <div class="flex justify-between">
            <span>Personen (Lead-Liste)</span>
            <b>{{ exportDialog.preview.leads_count.toLocaleString('de-DE') }}</b>
          </div>
          <p class="pt-1 text-xs text-gray-500">
            Pro Firma werden alle gefundenen Geschäftsführer als separate Zeilen
            in die Lead-Liste exportiert.
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
            📥 Firmen ({{ exportDialog.preview?.accounts_count || 0 }})
          </button>
          <button
            class="rounded-lg border border-blue-300 bg-blue-50 px-3 py-1.5 text-sm font-medium text-blue-700 hover:bg-blue-100 disabled:opacity-60 dark:border-blue-700 dark:bg-blue-900/40 dark:text-blue-200 dark:hover:bg-blue-900/60"
            :disabled="exportDialog.busy || !exportDialog.preview?.leads_count"
            @click="downloadExport('leads')"
          >
            📥 Personen ({{ exportDialog.preview?.leads_count || 0 }})
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
        <h3 class="text-lg font-semibold">Top-Leads in Funnel kippen</h3>
        <p class="mt-2 text-sm text-gray-600 dark:text-gray-400">
          Konvertiert qualifizierende Prospects in Contacts und reiht sie in die
          verknüpfte Engagement-Pipeline ein. Prospects ohne Email werden übersprungen.
        </p>

        <div v-if="handoffDialog.result" class="mt-4 space-y-2">
          <div class="rounded-lg border border-emerald-300 bg-emerald-50 p-3 text-sm dark:border-emerald-700 dark:bg-emerald-900/30">
            <div class="font-medium text-emerald-900 dark:text-emerald-100">
              ✓ Handoff erfolgreich
            </div>
            <ul class="mt-2 space-y-0.5 text-xs text-emerald-800 dark:text-emerald-200">
              <li>{{ handoffDialog.result.enrolled }} Leads in Pipeline #{{ handoffDialog.result.pipeline_id }} eingereiht</li>
              <li>{{ handoffDialog.result.contacts_created }} neue Contacts angelegt, {{ handoffDialog.result.contacts_reused }} wiederverwendet</li>
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
              />
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
              />
            </label>
          </div>

          <div
            v-if="handoffDialog.preview"
            class="mt-4 rounded-lg bg-gray-50 p-3 text-xs space-y-0.5 dark:bg-gray-900/50"
          >
            <div class="font-medium text-gray-800 dark:text-gray-200">Vorschau</div>
            <div>Eligible insgesamt: <b>{{ handoffDialog.preview.eligible_total }}</b></div>
            <div>Davon mit Email (werden enrolled): <b class="text-emerald-700 dark:text-emerald-300">{{ handoffDialog.preview.would_enroll }}</b></div>
            <div v-if="handoffDialog.preview.already_have_contact > 0" class="text-gray-500">
              {{ handoffDialog.preview.already_have_contact }} bereits als Contact verlinkt
            </div>
            <div v-if="handoffDialog.preview.missing_email > 0" class="text-yellow-700 dark:text-yellow-300">
              {{ handoffDialog.preview.missing_email }} ohne Impressum-Email werden übersprungen
            </div>
          </div>

          <div class="mt-3 rounded-lg bg-blue-50 dark:bg-blue-900/30 p-3 text-xs">
            <div class="font-medium text-blue-900 dark:text-blue-100">Pipeline</div>
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

    <!-- Enrich Dialog -->
    <div
      v-if="enrichDialog.open"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      @click.self="closeEnrichDialog"
    >
      <div class="w-full max-w-md rounded-xl bg-white p-6 shadow-xl dark:bg-gray-800">
        <h3 class="text-lg font-semibold">Firmen mit LLM anreichern</h3>
        <p class="mt-2 text-sm text-gray-600 dark:text-gray-400">
          Reichert Firmen aus dem Pool der noch nicht analysierten Prospects an.
          Springt direkt in Stage 3 — keine neuen Google-Calls.
        </p>
        <p class="mt-2 text-xs text-gray-500">
          Verfügbarer Pool: <b>{{ enrichEligibleCount.toLocaleString('de-DE') }}</b> Prospects
          ohne LLM-Analyse.
        </p>

        <label class="mt-4 block text-sm">
          <span class="text-gray-700 dark:text-gray-300">Anzahl Firmen</span>
          <input
            v-model.number="enrichDialog.limit"
            type="number"
            min="1"
            :max="Math.max(1, enrichEligibleCount)"
            class="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900"
          />
          <div class="mt-2 flex flex-wrap gap-1">
            <button
              v-for="n in [10, 50, 100, 500, 1000, 5000]"
              :key="n"
              type="button"
              :disabled="n > enrichEligibleCount"
              class="rounded-full border border-gray-300 px-2.5 py-0.5 text-xs hover:bg-gray-100 disabled:opacity-40 dark:border-gray-600 dark:hover:bg-gray-700"
              @click="enrichDialog.limit = n"
            >
              {{ n.toLocaleString('de-DE') }}
            </button>
            <button
              type="button"
              :disabled="enrichEligibleCount === 0"
              class="rounded-full border border-purple-300 bg-purple-50 px-2.5 py-0.5 text-xs font-medium text-purple-700 hover:bg-purple-100 disabled:opacity-40 dark:border-purple-700 dark:bg-purple-900/40 dark:text-purple-200 dark:hover:bg-purple-900/60"
              @click="enrichDialog.limit = enrichEligibleCount"
            >
              Alle ({{ enrichEligibleCount.toLocaleString('de-DE') }})
            </button>
          </div>
        </label>

        <fieldset class="mt-4 text-sm">
          <legend class="text-gray-700 dark:text-gray-300">Auswahl</legend>
          <label class="mt-1 flex items-start gap-2 rounded-lg border border-gray-200 p-2 cursor-pointer dark:border-gray-600">
            <input
              v-model="enrichDialog.sampling"
              type="radio"
              value="top_rated"
              class="mt-0.5"
            />
            <span>
              <span class="font-medium">Best-bewertet zuerst</span>
              <span class="block text-xs text-gray-500">
                Sortiert nach Google-Sterne-Bewertung — die etabliertesten Betriebe zuerst.
              </span>
            </span>
          </label>
          <label class="mt-1 flex items-start gap-2 rounded-lg border border-gray-200 p-2 cursor-pointer dark:border-gray-600">
            <input
              v-model="enrichDialog.sampling"
              type="radio"
              value="random"
              class="mt-0.5"
            />
            <span>
              <span class="font-medium">Zufällig</span>
              <span class="block text-xs text-gray-500">
                Gleichmäßige Stichprobe über den ganzen Pool — gut für Qualitäts-Tests.
              </span>
            </span>
          </label>
        </fieldset>

        <div class="mt-4 rounded-lg bg-gray-50 p-3 text-xs dark:bg-gray-900/50">
          <div class="font-medium">Kosten-Schätzung</div>
          <div class="text-gray-600 dark:text-gray-400">
            ~${{ enrichCostUsd }} ({{ enrichDialog.limit || 0 }} × $0.003 Haiku)
          </div>
        </div>

        <p
          v-if="enrichDialog.error"
          class="mt-3 rounded-lg bg-red-50 p-2 text-sm text-red-700 dark:bg-red-900/40 dark:text-red-200"
        >
          {{ enrichDialog.error }}
        </p>

        <div class="mt-5 flex justify-end gap-2">
          <button
            class="rounded-lg border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-700"
            :disabled="enrichDialog.busy"
            @click="closeEnrichDialog"
          >
            Abbrechen
          </button>
          <button
            class="rounded-lg bg-go4-primary px-3 py-1.5 text-sm font-medium text-white disabled:opacity-60"
            :disabled="enrichDialog.busy || !enrichDialog.limit || enrichDialog.limit < 1"
            @click="confirmEnrich"
          >
            {{ enrichDialog.busy ? 'Startet…' : 'Anreichern starten' }}
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
        <h3 class="text-lg font-semibold">Run fortsetzen</h3>
        <p class="mt-2 text-sm text-gray-600 dark:text-gray-400">
          Zusätzliches Budget in API Calls. Wird zu <b>max_api_calls</b> der Kampagne addiert, dann
          wechselt der Run von <code>paused</code> zu <code>queued</code>.
        </p>
        <label class="mt-4 block text-sm">
          <span class="text-gray-700 dark:text-gray-300">Zusätzliche API Calls</span>
          <input
            v-model.number="resumeDialog.additionalBudget"
            type="number"
            min="1"
            max="100000"
            class="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900"
          />
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
