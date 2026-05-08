<script setup>
/**
 * LLM-Konfiguration als Tab im Einstellungen-Modul.
 *
 * Premium  — interaktive, kreative Aufgaben (Setup-Assistent, KI-Designer)
 * Standard — Personalisierung pro Empfänger (Body, Subject, Reply-Drafts)
 * Bulk     — Klassifikation, Scraping, Sentiment (häufig + günstig)
 *
 * "Aktuelle Modelle prüfen" ruft Anthropic /v1/models live ab und schlägt
 * Klassen vor (Opus -> premium, Sonnet -> standard, Haiku -> bulk).
 */
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import api from '@/api'
import { usePageTopics } from '@/stores/pageTopics'

const pageTopics = usePageTopics()

const settings = ref(null)
const available = ref([])
const loadingSettings = ref(true)
const loadingModels = ref(false)
const saving = ref(false)
const error = ref(null)
const savedToast = ref(false)

const cardClass =
  'rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800'
const labelClass = 'block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1'
const inputClass =
  'block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 ' +
  'placeholder-gray-400 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary ' +
  'dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100'
const primaryBtnClass =
  'rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark ' +
  'disabled:opacity-50 disabled:cursor-not-allowed'
const secondaryBtnClass =
  'rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 ' +
  'hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed ' +
  'dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600'

const classMeta = {
  premium: {
    icon: '🚀',
    label: 'Premium',
    short: 'Setup, KI-Designer, Strategie',
    description:
      'Beste Qualität, langsamer + teurer. Wird verwendet für interaktive Aufgaben mit Mensch im Loop: ' +
      'Setup-Assistent, KI-Designer-Chat im Email-Editor, Strategie-Dialoge.',
  },
  standard: {
    icon: '⚡',
    label: 'Standard',
    short: 'Body-Generierung pro Empfänger',
    description:
      'Personalisierungs-Workhorse. Gut + bezahlbar. Wird verwendet für: Body-Texte pro Empfänger ' +
      '({{llm_body}}), Subject-Personalisierung, Reply-Drafts vom Brain.',
  },
  bulk: {
    icon: '🪙',
    label: 'Bulk',
    short: 'Klassifikation, Sentiment, Scraping',
    description:
      'Sehr häufig + spottbillig. Wird verwendet für: Sentiment-Analyse, Intent-Klassifikation, ' +
      'Webseiten-Scraping (Leadgen), Lead-Scoring.',
  },
}

const optionsForClass = computed(() => {
  return (cls) => {
    const sorted = [...available.value].sort((a, b) => {
      const aMatch = a.suggested_class === cls ? 0 : 1
      const bMatch = b.suggested_class === cls ? 0 : 1
      if (aMatch !== bMatch) return aMatch - bMatch
      return a.id.localeCompare(b.id)
    })
    return sorted
  }
})

async function loadSettings() {
  loadingSettings.value = true
  error.value = null
  try {
    const { data } = await api.get('/v1/settings/llm')
    settings.value = data
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    loadingSettings.value = false
  }
}

async function loadAvailable() {
  loadingModels.value = true
  error.value = null
  try {
    const { data } = await api.get('/v1/settings/llm/available')
    available.value = data
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    loadingModels.value = false
  }
}

async function save() {
  if (!settings.value) return
  saving.value = true
  error.value = null
  try {
    const { data } = await api.put('/v1/settings/llm', {
      premium_model: settings.value.premium.model,
      standard_model: settings.value.standard.model,
      bulk_model: settings.value.bulk.model,
    })
    settings.value = data
    savedToast.value = true
    setTimeout(() => (savedToast.value = false), 2500)
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    saving.value = false
  }
}

function isUpdateAvailable(currentModel, cls) {
  if (!available.value.length || !currentModel) return null
  const matches = available.value.filter((m) => m.suggested_class === cls)
  if (!matches.length) return null
  const newest = matches.reduce((a, b) => (a.id > b.id ? a : b))
  if (newest.id > currentModel) return newest
  return null
}

onMounted(async () => {
  pageTopics.setTopics([
    {
      topic: 'llm-settings',
      title: 'LLM-Modelle',
      context: {
        module: 'settings',
        page: '/settings#llm',
        form_state: settings.value || {},
      },
      suggestions: [
        'Was ist der Unterschied zwischen Premium und Standard?',
        'Soll ich Sonnet oder Haiku nehmen?',
        'Wie viel kostet das im Monat?',
      ],
    },
  ])
  await loadSettings()
  await loadAvailable()
})

onBeforeUnmount(() => {
  pageTopics.clearTopics()
})
</script>

<template>
  <div>
    <div class="mb-6 flex items-center justify-between gap-3">
      <div>
        <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
          LLM-Modelle
        </h2>
        <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Drei Modell-Klassen für unterschiedliche Use-Cases — global pro Tenant einstellbar.
        </p>
      </div>
      <div class="flex items-center gap-2">
        <button
          type="button"
          :class="secondaryBtnClass"
          :disabled="loadingModels"
          @click="loadAvailable"
        >
          {{ loadingModels ? 'Prüfen…' : 'Auf neueste Modelle prüfen' }}
        </button>
        <button
          type="button"
          :class="primaryBtnClass"
          :disabled="saving || !settings"
          @click="save"
        >
          {{ saving ? 'Speichern…' : 'Speichern' }}
        </button>
      </div>
    </div>

    <div
      v-if="loadingSettings"
      class="flex items-center justify-center py-12"
    >
      <span class="text-gray-500 dark:text-gray-400">Laden…</span>
    </div>

    <div
      v-else-if="error"
      class="rounded-lg bg-red-50 dark:bg-red-900/20 p-4 text-red-700 dark:text-red-300"
    >
      {{ error }}
    </div>

    <template v-else-if="settings">
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div
          v-for="cls in ['premium', 'standard', 'bulk']"
          :key="cls"
          :class="cardClass"
        >
          <div class="mb-2 flex items-center gap-2">
            <span class="text-2xl">{{ classMeta[cls].icon }}</span>
            <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
              {{ classMeta[cls].label }}
            </h3>
          </div>
          <p class="text-xs text-go4-primary font-medium mb-3">
            {{ classMeta[cls].short }}
          </p>

          <label :class="labelClass">Aktuelles Modell</label>
          <select
            v-model="settings[cls].model"
            :class="inputClass"
          >
            <option
              v-if="!available.length"
              :value="settings[cls].model"
            >
              {{ settings[cls].model }} (live-Liste nicht geladen)
            </option>
            <optgroup
              v-if="available.length"
              :label="`Empfohlen für ${classMeta[cls].label}`"
            >
              <option
                v-for="m in optionsForClass(cls).filter((x) => x.suggested_class === cls)"
                :key="m.id"
                :value="m.id"
              >
                {{ m.display_name || m.id }}
              </option>
            </optgroup>
            <optgroup
              v-if="available.length"
              label="Andere Modelle"
            >
              <option
                v-for="m in optionsForClass(cls).filter((x) => x.suggested_class !== cls)"
                :key="m.id"
                :value="m.id"
              >
                {{ m.display_name || m.id }}
              </option>
            </optgroup>
          </select>

          <p
            v-if="settings[cls].is_default"
            class="mt-2 text-xs text-gray-500 dark:text-gray-400"
          >
            ⚙️ Verwendet Standard-Default (kein Tenant-Override aktiv)
          </p>

          <div
            v-if="isUpdateAvailable(settings[cls].model, cls)"
            class="mt-3 rounded-md bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800/40 p-2 text-xs"
          >
            <span class="font-medium text-amber-800 dark:text-amber-200">
              📦 Neuere Version verfügbar:
            </span>
            <span class="text-amber-700 dark:text-amber-300">
              {{ isUpdateAvailable(settings[cls].model, cls).id }}
            </span>
            <button
              type="button"
              class="ml-2 underline text-amber-800 dark:text-amber-200 hover:text-amber-900"
              @click="settings[cls].model = isUpdateAvailable(settings[cls].model, cls).id"
            >
              Übernehmen
            </button>
          </div>

          <p class="mt-4 text-xs text-gray-600 dark:text-gray-400 leading-relaxed">
            {{ classMeta[cls].description }}
          </p>
        </div>
      </div>

      <div :class="`${cardClass} mt-6`">
        <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
          Wo werden die Klassen verwendet?
        </h3>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div>
            <p class="font-medium text-gray-900 dark:text-gray-100 mb-1">
              🚀 Premium
            </p>
            <ul class="list-disc list-inside text-xs text-gray-600 dark:text-gray-400 space-y-0.5">
              <li>Setup-Assistent (Pipeline-Onboarding)</li>
              <li>Email-Template KI-Designer-Chat</li>
              <li>Strategie-Dialoge im Engagement</li>
            </ul>
          </div>
          <div>
            <p class="font-medium text-gray-900 dark:text-gray-100 mb-1">
              ⚡ Standard
            </p>
            <ul class="list-disc list-inside text-xs text-gray-600 dark:text-gray-400 space-y-0.5">
              <li>{{ '{' }}{{ '{' }}llm_body{{ '}' }}{{ '}' }} pro Empfänger</li>
              <li>Subject-Personalisierung</li>
              <li>Reply-Drafts vom Brain</li>
            </ul>
          </div>
          <div>
            <p class="font-medium text-gray-900 dark:text-gray-100 mb-1">
              🪙 Bulk
            </p>
            <ul class="list-disc list-inside text-xs text-gray-600 dark:text-gray-400 space-y-0.5">
              <li>Sentiment-Analyse von Replies</li>
              <li>Intent-Klassifikation</li>
              <li>Leadgen Webseiten-Analyse</li>
              <li>Lead-Scoring</li>
            </ul>
          </div>
        </div>
      </div>
    </template>

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
        class="fixed bottom-4 right-4 z-50 rounded-lg bg-emerald-600 text-white px-4 py-2 shadow-lg text-sm font-medium"
      >
        ✓ Gespeichert
      </div>
    </transition>
  </div>
</template>
