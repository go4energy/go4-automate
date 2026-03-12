<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useLinkedInStore } from '@/stores/linkedin'
import { useEngagementStore } from '@/stores/engagement'
import { usePipelineContext } from '@/stores/pipelineContext'
import PageHeader from '@/components/ui/PageHeader.vue'

const props = defineProps({
  id: { type: [String, Number], default: null }
})

const route = useRoute()
const router = useRouter()
const store = useLinkedInStore()
const engagementStore = useEngagementStore()
const pipelineCtx = usePipelineContext()

const jobId = computed(() => props.id || route.params.id)
const isEdit = computed(() => !!jobId.value)
const isFirstDegreePreset = computed(() => route.query.preset === '1st-degree')

const loading = ref(false)
const saving = ref(false)
const error = ref(null)

const formData = ref({
  name: '',
  account_id: null,
  pipeline_id: null,
  auto_enroll_pipeline: false,
  job_type: 'profile_list',
  search_url: '',
  profile_urls_text: '',
  connections_since_date: null,
  max_profiles: 100,
  profiles_scraped: 0,
  daily_limit: 2500,
  delay_seconds: 5,
  // Schedule settings
  schedule_enabled: false,
  schedule_days: [0, 1, 2, 3, 4], // Mo-Fr default
  schedule_start_time: '08:00',
  schedule_end_time: '18:00'
})

const weekdays = [
  { value: 0, label: 'Mo' },
  { value: 1, label: 'Di' },
  { value: 2, label: 'Mi' },
  { value: 3, label: 'Do' },
  { value: 4, label: 'Fr' },
  { value: 5, label: 'Sa' },
  { value: 6, label: 'So' }
]

function toggleDay(day) {
  const idx = formData.value.schedule_days.indexOf(day)
  if (idx >= 0) {
    formData.value.schedule_days.splice(idx, 1)
  } else {
    formData.value.schedule_days.push(day)
    formData.value.schedule_days.sort((a, b) => a - b)
  }
}

onMounted(async () => {
  await Promise.all([store.fetchAccounts(), engagementStore.fetchPipelines()])

  if (isEdit.value) {
    loading.value = true
    try {
      const job = await store.fetchJob(jobId.value)
      formData.value = {
        name: job.name,
        account_id: job.account_id,
        pipeline_id: job.pipeline_id,
        auto_enroll_pipeline: job.auto_enroll_pipeline || false,
        job_type: job.job_type,
        search_url: job.search_url || '',
        profile_urls_text: (job.profile_urls || []).join('\n'),
        max_profiles: job.max_profiles || 100,
        profiles_scraped: job.profiles_scraped || 0,
        daily_limit: job.daily_limit || 2500,
        delay_seconds: job.min_delay_seconds || 5,
        // Schedule settings
        schedule_enabled: job.schedule_enabled || false,
        schedule_days: job.schedule_days || [0, 1, 2, 3, 4],
        schedule_start_time: job.schedule_start_time || '08:00',
        schedule_end_time: job.schedule_end_time || '18:00'
      }
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  } else {
    if (store.accounts.length > 0) {
      formData.value.account_id = store.accounts[0].id
    }
    // Pre-select active pipeline from context
    if (pipelineCtx.activePipelineId) {
      formData.value.pipeline_id = pipelineCtx.activePipelineId
      formData.value.auto_enroll_pipeline = true
    }
    // Preset: 1st-degree connections (uses regular LinkedIn, no Sales Navigator)
    if (route.query.preset === '1st-degree') {
      formData.value.name = 'Meine Kontakte (1. Grad)'
      formData.value.job_type = 'connections'
      formData.value.daily_limit = 2500
      formData.value.delay_seconds = 3
      formData.value.schedule_enabled = true
      formData.value.schedule_days = [0, 1, 2, 3, 4]
      formData.value.schedule_start_time = '06:00'
      formData.value.schedule_end_time = '23:00'
    }
  }
})

async function save() {
  if (!formData.value.name.trim()) {
    error.value = 'Name ist erforderlich'
    return
  }

  if (!formData.value.account_id) {
    error.value = 'Account ist erforderlich'
    return
  }

  saving.value = true
  error.value = null

  try {
    const data = {
      name: formData.value.name,
      account_id: formData.value.account_id,
      pipeline_id: formData.value.pipeline_id,
      auto_enroll_pipeline: formData.value.auto_enroll_pipeline,
      job_type: formData.value.job_type,
      max_profiles: formData.value.max_profiles,
      profiles_scraped: formData.value.profiles_scraped,
      daily_limit: formData.value.daily_limit,
      min_delay_seconds: formData.value.delay_seconds,
      // Schedule settings
      schedule_enabled: formData.value.schedule_enabled,
      schedule_days: formData.value.schedule_enabled ? formData.value.schedule_days : null,
      schedule_start_time: formData.value.schedule_enabled
        ? formData.value.schedule_start_time
        : null,
      schedule_end_time: formData.value.schedule_enabled ? formData.value.schedule_end_time : null
    }

    if (formData.value.job_type === 'search') {
      data.search_url = formData.value.search_url
    } else if (formData.value.job_type === 'profile_list') {
      data.profile_urls = formData.value.profile_urls_text
        .split('\n')
        .map((u) => u.trim())
        .filter((u) => u.length > 0)
    } else if (formData.value.job_type === 'connections') {
      if (formData.value.connections_since_date) {
        data.connections_since_date = formData.value.connections_since_date
      }
    }

    if (isEdit.value) {
      await store.editJob(jobId.value, data)
      router.push(`/linkedin/jobs/${jobId.value}`)
    } else {
      const job = await store.addJob(data)
      router.push(`/linkedin/jobs/${job.id}`)
    }
  } catch (err) {
    const detail = err.response?.data?.detail
    if (Array.isArray(detail)) {
      error.value = detail.map((e) => e.msg || e.message || JSON.stringify(e)).join(', ')
    } else {
      error.value = detail || err.message || 'Fehler beim Speichern des Jobs'
    }
  } finally {
    saving.value = false
  }
}

function cancel() {
  if (isEdit.value) {
    router.push(`/linkedin/jobs/${jobId.value}`)
  } else {
    router.push('/linkedin')
  }
}
</script>

<template>
  <div class="min-h-screen bg-go4-bg dark:bg-gray-900">
    <PageHeader
      :title="isEdit ? 'Job bearbeiten' : 'Neuer Scraper Job'"
      subtitle="LinkedIn Sales Navigator Scraping"
    >
      <template #actions>
        <button
          class="rounded-lg px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
          @click="cancel"
        >
          Abbrechen
        </button>
        <button
          class="rounded-lg bg-go4-primary px-4 py-2 text-sm text-white hover:bg-go4-primary-dark disabled:opacity-50"
          :disabled="saving"
          @click="save"
        >
          {{ saving ? 'Speichern...' : 'Speichern' }}
        </button>
      </template>
    </PageHeader>

    <div class="mx-auto max-w-3xl px-4 py-6 sm:px-6 lg:px-8">
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

      <!-- Form -->
      <div
        v-if="!loading"
        class="space-y-6"
      >
        <!-- Basic Info -->
        <div
          class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800"
        >
          <h3 class="mb-4 font-medium text-go4-secondary dark:text-white">
            Grundeinstellungen
          </h3>

          <div class="space-y-4">
            <!-- Name -->
            <div>
              <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                Job-Name *
              </label>
              <input
                v-model="formData.name"
                type="text"
                required
                class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                placeholder="z.B. Marketing Manager DACH"
              >
            </div>

            <!-- Account -->
            <div>
              <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                LinkedIn Account *
              </label>
              <select
                v-model="formData.account_id"
                required
                class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
                <option
                  :value="null"
                  disabled
                >
                  Account waehlen...
                </option>
                <option
                  v-for="account in store.accounts"
                  :key="account.id"
                  :value="account.id"
                >
                  {{ account.name }} ({{ account.email }})
                </option>
              </select>
            </div>

            <!-- Pipeline -->
            <div>
              <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                Produkt-Pipeline
              </label>
              <select
                v-model="formData.pipeline_id"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
                <option :value="null">
                  Keine Pipeline
                </option>
                <option
                  v-for="pipeline in engagementStore.activePipelines"
                  :key="pipeline.id"
                  :value="pipeline.id"
                >
                  {{ pipeline.name }}
                </option>
              </select>
              <p class="mt-1 text-xs text-go4-muted dark:text-gray-400">
                Gescrapte Kontakte werden dieser Pipeline zugeordnet
              </p>
            </div>

            <!-- Auto-Enroll in Pipeline -->
            <div
              v-if="formData.pipeline_id"
              class="flex items-start gap-3 rounded-lg bg-go4-primary/5 p-3 dark:bg-go4-primary/10"
            >
              <input
                id="auto_enroll_pipeline"
                v-model="formData.auto_enroll_pipeline"
                type="checkbox"
                class="mt-0.5 h-4 w-4 rounded border-gray-300 text-go4-primary"
              >
              <div>
                <label
                  for="auto_enroll_pipeline"
                  class="text-sm font-medium text-go4-secondary dark:text-gray-200"
                >
                  Auto-Enrollment aktivieren
                </label>
                <p class="text-xs text-go4-muted dark:text-gray-400">
                  Gescrapte Kontakte werden automatisch als zentrale Kontakte importiert und in die Pipeline enrolled. Das Brain uebernimmt dann die Steuerung.
                </p>
              </div>
            </div>

          </div>
        </div>

        <!-- Source -->
        <div
          class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800"
        >
          <h3 class="mb-4 font-medium text-go4-secondary dark:text-white">
            Datenquelle
          </h3>

          <div class="space-y-4">
            <!-- Job Type -->
            <div>
              <label class="mb-2 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                Job-Typ
              </label>
              <div class="flex gap-4">
                <label class="flex cursor-pointer items-center gap-2">
                  <input
                    v-model="formData.job_type"
                    type="radio"
                    value="profile_list"
                    class="h-4 w-4 text-go4-primary"
                  >
                  <span class="text-sm text-go4-secondary dark:text-gray-200">Profil-URLs</span>
                </label>
                <label class="flex cursor-pointer items-center gap-2">
                  <input
                    v-model="formData.job_type"
                    type="radio"
                    value="connections"
                    class="h-4 w-4 text-go4-primary"
                  >
                  <span class="text-sm text-go4-secondary dark:text-gray-200">Meine Kontakte (1. Grad)</span>
                </label>
                <label class="flex cursor-pointer items-center gap-2">
                  <input
                    v-model="formData.job_type"
                    type="radio"
                    value="search"
                    class="h-4 w-4 text-go4-primary"
                  >
                  <span class="text-sm text-go4-secondary dark:text-gray-200">Sales Navigator Suche</span>
                </label>
              </div>
            </div>

            <!-- Search URL -->
            <div v-if="formData.job_type === 'search'">
              <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                Sales Navigator Such-URL
              </label>
              <input
                v-model="formData.search_url"
                type="url"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                placeholder="https://www.linkedin.com/sales/search/people?..."
              >
              <p class="mt-1 text-xs text-go4-muted dark:text-gray-400">
                Oeffne Sales Navigator, erstelle eine Suche und kopiere die URL
              </p>
            </div>

            <!-- Connections (1st degree) -->
            <div v-if="formData.job_type === 'connections'">
              <div class="rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-700 dark:border-green-800 dark:bg-green-900/20 dark:text-green-400">
                Liest alle 1. Grad Kontakte von deiner LinkedIn-Seite. Kein Sales Navigator noetig. Pro Kontakt werden Profil-Details und Kontaktinformationen (E-Mail, Telefon etc.) abgerufen.
              </div>
              <div class="mt-4">
                <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                  Kontakte ab Datum (optional)
                </label>
                <input
                  v-model="formData.connections_since_date"
                  type="date"
                  class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                >
                <p class="mt-1 text-xs text-go4-muted dark:text-gray-400">
                  Nur Kontakte lesen, die nach diesem Datum hinzugefuegt wurden. Leer = alle Kontakte.
                </p>
              </div>
            </div>

            <!-- Profile URLs -->
            <div v-if="formData.job_type === 'profile_list'">
              <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                LinkedIn Profil-URLs (eine pro Zeile)
              </label>
              <textarea
                v-model="formData.profile_urls_text"
                rows="8"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                placeholder="https://www.linkedin.com/in/max-mustermann/
https://www.linkedin.com/in/erika-musterfrau/
..."
              />
              <p class="mt-1 text-xs text-go4-muted dark:text-gray-400">
                {{ formData.profile_urls_text.split('\n').filter((u) => u.trim()).length }} URLs
                eingetragen
              </p>
            </div>
          </div>
        </div>

        <!-- Limits -->
        <div
          class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800"
        >
          <h3 class="mb-4 font-medium text-go4-secondary dark:text-white">
            Limits & Geschwindigkeit
          </h3>

          <div class="grid gap-4 md:grid-cols-2">
            <!-- Max Profiles -->
            <div>
              <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                Max. Profile (gesamt)
              </label>
              <input
                v-model.number="formData.max_profiles"
                type="number"
                min="1"
                max="10000"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
              <p class="mt-1 text-xs text-go4-muted dark:text-gray-400">
                Job pausiert wenn erreicht
              </p>
            </div>

            <!-- Profiles Scraped (offset) -->
            <div>
              <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                Bereits abgearbeitet (Offset)
              </label>
              <input
                v-model.number="formData.profiles_scraped"
                type="number"
                min="0"
                max="10000"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
              <p class="mt-1 text-xs text-go4-muted dark:text-gray-400">
                Auf 0 setzen = von vorne beginnen
              </p>
            </div>

            <!-- Daily Limit -->
            <div>
              <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                Max. Profile pro Tag
              </label>
              <input
                v-model.number="formData.daily_limit"
                type="number"
                min="1"
                max="10000"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
            </div>

            <!-- Delay -->
            <div>
              <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                Verzoegerung zw. Seiten (Sek.)
              </label>
              <input
                v-model.number="formData.delay_seconds"
                type="number"
                min="1"
                max="300"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
            </div>
          </div>
        </div>

        <!-- Schedule Settings -->
        <div
          class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800"
        >
          <h3 class="mb-4 font-medium text-go4-secondary dark:text-white">
            Zeitplanung
          </h3>

          <div class="flex items-center gap-3">
            <input
              id="schedule_enabled"
              v-model="formData.schedule_enabled"
              type="checkbox"
              class="h-4 w-4 rounded border-gray-300 text-go4-primary"
            >
            <label
              for="schedule_enabled"
              class="text-sm text-go4-secondary dark:text-gray-200"
            >
              Automatisch nach Zeitplan ausfuehren
            </label>
          </div>

          <div
            v-if="formData.schedule_enabled"
            class="mt-4 space-y-4"
          >
            <!-- Days of Week -->
            <div>
              <label class="mb-2 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                Wochentage
              </label>
              <div class="flex flex-wrap gap-2">
                <button
                  v-for="day in weekdays"
                  :key="day.value"
                  type="button"
                  :class="[
                    'rounded-lg px-3 py-1.5 text-sm font-medium transition-colors',
                    formData.schedule_days.includes(day.value)
                      ? 'bg-go4-primary text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
                  ]"
                  @click="toggleDay(day.value)"
                >
                  {{ day.label }}
                </button>
              </div>
            </div>

            <!-- Time Range -->
            <div class="grid gap-4 md:grid-cols-2">
              <div>
                <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                  Startzeit
                </label>
                <input
                  v-model="formData.schedule_start_time"
                  type="time"
                  class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                >
              </div>
              <div>
                <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                  Endzeit
                </label>
                <input
                  v-model="formData.schedule_end_time"
                  type="time"
                  class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                >
              </div>
            </div>

          </div>

          <p
            v-if="formData.schedule_enabled"
            class="mt-4 rounded bg-blue-50 p-3 text-sm text-blue-700 dark:bg-blue-900/20 dark:text-blue-300"
          >
            Der Job wird im angegebenen Zeitraum automatisch fortgesetzt und pausiert, bis alle
            Seiten abgearbeitet sind.
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
