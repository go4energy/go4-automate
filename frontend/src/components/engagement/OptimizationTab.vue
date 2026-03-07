<script setup>
import { ref, computed, onMounted } from 'vue'
import { useEngagementStore } from '@/stores/engagement'
import {
  analyzePipeline,
  listReports,
  getReport,
  applyRecommendations,
  listInsights,
  getOptimizationStats
} from '@/api/optimization'
import EmptyState from '@/components/ui/EmptyState.vue'

const store = useEngagementStore()

const loading = ref(false)
const error = ref(null)
const stats = ref(null)
const reports = ref([])
const insights = ref([])
const selectedReport = ref(null)
const showReportModal = ref(false)
const showAnalyzeModal = ref(false)
const selectedPipelineId = ref(null)
const analyzeParams = ref({
  report_type: 'ad_hoc',
  days: 30
})
const analyzing = ref(false)
const applying = ref(false)

const priorityLabels = {
  high: 'Hoch',
  medium: 'Mittel',
  low: 'Niedrig'
}

const priorityColors = {
  high: 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300',
  medium: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-300',
  low: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
}

const statusLabels = {
  pending: 'Ausstehend',
  analyzing: 'Analysiert...',
  completed: 'Abgeschlossen',
  failed: 'Fehlgeschlagen'
}

const statusColors = {
  pending: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
  analyzing: 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300',
  completed: 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300',
  failed: 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300'
}

const insightTypeLabels = {
  pattern: 'Muster',
  recommendation: 'Empfehlung',
  warning: 'Warnung',
  opportunity: 'Chance'
}

const insightTypeColors = {
  pattern: 'bg-purple-100 text-purple-700 dark:bg-purple-900/50 dark:text-purple-300',
  recommendation: 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300',
  warning: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-300',
  opportunity: 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300'
}

onMounted(async () => {
  await loadData()
})

async function loadData() {
  loading.value = true
  error.value = null
  try {
    const [statsResult, reportsResult, insightsResult] = await Promise.all([
      getOptimizationStats(),
      listReports({ limit: 20 }),
      listInsights({ limit: 20, priority: 'high' })
    ])
    stats.value = statsResult.data
    reports.value = reportsResult.data.items
    insights.value = insightsResult.data.items

    // Pipelines laden falls noch nicht vorhanden
    if (store.pipelines.length === 0) {
      await store.fetchPipelines()
    }
  } catch (err) {
    error.value = err.response?.data?.detail || err.message
  } finally {
    loading.value = false
  }
}

function openAnalyzeModal() {
  selectedPipelineId.value = store.pipelines[0]?.id || null
  analyzeParams.value = { report_type: 'ad_hoc', days: 30 }
  showAnalyzeModal.value = true
}

async function runAnalysis() {
  if (!selectedPipelineId.value) return

  analyzing.value = true
  error.value = null
  try {
    const result = await analyzePipeline(selectedPipelineId.value, analyzeParams.value)
    showAnalyzeModal.value = false
    // Neuen Report zur Liste hinzufuegen
    reports.value.unshift(result.data)
    // Stats aktualisieren
    const statsResult = await getOptimizationStats()
    stats.value = statsResult.data
  } catch (err) {
    error.value = err.response?.data?.detail || err.message
  } finally {
    analyzing.value = false
  }
}

async function openReportDetail(report) {
  loading.value = true
  error.value = null
  try {
    const result = await getReport(report.id)
    selectedReport.value = result.data
    showReportModal.value = true
  } catch (err) {
    error.value = err.response?.data?.detail || err.message
  } finally {
    loading.value = false
  }
}

async function applyReportRecommendations() {
  if (!selectedReport.value) return

  applying.value = true
  error.value = null
  try {
    await applyRecommendations(selectedReport.value.id)
    // Report in Liste aktualisieren
    const idx = reports.value.findIndex(r => r.id === selectedReport.value.id)
    if (idx >= 0) {
      reports.value[idx].applied_at = new Date().toISOString()
    }
    selectedReport.value.applied_at = new Date().toISOString()
  } catch (err) {
    error.value = err.response?.data?.detail || err.message
  } finally {
    applying.value = false
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

function formatPercent(value) {
  if (value == null) return '-'
  return `${(value * 100).toFixed(1)}%`
}
</script>

<template>
  <div class="space-y-6">
    <!-- Loading -->
    <div
      v-if="loading && !stats"
      class="flex items-center justify-center py-12"
    >
      <span class="text-go4-muted dark:text-gray-400">Laden...</span>
    </div>

    <!-- Error -->
    <div
      v-else-if="error && !stats"
      class="rounded-lg bg-red-50 p-4 text-red-700 dark:bg-red-900/30 dark:text-red-300"
    >
      {{ error }}
    </div>

    <template v-else>
      <!-- Header with Analyze Button -->
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-lg font-semibold text-go4-secondary dark:text-white">
            Optimierung
          </h2>
          <p class="text-sm text-go4-muted dark:text-gray-400">
            KI-gestuetzte Analyse und Empfehlungen fuer deine Pipelines
          </p>
        </div>
        <button
          class="flex items-center gap-2 rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark"
          @click="openAnalyzeModal"
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
              d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
            />
          </svg>
          Neue Analyse
        </button>
      </div>

      <!-- Stats Cards -->
      <div class="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
        <div class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm text-go4-muted dark:text-gray-400">
                Reports gesamt
              </p>
              <p class="mt-1 text-2xl font-semibold text-go4-secondary dark:text-white">
                {{ stats?.total_reports || 0 }}
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
                  d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
            </div>
          </div>
        </div>

        <div class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm text-go4-muted dark:text-gray-400">
                Durchschn. Conversion
              </p>
              <p class="mt-1 text-2xl font-semibold text-go4-secondary dark:text-white">
                {{ formatPercent(stats?.avg_conversion_rate) }}
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
                  d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"
                />
              </svg>
            </div>
          </div>
        </div>

        <div class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm text-go4-muted dark:text-gray-400">
                Empfehlungen
              </p>
              <p class="mt-1 text-2xl font-semibold text-go4-secondary dark:text-white">
                {{ stats?.total_recommendations || 0 }}
              </p>
              <p class="mt-1 text-xs text-go4-muted dark:text-gray-500">
                {{ stats?.applied_recommendations || 0 }} angewendet
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
                  d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                />
              </svg>
            </div>
          </div>
        </div>

        <div class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm text-go4-muted dark:text-gray-400">
                Wichtige Insights
              </p>
              <p class="mt-1 text-2xl font-semibold text-go4-secondary dark:text-white">
                {{ stats?.high_priority_insights || 0 }}
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
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
            </div>
          </div>
        </div>
      </div>

      <!-- Best/Worst Pipelines -->
      <div
        v-if="stats?.best_performing_pipeline || stats?.worst_performing_pipeline"
        class="grid grid-cols-1 gap-6 md:grid-cols-2"
      >
        <div
          v-if="stats?.best_performing_pipeline"
          class="rounded-lg border border-green-200 bg-green-50 p-4 dark:border-green-800/50 dark:bg-green-900/20"
        >
          <div class="flex items-center gap-2">
            <svg
              class="h-5 w-5 text-green-600 dark:text-green-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"
              />
            </svg>
            <span class="text-sm font-medium text-green-700 dark:text-green-300">Beste Pipeline</span>
          </div>
          <p class="mt-2 text-lg font-semibold text-green-800 dark:text-green-200">
            {{ stats.best_performing_pipeline }}
          </p>
        </div>

        <div
          v-if="stats?.worst_performing_pipeline"
          class="rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800/50 dark:bg-red-900/20"
        >
          <div class="flex items-center gap-2">
            <svg
              class="h-5 w-5 text-red-600 dark:text-red-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
            <span class="text-sm font-medium text-red-700 dark:text-red-300">Optimierungsbedarf</span>
          </div>
          <p class="mt-2 text-lg font-semibold text-red-800 dark:text-red-200">
            {{ stats.worst_performing_pipeline }}
          </p>
        </div>
      </div>

      <!-- High Priority Insights -->
      <div class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
        <h3 class="mb-4 font-semibold text-go4-secondary dark:text-white">
          Wichtige Insights
        </h3>

        <EmptyState
          v-if="insights.length === 0"
          title="Keine Insights"
          description="Fuehre eine Analyse durch um Insights zu generieren."
        />

        <div
          v-else
          class="space-y-3"
        >
          <div
            v-for="insight in insights"
            :key="insight.id"
            class="rounded-lg border border-gray-100 p-4 dark:border-gray-700"
          >
            <div class="flex items-start justify-between">
              <div class="flex-1">
                <div class="flex items-center gap-2">
                  <span
                    class="rounded-full px-2 py-0.5 text-xs font-medium"
                    :class="insightTypeColors[insight.insight_type]"
                  >
                    {{ insightTypeLabels[insight.insight_type] }}
                  </span>
                  <span
                    class="rounded-full px-2 py-0.5 text-xs font-medium"
                    :class="priorityColors[insight.priority]"
                  >
                    {{ priorityLabels[insight.priority] }}
                  </span>
                </div>
                <h4 class="mt-2 font-medium text-go4-secondary dark:text-white">
                  {{ insight.title }}
                </h4>
                <p class="mt-1 text-sm text-go4-muted dark:text-gray-400">
                  {{ insight.description }}
                </p>
                <p
                  v-if="insight.suggested_action"
                  class="mt-2 text-sm text-go4-primary"
                >
                  Empfehlung: {{ insight.suggested_action }}
                </p>
              </div>
              <div class="ml-4 text-right text-xs text-go4-muted dark:text-gray-500">
                <span
                  v-if="insight.confidence"
                  class="block"
                >
                  {{ (insight.confidence * 100).toFixed(0) }}% Konfidenz
                </span>
                <span
                  v-if="insight.is_applied"
                  class="mt-1 block text-green-600 dark:text-green-400"
                >
                  Angewendet
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Recent Reports -->
      <div class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
        <h3 class="mb-4 font-semibold text-go4-secondary dark:text-white">
          Letzte Analysen
        </h3>

        <EmptyState
          v-if="reports.length === 0"
          title="Keine Reports"
          description="Starte eine Analyse um Optimierungspotentiale zu identifizieren."
        >
          <button
            class="mt-4 rounded-lg bg-go4-primary px-4 py-2 text-sm text-white hover:bg-go4-primary-dark"
            @click="openAnalyzeModal"
          >
            Erste Analyse starten
          </button>
        </EmptyState>

        <div
          v-else
          class="overflow-hidden rounded-lg border border-gray-100 dark:border-gray-700"
        >
          <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead class="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th class="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-300">
                  Pipeline
                </th>
                <th class="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-300">
                  Typ
                </th>
                <th class="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-300">
                  Conversion
                </th>
                <th class="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-300">
                  Empfehlungen
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
                v-for="report in reports"
                :key="report.id"
                class="hover:bg-gray-50 dark:hover:bg-gray-700/50"
              >
                <td class="whitespace-nowrap px-4 py-3 text-sm font-medium text-go4-secondary dark:text-white">
                  {{ report.pipeline_name || `Pipeline #${report.pipeline_id}` }}
                </td>
                <td class="whitespace-nowrap px-4 py-3 text-sm text-go4-muted dark:text-gray-400">
                  {{ report.report_type }}
                </td>
                <td class="whitespace-nowrap px-4 py-3 text-sm text-go4-secondary dark:text-gray-200">
                  {{ formatPercent(report.conversion_rate) }}
                </td>
                <td class="whitespace-nowrap px-4 py-3 text-sm text-go4-muted dark:text-gray-400">
                  {{ report.recommendations?.length || 0 }}
                </td>
                <td class="whitespace-nowrap px-4 py-3">
                  <span
                    class="rounded-full px-2 py-0.5 text-xs font-medium"
                    :class="statusColors[report.status]"
                  >
                    {{ statusLabels[report.status] }}
                  </span>
                  <span
                    v-if="report.applied_at"
                    class="ml-2 text-xs text-green-600 dark:text-green-400"
                  >
                    Angewendet
                  </span>
                </td>
                <td class="whitespace-nowrap px-4 py-3 text-sm text-go4-muted dark:text-gray-400">
                  {{ formatDate(report.created_at) }}
                </td>
                <td class="whitespace-nowrap px-4 py-3 text-right">
                  <button
                    class="text-sm text-go4-primary hover:text-go4-primary-dark"
                    @click="openReportDetail(report)"
                  >
                    Details
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <!-- Analyze Modal -->
    <div
      v-if="showAnalyzeModal"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      @click.self="showAnalyzeModal = false"
    >
      <div class="mx-4 w-full max-w-md rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800">
        <div class="mb-4 flex items-center justify-between">
          <h3 class="text-lg font-semibold text-go4-secondary dark:text-white">
            Pipeline analysieren
          </h3>
          <button
            class="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700 dark:hover:text-gray-300"
            @click="showAnalyzeModal = false"
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

        <div class="space-y-4">
          <div>
            <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
              Pipeline
            </label>
            <select
              v-model="selectedPipelineId"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            >
              <option
                v-for="pipeline in store.pipelines"
                :key="pipeline.id"
                :value="pipeline.id"
              >
                {{ pipeline.name }}
              </option>
            </select>
          </div>

          <div>
            <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
              Report-Typ
            </label>
            <select
              v-model="analyzeParams.report_type"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            >
              <option value="ad_hoc">
                Ad-hoc
              </option>
              <option value="weekly">
                Woechentlich
              </option>
              <option value="monthly">
                Monatlich
              </option>
            </select>
          </div>

          <div>
            <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
              Analysezeitraum (Tage)
            </label>
            <input
              v-model.number="analyzeParams.days"
              type="number"
              min="7"
              max="365"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            >
          </div>

          <div
            v-if="error"
            class="rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300"
          >
            {{ error }}
          </div>
        </div>

        <div class="mt-6 flex justify-end gap-3">
          <button
            class="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
            @click="showAnalyzeModal = false"
          >
            Abbrechen
          </button>
          <button
            class="flex items-center gap-2 rounded-lg bg-go4-primary px-4 py-2 text-sm text-white hover:bg-go4-primary-dark disabled:opacity-50"
            :disabled="!selectedPipelineId || analyzing"
            @click="runAnalysis"
          >
            <svg
              v-if="analyzing"
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
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            {{ analyzing ? 'Analysiere...' : 'Analyse starten' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Report Detail Modal -->
    <div
      v-if="showReportModal && selectedReport"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      @click.self="showReportModal = false"
    >
      <div class="mx-4 max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800">
        <div class="mb-4 flex items-center justify-between">
          <div>
            <h3 class="text-lg font-semibold text-go4-secondary dark:text-white">
              {{ selectedReport.pipeline_name || `Pipeline #${selectedReport.pipeline_id}` }}
            </h3>
            <p class="text-sm text-go4-muted dark:text-gray-400">
              {{ formatDate(selectedReport.analysis_period_start) }} - {{ formatDate(selectedReport.analysis_period_end) }}
            </p>
          </div>
          <button
            class="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700 dark:hover:text-gray-300"
            @click="showReportModal = false"
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

        <!-- Metrics -->
        <div class="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
          <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-700">
            <p class="text-xs text-go4-muted dark:text-gray-400">
              Enrollments
            </p>
            <p class="text-lg font-semibold text-go4-secondary dark:text-white">
              {{ selectedReport.total_enrollments }}
            </p>
          </div>
          <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-700">
            <p class="text-xs text-go4-muted dark:text-gray-400">
              Erfolgreiche
            </p>
            <p class="text-lg font-semibold text-green-600 dark:text-green-400">
              {{ selectedReport.successful_enrollments }}
            </p>
          </div>
          <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-700">
            <p class="text-xs text-go4-muted dark:text-gray-400">
              Conversion Rate
            </p>
            <p class="text-lg font-semibold text-go4-secondary dark:text-white">
              {{ formatPercent(selectedReport.conversion_rate) }}
            </p>
          </div>
          <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-700">
            <p class="text-xs text-go4-muted dark:text-gray-400">
              Avg. Touches
            </p>
            <p class="text-lg font-semibold text-go4-secondary dark:text-white">
              {{ selectedReport.avg_touches_to_conversion?.toFixed(1) || '-' }}
            </p>
          </div>
        </div>

        <!-- Patterns -->
        <div
          v-if="selectedReport.patterns_found?.length > 0"
          class="mb-6"
        >
          <h4 class="mb-3 font-medium text-go4-secondary dark:text-white">
            Erkannte Muster
          </h4>
          <div class="space-y-2">
            <div
              v-for="(pattern, idx) in selectedReport.patterns_found"
              :key="idx"
              class="rounded-lg border border-gray-100 p-3 dark:border-gray-700"
            >
              <p class="text-sm font-medium text-go4-secondary dark:text-white">
                {{ pattern.type }}
              </p>
              <p class="mt-1 text-sm text-go4-muted dark:text-gray-400">
                {{ pattern.description }}
              </p>
            </div>
          </div>
        </div>

        <!-- Recommendations -->
        <div
          v-if="selectedReport.recommendations?.length > 0"
          class="mb-6"
        >
          <h4 class="mb-3 font-medium text-go4-secondary dark:text-white">
            Empfehlungen
          </h4>
          <div class="space-y-2">
            <div
              v-for="(rec, idx) in selectedReport.recommendations"
              :key="idx"
              class="rounded-lg border border-blue-100 bg-blue-50 p-3 dark:border-blue-800/50 dark:bg-blue-900/20"
            >
              <div class="flex items-start justify-between">
                <p class="text-sm font-medium text-blue-800 dark:text-blue-200">
                  {{ rec.title }}
                </p>
                <span
                  v-if="rec.priority"
                  class="rounded-full px-2 py-0.5 text-xs font-medium"
                  :class="priorityColors[rec.priority]"
                >
                  {{ priorityLabels[rec.priority] }}
                </span>
              </div>
              <p class="mt-1 text-sm text-blue-700 dark:text-blue-300">
                {{ rec.description }}
              </p>
              <p
                v-if="rec.expected_impact"
                class="mt-1 text-xs text-blue-600 dark:text-blue-400"
              >
                Erwarteter Effekt: {{ rec.expected_impact }}
              </p>
            </div>
          </div>
        </div>

        <!-- Insights -->
        <div
          v-if="selectedReport.insights?.length > 0"
          class="mb-6"
        >
          <h4 class="mb-3 font-medium text-go4-secondary dark:text-white">
            Insights ({{ selectedReport.insights_count }})
          </h4>
          <div class="space-y-2">
            <div
              v-for="insight in selectedReport.insights.slice(0, 5)"
              :key="insight.id"
              class="rounded-lg border border-gray-100 p-3 dark:border-gray-700"
            >
              <div class="flex items-center gap-2">
                <span
                  class="rounded-full px-2 py-0.5 text-xs font-medium"
                  :class="insightTypeColors[insight.insight_type]"
                >
                  {{ insightTypeLabels[insight.insight_type] }}
                </span>
                <span class="text-sm font-medium text-go4-secondary dark:text-white">
                  {{ insight.title }}
                </span>
              </div>
              <p class="mt-1 text-sm text-go4-muted dark:text-gray-400">
                {{ insight.description }}
              </p>
            </div>
          </div>
        </div>

        <!-- Error -->
        <div
          v-if="error"
          class="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300"
        >
          {{ error }}
        </div>

        <!-- Actions -->
        <div class="flex justify-end gap-3 border-t border-gray-200 pt-4 dark:border-gray-700">
          <button
            class="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
            @click="showReportModal = false"
          >
            Schliessen
          </button>
          <button
            v-if="selectedReport.recommendations?.length > 0 && !selectedReport.applied_at"
            class="flex items-center gap-2 rounded-lg bg-go4-primary px-4 py-2 text-sm text-white hover:bg-go4-primary-dark disabled:opacity-50"
            :disabled="applying"
            @click="applyReportRecommendations"
          >
            <svg
              v-if="applying"
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
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            {{ applying ? 'Wende an...' : 'Empfehlungen anwenden' }}
          </button>
          <span
            v-else-if="selectedReport.applied_at"
            class="flex items-center gap-2 rounded-lg bg-green-100 px-4 py-2 text-sm text-green-700 dark:bg-green-900/30 dark:text-green-300"
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
                d="M5 13l4 4L19 7"
              />
            </svg>
            Bereits angewendet
          </span>
        </div>
      </div>
    </div>
  </div>
</template>
