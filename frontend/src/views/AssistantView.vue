<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useAssistantStore } from '@/stores/assistant'
import PageHeader from '@/components/ui/PageHeader.vue'
import Breadcrumb from '@/components/ui/Breadcrumb.vue'
import EmptyState from '@/components/ui/EmptyState.vue'

const route = useRoute()
const store = useAssistantStore()

const activeTab = computed(() => route.meta?.tab || 'dashboard')

const tabs = [
  { key: 'dashboard', label: 'Mein Assistant', route: '/assistant/dashboard' },
  { key: 'accounts', label: 'Konten', route: '/assistant/accounts' },
  { key: 'rules', label: 'Regeln', route: '/assistant/rules' },
  { key: 'activity', label: 'Aktivitaet', route: '/assistant/activity' },
  { key: 'approvals', label: 'Freigaben', route: '/assistant/approvals' },
  { key: 'settings', label: 'Einstellungen', route: '/assistant/settings' },
  { key: 'test', label: 'Test', route: '/assistant/test' },
]

// Rule form
const showRuleForm = ref(false)
const ruleForm = ref({
  name: '',
  action_type: 'label',
  risk_level: 'low',
  match_criteria_json: null,
  action_payload_json: null,
})

// Provider menu
const showProviderMenu = ref(false)
const showAccountTypeDialog = ref(false)
const showSharedInput = ref(false)
const selectedProvider = ref(null)
const sharedMailboxAddress = ref('')
const providers = [
  { key: 'microsoft', label: 'Microsoft 365', icon: '📧', enabled: true, supportsShared: true },
  { key: 'google', label: 'Google Workspace', icon: '📬', enabled: true, supportsShared: false },
  { key: 'imap', label: 'IMAP / SMTP', icon: '📨', enabled: false, supportsShared: false },
  { key: 'exchange', label: 'Exchange (On-Premise)', icon: '🏢', enabled: false, supportsShared: true },
]

// Profile form
const profileForm = ref({})
const profileLoaded = ref(false)

onMounted(async () => {
  await store.fetchDashboard()
  if (activeTab.value === 'accounts') await store.fetchSources()
  if (activeTab.value === 'rules') await store.fetchRules()
  if (activeTab.value === 'activity') await store.fetchItems()
  if (activeTab.value === 'approvals') await store.fetchPendingActions()
  if (activeTab.value === 'settings') await loadProfile()

  document.addEventListener('click', closeProviderMenu)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', closeProviderMenu)
})

function closeProviderMenu(e) {
  if (showProviderMenu.value && !e.target.closest('.relative')) {
    showProviderMenu.value = false
  }
}

watch(activeTab, async (tab) => {
  if (tab === 'dashboard') await store.fetchDashboard()
  if (tab === 'accounts') await store.fetchSources()
  if (tab === 'rules') await store.fetchRules()
  if (tab === 'activity') await store.fetchItems()
  if (tab === 'approvals') await store.fetchPendingActions()
  if (tab === 'settings' && !profileLoaded.value) await loadProfile()
})

async function loadProfile() {
  await store.fetchProfile()
  if (store.profile) {
    profileForm.value = { ...store.profile }
    profileLoaded.value = true
  }
}

async function saveProfile() {
  await store.updateProfile({
    active: profileForm.value.active,
    briefing_enabled: profileForm.value.briefing_enabled,
    voice_enabled: profileForm.value.voice_enabled,
    autopilot_enabled: profileForm.value.autopilot_enabled,
    timezone: profileForm.value.timezone,
    delivery_time: profileForm.value.delivery_time,
    llm_provider: profileForm.value.llm_provider,
    llm_model: profileForm.value.llm_model,
    tts_provider: profileForm.value.tts_provider,
    tts_voice: profileForm.value.tts_voice,
    stt_provider: profileForm.value.stt_provider,
    max_items_per_run: profileForm.value.max_items_per_run,
    default_reply_mode: profileForm.value.default_reply_mode,
  })
}

async function handleCreateRule() {
  await store.addRule(ruleForm.value)
  showRuleForm.value = false
  ruleForm.value = {
    name: '',
    action_type: 'label',
    risk_level: 'low',
    match_criteria_json: null,
    action_payload_json: null,
  }
}

async function handleDeleteRule(id) {
  if (confirm('Regel wirklich loeschen?')) {
    await store.removeRule(id)
  }
}

async function handleToggleRule(rule) {
  await store.editRule(rule.id, { enabled: !rule.enabled })
}

function handleProviderSelect(providerKey) {
  const provider = providers.find((p) => p.key === providerKey)
  if (!provider?.enabled) return
  showProviderMenu.value = false

  if (provider.supportsShared) {
    selectedProvider.value = providerKey
    sharedMailboxAddress.value = ''
    showSharedInput.value = false
    showAccountTypeDialog.value = true
  } else {
    store.connectAccount(providerKey)
  }
}

async function handleConnectPersonal() {
  showAccountTypeDialog.value = false
  await store.connectAccount(selectedProvider.value)
}

async function handleConnectShared() {
  const addr = sharedMailboxAddress.value.trim()
  if (!addr) return
  showAccountTypeDialog.value = false
  await store.connectAccount(selectedProvider.value, addr)
}

async function handleApprove(id) {
  await store.approveAction(id)
}

async function handleReject(id) {
  await store.rejectAction(id)
}

async function handleDeleteSource(id) {
  if (confirm('Quelle wirklich entfernen?')) {
    await store.removeSource(id)
  }
}

function riskBadgeClass(level) {
  if (level === 'high') return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
  if (level === 'medium') return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400'
  return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
}

function formatDate(d) {
  if (!d) return '-'
  return new Date(d).toLocaleString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function providerIcon(provider) {
  const icons = {
    microsoft_graph: '📧',
    google_workspace: '📬',
    imap: '📨',
    exchange: '🏢',
  }
  return icons[provider] || '📩'
}

function providerLabel(provider) {
  const labels = {
    microsoft_graph: 'Microsoft 365',
    google_workspace: 'Google Workspace',
    imap: 'IMAP / SMTP',
    exchange: 'Exchange',
  }
  return labels[provider] || provider || 'Unbekannt'
}

async function handleTrigger(step) {
  if (step === 'intake') await store.triggerIntake()
  else if (step === 'classify') await store.triggerClassify()
  else if (step === 'rules') await store.triggerRules()
  else if (step === 'briefing') await store.triggerBriefing()
  else if (step === 'full') await store.triggerFullPipeline()
}

async function handleApplySuggestion(suggestion) {
  await store.addRule({
    name: suggestion.name,
    action_type: suggestion.action_type,
    risk_level: suggestion.risk_level || 'low',
    match_criteria_json: suggestion.match_criteria,
    priority: suggestion.priority || 10,
  })
  await store.fetchRuleSuggestions()
}

function resultDetails(r) {
  const details = {}
  if (r.sources !== undefined) details.Quellen = r.sources
  if (r.events_created !== undefined) details.Events = r.events_created
  if (r.items_created !== undefined) details.Items = r.items_created
  if (r.items_classified !== undefined) details.Klassifiziert = r.items_classified
  if (r.items_processed !== undefined) details.Verarbeitet = r.items_processed
  if (r.actions_created !== undefined) details.Aktionen = r.actions_created
  if (r.decisions_created !== undefined) details.Entscheidungen = r.decisions_created
  return details
}

function formatTime(d) {
  if (!d) return ''
  return new Date(d).toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function isShared(source) {
  const conn = source.connection
  if (!conn) return false
  return conn.mailbox_address && conn.mailbox_address !== conn.connected_email
}

function statusClass(status) {
  if (status === 'connected') return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
  if (status === 'error') return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
  if (status === 'pending') return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400'
  return 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
}

function statusLabel(status) {
  const labels = {
    connected: 'Verbunden',
    active: 'Aktiv',
    error: 'Fehler',
    pending: 'Ausstehend',
  }
  return labels[status] || status || 'Unbekannt'
}
</script>

<template>
  <div>
    <Breadcrumb class="mb-4" />
    <PageHeader
      title="Assistant"
      subtitle="Persoenlicher KI-Assistent fuer Mail, Kalender und Voice"
    />

    <!-- Error -->
    <div
      v-if="store.error"
      class="mb-4 rounded-lg bg-red-50 p-4 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-400"
    >
      {{ store.error }}
    </div>

    <!-- Tabs -->
    <div class="border-b border-gray-200 dark:border-gray-700 mb-6">
      <nav class="-mb-px flex items-center gap-6">
        <router-link
          v-for="tab in tabs"
          :key="tab.key"
          :to="tab.route"
          class="border-b-2 px-1 pb-3 text-sm font-medium whitespace-nowrap transition"
          :class="
            activeTab === tab.key
              ? 'border-go4-primary text-go4-primary'
              : 'border-transparent text-go4-muted dark:text-gray-400 hover:border-gray-300 dark:hover:border-gray-600 hover:text-go4-secondary dark:hover:text-gray-100'
          "
        >
          {{ tab.label }}
        </router-link>
      </nav>
    </div>

    <!-- ═══ Kontotyp-Dialog ═══ -->
    <div
      v-if="showAccountTypeDialog"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      @click.self="showAccountTypeDialog = false"
    >
      <div class="w-full max-w-md rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800">
        <h3 class="text-lg font-semibold text-go4-secondary dark:text-gray-100">
          Kontotyp waehlen
        </h3>
        <p class="mt-1 text-sm text-go4-muted dark:text-gray-400">
          Welche Art von Konto moechtest du verbinden?
        </p>
        <div class="mt-5 space-y-3">
          <button
            class="flex w-full items-center gap-3 rounded-lg border border-gray-200 dark:border-gray-600 p-4 text-left transition hover:bg-gray-50 dark:hover:bg-gray-700"
            @click="handleConnectPersonal"
          >
            <span class="text-2xl">👤</span>
            <div>
              <p class="font-medium text-go4-secondary dark:text-gray-100">
                Persoenliches Konto
              </p>
              <p class="text-sm text-go4-muted dark:text-gray-400">
                Dein eigenes Mail- und Kalenderkonto
              </p>
            </div>
          </button>
          <button
            class="flex w-full items-center gap-3 rounded-lg border border-gray-200 dark:border-gray-600 p-4 text-left transition hover:bg-gray-50 dark:hover:bg-gray-700"
            @click="showSharedInput = true"
          >
            <span class="text-2xl">👥</span>
            <div>
              <p class="font-medium text-go4-secondary dark:text-gray-100">
                Shared Mailbox
              </p>
              <p class="text-sm text-go4-muted dark:text-gray-400">
                Gemeinsames Postfach (z.B. info@firma.de)
              </p>
            </div>
          </button>
          <div
            v-if="showSharedInput"
            class="rounded-lg border border-gray-200 dark:border-gray-600 bg-go4-surface dark:bg-gray-700 p-4"
          >
            <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">
              Shared Mailbox Adresse
            </label>
            <input
              v-model="sharedMailboxAddress"
              type="email"
              placeholder="info@firma.de"
              class="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
              @keyup.enter="handleConnectShared"
            />
            <button
              class="mt-3 rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white transition hover:bg-go4-primary/90 disabled:opacity-50"
              :disabled="!sharedMailboxAddress.trim()"
              @click="handleConnectShared"
            >
              Verbinden
            </button>
          </div>
        </div>
        <button
          class="mt-4 text-sm text-go4-muted dark:text-gray-400 transition hover:text-go4-secondary dark:hover:text-gray-100"
          @click="showAccountTypeDialog = false"
        >
          Abbrechen
        </button>
      </div>
    </div>

    <!-- ═══ Dashboard ═══ -->
    <div v-if="activeTab === 'dashboard'" class="space-y-6">
      <div
        v-if="store.loading"
        class="flex items-center justify-center p-8"
      >
        <span class="text-go4-muted dark:text-gray-400">Laden...</span>
      </div>
      <div
        v-else-if="store.dashboardStats"
        class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4"
      >
        <div class="rounded-lg bg-white p-4 shadow-sm dark:bg-gray-800">
          <p class="text-xs font-medium text-go4-muted dark:text-gray-400">
            Verbundene Quellen
          </p>
          <p class="mt-1 text-2xl font-semibold text-go4-secondary dark:text-gray-100">
            {{ store.dashboardStats.connected_sources }}
          </p>
        </div>
        <div class="rounded-lg bg-white p-4 shadow-sm dark:bg-gray-800">
          <p class="text-xs font-medium text-go4-muted dark:text-gray-400">
            Erfasste Items
          </p>
          <p class="mt-1 text-2xl font-semibold text-go4-secondary dark:text-gray-100">
            {{ store.dashboardStats.total_items }}
          </p>
        </div>
        <div class="rounded-lg bg-white p-4 shadow-sm dark:bg-gray-800">
          <p class="text-xs font-medium text-go4-muted dark:text-gray-400">
            Aktive Regeln
          </p>
          <p class="mt-1 text-2xl font-semibold text-go4-secondary dark:text-gray-100">
            {{ store.dashboardStats.active_rules }}
          </p>
        </div>
        <div class="rounded-lg bg-white p-4 shadow-sm dark:bg-gray-800">
          <p class="text-xs font-medium text-go4-muted dark:text-gray-400">
            Offene Freigaben
          </p>
          <p class="mt-1 text-2xl font-semibold text-go4-secondary dark:text-gray-100">
            {{ store.dashboardStats.pending_actions }}
          </p>
        </div>
      </div>
    </div>

    <!-- ═══ Konten ═══ -->
    <div v-if="activeTab === 'accounts'" class="space-y-4">
      <div class="flex items-center justify-between">
        <p class="text-sm text-go4-muted dark:text-gray-400">
          {{ store.sources.length }} Konto{{ store.sources.length !== 1 ? 'en' : '' }} verbunden
        </p>
        <div class="relative">
          <button
            class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white transition hover:bg-go4-primary/90"
            @click="showProviderMenu = !showProviderMenu"
          >
            + Konto verbinden
          </button>
          <div
            v-if="showProviderMenu"
            class="absolute right-0 z-10 mt-2 w-56 rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 py-1 shadow-lg"
          >
            <button
              v-for="p in providers"
              :key="p.key"
              class="flex w-full items-center gap-3 px-4 py-2.5 text-left text-sm text-gray-700 dark:text-gray-200 transition hover:bg-gray-50 dark:hover:bg-gray-700"
              :disabled="!p.enabled"
              :class="{ 'opacity-40 cursor-not-allowed': !p.enabled }"
              @click="handleProviderSelect(p.key)"
            >
              <span class="text-lg">{{ p.icon }}</span>
              <div>
                <span class="font-medium">{{ p.label }}</span>
                <span
                  v-if="!p.enabled"
                  class="ml-1 text-xs text-go4-muted dark:text-gray-500"
                >
                  (bald)
                </span>
              </div>
            </button>
          </div>
        </div>
      </div>

      <EmptyState
        v-if="store.sources.length === 0"
        title="Keine Quellen verbunden"
        description="Verbinde ein Mail- oder Kalenderkonto, um den Assistant zu nutzen."
      />
      <div v-else class="space-y-2">
        <div
          v-for="source in store.sources"
          :key="source.id"
          class="flex items-center justify-between rounded-lg bg-white px-4 py-2.5 shadow-sm dark:bg-gray-800"
        >
          <div class="flex items-center gap-3">
            <span class="text-lg">{{ providerIcon(source.connection?.provider) }}</span>
            <div>
              <div class="flex items-center gap-2">
                <span class="text-sm font-medium text-go4-secondary dark:text-gray-100">
                  {{ source.connection?.account_label || source.connection?.mailbox_address || 'Unbekannt' }}
                </span>
                <span
                  class="rounded-full px-2 py-0.5 text-xs font-medium"
                  :class="statusClass(source.connection?.status)"
                >
                  {{ statusLabel(source.connection?.status) }}
                </span>
                <span
                  v-if="source.briefing_enabled"
                  class="rounded bg-blue-100 px-1.5 py-0.5 text-xs text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                >
                  Briefing
                </span>
                <span
                  v-if="source.voice_enabled"
                  class="rounded bg-purple-100 px-1.5 py-0.5 text-xs text-purple-700 dark:bg-purple-900/30 dark:text-purple-400"
                >
                  Voice
                </span>
                <span
                  v-if="source.reply_enabled"
                  class="rounded bg-green-100 px-1.5 py-0.5 text-xs text-green-700 dark:bg-green-900/30 dark:text-green-400"
                >
                  Reply
                </span>
                <span
                  v-if="source.autopilot_enabled"
                  class="rounded bg-orange-100 px-1.5 py-0.5 text-xs text-orange-700 dark:bg-orange-900/30 dark:text-orange-400"
                >
                  Autopilot
                </span>
              </div>
              <p class="text-xs text-go4-muted dark:text-gray-400">
                {{ providerLabel(source.connection?.provider) }},
                {{ isShared(source) ? 'Shared' : 'Personal' }}
                <span v-if="source.connection?.last_synced_at">
                  &middot; Sync: {{ formatDate(source.connection.last_synced_at) }}
                </span>
              </p>
            </div>
          </div>
          <button
            class="text-xs text-red-500 transition hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
            @click="handleDeleteSource(source.id)"
          >
            Entfernen
          </button>
        </div>
      </div>
    </div>

    <!-- ═══ Regeln ═══ -->
    <div v-if="activeTab === 'rules'" class="space-y-4">
      <div class="flex items-center justify-between">
        <p class="text-sm text-go4-muted dark:text-gray-400">
          {{ store.rules.length }} Regeln
        </p>
        <button
          class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white transition hover:bg-go4-primary/90"
          @click="showRuleForm = !showRuleForm"
        >
          + Neue Regel
        </button>
      </div>

      <!-- New Rule Form -->
      <div
        v-if="showRuleForm"
        class="rounded-lg bg-white p-6 shadow-sm dark:bg-gray-800 space-y-4"
      >
        <div>
          <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">
            Name
          </label>
          <input
            v-model="ruleForm.name"
            type="text"
            class="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
            placeholder="z.B. Newsletter archivieren"
          />
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">
              Aktion
            </label>
            <select
              v-model="ruleForm.action_type"
              class="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
            >
              <option value="label">
                Labeln
              </option>
              <option value="archive">
                Archivieren
              </option>
              <option value="move">
                Verschieben
              </option>
              <option value="prioritize">
                Priorisieren
              </option>
              <option value="mute">
                Stumm schalten
              </option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">
              Risikostufe
            </label>
            <select
              v-model="ruleForm.risk_level"
              class="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
            >
              <option value="low">
                Niedrig
              </option>
              <option value="medium">
                Mittel
              </option>
              <option value="high">
                Hoch
              </option>
            </select>
          </div>
        </div>
        <div class="flex gap-2">
          <button
            class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white transition hover:bg-go4-primary/90 disabled:opacity-50"
            :disabled="!ruleForm.name"
            @click="handleCreateRule"
          >
            Speichern
          </button>
          <button
            class="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-200 transition hover:bg-gray-50 dark:hover:bg-gray-600"
            @click="showRuleForm = false"
          >
            Abbrechen
          </button>
        </div>
      </div>

      <!-- Rules List -->
      <EmptyState
        v-if="store.rules.length === 0 && !showRuleForm"
        title="Keine Regeln"
        description="Erstelle Regeln fuer automatische Mail-Triage."
      />
      <div v-else class="space-y-2">
        <div
          v-for="rule in store.rules"
          :key="rule.id"
          class="flex items-center justify-between rounded-lg bg-white p-4 shadow-sm dark:bg-gray-800"
        >
          <div class="flex items-center gap-3">
            <button
              class="h-5 w-5 rounded border transition"
              :class="rule.enabled ? 'bg-go4-primary border-go4-primary' : 'border-gray-300 dark:border-gray-600'"
              @click="handleToggleRule(rule)"
            />
            <div>
              <p
                class="text-sm font-medium"
                :class="rule.enabled ? 'text-go4-secondary dark:text-gray-100' : 'text-go4-muted dark:text-gray-500'"
              >
                {{ rule.name }}
              </p>
              <div class="mt-1 flex gap-2 text-xs">
                <span
                  class="rounded-full px-2 py-0.5 font-medium"
                  :class="riskBadgeClass(rule.risk_level)"
                >
                  {{ rule.risk_level }}
                </span>
                <span class="text-go4-muted dark:text-gray-400">
                  {{ rule.action_type }}
                </span>
                <span
                  v-if="rule.origin !== 'manual'"
                  class="italic text-go4-muted dark:text-gray-500"
                >
                  {{ rule.origin }}
                </span>
              </div>
            </div>
          </div>
          <button
            class="text-sm text-red-500 transition hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
            @click="handleDeleteRule(rule.id)"
          >
            Loeschen
          </button>
        </div>
      </div>
    </div>

    <!-- ═══ Aktivitaet ═══ -->
    <div v-if="activeTab === 'activity'" class="space-y-4">
      <div
        v-if="store.loading"
        class="flex items-center justify-center p-8"
      >
        <span class="text-go4-muted dark:text-gray-400">Laden...</span>
      </div>
      <EmptyState
        v-else-if="store.items.length === 0"
        title="Keine Aktivitaet"
        description="Sobald Quellen verbunden sind, erscheinen hier Mail- und Kalender-Items."
      />
      <div v-else class="space-y-2">
        <div
          v-for="item in store.items"
          :key="item.id"
          class="rounded-lg bg-white p-4 shadow-sm dark:bg-gray-800"
        >
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-go4-secondary dark:text-gray-100">
                {{ item.title || '(kein Betreff)' }}
              </p>
              <p class="text-xs text-go4-muted dark:text-gray-400">
                {{ item.sender }} &middot; {{ item.item_type }} &middot; {{ formatDate(item.occurred_at) }}
              </p>
            </div>
            <span
              class="rounded-full px-2.5 py-0.5 text-xs font-medium"
              :class="item.status === 'new' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400' : item.status === 'classified' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'"
            >
              {{ item.status }}
            </span>
          </div>
          <p
            v-if="item.summary"
            class="mt-2 text-sm text-gray-700 dark:text-gray-300"
          >
            {{ item.summary }}
          </p>
        </div>
      </div>
    </div>

    <!-- ═══ Freigaben ═══ -->
    <div v-if="activeTab === 'approvals'" class="space-y-4">
      <EmptyState
        v-if="store.pendingActions.length === 0"
        title="Keine offenen Freigaben"
        description="Aktionen, die eine Bestaetigung erfordern, erscheinen hier."
      />
      <div v-else class="space-y-2">
        <div
          v-for="action in store.pendingActions"
          :key="action.id"
          class="flex items-center justify-between rounded-lg bg-white p-4 shadow-sm dark:bg-gray-800"
        >
          <div>
            <p class="text-sm font-medium text-go4-secondary dark:text-gray-100">
              {{ action.action_type }}
            </p>
            <div class="mt-1 flex gap-2 text-xs">
              <span
                class="rounded-full px-2 py-0.5 font-medium"
                :class="riskBadgeClass(action.risk_level)"
              >
                {{ action.risk_level }}
              </span>
              <span class="text-go4-muted dark:text-gray-400">
                Item #{{ action.item_id }}
              </span>
            </div>
          </div>
          <div class="flex gap-2">
            <button
              class="rounded-lg bg-green-600 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-green-700"
              @click="handleApprove(action.id)"
            >
              Freigeben
            </button>
            <button
              class="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-200 transition hover:bg-gray-50 dark:hover:bg-gray-600"
              @click="handleReject(action.id)"
            >
              Ablehnen
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ═══ Einstellungen ═══ -->
    <div v-if="activeTab === 'settings'" class="space-y-6">
      <div
        v-if="store.loading"
        class="flex items-center justify-center p-8"
      >
        <span class="text-go4-muted dark:text-gray-400">Laden...</span>
      </div>
      <div
        v-else-if="profileLoaded"
        class="max-w-2xl space-y-6"
      >
        <!-- General -->
        <section class="rounded-lg bg-white p-6 shadow-sm dark:bg-gray-800 space-y-4">
          <h2 class="text-lg font-semibold text-go4-secondary dark:text-gray-100">
            Allgemein
          </h2>
          <div class="flex items-center gap-3">
            <input
              id="active"
              v-model="profileForm.active"
              type="checkbox"
              class="h-4 w-4 rounded border-gray-300 text-go4-primary focus:ring-go4-primary"
            />
            <label
              for="active"
              class="text-sm text-gray-700 dark:text-gray-300"
            >
              Assistant aktiv
            </label>
          </div>
          <div class="flex items-center gap-3">
            <input
              id="briefing"
              v-model="profileForm.briefing_enabled"
              type="checkbox"
              class="h-4 w-4 rounded border-gray-300 text-go4-primary focus:ring-go4-primary"
            />
            <label
              for="briefing"
              class="text-sm text-gray-700 dark:text-gray-300"
            >
              Briefing aktiviert
            </label>
          </div>
          <div class="flex items-center gap-3">
            <input
              id="voice"
              v-model="profileForm.voice_enabled"
              type="checkbox"
              class="h-4 w-4 rounded border-gray-300 text-go4-primary focus:ring-go4-primary"
            />
            <label
              for="voice"
              class="text-sm text-gray-700 dark:text-gray-300"
            >
              Voice aktiviert
            </label>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">
                Zeitzone
              </label>
              <input
                v-model="profileForm.timezone"
                type="text"
                class="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">
                Briefing-Zeit
              </label>
              <input
                v-model="profileForm.delivery_time"
                type="text"
                class="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
                placeholder="07:00"
              />
            </div>
          </div>
        </section>

        <!-- LLM -->
        <section class="rounded-lg bg-white p-6 shadow-sm dark:bg-gray-800 space-y-4">
          <h2 class="text-lg font-semibold text-go4-secondary dark:text-gray-100">
            LLM
          </h2>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">
                Provider
              </label>
              <select
                v-model="profileForm.llm_provider"
                class="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
              >
                <option value="ollama">
                  Ollama (lokal)
                </option>
                <option value="anthropic">
                  Anthropic
                </option>
                <option value="openai">
                  OpenAI
                </option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">
                Modell
              </label>
              <input
                v-model="profileForm.llm_model"
                type="text"
                class="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
                placeholder="z.B. llama3"
              />
            </div>
          </div>
        </section>

        <!-- TTS / STT -->
        <section class="rounded-lg bg-white p-6 shadow-sm dark:bg-gray-800 space-y-4">
          <h2 class="text-lg font-semibold text-go4-secondary dark:text-gray-100">
            Audio
          </h2>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">
                TTS Provider
              </label>
              <select
                v-model="profileForm.tts_provider"
                class="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
              >
                <option value="piper">
                  Piper
                </option>
                <option value="xtts">
                  XTTS
                </option>
                <option value="disabled">
                  Deaktiviert
                </option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">
                STT Provider
              </label>
              <select
                v-model="profileForm.stt_provider"
                class="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
              >
                <option value="faster-whisper">
                  faster-whisper (lokal)
                </option>
                <option value="openai">
                  OpenAI Whisper
                </option>
                <option value="disabled">
                  Deaktiviert
                </option>
              </select>
            </div>
          </div>
          <div>
            <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">
              Max Items pro Briefing
            </label>
            <input
              v-model.number="profileForm.max_items_per_run"
              type="number"
              min="1"
              max="200"
              class="mt-1 block w-32 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
            />
          </div>
        </section>

        <button
          class="rounded-lg bg-go4-primary px-6 py-2.5 text-sm font-medium text-white transition hover:bg-go4-primary/90"
          @click="saveProfile"
        >
          Einstellungen speichern
        </button>
      </div>
    </div>

    <!-- ═══ Test ═══ -->
    <div v-if="activeTab === 'test'" class="space-y-6">
      <!-- Pipeline Buttons -->
      <section class="rounded-lg bg-white p-6 shadow-sm dark:bg-gray-800">
        <h2 class="text-lg font-semibold text-go4-secondary dark:text-gray-100">
          Pipeline manuell steuern
        </h2>
        <p class="mt-1 text-sm text-go4-muted dark:text-gray-400">
          Einzelne Schritte oder die komplette Pipeline ausfuehren.
        </p>
        <div class="mt-4 flex flex-wrap gap-3">
          <button
            class="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-200 transition hover:bg-gray-50 dark:hover:bg-gray-600"
            @click="handleTrigger('intake')"
          >
            1. Mails abrufen
          </button>
          <button
            class="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-200 transition hover:bg-gray-50 dark:hover:bg-gray-600"
            @click="handleTrigger('classify')"
          >
            2. Klassifizieren
          </button>
          <button
            class="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-200 transition hover:bg-gray-50 dark:hover:bg-gray-600"
            @click="handleTrigger('rules')"
          >
            3. Regeln anwenden
          </button>
          <button
            class="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-200 transition hover:bg-gray-50 dark:hover:bg-gray-600"
            @click="handleTrigger('briefing')"
          >
            4. Briefing erzeugen
          </button>
          <button
            class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white transition hover:bg-go4-primary/90"
            @click="handleTrigger('full')"
          >
            Alles ausfuehren (1-4)
          </button>
        </div>
      </section>

      <!-- Briefing Output -->
      <section
        v-if="store.briefingText"
        class="rounded-lg bg-white p-6 shadow-sm dark:bg-gray-800"
      >
        <h2 class="text-lg font-semibold text-go4-secondary dark:text-gray-100">
          Briefing
        </h2>
        <pre class="mt-3 whitespace-pre-wrap rounded-lg bg-go4-surface dark:bg-gray-900 p-4 text-sm text-gray-700 dark:text-gray-300">{{ store.briefingText }}</pre>
      </section>

      <!-- Log -->
      <section
        v-if="store.testResults.length"
        class="rounded-lg bg-white p-6 shadow-sm dark:bg-gray-800"
      >
        <h2 class="text-lg font-semibold text-go4-secondary dark:text-gray-100">
          Ergebnisse
        </h2>
        <div class="mt-3 space-y-2">
          <div
            v-for="(r, i) in store.testResults"
            :key="i"
            class="flex items-center justify-between rounded-lg bg-go4-surface dark:bg-gray-900 px-3 py-2 text-sm"
          >
            <div class="flex items-center gap-2">
              <span class="font-medium text-go4-secondary dark:text-gray-100">
                {{ r.action }}
              </span>
              <span
                v-for="(val, key) in resultDetails(r)"
                :key="key"
                class="text-go4-muted dark:text-gray-400"
              >
                {{ key }}: {{ val }}
              </span>
            </div>
            <span class="text-xs text-go4-muted dark:text-gray-500">
              {{ formatTime(r.time) }}
            </span>
          </div>
        </div>
      </section>

      <!-- Rule Suggestions -->
      <section class="rounded-lg bg-white p-6 shadow-sm dark:bg-gray-800">
        <div class="flex items-center justify-between">
          <h2 class="text-lg font-semibold text-go4-secondary dark:text-gray-100">
            Regelvorschlaege
          </h2>
          <button
            class="text-sm text-go4-primary transition hover:underline"
            @click="store.fetchRuleSuggestions()"
          >
            Aktualisieren
          </button>
        </div>
        <p
          v-if="!store.ruleSuggestions.length"
          class="mt-3 text-sm text-go4-muted dark:text-gray-400"
        >
          Keine Vorschlaege. Gib erst Feedback auf Items, dann werden hier Muster erkannt.
        </p>
        <div
          v-else
          class="mt-3 space-y-2"
        >
          <div
            v-for="(s, i) in store.ruleSuggestions"
            :key="i"
            class="flex items-center justify-between rounded-lg bg-go4-surface dark:bg-gray-900 px-3 py-2 text-sm"
          >
            <div>
              <p class="font-medium text-go4-secondary dark:text-gray-100">
                {{ s.name }}
              </p>
              <p class="text-xs text-go4-muted dark:text-gray-400">
                {{ s.reason }} &middot; Confidence: {{ Math.round((s.confidence || 0) * 100) }}%
              </p>
            </div>
            <button
              class="rounded-lg bg-go4-primary px-3 py-1 text-xs font-medium text-white transition hover:bg-go4-primary/90"
              @click="handleApplySuggestion(s)"
            >
              Uebernehmen
            </button>
          </div>
        </div>
      </section>

      <!-- Items with Feedback -->
      <section class="rounded-lg bg-white p-6 shadow-sm dark:bg-gray-800">
        <div class="flex items-center justify-between">
          <h2 class="text-lg font-semibold text-go4-secondary dark:text-gray-100">
            Items ({{ store.items.length }})
          </h2>
          <button
            class="text-sm text-go4-primary transition hover:underline"
            @click="store.fetchItems()"
          >
            Aktualisieren
          </button>
        </div>
        <div
          v-if="store.items.length"
          class="mt-3 space-y-2"
        >
          <div
            v-for="item in store.items"
            :key="item.id"
            class="rounded-lg border border-gray-100 dark:border-gray-700 bg-go4-surface dark:bg-gray-900 px-3 py-2"
          >
            <div class="flex items-center justify-between">
              <div>
                <span class="text-sm font-medium text-go4-secondary dark:text-gray-100">
                  {{ item.title || '(kein Betreff)' }}
                </span>
                <span class="ml-2 text-xs text-go4-muted dark:text-gray-400">
                  {{ item.sender }}
                </span>
              </div>
              <span
                class="rounded-full px-2.5 py-0.5 text-xs font-medium"
                :class="item.status === 'new' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' : item.status === 'classified' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'"
              >
                {{ item.status }}
              </span>
            </div>
            <div class="mt-1.5 flex gap-1.5">
              <button
                class="rounded bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700 transition hover:bg-green-200 dark:bg-green-900/30 dark:text-green-400 dark:hover:bg-green-900/50"
                @click="store.sendFeedback(item.id, { feedback_type: 'keep' })"
              >
                Behalten
              </button>
              <button
                class="rounded bg-yellow-100 px-2 py-0.5 text-xs font-medium text-yellow-700 transition hover:bg-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-400 dark:hover:bg-yellow-900/50"
                @click="store.sendFeedback(item.id, { feedback_type: 'ignore' })"
              >
                Ignorieren
              </button>
              <button
                class="rounded bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700 transition hover:bg-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:hover:bg-blue-900/50"
                @click="store.sendFeedback(item.id, { feedback_type: 'move' })"
              >
                Verschieben
              </button>
              <button
                class="rounded bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700 transition hover:bg-red-200 dark:bg-red-900/30 dark:text-red-400 dark:hover:bg-red-900/50"
                @click="store.sendFeedback(item.id, { feedback_type: 'delete' })"
              >
                Loeschen
              </button>
            </div>
          </div>
        </div>
        <p
          v-else
          class="mt-3 text-sm text-go4-muted dark:text-gray-400"
        >
          Keine Items. Fuehre zuerst "Mails abrufen" aus.
        </p>
      </section>
    </div>
  </div>
</template>
