<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useEngagementStore } from '@/stores/engagement'
import PageHeader from '@/components/ui/PageHeader.vue'
import Breadcrumb from '@/components/ui/Breadcrumb.vue'
import PipelineSetupWizard from '@/components/engagement/PipelineSetupWizard.vue'

const props = defineProps({
  id: { type: [String, Number], default: null }
})

const route = useRoute()
const router = useRouter()
const store = useEngagementStore()

const pipelineId = computed(() => props.id || route.params.id)
const isEdit = computed(() => !!pipelineId.value)

const loading = ref(false)
const saving = ref(false)
const error = ref(null)
const showWizard = ref(false)

function handleWizardComplete(result) {
  showWizard.value = false

  if (result.fill_form && result.pipeline_config) {
    // Fill form with AI-generated config
    const config = result.pipeline_config
    formData.value = {
      name: config.name || formData.value.name,
      slug: config.slug || generateSlug(config.name || ''),
      product_name: config.product_name || formData.value.product_name,
      product_description: config.product_description || formData.value.product_description,
      target_audience: config.target_audience || formData.value.target_audience,
      channels: config.channels || formData.value.channels,
      goal: config.goal || formData.value.goal,
      tone_of_voice: config.tone_of_voice || formData.value.tone_of_voice,
      min_days_between_touches: config.min_days_between_touches || formData.value.min_days_between_touches,
      is_active: true,
      playbook: config.playbook || formData.value.playbook
    }
  } else if (result.pipeline) {
    // Pipeline was created by the wizard, redirect to detail
    router.push(`/engagement/pipelines/${result.pipeline.id}`)
  }
}

const formData = ref({
  name: '',
  slug: '',
  product_name: '',
  product_description: '',
  target_audience: '',
  channels: [],
  goal: '',
  tone_of_voice: 'professionell',
  min_days_between_touches: 3,
  is_active: true,
  playbook: '',
  tracking_config: {
    auto_create_tracking_hash: false,
    utm_source: '',
    utm_medium: '',
    utm_campaign: '',
    utm_term: '',
    utm_content: '',
    custom_params: {}
  }
})

// Custom-param row management — convert object to array of {key, value} for UI
const customParamRows = ref([])
function addCustomParam() {
  customParamRows.value.push({ key: '', value: '' })
}
function removeCustomParam(idx) {
  customParamRows.value.splice(idx, 1)
}
function syncCustomParamsToForm() {
  const obj = {}
  for (const row of customParamRows.value) {
    if (row.key) obj[row.key] = row.value
  }
  formData.value.tracking_config.custom_params = obj
}

const availableChannels = [
  { value: 'linkedin', label: 'LinkedIn' },
  { value: 'email', label: 'Email' },
  { value: 'phone', label: 'Telefon' },
  { value: 'letter', label: 'Brief' },
  { value: 'whatsapp', label: 'WhatsApp' }
]

const goalOptions = [
  { value: 'vor_ort_termin', label: 'Vor-Ort Termin' },
  { value: 'demo', label: 'Demo / Online-Praesentation' },
  { value: 'angebot', label: 'Angebot erstellen' },
  { value: 'verkauf', label: 'Direktverkauf' },
  { value: 'leads', label: 'Lead-Generierung' }
]

const toneOptions = [
  { value: 'professionell', label: 'Professionell' },
  { value: 'locker', label: 'Locker / Freundlich' },
  { value: 'technisch', label: 'Technisch' },
  { value: 'persoenlich', label: 'Persoenlich' }
]

function toggleChannel(channel) {
  const idx = formData.value.channels.indexOf(channel)
  if (idx >= 0) {
    formData.value.channels.splice(idx, 1)
  } else {
    formData.value.channels.push(channel)
  }
}

function generateSlug(name) {
  return name
    .toLowerCase()
    .replace(/[aeiou]/g, (c) => ({ ae: 'ae', oe: 'oe', ue: 'ue' })[c] || c)
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
}

function handleNameChange() {
  if (!isEdit.value && !formData.value.slug) {
    formData.value.slug = generateSlug(formData.value.name)
  }
}

onMounted(async () => {
  if (isEdit.value) {
    loading.value = true
    try {
      const pipeline = await store.fetchPipeline(pipelineId.value)
      const tc = pipeline.tracking_config || {}
      formData.value = {
        name: pipeline.name || '',
        slug: pipeline.slug || '',
        product_name: pipeline.product_name || '',
        product_description: pipeline.product_description || '',
        target_audience: pipeline.target_audience || '',
        channels: pipeline.channels || [],
        goal: pipeline.goal || '',
        tone_of_voice: pipeline.tone_of_voice || 'professionell',
        min_days_between_touches: pipeline.min_days_between_touches || 3,
        is_active: pipeline.is_active ?? true,
        playbook: pipeline.playbook || '',
        tracking_config: {
          auto_create_tracking_hash: tc.auto_create_tracking_hash ?? false,
          utm_source: tc.utm_source || '',
          utm_medium: tc.utm_medium || '',
          utm_campaign: tc.utm_campaign || '',
          utm_term: tc.utm_term || '',
          utm_content: tc.utm_content || '',
          custom_params: tc.custom_params || {}
        }
      }
      customParamRows.value = Object.entries(tc.custom_params || {}).map(
        ([key, value]) => ({ key, value })
      )
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }
})

async function save() {
  if (!formData.value.name.trim()) {
    error.value = 'Name ist erforderlich'
    return
  }
  if (!formData.value.slug.trim()) {
    error.value = 'Slug ist erforderlich'
    return
  }
  if (formData.value.channels.length === 0) {
    error.value = 'Mindestens ein Kanal muss ausgewaehlt werden'
    return
  }

  saving.value = true
  error.value = null

  try {
    syncCustomParamsToForm()
    const data = {
      name: formData.value.name,
      slug: formData.value.slug,
      product_name: formData.value.product_name || null,
      product_description: formData.value.product_description || null,
      target_audience: formData.value.target_audience || null,
      channels: formData.value.channels,
      goal: formData.value.goal || null,
      tone_of_voice: formData.value.tone_of_voice,
      min_days_between_touches: formData.value.min_days_between_touches,
      is_active: formData.value.is_active,
      playbook: formData.value.playbook || null,
      tracking_config: { ...formData.value.tracking_config }
    }

    if (isEdit.value) {
      await store.editPipeline(pipelineId.value, data)
    } else {
      await store.addPipeline(data)
    }

    router.push('/engagement/pipelines')
  } catch (err) {
    error.value = err.response?.data?.detail || err.message
  } finally {
    saving.value = false
  }
}

function cancel() {
  router.push('/engagement/pipelines')
}
</script>

<template>
  <div class="flex flex-1 flex-col overflow-hidden">
    <PageHeader
      :title="isEdit ? 'Pipeline bearbeiten' : 'Neue Pipeline'"
      :subtitle="isEdit ? formData.name : 'Engagement-Pipeline erstellen'"
    >
      <template #actions>
        <button
          v-if="!isEdit"
          class="flex items-center gap-2 rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark"
          @click="showWizard = true"
        >
          <svg
            class="h-4 w-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M13 10V3L4 14h7v7l9-11h-7z"
            />
          </svg>
          AI-Assistent
        </button>
      </template>
    </PageHeader>

    <Breadcrumb class="mx-4 mb-2" />

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

      <!-- Form -->
      <form
        v-else
        class="mx-auto max-w-3xl space-y-6"
        @submit.prevent="save"
      >
        <!-- Error -->
        <div
          v-if="error"
          class="rounded-lg bg-red-50 p-4 text-red-700 dark:bg-red-900/50 dark:text-red-300"
        >
          {{ error }}
        </div>

        <!-- Basic Info -->
        <div class="rounded-lg bg-white p-6 shadow dark:bg-gray-800">
          <h3 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">
            Grundinformationen
          </h3>

          <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <label class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                Name *
              </label>
              <input
                v-model="formData.name"
                type="text"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                placeholder="z.B. Solar KMU Pipeline"
                @blur="handleNameChange"
              >
            </div>

            <div>
              <label class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                Slug *
              </label>
              <input
                v-model="formData.slug"
                type="text"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                placeholder="z.B. solar-kmu"
              >
              <p class="mt-1 text-xs text-gray-500">
                Eindeutiger Identifier (keine Leerzeichen)
              </p>
            </div>

            <div class="md:col-span-2">
              <label class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                Produktname
              </label>
              <input
                v-model="formData.product_name"
                type="text"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                placeholder="z.B. Solaranlagen"
              >
            </div>

            <div class="md:col-span-2">
              <label class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                Produktbeschreibung
              </label>
              <textarea
                v-model="formData.product_description"
                rows="3"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                placeholder="Beschreiben Sie das Produkt/Service..."
              />
            </div>

            <div class="md:col-span-2">
              <label class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                Zielgruppe
              </label>
              <textarea
                v-model="formData.target_audience"
                rows="2"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                placeholder="z.B. KMU mit 10-50 Mitarbeitern in der Fertigungsindustrie"
              />
            </div>
          </div>
        </div>

        <!-- Channels -->
        <div class="rounded-lg bg-white p-6 shadow dark:bg-gray-800">
          <h3 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">
            Kanaele *
          </h3>
          <div class="flex flex-wrap gap-3">
            <button
              v-for="channel in availableChannels"
              :key="channel.value"
              type="button"
              class="rounded-lg border-2 px-4 py-2 text-sm font-medium transition-colors"
              :class="
                formData.channels.includes(channel.value)
                  ? 'border-go4-primary bg-go4-primary/10 text-go4-primary'
                  : 'border-gray-300 text-gray-700 hover:border-gray-400 dark:border-gray-600 dark:text-gray-300'
              "
              @click="toggleChannel(channel.value)"
            >
              {{ channel.label }}
            </button>
          </div>
          <p class="mt-2 text-sm text-gray-500">
            Waehlen Sie die Kanaele, ueber die Kontakte angesprochen werden sollen.
          </p>
        </div>

        <!-- Settings -->
        <div class="rounded-lg bg-white p-6 shadow dark:bg-gray-800">
          <h3 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">
            Einstellungen
          </h3>

          <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <label class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                Ziel
              </label>
              <select
                v-model="formData.goal"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
                <option value="">
                  Bitte waehlen
                </option>
                <option
                  v-for="option in goalOptions"
                  :key="option.value"
                  :value="option.value"
                >
                  {{ option.label }}
                </option>
              </select>
            </div>

            <div>
              <label class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                Tonalitaet
              </label>
              <select
                v-model="formData.tone_of_voice"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
                <option
                  v-for="option in toneOptions"
                  :key="option.value"
                  :value="option.value"
                >
                  {{ option.label }}
                </option>
              </select>
            </div>

            <div>
              <label class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                Min. Tage zwischen Touches
              </label>
              <input
                v-model.number="formData.min_days_between_touches"
                type="number"
                min="1"
                max="30"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
            </div>

            <div class="flex items-center">
              <label class="flex cursor-pointer items-center gap-3">
                <input
                  v-model="formData.is_active"
                  type="checkbox"
                  class="h-5 w-5 rounded border-gray-300 text-go4-primary focus:ring-go4-primary"
                >
                <span class="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Pipeline ist aktiv
                </span>
              </label>
            </div>
          </div>
        </div>

        <!-- Playbook -->
        <div class="rounded-lg bg-white p-6 shadow dark:bg-gray-800">
          <h3 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">
            Playbook
          </h3>
          <p class="mb-3 text-sm text-gray-500 dark:text-gray-400">
            Optionale Richtlinien fuer das Brain, wie Kontakte angesprochen werden sollen.
          </p>
          <textarea
            v-model="formData.playbook"
            rows="6"
            class="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            placeholder="z.B.
- Bei Erstansprache immer auf aktuelle Branchentrends verweisen
- Nach 2 erfolglosen Touches auf anderen Kanal wechseln
- Bei positiver Antwort sofort Termin vorschlagen
..."
          />
        </div>

        <!-- Tracking & Attribution -->
        <div class="rounded-lg bg-white p-6 shadow dark:bg-gray-800">
          <h3 class="mb-1 text-lg font-semibold text-gray-900 dark:text-white">
            Tracking & Attribution
          </h3>
          <p class="mb-4 text-sm text-gray-500 dark:text-gray-400">
            Beim Enrollment wird optional ein Tracking-Hash pro Kontakt erzeugt.
            UTM-Parameter werden in alle ausgehenden URLs (Briefe, Emails) der
            Pipeline injiziert.
          </p>

          <label class="mb-4 flex cursor-pointer items-center gap-3">
            <input
              v-model="formData.tracking_config.auto_create_tracking_hash"
              type="checkbox"
              class="h-5 w-5 rounded border-gray-300 text-go4-primary focus:ring-go4-primary"
            >
            <span class="text-sm font-medium text-gray-700 dark:text-gray-300">
              Hash pro Kontakt automatisch erstellen (beim Enrollment)
            </span>
          </label>

          <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <label class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">utm_source</label>
              <input
                v-model="formData.tracking_config.utm_source"
                type="text"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                placeholder="z.B. newsletter, brief, linkedin"
              >
            </div>
            <div>
              <label class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">utm_medium</label>
              <input
                v-model="formData.tracking_config.utm_medium"
                type="text"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                placeholder="z.B. email, mail, social"
              >
            </div>
            <div>
              <label class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">utm_campaign</label>
              <input
                v-model="formData.tracking_config.utm_campaign"
                type="text"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                placeholder="z.B. q2-2026"
              >
            </div>
            <div>
              <label class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">utm_term</label>
              <input
                v-model="formData.tracking_config.utm_term"
                type="text"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
            </div>
            <div class="md:col-span-2">
              <label class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">utm_content</label>
              <input
                v-model="formData.tracking_config.utm_content"
                type="text"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
            </div>
          </div>

          <!-- Custom params -->
          <div class="mt-6">
            <div class="mb-2 flex items-center justify-between">
              <label class="text-sm font-medium text-gray-700 dark:text-gray-300">
                Eigene Parameter
              </label>
              <button
                type="button"
                class="text-sm text-go4-primary hover:underline"
                @click="addCustomParam"
              >
                + Hinzufügen
              </button>
            </div>
            <div class="space-y-2">
              <div
                v-for="(row, idx) in customParamRows"
                :key="idx"
                class="grid grid-cols-[1fr_1fr_auto] gap-2"
              >
                <input
                  v-model="row.key"
                  type="text"
                  placeholder="key"
                  class="rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                >
                <input
                  v-model="row.value"
                  type="text"
                  placeholder="value"
                  class="rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                >
                <button
                  type="button"
                  class="px-2 text-red-500 hover:text-red-700"
                  @click="removeCustomParam(idx)"
                >
                  ×
                </button>
              </div>
              <p
                v-if="customParamRows.length === 0"
                class="text-xs text-gray-400"
              >
                Keine eigenen Parameter — UTM oben reicht für die meisten Fälle.
              </p>
            </div>
          </div>
        </div>

        <!-- Actions -->
        <div class="flex justify-end gap-3">
          <button
            type="button"
            class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
            @click="cancel"
          >
            Abbrechen
          </button>
          <button
            type="submit"
            class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark disabled:opacity-50"
            :disabled="saving"
          >
            <span v-if="saving">Speichern...</span>
            <span v-else>{{ isEdit ? 'Speichern' : 'Pipeline erstellen' }}</span>
          </button>
        </div>
      </form>
    </div>

    <!-- AI Setup Wizard -->
    <PipelineSetupWizard
      :visible="showWizard"
      @close="showWizard = false"
      @complete="handleWizardComplete"
    />
  </div>
</template>
