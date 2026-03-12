<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useLinkedInStore } from '@/stores/linkedin'
import { useFunnelsStore } from '@/stores/funnels'
import PageHeader from '@/components/ui/PageHeader.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import DataTable from '@/components/ui/DataTable.vue'

const props = defineProps({
  id: { type: [String, Number], default: null }
})

const route = useRoute()
const router = useRouter()
const store = useLinkedInStore()
const funnelsStore = useFunnelsStore()

const jobId = computed(() => {
  // route.params.id is the most reliable source (works on refresh too)
  const raw = route.params.id || props.id
  if (!raw) return null
  const num = parseInt(raw, 10)
  return Number.isNaN(num) ? null : num
})
const job = computed(() => store.currentJob)
const contacts = computed(() => store.jobContacts)
const logs = computed(() => store.jobLogs)

const loading = ref(false)
const error = ref(null)
const showImportModal = ref(false)
const showAddUrlsModal = ref(false)
const showDeleteConfirm = ref(false)
const showLogsModal = ref(false)
const importLoading = ref(false)
const urlsLoading = ref(false)
const logsLoading = ref(false)
const pollInterval = ref(null)

const importForm = ref({
  funnel_id: null,
  stage_id: null,
  skip_duplicates: true,
  create_companies: true
})

const urlsForm = ref({
  urls_text: ''
})

const selectedFunnel = computed(() =>
  funnelsStore.funnels.find((f) => f.id === importForm.value.funnel_id)
)

const statusColors = {
  draft: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
  queued: 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300',
  running: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300',
  paused: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-300',
  completed: 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300',
  failed: 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300',
  cancelled: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
  scraped: 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300',
  imported: 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300',
  skipped: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
}

const statusLabels = {
  draft: 'Entwurf',
  queued: 'In Warteschlange',
  running: 'Laeuft',
  paused: 'Pausiert',
  completed: 'Abgeschlossen',
  failed: 'Fehlgeschlagen',
  cancelled: 'Abgebrochen',
  scraped: 'Gescraped',
  imported: 'Importiert',
  skipped: 'Uebersprungen'
}

const contactColumns = [
  { key: 'name', label: 'Name' },
  { key: 'position', label: 'Position' },
  { key: 'company_name', label: 'Unternehmen' },
  { key: 'status', label: 'Status' },
  { key: 'linkedin_url', label: 'LinkedIn' }
]

const scrapedContacts = computed(() => contacts.value.filter((c) => c.status === 'scraped'))

onMounted(async () => {
  if (!jobId.value) {
    error.value = 'Ungültige Job-ID'
    return
  }
  loading.value = true
  try {
    await Promise.all([
      store.fetchJob(jobId.value),
      store.fetchJobContacts(jobId.value),
      funnelsStore.fetchFunnels()
    ])

    // Set default funnel for import
    if (job.value?.funnel_id) {
      importForm.value.funnel_id = job.value.funnel_id
    }

    // Start polling if job is running
    if (job.value && ['running', 'queued'].includes(job.value.status)) {
      startPolling()
    }
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  stopPolling()
})

function startPolling() {
  if (pollInterval.value) return
  pollInterval.value = setInterval(async () => {
    await store.fetchJob(jobId.value)
    await store.fetchJobContacts(jobId.value)
    if (job.value && !['running', 'queued'].includes(job.value.status)) {
      stopPolling()
    }
  }, 5000)
}

function stopPolling() {
  if (pollInterval.value) {
    clearInterval(pollInterval.value)
    pollInterval.value = null
  }
}

function editJob() {
  router.push(`/linkedin/jobs/${jobId.value}/edit`)
}

async function startJob() {
  if (!jobId.value) return
  try {
    await store.runJob(jobId.value)
    startPolling()
  } catch (err) {
    error.value = err.response?.data?.detail || err.message
  }
}

async function pauseJob() {
  if (!jobId.value) return
  try {
    await store.stopJob(jobId.value)
    stopPolling()
  } catch (err) {
    error.value = err.response?.data?.detail || err.message
  }
}

async function cancelJob() {
  if (!jobId.value) return
  try {
    await store.abortJob(jobId.value)
    stopPolling()
  } catch (err) {
    error.value = err.response?.data?.detail || err.message
  }
}

async function deleteJob() {
  try {
    await store.removeJob(jobId.value)
    router.push('/linkedin')
  } catch (err) {
    error.value = err.message
  }
}

const showDeleteContactsConfirm = ref(false)

async function deleteAllJobContacts() {
  try {
    await store.removeJobContacts(jobId.value)
    showDeleteContactsConfirm.value = false
    await store.fetchJobContacts(jobId.value)
  } catch (err) {
    error.value = err.message
  }
}

function openImportModal() {
  if (job.value?.funnel_id) {
    importForm.value.funnel_id = job.value.funnel_id
  }
  showImportModal.value = true
}

async function importContacts() {
  if (!importForm.value.funnel_id) {
    error.value = 'Bitte waehle einen Funnel aus'
    return
  }

  importLoading.value = true
  error.value = null

  try {
    const result = await store.importContacts(jobId.value, importForm.value)
    showImportModal.value = false
    // Show success message
    alert(
      `${result.imported} Kontakte importiert, ${result.duplicates} Duplikate, ${result.companies_created} Firmen erstellt`
    )
  } catch (err) {
    error.value = err.message
  } finally {
    importLoading.value = false
  }
}

function openAddUrlsModal() {
  urlsForm.value.urls_text = ''
  showAddUrlsModal.value = true
}

async function addUrls() {
  const urls = urlsForm.value.urls_text
    .split('\n')
    .map((u) => u.trim())
    .filter((u) => u.length > 0)

  if (urls.length === 0) {
    error.value = 'Bitte gib mindestens eine URL ein'
    return
  }

  urlsLoading.value = true
  error.value = null

  try {
    const result = await store.addUrls(jobId.value, urls)
    showAddUrlsModal.value = false
    alert(`${result.added} URLs hinzugefuegt, ${result.duplicates} Duplikate`)
  } catch (err) {
    error.value = err.message
  } finally {
    urlsLoading.value = false
  }
}

async function openLogsModal() {
  showLogsModal.value = true
  logsLoading.value = true
  try {
    await store.fetchJobLogs(jobId.value)
  } catch (err) {
    error.value = err.message
  } finally {
    logsLoading.value = false
  }
}

function formatDuration(seconds) {
  if (!seconds) return '-'
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  if (mins > 0) {
    return `${mins}m ${secs}s`
  }
  return `${secs}s`
}

function formatDateTime(dateStr) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const logStatusColors = {
  running: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300',
  completed: 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300',
  failed: 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300',
  cancelled: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
}

const logStatusLabels = {
  running: 'Laeuft',
  completed: 'Abgeschlossen',
  failed: 'Fehlgeschlagen',
  cancelled: 'Abgebrochen'
}
</script>

<template>
  <div class="min-h-screen bg-go4-bg dark:bg-gray-900">
    <PageHeader
      :title="job?.name || 'Job laden...'"
      :subtitle="job?.account_name"
    >
      <template #actions>
        <button
          v-if="job && job.status === 'draft'"
          class="rounded-lg bg-green-600 px-4 py-2 text-sm text-white hover:bg-green-700"
          @click="startJob"
        >
          Starten
        </button>
        <button
          v-if="job && ['paused', 'failed', 'cancelled', 'completed'].includes(job.status)"
          class="rounded-lg bg-green-600 px-4 py-2 text-sm text-white hover:bg-green-700"
          @click="startJob"
        >
          {{ job.status === 'completed' ? 'Neu starten' : 'Fortsetzen' }}
        </button>
        <button
          v-if="job && job.status === 'running'"
          class="rounded-lg bg-yellow-600 px-4 py-2 text-sm text-white hover:bg-yellow-700"
          @click="pauseJob"
        >
          Pausieren
        </button>
        <button
          v-if="job && ['running', 'queued'].includes(job.status)"
          class="rounded-lg bg-red-600 px-4 py-2 text-sm text-white hover:bg-red-700"
          @click="cancelJob"
        >
          Abbrechen
        </button>
        <button
          v-if="job && !['running', 'queued'].includes(job.status)"
          class="rounded-lg px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
          @click="editJob"
        >
          Bearbeiten
        </button>
        <button
          v-if="job && job.status !== 'running'"
          class="rounded-lg px-4 py-2 text-sm text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20"
          @click="showDeleteConfirm = true"
        >
          Loeschen
        </button>
      </template>
    </PageHeader>

    <div class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <!-- Loading -->
      <div
        v-if="loading"
        class="py-12 text-center text-go4-muted"
      >
        Laden...
      </div>

      <!-- Error -->
      <div
        v-if="error"
        class="mb-4 rounded-lg bg-red-50 p-4 text-red-700 dark:bg-red-900/30 dark:text-red-300"
      >
        {{ error }}
      </div>

      <div
        v-if="job && !loading"
        class="space-y-6"
      >
        <!-- Status & Progress -->
        <div
          class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800"
        >
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-4">
              <span
                :class="statusColors[job.status]"
                class="rounded-full px-3 py-1 text-sm font-medium"
              >
                {{ statusLabels[job.status] }}
              </span>
              <span
                v-if="job.funnel_name"
                class="text-sm text-go4-muted dark:text-gray-400"
              >
                -&gt; {{ job.funnel_name }}
              </span>
            </div>

            <div
              v-if="job.status === 'running'"
              class="flex items-center gap-3"
            >
              <div class="h-2 w-48 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
                <div
                  class="h-full bg-indigo-500 transition-all"
                  :style="{ width: `${job.progress_percent}%` }"
                />
              </div>
              <span class="text-sm font-medium">{{ Math.round(job.progress_percent) }}%</span>
            </div>
          </div>

          <!-- Stats Grid -->
          <div class="mt-6 grid gap-4 md:grid-cols-4">
            <div class="rounded-lg bg-gray-50 p-4 dark:bg-gray-700">
              <div class="text-sm text-go4-muted dark:text-gray-400">
                Profile gefunden
              </div>
              <div class="mt-1 text-xl font-bold text-go4-secondary dark:text-white">
                {{ job.profiles_found }}
              </div>
            </div>
            <div class="rounded-lg bg-gray-50 p-4 dark:bg-gray-700">
              <div class="text-sm text-go4-muted dark:text-gray-400">
                Gescraped
              </div>
              <div class="mt-1 text-xl font-bold text-go4-secondary dark:text-white">
                {{ job.profiles_scraped }}
              </div>
            </div>
            <div class="rounded-lg bg-gray-50 p-4 dark:bg-gray-700">
              <div class="text-sm text-go4-muted dark:text-gray-400">
                Fehlgeschlagen
              </div>
              <div class="mt-1 text-xl font-bold text-red-600 dark:text-red-400">
                {{ job.profiles_failed }}
              </div>
            </div>
            <div class="rounded-lg bg-gray-50 p-4 dark:bg-gray-700">
              <div class="text-sm text-go4-muted dark:text-gray-400">
                Max. Profile
              </div>
              <div class="mt-1 text-xl font-bold text-go4-secondary dark:text-white">
                {{ job.max_profiles }}
              </div>
            </div>
          </div>

          <!-- Error Message -->
          <div
            v-if="job.error_message"
            class="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-300"
          >
            <strong>Fehler:</strong> {{ job.error_message }}
          </div>
        </div>

        <!-- Actions -->
        <div class="flex gap-4">
          <button
            class="flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
            @click="openLogsModal"
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
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            Ausfuehrungen
          </button>

          <button
            v-if="job.job_type === 'profile_list'"
            class="flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
            @click="openAddUrlsModal"
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
                d="M12 4v16m8-8H4"
              />
            </svg>
            URLs hinzufuegen
          </button>

          <button
            v-if="scrapedContacts.length > 0"
            class="flex items-center gap-2 rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark"
            @click="openImportModal"
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
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"
              />
            </svg>
            {{ scrapedContacts.length }} Kontakte importieren
          </button>
        </div>

        <!-- Contacts Table -->
        <div
          class="rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800"
        >
          <div class="flex items-center justify-between border-b border-gray-200 p-4 dark:border-gray-700">
            <h3 class="font-medium text-go4-secondary dark:text-white">
              Gescrapte Kontakte ({{ contacts.length }})
            </h3>
            <button
              v-if="contacts.length > 0"
              class="rounded-lg border border-red-300 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 dark:border-red-700 dark:text-red-400 dark:hover:bg-red-900/20"
              @click="showDeleteContactsConfirm = true"
            >
              Alle loeschen
            </button>
          </div>

          <div
            v-if="contacts.length === 0"
            class="p-8 text-center text-go4-muted dark:text-gray-400"
          >
            Noch keine Kontakte gescraped
          </div>

          <div
            v-else
            class="overflow-x-auto"
          >
            <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead class="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th
                    v-for="col in contactColumns"
                    :key="col.key"
                    class="px-4 py-3 text-left text-xs font-medium uppercase text-go4-muted dark:text-gray-400"
                  >
                    {{ col.label }}
                  </th>
                </tr>
              </thead>
              <tbody
                class="divide-y divide-gray-200 bg-white dark:divide-gray-700 dark:bg-gray-800"
              >
                <tr
                  v-for="contact in contacts.slice(0, 100)"
                  :key="contact.id"
                  class="hover:bg-gray-50 dark:hover:bg-gray-700"
                >
                  <td class="whitespace-nowrap px-4 py-3">
                    <div class="font-medium text-go4-secondary dark:text-white">
                      {{ contact.name }}
                    </div>
                    <div
                      v-if="contact.headline"
                      class="max-w-xs truncate text-xs text-go4-muted"
                    >
                      {{ contact.headline }}
                    </div>
                  </td>
                  <td class="whitespace-nowrap px-4 py-3 text-sm text-go4-muted dark:text-gray-400">
                    {{ contact.position || '-' }}
                  </td>
                  <td class="whitespace-nowrap px-4 py-3 text-sm text-go4-muted dark:text-gray-400">
                    {{ contact.company_name || '-' }}
                  </td>
                  <td class="whitespace-nowrap px-4 py-3">
                    <span
                      :class="statusColors[contact.status]"
                      class="rounded-full px-2 py-0.5 text-xs font-medium"
                    >
                      {{ statusLabels[contact.status] }}
                    </span>
                  </td>
                  <td class="whitespace-nowrap px-4 py-3">
                    <a
                      :href="contact.linkedin_url"
                      target="_blank"
                      class="text-blue-600 hover:underline dark:text-blue-400"
                    >
                      Profil
                    </a>
                  </td>
                </tr>
              </tbody>
            </table>
            <div
              v-if="contacts.length > 100"
              class="p-4 text-center text-sm text-go4-muted"
            >
              Zeige 100 von {{ contacts.length }} Kontakten
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Import Modal -->
    <Teleport to="body">
      <div
        v-if="showImportModal"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
        @click.self="showImportModal = false"
      >
        <div class="w-full max-w-md rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800">
          <h2 class="mb-4 text-lg font-semibold text-go4-secondary dark:text-white">
            Kontakte importieren
          </h2>

          <form
            class="space-y-4"
            @submit.prevent="importContacts"
          >
            <div>
              <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                Ziel-Funnel *
              </label>
              <select
                v-model="importForm.funnel_id"
                required
                class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
                <option
                  :value="null"
                  disabled
                >
                  Funnel waehlen...
                </option>
                <option
                  v-for="funnel in funnelsStore.funnels"
                  :key="funnel.id"
                  :value="funnel.id"
                >
                  {{ funnel.name }}
                </option>
              </select>
            </div>

            <div v-if="selectedFunnel">
              <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                Import-Stage
              </label>
              <select
                v-model="importForm.stage_id"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
                <option :value="null">
                  Erste Stage
                </option>
                <option
                  v-for="stage in selectedFunnel.stages"
                  :key="stage.id"
                  :value="stage.id"
                >
                  {{ stage.name }}
                </option>
              </select>
            </div>

            <div class="flex items-center gap-3">
              <input
                id="skip_duplicates"
                v-model="importForm.skip_duplicates"
                type="checkbox"
                class="h-4 w-4 rounded border-gray-300 text-go4-primary"
              >
              <label
                for="skip_duplicates"
                class="text-sm text-go4-secondary dark:text-gray-200"
              >
                Duplikate ueberspringen
              </label>
            </div>

            <div class="flex items-center gap-3">
              <input
                id="create_companies"
                v-model="importForm.create_companies"
                type="checkbox"
                class="h-4 w-4 rounded border-gray-300 text-go4-primary"
              >
              <label
                for="create_companies"
                class="text-sm text-go4-secondary dark:text-gray-200"
              >
                Firmen automatisch erstellen
              </label>
            </div>

            <div class="flex justify-end gap-3 pt-4">
              <button
                type="button"
                class="rounded-lg px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
                @click="showImportModal = false"
              >
                Abbrechen
              </button>
              <button
                type="submit"
                class="rounded-lg bg-go4-primary px-4 py-2 text-sm text-white hover:bg-go4-primary-dark disabled:opacity-50"
                :disabled="importLoading"
              >
                {{ importLoading ? 'Importieren...' : `${scrapedContacts.length} importieren` }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Add URLs Modal -->
    <Teleport to="body">
      <div
        v-if="showAddUrlsModal"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
        @click.self="showAddUrlsModal = false"
      >
        <div class="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800">
          <h2 class="mb-4 text-lg font-semibold text-go4-secondary dark:text-white">
            URLs hinzufuegen
          </h2>

          <form
            class="space-y-4"
            @submit.prevent="addUrls"
          >
            <div>
              <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                LinkedIn Profil-URLs (eine pro Zeile)
              </label>
              <textarea
                v-model="urlsForm.urls_text"
                rows="10"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                placeholder="https://www.linkedin.com/in/max-mustermann/
https://www.linkedin.com/in/erika-musterfrau/
..."
              />
            </div>

            <div class="flex justify-end gap-3">
              <button
                type="button"
                class="rounded-lg px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
                @click="showAddUrlsModal = false"
              >
                Abbrechen
              </button>
              <button
                type="submit"
                class="rounded-lg bg-go4-primary px-4 py-2 text-sm text-white hover:bg-go4-primary-dark disabled:opacity-50"
                :disabled="urlsLoading"
              >
                {{ urlsLoading ? 'Hinzufuegen...' : 'Hinzufuegen' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Logs Modal -->
    <Teleport to="body">
      <div
        v-if="showLogsModal"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
        @click.self="showLogsModal = false"
      >
        <div class="w-full max-w-4xl rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800">
          <div class="mb-4 flex items-center justify-between">
            <h2 class="text-lg font-semibold text-go4-secondary dark:text-white">
              Job-Ausfuehrungen
            </h2>
            <button
              class="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700"
              @click="showLogsModal = false"
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

          <!-- Loading -->
          <div
            v-if="logsLoading"
            class="py-8 text-center text-go4-muted"
          >
            Lade Ausfuehrungen...
          </div>

          <!-- Empty State -->
          <div
            v-else-if="logs.length === 0"
            class="py-8 text-center text-go4-muted"
          >
            Noch keine Ausfuehrungen vorhanden
          </div>

          <!-- Logs Table -->
          <div
            v-else
            class="max-h-96 overflow-auto"
          >
            <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead class="sticky top-0 bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th
                    class="px-4 py-3 text-left text-xs font-medium uppercase text-go4-muted dark:text-gray-400"
                  >
                    Datum
                  </th>
                  <th
                    class="px-4 py-3 text-left text-xs font-medium uppercase text-go4-muted dark:text-gray-400"
                  >
                    Seiten
                  </th>
                  <th
                    class="px-4 py-3 text-left text-xs font-medium uppercase text-go4-muted dark:text-gray-400"
                  >
                    Profile
                  </th>
                  <th
                    class="px-4 py-3 text-left text-xs font-medium uppercase text-go4-muted dark:text-gray-400"
                  >
                    Dauer
                  </th>
                  <th
                    class="px-4 py-3 text-left text-xs font-medium uppercase text-go4-muted dark:text-gray-400"
                  >
                    Status
                  </th>
                </tr>
              </thead>
              <tbody
                class="divide-y divide-gray-200 bg-white dark:divide-gray-700 dark:bg-gray-800"
              >
                <tr
                  v-for="log in logs"
                  :key="log.id"
                  class="hover:bg-gray-50 dark:hover:bg-gray-700"
                >
                  <td
                    class="whitespace-nowrap px-4 py-3 text-sm text-go4-secondary dark:text-white"
                  >
                    {{ formatDateTime(log.started_at) }}
                  </td>
                  <td class="whitespace-nowrap px-4 py-3 text-sm text-go4-muted dark:text-gray-400">
                    {{ log.start_page }}
                    <span v-if="log.end_page"> - {{ log.end_page }}</span>
                  </td>
                  <td class="whitespace-nowrap px-4 py-3 text-sm">
                    <span class="font-medium text-go4-secondary dark:text-white">
                      {{ log.profiles_scraped }}
                    </span>
                    <span
                      v-if="log.profiles_failed > 0"
                      class="ml-2 text-red-600 dark:text-red-400"
                    >
                      ({{ log.profiles_failed }} fehlgeschl.)
                    </span>
                    <span
                      v-if="log.profiles_skipped > 0"
                      class="ml-2 text-gray-500"
                    >
                      ({{ log.profiles_skipped }} uebersprungen)
                    </span>
                  </td>
                  <td class="whitespace-nowrap px-4 py-3 text-sm text-go4-muted dark:text-gray-400">
                    {{ formatDuration(log.duration_seconds) }}
                  </td>
                  <td class="whitespace-nowrap px-4 py-3">
                    <span
                      :class="logStatusColors[log.status] || 'bg-gray-100 text-gray-700'"
                      class="rounded-full px-2 py-0.5 text-xs font-medium"
                    >
                      {{ logStatusLabels[log.status] || log.status }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Error Messages (if any log has error) -->
          <div class="mt-4 space-y-2">
            <template
              v-for="log in logs"
              :key="`err-${log.id}`"
            >
              <div
                v-if="log.error_message"
                class="rounded-lg bg-red-50 p-3 text-sm dark:bg-red-900/20"
              >
                <span class="font-medium text-red-700 dark:text-red-300">
                  {{ formatDateTime(log.started_at) }}:
                </span>
                <span class="text-red-600 dark:text-red-400">
                  {{ log.error_message }}
                </span>
              </div>
            </template>
          </div>

          <div class="mt-4 flex justify-end">
            <button
              class="rounded-lg px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
              @click="showLogsModal = false"
            >
              Schliessen
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Delete Confirmation -->
    <ConfirmDialog
      :open="showDeleteConfirm"
      title="Job loeschen?"
      message="Moechtest du diesen Job wirklich loeschen? Alle gescrapten Kontakte werden ebenfalls geloescht."
      confirm-text="Loeschen"
      variant="danger"
      @confirm="deleteJob"
      @cancel="showDeleteConfirm = false"
    />

    <ConfirmDialog
      :open="showDeleteContactsConfirm"
      title="Alle Kontakte loeschen?"
      :message="`Moechtest du wirklich alle ${contacts.length} Kontakte dieses Jobs loeschen?`"
      confirm-text="Alle loeschen"
      variant="danger"
      @confirm="deleteAllJobContacts"
      @cancel="showDeleteContactsConfirm = false"
    />
  </div>
</template>
