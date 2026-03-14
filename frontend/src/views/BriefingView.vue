<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useBriefingStore } from '@/stores/briefing'
import { useAuthStore } from '@/stores/auth'
import PageHeader from '@/components/ui/PageHeader.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'

const router = useRouter()
const route = useRoute()
const store = useBriefingStore()
const authStore = useAuthStore()

// Tab state from route
const activeTab = computed(() => route.meta?.tab || 'sources')

const tabs = [
  { key: 'personal', label: 'Mein Briefing', route: '/briefing/personal' },
  { key: 'sources', label: 'Quellen', route: '/briefing/sources' },
  { key: 'findings', label: 'Findings', route: '/briefing/findings' },
  { key: 'channels', label: 'Channels', route: '/briefing/channels' },
  { key: 'speakers', label: 'Sprecher', route: '/briefing/speakers' }
]

const statusFilter = ref('')
const sourceTypeFilter = ref('')

// Speaker upload form
const speakerName = ref('')
const speakerLanguage = ref('de')
const speakerDescription = ref('')
const speakerFile = ref(null)
const speakerUploading = ref(false)
const personalForm = ref({
  email_enabled: false,
  calendar_enabled: false,
  unread_only: true,
  days_back: 1,
  max_items: 8,
  timezone: 'Europe/Berlin',
  delivery_time: '07:00'
})
const llmForm = ref({
  llm_provider: 'ollama',
  llm_model: ''
})
const personalLoaded = ref(false)

onMounted(() => {
  store.fetchChannels()
  store.fetchSources()
  store.fetchFindings()
  store.fetchSpeakers()
  if (activeTab.value === 'personal') {
    ensurePersonalData()
  }
})

watch(activeTab, async (tab) => {
  if (tab === 'personal' && !personalLoaded.value) {
    await ensurePersonalData()
  }
})

async function handleDeleteChannel(id) {
  if (confirm('Channel und alle Episoden wirklich loeschen?')) {
    await store.removeChannel(id)
  }
}

async function handleToggle(channel) {
  await store.editChannel(channel.id, { active: !channel.active })
}

async function handleCloneChannel(channel) {
  const cloned = await store.cloneOrgChannel(channel.id)
  if (cloned) {
    router.push(`/briefing/channels/${cloned.id}/edit`)
  }
}

async function handleDeleteSource(id) {
  if (confirm('Quelle wirklich loeschen?')) {
    await store.removeSource(id)
  }
}

async function handleRunSource(id) {
  const result = await store.runSingleSource(id)
  if (result) {
    await store.fetchSources()
    await store.fetchFindings()
  }
}

async function handleRunAllSources() {
  const result = await store.runAllSources()
  if (result) {
    await store.fetchSources()
    await store.fetchFindings()
  }
}

async function handleDismissFinding(id) {
  await store.editFinding(id, { status: 'dismissed' })
}

function onSpeakerFileChange(event) {
  speakerFile.value = event.target.files[0] || null
}

async function handleUploadSpeaker() {
  if (!speakerName.value || !speakerFile.value) return
  speakerUploading.value = true
  try {
    const formData = new FormData()
    formData.append('name', speakerName.value)
    formData.append('language', speakerLanguage.value)
    if (speakerDescription.value) formData.append('description', speakerDescription.value)
    formData.append('file', speakerFile.value)
    await store.addSpeaker(formData)
    speakerName.value = ''
    speakerLanguage.value = 'de'
    speakerDescription.value = ''
    speakerFile.value = null
  } catch {
    // error handled by store
  } finally {
    speakerUploading.value = false
  }
}

async function handleDeleteSpeaker(id) {
  if (confirm('Sprecher wirklich loeschen?')) {
    await store.removeSpeaker(id)
  }
}

function syncPersonalForm(settings) {
  if (!settings) return
  personalForm.value = {
    email_enabled: settings.email_enabled ?? false,
    calendar_enabled: settings.calendar_enabled ?? false,
    unread_only: settings.unread_only ?? true,
    days_back: settings.days_back ?? 1,
    max_items: settings.max_items ?? 8,
    timezone: settings.timezone || 'Europe/Berlin',
    delivery_time: settings.delivery_time || '07:00'
  }
}

async function ensurePersonalData() {
  try {
    const tasks = [
      store.fetchPersonalSettings(),
      store.fetchPersonalConnections()
    ]
    if (authStore.isAdmin) {
      tasks.push(store.fetchBriefingModuleConfig())
      tasks.push(store.fetchAvailableOllamaModels())
    }
    const [settings, , moduleConfig] = await Promise.all(tasks)
    syncPersonalForm(settings)
    syncLlmForm(moduleConfig || store.briefingModuleConfig)
    personalLoaded.value = true
  } catch {
    // error handled by store
  }
}

async function handleSavePersonalSettings() {
  try {
    const data = await store.savePersonalSettings({ ...personalForm.value })
    syncPersonalForm(data)
  } catch {
    // error handled by store
  }
}

function syncLlmForm(moduleConfig) {
  const config = moduleConfig?.config || {}
  llmForm.value = {
    llm_provider: config.llm_provider || 'ollama',
    llm_model: config.llm_model || ''
  }
}

async function handleSaveBriefingLlmConfig() {
  try {
    const data = await store.saveBriefingModuleConfig({ ...llmForm.value })
    syncLlmForm(data)
  } catch {
    // error handled by store
  }
}

async function refreshOllamaModels() {
  try {
    await store.fetchAvailableOllamaModels()
  } catch {
    // error handled by store
  }
}

function providerHint(provider) {
  if (provider === 'ollama') {
    return 'Nutzen Sie ein lokal installiertes Ollama-Modell, z. B. mistral oder llama3.2.'
  }
  if (provider === 'openai') {
    return 'Verwendet die global hinterlegte OpenAI-API-Konfiguration.'
  }
  if (provider === 'anthropic') {
    return 'Verwendet die global hinterlegte Anthropic-API-Konfiguration.'
  }
  return ''
}

const hasOllamaModels = computed(() => store.ollamaModels.length > 0)

function providerLabel(provider) {
  if (provider === 'microsoft') return 'Microsoft 365'
  if (provider === 'google') return 'Google'
  return provider
}

function findPersonalConnection(integrationType, provider) {
  return store.personalConnections.find(
    (connection) =>
      connection.integration_type === integrationType && connection.provider === provider
  )
}

async function connectPersonal(provider, integrationType) {
  try {
    const { auth_url: authUrl } = await store.startPersonalOAuth(provider, integrationType)
    window.open(authUrl, 'personal-oauth', 'width=600,height=700')
  } catch {
    // error handled by store
  }
}

async function disconnectPersonal(connection) {
  if (!confirm('Verbindung wirklich trennen?')) return
  try {
    await store.disconnectPersonalAccount(connection.id)
  } catch {
    // error handled by store
  }
}

async function handleRunPersonalBriefing() {
  try {
    await store.runPersonalBriefing()
  } catch {
    // error handled by store
  }
}

async function onOAuthMessage(event) {
  if (event.data?.type === 'oauth_success') {
    await store.fetchPersonalConnections()
    return
  }
  if (event.data?.type === 'oauth_error') {
    store.error = event.data.error || 'OAuth-Verbindung fehlgeschlagen'
  }
}

onMounted(() => {
  window.addEventListener('message', onOAuthMessage)
})

onBeforeUnmount(() => {
  window.removeEventListener('message', onOAuthMessage)
})

function formatFileSize(bytes) {
  if (!bytes) return '-'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDuration(seconds) {
  if (!seconds) return '-'
  const min = Math.floor(seconds / 60)
  const sec = seconds % 60
  return `${min}:${sec.toString().padStart(2, '0')}`
}

function speakerPreviewUrl(id) {
  return `/api/v1/briefing/speakers/${id}/preview`
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

function formatConnectionStatus(status) {
  if (status === 'connected') return 'Verbunden'
  if (status === 'revoked') return 'Getrennt'
  if (status === 'pending') return 'Ausstehend'
  return status || '-'
}

const sourceTypeLabels = {
  rss: 'RSS',
  website: 'Website',
  websearch: 'Websuche',
  calendar: 'Kalender',
  email: 'E-Mail',
  kpi: 'KPI'
}

const filteredFindings = () => {
  let items = store.findings
  if (statusFilter.value) {
    items = items.filter((f) => f.status === statusFilter.value)
  }
  if (sourceTypeFilter.value) {
    items = items.filter((f) => f.source_type === sourceTypeFilter.value)
  }
  return items
}
</script>

<template>
  <div>
    <PageHeader
      title="Briefing"
      subtitle="Internes Briefing fuer Ihre Zielgruppen"
    >
      <template #actions>
        <router-link
          v-if="activeTab === 'channels'"
          to="/briefing/channels/new"
          class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white transition hover:bg-go4-primary/90"
        >
          Neuer Channel
        </router-link>
        <router-link
          v-if="activeTab === 'sources'"
          to="/briefing/sources/new"
          class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white transition hover:bg-go4-primary/90"
        >
          Neue Quelle
        </router-link>
        <button
          v-if="activeTab === 'sources'"
          :disabled="store.runningSource"
          class="rounded-lg border border-go4-primary px-4 py-2 text-sm font-medium text-go4-primary transition hover:bg-go4-primary/5 disabled:opacity-50"
          @click="handleRunAllSources"
        >
          {{ store.runningSource ? 'Laeuft...' : 'Alle fetchen' }}
        </button>
      </template>
    </PageHeader>

    <!-- Error -->
    <div
      v-if="store.error"
      class="mt-4 rounded-lg bg-red-50 p-4 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-400"
    >
      {{ store.error }}
    </div>

    <!-- Tabs with arrow separators -->
    <div class="mt-4 border-b border-gray-200 dark:border-gray-700">
      <nav class="-mb-px flex items-center">
        <template
          v-for="(tab, index) in tabs"
          :key="tab.key"
        >
          <router-link
            :to="tab.route"
            class="border-b-2 px-1 pb-3 text-sm font-medium transition"
            :class="
              activeTab === tab.key
                ? 'border-go4-primary text-go4-primary'
                : 'border-transparent text-go4-muted dark:text-gray-400 hover:border-gray-300 dark:hover:border-gray-600 hover:text-go4-secondary dark:hover:text-gray-100'
            "
          >
            {{ tab.label }}
          </router-link>
          <span
            v-if="index < tabs.length - 1"
            class="mx-3 pb-3 text-go4-muted dark:text-gray-500 select-none"
          >
            &rarr;
          </span>
        </template>
      </nav>
    </div>

    <!-- Personal Tab -->
    <div
      v-if="activeTab === 'personal'"
      class="mt-6 space-y-6"
    >
      <div
        class="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]"
      >
        <section class="rounded-xl bg-white p-6 shadow-sm dark:bg-gray-800">
          <div class="flex items-start justify-between gap-4">
            <div>
              <h2 class="text-lg font-semibold text-go4-secondary dark:text-gray-100">
                Einstellungen
              </h2>
              <p class="mt-1 text-sm text-go4-muted dark:text-gray-400">
                Definieren Sie, wie Ihr persoenliches Morgenbriefing vorbereitet werden soll.
              </p>
            </div>
            <span
              v-if="store.personalLoading && !personalLoaded"
              class="text-sm text-go4-muted dark:text-gray-400"
            >
              Laden...
            </span>
          </div>

          <form
            class="mt-6 space-y-6"
            @submit.prevent="handleSavePersonalSettings"
          >
            <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
              <label class="rounded-lg border border-gray-200 p-4 dark:border-gray-700">
                <div class="flex items-start justify-between gap-4">
                  <div>
                    <p class="text-sm font-medium text-go4-secondary dark:text-gray-100">
                      E-Mail einbeziehen
                    </p>
                    <p class="mt-1 text-xs text-go4-muted dark:text-gray-400">
                      Ungelesene oder aktuelle E-Mails fuer Ihr Briefing beruecksichtigen.
                    </p>
                  </div>
                  <input
                    v-model="personalForm.email_enabled"
                    type="checkbox"
                    class="mt-1 h-4 w-4 rounded border-gray-300 text-go4-primary focus:ring-go4-primary"
                  >
                </div>
              </label>

              <label class="rounded-lg border border-gray-200 p-4 dark:border-gray-700">
                <div class="flex items-start justify-between gap-4">
                  <div>
                    <p class="text-sm font-medium text-go4-secondary dark:text-gray-100">
                      Kalender einbeziehen
                    </p>
                    <p class="mt-1 text-xs text-go4-muted dark:text-gray-400">
                      Bevorstehende Termine in das Morgenbriefing aufnehmen.
                    </p>
                  </div>
                  <input
                    v-model="personalForm.calendar_enabled"
                    type="checkbox"
                    class="mt-1 h-4 w-4 rounded border-gray-300 text-go4-primary focus:ring-go4-primary"
                  >
                </div>
              </label>
            </div>

            <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
              <label class="rounded-lg border border-gray-200 p-4 dark:border-gray-700">
                <div class="flex items-start justify-between gap-4">
                  <div>
                    <p class="text-sm font-medium text-go4-secondary dark:text-gray-100">
                      Nur ungelesene E-Mails
                    </p>
                    <p class="mt-1 text-xs text-go4-muted dark:text-gray-400">
                      Filtert das Briefing auf neue Nachrichten.
                    </p>
                  </div>
                  <input
                    v-model="personalForm.unread_only"
                    type="checkbox"
                    class="mt-1 h-4 w-4 rounded border-gray-300 text-go4-primary focus:ring-go4-primary"
                  >
                </div>
              </label>

              <div class="rounded-lg border border-gray-200 p-4 dark:border-gray-700">
                <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">
                  Versandzeit
                </label>
                <input
                  v-model="personalForm.delivery_time"
                  type="time"
                  class="mt-2 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-800 focus:border-go4-primary focus:ring-1 focus:ring-go4-primary dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
                >
              </div>
            </div>

            <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
              <div>
                <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">
                  Rueckblick in Tagen
                </label>
                <input
                  v-model.number="personalForm.days_back"
                  type="number"
                  min="1"
                  max="14"
                  class="mt-1 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-800 focus:border-go4-primary focus:ring-1 focus:ring-go4-primary dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
                >
              </div>

              <div>
                <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">
                  Max. Eintraege
                </label>
                <input
                  v-model.number="personalForm.max_items"
                  type="number"
                  min="1"
                  max="20"
                  class="mt-1 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-800 focus:border-go4-primary focus:ring-1 focus:ring-go4-primary dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
                >
              </div>

              <div>
                <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">
                  Zeitzone
                </label>
                <input
                  v-model="personalForm.timezone"
                  type="text"
                  class="mt-1 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-800 focus:border-go4-primary focus:ring-1 focus:ring-go4-primary dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
                  placeholder="Europe/Berlin"
                >
              </div>
            </div>

            <div class="flex items-center justify-between gap-3 border-t border-gray-100 pt-4 dark:border-gray-700">
              <p class="text-xs text-go4-muted dark:text-gray-400">
                Diese Einstellungen definieren die Basis fuer den spaeteren automatischen Briefing-Run.
              </p>
              <button
                type="submit"
                :disabled="store.personalSaving"
                class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white transition hover:bg-go4-primary/90 disabled:opacity-50"
              >
                {{ store.personalSaving ? 'Speichert...' : 'Einstellungen speichern' }}
              </button>
            </div>
          </form>
        </section>

        <section class="rounded-xl bg-white p-6 shadow-sm dark:bg-gray-800">
          <h2 class="text-lg font-semibold text-go4-secondary dark:text-gray-100">
            Verbindungsstatus
          </h2>
          <p class="mt-1 text-sm text-go4-muted dark:text-gray-400">
            Verbinden Sie Ihre bevorzugten Konten fuer E-Mail und Kalender.
          </p>

          <div class="mt-6 space-y-5">
            <div
              v-for="integrationType in ['email', 'calendar']"
              :key="integrationType"
              class="rounded-lg border border-gray-200 p-4 dark:border-gray-700"
            >
              <div class="flex items-center justify-between gap-3">
                <div>
                  <h3 class="text-sm font-semibold uppercase tracking-wider text-go4-secondary dark:text-gray-100">
                    {{ integrationType === 'email' ? 'E-Mail' : 'Kalender' }}
                  </h3>
                  <p class="mt-1 text-xs text-go4-muted dark:text-gray-400">
                    {{
                      integrationType === 'email'
                        ? 'Lesender Zugriff fuer Ihr persoenliches Morgenbriefing.'
                        : 'Lesender Zugriff auf Ihre anstehenden Termine.'
                    }}
                  </p>
                </div>
                <span class="text-xs text-go4-muted dark:text-gray-400">
                  {{ store.personalConnectionsByType[integrationType]?.length || 0 }} Verbindung(en)
                </span>
              </div>

              <div class="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
                <div
                  v-for="provider in ['microsoft', 'google']"
                  :key="provider"
                  class="rounded-lg bg-gray-50 p-4 dark:bg-gray-900/40"
                >
                  <div class="flex items-start justify-between gap-3">
                    <div class="min-w-0">
                      <p class="text-sm font-medium text-go4-secondary dark:text-gray-100">
                        {{ providerLabel(provider) }}
                      </p>
                      <p class="mt-1 text-xs text-go4-muted dark:text-gray-400">
                        {{
                          findPersonalConnection(integrationType, provider)?.connected_email ||
                            'Noch keine Verbindung hergestellt'
                        }}
                      </p>
                    </div>
                    <StatusBadge
                      :status="findPersonalConnection(integrationType, provider)?.status || 'inactive'"
                    />
                  </div>

                  <div class="mt-3 text-xs text-go4-muted dark:text-gray-400">
                    Status:
                    {{ formatConnectionStatus(findPersonalConnection(integrationType, provider)?.status) }}
                  </div>
                  <div
                    v-if="findPersonalConnection(integrationType, provider)?.last_error"
                    class="mt-2 rounded bg-red-50 px-2 py-1 text-xs text-red-700 dark:bg-red-900/20 dark:text-red-400"
                  >
                    {{ findPersonalConnection(integrationType, provider).last_error }}
                  </div>

                  <div class="mt-4 flex items-center gap-2">
                    <button
                      class="rounded-lg bg-go4-primary px-3 py-2 text-xs font-medium text-white transition hover:bg-go4-primary/90 disabled:opacity-50"
                      :disabled="store.personalConnecting === `${provider}:${integrationType}`"
                      @click="connectPersonal(provider, integrationType)"
                    >
                      {{
                        findPersonalConnection(integrationType, provider)?.status === 'connected'
                          ? 'Neu verbinden'
                          : store.personalConnecting === `${provider}:${integrationType}`
                            ? 'Startet...'
                            : 'Verbinden'
                      }}
                    </button>
                    <button
                      v-if="findPersonalConnection(integrationType, provider)"
                      class="rounded-lg border border-gray-300 px-3 py-2 text-xs font-medium text-gray-700 transition hover:bg-gray-100 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700"
                      @click="disconnectPersonal(findPersonalConnection(integrationType, provider))"
                    >
                      Trennen
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section
          v-if="authStore.isAdmin"
          class="rounded-xl bg-white p-6 shadow-sm dark:bg-gray-800"
        >
          <div class="flex items-start justify-between gap-4">
            <div>
              <h2 class="text-lg font-semibold text-go4-secondary dark:text-gray-100">
                LLM-Konfiguration
              </h2>
              <p class="mt-1 text-sm text-go4-muted dark:text-gray-400">
                Diese Einstellung gilt fuer das Briefing-Modul. Globale LLM-Settings bleiben nur Fallback.
              </p>
            </div>
            <span
              class="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-600 dark:bg-gray-900/40 dark:text-gray-300"
            >
              Admin
            </span>
          </div>

          <div class="mt-5 grid gap-4 md:grid-cols-2">
            <div>
              <label class="mb-2 block text-sm font-medium text-go4-secondary dark:text-gray-100">
                Provider
              </label>
              <select
                v-model="llmForm.llm_provider"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100"
              >
                <option value="ollama">
                  Ollama (lokal)
                </option>
                <option value="openai">
                  OpenAI (extern)
                </option>
                <option value="anthropic">
                  Anthropic (extern)
                </option>
              </select>
            </div>

            <div>
              <label class="mb-2 block text-sm font-medium text-go4-secondary dark:text-gray-100">
                Modellname
              </label>
              <select
                v-if="llmForm.llm_provider === 'ollama' && hasOllamaModels"
                v-model="llmForm.llm_model"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100"
              >
                <option value="">
                  Bitte Modell waehlen
                </option>
                <option
                  v-for="model in store.ollamaModels"
                  :key="model"
                  :value="model"
                >
                  {{ model }}
                </option>
              </select>
              <input
                v-else
                v-model="llmForm.llm_model"
                type="text"
                placeholder="z. B. mistral oder gpt-4o-mini"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100"
              >
              <p
                v-if="llmForm.llm_provider === 'ollama'"
                class="mt-2 text-xs text-go4-muted dark:text-gray-400"
              >
                {{
                  store.ollamaModelsLoading
                    ? 'Ollama-Modelle werden geladen...'
                    : hasOllamaModels
                      ? `${store.ollamaModels.length} lokale Modelle verfuegbar`
                      : 'Keine lokale Modellliste verfuegbar, Modellname kann manuell gesetzt werden.'
                }}
              </p>
            </div>
          </div>

          <p class="mt-3 text-xs text-go4-muted dark:text-gray-400">
            {{ providerHint(llmForm.llm_provider) }}
          </p>

          <div class="mt-5 flex items-center gap-3">
            <button
              class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white transition hover:bg-go4-primary/90 disabled:opacity-50"
              :disabled="store.briefingConfigLoading || store.briefingConfigSaving"
              @click="handleSaveBriefingLlmConfig"
            >
              {{
                store.briefingConfigSaving
                  ? 'Speichert...'
                  : store.briefingConfigLoading
                    ? 'Laedt...'
                    : 'LLM-Konfiguration speichern'
              }}
            </button>
            <span
              v-if="store.briefingModuleConfig?.config"
              class="text-xs text-go4-muted dark:text-gray-400"
            >
              Aktiv: {{ store.briefingModuleConfig.config.llm_provider || 'ollama' }}
              <template v-if="store.briefingModuleConfig.config.llm_model">
                / {{ store.briefingModuleConfig.config.llm_model }}
              </template>
            </span>
            <button
              v-if="llmForm.llm_provider === 'ollama'"
              class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-100 disabled:opacity-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700"
              :disabled="store.ollamaModelsLoading"
              @click="refreshOllamaModels"
            >
              {{ store.ollamaModelsLoading ? 'Aktualisiert...' : 'Modelle neu laden' }}
            </button>
          </div>
        </section>

        <section class="rounded-xl bg-white p-6 shadow-sm dark:bg-gray-800">
          <div class="flex items-center justify-between gap-4">
            <div>
              <h2 class="text-lg font-semibold text-go4-secondary dark:text-gray-100">
                Text-Briefing
              </h2>
              <p class="mt-1 text-sm text-go4-muted dark:text-gray-400">
                Liest verbundene E-Mails und Termine ein und erzeugt daraus eine kurze Zusammenfassung.
              </p>
            </div>
            <button
              class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white transition hover:bg-go4-primary/90 disabled:opacity-50"
              :disabled="store.personalRunning"
              @click="handleRunPersonalBriefing"
            >
              {{ store.personalRunning ? 'Laeuft...' : 'Jetzt Briefing erzeugen' }}
            </button>
          </div>

          <div
            v-if="store.personalRunResult"
            class="mt-5 space-y-4"
          >
            <div class="flex flex-wrap gap-3 text-xs text-go4-muted dark:text-gray-400">
              <span>E-Mails: {{ store.personalRunResult.sections?.email?.items_count || 0 }}</span>
              <span>Termine: {{ store.personalRunResult.sections?.calendar?.items_count || 0 }}</span>
              <span>Text via: {{ store.personalRunResult.briefing_generated_by || '-' }}</span>
            </div>

            <div class="rounded-lg bg-gray-50 p-4 dark:bg-gray-900/40">
              <p class="whitespace-pre-line text-sm leading-6 text-go4-secondary dark:text-gray-100">
                {{ store.personalRunResult.briefing_text || 'Noch kein Text-Briefing erzeugt.' }}
              </p>
            </div>

            <div
              v-if="store.personalRunResult.errors?.length"
              class="rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-400"
            >
              {{ store.personalRunResult.errors.join(' | ') }}
            </div>
          </div>
        </section>
      </div>
    </div>

    <!-- Sources Tab -->
    <div
      v-if="activeTab === 'sources'"
      class="mt-6"
    >
      <div
        v-if="store.sourcesLoading"
        class="flex items-center justify-center py-12"
      >
        <span class="text-go4-muted dark:text-gray-400">Laden...</span>
      </div>

      <EmptyState
        v-else-if="store.sources.length === 0"
        title="Noch keine Quellen"
        description="Erstellen Sie eine Briefing-Quelle (RSS, Website, Kalender, etc.)."
      />

      <template v-else>
        <!-- Meine Quellen -->
        <div
          v-if="store.mySources.length > 0"
          class="mb-8"
        >
          <h3
            class="mb-3 text-sm font-semibold uppercase tracking-wider text-go4-muted dark:text-gray-400"
          >
            Meine Quellen
          </h3>
          <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            <div
              v-for="source in store.mySources"
              :key="source.id"
              class="rounded-lg bg-white p-5 shadow-sm transition hover:shadow-md dark:bg-gray-800"
            >
              <div class="flex items-start justify-between">
                <div class="min-w-0 flex-1">
                  <p class="text-base font-semibold text-go4-secondary dark:text-gray-100">
                    {{ source.name }}
                  </p>
                  <p class="mt-1 text-xs text-go4-muted dark:text-gray-400">
                    {{ sourceTypeLabels[source.source_type] || source.source_type }}
                  </p>
                </div>
                <span
                  class="ml-2 shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium"
                  :class="
                    source.active
                      ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                      : 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400'
                  "
                >
                  {{ source.active ? 'Aktiv' : 'Inaktiv' }}
                </span>
              </div>
              <!-- OAuth status for calendar/email -->
              <div
                v-if="['calendar', 'email'].includes(source.source_type)"
                class="mt-2"
              >
                <span
                  v-if="source.oauth_connected"
                  class="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700 dark:bg-green-900/30 dark:text-green-400"
                >
                  Verbunden
                  <span
                    v-if="source.oauth_email"
                    class="font-normal text-green-600 dark:text-green-500"
                  >
                    ({{ source.oauth_email }})
                  </span>
                </span>
                <span
                  v-else
                  class="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-500 dark:bg-gray-700 dark:text-gray-400"
                >
                  Nicht verbunden
                </span>
              </div>
              <p
                v-else-if="source.url"
                class="mt-2 truncate text-xs text-gray-400 dark:text-gray-500"
              >
                {{ source.url }}
              </p>
              <div class="mt-3 flex items-center gap-4 text-xs text-go4-muted dark:text-gray-400">
                <span>Alle {{ source.fetch_interval_hours }}h</span>
                <span v-if="source.last_fetched_at">
                  Letzter Fetch: {{ formatDate(source.last_fetched_at) }}
                </span>
                <span v-else>Noch nie gefetcht</span>
              </div>
              <div
                class="mt-4 flex items-center gap-2 border-t border-gray-100 pt-3 dark:border-gray-700"
              >
                <router-link
                  :to="`/briefing/sources/${source.id}/edit`"
                  class="rounded bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
                >
                  Bearbeiten
                </router-link>
                <button
                  :disabled="store.runningSource"
                  class="rounded bg-sky-100 px-2.5 py-1 text-xs font-medium text-sky-700 hover:bg-sky-200 disabled:opacity-50 dark:bg-sky-900/30 dark:text-sky-400 dark:hover:bg-sky-800/40"
                  @click="handleRunSource(source.id)"
                >
                  Jetzt fetchen
                </button>
                <button
                  class="rounded bg-red-100 px-2.5 py-1 text-xs font-medium text-red-700 hover:bg-red-200 dark:bg-red-900/30 dark:text-red-400 dark:hover:bg-red-800/40"
                  @click="handleDeleteSource(source.id)"
                >
                  Loeschen
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Organisation Quellen -->
        <div v-if="store.orgSources.length > 0">
          <h3
            class="mb-3 text-sm font-semibold uppercase tracking-wider text-go4-muted dark:text-gray-400"
          >
            Organisation
          </h3>
          <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            <div
              v-for="source in store.orgSources"
              :key="source.id"
              class="rounded-lg bg-white p-5 shadow-sm transition hover:shadow-md dark:bg-gray-800"
            >
              <div class="flex items-start justify-between">
                <div class="min-w-0 flex-1">
                  <p class="text-base font-semibold text-go4-secondary dark:text-gray-100">
                    {{ source.name }}
                  </p>
                  <p class="mt-1 text-xs text-go4-muted dark:text-gray-400">
                    {{ sourceTypeLabels[source.source_type] || source.source_type }}
                  </p>
                </div>
                <span
                  class="ml-2 shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium"
                  :class="
                    source.active
                      ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                      : 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400'
                  "
                >
                  {{ source.active ? 'Aktiv' : 'Inaktiv' }}
                </span>
              </div>
              <!-- OAuth status for calendar/email -->
              <div
                v-if="['calendar', 'email'].includes(source.source_type)"
                class="mt-2"
              >
                <span
                  v-if="source.oauth_connected"
                  class="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700 dark:bg-green-900/30 dark:text-green-400"
                >
                  Verbunden
                  <span
                    v-if="source.oauth_email"
                    class="font-normal text-green-600 dark:text-green-500"
                  >
                    ({{ source.oauth_email }})
                  </span>
                </span>
                <span
                  v-else
                  class="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-500 dark:bg-gray-700 dark:text-gray-400"
                >
                  Nicht verbunden
                </span>
              </div>
              <p
                v-else-if="source.url"
                class="mt-2 truncate text-xs text-gray-400 dark:text-gray-500"
              >
                {{ source.url }}
              </p>
              <div class="mt-3 flex items-center gap-4 text-xs text-go4-muted dark:text-gray-400">
                <span>Alle {{ source.fetch_interval_hours }}h</span>
                <span v-if="source.last_fetched_at">
                  Letzter Fetch: {{ formatDate(source.last_fetched_at) }}
                </span>
                <span v-else>Noch nie gefetcht</span>
              </div>
              <div
                class="mt-4 flex items-center gap-2 border-t border-gray-100 pt-3 dark:border-gray-700"
              >
                <template v-if="authStore.isAdmin">
                  <router-link
                    :to="`/briefing/sources/${source.id}/edit`"
                    class="rounded bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
                  >
                    Bearbeiten
                  </router-link>
                  <button
                    :disabled="store.runningSource"
                    class="rounded bg-sky-100 px-2.5 py-1 text-xs font-medium text-sky-700 hover:bg-sky-200 disabled:opacity-50 dark:bg-sky-900/30 dark:text-sky-400 dark:hover:bg-sky-800/40"
                    @click="handleRunSource(source.id)"
                  >
                    Jetzt fetchen
                  </button>
                  <button
                    class="rounded bg-red-100 px-2.5 py-1 text-xs font-medium text-red-700 hover:bg-red-200 dark:bg-red-900/30 dark:text-red-400 dark:hover:bg-red-800/40"
                    @click="handleDeleteSource(source.id)"
                  >
                    Loeschen
                  </button>
                </template>
                <button
                  v-else
                  :disabled="store.runningSource"
                  class="rounded bg-sky-100 px-2.5 py-1 text-xs font-medium text-sky-700 hover:bg-sky-200 disabled:opacity-50 dark:bg-sky-900/30 dark:text-sky-400 dark:hover:bg-sky-800/40"
                  @click="handleRunSource(source.id)"
                >
                  Jetzt fetchen
                </button>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- Findings Tab -->
    <div
      v-else-if="activeTab === 'findings'"
      class="mt-6"
    >
      <!-- Filters -->
      <div class="mb-4 flex flex-wrap items-center gap-3">
        <select
          v-model="statusFilter"
          class="rounded-lg border border-gray-300 px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
        >
          <option value="">
            Alle Status
          </option>
          <option value="new">
            Neu
          </option>
          <option value="used">
            Verwendet
          </option>
          <option value="dismissed">
            Verworfen
          </option>
        </select>
        <select
          v-model="sourceTypeFilter"
          class="rounded-lg border border-gray-300 px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
        >
          <option value="">
            Alle Typen
          </option>
          <option value="rss">
            RSS
          </option>
          <option value="website">
            Website
          </option>
          <option value="websearch">
            Websuche
          </option>
          <option value="calendar">
            Kalender
          </option>
          <option value="email">
            E-Mail
          </option>
          <option value="kpi">
            KPI
          </option>
        </select>
      </div>

      <div
        v-if="store.findingsLoading"
        class="flex items-center justify-center py-12"
      >
        <span class="text-go4-muted dark:text-gray-400">Laden...</span>
      </div>

      <EmptyState
        v-else-if="filteredFindings().length === 0"
        title="Keine Findings"
        description="Erstellen Sie Quellen und fetchen Sie diese, um Findings zu erhalten."
      />

      <div
        v-else
        class="overflow-hidden rounded-lg bg-white shadow-sm dark:bg-gray-800"
      >
        <table class="w-full text-left text-sm">
          <thead
            class="border-b border-gray-100 bg-gray-50 text-xs uppercase tracking-wider text-go4-muted dark:border-gray-700 dark:bg-gray-800/50 dark:text-gray-400"
          >
            <tr>
              <th class="px-4 py-3 font-medium">
                Titel
              </th>
              <th class="hidden px-4 py-3 font-medium md:table-cell">
                Typ
              </th>
              <th class="px-4 py-3 font-medium">
                Status
              </th>
              <th class="hidden px-4 py-3 font-medium lg:table-cell">
                Gefunden
              </th>
              <th class="px-4 py-3 text-right font-medium">
                Aktionen
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50 dark:divide-gray-700">
            <tr
              v-for="finding in filteredFindings()"
              :key="finding.id"
              class="transition hover:bg-gray-50/50 dark:hover:bg-gray-700/50"
            >
              <td class="max-w-xs px-4 py-3">
                <a
                  v-if="finding.url"
                  :href="finding.url"
                  target="_blank"
                  class="font-medium text-go4-secondary hover:text-go4-primary dark:text-gray-100"
                >
                  {{ finding.title }}
                </a>
                <p
                  v-else
                  class="font-medium text-go4-secondary dark:text-gray-100"
                >
                  {{ finding.title }}
                </p>
                <p
                  v-if="finding.summary"
                  class="mt-0.5 line-clamp-1 text-xs text-go4-muted dark:text-gray-400"
                >
                  {{ finding.summary }}
                </p>
              </td>
              <td class="hidden px-4 py-3 text-xs text-go4-muted dark:text-gray-400 md:table-cell">
                {{ sourceTypeLabels[finding.source_type] || finding.source_type || '-' }}
              </td>
              <td class="px-4 py-3">
                <StatusBadge :status="finding.status" />
              </td>
              <td class="hidden px-4 py-3 text-xs text-gray-400 dark:text-gray-500 lg:table-cell">
                {{ formatDate(finding.found_at) }}
              </td>
              <td class="px-4 py-3">
                <div class="flex items-center justify-end gap-1.5">
                  <button
                    v-if="finding.status === 'new'"
                    class="rounded bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
                    @click="handleDismissFinding(finding.id)"
                  >
                    Verwerfen
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Channels Tab -->
    <div
      v-else-if="activeTab === 'channels'"
      class="mt-6"
    >
      <div
        v-if="store.loading"
        class="flex items-center justify-center py-12"
      >
        <span class="text-go4-muted dark:text-gray-400">Laden...</span>
      </div>

      <EmptyState
        v-else-if="store.channels.length === 0"
        title="Noch keine Channels"
        description="Erstellen Sie einen Briefing-Channel fuer Ihre erste Zielgruppe."
      />

      <template v-else>
        <!-- Meine Briefings -->
        <div
          v-if="store.myChannels.length > 0"
          class="mb-8"
        >
          <h3
            class="mb-3 text-sm font-semibold uppercase tracking-wider text-go4-muted dark:text-gray-400"
          >
            Meine Briefings
          </h3>
          <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            <div
              v-for="channel in store.myChannels"
              :key="channel.id"
              class="rounded-lg bg-white p-5 shadow-sm transition hover:shadow-md dark:bg-gray-800"
            >
              <div class="flex items-start justify-between">
                <div class="min-w-0 flex-1">
                  <router-link
                    :to="`/briefing/channels/${channel.id}`"
                    class="text-base font-semibold text-go4-secondary hover:text-go4-primary dark:text-gray-100"
                  >
                    {{ channel.name }}
                  </router-link>
                  <p
                    v-if="channel.target_audience"
                    class="mt-1 text-xs text-go4-muted dark:text-gray-400"
                  >
                    Zielgruppe: {{ channel.target_audience }}
                  </p>
                </div>
                <button
                  class="ml-2 shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium transition"
                  :class="
                    channel.active
                      ? 'bg-green-100 text-green-700 hover:bg-green-200 dark:bg-green-900/30 dark:text-green-400 dark:hover:bg-green-800/40'
                      : 'bg-gray-100 text-gray-500 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-400 dark:hover:bg-gray-600'
                  "
                  @click="handleToggle(channel)"
                >
                  {{ channel.active ? 'Aktiv' : 'Inaktiv' }}
                </button>
              </div>
              <p
                v-if="channel.description"
                class="mt-2 line-clamp-2 text-sm text-gray-500 dark:text-gray-400"
              >
                {{ channel.description }}
              </p>
              <div class="mt-4 flex items-center gap-4 text-xs text-go4-muted dark:text-gray-400">
                <span>{{ channel.episode_count || 0 }} Episoden</span>
                <span v-if="channel.output_format && channel.output_format !== 'audio'">
                  {{ channel.output_format === 'both' ? 'Audio + Text' : 'Text' }}
                </span>
              </div>
              <div
                class="mt-4 flex items-center gap-2 border-t border-gray-100 pt-3 dark:border-gray-700"
              >
                <router-link
                  :to="`/briefing/channels/${channel.id}`"
                  class="rounded bg-go4-primary/10 px-2.5 py-1 text-xs font-medium text-go4-primary hover:bg-go4-primary/20"
                >
                  Details
                </router-link>
                <router-link
                  :to="`/briefing/channels/${channel.id}/edit`"
                  class="rounded bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
                >
                  Bearbeiten
                </router-link>
                <button
                  class="rounded bg-red-100 px-2.5 py-1 text-xs font-medium text-red-700 hover:bg-red-200 dark:bg-red-900/30 dark:text-red-400 dark:hover:bg-red-800/40"
                  @click="handleDeleteChannel(channel.id)"
                >
                  Loeschen
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Org-Vorlagen -->
        <div v-if="store.orgChannels.length > 0">
          <h3
            class="mb-3 text-sm font-semibold uppercase tracking-wider text-go4-muted dark:text-gray-400"
          >
            Org-Vorlagen
          </h3>
          <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            <div
              v-for="channel in store.orgChannels"
              :key="channel.id"
              class="rounded-lg bg-white p-5 shadow-sm transition hover:shadow-md dark:bg-gray-800"
            >
              <div class="flex items-start justify-between">
                <div class="min-w-0 flex-1">
                  <router-link
                    :to="`/briefing/channels/${channel.id}`"
                    class="text-base font-semibold text-go4-secondary hover:text-go4-primary dark:text-gray-100"
                  >
                    {{ channel.name }}
                  </router-link>
                  <p
                    v-if="channel.target_audience"
                    class="mt-1 text-xs text-go4-muted dark:text-gray-400"
                  >
                    Zielgruppe: {{ channel.target_audience }}
                  </p>
                </div>
                <button
                  class="ml-2 shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium transition"
                  :class="
                    channel.active
                      ? 'bg-green-100 text-green-700 hover:bg-green-200 dark:bg-green-900/30 dark:text-green-400 dark:hover:bg-green-800/40'
                      : 'bg-gray-100 text-gray-500 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-400 dark:hover:bg-gray-600'
                  "
                  @click="authStore.isAdmin && handleToggle(channel)"
                >
                  {{ channel.active ? 'Aktiv' : 'Inaktiv' }}
                </button>
              </div>
              <p
                v-if="channel.description"
                class="mt-2 line-clamp-2 text-sm text-gray-500 dark:text-gray-400"
              >
                {{ channel.description }}
              </p>
              <div class="mt-4 flex items-center gap-4 text-xs text-go4-muted dark:text-gray-400">
                <span>{{ channel.episode_count || 0 }} Episoden</span>
                <span>{{ channel.subscriber_count || 0 }} Abonnenten</span>
                <span v-if="channel.output_format && channel.output_format !== 'audio'">
                  {{ channel.output_format === 'both' ? 'Audio + Text' : 'Text' }}
                </span>
              </div>
              <div
                class="mt-4 flex items-center gap-2 border-t border-gray-100 pt-3 dark:border-gray-700"
              >
                <router-link
                  :to="`/briefing/channels/${channel.id}`"
                  class="rounded bg-go4-primary/10 px-2.5 py-1 text-xs font-medium text-go4-primary hover:bg-go4-primary/20"
                >
                  Details
                </router-link>
                <button
                  class="rounded bg-sky-100 px-2.5 py-1 text-xs font-medium text-sky-700 hover:bg-sky-200 dark:bg-sky-900/30 dark:text-sky-400 dark:hover:bg-sky-800/40"
                  @click="handleCloneChannel(channel)"
                >
                  Anpassen
                </button>
                <template v-if="authStore.isAdmin">
                  <router-link
                    :to="`/briefing/channels/${channel.id}/edit`"
                    class="rounded bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
                  >
                    Bearbeiten
                  </router-link>
                  <button
                    class="rounded bg-red-100 px-2.5 py-1 text-xs font-medium text-red-700 hover:bg-red-200 dark:bg-red-900/30 dark:text-red-400 dark:hover:bg-red-800/40"
                    @click="handleDeleteChannel(channel.id)"
                  >
                    Loeschen
                  </button>
                </template>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- Speakers Tab -->
    <div
      v-else-if="activeTab === 'speakers'"
      class="mt-6"
    >
      <div
        v-if="store.speakersLoading"
        class="flex items-center justify-center py-12"
      >
        <span class="text-go4-muted dark:text-gray-400">Laden...</span>
      </div>

      <template v-else>
        <!-- Upload Form (Admin only) -->
        <div
          v-if="authStore.isAdmin"
          class="mb-6 rounded-lg bg-white p-5 shadow-sm dark:bg-gray-800"
        >
          <h3 class="mb-4 text-sm font-semibold text-go4-secondary dark:text-gray-100">
            Neuen Sprecher hochladen
          </h3>
          <form
            class="space-y-4"
            @submit.prevent="handleUploadSpeaker"
          >
            <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
              <div>
                <label class="block text-xs font-medium text-go4-muted dark:text-gray-400">Name *</label>
                <input
                  v-model="speakerName"
                  required
                  class="mt-1 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-800 focus:border-go4-primary focus:ring-1 focus:ring-go4-primary dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
                  placeholder="Thomas"
                >
              </div>
              <div>
                <label class="block text-xs font-medium text-go4-muted dark:text-gray-400">Sprache</label>
                <select
                  v-model="speakerLanguage"
                  class="mt-1 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-800 focus:border-go4-primary focus:ring-1 focus:ring-go4-primary dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
                >
                  <option value="de">
                    Deutsch
                  </option>
                  <option value="en">
                    Englisch
                  </option>
                </select>
              </div>
              <div>
                <label class="block text-xs font-medium text-go4-muted dark:text-gray-400">WAV-Datei * (6-30s)</label>
                <input
                  type="file"
                  accept=".wav"
                  class="mt-1 block w-full text-sm text-gray-500 file:mr-3 file:rounded file:border-0 file:bg-go4-primary/10 file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-go4-primary dark:text-gray-400"
                  @change="onSpeakerFileChange"
                >
              </div>
            </div>
            <div>
              <label class="block text-xs font-medium text-go4-muted dark:text-gray-400">Beschreibung</label>
              <input
                v-model="speakerDescription"
                class="mt-1 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-800 focus:border-go4-primary focus:ring-1 focus:ring-go4-primary dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
                placeholder="Maennliche Stimme, ruhig und professionell"
              >
            </div>
            <button
              type="submit"
              :disabled="speakerUploading || !speakerName || !speakerFile"
              class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white transition hover:bg-go4-primary/90 disabled:opacity-50"
            >
              {{ speakerUploading ? 'Hochladen...' : 'Sprecher hochladen' }}
            </button>
          </form>
        </div>

        <!-- Speaker List -->
        <EmptyState
          v-if="store.speakers.length === 0"
          title="Noch keine Sprecher"
          description="Laden Sie eine WAV-Datei (6-30s) hoch, um XTTS Voice Cloning zu nutzen."
        />
        <div
          v-else
          class="overflow-hidden rounded-lg bg-white shadow-sm dark:bg-gray-800"
        >
          <table class="w-full text-left text-sm">
            <thead
              class="border-b border-gray-100 bg-gray-50 text-xs uppercase tracking-wider text-go4-muted dark:border-gray-700 dark:bg-gray-800/50 dark:text-gray-400"
            >
              <tr>
                <th class="px-4 py-3 font-medium">
                  Name
                </th>
                <th class="px-4 py-3 font-medium">
                  Sprache
                </th>
                <th class="hidden px-4 py-3 font-medium md:table-cell">
                  Dauer
                </th>
                <th class="hidden px-4 py-3 font-medium md:table-cell">
                  Groesse
                </th>
                <th class="px-4 py-3 text-right font-medium">
                  Aktionen
                </th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-50 dark:divide-gray-700">
              <tr
                v-for="speaker in store.speakers"
                :key="speaker.id"
                class="transition hover:bg-gray-50/50 dark:hover:bg-gray-700/50"
              >
                <td class="px-4 py-3">
                  <p class="font-medium text-go4-secondary dark:text-gray-100">
                    {{ speaker.name }}
                  </p>
                  <p
                    v-if="speaker.description"
                    class="mt-0.5 text-xs text-go4-muted dark:text-gray-400"
                  >
                    {{ speaker.description }}
                  </p>
                </td>
                <td class="px-4 py-3 text-xs text-go4-muted dark:text-gray-400">
                  {{ speaker.language === 'de' ? 'Deutsch' : 'Englisch' }}
                </td>
                <td
                  class="hidden px-4 py-3 text-xs text-go4-muted dark:text-gray-400 md:table-cell"
                >
                  {{ formatDuration(speaker.duration_seconds) }}
                </td>
                <td
                  class="hidden px-4 py-3 text-xs text-go4-muted dark:text-gray-400 md:table-cell"
                >
                  {{ formatFileSize(speaker.file_size_bytes) }}
                </td>
                <td class="px-4 py-3">
                  <div class="flex items-center justify-end gap-1.5">
                    <a
                      :href="speakerPreviewUrl(speaker.id)"
                      target="_blank"
                      class="rounded bg-sky-100 px-2.5 py-1 text-xs font-medium text-sky-700 hover:bg-sky-200 dark:bg-sky-900/30 dark:text-sky-400 dark:hover:bg-sky-800/40"
                    >
                      Vorhoeren
                    </a>
                    <button
                      v-if="authStore.isAdmin"
                      class="rounded bg-red-100 px-2.5 py-1 text-xs font-medium text-red-700 hover:bg-red-200 dark:bg-red-900/30 dark:text-red-400 dark:hover:bg-red-800/40"
                      @click="handleDeleteSpeaker(speaker.id)"
                    >
                      Loeschen
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </div>
  </div>
</template>
