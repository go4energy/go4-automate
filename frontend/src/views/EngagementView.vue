<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useEngagementStore } from '@/stores/engagement'
import PageHeader from '@/components/ui/PageHeader.vue'
import Breadcrumb from '@/components/ui/Breadcrumb.vue'
import SearchInput from '@/components/ui/SearchInput.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import MetaSetupTab from '@/components/engagement/MetaSetupTab.vue'
import AudiencesTab from '@/components/engagement/AudiencesTab.vue'
import OptimizationTab from '@/components/engagement/OptimizationTab.vue'

const router = useRouter()
const route = useRoute()
const store = useEngagementStore()

// Tab state from route
const activeTab = computed(() => route.meta?.tab || 'dashboard')

const searchQuery = ref('')
const statusFilter = ref('')
const showDeleteConfirm = ref(false)
const pipelineToDelete = ref(null)
const showDeleteABTestConfirm = ref(false)
const abTestToDelete = ref(null)
const showPixelCodeModal = ref(false)

const tabs = [
  { key: 'dashboard', label: 'Dashboard', route: '/engagement/dashboard' },
  { key: 'pipelines', label: 'Pipelines', route: '/engagement/pipelines' },
  { key: 'enrollments', label: 'Enrollments', route: '/engagement/enrollments' },
  { key: 'actions', label: 'Aktionen', route: '/engagement/actions' },
  { key: 'approval', label: 'Freigabe', route: '/engagement/approval' },
  { key: 'activities', label: 'Aktivitaeten', route: '/engagement/activities' },
  { key: 'ab-tests', label: 'A/B Tests', route: '/engagement/ab-tests' },
  { key: 'tracking', label: 'Tracking', route: '/engagement/tracking' },
  { key: 'meta', label: 'Meta', route: '/engagement/meta' },
  { key: 'audiences', label: 'Audiences', route: '/engagement/audiences' },
  { key: 'optimization', label: 'Optimierung', route: '/engagement/optimization' }
]

const stageLabels = {
  lead: 'Lead',
  contacted: 'Kontaktiert',
  engaged: 'Engagiert',
  qualified: 'Qualifiziert',
  converted: 'Konvertiert',
  lost: 'Verloren'
}

const stageColors = {
  lead: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
  contacted: 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300',
  engaged: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-300',
  qualified: 'bg-purple-100 text-purple-700 dark:bg-purple-900/50 dark:text-purple-300',
  converted: 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300',
  lost: 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300'
}

const statusLabels = {
  active: 'Aktiv',
  paused: 'Pausiert',
  completed: 'Abgeschlossen',
  stopped: 'Gestoppt'
}

const statusColors = {
  active: 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300',
  paused: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-300',
  completed: 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300',
  stopped: 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300'
}

const actionStatusLabels = {
  pending: 'Ausstehend',
  ready_for_approval: 'Zur Freigabe',
  approved: 'Freigegeben',
  completed: 'Erledigt',
  failed: 'Fehlgeschlagen',
  cancelled: 'Abgebrochen'
}

const actionStatusColors = {
  pending: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
  ready_for_approval: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-300',
  approved: 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300',
  completed: 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300',
  failed: 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300',
  cancelled: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
}

const abTestStatusLabels = {
  draft: 'Entwurf',
  running: 'Laufend',
  paused: 'Pausiert',
  completed: 'Abgeschlossen'
}

const abTestStatusColors = {
  draft: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
  running: 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300',
  paused: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-300',
  completed: 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300'
}

const channelIcons = {
  linkedin: 'M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.32 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.79M6.88 8.56a1.68 1.68 0 0 0 1.68-1.68c0-.93-.75-1.69-1.68-1.69a1.69 1.69 0 0 0-1.69 1.69c0 .93.76 1.68 1.69 1.68m1.39 9.94v-8.37H5.5v8.37h2.77z',
  email: 'M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z',
  phone: 'M6.62 10.79c1.44 2.83 3.76 5.14 6.59 6.59l2.2-2.2c.27-.27.67-.36 1.02-.24 1.12.37 2.33.57 3.57.57.55 0 1 .45 1 1V20c0 .55-.45 1-1 1-9.39 0-17-7.61-17-17 0-.55.45-1 1-1h3.5c.55 0 1 .45 1 1 0 1.25.2 2.45.57 3.57.11.35.03.74-.25 1.02l-2.2 2.2z',
  whatsapp: 'M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z',
  postmail: 'M20 8l-8 5-8-5V6l8 5 8-5m0-2H4c-1.11 0-2 .89-2 2v12a2 2 0 002 2h16a2 2 0 002-2V6a2 2 0 00-2-2z',
  meeting: 'M19 3h-1V1h-2v2H8V1H6v2H5c-1.11 0-1.99.9-1.99 2L3 19c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V8h14v11zM9 10H7v2h2v-2zm4 0h-2v2h2v-2zm4 0h-2v2h2v-2zm-8 4H7v2h2v-2zm4 0h-2v2h2v-2zm4 0h-2v2h2v-2z'
}

const filteredPipelines = computed(() => {
  let result = store.pipelines
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(
      (p) => p.name.toLowerCase().includes(query) || p.product_name?.toLowerCase().includes(query)
    )
  }
  return result
})

const filteredEnrollments = computed(() => {
  let result = store.enrollments
  if (statusFilter.value) {
    result = result.filter((e) => e.status === statusFilter.value)
  }
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(
      (e) =>
        e.contact?.email?.toLowerCase().includes(query) ||
        e.contact?.first_name?.toLowerCase().includes(query) ||
        e.contact?.last_name?.toLowerCase().includes(query)
    )
  }
  return result
})

const filteredActions = computed(() => {
  let result = store.pendingActions
  if (statusFilter.value) {
    result = result.filter((a) => a.status === statusFilter.value)
  }
  return result
})

const filteredABTests = computed(() => {
  let result = store.abTests
  if (statusFilter.value) {
    result = result.filter((t) => t.status === statusFilter.value)
  }
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(
      (t) => t.name.toLowerCase().includes(query) || t.description?.toLowerCase().includes(query)
    )
  }
  return result
})

const filteredTrackingLinks = computed(() => {
  let result = store.trackingLinks
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter((l) => l.target_url?.toLowerCase().includes(query))
  }
  return result
})

onMounted(async () => {
  await loadData()
})

watch(activeTab, async () => {
  searchQuery.value = ''
  statusFilter.value = ''
  await loadData()
})

async function loadData() {
  try {
    if (activeTab.value === 'dashboard') {
      await store.fetchDashboard()
      await store.fetchPipelines()
    } else if (activeTab.value === 'pipelines') {
      await store.fetchPipelines()
    } else if (activeTab.value === 'enrollments') {
      await store.fetchEnrollments()
    } else if (activeTab.value === 'actions') {
      await store.fetchActions()
    } else if (activeTab.value === 'approval') {
      await store.fetchApprovalQueue()
    } else if (activeTab.value === 'activities') {
      await store.fetchRecentActivities(50)
    } else if (activeTab.value === 'ab-tests') {
      await store.fetchABTests()
      await store.fetchPipelines()
    } else if (activeTab.value === 'tracking') {
      await store.fetchTrackingLinks()
      await store.fetchEventSummary()
      await store.fetchAttributionDashboard()
    }
  } catch {
    // Error is set in store
  }
}

function goToPipeline(pipeline) {
  router.push({ name: 'engagement-pipeline-detail', params: { id: pipeline.id } })
}

function editPipeline(pipeline) {
  router.push({ name: 'engagement-pipeline-edit', params: { id: pipeline.id } })
}

function createPipeline() {
  router.push({ name: 'engagement-pipeline-new' })
}

function confirmDeletePipeline(pipeline) {
  pipelineToDelete.value = pipeline
  showDeleteConfirm.value = true
}

async function deletePipeline() {
  if (!pipelineToDelete.value) return
  try {
    await store.removePipeline(pipelineToDelete.value.id)
  } catch {
    // Error is in store
  } finally {
    showDeleteConfirm.value = false
    pipelineToDelete.value = null
  }
}

async function approveAction(action) {
  try {
    await store.approve(action.id)
    await loadData()
  } catch {
    // Error is in store
  }
}

async function cancelAction(action) {
  try {
    await store.cancel(action.id)
    await loadData()
  } catch {
    // Error is in store
  }
}

// A/B Test functions
function createABTest() {
  router.push({ name: 'engagement-ab-test-new' })
}

function editABTest(test) {
  router.push({ name: 'engagement-ab-test-edit', params: { id: test.id } })
}

function confirmDeleteABTest(test) {
  abTestToDelete.value = test
  showDeleteABTestConfirm.value = true
}

async function deleteABTest() {
  if (!abTestToDelete.value) return
  try {
    await store.removeABTest(abTestToDelete.value.id)
    showDeleteABTestConfirm.value = false
    abTestToDelete.value = null
  } catch {
    // Error is in store
  }
}

async function startABTest(test) {
  try {
    await store.startTest(test.id)
    await loadData()
  } catch {
    // Error is in store
  }
}

async function pauseABTest(test) {
  try {
    await store.pauseTest(test.id)
    await loadData()
  } catch {
    // Error is in store
  }
}

async function completeABTest(test) {
  try {
    await store.completeTest(test.id)
    await loadData()
  } catch {
    // Error is in store
  }
}

// Tracking functions
async function openPixelCodeModal() {
  await store.fetchPixelCode()
  showPixelCodeModal.value = true
}

async function copyPixelCode() {
  if (store.pixelCode?.code) {
    await navigator.clipboard.writeText(store.pixelCode.code)
  }
}

async function deactivateTrackingLink(link) {
  try {
    await store.deactivateLink(link.id)
    await loadData()
  } catch {
    // Error is in store
  }
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function formatChannel(channel) {
  const labels = {
    linkedin: 'LinkedIn',
    email: 'Email',
    phone: 'Telefon',
    whatsapp: 'WhatsApp',
    postmail: 'Brief',
    meeting: 'Meeting'
  }
  return labels[channel] || channel
}
</script>

<template>
  <div class="min-h-screen bg-go4-bg dark:bg-gray-900">
    <PageHeader
      title="Engagement"
      subtitle="Multi-Channel KI-gesteuertes Engagement"
    />

    <div class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <Breadcrumb class="mb-4" />

      <!-- Tabs -->
      <nav class="-mb-px flex gap-6 border-b border-gray-200 dark:border-gray-700">
        <router-link
          v-for="tab in tabs"
          :key="tab.key"
          :to="tab.route"
          class="border-b-2 pb-3 text-sm font-medium transition-colors"
          :class="
            activeTab === tab.key
              ? 'border-go4-primary text-go4-primary'
              : 'border-transparent text-go4-muted hover:border-gray-300 hover:text-go4-secondary dark:text-gray-400 dark:hover:text-gray-300'
          "
        >
          {{ tab.label }}
        </router-link>
      </nav>

      <!-- Loading -->
      <div
        v-if="store.loading"
        class="mt-8 flex items-center justify-center py-12"
      >
        <span class="text-go4-muted dark:text-gray-400">Laden...</span>
      </div>

      <!-- Error -->
      <div
        v-else-if="store.error"
        class="mt-8 rounded-lg bg-red-50 p-4 text-red-700 dark:bg-red-900/30 dark:text-red-300"
      >
        {{ store.error }}
      </div>

      <!-- Dashboard Tab -->
      <div
        v-else-if="activeTab === 'dashboard'"
        class="mt-6 space-y-6"
      >
        <!-- Stats Cards -->
        <div class="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
          <div class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-sm text-go4-muted dark:text-gray-400">
                  Aktive Pipelines
                </p>
                <p class="mt-1 text-2xl font-semibold text-go4-secondary dark:text-white">
                  {{ store.activePipelines.length }}
                </p>
              </div>
              <div class="rounded-lg bg-purple-100 p-3 dark:bg-purple-900/30">
                <svg
                  class="h-6 w-6 text-purple-600 dark:text-purple-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M13 10V3L4 14h7v7l9-11h-7z"
                  />
                </svg>
              </div>
            </div>
          </div>

          <div class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-sm text-go4-muted dark:text-gray-400">
                  Aktive Enrollments
                </p>
                <p class="mt-1 text-2xl font-semibold text-go4-secondary dark:text-white">
                  {{ store.activeEnrollments.length }}
                </p>
              </div>
              <div class="rounded-lg bg-blue-100 p-3 dark:bg-blue-900/30">
                <svg
                  class="h-6 w-6 text-blue-600 dark:text-blue-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
                  />
                </svg>
              </div>
            </div>
          </div>

          <div class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-sm text-go4-muted dark:text-gray-400">
                  Zur Freigabe
                </p>
                <p class="mt-1 text-2xl font-semibold text-go4-secondary dark:text-white">
                  {{ store.pendingActionsCount }}
                </p>
              </div>
              <div class="rounded-lg bg-yellow-100 p-3 dark:bg-yellow-900/30">
                <svg
                  class="h-6 w-6 text-yellow-600 dark:text-yellow-400"
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
              </div>
            </div>
          </div>

          <div class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-sm text-go4-muted dark:text-gray-400">
                  Aktivitaeten heute
                </p>
                <p class="mt-1 text-2xl font-semibold text-go4-secondary dark:text-white">
                  {{ store.dashboard?.activities_today || 0 }}
                </p>
              </div>
              <div class="rounded-lg bg-green-100 p-3 dark:bg-green-900/30">
                <svg
                  class="h-6 w-6 text-green-600 dark:text-green-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </div>
            </div>
          </div>
        </div>

        <!-- Recent Pipelines -->
        <div class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
          <div class="mb-4 flex items-center justify-between">
            <h3 class="font-semibold text-go4-secondary dark:text-white">
              Pipelines
            </h3>
            <router-link
              to="/engagement/pipelines"
              class="text-sm text-go4-primary hover:text-go4-primary-dark"
            >
              Alle anzeigen
            </router-link>
          </div>

          <div
            v-if="store.pipelines.length === 0"
            class="py-8 text-center text-go4-muted dark:text-gray-400"
          >
            Keine Pipelines vorhanden.
            <button
              class="mt-2 block w-full text-go4-primary hover:text-go4-primary-dark"
              @click="createPipeline"
            >
              Erste Pipeline erstellen
            </button>
          </div>

          <div
            v-else
            class="space-y-3"
          >
            <div
              v-for="pipeline in store.pipelines.slice(0, 5)"
              :key="pipeline.id"
              class="flex cursor-pointer items-center justify-between rounded-lg border border-gray-100 p-4 hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-700/50"
              @click="goToPipeline(pipeline)"
            >
              <div>
                <p class="font-medium text-go4-secondary dark:text-white">
                  {{ pipeline.name }}
                </p>
                <p class="text-sm text-go4-muted dark:text-gray-400">
                  {{ pipeline.product_name }}
                </p>
              </div>
              <div class="flex items-center gap-4">
                <div class="flex gap-1">
                  <svg
                    v-for="channel in (pipeline.channels || []).slice(0, 4)"
                    :key="channel"
                    class="h-5 w-5 text-gray-400"
                    viewBox="0 0 24 24"
                    fill="currentColor"
                  >
                    <path :d="channelIcons[channel] || channelIcons.email" />
                  </svg>
                </div>
                <span
                  class="rounded-full px-2 py-0.5 text-xs font-medium"
                  :class="pipeline.is_active ? 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300' : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'"
                >
                  {{ pipeline.is_active ? 'Aktiv' : 'Inaktiv' }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Pipelines Tab -->
      <div
        v-else-if="activeTab === 'pipelines'"
        class="mt-6"
      >
        <!-- Header with search and add button -->
        <div class="mb-6 flex items-center justify-between gap-4">
          <SearchInput
            v-model="searchQuery"
            placeholder="Pipeline suchen..."
            class="w-64"
          />
          <button
            class="flex items-center gap-2 rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark"
            @click="createPipeline"
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
            Neue Pipeline
          </button>
        </div>

        <EmptyState
          v-if="filteredPipelines.length === 0"
          title="Keine Pipelines"
          description="Erstelle deine erste Engagement-Pipeline."
        >
          <button
            class="mt-4 rounded-lg bg-go4-primary px-4 py-2 text-sm text-white hover:bg-go4-primary-dark"
            @click="createPipeline"
          >
            Pipeline erstellen
          </button>
        </EmptyState>

        <div
          v-else
          class="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3"
        >
          <div
            v-for="pipeline in filteredPipelines"
            :key="pipeline.id"
            class="group relative rounded-lg border border-gray-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md dark:border-gray-700 dark:bg-gray-800"
          >
            <!-- Header -->
            <div class="mb-3 flex items-start justify-between">
              <div
                class="flex-1 cursor-pointer"
                @click="goToPipeline(pipeline)"
              >
                <h3 class="font-medium text-go4-secondary dark:text-white">
                  {{ pipeline.name }}
                </h3>
                <p
                  v-if="pipeline.product_name"
                  class="mt-1 text-sm text-go4-muted dark:text-gray-400"
                >
                  {{ pipeline.product_name }}
                </p>
              </div>

              <!-- Actions -->
              <div class="ml-2 flex gap-1">
                <button
                  class="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700 dark:hover:text-gray-300"
                  title="Bearbeiten"
                  @click="editPipeline(pipeline)"
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
                  class="rounded p-1 text-gray-400 hover:bg-red-100 hover:text-red-600 dark:hover:bg-red-900/30 dark:hover:text-red-400"
                  title="Loeschen"
                  @click="confirmDeletePipeline(pipeline)"
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

            <!-- Status -->
            <div class="mb-3 flex items-center gap-2">
              <span
                class="rounded-full px-2 py-0.5 text-xs font-medium"
                :class="pipeline.is_active ? 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300' : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'"
              >
                {{ pipeline.is_active ? 'Aktiv' : 'Inaktiv' }}
              </span>
              <span class="text-xs text-go4-muted dark:text-gray-500">
                {{ pipeline.goal || 'Kein Ziel definiert' }}
              </span>
            </div>

            <!-- Channels -->
            <div class="mb-3 flex items-center gap-2">
              <span class="text-xs text-go4-muted dark:text-gray-500">Kanaele:</span>
              <div class="flex gap-1">
                <span
                  v-for="channel in (pipeline.channels || [])"
                  :key="channel"
                  class="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-700 dark:bg-gray-700 dark:text-gray-300"
                >
                  {{ formatChannel(channel) }}
                </span>
              </div>
            </div>

            <!-- Stats -->
            <div class="flex items-center gap-4 text-sm text-go4-muted dark:text-gray-400">
              <div class="flex items-center gap-1">
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
                    d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
                  />
                </svg>
                <span>{{ pipeline.enrollment_count || 0 }} Enrollments</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Enrollments Tab -->
      <div
        v-else-if="activeTab === 'enrollments'"
        class="mt-6"
      >
        <!-- Filters -->
        <div class="mb-6 flex items-center gap-4">
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
            <option value="active">
              Aktiv
            </option>
            <option value="paused">
              Pausiert
            </option>
            <option value="completed">
              Abgeschlossen
            </option>
            <option value="stopped">
              Gestoppt
            </option>
          </select>
        </div>

        <EmptyState
          v-if="filteredEnrollments.length === 0"
          title="Keine Enrollments"
          description="Noch keine Kontakte in Pipelines eingeschrieben."
        />

        <div
          v-else
          class="overflow-hidden rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800"
        >
          <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead class="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-300">
                  Kontakt
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-300">
                  Pipeline
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-300">
                  Stage
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-300">
                  Status
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-300">
                  Letzter Kontakt
                </th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-200 bg-white dark:divide-gray-700 dark:bg-gray-800">
              <tr
                v-for="enrollment in filteredEnrollments"
                :key="enrollment.id"
                class="hover:bg-gray-50 dark:hover:bg-gray-700/50"
              >
                <td class="whitespace-nowrap px-6 py-4">
                  <div>
                    <p class="font-medium text-go4-secondary dark:text-white">
                      {{ enrollment.contact?.first_name }} {{ enrollment.contact?.last_name }}
                    </p>
                    <p class="text-sm text-go4-muted dark:text-gray-400">
                      {{ enrollment.contact?.email }}
                    </p>
                  </div>
                </td>
                <td class="whitespace-nowrap px-6 py-4 text-sm text-go4-secondary dark:text-gray-200">
                  {{ enrollment.pipeline?.name || '-' }}
                </td>
                <td class="whitespace-nowrap px-6 py-4">
                  <span
                    class="rounded-full px-2 py-0.5 text-xs font-medium"
                    :class="stageColors[enrollment.stage]"
                  >
                    {{ stageLabels[enrollment.stage] }}
                  </span>
                </td>
                <td class="whitespace-nowrap px-6 py-4">
                  <span
                    class="rounded-full px-2 py-0.5 text-xs font-medium"
                    :class="statusColors[enrollment.status]"
                  >
                    {{ statusLabels[enrollment.status] }}
                  </span>
                </td>
                <td class="whitespace-nowrap px-6 py-4 text-sm text-go4-muted dark:text-gray-400">
                  {{ formatDate(enrollment.last_touch_at) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Actions Tab -->
      <div
        v-else-if="activeTab === 'actions'"
        class="mt-6"
      >
        <!-- Filters -->
        <div class="mb-6 flex items-center gap-4">
          <select
            v-model="statusFilter"
            class="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
          >
            <option value="">
              Alle Status
            </option>
            <option value="pending">
              Ausstehend
            </option>
            <option value="ready_for_approval">
              Zur Freigabe
            </option>
            <option value="approved">
              Freigegeben
            </option>
            <option value="completed">
              Erledigt
            </option>
            <option value="failed">
              Fehlgeschlagen
            </option>
          </select>
        </div>

        <EmptyState
          v-if="filteredActions.length === 0"
          title="Keine Aktionen"
          description="Keine ausstehenden Aktionen vorhanden."
        />

        <div
          v-else
          class="space-y-4"
        >
          <div
            v-for="action in filteredActions"
            :key="action.id"
            class="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
          >
            <div class="flex items-start justify-between">
              <div>
                <div class="flex items-center gap-2">
                  <svg
                    class="h-5 w-5 text-gray-400"
                    viewBox="0 0 24 24"
                    fill="currentColor"
                  >
                    <path :d="channelIcons[action.module] || channelIcons.email" />
                  </svg>
                  <span class="font-medium text-go4-secondary dark:text-white">
                    {{ formatChannel(action.module) }}: {{ action.action_type }}
                  </span>
                  <span
                    class="rounded-full px-2 py-0.5 text-xs font-medium"
                    :class="actionStatusColors[action.status]"
                  >
                    {{ actionStatusLabels[action.status] }}
                  </span>
                </div>
                <p class="mt-1 text-sm text-go4-muted dark:text-gray-400">
                  Kontakt: {{ action.contact?.first_name }} {{ action.contact?.last_name }}
                </p>
                <p
                  v-if="action.suggested_content"
                  class="mt-2 text-sm text-go4-secondary dark:text-gray-200"
                >
                  {{ action.suggested_content.substring(0, 200) }}{{ action.suggested_content.length > 200 ? '...' : '' }}
                </p>
              </div>
              <div
                v-if="action.status === 'ready_for_approval'"
                class="flex gap-2"
              >
                <button
                  class="rounded-lg bg-green-500 px-3 py-1.5 text-sm text-white hover:bg-green-600"
                  @click="approveAction(action)"
                >
                  Freigeben
                </button>
                <button
                  class="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
                  @click="cancelAction(action)"
                >
                  Abbrechen
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Approval Tab -->
      <div
        v-else-if="activeTab === 'approval'"
        class="mt-6"
      >
        <EmptyState
          v-if="store.approvalQueue.length === 0"
          title="Keine Freigaben"
          description="Keine Aktionen warten auf Freigabe."
        />

        <div
          v-else
          class="space-y-4"
        >
          <div
            v-for="action in store.approvalQueue"
            :key="action.id"
            class="rounded-lg border border-yellow-200 bg-yellow-50 p-4 dark:border-yellow-800/50 dark:bg-yellow-900/20"
          >
            <div class="flex items-start justify-between">
              <div>
                <div class="flex items-center gap-2">
                  <svg
                    class="h-5 w-5 text-yellow-600 dark:text-yellow-400"
                    viewBox="0 0 24 24"
                    fill="currentColor"
                  >
                    <path :d="channelIcons[action.module] || channelIcons.email" />
                  </svg>
                  <span class="font-medium text-go4-secondary dark:text-white">
                    {{ formatChannel(action.module) }}: {{ action.action_type }}
                  </span>
                </div>
                <p class="mt-1 text-sm text-go4-muted dark:text-gray-400">
                  Kontakt: {{ action.contact?.first_name }} {{ action.contact?.last_name }}
                </p>
                <p
                  v-if="action.suggested_content"
                  class="mt-2 rounded-lg bg-white p-3 text-sm text-go4-secondary dark:bg-gray-800 dark:text-gray-200"
                >
                  {{ action.suggested_content }}
                </p>
              </div>
              <div class="flex gap-2">
                <button
                  class="rounded-lg bg-green-500 px-3 py-1.5 text-sm text-white hover:bg-green-600"
                  @click="approveAction(action)"
                >
                  Freigeben
                </button>
                <button
                  class="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
                  @click="cancelAction(action)"
                >
                  Abbrechen
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Activities Tab -->
      <div
        v-else-if="activeTab === 'activities'"
        class="mt-6"
      >
        <EmptyState
          v-if="store.recentActivities.length === 0"
          title="Keine Aktivitaeten"
          description="Noch keine Aktivitaeten aufgezeichnet."
        />

        <div
          v-else
          class="space-y-4"
        >
          <div
            v-for="activity in store.recentActivities"
            :key="activity.id"
            class="flex gap-4 rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
          >
            <div
              class="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full"
              :class="activity.direction === 'inbound' ? 'bg-green-100 dark:bg-green-900/30' : 'bg-blue-100 dark:bg-blue-900/30'"
            >
              <svg
                class="h-5 w-5"
                :class="activity.direction === 'inbound' ? 'text-green-600 dark:text-green-400' : 'text-blue-600 dark:text-blue-400'"
                viewBox="0 0 24 24"
                fill="currentColor"
              >
                <path :d="channelIcons[activity.channel] || channelIcons.email" />
              </svg>
            </div>
            <div class="flex-1">
              <div class="flex items-center gap-2">
                <span class="font-medium text-go4-secondary dark:text-white">
                  {{ formatChannel(activity.channel) }}
                </span>
                <span
                  class="rounded-full px-2 py-0.5 text-xs font-medium"
                  :class="activity.direction === 'inbound' ? 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300' : 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300'"
                >
                  {{ activity.direction === 'inbound' ? 'Eingehend' : 'Ausgehend' }}
                </span>
                <span class="text-xs text-go4-muted dark:text-gray-500">
                  {{ activity.activity_type }}
                </span>
              </div>
              <p
                v-if="activity.subject"
                class="mt-1 text-sm text-go4-secondary dark:text-gray-200"
              >
                {{ activity.subject }}
              </p>
              <p
                v-if="activity.content"
                class="mt-1 line-clamp-2 text-sm text-go4-muted dark:text-gray-400"
              >
                {{ activity.content }}
              </p>
              <p class="mt-2 text-xs text-go4-muted dark:text-gray-500">
                {{ formatDate(activity.performed_at) }}
              </p>
            </div>
          </div>
        </div>
      </div>

      <!-- A/B Tests Tab -->
      <div
        v-else-if="activeTab === 'ab-tests'"
        class="mt-6"
      >
        <!-- Filters -->
        <div class="mb-6 flex items-center justify-between">
          <div class="flex items-center gap-4">
            <SearchInput
              v-model="searchQuery"
              placeholder="Test suchen..."
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
              <option value="running">
                Laufend
              </option>
              <option value="paused">
                Pausiert
              </option>
              <option value="completed">
                Abgeschlossen
              </option>
            </select>
          </div>
          <button
            class="flex items-center gap-2 rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark"
            @click="createABTest"
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
            Neuer A/B Test
          </button>
        </div>

        <EmptyState
          v-if="filteredABTests.length === 0"
          title="Keine A/B Tests"
          description="Erstelle deinen ersten A/B Test um verschiedene Varianten zu vergleichen."
        >
          <button
            class="mt-4 rounded-lg bg-go4-primary px-4 py-2 text-sm text-white hover:bg-go4-primary-dark"
            @click="createABTest"
          >
            A/B Test erstellen
          </button>
        </EmptyState>

        <div
          v-else
          class="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3"
        >
          <div
            v-for="test in filteredABTests"
            :key="test.id"
            class="rounded-lg border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-800"
          >
            <div class="mb-3 flex items-start justify-between">
              <div>
                <h3 class="font-medium text-go4-secondary dark:text-white">
                  {{ test.name }}
                </h3>
                <p class="mt-1 text-sm text-go4-muted dark:text-gray-400">
                  {{ test.test_type }} Test
                </p>
              </div>
              <span
                class="rounded-full px-2 py-0.5 text-xs font-medium"
                :class="abTestStatusColors[test.status]"
              >
                {{ abTestStatusLabels[test.status] }}
              </span>
            </div>

            <p
              v-if="test.description"
              class="mb-3 line-clamp-2 text-sm text-go4-muted dark:text-gray-400"
            >
              {{ test.description }}
            </p>

            <div class="mb-3 flex items-center gap-4 text-sm text-go4-muted dark:text-gray-400">
              <span>{{ test.variants?.length || 0 }} Varianten</span>
              <span
                v-if="test.sample_size"
              >Ziel: {{ test.sample_size }}</span>
            </div>

            <div class="flex items-center justify-between border-t border-gray-100 pt-3 dark:border-gray-700">
              <div class="flex gap-2">
                <button
                  v-if="test.status === 'draft'"
                  class="rounded-lg bg-green-500 px-3 py-1.5 text-xs text-white hover:bg-green-600"
                  @click="startABTest(test)"
                >
                  Starten
                </button>
                <button
                  v-if="test.status === 'running'"
                  class="rounded-lg bg-yellow-500 px-3 py-1.5 text-xs text-white hover:bg-yellow-600"
                  @click="pauseABTest(test)"
                >
                  Pausieren
                </button>
                <button
                  v-if="test.status === 'paused'"
                  class="rounded-lg bg-green-500 px-3 py-1.5 text-xs text-white hover:bg-green-600"
                  @click="startABTest(test)"
                >
                  Fortsetzen
                </button>
                <button
                  v-if="test.status === 'running' || test.status === 'paused'"
                  class="rounded-lg bg-blue-500 px-3 py-1.5 text-xs text-white hover:bg-blue-600"
                  @click="completeABTest(test)"
                >
                  Beenden
                </button>
              </div>
              <div class="flex gap-1">
                <button
                  class="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700 dark:hover:text-gray-300"
                  title="Bearbeiten"
                  @click="editABTest(test)"
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
                  class="rounded p-1 text-gray-400 hover:bg-red-100 hover:text-red-600 dark:hover:bg-red-900/30 dark:hover:text-red-400"
                  title="Loeschen"
                  @click="confirmDeleteABTest(test)"
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

      <!-- Tracking Tab -->
      <div
        v-else-if="activeTab === 'tracking'"
        class="mt-6 space-y-6"
      >
        <!-- Stats Cards -->
        <div class="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
          <div class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-sm text-go4-muted dark:text-gray-400">
                  Tracking Links
                </p>
                <p class="mt-1 text-2xl font-semibold text-go4-secondary dark:text-white">
                  {{ store.activeTrackingLinks.length }}
                </p>
              </div>
              <div class="rounded-lg bg-blue-100 p-3 dark:bg-blue-900/30">
                <svg
                  class="h-6 w-6 text-blue-600 dark:text-blue-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"
                  />
                </svg>
              </div>
            </div>
          </div>

          <div class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-sm text-go4-muted dark:text-gray-400">
                  Events (30 Tage)
                </p>
                <p class="mt-1 text-2xl font-semibold text-go4-secondary dark:text-white">
                  {{ store.eventSummary?.total_events || 0 }}
                </p>
              </div>
              <div class="rounded-lg bg-purple-100 p-3 dark:bg-purple-900/30">
                <svg
                  class="h-6 w-6 text-purple-600 dark:text-purple-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                  />
                </svg>
              </div>
            </div>
          </div>

          <div class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-sm text-go4-muted dark:text-gray-400">
                  Conversions
                </p>
                <p class="mt-1 text-2xl font-semibold text-go4-secondary dark:text-white">
                  {{ store.attributionDashboard?.total_conversions || 0 }}
                </p>
              </div>
              <div class="rounded-lg bg-green-100 p-3 dark:bg-green-900/30">
                <svg
                  class="h-6 w-6 text-green-600 dark:text-green-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </div>
            </div>
          </div>

          <div class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-sm text-go4-muted dark:text-gray-400">
                  Conversion-Wert
                </p>
                <p class="mt-1 text-2xl font-semibold text-go4-secondary dark:text-white">
                  {{ (store.attributionDashboard?.total_value || 0).toLocaleString('de-DE', { style: 'currency', currency: 'EUR' }) }}
                </p>
              </div>
              <div class="rounded-lg bg-yellow-100 p-3 dark:bg-yellow-900/30">
                <svg
                  class="h-6 w-6 text-yellow-600 dark:text-yellow-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </div>
            </div>
          </div>
        </div>

        <!-- Pixel Code Section -->
        <div class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
          <div class="mb-4 flex items-center justify-between">
            <h3 class="font-semibold text-go4-secondary dark:text-white">
              Website-Pixel
            </h3>
            <button
              class="flex items-center gap-2 rounded-lg bg-go4-primary px-4 py-2 text-sm text-white hover:bg-go4-primary-dark"
              @click="openPixelCodeModal"
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
                  d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"
                />
              </svg>
              Pixel-Code anzeigen
            </button>
          </div>
          <p class="text-sm text-go4-muted dark:text-gray-400">
            Integriere den Tracking-Pixel auf deiner Website um Besucher-Events zu erfassen und Cross-Channel-Attribution zu ermoeglichen.
          </p>
        </div>

        <!-- Tracking Links -->
        <div class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
          <div class="mb-4 flex items-center justify-between">
            <h3 class="font-semibold text-go4-secondary dark:text-white">
              Tracking Links
            </h3>
            <SearchInput
              v-model="searchQuery"
              placeholder="URL suchen..."
              class="w-64"
            />
          </div>

          <div
            v-if="filteredTrackingLinks.length === 0"
            class="py-8 text-center text-go4-muted dark:text-gray-400"
          >
            Keine Tracking-Links vorhanden. Links werden automatisch erstellt wenn Kontakte ueber Pipelines angesprochen werden.
          </div>

          <div
            v-else
            class="overflow-hidden rounded-lg border border-gray-100 dark:border-gray-700"
          >
            <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead class="bg-gray-50 dark:bg-gray-700">
                <tr>
                  <th class="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-300">
                    Ziel-URL
                  </th>
                  <th class="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-300">
                    UTM Source
                  </th>
                  <th class="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-300">
                    Klicks
                  </th>
                  <th class="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-300">
                    Status
                  </th>
                  <th class="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-300">
                    Erstellt
                  </th>
                  <th class="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-300">
                    Aktionen
                  </th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-200 bg-white dark:divide-gray-700 dark:bg-gray-800">
                <tr
                  v-for="link in filteredTrackingLinks.slice(0, 10)"
                  :key="link.id"
                  class="hover:bg-gray-50 dark:hover:bg-gray-700/50"
                >
                  <td class="max-w-xs truncate px-4 py-3 text-sm text-go4-secondary dark:text-gray-200">
                    {{ link.target_url }}
                  </td>
                  <td class="whitespace-nowrap px-4 py-3 text-sm text-go4-muted dark:text-gray-400">
                    {{ link.utm_source || '-' }}
                  </td>
                  <td class="whitespace-nowrap px-4 py-3 text-sm font-medium text-go4-secondary dark:text-white">
                    {{ link.click_count || 0 }}
                  </td>
                  <td class="whitespace-nowrap px-4 py-3">
                    <span
                      class="rounded-full px-2 py-0.5 text-xs font-medium"
                      :class="link.is_active ? 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300' : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'"
                    >
                      {{ link.is_active ? 'Aktiv' : 'Inaktiv' }}
                    </span>
                  </td>
                  <td class="whitespace-nowrap px-4 py-3 text-sm text-go4-muted dark:text-gray-400">
                    {{ formatDate(link.created_at) }}
                  </td>
                  <td class="whitespace-nowrap px-4 py-3 text-right">
                    <button
                      v-if="link.is_active"
                      class="text-sm text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300"
                      @click="deactivateTrackingLink(link)"
                    >
                      Deaktivieren
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Attribution by Channel -->
        <div
          v-if="store.attributionDashboard?.by_channel"
          class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800"
        >
          <h3 class="mb-4 font-semibold text-go4-secondary dark:text-white">
            Attribution nach Kanal
          </h3>
          <div class="space-y-3">
            <div
              v-for="(channel, index) in store.attributionDashboard.by_channel"
              :key="index"
              class="flex items-center justify-between rounded-lg bg-gray-50 p-3 dark:bg-gray-700/50"
            >
              <div class="flex items-center gap-3">
                <div class="h-3 w-3 rounded-full bg-go4-primary" />
                <span class="font-medium text-go4-secondary dark:text-white">
                  {{ formatChannel(channel.channel || 'Unbekannt') }}
                </span>
              </div>
              <div class="flex items-center gap-4 text-sm">
                <span class="text-go4-muted dark:text-gray-400">
                  {{ channel.conversion_count }} Conversions
                </span>
                <span class="font-medium text-go4-secondary dark:text-white">
                  {{ (channel.total_value || 0).toLocaleString('de-DE', { style: 'currency', currency: 'EUR' }) }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Meta Tab -->
      <div
        v-else-if="activeTab === 'meta'"
        class="mt-6"
      >
        <MetaSetupTab />
      </div>

      <!-- Audiences Tab -->
      <div
        v-else-if="activeTab === 'audiences'"
        class="mt-6"
      >
        <AudiencesTab />
      </div>

      <!-- Optimization Tab -->
      <div
        v-else-if="activeTab === 'optimization'"
        class="mt-6"
      >
        <OptimizationTab />
      </div>
    </div>

    <!-- Delete Confirmation -->
    <ConfirmDialog
      :open="showDeleteConfirm"
      title="Pipeline loeschen?"
      :message="`Moechtest du die Pipeline '${pipelineToDelete?.name}' wirklich loeschen? Alle Enrollments werden ebenfalls entfernt.`"
      confirm-text="Loeschen"
      variant="danger"
      @confirm="deletePipeline"
      @cancel="showDeleteConfirm = false"
    />

    <!-- A/B Test Delete Confirmation -->
    <ConfirmDialog
      :open="showDeleteABTestConfirm"
      title="A/B Test loeschen?"
      :message="`Moechtest du den A/B Test '${abTestToDelete?.name}' wirklich loeschen?`"
      confirm-text="Loeschen"
      variant="danger"
      @confirm="deleteABTest"
      @cancel="showDeleteABTestConfirm = false"
    />

    <!-- Pixel Code Modal -->
    <div
      v-if="showPixelCodeModal"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      @click.self="showPixelCodeModal = false"
    >
      <div class="mx-4 w-full max-w-2xl rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800">
        <div class="mb-4 flex items-center justify-between">
          <h3 class="text-lg font-semibold text-go4-secondary dark:text-white">
            Website-Pixel Code
          </h3>
          <button
            class="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700 dark:hover:text-gray-300"
            @click="showPixelCodeModal = false"
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
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <p class="mb-4 text-sm text-go4-muted dark:text-gray-400">
          Fuege diesen Code vor dem schliessenden &lt;/body&gt; Tag deiner Website ein.
        </p>

        <div class="relative">
          <pre class="max-h-96 overflow-auto rounded-lg bg-gray-900 p-4 text-sm text-gray-100">{{ store.pixelCode?.code || 'Lade...' }}</pre>
          <button
            class="absolute right-2 top-2 rounded bg-gray-700 px-3 py-1 text-xs text-white hover:bg-gray-600"
            @click="copyPixelCode"
          >
            Kopieren
          </button>
        </div>

        <div class="mt-4 flex justify-end">
          <button
            class="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
            @click="showPixelCodeModal = false"
          >
            Schliessen
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
