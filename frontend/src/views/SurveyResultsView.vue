<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useSurveysStore } from '@/stores/surveys'
import PageHeader from '@/components/ui/PageHeader.vue'

const props = defineProps({
  id: { type: [String, Number], required: true }
})

const router = useRouter()
const store = useSurveysStore()

const activeTab = ref('overview')

const survey = computed(() => store.currentSurvey)
const stats = computed(() => store.stats)
const responses = computed(() => store.responses)

const npsColor = computed(() => {
  if (!stats.value?.nps) return 'text-gray-500'
  const score = stats.value.nps.score
  if (score >= 50) return 'text-green-600'
  if (score >= 0) return 'text-yellow-600'
  return 'text-red-600'
})

onMounted(async () => {
  await Promise.all([
    store.fetchSurvey(props.id),
    store.fetchStats(props.id),
    store.fetchResponses(props.id)
  ])
})

function goBack() {
  router.push(`/surveys/${props.id}`)
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

function formatDuration(seconds) {
  if (!seconds) return '-'
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
}
</script>

<template>
  <div class="bg-go4-bg dark:bg-gray-900">
    <PageHeader
      :title="`Ergebnisse: ${survey?.title || 'Laden...'}`"
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
              activeTab === 'overview'
                ? 'border-go4-primary text-go4-primary'
                : 'border-transparent text-go4-muted hover:text-go4-secondary dark:text-gray-400 dark:hover:text-gray-200'
            "
            @click="activeTab = 'overview'"
          >
            Uebersicht
          </button>
          <button
            class="border-b-2 px-1 py-3 text-sm font-medium transition-colors"
            :class="
              activeTab === 'questions'
                ? 'border-go4-primary text-go4-primary'
                : 'border-transparent text-go4-muted hover:text-go4-secondary dark:text-gray-400 dark:hover:text-gray-200'
            "
            @click="activeTab = 'questions'"
          >
            Fragen
          </button>
          <button
            class="border-b-2 px-1 py-3 text-sm font-medium transition-colors"
            :class="
              activeTab === 'responses'
                ? 'border-go4-primary text-go4-primary'
                : 'border-transparent text-go4-muted hover:text-go4-secondary dark:text-gray-400 dark:hover:text-gray-200'
            "
            @click="activeTab = 'responses'"
          >
            Antworten ({{ responses.length }})
          </button>
        </nav>
      </div>

      <!-- Loading -->
      <div
        v-if="store.loading"
        class="flex items-center justify-center py-12"
      >
        <span class="text-go4-muted dark:text-gray-400">Laden...</span>
      </div>

      <!-- Overview Tab -->
      <div
        v-else-if="activeTab === 'overview' && stats"
        class="space-y-6"
      >
        <!-- Stats Cards -->
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-4">
          <div
            class="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
          >
            <div class="text-2xl font-bold text-go4-secondary dark:text-white">
              {{ stats.total_responses }}
            </div>
            <div class="text-sm text-go4-muted dark:text-gray-400">
              Gesamt
            </div>
          </div>
          <div
            class="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
          >
            <div class="text-2xl font-bold text-go4-secondary dark:text-white">
              {{ stats.completed_responses }}
            </div>
            <div class="text-sm text-go4-muted dark:text-gray-400">
              Abgeschlossen
            </div>
          </div>
          <div
            class="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
          >
            <div class="text-2xl font-bold text-go4-secondary dark:text-white">
              {{ stats.completion_rate.toFixed(1) }}%
            </div>
            <div class="text-sm text-go4-muted dark:text-gray-400">
              Abschlussrate
            </div>
          </div>
          <div
            class="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
          >
            <div class="text-2xl font-bold text-go4-secondary dark:text-white">
              {{ formatDuration(stats.avg_completion_time) }}
            </div>
            <div class="text-sm text-go4-muted dark:text-gray-400">
              Ø Dauer
            </div>
          </div>
        </div>

        <!-- NPS Card -->
        <div
          v-if="stats.nps"
          class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800"
        >
          <h3 class="mb-4 text-lg font-medium text-go4-secondary dark:text-white">
            Net Promoter Score
          </h3>
          <div class="flex items-center gap-8">
            <div class="text-center">
              <div
                class="text-5xl font-bold"
                :class="npsColor"
              >
                {{ stats.nps.score }}
              </div>
              <div class="text-sm text-go4-muted dark:text-gray-400">
                NPS
              </div>
            </div>
            <div class="flex-1 space-y-2">
              <div class="flex items-center gap-2">
                <div class="w-24 text-sm text-go4-muted dark:text-gray-400">
                  Promoter
                </div>
                <div class="flex-1 rounded-full bg-gray-200 dark:bg-gray-700">
                  <div
                    class="h-4 rounded-full bg-green-500"
                    :style="{ width: `${stats.nps.promoter_percentage}%` }"
                  />
                </div>
                <div class="w-16 text-right text-sm">
                  {{ stats.nps.promoters }} ({{ stats.nps.promoter_percentage.toFixed(0) }}%)
                </div>
              </div>
              <div class="flex items-center gap-2">
                <div class="w-24 text-sm text-go4-muted dark:text-gray-400">
                  Passive
                </div>
                <div class="flex-1 rounded-full bg-gray-200 dark:bg-gray-700">
                  <div
                    class="h-4 rounded-full bg-yellow-500"
                    :style="{ width: `${stats.nps.passive_percentage}%` }"
                  />
                </div>
                <div class="w-16 text-right text-sm">
                  {{ stats.nps.passives }} ({{ stats.nps.passive_percentage.toFixed(0) }}%)
                </div>
              </div>
              <div class="flex items-center gap-2">
                <div class="w-24 text-sm text-go4-muted dark:text-gray-400">
                  Detractor
                </div>
                <div class="flex-1 rounded-full bg-gray-200 dark:bg-gray-700">
                  <div
                    class="h-4 rounded-full bg-red-500"
                    :style="{ width: `${stats.nps.detractor_percentage}%` }"
                  />
                </div>
                <div class="w-16 text-right text-sm">
                  {{ stats.nps.detractors }} ({{ stats.nps.detractor_percentage.toFixed(0) }}%)
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Questions Tab -->
      <div
        v-else-if="activeTab === 'questions' && stats"
        class="space-y-4"
      >
        <div
          v-for="q in stats.questions"
          :key="q.question_id"
          class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800"
        >
          <div class="mb-4 flex items-start justify-between">
            <h3 class="font-medium text-go4-secondary dark:text-white">
              {{ q.question_title }}
            </h3>
            <span
              class="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600 dark:bg-gray-700 dark:text-gray-300"
            >
              {{ q.total_answers }} Antworten
            </span>
          </div>

          <!-- Option counts (choice questions) -->
          <div
            v-if="q.option_counts"
            class="space-y-2"
          >
            <div
              v-for="(count, option) in q.option_counts"
              :key="option"
              class="flex items-center gap-2"
            >
              <div class="w-1/3 truncate text-sm text-go4-muted dark:text-gray-400">
                {{ option }}
              </div>
              <div class="flex-1 rounded-full bg-gray-200 dark:bg-gray-700">
                <div
                  class="h-4 rounded-full bg-go4-primary"
                  :style="{ width: `${(count / q.total_answers) * 100}%` }"
                />
              </div>
              <div class="w-16 text-right text-sm">
                {{ count }} ({{ ((count / q.total_answers) * 100).toFixed(0) }}%)
              </div>
            </div>
          </div>

          <!-- Numeric stats (scale/rating) -->
          <div
            v-else-if="q.average !== null"
            class="flex items-center gap-8"
          >
            <div class="text-center">
              <div class="text-3xl font-bold text-go4-secondary dark:text-white">
                {{ q.average.toFixed(1) }}
              </div>
              <div class="text-sm text-go4-muted dark:text-gray-400">
                Durchschnitt
              </div>
            </div>
            <div class="text-sm text-go4-muted dark:text-gray-400">
              Min: {{ q.min_value }} | Max: {{ q.max_value }}
            </div>
          </div>

          <!-- Distribution (if available) -->
          <div
            v-if="q.distribution"
            class="mt-4 flex items-end gap-1"
          >
            <div
              v-for="(count, value) in q.distribution"
              :key="value"
              class="flex flex-1 flex-col items-center"
            >
              <div
                class="w-full rounded-t bg-go4-primary"
                :style="{ height: `${(count / q.total_answers) * 100}px` }"
              />
              <div class="mt-1 text-xs text-go4-muted dark:text-gray-400">
                {{ value }}
              </div>
            </div>
          </div>
        </div>

        <div
          v-if="stats.questions.length === 0"
          class="rounded-lg border border-gray-200 bg-white p-8 text-center dark:border-gray-700 dark:bg-gray-800"
        >
          <p class="text-go4-muted dark:text-gray-400">
            Keine Fragenstatistiken verfuegbar.
          </p>
        </div>
      </div>

      <!-- Responses Tab -->
      <div
        v-else-if="activeTab === 'responses'"
        class="rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800"
      >
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead class="bg-gray-50 dark:bg-gray-900">
              <tr>
                <th
                  class="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-go4-muted dark:text-gray-400"
                >
                  ID
                </th>
                <th
                  class="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-go4-muted dark:text-gray-400"
                >
                  Status
                </th>
                <th
                  class="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-go4-muted dark:text-gray-400"
                >
                  Gestartet
                </th>
                <th
                  class="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-go4-muted dark:text-gray-400"
                >
                  Abgeschlossen
                </th>
                <th
                  class="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-go4-muted dark:text-gray-400"
                >
                  Dauer
                </th>
                <th
                  v-if="survey?.survey_type === 'nps'"
                  class="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-go4-muted dark:text-gray-400"
                >
                  NPS
                </th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
              <tr
                v-for="response in responses"
                :key="response.id"
              >
                <td class="whitespace-nowrap px-4 py-3 text-sm text-go4-secondary dark:text-white">
                  #{{ response.id }}
                </td>
                <td class="whitespace-nowrap px-4 py-3">
                  <span
                    class="rounded-full px-2 py-0.5 text-xs font-medium"
                    :class="{
                      'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300':
                        response.status === 'completed',
                      'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-300':
                        response.status === 'started',
                      'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300':
                        response.status === 'abandoned'
                    }"
                  >
                    {{ response.status }}
                  </span>
                </td>
                <td class="whitespace-nowrap px-4 py-3 text-sm text-go4-muted dark:text-gray-400">
                  {{ formatDate(response.started_at) }}
                </td>
                <td class="whitespace-nowrap px-4 py-3 text-sm text-go4-muted dark:text-gray-400">
                  {{ formatDate(response.completed_at) }}
                </td>
                <td class="whitespace-nowrap px-4 py-3 text-sm text-go4-muted dark:text-gray-400">
                  {{ formatDuration(response.duration_seconds) }}
                </td>
                <td
                  v-if="survey?.survey_type === 'nps'"
                  class="whitespace-nowrap px-4 py-3 text-sm"
                >
                  <span
                    v-if="response.nps_score !== null"
                    class="font-medium"
                    :class="{
                      'text-green-600': response.nps_category === 'promoter',
                      'text-yellow-600': response.nps_category === 'passive',
                      'text-red-600': response.nps_category === 'detractor'
                    }"
                  >
                    {{ response.nps_score }}
                  </span>
                  <span
                    v-else
                    class="text-gray-400"
                  >-</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div
          v-if="responses.length === 0"
          class="p-8 text-center text-go4-muted dark:text-gray-400"
        >
          Noch keine Antworten.
        </div>
      </div>
    </div>
  </div>
</template>
