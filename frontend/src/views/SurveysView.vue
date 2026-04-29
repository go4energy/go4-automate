<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useSurveysStore } from '@/stores/surveys'
import PageHeader from '@/components/ui/PageHeader.vue'
import SearchInput from '@/components/ui/SearchInput.vue'
import CardGrid from '@/components/ui/CardGrid.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'

const router = useRouter()
const store = useSurveysStore()

const searchQuery = ref('')
const statusFilter = ref('')
const typeFilter = ref('')
const showCreateModal = ref(false)
const showDeleteConfirm = ref(false)
const surveyToDelete = ref(null)
const formData = ref({
  title: '',
  description: '',
  survey_type: 'general',
  anonymous: true,
  primary_color: '#FF6600'
})
const formLoading = ref(false)

const colors = [
  '#FF6600', // Orange (go4)
  '#10B981', // Green
  '#3B82F6', // Blue
  '#8B5CF6', // Purple
  '#EF4444', // Red
  '#EC4899', // Pink
  '#14B8A6', // Teal
  '#F59E0B' // Amber
]

const surveyTypes = [
  { value: 'general', label: 'Allgemein' },
  { value: 'nps', label: 'NPS' },
  { value: 'csat', label: 'CSAT' },
  { value: 'feedback', label: 'Feedback' }
]

const statusLabels = {
  draft: 'Entwurf',
  active: 'Aktiv',
  paused: 'Pausiert',
  closed: 'Beendet'
}

const statusColors = {
  draft: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
  active: 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300',
  paused: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-300',
  closed: 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300'
}

const filteredSurveys = computed(() => {
  let result = store.surveys

  if (statusFilter.value) {
    result = result.filter((s) => s.status === statusFilter.value)
  }

  if (typeFilter.value) {
    result = result.filter((s) => s.survey_type === typeFilter.value)
  }

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(
      (s) => s.title.toLowerCase().includes(query) || s.description?.toLowerCase().includes(query)
    )
  }

  return result
})

onMounted(async () => {
  await store.fetchSurveys()
})

function openSurvey(survey) {
  router.push(`/surveys/${survey.id}`)
}

function editSurvey(survey) {
  router.push(`/surveys/${survey.id}/edit`)
}

function viewResults(survey) {
  router.push(`/surveys/${survey.id}/results`)
}

function openCreateModal() {
  formData.value = {
    title: '',
    description: '',
    survey_type: 'general',
    anonymous: true,
    primary_color: '#FF6600'
  }
  showCreateModal.value = true
}

async function createSurvey() {
  if (!formData.value.title.trim()) return

  formLoading.value = true
  try {
    const survey = await store.addSurvey(formData.value)
    showCreateModal.value = false
    router.push(`/surveys/${survey.id}/edit`)
  } finally {
    formLoading.value = false
  }
}

function confirmDelete(survey) {
  surveyToDelete.value = survey
  showDeleteConfirm.value = true
}

async function deleteSurvey() {
  if (!surveyToDelete.value) return

  try {
    await store.removeSurvey(surveyToDelete.value.id)
    showDeleteConfirm.value = false
    surveyToDelete.value = null
  } catch {
    // Error is in store
  }
}

async function duplicateSurvey(survey) {
  try {
    const newSurvey = await store.duplicate(survey.id)
    router.push(`/surveys/${newSurvey.id}/edit`)
  } catch {
    // Error is in store
  }
}

async function toggleStatus(survey) {
  const newStatus = survey.status === 'active' ? 'paused' : 'active'
  await store.setStatus(survey.id, newStatus)
}
</script>

<template>
  <div class="bg-go4-bg dark:bg-gray-900">
    <PageHeader
      title="Umfragen"
    >
      <template #actions>
        <button
          class="flex items-center gap-2 rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark"
          @click="openCreateModal"
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
          Neue Umfrage
        </button>
      </template>
    </PageHeader>

    <div class="sm: lg:">
      <!-- Filters -->
      <div class="mb-6 flex flex-wrap items-center gap-4">
        <SearchInput
          v-model="searchQuery"
          placeholder="Suchen..."
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
          <option value="active">
            Aktiv
          </option>
          <option value="paused">
            Pausiert
          </option>
          <option value="closed">
            Beendet
          </option>
        </select>

        <select
          v-model="typeFilter"
          class="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
        >
          <option value="">
            Alle Typen
          </option>
          <option
            v-for="type in surveyTypes"
            :key="type.value"
            :value="type.value"
          >
            {{ type.label }}
          </option>
        </select>

        <!-- Stats -->
        <div class="ml-auto flex items-center gap-4 text-sm text-go4-muted dark:text-gray-400">
          <span>{{ filteredSurveys.length }} Umfragen</span>
          <span>{{ store.totalResponses }} Antworten</span>
        </div>
      </div>

      <!-- Loading -->
      <div
        v-if="store.loading"
        class="flex items-center justify-center py-12"
      >
        <span class="text-go4-muted dark:text-gray-400">Laden...</span>
      </div>

      <!-- Error -->
      <div
        v-else-if="store.error"
        class="rounded-lg bg-red-50 p-4 text-red-700 dark:bg-red-900/30 dark:text-red-300"
      >
        {{ store.error }}
      </div>

      <!-- Empty State -->
      <EmptyState
        v-else-if="filteredSurveys.length === 0"
        title="Keine Umfragen"
      >
        <button
          class="mt-4 rounded-lg bg-go4-primary px-4 py-2 text-sm text-white hover:bg-go4-primary-dark"
          @click="openCreateModal"
        >
          Umfrage erstellen
        </button>
      </EmptyState>

      <!-- Survey Grid -->
      <CardGrid
        v-else
        :columns="3"
      >
        <div
          v-for="survey in filteredSurveys"
          :key="survey.id"
          class="group relative rounded-lg border border-gray-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md dark:border-gray-700 dark:bg-gray-800"
        >
          <!-- Color indicator -->
          <div
            class="absolute left-0 top-0 h-1 w-full rounded-t-lg"
            :style="{ backgroundColor: survey.primary_color }"
          />

          <!-- Header -->
          <div class="mb-3 flex items-start justify-between pt-1">
            <div
              class="flex-1 cursor-pointer"
              @click="openSurvey(survey)"
            >
              <h3 class="font-medium text-go4-secondary dark:text-white">
                {{ survey.title }}
              </h3>
              <p
                v-if="survey.description"
                class="mt-1 line-clamp-2 text-sm text-go4-muted dark:text-gray-400"
              >
                {{ survey.description }}
              </p>
            </div>

            <!-- Actions -->
            <div class="ml-2 flex gap-1">
              <button
                class="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700 dark:hover:text-gray-300"
                title="Bearbeiten"
                @click="editSurvey(survey)"
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
                class="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700 dark:hover:text-gray-300"
                title="Duplizieren"
                @click="duplicateSurvey(survey)"
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
                    d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                  />
                </svg>
              </button>
              <button
                class="rounded p-1 text-gray-400 hover:bg-red-100 hover:text-red-600 dark:hover:bg-red-900/30 dark:hover:text-red-400"
                title="Loeschen"
                @click="confirmDelete(survey)"
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

          <!-- Status & Type -->
          <div class="mb-3 flex items-center gap-2">
            <span
              class="rounded-full px-2 py-0.5 text-xs font-medium"
              :class="statusColors[survey.status]"
            >
              {{ statusLabels[survey.status] }}
            </span>
            <span class="text-xs text-go4-muted dark:text-gray-500">
              {{
                surveyTypes.find((t) => t.value === survey.survey_type)?.label || survey.survey_type
              }}
            </span>
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
              <span>{{ survey.response_count || 0 }} Antworten</span>
            </div>
            <div
              v-if="survey.completion_rate !== null"
              class="flex items-center gap-1"
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
                  d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                />
              </svg>
              <span>{{ Math.round(survey.completion_rate) }}% fertig</span>
            </div>
          </div>

          <!-- Quick Actions -->
          <div class="mt-4 flex gap-2">
            <button
              v-if="survey.status === 'draft'"
              class="flex-1 rounded-lg border border-green-500 px-3 py-1.5 text-sm font-medium text-green-600 hover:bg-green-50 dark:text-green-400 dark:hover:bg-green-900/20"
              @click="store.setStatus(survey.id, 'active')"
            >
              Aktivieren
            </button>
            <button
              v-else-if="survey.status === 'active'"
              class="flex-1 rounded-lg border border-yellow-500 px-3 py-1.5 text-sm font-medium text-yellow-600 hover:bg-yellow-50 dark:text-yellow-400 dark:hover:bg-yellow-900/20"
              @click="store.setStatus(survey.id, 'paused')"
            >
              Pausieren
            </button>
            <button
              v-else-if="survey.status === 'paused'"
              class="flex-1 rounded-lg border border-green-500 px-3 py-1.5 text-sm font-medium text-green-600 hover:bg-green-50 dark:text-green-400 dark:hover:bg-green-900/20"
              @click="store.setStatus(survey.id, 'active')"
            >
              Fortsetzen
            </button>
            <button
              v-if="survey.response_count > 0"
              class="flex-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
              @click="viewResults(survey)"
            >
              Ergebnisse
            </button>
          </div>
        </div>
      </CardGrid>
    </div>

    <!-- Create Modal -->
    <Teleport to="body">
      <div
        v-if="showCreateModal"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
        @click.self="showCreateModal = false"
      >
        <div class="w-full max-w-md rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800">
          <h2 class="mb-4 text-lg font-semibold text-go4-secondary dark:text-white">
            Neue Umfrage
          </h2>

          <form
            class="space-y-4"
            @submit.prevent="createSurvey"
          >
            <div>
              <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                Titel *
              </label>
              <input
                v-model="formData.title"
                type="text"
                required
                class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                placeholder="z.B. Kundenzufriedenheit Q1"
              >
            </div>

            <div>
              <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                Beschreibung
              </label>
              <textarea
                v-model="formData.description"
                rows="2"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                placeholder="Optional"
              />
            </div>

            <div>
              <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                Typ
              </label>
              <select
                v-model="formData.survey_type"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
                <option
                  v-for="type in surveyTypes"
                  :key="type.value"
                  :value="type.value"
                >
                  {{ type.label }}
                </option>
              </select>
            </div>

            <div>
              <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                Farbe
              </label>
              <div class="flex gap-2">
                <button
                  v-for="color in colors"
                  :key="color"
                  type="button"
                  class="h-8 w-8 rounded-full border-2 transition-transform hover:scale-110"
                  :class="{
                    'border-gray-800 dark:border-white': formData.primary_color === color,
                    'border-transparent': formData.primary_color !== color
                  }"
                  :style="{ backgroundColor: color }"
                  @click="formData.primary_color = color"
                />
              </div>
            </div>

            <div class="flex items-center gap-2">
              <input
                id="anonymous"
                v-model="formData.anonymous"
                type="checkbox"
                class="h-4 w-4 rounded border-gray-300 text-go4-primary"
              >
              <label
                for="anonymous"
                class="text-sm text-go4-secondary dark:text-gray-200"
              >
                Anonyme Umfrage
              </label>
            </div>

            <div class="flex justify-end gap-3 pt-4">
              <button
                type="button"
                class="rounded-lg px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
                @click="showCreateModal = false"
              >
                Abbrechen
              </button>
              <button
                type="submit"
                class="rounded-lg bg-go4-primary px-4 py-2 text-sm text-white hover:bg-go4-primary-dark disabled:opacity-50"
                :disabled="formLoading || !formData.title.trim()"
              >
                {{ formLoading ? 'Erstellen...' : 'Erstellen' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Delete Confirmation -->
    <ConfirmDialog
      :open="showDeleteConfirm"
      title="Umfrage loeschen?"
      :message="`Moechtest du die Umfrage '${surveyToDelete?.title}' wirklich loeschen? Alle Antworten werden ebenfalls geloescht.`"
      confirm-text="Loeschen"
      variant="danger"
      @confirm="deleteSurvey"
      @cancel="showDeleteConfirm = false"
    />
  </div>
</template>
