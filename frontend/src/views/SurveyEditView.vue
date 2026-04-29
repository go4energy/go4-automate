<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useSurveysStore } from '@/stores/surveys'
import PageHeader from '@/components/ui/PageHeader.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'

const props = defineProps({
  id: { type: [String, Number], required: true }
})

const router = useRouter()
const store = useSurveysStore()

const activeTab = ref('questions')
const showQuestionModal = ref(false)
const showDeleteConfirm = ref(false)
const questionToEdit = ref(null)
const questionToDelete = ref(null)
const formLoading = ref(false)

const questionTypes = [
  { value: 'single_choice', label: 'Einfachauswahl' },
  { value: 'multiple_choice', label: 'Mehrfachauswahl' },
  { value: 'text', label: 'Kurztext' },
  { value: 'textarea', label: 'Langtext' },
  { value: 'scale', label: 'Skala' },
  { value: 'nps', label: 'NPS (0-10)' },
  { value: 'yes_no', label: 'Ja/Nein' },
  { value: 'rating', label: 'Bewertung (Sterne)' }
]

const defaultQuestion = {
  question_type: 'single_choice',
  title: '',
  description: '',
  required: false,
  options: [''],
  settings: {}
}

const questionForm = ref({ ...defaultQuestion })
const surveyForm = ref({
  title: '',
  description: '',
  survey_type: 'general',
  anonymous: true,
  show_progress: true,
  primary_color: '#FF6600',
  background_color: '#FFFFFF',
  thank_you_title: 'Vielen Dank!',
  thank_you_message: '',
  webhook_url: '',
  webhook_on_complete: false
})

const survey = computed(() => store.currentSurvey)
const questions = computed(() => store.questions)

const needsOptions = computed(() => {
  return ['single_choice', 'multiple_choice'].includes(questionForm.value.question_type)
})

onMounted(async () => {
  await store.fetchSurvey(props.id)
  if (survey.value) {
    surveyForm.value = {
      title: survey.value.title,
      description: survey.value.description || '',
      survey_type: survey.value.survey_type,
      anonymous: survey.value.anonymous,
      show_progress: survey.value.show_progress,
      primary_color: survey.value.primary_color,
      background_color: survey.value.background_color,
      thank_you_title: survey.value.thank_you_title,
      thank_you_message: survey.value.thank_you_message || '',
      webhook_url: survey.value.webhook_url || '',
      webhook_on_complete: survey.value.webhook_on_complete
    }
  }
})

function openAddQuestion() {
  questionToEdit.value = null
  questionForm.value = { ...defaultQuestion, options: [''] }
  showQuestionModal.value = true
}

function openEditQuestion(question) {
  questionToEdit.value = question
  questionForm.value = {
    question_type: question.question_type,
    title: question.title,
    description: question.description || '',
    required: question.required,
    options: question.options?.length ? [...question.options] : [''],
    settings: question.settings || {}
  }
  showQuestionModal.value = true
}

function addOption() {
  questionForm.value.options.push('')
}

function removeOption(index) {
  if (questionForm.value.options.length > 1) {
    questionForm.value.options.splice(index, 1)
  }
}

async function saveQuestion() {
  if (!questionForm.value.title.trim()) return

  formLoading.value = true
  try {
    const data = {
      ...questionForm.value,
      options: needsOptions.value ? questionForm.value.options.filter((o) => o.trim()) : null
    }

    if (questionToEdit.value) {
      await store.editQuestion(questionToEdit.value.id, data)
    } else {
      await store.addQuestion(props.id, data)
    }
    showQuestionModal.value = false
  } finally {
    formLoading.value = false
  }
}

function confirmDeleteQuestion(question) {
  questionToDelete.value = question
  showDeleteConfirm.value = true
}

async function deleteQuestion() {
  if (!questionToDelete.value) return

  try {
    await store.removeQuestion(questionToDelete.value.id)
    showDeleteConfirm.value = false
    questionToDelete.value = null
  } catch {
    // Error is in store
  }
}

async function saveSurvey() {
  formLoading.value = true
  try {
    await store.editSurvey(props.id, surveyForm.value)
  } finally {
    formLoading.value = false
  }
}

function goBack() {
  router.push(`/surveys/${props.id}`)
}

async function moveQuestion(index, direction) {
  const newIndex = direction === 'up' ? index - 1 : index + 1
  if (newIndex < 0 || newIndex >= questions.value.length) return

  const ids = questions.value.map((q) => q.id)
  const temp = ids[index]
  ids[index] = ids[newIndex]
  ids[newIndex] = temp

  await store.reorder(props.id, ids)
}
</script>

<template>
  <div class="bg-go4-bg dark:bg-gray-900">
    <PageHeader
      :title="`${survey?.title || 'Laden...'} bearbeiten`"
    >
      <template #actions>
        <button
          class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
          @click="goBack"
        >
          Zurueck
        </button>
      </template>
    </PageHeader>

    <div class="sm: lg:">
      <!-- Tabs -->
      <div class="mb-6 border-b border-gray-200 dark:border-gray-700">
        <nav class="-mb-px flex gap-6">
          <button
            class="border-b-2 px-1 py-3 text-sm font-medium transition-colors"
            :class="
              activeTab === 'questions'
                ? 'border-go4-primary text-go4-primary'
                : 'border-transparent text-go4-muted hover:text-go4-secondary dark:text-gray-400 dark:hover:text-gray-200'
            "
            @click="activeTab = 'questions'"
          >
            Fragen ({{ questions.length }})
          </button>
          <button
            class="border-b-2 px-1 py-3 text-sm font-medium transition-colors"
            :class="
              activeTab === 'settings'
                ? 'border-go4-primary text-go4-primary'
                : 'border-transparent text-go4-muted hover:text-go4-secondary dark:text-gray-400 dark:hover:text-gray-200'
            "
            @click="activeTab = 'settings'"
          >
            Einstellungen
          </button>
          <button
            class="border-b-2 px-1 py-3 text-sm font-medium transition-colors"
            :class="
              activeTab === 'design'
                ? 'border-go4-primary text-go4-primary'
                : 'border-transparent text-go4-muted hover:text-go4-secondary dark:text-gray-400 dark:hover:text-gray-200'
            "
            @click="activeTab = 'design'"
          >
            Design
          </button>
          <button
            class="border-b-2 px-1 py-3 text-sm font-medium transition-colors"
            :class="
              activeTab === 'webhook'
                ? 'border-go4-primary text-go4-primary'
                : 'border-transparent text-go4-muted hover:text-go4-secondary dark:text-gray-400 dark:hover:text-gray-200'
            "
            @click="activeTab = 'webhook'"
          >
            Webhook
          </button>
        </nav>
      </div>

      <!-- Loading -->
      <div
        v-if="store.loading && !survey"
        class="flex items-center justify-center py-12"
      >
        <span class="text-go4-muted dark:text-gray-400">Laden...</span>
      </div>

      <!-- Questions Tab -->
      <div
        v-else-if="activeTab === 'questions'"
        class="space-y-4"
      >
        <div class="flex justify-end">
          <button
            class="flex items-center gap-2 rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark"
            @click="openAddQuestion"
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
            Frage hinzufuegen
          </button>
        </div>

        <!-- Questions List -->
        <div class="space-y-3">
          <div
            v-for="(question, index) in questions"
            :key="question.id"
            class="flex items-center gap-3 rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
          >
            <!-- Reorder -->
            <div class="flex flex-col gap-1">
              <button
                :disabled="index === 0"
                class="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 disabled:opacity-30 dark:hover:bg-gray-700"
                @click="moveQuestion(index, 'up')"
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
                    d="M5 15l7-7 7 7"
                  />
                </svg>
              </button>
              <button
                :disabled="index === questions.length - 1"
                class="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 disabled:opacity-30 dark:hover:bg-gray-700"
                @click="moveQuestion(index, 'down')"
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
                    d="M19 9l-7 7-7-7"
                  />
                </svg>
              </button>
            </div>

            <!-- Content -->
            <div class="flex-1">
              <div class="flex items-center gap-2">
                <span class="text-sm font-medium text-go4-muted dark:text-gray-400">{{ index + 1 }}.</span>
                <h3 class="font-medium text-go4-secondary dark:text-white">
                  {{ question.title }}
                </h3>
                <span
                  v-if="question.required"
                  class="text-xs text-red-500"
                >*</span>
              </div>
              <div class="mt-1 flex items-center gap-2 text-sm text-go4-muted dark:text-gray-400">
                <span class="rounded bg-gray-100 px-1.5 py-0.5 text-xs dark:bg-gray-700">
                  {{ questionTypes.find((t) => t.value === question.question_type)?.label }}
                </span>
                <span v-if="question.options?.length">
                  {{ question.options.length }} Optionen
                </span>
              </div>
            </div>

            <!-- Actions -->
            <div class="flex gap-1">
              <button
                class="rounded p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700"
                @click="openEditQuestion(question)"
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
                class="rounded p-2 text-gray-400 hover:bg-red-100 hover:text-red-600 dark:hover:bg-red-900/30"
                @click="confirmDeleteQuestion(question)"
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

        <div
          v-if="questions.length === 0"
          class="rounded-lg border-2 border-dashed border-gray-300 bg-white p-8 text-center dark:border-gray-600 dark:bg-gray-800"
        >
          <p class="text-go4-muted dark:text-gray-400">
            Noch keine Fragen. Fuege deine erste Frage hinzu.
          </p>
          <button
            class="mt-4 rounded-lg bg-go4-primary px-4 py-2 text-sm text-white hover:bg-go4-primary-dark"
            @click="openAddQuestion"
          >
            Frage hinzufuegen
          </button>
        </div>
      </div>

      <!-- Settings Tab -->
      <div
        v-else-if="activeTab === 'settings'"
        class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800"
      >
        <form
          class="space-y-4"
          @submit.prevent="saveSurvey"
        >
          <div>
            <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
              Titel
            </label>
            <input
              v-model="surveyForm.title"
              type="text"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            >
          </div>

          <div>
            <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
              Beschreibung
            </label>
            <textarea
              v-model="surveyForm.description"
              rows="2"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            />
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div class="flex items-center gap-2">
              <input
                id="anonymous"
                v-model="surveyForm.anonymous"
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

            <div class="flex items-center gap-2">
              <input
                id="show_progress"
                v-model="surveyForm.show_progress"
                type="checkbox"
                class="h-4 w-4 rounded border-gray-300 text-go4-primary"
              >
              <label
                for="show_progress"
                class="text-sm text-go4-secondary dark:text-gray-200"
              >
                Fortschritt anzeigen
              </label>
            </div>
          </div>

          <div>
            <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
              Danke-Titel
            </label>
            <input
              v-model="surveyForm.thank_you_title"
              type="text"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            >
          </div>

          <div>
            <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
              Danke-Nachricht
            </label>
            <textarea
              v-model="surveyForm.thank_you_message"
              rows="2"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            />
          </div>

          <div class="flex justify-end pt-4">
            <button
              type="submit"
              class="rounded-lg bg-go4-primary px-4 py-2 text-sm text-white hover:bg-go4-primary-dark disabled:opacity-50"
              :disabled="formLoading"
            >
              {{ formLoading ? 'Speichern...' : 'Speichern' }}
            </button>
          </div>
        </form>
      </div>

      <!-- Design Tab -->
      <div
        v-else-if="activeTab === 'design'"
        class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800"
      >
        <form
          class="space-y-4"
          @submit.prevent="saveSurvey"
        >
          <div>
            <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
              Primaerfarbe
            </label>
            <input
              v-model="surveyForm.primary_color"
              type="color"
              class="h-10 w-20 rounded border border-gray-300"
            >
          </div>

          <div>
            <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
              Hintergrundfarbe
            </label>
            <input
              v-model="surveyForm.background_color"
              type="color"
              class="h-10 w-20 rounded border border-gray-300"
            >
          </div>

          <div class="flex justify-end pt-4">
            <button
              type="submit"
              class="rounded-lg bg-go4-primary px-4 py-2 text-sm text-white hover:bg-go4-primary-dark disabled:opacity-50"
              :disabled="formLoading"
            >
              {{ formLoading ? 'Speichern...' : 'Speichern' }}
            </button>
          </div>
        </form>
      </div>

      <!-- Webhook Tab -->
      <div
        v-else-if="activeTab === 'webhook'"
        class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800"
      >
        <form
          class="space-y-4"
          @submit.prevent="saveSurvey"
        >
          <div>
            <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
              Webhook URL (n8n)
            </label>
            <input
              v-model="surveyForm.webhook_url"
              type="url"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              placeholder="https://n8n.example.com/webhook/..."
            >
          </div>

          <div class="flex items-center gap-2">
            <input
              id="webhook_on_complete"
              v-model="surveyForm.webhook_on_complete"
              type="checkbox"
              class="h-4 w-4 rounded border-gray-300 text-go4-primary"
            >
            <label
              for="webhook_on_complete"
              class="text-sm text-go4-secondary dark:text-gray-200"
            >
              Bei Abschluss triggern
            </label>
          </div>

          <div class="flex justify-end pt-4">
            <button
              type="submit"
              class="rounded-lg bg-go4-primary px-4 py-2 text-sm text-white hover:bg-go4-primary-dark disabled:opacity-50"
              :disabled="formLoading"
            >
              {{ formLoading ? 'Speichern...' : 'Speichern' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Question Modal -->
    <Teleport to="body">
      <div
        v-if="showQuestionModal"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
        @click.self="showQuestionModal = false"
      >
        <div
          class="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800"
        >
          <h2 class="mb-4 text-lg font-semibold text-go4-secondary dark:text-white">
            {{ questionToEdit ? 'Frage bearbeiten' : 'Neue Frage' }}
          </h2>

          <form
            class="space-y-4"
            @submit.prevent="saveQuestion"
          >
            <div>
              <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                Fragetyp
              </label>
              <select
                v-model="questionForm.question_type"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
                <option
                  v-for="type in questionTypes"
                  :key="type.value"
                  :value="type.value"
                >
                  {{ type.label }}
                </option>
              </select>
            </div>

            <div>
              <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                Frage *
              </label>
              <input
                v-model="questionForm.title"
                type="text"
                required
                class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                placeholder="Wie zufrieden sind Sie mit unserem Service?"
              >
            </div>

            <div>
              <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                Beschreibung (optional)
              </label>
              <textarea
                v-model="questionForm.description"
                rows="2"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                placeholder="Zusaetzliche Erlaeuterung"
              />
            </div>

            <!-- Options for choice questions -->
            <div v-if="needsOptions">
              <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                Antwortoptionen
              </label>
              <div class="space-y-2">
                <div
                  v-for="(option, index) in questionForm.options"
                  :key="index"
                  class="flex gap-2"
                >
                  <input
                    v-model="questionForm.options[index]"
                    type="text"
                    class="flex-1 rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                    :placeholder="`Option ${index + 1}`"
                  >
                  <button
                    v-if="questionForm.options.length > 1"
                    type="button"
                    class="rounded p-2 text-gray-400 hover:bg-red-100 hover:text-red-600"
                    @click="removeOption(index)"
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
              </div>
              <button
                type="button"
                class="mt-2 text-sm text-go4-primary hover:underline"
                @click="addOption"
              >
                + Option hinzufuegen
              </button>
            </div>

            <div class="flex items-center gap-2">
              <input
                id="required"
                v-model="questionForm.required"
                type="checkbox"
                class="h-4 w-4 rounded border-gray-300 text-go4-primary"
              >
              <label
                for="required"
                class="text-sm text-go4-secondary dark:text-gray-200"
              >
                Pflichtfrage
              </label>
            </div>

            <div class="flex justify-end gap-3 pt-4">
              <button
                type="button"
                class="rounded-lg px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
                @click="showQuestionModal = false"
              >
                Abbrechen
              </button>
              <button
                type="submit"
                class="rounded-lg bg-go4-primary px-4 py-2 text-sm text-white hover:bg-go4-primary-dark disabled:opacity-50"
                :disabled="formLoading || !questionForm.title.trim()"
              >
                {{ formLoading ? 'Speichern...' : 'Speichern' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Delete Confirmation -->
    <ConfirmDialog
      :open="showDeleteConfirm"
      title="Frage loeschen?"
      :message="`Moechtest du die Frage '${questionToDelete?.title}' wirklich loeschen?`"
      confirm-text="Loeschen"
      variant="danger"
      @confirm="deleteQuestion"
      @cancel="showDeleteConfirm = false"
    />
  </div>
</template>
