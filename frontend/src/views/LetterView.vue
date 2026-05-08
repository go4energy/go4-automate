<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useLetterStore } from '@/stores/letter'
import { usePipelineContext } from '@/stores/pipelineContext'
import PageHeader from '@/components/ui/PageHeader.vue'
import EmptyState from '@/components/ui/EmptyState.vue'

const route = useRoute()
const router = useRouter()
const store = useLetterStore()
const pipelineCtx = usePipelineContext()

// Active tab from route
const activeTab = computed(() => route.meta?.tab || 'dashboard')

const tabs = [
  { key: 'dashboard', label: 'Dashboard', route: '/letter' },
  { key: 'letters', label: 'Briefe', route: '/letter/letters' },
  { key: 'templates', label: 'Templates', route: '/letter/templates' },
  { key: 'batches', label: 'Batches', route: '/letter/batches' },
  { key: 'settings', label: 'Setup', route: '/letter/setup' },
]

// Stats + provider data
const stats = computed(() => store.stats)
const balance = computed(() => store.balance)
const costStats = computed(() => store.costStats)
const settings = computed(() => store.settings)

// Settings form (mirrored from store.settings, edited locally before save)
const settingsForm = ref({
  letterxpress_username: '',
  letterxpress_apikey: '',
  letterxpress_default_mode: 'test',
  letterxpress_default_color: '4',
  letterxpress_c4_envelope: '1',
  letterxpress_default_shipping: 'national',
})
const settingsBusy = ref(false)
const settingsMessage = ref('')

// Cost-stats period filter
const costPeriod = ref('month')
const costMode = ref('all')

function fmtEur(cents) {
  if (cents == null) return '—'
  return `${(cents / 100).toFixed(2).replace('.', ',')} €`
}

const provFmt = computed(() => ({
  test: 'bg-amber-100 text-amber-800',
  live: 'bg-emerald-100 text-emerald-800',
}))

// Letters
const letters = computed(() => store.letters)
const letterFilters = ref({
  status: '',
  search: '',
})

// Templates
const templates = computed(() => store.templates)

// Batches
const batches = computed(() => store.batches)

// Modals
const showCreateLetterModal = ref(false)
const showCreateTemplateModal = ref(false)
const showCreateBatchModal = ref(false)
const showPreviewModal = ref(false)
const previewContent = ref('')

// Selected items for batch creation
const selectedLetterIds = ref([])

// New letter form
const newLetter = ref({
  template_id: null,
  recipient: {
    name: '',
    company: '',
    street: '',
    zip: '',
    city: '',
    country: 'DE',
  },
})

// New template form
const newTemplate = ref({
  name: '',
  description: '',
  format: 'a4',
  content_html: '<p>Sehr geehrte/r {{contact.name}},</p>\n\n<p></p>\n\n<p>Mit freundlichen Grüßen</p>',
  header_html: '',
  footer_html: '',
})

// New batch form
const newBatch = ref({
  name: '',
  letter_ids: [],
})

// Status badge colors
const statusColors = {
  draft: 'bg-gray-100 text-gray-800',
  approved: 'bg-blue-100 text-blue-800',
  queued: 'bg-yellow-100 text-yellow-800',
  sent: 'bg-green-100 text-green-800',
  delivered: 'bg-green-200 text-green-900',
  returned: 'bg-red-100 text-red-800',
  collecting: 'bg-gray-100 text-gray-800',
  ready: 'bg-blue-100 text-blue-800',
  exported: 'bg-yellow-100 text-yellow-800',
}

const statusLabels = {
  draft: 'Entwurf',
  approved: 'Genehmigt',
  queued: 'In Warteschlange',
  sent: 'Versendet',
  delivered: 'Zugestellt',
  returned: 'Rückläufer',
  collecting: 'Sammeln',
  ready: 'Bereit',
  exported: 'Exportiert',
}

// Filtered letters
const filteredLetters = computed(() => {
  let result = letters.value
  if (letterFilters.value.status) {
    result = result.filter((l) => l.status === letterFilters.value.status)
  }
  if (letterFilters.value.search) {
    const search = letterFilters.value.search.toLowerCase()
    result = result.filter(
      (l) =>
        l.recipient_name.toLowerCase().includes(search) ||
        l.recipient_company?.toLowerCase().includes(search)
    )
  }
  return result
})

// ============== Sending + status sync (Letterxpress) ==============
async function handleSendLetter(letter, mode = 'test') {
  const verb = mode === 'live' ? 'LIVE versenden' : 'an Letterxpress (Test) übergeben'
  if (!confirm(`Brief #${letter.id} an ${letter.recipient_name} ${verb}?`)) return
  try {
    await store.sendLetter(letter.id, mode)
    await store.fetchBalance()
    await store.fetchCostStats({ period: costPeriod.value, mode: costMode.value })
  } catch (err) {
    console.error('Failed to send letter:', err)
  }
}

async function handleSyncStatus(letter) {
  try {
    await store.syncLetterStatus(letter.id)
  } catch (err) {
    console.error('Failed to sync status:', err)
  }
}

// ============== Settings ==============
async function loadSettings() {
  try {
    await store.fetchSettings()
    if (settings.value) {
      settingsForm.value.letterxpress_username = settings.value.username || ''
      // apikey stays blank — user must re-enter to change it
      settingsForm.value.letterxpress_default_mode = settings.value.mode || 'test'
      settingsForm.value.letterxpress_default_color = settings.value.color || '4'
      settingsForm.value.letterxpress_c4_envelope = String(settings.value.c4 ?? 1)
      settingsForm.value.letterxpress_default_shipping = settings.value.shipping || 'national'
    }
  } catch (err) {
    console.error('Failed to load settings:', err)
  }
}

async function saveSetting(variable, value) {
  if (value === '' || value == null) return
  settingsBusy.value = true
  settingsMessage.value = ''
  try {
    await store.updateSetting(variable, String(value))
    settingsMessage.value = 'Gespeichert.'
    await loadSettings()
  } catch (err) {
    settingsMessage.value = `Fehler: ${err.response?.data?.detail || err.message}`
  } finally {
    settingsBusy.value = false
  }
}

async function saveAllSettings() {
  settingsBusy.value = true
  settingsMessage.value = ''
  try {
    for (const [variable, value] of Object.entries(settingsForm.value)) {
      // Skip apikey if blank (means: user did not change it)
      if (variable === 'letterxpress_apikey' && !value) continue
      if (value === '' || value == null) continue
      await store.updateSetting(variable, String(value))
    }
    settingsMessage.value = 'Alle Einstellungen gespeichert.'
    settingsForm.value.letterxpress_apikey = ''  // clear input
    await loadSettings()
    await store.fetchBalance()
  } catch (err) {
    settingsMessage.value = `Fehler: ${err.response?.data?.detail || err.message}`
  } finally {
    settingsBusy.value = false
  }
}

async function testConnection() {
  settingsBusy.value = true
  settingsMessage.value = 'Teste Verbindung...'
  try {
    const b = await store.fetchBalance()
    if (b) {
      settingsMessage.value = `Verbindung OK — Guthaben: ${b.balance} ${b.currency} (Mode: ${b.mode})`
    } else {
      settingsMessage.value = `Verbindung fehlgeschlagen: ${store.error || 'unbekannt'}`
    }
  } finally {
    settingsBusy.value = false
  }
}

// Load data — scoped to the globally selected pipeline.
async function loadData() {
  try {
    const pid = pipelineCtx.activePipelineId || undefined
    const tasks = [
      store.fetchStats(),
      store.fetchLetters({ pipeline_id: pid }),
      store.fetchTemplates(),
      store.fetchBatches({ pipeline_id: pid }),
      store.fetchBalance(),
      store.fetchCostStats({
        period: costPeriod.value,
        mode: costMode.value,
        pipeline_id: pid,
      }),
    ]
    if (activeTab.value === 'settings') tasks.push(loadSettings())
    await Promise.all(tasks)
  } catch (err) {
    console.error('Failed to load letter data:', err)
  }
}

// Letter actions
async function createLetter() {
  try {
    await store.createLetter(newLetter.value)
    showCreateLetterModal.value = false
    resetLetterForm()
  } catch (err) {
    console.error('Failed to create letter:', err)
  }
}

async function approveLetter(id) {
  try {
    await store.approveLetter(id)
  } catch (err) {
    console.error('Failed to approve letter:', err)
  }
}

async function deleteLetter(id) {
  if (!confirm('Brief wirklich löschen?')) return
  try {
    await store.deleteLetter(id)
  } catch (err) {
    console.error('Failed to delete letter:', err)
  }
}

async function generatePdf(id) {
  try {
    await store.generateLetterPdf(id)
  } catch (err) {
    console.error('Failed to generate PDF:', err)
  }
}

function viewLetter(letter) {
  router.push(`/letter/letters/${letter.id}`)
}

// Template actions
async function createTemplate() {
  try {
    await store.createTemplate(newTemplate.value)
    showCreateTemplateModal.value = false
    resetTemplateForm()
  } catch (err) {
    console.error('Failed to create template:', err)
  }
}

function editTemplate(template) {
  router.push(`/letter/templates/${template.id}/edit`)
}

async function deleteTemplate(id) {
  if (!confirm('Template wirklich löschen?')) return
  try {
    await store.deleteTemplate(id)
  } catch (err) {
    console.error('Failed to delete template:', err)
  }
}

async function previewTemplate(template) {
  try {
    const result = await store.previewTemplate({ template_id: template.id })
    previewContent.value = result.html
    showPreviewModal.value = true
  } catch (err) {
    console.error('Failed to preview template:', err)
  }
}

// Batch actions
async function createBatch() {
  try {
    newBatch.value.letter_ids = selectedLetterIds.value
    await store.createBatch(newBatch.value)
    showCreateBatchModal.value = false
    selectedLetterIds.value = []
    resetBatchForm()
    // Reload letters to reflect batch assignment
    await store.fetchLetters()
  } catch (err) {
    console.error('Failed to create batch:', err)
  }
}

async function exportBatch(id) {
  try {
    const result = await store.exportBatch(id)
    alert(`Export erstellt: ${result.export_path}\n${result.letter_count} Briefe exportiert.`)
  } catch (err) {
    console.error('Failed to export batch:', err)
  }
}

async function markBatchSent(id) {
  if (!confirm('Batch als versendet markieren?')) return
  try {
    await store.markBatchSent(id)
  } catch (err) {
    console.error('Failed to mark batch as sent:', err)
  }
}

// Reset forms
function resetLetterForm() {
  newLetter.value = {
    template_id: null,
    recipient: {
      name: '',
      company: '',
      street: '',
      zip: '',
      city: '',
      country: 'DE',
    },
  }
}

function resetTemplateForm() {
  newTemplate.value = {
    name: '',
    description: '',
    format: 'a4',
    content_html: '<p>Sehr geehrte/r {{contact.name}},</p>\n\n<p></p>\n\n<p>Mit freundlichen Grüßen</p>',
    header_html: '',
    footer_html: '',
  }
}

function resetBatchForm() {
  newBatch.value = {
    name: '',
    letter_ids: [],
  }
}

// Toggle letter selection
function toggleLetterSelection(letterId) {
  const idx = selectedLetterIds.value.indexOf(letterId)
  if (idx === -1) {
    selectedLetterIds.value.push(letterId)
  } else {
    selectedLetterIds.value.splice(idx, 1)
  }
}

// Select all approved letters
function selectAllApproved() {
  selectedLetterIds.value = store.approvedLetters
    .filter((l) => !l.batch_id)
    .map((l) => l.id)
}

// Format date
function formatDate(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

onMounted(async () => {
  await pipelineCtx.ensurePipelines()
  loadData()
})

// Reload when tab or active pipeline changes
watch(activeTab, () => {
  loadData()
})

watch(
  () => pipelineCtx.activePipelineId,
  () => loadData(),
)
</script>

<template>
  <div class="space-y-6">
    <PageHeader
      title="Post-Mail"
    >
      <template #actions>
        <button
          v-if="activeTab === 'letters'"
          class="btn btn-primary"
          @click="showCreateLetterModal = true"
        >
          Neuer Brief
        </button>
        <button
          v-if="activeTab === 'templates'"
          class="btn btn-primary"
          @click="showCreateTemplateModal = true"
        >
          Neues Template
        </button>
        <button
          v-if="activeTab === 'letters' && selectedLetterIds.length > 0"
          class="btn btn-secondary"
          @click="showCreateBatchModal = true"
        >
          Batch erstellen ({{ selectedLetterIds.length }})
        </button>
      </template>
    </PageHeader>

    <!-- Stats Cards -->
    <div
      v-if="stats"
      class="grid grid-cols-2 gap-4 sm:grid-cols-5"
    >
      <div class="rounded-lg bg-white p-4 shadow-sm">
        <div class="text-sm text-gray-500">
          Templates
        </div>
        <div class="text-2xl font-bold text-gray-900">
          {{ stats.active_templates }} / {{ stats.total_templates }}
        </div>
      </div>
      <div class="rounded-lg bg-white p-4 shadow-sm">
        <div class="text-sm text-gray-500">
          Briefe gesamt
        </div>
        <div class="text-2xl font-bold text-gray-900">
          {{ stats.total_letters }}
        </div>
      </div>
      <div class="rounded-lg bg-white p-4 shadow-sm">
        <div class="text-sm text-gray-500">
          Versendet
        </div>
        <div class="text-2xl font-bold text-green-600">
          {{ stats.letters_by_status?.sent || 0 }}
        </div>
      </div>
      <div class="rounded-lg bg-white p-4 shadow-sm">
        <div class="flex items-center justify-between text-sm text-gray-500">
          <span>Kosten ({{ costPeriod }})</span>
          <span
            v-if="costMode !== 'all'"
            class="rounded px-1.5 py-0.5 text-[10px] font-medium uppercase"
            :class="costMode === 'live' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'"
          >{{ costMode }}</span>
        </div>
        <div class="text-2xl font-bold text-gray-900">
          {{ costStats ? fmtEur(costStats.cost_cents) : '—' }}
        </div>
        <div class="mt-1 text-[11px] text-gray-400">
          {{ costStats?.count ?? 0 }} Briefe
        </div>
      </div>
      <div class="rounded-lg bg-white p-4 shadow-sm">
        <div class="flex items-center justify-between text-sm text-gray-500">
          <span>Letterxpress-Guthaben</span>
          <span
            v-if="balance"
            class="rounded px-1.5 py-0.5 text-[10px] font-medium uppercase"
            :class="balance.mode === 'live' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'"
          >{{ balance.mode }}</span>
        </div>
        <div
          class="text-2xl font-bold"
          :class="balance && balance.balance < 5 ? 'text-red-600' : 'text-gray-900'"
        >
          {{ balance ? `${balance.balance.toFixed(2).replace('.', ',')} ${balance.currency}` : '—' }}
        </div>
        <div
          v-if="!balance"
          class="mt-1 text-[11px] text-gray-400"
        >
          (Settings prüfen)
        </div>
      </div>
    </div>

    <!-- Tabs -->
    <div class="border-b border-gray-200">
      <nav class="-mb-px flex gap-6">
        <router-link
          v-for="tab in tabs"
          :key="tab.key"
          :to="tab.route"
          class="border-b-2 pb-3 text-sm font-medium transition-colors"
          :class="
            activeTab === tab.key
              ? 'border-go4-primary text-go4-primary'
              : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
          "
        >
          {{ tab.label }}
        </router-link>
      </nav>
    </div>

    <!-- Dashboard Tab — Status der ausgewählten Pipeline -->
    <div v-if="activeTab === 'dashboard'">
      <div
        v-if="!pipelineCtx.activePipelineId"
        class="rounded-lg border border-dashed border-gray-300 bg-white p-8 text-center text-sm text-gray-500 dark:border-gray-600 dark:bg-gray-800"
      >
        <p class="font-medium text-gray-700 dark:text-gray-300">
          Keine Pipeline ausgewählt
        </p>
        <p class="mt-1">
          Wähle oben im Header eine Pipeline aus oder lege im Engagement-Modul eine neue an,
          um die Briefe dieser Kampagne zu sehen.
        </p>
        <router-link
          to="/engagement"
          class="mt-3 inline-block text-go4-primary hover:text-go4-primary-dark"
        >
          Zum Engagement →
        </router-link>
      </div>
      <div
        v-else-if="!pipelineCtx.activePipelineMatchesModule"
        class="rounded-lg border border-amber-200 bg-amber-50 p-6 text-sm text-amber-800 dark:border-amber-800/50 dark:bg-amber-900/20 dark:text-amber-200"
      >
        <p class="font-medium">
          Diese Pipeline hat keinen Letter-Kanal aktiv
        </p>
        <p class="mt-1">
          Aktiviere den Brief-Kanal im Engagement, um Briefe für
          <strong>{{ pipelineCtx.activePipeline?.name }}</strong> zu versenden.
        </p>
        <router-link
          :to="`/engagement/pipelines/${pipelineCtx.activePipelineId}/setup`"
          class="mt-2 inline-block text-go4-primary hover:text-go4-primary-dark"
        >
          Pipeline-Setup öffnen →
        </router-link>
      </div>
      <div
        v-else
        class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800"
      >
        <div class="mb-3 flex items-center justify-between">
          <h3 class="font-semibold text-gray-900 dark:text-gray-100">
            {{ pipelineCtx.activePipeline?.name }}
          </h3>
          <router-link
            to="/letter/letters"
            class="text-sm text-go4-primary hover:text-go4-primary-dark"
          >
            Briefe öffnen →
          </router-link>
        </div>
        <p class="text-sm text-gray-500 dark:text-gray-400">
          Stats und Briefe-Übersicht werden über die anderen Tabs angezeigt.
          Die globalen Stats-Cards oben spiegeln das gesamte Tenant-Volumen.
        </p>
      </div>
    </div>

    <!-- Letters Tab -->
    <div
      v-if="activeTab === 'letters'"
      class="space-y-4"
    >
      <!-- Filters -->
      <div class="flex gap-4">
        <input
          v-model="letterFilters.search"
          type="text"
          placeholder="Suchen..."
          class="input w-64"
        >
        <select
          v-model="letterFilters.status"
          class="input w-48"
        >
          <option value="">
            Alle Status
          </option>
          <option value="draft">
            Entwurf
          </option>
          <option value="approved">
            Genehmigt
          </option>
          <option value="queued">
            Warteschlange
          </option>
          <option value="sent">
            Versendet
          </option>
          <option value="delivered">
            Zugestellt
          </option>
          <option value="returned">
            Rückläufer
          </option>
        </select>
        <button
          v-if="store.approvedLetters.filter((l) => !l.batch_id).length > 0"
          class="btn btn-secondary"
          @click="selectAllApproved"
        >
          Alle genehmigten auswählen
        </button>
      </div>

      <!-- Letters Table -->
      <div
        v-if="store.loading"
        class="py-8 text-center text-gray-500"
      >
        Laden...
      </div>
      <div
        v-else-if="filteredLetters.length === 0"
        class="py-8 text-center text-gray-500"
      >
        <EmptyState
          title="Keine Briefe"
          action-label="Brief erstellen"
          @action="showCreateLetterModal = true"
        />
      </div>
      <div
        v-else
        class="overflow-hidden rounded-lg bg-white shadow"
      >
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th class="w-12 px-4 py-3">
                <input
                  type="checkbox"
                  :checked="
                    selectedLetterIds.length > 0 &&
                      selectedLetterIds.length === filteredLetters.filter((l) => l.status === 'approved' && !l.batch_id).length
                  "
                  @change="
                    selectedLetterIds.length > 0
                      ? (selectedLetterIds = [])
                      : selectAllApproved()
                  "
                >
              </th>
              <th
                class="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500"
              >
                Empfänger
              </th>
              <th
                class="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500"
              >
                Template
              </th>
              <th
                class="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500"
              >
                Status
              </th>
              <th
                class="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500"
              >
                Mode
              </th>
              <th
                class="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500"
              >
                Provider
              </th>
              <th
                class="px-4 py-3 text-right text-xs font-medium uppercase text-gray-500"
              >
                Kosten
              </th>
              <th
                class="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500"
              >
                Batch
              </th>
              <th
                class="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500"
              >
                Erstellt
              </th>
              <th class="px-4 py-3" />
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200">
            <tr
              v-for="letter in filteredLetters"
              :key="letter.id"
              class="hover:bg-gray-50"
            >
              <td class="px-4 py-3">
                <input
                  v-if="letter.status === 'approved' && !letter.batch_id"
                  type="checkbox"
                  :checked="selectedLetterIds.includes(letter.id)"
                  @change="toggleLetterSelection(letter.id)"
                >
              </td>
              <td class="px-4 py-3">
                <div class="font-medium text-gray-900">
                  {{ letter.recipient_name }}
                </div>
                <div
                  v-if="letter.recipient_company"
                  class="text-sm text-gray-500"
                >
                  {{ letter.recipient_company }}
                </div>
              </td>
              <td class="px-4 py-3 text-sm text-gray-500">
                {{ letter.template_name || '-' }}
              </td>
              <td class="px-4 py-3">
                <span
                  class="inline-flex rounded-full px-2 py-1 text-xs font-medium"
                  :class="statusColors[letter.status]"
                >
                  {{ statusLabels[letter.status] || letter.status }}
                </span>
              </td>
              <td class="px-4 py-3">
                <span
                  v-if="letter.send_mode"
                  class="inline-flex rounded px-1.5 py-0.5 text-[10px] font-medium uppercase"
                  :class="provFmt[letter.send_mode] || 'bg-gray-100 text-gray-600'"
                >
                  {{ letter.send_mode }}
                </span>
              </td>
              <td class="px-4 py-3 text-xs text-gray-500">
                <div v-if="letter.letterxpress_job_id">
                  <div class="font-mono">
                    #{{ letter.letterxpress_job_id }}
                  </div>
                  <div class="text-[10px]">
                    {{ letter.provider_status || '—' }}
                  </div>
                </div>
                <span v-else>—</span>
              </td>
              <td class="px-4 py-3 text-right text-sm text-gray-700 tabular-nums">
                {{ fmtEur(letter.provider_cost_cents) }}
              </td>
              <td class="px-4 py-3 text-sm text-gray-500">
                {{ letter.batch_id ? `#${letter.batch_id}` : '-' }}
              </td>
              <td class="px-4 py-3 text-sm text-gray-500">
                {{ formatDate(letter.created_at) }}
              </td>
              <td class="px-4 py-3 text-right">
                <div class="flex justify-end gap-2">
                  <button
                    class="text-gray-400 hover:text-gray-600"
                    title="Anzeigen"
                    @click="viewLetter(letter)"
                  >
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
                        d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                      />
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                      />
                    </svg>
                  </button>
                  <button
                    v-if="letter.status === 'draft'"
                    class="text-blue-400 hover:text-blue-600"
                    title="Genehmigen"
                    @click="approveLetter(letter.id)"
                  >
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
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                  </button>
                  <button
                    v-if="['draft','approved','queued'].includes(letter.status)"
                    class="rounded bg-amber-50 px-2 py-1 text-[11px] font-medium text-amber-800 hover:bg-amber-100"
                    title="An Letterxpress (Test) senden"
                    @click="handleSendLetter(letter, 'test')"
                  >
                    Senden (Test)
                  </button>
                  <button
                    v-if="['draft','approved','queued'].includes(letter.status)"
                    class="rounded bg-emerald-50 px-2 py-1 text-[11px] font-medium text-emerald-800 hover:bg-emerald-100"
                    title="An Letterxpress (Live) senden"
                    @click="handleSendLetter(letter, 'live')"
                  >
                    Senden (Live)
                  </button>
                  <button
                    v-if="letter.letterxpress_job_id && letter.status === 'sent'"
                    class="rounded bg-blue-50 px-2 py-1 text-[11px] font-medium text-blue-800 hover:bg-blue-100"
                    title="Status synchronisieren"
                    @click="handleSyncStatus(letter)"
                  >
                    Sync
                  </button>
                  <button
                    v-if="letter.status === 'approved' && !letter.pdf_path"
                    class="text-purple-400 hover:text-purple-600"
                    title="PDF generieren"
                    @click="generatePdf(letter.id)"
                  >
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
                        d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
                      />
                    </svg>
                  </button>
                  <button
                    v-if="letter.status === 'draft'"
                    class="text-red-400 hover:text-red-600"
                    title="Löschen"
                    @click="deleteLetter(letter.id)"
                  >
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
                        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                      />
                    </svg>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Templates Tab -->
    <div
      v-if="activeTab === 'templates'"
      class="space-y-4"
    >
      <div
        v-if="store.loading"
        class="py-8 text-center text-gray-500"
      >
        Laden...
      </div>
      <div
        v-else-if="templates.length === 0"
        class="py-8 text-center text-gray-500"
      >
        <EmptyState
          title="Keine Templates"
          action-label="Template erstellen"
          @action="showCreateTemplateModal = true"
        />
      </div>
      <div
        v-else
        class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
      >
        <div
          v-for="template in templates"
          :key="template.id"
          class="rounded-lg bg-white p-4 shadow-sm"
        >
          <div class="mb-2 flex items-start justify-between">
            <div>
              <h3 class="font-medium text-gray-900">
                {{ template.name }}
              </h3>
              <p
                v-if="template.description"
                class="text-sm text-gray-500"
              >
                {{ template.description }}
              </p>
            </div>
            <span
              class="rounded-full px-2 py-1 text-xs"
              :class="
                template.is_active
                  ? 'bg-green-100 text-green-800'
                  : 'bg-gray-100 text-gray-800'
              "
            >
              {{ template.is_active ? 'Aktiv' : 'Inaktiv' }}
            </span>
          </div>
          <div class="mb-3 text-sm text-gray-500">
            Format: {{ template.format.toUpperCase() }} |
            {{ template.letter_count }} Briefe
          </div>
          <div class="flex gap-2">
            <button
              class="btn btn-secondary btn-sm"
              @click="previewTemplate(template)"
            >
              Vorschau
            </button>
            <button
              class="btn btn-secondary btn-sm"
              @click="editTemplate(template)"
            >
              Bearbeiten
            </button>
            <button
              v-if="template.letter_count === 0"
              class="btn btn-danger btn-sm"
              @click="deleteTemplate(template.id)"
            >
              Löschen
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Batches Tab -->
    <div
      v-if="activeTab === 'batches'"
      class="space-y-4"
    >
      <div
        v-if="store.loading"
        class="py-8 text-center text-gray-500"
      >
        Laden...
      </div>
      <div
        v-else-if="batches.length === 0"
        class="py-8 text-center text-gray-500"
      >
        <EmptyState
          title="Keine Batches"
        />
      </div>
      <div
        v-else
        class="overflow-hidden rounded-lg bg-white shadow"
      >
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th
                class="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500"
              >
                Name
              </th>
              <th
                class="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500"
              >
                Briefe
              </th>
              <th
                class="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500"
              >
                Status
              </th>
              <th
                class="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500"
              >
                Erstellt
              </th>
              <th class="px-4 py-3" />
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200">
            <tr
              v-for="batch in batches"
              :key="batch.id"
              class="hover:bg-gray-50"
            >
              <td class="px-4 py-3 font-medium text-gray-900">
                {{ batch.name }}
              </td>
              <td class="px-4 py-3 text-sm text-gray-500">
                {{ batch.letter_count }}
              </td>
              <td class="px-4 py-3">
                <span
                  class="inline-flex rounded-full px-2 py-1 text-xs font-medium"
                  :class="statusColors[batch.status]"
                >
                  {{ statusLabels[batch.status] || batch.status }}
                </span>
              </td>
              <td class="px-4 py-3 text-sm text-gray-500">
                {{ formatDate(batch.created_at) }}
              </td>
              <td class="px-4 py-3 text-right">
                <div class="flex justify-end gap-2">
                  <button
                    v-if="batch.status === 'ready'"
                    class="btn btn-primary btn-sm"
                    @click="exportBatch(batch.id)"
                  >
                    Exportieren
                  </button>
                  <button
                    v-if="batch.status === 'exported'"
                    class="btn btn-success btn-sm"
                    @click="markBatchSent(batch.id)"
                  >
                    Als versendet markieren
                  </button>
                  <a
                    v-if="batch.export_path"
                    :href="`/uploads/${batch.export_path}`"
                    download
                    class="btn btn-secondary btn-sm"
                  >
                    Download CSV
                  </a>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Settings Tab -->
    <div
      v-if="activeTab === 'settings'"
      class="space-y-6"
    >
      <div class="rounded-lg bg-white p-6 shadow-sm">
        <h2 class="mb-1 text-lg font-semibold text-gray-900">
          Letterxpress-Zugangsdaten
        </h2>
        <p class="mb-4 text-sm text-gray-500">
          API-Zugang zu letterxpress.de. Test-Mode landet im Postfach (kein Druck/Versand,
          7 Tage Aufbewahrung). Live-Mode versendet sofort.
        </p>

        <div class="grid gap-4 sm:grid-cols-2">
          <div>
            <label class="block text-sm font-medium text-gray-700">Username</label>
            <input
              v-model="settingsForm.letterxpress_username"
              type="text"
              class="mt-1 block w-full rounded-md border border-gray-300 p-2 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              placeholder="LXPApi…"
            >
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700">
              API-Key
              <span
                v-if="settings?.apikey_set"
                class="ml-2 text-xs font-normal text-gray-400"
              >
                (gesetzt: {{ settings.apikey_masked }})
              </span>
            </label>
            <input
              v-model="settingsForm.letterxpress_apikey"
              type="password"
              autocomplete="new-password"
              class="mt-1 block w-full rounded-md border border-gray-300 p-2 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              placeholder="leer lassen, um den vorhandenen Key zu behalten"
            >
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700">Standard-Mode</label>
            <select
              v-model="settingsForm.letterxpress_default_mode"
              class="mt-1 block w-full rounded-md border border-gray-300 p-2 shadow-sm"
            >
              <option value="test">
                Test (Postbox, kein Druck)
              </option>
              <option value="live">
                Live (sofort versenden)
              </option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700">Standard-Farbe</label>
            <select
              v-model="settingsForm.letterxpress_default_color"
              class="mt-1 block w-full rounded-md border border-gray-300 p-2 shadow-sm"
            >
              <option value="1">
                Schwarz/Weiß
              </option>
              <option value="4">
                Vollfarbe (CMYK)
              </option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700">C4-Kuvert</label>
            <select
              v-model="settingsForm.letterxpress_c4_envelope"
              class="mt-1 block w-full rounded-md border border-gray-300 p-2 shadow-sm"
            >
              <option value="1">
                Ja (für längere Briefe)
              </option>
              <option value="0">
                Nein (Standard DL)
              </option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700">Versand</label>
            <select
              v-model="settingsForm.letterxpress_default_shipping"
              class="mt-1 block w-full rounded-md border border-gray-300 p-2 shadow-sm"
            >
              <option value="national">
                National
              </option>
              <option value="international">
                International
              </option>
              <option value="auto">
                Auto
              </option>
            </select>
          </div>
        </div>

        <div class="mt-6 flex items-center gap-3">
          <button
            class="btn btn-primary"
            :disabled="settingsBusy"
            @click="saveAllSettings"
          >
            Speichern
          </button>
          <button
            class="btn btn-secondary"
            :disabled="settingsBusy"
            @click="testConnection"
          >
            Verbindung testen
          </button>
          <span
            v-if="settingsMessage"
            class="text-sm"
            :class="settingsMessage.startsWith('Fehler') ? 'text-red-600' : 'text-green-700'"
          >
            {{ settingsMessage }}
          </span>
        </div>
      </div>

      <!-- Cost stats summary on settings tab -->
      <div
        v-if="costStats"
        class="rounded-lg bg-white p-6 shadow-sm"
      >
        <div class="mb-4 flex flex-wrap items-center gap-3">
          <h2 class="text-lg font-semibold text-gray-900">
            Kosten
          </h2>
          <select
            v-model="costPeriod"
            class="rounded border border-gray-300 px-2 py-1 text-sm"
            @change="store.fetchCostStats({ period: costPeriod, mode: costMode })"
          >
            <option value="today">
              Heute
            </option>
            <option value="week">
              7 Tage
            </option>
            <option value="month">
              30 Tage
            </option>
            <option value="all">
              Alle
            </option>
          </select>
          <select
            v-model="costMode"
            class="rounded border border-gray-300 px-2 py-1 text-sm"
            @change="store.fetchCostStats({ period: costPeriod, mode: costMode })"
          >
            <option value="all">
              Test + Live
            </option>
            <option value="live">
              Nur Live
            </option>
            <option value="test">
              Nur Test
            </option>
          </select>
        </div>
        <div class="grid gap-4 sm:grid-cols-3">
          <div class="rounded-md border border-gray-200 p-4">
            <div class="text-xs uppercase text-gray-500">
              Briefe
            </div>
            <div class="text-2xl font-bold">
              {{ costStats.count }}
            </div>
          </div>
          <div class="rounded-md border border-gray-200 p-4">
            <div class="text-xs uppercase text-gray-500">
              Kosten gesamt
            </div>
            <div class="text-2xl font-bold">
              {{ fmtEur(costStats.cost_cents) }}
            </div>
          </div>
          <div class="rounded-md border border-gray-200 p-4">
            <div class="text-xs uppercase text-gray-500">
              Pipelines
            </div>
            <div class="text-2xl font-bold">
              {{ costStats.by_pipeline?.length || 0 }}
            </div>
          </div>
        </div>

        <div
          v-if="costStats.by_pipeline?.length"
          class="mt-4"
        >
          <div class="mb-2 text-sm font-medium text-gray-700">
            Nach Pipeline
          </div>
          <table class="min-w-full text-sm">
            <thead class="bg-gray-50 text-xs uppercase text-gray-500">
              <tr>
                <th class="px-3 py-2 text-left">
                  Pipeline
                </th>
                <th class="px-3 py-2 text-right">
                  Anzahl
                </th>
                <th class="px-3 py-2 text-right">
                  Kosten
                </th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              <tr
                v-for="row in costStats.by_pipeline"
                :key="row.pipeline_id ?? 'none'"
              >
                <td class="px-3 py-2">
                  {{ row.pipeline_name || '— ohne Pipeline —' }}
                </td>
                <td class="px-3 py-2 text-right">
                  {{ row.count }}
                </td>
                <td class="px-3 py-2 text-right">
                  {{ fmtEur(row.cost_cents) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Create Letter Modal -->
    <div
      v-if="showCreateLetterModal"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      @click.self="showCreateLetterModal = false"
    >
      <div class="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl">
        <h2 class="mb-4 text-lg font-semibold">
          Neuer Brief
        </h2>
        <form
          class="space-y-4"
          @submit.prevent="createLetter"
        >
          <div>
            <label class="block text-sm font-medium text-gray-700">Template</label>
            <select
              v-model="newLetter.template_id"
              class="input mt-1 w-full"
              required
            >
              <option :value="null">
                Bitte wählen...
              </option>
              <option
                v-for="t in store.activeTemplates"
                :key="t.id"
                :value="t.id"
              >
                {{ t.name }}
              </option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700">Empfänger Name</label>
            <input
              v-model="newLetter.recipient.name"
              type="text"
              class="input mt-1 w-full"
              required
            >
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700">Firma</label>
            <input
              v-model="newLetter.recipient.company"
              type="text"
              class="input mt-1 w-full"
            >
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700">Straße</label>
              <input
                v-model="newLetter.recipient.street"
                type="text"
                class="input mt-1 w-full"
              >
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700">PLZ</label>
              <input
                v-model="newLetter.recipient.zip"
                type="text"
                class="input mt-1 w-full"
              >
            </div>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700">Stadt</label>
              <input
                v-model="newLetter.recipient.city"
                type="text"
                class="input mt-1 w-full"
              >
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700">Land</label>
              <input
                v-model="newLetter.recipient.country"
                type="text"
                class="input mt-1 w-full"
              >
            </div>
          </div>
          <div class="flex justify-end gap-3">
            <button
              type="button"
              class="btn btn-secondary"
              @click="showCreateLetterModal = false"
            >
              Abbrechen
            </button>
            <button
              type="submit"
              class="btn btn-primary"
              :disabled="store.loading"
            >
              Brief erstellen
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Create Template Modal -->
    <div
      v-if="showCreateTemplateModal"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      @click.self="showCreateTemplateModal = false"
    >
      <div class="w-full max-w-2xl rounded-lg bg-white p-6 shadow-xl">
        <h2 class="mb-4 text-lg font-semibold">
          Neues Template
        </h2>
        <form
          class="space-y-4"
          @submit.prevent="createTemplate"
        >
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700">Name</label>
              <input
                v-model="newTemplate.name"
                type="text"
                class="input mt-1 w-full"
                required
              >
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700">Format</label>
              <select
                v-model="newTemplate.format"
                class="input mt-1 w-full"
              >
                <option value="a4">
                  A4
                </option>
                <option value="us_letter">
                  US Letter
                </option>
                <option value="din_lang">
                  DIN Lang
                </option>
              </select>
            </div>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700">Beschreibung</label>
            <input
              v-model="newTemplate.description"
              type="text"
              class="input mt-1 w-full"
            >
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700">
              Inhalt (HTML)
              <span
                v-pre
                class="text-gray-400"
              >- Platzhalter: {{contact.name}}, {{contact.company}}</span>
            </label>
            <textarea
              v-model="newTemplate.content_html"
              rows="8"
              class="input mt-1 w-full font-mono text-sm"
              required
            />
          </div>
          <div class="flex justify-end gap-3">
            <button
              type="button"
              class="btn btn-secondary"
              @click="showCreateTemplateModal = false"
            >
              Abbrechen
            </button>
            <button
              type="submit"
              class="btn btn-primary"
              :disabled="store.loading"
            >
              Template erstellen
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Create Batch Modal -->
    <div
      v-if="showCreateBatchModal"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      @click.self="showCreateBatchModal = false"
    >
      <div class="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
        <h2 class="mb-4 text-lg font-semibold">
          Neuer Batch
        </h2>
        <form
          class="space-y-4"
          @submit.prevent="createBatch"
        >
          <div>
            <label class="block text-sm font-medium text-gray-700">Name</label>
            <input
              v-model="newBatch.name"
              type="text"
              class="input mt-1 w-full"
              placeholder="z.B. KW 12 - Solar Kampagne"
              required
            >
          </div>
          <div class="rounded-lg bg-gray-50 p-3">
            <p class="text-sm text-gray-600">
              {{ selectedLetterIds.length }} Briefe ausgewählt
            </p>
          </div>
          <div class="flex justify-end gap-3">
            <button
              type="button"
              class="btn btn-secondary"
              @click="showCreateBatchModal = false"
            >
              Abbrechen
            </button>
            <button
              type="submit"
              class="btn btn-primary"
              :disabled="store.loading || selectedLetterIds.length === 0"
            >
              Batch erstellen
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Preview Modal -->
    <div
      v-if="showPreviewModal"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      @click.self="showPreviewModal = false"
    >
      <div class="h-[80vh] w-full max-w-3xl overflow-auto rounded-lg bg-white p-6 shadow-xl">
        <div class="mb-4 flex items-center justify-between">
          <h2 class="text-lg font-semibold">
            Template-Vorschau
          </h2>
          <button
            class="text-gray-400 hover:text-gray-600"
            @click="showPreviewModal = false"
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
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>
        <div
          class="prose max-w-none rounded border border-gray-200 bg-white p-8"
          v-html="previewContent"
        />
      </div>
    </div>
  </div>
</template>
