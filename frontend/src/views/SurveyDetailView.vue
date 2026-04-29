<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSurveysStore } from '@/stores/surveys'
import PageHeader from '@/components/ui/PageHeader.vue'

const props = defineProps({
  id: { type: [String, Number], required: true }
})

const route = useRoute()
const router = useRouter()
const store = useSurveysStore()

const showShareModal = ref(false)
const linkCopied = ref(false)

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

const survey = computed(() => store.currentSurvey)
const questions = computed(() => store.questions)

onMounted(async () => {
  await store.fetchSurvey(props.id)
  await store.fetchShareLink(props.id)
})

function editSurvey() {
  router.push(`/surveys/${props.id}/edit`)
}

function viewResults() {
  router.push(`/surveys/${props.id}/results`)
}

async function copyLink() {
  if (store.shareLink?.url) {
    await navigator.clipboard.writeText(store.shareLink.url)
    linkCopied.value = true
    setTimeout(() => {
      linkCopied.value = false
    }, 2000)
  }
}

async function setStatus(status) {
  await store.setStatus(props.id, status)
}
</script>

<template>
  <div class="min-h-screen bg-go4-bg dark:bg-gray-900">
    <PageHeader
      :title="survey?.title || 'Laden...'"
    >
      <template #actions>
        <div class="flex items-center gap-2">
          <span
            v-if="survey"
            class="rounded-full px-3 py-1 text-sm font-medium"
            :class="statusColors[survey.status]"
          >
            {{ statusLabels[survey.status] }}
          </span>
          <button
            class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
            @click="showShareModal = true"
          >
            Teilen
          </button>
          <button
            class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark"
            @click="editSurvey"
          >
            Bearbeiten
          </button>
        </div>
      </template>
    </PageHeader>

    <div class="mx-auto max-w-5xl px-4 py-6 sm:px-6 lg:px-8">
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

      <div
        v-else-if="survey"
        class="space-y-6"
      >
        <!-- Stats Cards -->
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-4">
          <div
            class="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
          >
            <div class="text-2xl font-bold text-go4-secondary dark:text-white">
              {{ survey.response_count || 0 }}
            </div>
            <div class="text-sm text-go4-muted dark:text-gray-400">
              Antworten
            </div>
          </div>
          <div
            class="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
          >
            <div class="text-2xl font-bold text-go4-secondary dark:text-white">
              {{ survey.completion_rate ? Math.round(survey.completion_rate) : 0 }}%
            </div>
            <div class="text-sm text-go4-muted dark:text-gray-400">
              Abschlussrate
            </div>
          </div>
          <div
            class="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
          >
            <div class="text-2xl font-bold text-go4-secondary dark:text-white">
              {{ questions.length }}
            </div>
            <div class="text-sm text-go4-muted dark:text-gray-400">
              Fragen
            </div>
          </div>
          <div
            class="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
          >
            <div class="text-2xl font-bold text-go4-secondary dark:text-white">
              {{ survey.avg_completion_time ? Math.round(survey.avg_completion_time / 60) : '-' }}
            </div>
            <div class="text-sm text-go4-muted dark:text-gray-400">
              Ø Min. Dauer
            </div>
          </div>
        </div>

        <!-- Quick Actions -->
        <div class="flex gap-3">
          <button
            v-if="survey.status === 'draft'"
            class="rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700"
            @click="setStatus('active')"
          >
            Aktivieren
          </button>
          <button
            v-else-if="survey.status === 'active'"
            class="rounded-lg bg-yellow-500 px-4 py-2 text-sm font-medium text-white hover:bg-yellow-600"
            @click="setStatus('paused')"
          >
            Pausieren
          </button>
          <button
            v-else-if="survey.status === 'paused'"
            class="rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700"
            @click="setStatus('active')"
          >
            Fortsetzen
          </button>
          <button
            v-if="survey.response_count > 0"
            class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
            @click="viewResults"
          >
            Ergebnisse ansehen
          </button>
        </div>

        <!-- Questions Preview -->
        <div
          class="rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800"
        >
          <div class="border-b border-gray-200 px-6 py-4 dark:border-gray-700">
            <h2 class="text-lg font-medium text-go4-secondary dark:text-white">
              Fragen ({{ questions.length }})
            </h2>
          </div>
          <div class="divide-y divide-gray-200 dark:divide-gray-700">
            <div
              v-for="(question, index) in questions"
              :key="question.id"
              class="px-6 py-4"
            >
              <div class="flex items-start justify-between">
                <div>
                  <div class="flex items-center gap-2">
                    <span class="text-sm font-medium text-go4-muted dark:text-gray-400">
                      {{ index + 1 }}.
                    </span>
                    <h3 class="font-medium text-go4-secondary dark:text-white">
                      {{ question.title }}
                    </h3>
                    <span
                      v-if="question.required"
                      class="text-xs text-red-500"
                    >*</span>
                  </div>
                  <p
                    v-if="question.description"
                    class="mt-1 text-sm text-go4-muted dark:text-gray-400"
                  >
                    {{ question.description }}
                  </p>
                </div>
                <span
                  class="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600 dark:bg-gray-700 dark:text-gray-300"
                >
                  {{ question.question_type }}
                </span>
              </div>

              <!-- Options preview -->
              <div
                v-if="question.options?.length"
                class="mt-2 flex flex-wrap gap-2"
              >
                <span
                  v-for="option in question.options.slice(0, 5)"
                  :key="option"
                  class="rounded border border-gray-200 px-2 py-0.5 text-xs text-gray-600 dark:border-gray-600 dark:text-gray-400"
                >
                  {{ option }}
                </span>
                <span
                  v-if="question.options.length > 5"
                  class="text-xs text-go4-muted dark:text-gray-500"
                >
                  +{{ question.options.length - 5 }} weitere
                </span>
              </div>
            </div>
          </div>
          <div
            v-if="questions.length === 0"
            class="px-6 py-8 text-center text-go4-muted dark:text-gray-400"
          >
            Noch keine Fragen hinzugefuegt.
            <button
              class="ml-2 text-go4-primary hover:underline"
              @click="editSurvey"
            >
              Fragen hinzufuegen
            </button>
          </div>
        </div>

        <!-- Survey Settings -->
        <div
          class="rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800"
        >
          <div class="border-b border-gray-200 px-6 py-4 dark:border-gray-700">
            <h2 class="text-lg font-medium text-go4-secondary dark:text-white">
              Einstellungen
            </h2>
          </div>
          <div class="grid grid-cols-2 gap-4 p-6">
            <div>
              <span class="text-sm text-go4-muted dark:text-gray-400">Typ:</span>
              <span class="ml-2 text-go4-secondary dark:text-white">{{ survey.survey_type }}</span>
            </div>
            <div>
              <span class="text-sm text-go4-muted dark:text-gray-400">Anonym:</span>
              <span class="ml-2 text-go4-secondary dark:text-white">{{
                survey.anonymous ? 'Ja' : 'Nein'
              }}</span>
            </div>
            <div>
              <span class="text-sm text-go4-muted dark:text-gray-400">Fortschritt anzeigen:</span>
              <span class="ml-2 text-go4-secondary dark:text-white">{{
                survey.show_progress ? 'Ja' : 'Nein'
              }}</span>
            </div>
            <div>
              <span class="text-sm text-go4-muted dark:text-gray-400">Mehrfachteilnahme:</span>
              <span class="ml-2 text-go4-secondary dark:text-white">{{
                survey.allow_multiple_submissions ? 'Erlaubt' : 'Nicht erlaubt'
              }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Share Modal -->
    <Teleport to="body">
      <div
        v-if="showShareModal"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
        @click.self="showShareModal = false"
      >
        <div class="w-full max-w-md rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800">
          <h2 class="mb-4 text-lg font-semibold text-go4-secondary dark:text-white">
            Umfrage teilen
          </h2>

          <div class="space-y-4">
            <!-- Link -->
            <div>
              <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                Oeffentlicher Link
              </label>
              <div class="flex gap-2">
                <input
                  :value="store.shareLink?.url"
                  readonly
                  class="flex-1 rounded-lg border border-gray-300 bg-gray-50 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                >
                <button
                  class="rounded-lg bg-go4-primary px-4 py-2 text-sm text-white hover:bg-go4-primary-dark"
                  @click="copyLink"
                >
                  {{ linkCopied ? 'Kopiert!' : 'Kopieren' }}
                </button>
              </div>
            </div>

            <!-- QR Code -->
            <div v-if="store.shareLink?.qr_code_url">
              <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                QR-Code
              </label>
              <img
                :src="`/api${store.shareLink.qr_code_url}`"
                alt="QR Code"
                class="h-32 w-32 rounded-lg border border-gray-200 dark:border-gray-600"
              >
            </div>
          </div>

          <div class="mt-6 flex justify-end">
            <button
              class="rounded-lg px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
              @click="showShareModal = false"
            >
              Schliessen
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
