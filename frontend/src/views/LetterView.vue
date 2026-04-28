<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useLetterStore } from '@/stores/letter'
import PageHeader from '@/components/ui/PageHeader.vue'
import Breadcrumb from '@/components/ui/Breadcrumb.vue'
import EmptyState from '@/components/ui/EmptyState.vue'

const route = useRoute()
const router = useRouter()
const store = useLetterStore()

// Active tab from route
const activeTab = computed(() => route.meta?.tab || 'letters')

const tabs = [
  { key: 'letters', label: 'Briefe', route: '/letter' },
  { key: 'templates', label: 'Templates', route: '/letter/templates' },
  { key: 'batches', label: 'Batches', route: '/letter/batches' },
]

// Stats
const stats = computed(() => store.stats)

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

// Load data
async function loadData() {
  try {
    await Promise.all([
      store.fetchStats(),
      store.fetchLetters(),
      store.fetchTemplates(),
      store.fetchBatches(),
    ])
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

onMounted(() => {
  loadData()
})

// Reload when tab changes
watch(activeTab, () => {
  loadData()
})
</script>

<template>
  <div class="space-y-6">
    <Breadcrumb class="mb-4" />

    <PageHeader
      title="Post-Mail"
      description="Physische Briefe als Engagement-Kanal"
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
      class="grid grid-cols-2 gap-4 sm:grid-cols-4"
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
        <div class="text-sm text-gray-500">
          Offene Batches
        </div>
        <div class="text-2xl font-bold text-yellow-600">
          {{ stats.pending_batches }}
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
          description="Erstellen Sie Ihren ersten Brief."
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
          description="Erstellen Sie Ihr erstes Brief-Template."
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
          description="Wählen Sie genehmigte Briefe aus und erstellen Sie einen Batch."
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
