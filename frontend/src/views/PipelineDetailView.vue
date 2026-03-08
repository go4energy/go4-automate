<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useEngagementStore } from '@/stores/engagement'
import { getContacts } from '@/api/contacts'
import PageHeader from '@/components/ui/PageHeader.vue'
import Breadcrumb from '@/components/ui/Breadcrumb.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'

const props = defineProps({
  id: { type: [String, Number], default: null }
})

const route = useRoute()
const router = useRouter()
const store = useEngagementStore()

const pipelineId = computed(() => props.id || route.params.id)

const loading = ref(false)
const error = ref(null)
const activeTab = ref('overview')
const showDeleteDialog = ref(false)

// Enrollment modal state
const showEnrollModal = ref(false)
const enrollSearch = ref('')
const enrollLoading = ref(false)
const enrollError = ref(null)
const searchResults = ref([])
const selectedContacts = ref([])
const enrolling = ref(false)
const enrollSuccess = ref(null)

const tabs = [
  { id: 'overview', label: 'Uebersicht' },
  { id: 'enrollments', label: 'Enrollments' },
  { id: 'funnel', label: 'Funnel' }
]

const stageColors = {
  lead: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
  contacted: 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300',
  engaged: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300',
  qualified: 'bg-purple-100 text-purple-700 dark:bg-purple-900/50 dark:text-purple-300',
  converted: 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300',
  lost: 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300'
}

const stageLabels = {
  lead: 'Lead',
  contacted: 'Kontaktiert',
  engaged: 'Engagiert',
  qualified: 'Qualifiziert',
  converted: 'Konvertiert',
  lost: 'Verloren'
}

const statusColors = {
  active: 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300',
  paused: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-300',
  completed: 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300',
  stopped: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
}

const statusLabels = {
  active: 'Aktiv',
  paused: 'Pausiert',
  completed: 'Abgeschlossen',
  stopped: 'Gestoppt'
}

const channelLabels = {
  linkedin: 'LinkedIn',
  email: 'Email',
  phone: 'Telefon',
  postmail: 'Brief',
  whatsapp: 'WhatsApp'
}

const pipeline = computed(() => store.currentPipeline)
const stats = computed(() => store.pipelineStats)
const funnel = computed(() => store.pipelineFunnel)

const pipelineEnrollments = computed(() =>
  store.enrollments.filter((e) => e.pipeline_id === parseInt(pipelineId.value))
)

// Already enrolled contact IDs for filtering search results
const enrolledContactIds = computed(() =>
  new Set(pipelineEnrollments.value.map((e) => e.contact_id))
)

onMounted(async () => {
  loading.value = true
  try {
    await Promise.all([
      store.fetchPipeline(pipelineId.value),
      store.fetchPipelineStats(pipelineId.value),
      store.fetchPipelineFunnel(pipelineId.value),
      store.fetchEnrollments({ pipeline_id: pipelineId.value })
    ])
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
})

function goBack() {
  router.push('/engagement/pipelines')
}

function goToEdit() {
  router.push(`/engagement/pipelines/${pipelineId.value}/edit`)
}

function confirmDelete() {
  showDeleteDialog.value = true
}

async function deletePipeline() {
  try {
    await store.removePipeline(pipelineId.value)
    router.push('/engagement/pipelines')
  } catch {
    // Error handled in store
  }
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric'
  })
}

function goToContact(enrollment) {
  router.push(`/contacts/${enrollment.contact_id}`)
}

// ============== Enrollment Modal ==============

function openEnrollModal() {
  showEnrollModal.value = true
  enrollSearch.value = ''
  searchResults.value = []
  selectedContacts.value = []
  enrollError.value = null
  enrollSuccess.value = null
}

function closeEnrollModal() {
  showEnrollModal.value = false
}

let searchTimeout = null
function onSearchInput() {
  clearTimeout(searchTimeout)
  if (enrollSearch.value.length < 2) {
    searchResults.value = []
    return
  }
  searchTimeout = setTimeout(searchContacts, 300)
}

async function searchContacts() {
  enrollLoading.value = true
  enrollError.value = null
  try {
    const { data } = await getContacts({ search: enrollSearch.value, limit: 20 })
    // Filter out already enrolled contacts
    searchResults.value = data.filter((c) => !enrolledContactIds.value.has(c.id))
  } catch (err) {
    enrollError.value = err.response?.data?.detail || err.message
  } finally {
    enrollLoading.value = false
  }
}

function toggleContactSelection(contact) {
  const idx = selectedContacts.value.findIndex((c) => c.id === contact.id)
  if (idx !== -1) {
    selectedContacts.value.splice(idx, 1)
  } else {
    selectedContacts.value.push(contact)
  }
}

function isSelected(contactId) {
  return selectedContacts.value.some((c) => c.id === contactId)
}

async function enrollSelected() {
  if (!selectedContacts.value.length) return

  enrolling.value = true
  enrollError.value = null
  enrollSuccess.value = null
  try {
    const contactIds = selectedContacts.value.map((c) => c.id)
    await store.bulkEnroll({
      pipeline_id: parseInt(pipelineId.value),
      contact_ids: contactIds,
      source_module: 'manual'
    })

    enrollSuccess.value = `${contactIds.length} Kontakt(e) hinzugefuegt`

    // Refresh enrollments
    await store.fetchEnrollments({ pipeline_id: pipelineId.value })
    await store.fetchPipelineStats(pipelineId.value)
    await store.fetchPipelineFunnel(pipelineId.value)

    // Reset selection
    selectedContacts.value = []
    searchResults.value = []
    enrollSearch.value = ''
  } catch (err) {
    enrollError.value = err.response?.data?.detail || err.message
  } finally {
    enrolling.value = false
  }
}
</script>

<template>
  <div class="flex flex-1 flex-col overflow-hidden">
    <PageHeader
      :title="pipeline?.name || 'Pipeline'"
      :subtitle="pipeline?.product_name"
    >
      <template #actions>
        <button
          class="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
          @click="goBack"
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
              d="M10 19l-7-7m0 0l7-7m-7 7h18"
            />
          </svg>
          Zurueck
        </button>
        <button
          class="inline-flex items-center gap-2 rounded-lg bg-go4-primary px-3 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark"
          @click="goToEdit"
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
          Bearbeiten
        </button>
        <button
          class="inline-flex items-center gap-2 rounded-lg border border-red-300 px-3 py-2 text-sm font-medium text-red-700 hover:bg-red-50 dark:border-red-700 dark:text-red-400 dark:hover:bg-red-900/20"
          @click="confirmDelete"
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
          Loeschen
        </button>
      </template>
    </PageHeader>

    <Breadcrumb class="mx-4 mb-2" />

    <!-- Tabs -->
    <div class="border-b border-gray-200 px-4 dark:border-gray-700">
      <nav class="-mb-px flex gap-6">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="border-b-2 pb-3 text-sm font-medium transition-colors"
          :class="
            activeTab === tab.id
              ? 'border-go4-primary text-go4-primary'
              : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          "
          @click="activeTab = tab.id"
        >
          {{ tab.label }}
        </button>
      </nav>
    </div>

    <!-- Content -->
    <div class="flex-1 overflow-auto p-4">
      <!-- Loading -->
      <div
        v-if="loading"
        class="flex items-center justify-center py-12"
      >
        <svg
          class="h-8 w-8 animate-spin text-go4-primary"
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
      </div>

      <!-- Error -->
      <div
        v-else-if="error"
        class="mx-auto max-w-lg rounded-lg bg-red-50 p-4 text-red-700 dark:bg-red-900/50 dark:text-red-300"
      >
        {{ error }}
      </div>

      <!-- Overview Tab -->
      <template v-else-if="activeTab === 'overview' && pipeline">
        <div class="space-y-6">
          <!-- Stats Cards -->
          <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div class="rounded-lg bg-white p-4 shadow dark:bg-gray-800">
              <div class="text-sm text-gray-500 dark:text-gray-400">
                Enrollments
              </div>
              <div class="mt-1 text-2xl font-bold text-gray-900 dark:text-white">
                {{ stats?.total_enrollments || 0 }}
              </div>
              <div class="mt-1 text-sm text-gray-500">
                {{ stats?.active_enrollments || 0 }} aktiv
              </div>
            </div>

            <div class="rounded-lg bg-white p-4 shadow dark:bg-gray-800">
              <div class="text-sm text-gray-500 dark:text-gray-400">
                Conversion
              </div>
              <div class="mt-1 text-2xl font-bold text-go4-primary">
                {{ stats?.conversion_rate || 0 }}%
              </div>
              <div class="mt-1 text-sm text-gray-500">
                {{ stats?.converted_count || 0 }} konvertiert
              </div>
            </div>

            <div class="rounded-lg bg-white p-4 shadow dark:bg-gray-800">
              <div class="text-sm text-gray-500 dark:text-gray-400">
                Durchschn. Touches
              </div>
              <div class="mt-1 text-2xl font-bold text-gray-900 dark:text-white">
                {{ stats?.avg_touch_count?.toFixed(1) || 0 }}
              </div>
              <div class="mt-1 text-sm text-gray-500">
                pro Enrollment
              </div>
            </div>

            <div class="rounded-lg bg-white p-4 shadow dark:bg-gray-800">
              <div class="text-sm text-gray-500 dark:text-gray-400">
                Ausstehend
              </div>
              <div class="mt-1 text-2xl font-bold text-yellow-600 dark:text-yellow-400">
                {{ stats?.pending_actions || 0 }}
              </div>
              <div class="mt-1 text-sm text-gray-500">
                Aktionen zur Freigabe
              </div>
            </div>
          </div>

          <!-- Pipeline Info -->
          <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <div class="rounded-lg bg-white p-6 shadow dark:bg-gray-800">
              <h3 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">
                Details
              </h3>
              <dl class="space-y-3">
                <div class="flex justify-between">
                  <dt class="text-sm text-gray-500 dark:text-gray-400">
                    Status
                  </dt>
                  <dd>
                    <span
                      class="rounded-full px-2 py-0.5 text-xs font-medium"
                      :class="pipeline.is_active ? 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300' : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'"
                    >
                      {{ pipeline.is_active ? 'Aktiv' : 'Inaktiv' }}
                    </span>
                  </dd>
                </div>
                <div class="flex justify-between">
                  <dt class="text-sm text-gray-500 dark:text-gray-400">
                    Slug
                  </dt>
                  <dd class="text-sm font-mono text-gray-900 dark:text-white">
                    {{ pipeline.slug }}
                  </dd>
                </div>
                <div class="flex justify-between">
                  <dt class="text-sm text-gray-500 dark:text-gray-400">
                    Ziel
                  </dt>
                  <dd class="text-sm text-gray-900 dark:text-white">
                    {{ pipeline.goal || '-' }}
                  </dd>
                </div>
                <div class="flex justify-between">
                  <dt class="text-sm text-gray-500 dark:text-gray-400">
                    Tonalitaet
                  </dt>
                  <dd class="text-sm text-gray-900 dark:text-white">
                    {{ pipeline.tone_of_voice || '-' }}
                  </dd>
                </div>
                <div class="flex justify-between">
                  <dt class="text-sm text-gray-500 dark:text-gray-400">
                    Min. Tage zwischen Touches
                  </dt>
                  <dd class="text-sm text-gray-900 dark:text-white">
                    {{ pipeline.min_days_between_touches }}
                  </dd>
                </div>
                <div class="flex justify-between">
                  <dt class="text-sm text-gray-500 dark:text-gray-400">
                    Erstellt
                  </dt>
                  <dd class="text-sm text-gray-900 dark:text-white">
                    {{ formatDate(pipeline.created_at) }}
                  </dd>
                </div>
              </dl>
            </div>

            <div class="space-y-6">
              <!-- Channels -->
              <div class="rounded-lg bg-white p-6 shadow dark:bg-gray-800">
                <h3 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">
                  Kanaele
                </h3>
                <div class="flex flex-wrap gap-2">
                  <span
                    v-for="channel in pipeline.channels"
                    :key="channel"
                    class="rounded-lg bg-go4-primary/10 px-3 py-1.5 text-sm font-medium text-go4-primary"
                  >
                    {{ channelLabels[channel] || channel }}
                  </span>
                </div>
              </div>

              <!-- Target Audience -->
              <div
                v-if="pipeline.target_audience"
                class="rounded-lg bg-white p-6 shadow dark:bg-gray-800"
              >
                <h3 class="mb-2 text-lg font-semibold text-gray-900 dark:text-white">
                  Zielgruppe
                </h3>
                <p class="text-sm text-gray-600 dark:text-gray-300">
                  {{ pipeline.target_audience }}
                </p>
              </div>
            </div>
          </div>

          <!-- Product Description -->
          <div
            v-if="pipeline.product_description"
            class="rounded-lg bg-white p-6 shadow dark:bg-gray-800"
          >
            <h3 class="mb-2 text-lg font-semibold text-gray-900 dark:text-white">
              Produktbeschreibung
            </h3>
            <p class="text-sm text-gray-600 dark:text-gray-300 whitespace-pre-wrap">
              {{ pipeline.product_description }}
            </p>
          </div>

          <!-- Playbook -->
          <div
            v-if="pipeline.playbook"
            class="rounded-lg bg-white p-6 shadow dark:bg-gray-800"
          >
            <h3 class="mb-2 text-lg font-semibold text-gray-900 dark:text-white">
              Playbook
            </h3>
            <pre class="text-sm text-gray-600 dark:text-gray-300 whitespace-pre-wrap font-mono">{{ pipeline.playbook }}</pre>
          </div>
        </div>
      </template>

      <!-- Enrollments Tab -->
      <template v-else-if="activeTab === 'enrollments'">
        <!-- Add Contacts Button -->
        <div class="mb-4 flex justify-end">
          <button
            class="inline-flex items-center gap-2 rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark"
            @click="openEnrollModal"
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
                d="M12 6v6m0 0v6m0-6h6m-6 0H6"
              />
            </svg>
            Kontakte hinzufuegen
          </button>
        </div>

        <div
          v-if="pipelineEnrollments.length"
          class="overflow-x-auto rounded-lg bg-white shadow dark:bg-gray-800"
        >
          <table class="w-full">
            <thead class="border-b border-gray-200 dark:border-gray-700">
              <tr>
                <th class="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                  Kontakt
                </th>
                <th class="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                  Stage
                </th>
                <th class="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                  Status
                </th>
                <th class="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                  Touches
                </th>
                <th class="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                  Letzter Kontakt
                </th>
                <th class="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                  Enrolled
                </th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
              <tr
                v-for="enrollment in pipelineEnrollments"
                :key="enrollment.id"
                class="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700"
                @click="goToContact(enrollment)"
              >
                <td class="px-4 py-3">
                  <div class="font-medium text-gray-900 dark:text-white">
                    {{ enrollment.contact_name }}
                  </div>
                  <div class="text-xs text-gray-500">
                    {{ enrollment.contact_email }}
                  </div>
                </td>
                <td class="px-4 py-3">
                  <span
                    class="rounded-full px-2 py-0.5 text-xs font-medium"
                    :class="stageColors[enrollment.stage]"
                  >
                    {{ stageLabels[enrollment.stage] || enrollment.stage }}
                  </span>
                </td>
                <td class="px-4 py-3">
                  <span
                    class="rounded-full px-2 py-0.5 text-xs font-medium"
                    :class="statusColors[enrollment.status]"
                  >
                    {{ statusLabels[enrollment.status] || enrollment.status }}
                  </span>
                </td>
                <td class="px-4 py-3 text-sm text-gray-900 dark:text-white">
                  {{ enrollment.touch_count }}
                </td>
                <td class="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                  {{ formatDate(enrollment.last_touch_at) }}
                </td>
                <td class="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                  {{ formatDate(enrollment.enrolled_at) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <EmptyState
          v-else
          title="Keine Enrollments"
          description="Es sind noch keine Kontakte in dieser Pipeline eingeschrieben."
        >
          <template #action>
            <button
              class="mt-4 inline-flex items-center gap-2 rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark"
              @click="openEnrollModal"
            >
              Kontakte hinzufuegen
            </button>
          </template>
        </EmptyState>
      </template>

      <!-- Funnel Tab -->
      <template v-else-if="activeTab === 'funnel'">
        <div
          v-if="funnel?.stages?.length"
          class="mx-auto max-w-2xl space-y-4"
        >
          <div
            v-for="(stage, index) in funnel.stages"
            :key="stage.stage"
            class="relative"
          >
            <div
              class="rounded-lg bg-white p-4 shadow dark:bg-gray-800"
              :style="{ width: `${100 - index * 10}%`, marginLeft: `${index * 5}%` }"
            >
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                  <span
                    class="rounded-full px-3 py-1 text-sm font-medium"
                    :class="stageColors[stage.stage]"
                  >
                    {{ stageLabels[stage.stage] || stage.stage }}
                  </span>
                </div>
                <div class="text-right">
                  <div class="text-2xl font-bold text-gray-900 dark:text-white">
                    {{ stage.count }}
                  </div>
                  <div
                    v-if="stage.percentage"
                    class="text-sm text-gray-500"
                  >
                    {{ stage.percentage }}%
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <EmptyState
          v-else
          title="Keine Funnel-Daten"
          description="Es sind noch keine Enrollments vorhanden, um den Funnel darzustellen."
        />
      </template>
    </div>

    <!-- Delete Confirm Dialog -->
    <ConfirmDialog
      :show="showDeleteDialog"
      title="Pipeline loeschen?"
      :message="`Sind Sie sicher, dass Sie die Pipeline '${pipeline?.name}' loeschen moechten? Alle Enrollments werden ebenfalls geloescht.`"
      confirm-label="Loeschen"
      @confirm="deletePipeline"
      @cancel="showDeleteDialog = false"
    />

    <!-- Enrollment Modal -->
    <div
      v-if="showEnrollModal"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      @click.self="closeEnrollModal"
    >
      <div class="mx-4 w-full max-w-lg rounded-xl bg-white shadow-2xl dark:bg-gray-800">
        <!-- Header -->
        <div class="flex items-center justify-between border-b border-gray-200 px-6 py-4 dark:border-gray-700">
          <h3 class="text-lg font-semibold text-gray-900 dark:text-white">
            Kontakte hinzufuegen
          </h3>
          <button
            class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            @click="closeEnrollModal"
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

        <!-- Body -->
        <div class="px-6 py-4">
          <!-- Search -->
          <div class="relative">
            <svg
              class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
            <input
              v-model="enrollSearch"
              type="text"
              placeholder="Kontakt suchen (Name oder Email)..."
              class="w-full rounded-lg border border-gray-300 bg-white py-2.5 pl-10 pr-4 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              @input="onSearchInput"
            />
          </div>

          <!-- Selected count -->
          <div
            v-if="selectedContacts.length"
            class="mt-3 flex flex-wrap gap-2"
          >
            <span
              v-for="contact in selectedContacts"
              :key="contact.id"
              class="inline-flex items-center gap-1 rounded-full bg-go4-primary/10 px-3 py-1 text-xs font-medium text-go4-primary"
            >
              {{ contact.name }}
              <button
                class="ml-1 hover:text-go4-primary-dark"
                @click="toggleContactSelection(contact)"
              >
                <svg
                  class="h-3 w-3"
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
            </span>
          </div>

          <!-- Loading -->
          <div
            v-if="enrollLoading"
            class="flex items-center justify-center py-8"
          >
            <svg
              class="h-6 w-6 animate-spin text-go4-primary"
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
          </div>

          <!-- Results -->
          <div
            v-else-if="searchResults.length"
            class="mt-3 max-h-64 overflow-y-auto rounded-lg border border-gray-200 dark:border-gray-700"
          >
            <button
              v-for="contact in searchResults"
              :key="contact.id"
              class="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-gray-50 dark:hover:bg-gray-700"
              :class="isSelected(contact.id) ? 'bg-go4-primary/5' : ''"
              @click="toggleContactSelection(contact)"
            >
              <div
                class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-medium"
                :class="isSelected(contact.id) ? 'bg-go4-primary text-white' : 'bg-gray-200 text-gray-600 dark:bg-gray-600 dark:text-gray-300'"
              >
                <svg
                  v-if="isSelected(contact.id)"
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
                <span v-else>{{ contact.name?.charAt(0)?.toUpperCase() }}</span>
              </div>
              <div class="min-w-0 flex-1">
                <div class="truncate text-sm font-medium text-gray-900 dark:text-white">
                  {{ contact.name }}
                </div>
                <div class="truncate text-xs text-gray-500">
                  {{ contact.email }}
                  <span v-if="contact.position"> - {{ contact.position }}</span>
                </div>
              </div>
              <div
                v-if="contact.source"
                class="shrink-0 rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500 dark:bg-gray-700 dark:text-gray-400"
              >
                {{ contact.source }}
              </div>
            </button>
          </div>

          <!-- No results -->
          <div
            v-else-if="enrollSearch.length >= 2 && !enrollLoading"
            class="py-8 text-center text-sm text-gray-500"
          >
            Keine Kontakte gefunden
          </div>

          <!-- Hint -->
          <div
            v-else-if="!enrollSearch"
            class="py-8 text-center text-sm text-gray-500"
          >
            Suche nach Kontakten, um sie dieser Pipeline hinzuzufuegen
          </div>

          <!-- Error -->
          <div
            v-if="enrollError"
            class="mt-3 rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300"
          >
            {{ enrollError }}
          </div>

          <!-- Success -->
          <div
            v-if="enrollSuccess"
            class="mt-3 rounded-lg bg-green-50 p-3 text-sm text-green-700 dark:bg-green-900/30 dark:text-green-300"
          >
            {{ enrollSuccess }}
          </div>
        </div>

        <!-- Footer -->
        <div class="flex items-center justify-end gap-3 border-t border-gray-200 px-6 py-4 dark:border-gray-700">
          <button
            class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
            @click="closeEnrollModal"
          >
            Schliessen
          </button>
          <button
            class="inline-flex items-center gap-2 rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="!selectedContacts.length || enrolling"
            @click="enrollSelected"
          >
            <svg
              v-if="enrolling"
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
            {{ selectedContacts.length }} Kontakt(e) hinzufuegen
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
