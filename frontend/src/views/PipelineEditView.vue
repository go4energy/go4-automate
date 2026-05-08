<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useEngagementStore } from '@/stores/engagement'
import api from '@/api'
import PageHeader from '@/components/ui/PageHeader.vue'
import PipelineSetupWizard from '@/components/engagement/PipelineSetupWizard.vue'
import TagComboInput from '@/components/ui/TagComboInput.vue'

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
const savedToast = ref(false)

// Tab state — synced with URL ?tab= so deep-links from Übersicht work.
const tabs = [
  { key: 'allgemein', label: 'Allgemein' },
  { key: 'audience', label: 'Zielgruppe' },
  { key: 'product', label: 'Produktbeschreibung' },
  { key: 'playbook', label: 'Playbook' },
  { key: 'auto_enroll', label: 'Auto-Enrollment' },
]
const validTab = (t) => tabs.some((x) => x.key === t)
const activeTab = ref(validTab(route.query.tab) ? route.query.tab : 'allgemein')

watch(activeTab, (next) => {
  // Reflect tab in URL without pushing a new history entry.
  if (route.query.tab !== next) {
    router.replace({ query: { ...route.query, tab: next } })
  }
})
watch(
  () => route.query.tab,
  (next) => {
    if (validTab(next) && next !== activeTab.value) activeTab.value = next
  },
)

function handleWizardComplete(result) {
  showWizard.value = false

  if (result.fill_form && result.pipeline_config) {
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
      playbook: config.playbook || formData.value.playbook,
      tracking_config: formData.value.tracking_config,
    }
  } else if (result.pipeline) {
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

// Auto-Enrollment Filter — frei toggle-bar. Bei 'auto_enroll_enabled=false'
// wird beim Speichern auto_enroll_filter=null gesendet → Pipeline ist
// manuell-only.
const autoEnrollEnabled = ref(false)
const autoEnrollFilter = ref({
  tags_any: [],
  tags_all: [],
  tags_none: [],
  custom_fields: {}
})
const customFieldRows = ref([])
function addCustomFieldRow() {
  customFieldRows.value.push({ key: '', value: '' })
}
function removeCustomFieldRow(idx) {
  customFieldRows.value.splice(idx, 1)
}
function syncCustomFieldsToFilter() {
  const obj = {}
  for (const row of customFieldRows.value) {
    if (row.key) obj[row.key] = row.value
  }
  autoEnrollFilter.value.custom_fields = obj
}

// Tag-Suggestions: lazy load on first focus of any tag combobox
const tagSuggestions = ref([])
const tagsLoaded = ref(false)
async function loadTagSuggestions() {
  if (tagsLoaded.value) return
  try {
    const { data } = await api.get('/contacts/tags/suggest', { params: { limit: 100 } })
    tagSuggestions.value = data || []
  } catch (err) {
    console.warn('Tag-Suggest failed', err)
    tagSuggestions.value = []
  } finally {
    tagsLoaded.value = true
  }
}

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
  if (idx >= 0) formData.value.channels.splice(idx, 1)
  else formData.value.channels.push(channel)
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
      // Backwards-compat: support both nested (tc.utm.source) and flat
      // (tc.utm_source) shapes. Nested takes precedence if both exist.
      const nestedUtm = tc.utm || {}
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
          utm_source: nestedUtm.source || tc.utm_source || '',
          utm_medium: nestedUtm.medium || tc.utm_medium || '',
          utm_campaign: nestedUtm.campaign || tc.utm_campaign || '',
          utm_term: nestedUtm.term || tc.utm_term || '',
          utm_content: nestedUtm.content || tc.utm_content || '',
          custom_params: tc.custom_params || {}
        }
      }
      customParamRows.value = Object.entries(tc.custom_params || {}).map(
        ([key, value]) => ({ key, value })
      )

      // Auto-Enrollment-Filter laden
      if (pipeline.auto_enroll_filter) {
        autoEnrollEnabled.value = true
        autoEnrollFilter.value = {
          tags_any: pipeline.auto_enroll_filter.tags_any || [],
          tags_all: pipeline.auto_enroll_filter.tags_all || [],
          tags_none: pipeline.auto_enroll_filter.tags_none || [],
          custom_fields: pipeline.auto_enroll_filter.custom_fields || {}
        }
        customFieldRows.value = Object.entries(autoEnrollFilter.value.custom_fields).map(
          ([key, value]) => ({ key, value })
        )
      }
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
    activeTab.value = 'allgemein'
    return
  }
  if (!formData.value.slug.trim()) {
    error.value = 'Slug ist erforderlich'
    activeTab.value = 'allgemein'
    return
  }
  if (formData.value.channels.length === 0) {
    error.value = 'Mindestens ein Kanal muss ausgewaehlt werden'
    activeTab.value = 'allgemein'
    return
  }

  saving.value = true
  error.value = null

  try {
    syncCustomParamsToForm()
    syncCustomFieldsToFilter()
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
      tracking_config: (() => {
        // Mirror flat utm_* into nested utm: { ... }, but only write the
        // nested object if at least one UTM value is actually set —
        // otherwise the renderer would fall back to defaults and inject
        // unwanted UTM params into mails. Keep the flat fields as-is for
        // legacy compat; they're empty when the user hasn't set them.
        const tc = { ...formData.value.tracking_config }
        const nested = {}
        const map = {
          utm_source: 'source',
          utm_medium: 'medium',
          utm_campaign: 'campaign',
          utm_term: 'term',
          utm_content: 'content'
        }
        for (const [flat, short] of Object.entries(map)) {
          const v = (tc[flat] || '').trim()
          if (v) nested[short] = v
        }
        if (Object.keys(nested).length) {
          tc.utm = nested
        } else {
          delete tc.utm  // wipe stale nested utm if user cleared all fields
        }
        return tc
      })(),
      auto_enroll_filter: autoEnrollEnabled.value
        ? {
            tags_any: autoEnrollFilter.value.tags_any,
            tags_all: autoEnrollFilter.value.tags_all,
            tags_none: autoEnrollFilter.value.tags_none,
            custom_fields: autoEnrollFilter.value.custom_fields
          }
        : null
    }

    if (isEdit.value) {
      await store.editPipeline(pipelineId.value, data)
      // Stay on edit page after save — show toast, don't redirect
      savedToast.value = true
      setTimeout(() => (savedToast.value = false), 2500)
    } else {
      const created = await store.addPipeline(data)
      // After create: jump to detail view
      const newId = created?.id || pipelineId.value
      if (newId) {
        router.push(`/engagement/pipelines/${newId}/uebersicht`)
      } else {
        router.push('/engagement/pipelines')
      }
    }
  } catch (err) {
    error.value = err.response?.data?.detail || err.message
  } finally {
    saving.value = false
  }
}

function cancel() {
  if (isEdit.value) {
    router.push(`/engagement/pipelines/${pipelineId.value}/uebersicht`)
  } else {
    router.push('/engagement/pipelines')
  }
}

const inputClass =
  'w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white'
const labelClass = 'mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300'
const cardClass = 'rounded-lg bg-white p-6 shadow dark:bg-gray-800'
const longTextareaClass =
  'w-full rounded-lg border border-gray-300 bg-white px-3 py-3 text-sm leading-relaxed dark:border-gray-600 dark:bg-gray-700 dark:text-white'
</script>

<template>
  <div class="flex flex-1 flex-col overflow-hidden">
    <PageHeader :title="isEdit ? 'Pipeline bearbeiten' : 'Neue Pipeline'">
      <template #actions>
        <button
          v-if="!isEdit"
          type="button"
          class="flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
          @click="showWizard = true"
        >
          <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          AI-Assistent
        </button>
        <button
          type="button"
          class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
          @click="cancel"
        >
          {{ isEdit ? 'Zurück' : 'Abbrechen' }}
        </button>
        <button
          type="button"
          class="rounded-lg bg-go4-primary px-5 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark disabled:opacity-50"
          :disabled="saving || loading"
          @click="save"
        >
          <span v-if="saving">Speichern…</span>
          <span v-else>{{ isEdit ? 'Speichern' : 'Pipeline erstellen' }}</span>
        </button>
      </template>
    </PageHeader>

    <div class="flex-1 overflow-auto">
      <!-- Loading -->
      <div v-if="loading" class="flex items-center justify-center py-12">
        <svg class="h-8 w-8 animate-spin text-go4-primary" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
      </div>

      <!-- Form -->
      <form v-else class="mx-auto max-w-5xl pt-4 px-4 pb-8" @submit.prevent="save">
        <!-- Tab Bar -->
        <nav class="mb-4 border-b border-gray-200 dark:border-gray-700">
          <div class="-mb-px flex gap-6">
            <button
              v-for="t in tabs"
              :key="t.key"
              type="button"
              class="border-b-2 pb-3 text-sm font-medium transition"
              :class="
                activeTab === t.key
                  ? 'border-go4-primary text-go4-primary'
                  : 'border-transparent text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200'
              "
              @click="activeTab = t.key"
            >
              {{ t.label }}
            </button>
          </div>
        </nav>

        <!-- Error -->
        <div
          v-if="error"
          class="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300"
        >
          {{ error }}
        </div>

        <!-- ─── ALLGEMEIN ─── -->
        <div v-if="activeTab === 'allgemein'" class="space-y-6">
          <div :class="cardClass">
            <h3 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Grundinformationen</h3>
            <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div>
                <label :class="labelClass">Name *</label>
                <input
                  v-model="formData.name"
                  type="text"
                  :class="inputClass"
                  placeholder="z.B. Solar KMU Pipeline"
                  @blur="handleNameChange"
                >
              </div>
              <div>
                <label :class="labelClass">Slug *</label>
                <input
                  v-model="formData.slug"
                  type="text"
                  :class="inputClass"
                  placeholder="z.B. solar-kmu"
                >
                <p class="mt-1 text-xs text-gray-500">Eindeutiger Identifier (keine Leerzeichen)</p>
              </div>
              <div class="md:col-span-2">
                <label :class="labelClass">Produktname</label>
                <input
                  v-model="formData.product_name"
                  type="text"
                  :class="inputClass"
                  placeholder="z.B. Solaranlagen"
                >
              </div>
            </div>
          </div>

          <div :class="cardClass">
            <h3 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Kanäle *</h3>
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
            <p class="mt-2 text-sm text-gray-500">Über diese Kanäle wird kommuniziert.</p>
          </div>

          <div :class="cardClass">
            <h3 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Einstellungen</h3>
            <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div>
                <label :class="labelClass">Ziel</label>
                <select v-model="formData.goal" :class="inputClass">
                  <option value="">Bitte wählen</option>
                  <option v-for="o in goalOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
                </select>
              </div>
              <div>
                <label :class="labelClass">Tonalität</label>
                <select v-model="formData.tone_of_voice" :class="inputClass">
                  <option v-for="o in toneOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
                </select>
              </div>
              <div>
                <label :class="labelClass">Min. Tage zwischen Touches</label>
                <input
                  v-model.number="formData.min_days_between_touches"
                  type="number"
                  min="1"
                  max="30"
                  :class="inputClass"
                >
              </div>
              <div class="flex items-center">
                <label class="flex cursor-pointer items-center gap-3">
                  <input
                    v-model="formData.is_active"
                    type="checkbox"
                    class="h-5 w-5 rounded border-gray-300 text-go4-primary focus:ring-go4-primary"
                  >
                  <span class="text-sm font-medium text-gray-700 dark:text-gray-300">Pipeline ist aktiv</span>
                </label>
              </div>
            </div>
          </div>

          <div :class="cardClass">
            <h3 class="mb-1 text-lg font-semibold text-gray-900 dark:text-white">Tracking & Attribution</h3>
            <p class="mb-4 text-sm text-gray-500 dark:text-gray-400">
              Beim Enrollment wird optional ein Tracking-Hash pro Kontakt erzeugt.
              UTM-Parameter werden in alle ausgehenden URLs (Briefe, Emails) der Pipeline injiziert.
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
                <label :class="labelClass">utm_source</label>
                <input v-model="formData.tracking_config.utm_source" type="text" :class="inputClass" placeholder="z.B. newsletter, brief, linkedin">
              </div>
              <div>
                <label :class="labelClass">utm_medium</label>
                <input v-model="formData.tracking_config.utm_medium" type="text" :class="inputClass" placeholder="z.B. email, mail, social">
              </div>
              <div>
                <label :class="labelClass">utm_campaign</label>
                <input v-model="formData.tracking_config.utm_campaign" type="text" :class="inputClass" placeholder="z.B. q2-2026">
              </div>
              <div>
                <label :class="labelClass">utm_term</label>
                <input v-model="formData.tracking_config.utm_term" type="text" :class="inputClass">
              </div>
              <div class="md:col-span-2">
                <label :class="labelClass">utm_content</label>
                <input v-model="formData.tracking_config.utm_content" type="text" :class="inputClass">
              </div>
            </div>

            <div class="mt-6">
              <div class="mb-2 flex items-center justify-between">
                <label class="text-sm font-medium text-gray-700 dark:text-gray-300">Eigene Parameter</label>
                <button type="button" class="text-sm text-go4-primary hover:underline" @click="addCustomParam">
                  + Hinzufügen
                </button>
              </div>
              <div class="space-y-2">
                <div
                  v-for="(row, idx) in customParamRows"
                  :key="idx"
                  class="grid grid-cols-[1fr_1fr_auto] gap-2"
                >
                  <input v-model="row.key" type="text" placeholder="key" :class="inputClass">
                  <input v-model="row.value" type="text" placeholder="value" :class="inputClass">
                  <button type="button" class="px-2 text-red-500 hover:text-red-700" @click="removeCustomParam(idx)">×</button>
                </div>
                <p v-if="customParamRows.length === 0" class="text-xs text-gray-400">
                  Keine eigenen Parameter — UTM oben reicht für die meisten Fälle.
                </p>
              </div>
            </div>
          </div>
        </div>

        <!-- ─── ZIELGRUPPE ─── -->
        <div v-else-if="activeTab === 'audience'" :class="cardClass">
          <h3 class="mb-2 text-lg font-semibold text-gray-900 dark:text-white">Zielgruppe</h3>
          <p class="mb-4 text-sm text-gray-500 dark:text-gray-400">
            Wer soll angesprochen werden? Branchen, Positionen, Unternehmensgröße, Pain-Points,
            Ausschluss-Kriterien. Das Brain nutzt diesen Text als Kontext bei jeder Lead-Bewertung.
          </p>
          <textarea
            v-model="formData.target_audience"
            rows="22"
            :class="longTextareaClass"
            placeholder="z.B. Elektrofachbetriebe mit 5–50 Mitarbeitern, die Ladeinfrastruktur an MFH/WEGs verkaufen…"
          />
          <p class="mt-2 text-right text-xs text-gray-400">
            {{ (formData.target_audience || '').length.toLocaleString('de-DE') }} Zeichen
          </p>
        </div>

        <!-- ─── PRODUKTBESCHREIBUNG ─── -->
        <div v-else-if="activeTab === 'product'" :class="cardClass">
          <h3 class="mb-2 text-lg font-semibold text-gray-900 dark:text-white">Produktbeschreibung</h3>
          <p class="mb-4 text-sm text-gray-500 dark:text-gray-400">
            Was wird beworben? Hauptnutzen, Features, Marktanlass, Förderungen, Preisrahmen.
            Wird als Kontext für die personalisierten Touch-Texte verwendet.
          </p>
          <textarea
            v-model="formData.product_description"
            rows="22"
            :class="longTextareaClass"
            placeholder="Beschreiben Sie das Produkt/Service, seinen Hauptnutzen und den Marktanlass…"
          />
          <p class="mt-2 text-right text-xs text-gray-400">
            {{ (formData.product_description || '').length.toLocaleString('de-DE') }} Zeichen
          </p>
        </div>

        <!-- ─── AUTO-ENROLLMENT ─── -->
        <div v-else-if="activeTab === 'auto_enroll'" class="space-y-6">
          <div :class="cardClass">
            <h3 class="mb-2 text-lg font-semibold text-gray-900 dark:text-white">Auto-Enrollment</h3>
            <p class="mb-4 text-sm text-gray-500 dark:text-gray-400">
              Wenn aktiv, werden Kontakte automatisch in diese Pipeline aufgenommen, sobald
              sie sich auf der Webseite anmelden und die unten definierten Tag- und
              Custom-Field-Bedingungen erfüllen. Greift bei jedem
              <code class="rounded bg-gray-100 px-1 dark:bg-gray-700">/tracking/identify</code>-Call.
            </p>
            <label class="flex cursor-pointer items-center gap-3">
              <input
                v-model="autoEnrollEnabled"
                type="checkbox"
                class="h-5 w-5 rounded border-gray-300 text-go4-primary focus:ring-go4-primary"
                @change="loadTagSuggestions"
              >
              <span class="text-sm font-medium text-gray-700 dark:text-gray-300">
                Auto-Enrollment aktivieren
              </span>
            </label>
          </div>

          <div v-if="autoEnrollEnabled" :class="cardClass" class="space-y-6">
            <div>
              <label :class="labelClass">
                Lead muss <span class="font-bold">mindestens einen</span> dieser Tags haben (ODER)
              </label>
              <TagComboInput
                v-model="autoEnrollFilter.tags_any"
                :suggestions="tagSuggestions"
                placeholder="z.B. fachpartner, verwalter — Enter drücken zum Hinzufügen"
                @focus="loadTagSuggestions"
              />
              <p class="mt-1 text-xs text-gray-500">
                Leer lassen, um diesen Filter zu deaktivieren.
              </p>
            </div>

            <div>
              <label :class="labelClass">
                Lead muss <span class="font-bold">alle</span> diese Tags haben (UND)
              </label>
              <TagComboInput
                v-model="autoEnrollFilter.tags_all"
                :suggestions="tagSuggestions"
                placeholder="z.B. leadgen — Enter drücken zum Hinzufügen"
                @focus="loadTagSuggestions"
              />
            </div>

            <div>
              <label :class="labelClass">
                Lead darf <span class="font-bold">keinen</span> dieser Tags haben (NICHT)
              </label>
              <TagComboInput
                v-model="autoEnrollFilter.tags_none"
                :suggestions="tagSuggestions"
                placeholder="z.B. unqualified, do_not_contact"
                @focus="loadTagSuggestions"
              />
            </div>

            <div>
              <div class="mb-2 flex items-center justify-between">
                <label :class="labelClass">Custom-Field-Bedingungen (exact-Match)</label>
                <button
                  type="button"
                  class="text-sm text-go4-primary hover:underline"
                  @click="addCustomFieldRow"
                >
                  + Bedingung hinzufügen
                </button>
              </div>
              <div class="space-y-2">
                <div
                  v-for="(row, idx) in customFieldRows"
                  :key="idx"
                  class="grid grid-cols-[1fr_1fr_auto] gap-2"
                >
                  <input v-model="row.key" type="text" placeholder="key (z.B. region)" :class="inputClass">
                  <input v-model="row.value" type="text" placeholder="value (z.B. Bayern)" :class="inputClass">
                  <button
                    type="button"
                    class="px-2 text-red-500 hover:text-red-700"
                    @click="removeCustomFieldRow(idx)"
                  >
                    ×
                  </button>
                </div>
                <p v-if="customFieldRows.length === 0" class="text-xs text-gray-400">
                  Keine zusätzlichen Bedingungen — Tag-Filter oben reicht für die meisten Fälle.
                </p>
              </div>
            </div>

            <div class="rounded-lg bg-blue-50 p-4 text-sm text-blue-900 dark:bg-blue-900/20 dark:text-blue-200">
              <p class="font-semibold">Wie funktioniert das?</p>
              <ul class="mt-2 list-disc space-y-1 pl-5">
                <li>Bei jedem Identify-Call werden alle aktiven Pipelines mit Auto-Enrollment-Filter geprüft.</li>
                <li>Lead landet in <em>allen</em> matchenden Pipelines parallel.</li>
                <li>Kontakte mit einem bereits bestehenden Enrollment werden NICHT erneut enrolled (idempotent).</li>
                <li>Tag-Vokabular wählt der Tenant — keine Whitelist, frei wählbar.</li>
              </ul>
            </div>
          </div>
        </div>

        <!-- ─── PLAYBOOK ─── -->
        <div v-else-if="activeTab === 'playbook'" :class="cardClass">
          <h3 class="mb-2 text-lg font-semibold text-gray-900 dark:text-white">Playbook</h3>
          <p class="mb-4 text-sm text-gray-500 dark:text-gray-400">
            Strategie-Richtlinien für das Brain: Kern-Botschaft, Touchpoint-Sequenz mit Timing,
            Eskalation, Pause-Trigger. Das Brain konsultiert dieses Playbook bei jeder
            Next-Step-Entscheidung.
          </p>
          <textarea
            v-model="formData.playbook"
            rows="28"
            :class="longTextareaClass"
            placeholder="z.B.
Strategie: …
Kern-Botschaft: …
Schritt 1 — Email, Tag 0: …
Schritt 2 — Brief, Tag +7: …
Pause-Trigger: …"
          />
          <p class="mt-2 text-right text-xs text-gray-400">
            {{ (formData.playbook || '').length.toLocaleString('de-DE') }} Zeichen
          </p>
        </div>
      </form>
    </div>

    <!-- Saved toast -->
    <transition
      enter-active-class="transition duration-200"
      enter-from-class="opacity-0 translate-y-2"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition duration-200"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="savedToast"
        class="fixed bottom-4 right-4 z-50 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white shadow-lg"
      >
        ✓ Gespeichert
      </div>
    </transition>

    <!-- AI Setup Wizard -->
    <PipelineSetupWizard
      :visible="showWizard"
      @close="showWizard = false"
      @complete="handleWizardComplete"
    />
  </div>
</template>
