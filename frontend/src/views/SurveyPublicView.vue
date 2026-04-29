<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api'

const route = useRoute()
const slug = computed(() => route.params.slug)

const survey = ref(null)
const loading = ref(true)
const error = ref(null)
const currentPage = ref(1)
const answers = ref({})
const responseToken = ref(null)
const submitting = ref(false)
const completed = ref(false)
const thankYouData = ref(null)

const currentQuestions = computed(() => {
  if (!survey.value?.questions) return []
  return survey.value.questions.filter((q) => q.page === currentPage.value)
})

const totalPages = computed(() => {
  if (!survey.value?.questions) return 1
  return Math.max(...survey.value.questions.map((q) => q.page || 1))
})

const progress = computed(() => {
  if (totalPages.value <= 1) return 100
  return Math.round(((currentPage.value - 1) / totalPages.value) * 100)
})

const canProceed = computed(() => {
  const required = currentQuestions.value.filter((q) => q.required)
  return required.every((q) => answers.value[q.id] !== undefined && answers.value[q.id] !== '')
})

onMounted(async () => {
  await loadSurvey()
})

async function loadSurvey() {
  loading.value = true
  error.value = null
  try {
    const { data } = await api.get(`/v1/surveys/public/${slug.value}`)
    survey.value = data
    await startResponse()
  } catch (err) {
    error.value = err.response?.data?.detail || 'Umfrage nicht gefunden'
  } finally {
    loading.value = false
  }
}

async function startResponse() {
  try {
    const { data } = await api.post(`/v1/surveys/public/${slug.value}/start`)
    responseToken.value = data.token
  } catch (err) {
    console.error('Failed to start response:', err)
  }
}

function setAnswer(questionId, value) {
  answers.value[questionId] = value
}

function toggleMultiAnswer(questionId, option) {
  if (!answers.value[questionId]) {
    answers.value[questionId] = []
  }
  const idx = answers.value[questionId].indexOf(option)
  if (idx === -1) {
    answers.value[questionId].push(option)
  } else {
    answers.value[questionId].splice(idx, 1)
  }
}

async function nextPage() {
  // Save current answers
  await saveCurrentAnswers()

  if (currentPage.value < totalPages.value) {
    currentPage.value++
    window.scrollTo(0, 0)
  } else {
    await submitSurvey()
  }
}

function prevPage() {
  if (currentPage.value > 1) {
    currentPage.value--
    window.scrollTo(0, 0)
  }
}

async function saveCurrentAnswers() {
  if (!responseToken.value) return

  for (const q of currentQuestions.value) {
    const value = answers.value[q.id]
    if (value === undefined) continue

    const answerData = { question_id: q.id }

    if (Array.isArray(value)) {
      answerData.value_list = value
    } else if (typeof value === 'number') {
      answerData.value_number = value
    } else if (typeof value === 'boolean') {
      answerData.value_bool = value
    } else {
      answerData.value_text = String(value)
    }

    try {
      await api.post(
        `/v1/surveys/public/${slug.value}/answer?token=${responseToken.value}`,
        answerData
      )
    } catch (err) {
      console.error('Failed to save answer:', err)
    }
  }
}

async function submitSurvey() {
  if (!responseToken.value) return

  submitting.value = true
  try {
    const { data } = await api.post(
      `/v1/surveys/public/${slug.value}/complete?token=${responseToken.value}`
    )
    thankYouData.value = data
    completed.value = true

    if (data.redirect_url) {
      setTimeout(() => {
        window.location.href = data.redirect_url
      }, 3000)
    }
  } catch (err) {
    error.value = err.response?.data?.detail || 'Fehler beim Absenden'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div
    :style="{ backgroundColor: survey?.background_color || '#f9fafb' }"
  >
    <!-- Loading -->
    <div
      v-if="loading"
      class="flex min-h-screen items-center justify-center"
    >
      <div class="text-center">
        <div
          class="mb-4 h-8 w-8 animate-spin rounded-full border-4 border-gray-300 border-t-gray-600"
        />
        <p class="text-gray-600">
          Umfrage wird geladen...
        </p>
      </div>
    </div>

    <!-- Error -->
    <div
      v-else-if="error"
      class="flex min-h-screen items-center justify-center p-4"
    >
      <div class="max-w-md rounded-lg bg-white p-8 text-center shadow-lg">
        <svg
          class="mx-auto mb-4 h-16 w-16 text-red-500"
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
        <h2 class="mb-2 text-xl font-bold text-gray-800">
          {{ error }}
        </h2>
        <p class="text-gray-600">
          Die Umfrage ist nicht verfuegbar.
        </p>
      </div>
    </div>

    <!-- Completed -->
    <div
      v-else-if="completed"
      class="flex min-h-screen items-center justify-center p-4"
    >
      <div class="max-w-md rounded-lg bg-white p-8 text-center shadow-lg">
        <svg
          class="mx-auto mb-4 h-16 w-16 text-green-500"
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
        <h2
          class="mb-2 text-2xl font-bold"
          :style="{ color: survey?.primary_color }"
        >
          {{ thankYouData?.thank_you_title || 'Vielen Dank!' }}
        </h2>
        <p
          v-if="thankYouData?.thank_you_message"
          class="text-gray-600"
        >
          {{ thankYouData.thank_you_message }}
        </p>
        <p
          v-if="thankYouData?.redirect_url"
          class="mt-4 text-sm text-gray-500"
        >
          Sie werden in Kuerze weitergeleitet...
        </p>
      </div>
    </div>

    <!-- Survey -->
    <div
      v-else-if="survey"
      class="mx-auto max-w-2xl px-4 py-8"
    >
      <!-- Header -->
      <div class="mb-8 text-center">
        <img
          v-if="survey.logo_url"
          :src="survey.logo_url"
          alt="Logo"
          class="mx-auto mb-4 h-16"
        >
        <h1
          class="text-2xl font-bold"
          :style="{ color: survey.primary_color }"
        >
          {{ survey.title }}
        </h1>
        <p
          v-if="survey.description"
          class="mt-2 text-gray-600"
        >
          {{ survey.description }}
        </p>
      </div>

      <!-- Progress -->
      <div
        v-if="survey.show_progress && totalPages > 1"
        class="mb-6"
      >
        <div class="mb-1 flex justify-between text-sm text-gray-500">
          <span>Seite {{ currentPage }} von {{ totalPages }}</span>
          <span>{{ progress }}%</span>
        </div>
        <div class="h-2 w-full rounded-full bg-gray-200">
          <div
            class="h-2 rounded-full transition-all"
            :style="{ width: `${progress}%`, backgroundColor: survey.primary_color }"
          />
        </div>
      </div>

      <!-- Questions -->
      <div class="space-y-6">
        <div
          v-for="question in currentQuestions"
          :key="question.id"
          class="rounded-lg bg-white p-6 shadow"
        >
          <div class="mb-4">
            <h3 class="text-lg font-medium text-gray-800">
              {{ question.title }}
              <span
                v-if="question.required"
                class="text-red-500"
              >*</span>
            </h3>
            <p
              v-if="question.description"
              class="mt-1 text-sm text-gray-500"
            >
              {{ question.description }}
            </p>
          </div>

          <!-- Single Choice -->
          <div
            v-if="question.question_type === 'single_choice'"
            class="space-y-2"
          >
            <label
              v-for="option in question.options"
              :key="option"
              class="flex cursor-pointer items-center gap-3 rounded-lg border p-3 transition-colors hover:bg-gray-50"
              :class="{ 'border-2': answers[question.id] === option }"
              :style="answers[question.id] === option ? { borderColor: survey.primary_color } : {}"
            >
              <input
                type="radio"
                :name="`q_${question.id}`"
                :value="option"
                class="h-4 w-4"
                :style="{ accentColor: survey.primary_color }"
                @change="setAnswer(question.id, option)"
              >
              <span>{{ option }}</span>
            </label>
          </div>

          <!-- Multiple Choice -->
          <div
            v-else-if="question.question_type === 'multiple_choice'"
            class="space-y-2"
          >
            <label
              v-for="option in question.options"
              :key="option"
              class="flex cursor-pointer items-center gap-3 rounded-lg border p-3 transition-colors hover:bg-gray-50"
              :class="{ 'border-2': answers[question.id]?.includes(option) }"
              :style="
                answers[question.id]?.includes(option) ? { borderColor: survey.primary_color } : {}
              "
            >
              <input
                type="checkbox"
                :checked="answers[question.id]?.includes(option)"
                class="h-4 w-4"
                :style="{ accentColor: survey.primary_color }"
                @change="toggleMultiAnswer(question.id, option)"
              >
              <span>{{ option }}</span>
            </label>
          </div>

          <!-- Text -->
          <div v-else-if="question.question_type === 'text'">
            <input
              type="text"
              :value="answers[question.id]"
              class="w-full rounded-lg border px-4 py-2 focus:outline-none focus:ring-2"
              :style="{ '--tw-ring-color': survey.primary_color }"
              :placeholder="question.settings?.placeholder || ''"
              @input="setAnswer(question.id, $event.target.value)"
            >
          </div>

          <!-- Textarea -->
          <div v-else-if="question.question_type === 'textarea'">
            <textarea
              :value="answers[question.id]"
              rows="4"
              class="w-full rounded-lg border px-4 py-2 focus:outline-none focus:ring-2"
              :style="{ '--tw-ring-color': survey.primary_color }"
              :placeholder="question.settings?.placeholder || ''"
              @input="setAnswer(question.id, $event.target.value)"
            />
          </div>

          <!-- Scale / NPS -->
          <div v-else-if="question.question_type === 'scale' || question.question_type === 'nps'">
            <div class="flex justify-between gap-1">
              <button
                v-for="n in question.question_type === 'nps'
                  ? 11
                  : (question.settings?.max_value || 10) - (question.settings?.min_value || 0) + 1"
                :key="n"
                type="button"
                class="flex-1 rounded-lg border py-3 text-center font-medium transition-colors"
                :class="
                  answers[question.id] ===
                    (question.question_type === 'nps'
                      ? n - 1
                      : (question.settings?.min_value || 0) + n - 1)
                    ? 'text-white'
                    : 'hover:bg-gray-50'
                "
                :style="
                  answers[question.id] ===
                    (question.question_type === 'nps'
                      ? n - 1
                      : (question.settings?.min_value || 0) + n - 1)
                    ? { backgroundColor: survey.primary_color }
                    : {}
                "
                @click="
                  setAnswer(
                    question.id,
                    question.question_type === 'nps'
                      ? n - 1
                      : (question.settings?.min_value || 0) + n - 1
                  )
                "
              >
                {{
                  question.question_type === 'nps'
                    ? n - 1
                    : (question.settings?.min_value || 0) + n - 1
                }}
              </button>
            </div>
            <div
              v-if="question.settings?.min_label || question.settings?.max_label"
              class="mt-2 flex justify-between text-sm text-gray-500"
            >
              <span>{{ question.settings?.min_label }}</span>
              <span>{{ question.settings?.max_label }}</span>
            </div>
          </div>

          <!-- Yes/No -->
          <div
            v-else-if="question.question_type === 'yes_no'"
            class="flex gap-4"
          >
            <button
              type="button"
              class="flex-1 rounded-lg border py-3 font-medium transition-colors"
              :class="answers[question.id] === true ? 'text-white' : 'hover:bg-gray-50'"
              :style="
                answers[question.id] === true ? { backgroundColor: survey.primary_color } : {}
              "
              @click="setAnswer(question.id, true)"
            >
              Ja
            </button>
            <button
              type="button"
              class="flex-1 rounded-lg border py-3 font-medium transition-colors"
              :class="answers[question.id] === false ? 'text-white' : 'hover:bg-gray-50'"
              :style="
                answers[question.id] === false ? { backgroundColor: survey.primary_color } : {}
              "
              @click="setAnswer(question.id, false)"
            >
              Nein
            </button>
          </div>

          <!-- Rating (Stars) -->
          <div
            v-else-if="question.question_type === 'rating'"
            class="flex gap-2"
          >
            <button
              v-for="n in 5"
              :key="n"
              type="button"
              class="text-3xl transition-transform hover:scale-110"
              :style="{ color: answers[question.id] >= n ? survey.primary_color : '#d1d5db' }"
              @click="setAnswer(question.id, n)"
            >
              ★
            </button>
          </div>
        </div>
      </div>

      <!-- Navigation -->
      <div class="mt-8 flex justify-between">
        <button
          v-if="currentPage > 1"
          type="button"
          class="rounded-lg border px-6 py-2 font-medium text-gray-600 hover:bg-gray-50"
          @click="prevPage"
        >
          Zurueck
        </button>
        <div v-else />

        <button
          type="button"
          class="rounded-lg px-8 py-2 font-medium text-white transition-colors disabled:opacity-50"
          :style="{ backgroundColor: survey.primary_color }"
          :disabled="!canProceed || submitting"
          @click="nextPage"
        >
          <span v-if="submitting">Wird gesendet...</span>
          <span v-else-if="currentPage < totalPages">Weiter</span>
          <span v-else>Absenden</span>
        </button>
      </div>
    </div>
  </div>
</template>
