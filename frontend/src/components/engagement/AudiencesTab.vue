<script setup>
/**
 * Custom Audiences Tab
 *
 * Manages Meta Custom Audiences for retargeting.
 * Allows creating, syncing, and monitoring audiences.
 */
import { ref, computed, onMounted } from 'vue'
import {
  listAudiences,
  createAudience,
  updateAudience,
  deleteAudience,
  syncAudience,
  getAudienceSyncLogs,
  getMetaStatus
} from '@/api/meta'

// State
const loading = ref(false)
const error = ref(null)
const audiences = ref([])
const syncLogs = ref([])
const metaStatus = ref(null)
const showCreateModal = ref(false)
const showLogsModal = ref(false)
const syncingAudienceId = ref(null)

// Form state
const form = ref({
  name: '',
  description: '',
  pipeline_id: null,
  segment_filter: {
    stages: [],
    statuses: ['active'],
    tags: []
  },
  sync_mode: 'manual',
  create_in_meta: true
})

// Computed
const hasMetaIntegration = computed(() => metaStatus.value?.is_configured)
const hasAdAccount = computed(() => metaStatus.value?.pixel_id) // Simplified check

// Stage options for filter
const stageOptions = [
  { value: 'lead', label: 'Lead' },
  { value: 'contacted', label: 'Kontaktiert' },
  { value: 'engaged', label: 'Engagiert' },
  { value: 'qualified', label: 'Qualifiziert' },
  { value: 'converted', label: 'Konvertiert' }
]

const syncModeOptions = [
  { value: 'manual', label: 'Manuell' },
  { value: 'daily', label: 'Täglich' },
  { value: 'realtime', label: 'Echtzeit' }
]

// Methods
async function loadData() {
  loading.value = true
  error.value = null
  try {
    const [statusRes, audiencesRes] = await Promise.all([
      getMetaStatus(),
      listAudiences()
    ])
    metaStatus.value = statusRes.data
    audiences.value = audiencesRes.data.items || []
  } catch (err) {
    error.value = err.response?.data?.detail || err.message
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  if (!form.value.name.trim()) {
    error.value = 'Name ist erforderlich'
    return
  }

  loading.value = true
  error.value = null
  try {
    await createAudience(form.value)
    showCreateModal.value = false
    resetForm()
    await loadData()
  } catch (err) {
    error.value = err.response?.data?.detail || err.message
  } finally {
    loading.value = false
  }
}

async function handleSync(audienceId) {
  syncingAudienceId.value = audienceId
  error.value = null
  try {
    await syncAudience(audienceId)
    await loadData()
  } catch (err) {
    error.value = err.response?.data?.detail || err.message
  } finally {
    syncingAudienceId.value = null
  }
}

async function handleDelete(audience) {
  if (!confirm(`Audience "${audience.name}" wirklich löschen?`)) return

  loading.value = true
  error.value = null
  try {
    await deleteAudience(audience.id, false)
    await loadData()
  } catch (err) {
    error.value = err.response?.data?.detail || err.message
  } finally {
    loading.value = false
  }
}

async function handleToggleActive(audience) {
  try {
    await updateAudience(audience.id, { is_active: !audience.is_active })
    await loadData()
  } catch (err) {
    error.value = err.response?.data?.detail || err.message
  }
}

async function loadSyncLogs(audienceId = null) {
  try {
    const res = await getAudienceSyncLogs({ audience_id: audienceId, limit: 20 })
    syncLogs.value = res.data.items || []
    showLogsModal.value = true
  } catch (err) {
    error.value = err.response?.data?.detail || err.message
  }
}

function resetForm() {
  form.value = {
    name: '',
    description: '',
    pipeline_id: null,
    segment_filter: {
      stages: [],
      statuses: ['active'],
      tags: []
    },
    sync_mode: 'manual',
    create_in_meta: true
  }
}

function formatDate(date) {
  if (!date) return '-'
  return new Date(date).toLocaleString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function getSyncStatusColor(status) {
  const colors = {
    success: 'text-green-600 bg-green-50',
    partial: 'text-yellow-600 bg-yellow-50',
    failed: 'text-red-600 bg-red-50',
    pending: 'text-gray-600 bg-gray-50'
  }
  return colors[status] || colors.pending
}

// Lifecycle
onMounted(() => {
  loadData()
})
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-lg font-semibold text-gray-900">
          Custom Audiences
        </h2>
        <p class="text-sm text-gray-500">
          Synchronisiere Contact-Segmente zu Meta für Retargeting
        </p>
      </div>
      <div class="flex gap-2">
        <button
          class="px-3 py-2 text-sm text-gray-600 hover:text-gray-900"
          @click="loadSyncLogs()"
        >
          Sync-Logs
        </button>
        <button
          class="px-4 py-2 bg-go4-primary text-white rounded-lg hover:bg-go4-primary/90 disabled:opacity-50"
          :disabled="!hasMetaIntegration"
          @click="showCreateModal = true"
        >
          + Neue Audience
        </button>
      </div>
    </div>

    <!-- No Integration Warning -->
    <div
      v-if="!loading && !hasMetaIntegration"
      class="rounded-lg bg-yellow-50 border border-yellow-200 p-4"
    >
      <p class="text-yellow-800">
        Meta Integration nicht konfiguriert. Bitte zuerst im "Meta CAPI" Tab einrichten.
      </p>
    </div>

    <!-- Error -->
    <div
      v-if="error"
      class="rounded-lg bg-red-50 border border-red-200 p-4 text-red-700"
    >
      {{ error }}
    </div>

    <!-- Loading -->
    <div
      v-if="loading"
      class="text-center py-12 text-gray-500"
    >
      Laden...
    </div>

    <!-- Empty State -->
    <div
      v-else-if="audiences.length === 0 && hasMetaIntegration"
      class="text-center py-12"
    >
      <div class="text-gray-400 mb-4">
        <svg
          class="mx-auto h-12 w-12"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
          />
        </svg>
      </div>
      <p class="text-gray-500">
        Noch keine Custom Audiences erstellt
      </p>
      <button
        class="mt-4 px-4 py-2 bg-go4-primary text-white rounded-lg hover:bg-go4-primary/90"
        @click="showCreateModal = true"
      >
        Erste Audience erstellen
      </button>
    </div>

    <!-- Audiences List -->
    <div
      v-else
      class="space-y-4"
    >
      <div
        v-for="audience in audiences"
        :key="audience.id"
        class="bg-white rounded-lg border border-gray-200 p-4"
      >
        <div class="flex items-start justify-between">
          <div class="flex-1">
            <div class="flex items-center gap-3">
              <h3 class="font-medium text-gray-900">
                {{ audience.name }}
              </h3>
              <span
                v-if="audience.is_active"
                class="px-2 py-0.5 text-xs rounded-full bg-green-100 text-green-700"
              >
                Aktiv
              </span>
              <span
                v-else
                class="px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-500"
              >
                Inaktiv
              </span>
            </div>
            <p
              v-if="audience.description"
              class="text-sm text-gray-500 mt-1"
            >
              {{ audience.description }}
            </p>
            <div class="flex items-center gap-4 mt-2 text-sm text-gray-500">
              <span v-if="audience.pipeline_name">
                Pipeline: {{ audience.pipeline_name }}
              </span>
              <span>
                Sync: {{ audience.sync_mode }}
              </span>
              <span>
                Kontakte: {{ audience.audience_size.toLocaleString() }}
              </span>
            </div>
          </div>

          <div class="flex items-center gap-2">
            <!-- Sync Status -->
            <span
              v-if="audience.last_sync_status"
              :class="['px-2 py-1 text-xs rounded', getSyncStatusColor(audience.last_sync_status)]"
            >
              {{ audience.last_sync_status }}
            </span>

            <!-- Actions -->
            <button
              class="p-2 text-gray-400 hover:text-go4-primary disabled:opacity-50"
              :disabled="syncingAudienceId === audience.id"
              title="Jetzt synchronisieren"
              @click="handleSync(audience.id)"
            >
              <svg
                class="w-5 h-5"
                :class="{ 'animate-spin': syncingAudienceId === audience.id }"
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
            </button>
            <button
              class="p-2 text-gray-400 hover:text-gray-600"
              title="Logs anzeigen"
              @click="loadSyncLogs(audience.id)"
            >
              <svg
                class="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                />
              </svg>
            </button>
            <button
              class="p-2 text-gray-400 hover:text-gray-600"
              :title="audience.is_active ? 'Deaktivieren' : 'Aktivieren'"
              @click="handleToggleActive(audience)"
            >
              <svg
                v-if="audience.is_active"
                class="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"
                />
              </svg>
              <svg
                v-else
                class="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </button>
            <button
              class="p-2 text-gray-400 hover:text-red-500"
              title="Löschen"
              @click="handleDelete(audience)"
            >
              <svg
                class="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
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

        <!-- Last Sync Info -->
        <div
          v-if="audience.last_sync_at"
          class="mt-3 pt-3 border-t border-gray-100 text-xs text-gray-400"
        >
          Letzter Sync: {{ formatDate(audience.last_sync_at) }} ({{ audience.last_sync_count }} Kontakte)
        </div>
      </div>
    </div>

    <!-- Create Modal -->
    <div
      v-if="showCreateModal"
      class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      @click.self="showCreateModal = false"
    >
      <div class="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 p-6">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">
          Neue Custom Audience
        </h3>

        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Name *</label>
            <input
              v-model="form.name"
              type="text"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-go4-primary focus:border-transparent"
              placeholder="z.B. Solar Leads - Engagiert"
            >
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Beschreibung</label>
            <textarea
              v-model="form.description"
              rows="2"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-go4-primary focus:border-transparent"
              placeholder="Optionale Beschreibung"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Pipeline-Stages</label>
            <div class="flex flex-wrap gap-2">
              <label
                v-for="option in stageOptions"
                :key="option.value"
                class="flex items-center gap-2 px-3 py-1.5 border rounded-lg cursor-pointer hover:bg-gray-50"
                :class="form.segment_filter.stages.includes(option.value) ? 'border-go4-primary bg-go4-primary/5' : 'border-gray-200'"
              >
                <input
                  v-model="form.segment_filter.stages"
                  type="checkbox"
                  :value="option.value"
                  class="sr-only"
                >
                <span class="text-sm">{{ option.label }}</span>
              </label>
            </div>
            <p class="text-xs text-gray-500 mt-1">
              Leer = alle Stages
            </p>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Sync-Modus</label>
            <select
              v-model="form.sync_mode"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-go4-primary focus:border-transparent"
            >
              <option
                v-for="option in syncModeOptions"
                :key="option.value"
                :value="option.value"
              >
                {{ option.label }}
              </option>
            </select>
          </div>

          <div class="flex items-center gap-2">
            <input
              id="createInMeta"
              v-model="form.create_in_meta"
              type="checkbox"
              class="rounded border-gray-300 text-go4-primary focus:ring-go4-primary"
            >
            <label
              for="createInMeta"
              class="text-sm text-gray-700"
            >
              Direkt in Meta erstellen
            </label>
          </div>
        </div>

        <div class="flex justify-end gap-3 mt-6">
          <button
            class="px-4 py-2 text-gray-600 hover:text-gray-800"
            @click="showCreateModal = false; resetForm()"
          >
            Abbrechen
          </button>
          <button
            class="px-4 py-2 bg-go4-primary text-white rounded-lg hover:bg-go4-primary/90 disabled:opacity-50"
            :disabled="loading || !form.name.trim()"
            @click="handleCreate"
          >
            Erstellen
          </button>
        </div>
      </div>
    </div>

    <!-- Logs Modal -->
    <div
      v-if="showLogsModal"
      class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      @click.self="showLogsModal = false"
    >
      <div class="bg-white rounded-xl shadow-xl w-full max-w-2xl mx-4 p-6 max-h-[80vh] overflow-hidden flex flex-col">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold text-gray-900">
            Sync-Logs
          </h3>
          <button
            class="text-gray-400 hover:text-gray-600"
            @click="showLogsModal = false"
          >
            <svg
              class="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
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

        <div class="overflow-auto flex-1">
          <table class="w-full text-sm">
            <thead class="bg-gray-50 sticky top-0">
              <tr>
                <th class="text-left px-3 py-2 font-medium text-gray-500">
                  Audience
                </th>
                <th class="text-left px-3 py-2 font-medium text-gray-500">
                  Datum
                </th>
                <th class="text-left px-3 py-2 font-medium text-gray-500">
                  Kontakte
                </th>
                <th class="text-left px-3 py-2 font-medium text-gray-500">
                  Status
                </th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              <tr
                v-for="log in syncLogs"
                :key="log.id"
              >
                <td class="px-3 py-2">
                  {{ log.audience_name }}
                </td>
                <td class="px-3 py-2">
                  {{ formatDate(log.started_at) }}
                </td>
                <td class="px-3 py-2">
                  {{ log.contacts_added }} / {{ log.contacts_processed }}
                </td>
                <td class="px-3 py-2">
                  <span :class="['px-2 py-0.5 text-xs rounded', getSyncStatusColor(log.status)]">
                    {{ log.status }}
                  </span>
                </td>
              </tr>
              <tr v-if="syncLogs.length === 0">
                <td
                  colspan="4"
                  class="px-3 py-8 text-center text-gray-400"
                >
                  Keine Sync-Logs vorhanden
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>
