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
const providers = [
  { key: 'microsoft', label: 'Microsoft 365', icon: '📧', enabled: true },
  { key: 'google', label: 'Google Workspace', icon: '📬', enabled: true },
  { key: 'imap', label: 'IMAP / SMTP', icon: '📨', enabled: false },
  { key: 'exchange', label: 'Exchange (On-Premise)', icon: '🏢', enabled: false },
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

  // Close provider menu on click outside
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

async function handleConnectAccount(providerKey) {
  const provider = providers.find((p) => p.key === providerKey)
  if (!provider?.enabled) return
  showProviderMenu.value = false
  await store.connectAccount(providerKey)
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
  if (level === 'high') return 'bg-red-100 text-red-800'
  if (level === 'medium') return 'bg-yellow-100 text-yellow-800'
  return 'bg-green-100 text-green-800'
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

function statusClass(status) {
  if (status === 'connected') return 'bg-green-100 text-green-800'
  if (status === 'error') return 'bg-red-100 text-red-800'
  if (status === 'pending') return 'bg-yellow-100 text-yellow-800'
  return 'bg-gray-100 text-gray-600'
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
    <PageHeader title="Assistant" subtitle="Persoenlicher KI-Assistent fuer Mail, Kalender und Voice" />

    <!-- Error -->
    <div v-if="store.error" class="mb-4 rounded-lg bg-red-50 p-4 text-red-700">
      {{ store.error }}
    </div>

    <!-- Tabs -->
    <div class="border-b border-gray-200 mb-6">
      <nav class="-mb-px flex gap-6">
        <router-link
          v-for="tab in tabs"
          :key="tab.key"
          :to="tab.route"
          class="border-b-2 pb-3 text-sm font-medium whitespace-nowrap"
          :class="
            activeTab === tab.key
              ? 'border-go4-primary text-go4-primary'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
          "
        >
          {{ tab.label }}
        </router-link>
      </nav>
    </div>

    <!-- ═══ Dashboard ═══ -->
    <div v-if="activeTab === 'dashboard'" class="space-y-6">
      <div v-if="store.loading" class="text-gray-500">Laden...</div>
      <div v-else-if="store.dashboardStats" class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div class="rounded-lg border border-gray-200 bg-white p-5">
          <p class="text-sm text-gray-500">Verbundene Quellen</p>
          <p class="mt-1 text-2xl font-semibold">{{ store.dashboardStats.connected_sources }}</p>
        </div>
        <div class="rounded-lg border border-gray-200 bg-white p-5">
          <p class="text-sm text-gray-500">Erfasste Items</p>
          <p class="mt-1 text-2xl font-semibold">{{ store.dashboardStats.total_items }}</p>
        </div>
        <div class="rounded-lg border border-gray-200 bg-white p-5">
          <p class="text-sm text-gray-500">Aktive Regeln</p>
          <p class="mt-1 text-2xl font-semibold">{{ store.dashboardStats.active_rules }}</p>
        </div>
        <div class="rounded-lg border border-gray-200 bg-white p-5">
          <p class="text-sm text-gray-500">Offene Freigaben</p>
          <p class="mt-1 text-2xl font-semibold">{{ store.dashboardStats.pending_actions }}</p>
        </div>
      </div>
    </div>

    <!-- ═══ Konten ═══ -->
    <div v-if="activeTab === 'accounts'" class="space-y-4">
      <div class="flex items-center justify-between">
        <p class="text-sm text-gray-500">
          {{ store.sources.length }} Konto{{ store.sources.length !== 1 ? 'en' : '' }} verbunden
        </p>
        <div class="relative">
          <button
            class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary/90"
            @click="showProviderMenu = !showProviderMenu"
          >
            + Konto verbinden
          </button>
          <div
            v-if="showProviderMenu"
            class="absolute right-0 z-10 mt-2 w-56 rounded-lg border border-gray-200 bg-white py-1 shadow-lg"
          >
            <button
              v-for="p in providers"
              :key="p.key"
              class="flex w-full items-center gap-3 px-4 py-2.5 text-left text-sm text-gray-700 hover:bg-gray-50"
              :disabled="!p.enabled"
              :class="{ 'opacity-40 cursor-not-allowed': !p.enabled }"
              @click="handleConnectAccount(p.key)"
            >
              <span class="text-lg">{{ p.icon }}</span>
              <div>
                <span class="font-medium">{{ p.label }}</span>
                <span
                  v-if="!p.enabled"
                  class="ml-1 text-xs text-gray-400"
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
      <div v-else class="space-y-3">
        <div
          v-for="source in store.sources"
          :key="source.id"
          class="rounded-lg border border-gray-200 bg-white p-4"
        >
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <span class="text-2xl">{{ providerIcon(source.connection?.provider) }}</span>
              <div>
                <p class="font-medium text-gray-900">
                  {{ source.connection?.connected_email || 'Unbekannt' }}
                </p>
                <p class="text-sm text-gray-500">
                  {{ providerLabel(source.connection?.provider) }}
                </p>
              </div>
            </div>
            <div class="flex items-center gap-3">
              <span
                class="rounded-full px-2.5 py-0.5 text-xs font-medium"
                :class="statusClass(source.connection?.status)"
              >
                {{ statusLabel(source.connection?.status) }}
              </span>
              <button
                class="text-sm text-red-600 hover:text-red-800"
                @click="handleDeleteSource(source.id)"
              >
                Entfernen
              </button>
            </div>
          </div>
          <div class="mt-3 flex items-center justify-between">
            <div class="flex gap-2 text-xs">
              <span
                v-if="source.briefing_enabled"
                class="rounded bg-blue-100 px-2 py-0.5 text-blue-800"
              >
                Briefing
              </span>
              <span
                v-if="source.voice_enabled"
                class="rounded bg-purple-100 px-2 py-0.5 text-purple-800"
              >
                Voice
              </span>
              <span
                v-if="source.reply_enabled"
                class="rounded bg-green-100 px-2 py-0.5 text-green-800"
              >
                Reply
              </span>
              <span
                v-if="source.autopilot_enabled"
                class="rounded bg-orange-100 px-2 py-0.5 text-orange-800"
              >
                Autopilot
              </span>
            </div>
            <p
              v-if="source.connection?.last_synced_at"
              class="text-xs text-gray-400"
            >
              Sync: {{ formatDate(source.connection.last_synced_at) }}
            </p>
          </div>
          <p
            v-if="source.connection?.last_error"
            class="mt-2 rounded bg-red-50 px-3 py-1.5 text-xs text-red-600"
          >
            {{ source.connection.last_error }}
          </p>
        </div>
      </div>
    </div>

    <!-- ═══ Regeln ═══ -->
    <div v-if="activeTab === 'rules'" class="space-y-4">
      <div class="flex items-center justify-between">
        <p class="text-sm text-gray-500">{{ store.rules.length }} Regeln</p>
        <button
          class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary/90"
          @click="showRuleForm = !showRuleForm"
        >
          + Neue Regel
        </button>
      </div>

      <!-- New Rule Form -->
      <div v-if="showRuleForm" class="rounded-lg border border-gray-200 bg-white p-4 space-y-3">
        <div>
          <label class="block text-sm font-medium text-gray-700">Name</label>
          <input
            v-model="ruleForm.name"
            type="text"
            class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            placeholder="z.B. Newsletter archivieren"
          />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-sm font-medium text-gray-700">Aktion</label>
            <select v-model="ruleForm.action_type" class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm">
              <option value="label">Labeln</option>
              <option value="archive">Archivieren</option>
              <option value="move">Verschieben</option>
              <option value="prioritize">Priorisieren</option>
              <option value="mute">Stumm schalten</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700">Risikostufe</label>
            <select v-model="ruleForm.risk_level" class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm">
              <option value="low">Niedrig</option>
              <option value="medium">Mittel</option>
              <option value="high">Hoch</option>
            </select>
          </div>
        </div>
        <div class="flex gap-2">
          <button
            class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary/90"
            :disabled="!ruleForm.name"
            @click="handleCreateRule"
          >
            Speichern
          </button>
          <button
            class="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
            @click="showRuleForm = false"
          >
            Abbrechen
          </button>
        </div>
      </div>

      <!-- Rules List -->
      <EmptyState v-if="store.rules.length === 0 && !showRuleForm" title="Keine Regeln" description="Erstelle Regeln fuer automatische Mail-Triage." />
      <div v-else class="space-y-2">
        <div
          v-for="rule in store.rules"
          :key="rule.id"
          class="flex items-center justify-between rounded-lg border border-gray-200 bg-white p-4"
        >
          <div class="flex items-center gap-3">
            <button
              class="h-5 w-5 rounded border"
              :class="rule.enabled ? 'bg-go4-primary border-go4-primary' : 'border-gray-300'"
              @click="handleToggleRule(rule)"
            />
            <div>
              <p class="font-medium" :class="rule.enabled ? 'text-gray-900' : 'text-gray-400'">{{ rule.name }}</p>
              <div class="mt-1 flex gap-2 text-xs">
                <span class="rounded px-2 py-0.5" :class="riskBadgeClass(rule.risk_level)">{{ rule.risk_level }}</span>
                <span class="text-gray-400">{{ rule.action_type }}</span>
                <span v-if="rule.origin !== 'manual'" class="text-gray-400 italic">{{ rule.origin }}</span>
              </div>
            </div>
          </div>
          <button class="text-sm text-red-600 hover:text-red-800" @click="handleDeleteRule(rule.id)">
            Loeschen
          </button>
        </div>
      </div>
    </div>

    <!-- ═══ Aktivitaet ═══ -->
    <div v-if="activeTab === 'activity'" class="space-y-4">
      <div v-if="store.loading" class="text-gray-500">Laden...</div>
      <EmptyState v-else-if="store.items.length === 0" title="Keine Aktivitaet" description="Sobald Quellen verbunden sind, erscheinen hier Mail- und Kalender-Items." />
      <div v-else class="space-y-2">
        <div
          v-for="item in store.items"
          :key="item.id"
          class="rounded-lg border border-gray-200 bg-white p-4"
        >
          <div class="flex items-center justify-between">
            <div>
              <p class="font-medium text-gray-900">{{ item.title || '(kein Betreff)' }}</p>
              <p class="text-sm text-gray-500">
                {{ item.sender }} &middot; {{ item.item_type }} &middot; {{ formatDate(item.occurred_at) }}
              </p>
            </div>
            <span
              class="rounded px-2 py-0.5 text-xs"
              :class="item.status === 'new' ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-600'"
            >
              {{ item.status }}
            </span>
          </div>
          <p v-if="item.summary" class="mt-2 text-sm text-gray-600">{{ item.summary }}</p>
        </div>
      </div>
    </div>

    <!-- ═══ Freigaben ═══ -->
    <div v-if="activeTab === 'approvals'" class="space-y-4">
      <EmptyState v-if="store.pendingActions.length === 0" title="Keine offenen Freigaben" description="Aktionen, die eine Bestaetigung erfordern, erscheinen hier." />
      <div v-else class="space-y-2">
        <div
          v-for="action in store.pendingActions"
          :key="action.id"
          class="flex items-center justify-between rounded-lg border border-gray-200 bg-white p-4"
        >
          <div>
            <p class="font-medium text-gray-900">{{ action.action_type }}</p>
            <div class="mt-1 flex gap-2 text-xs">
              <span class="rounded px-2 py-0.5" :class="riskBadgeClass(action.risk_level)">{{ action.risk_level }}</span>
              <span class="text-gray-400">Item #{{ action.item_id }}</span>
            </div>
          </div>
          <div class="flex gap-2">
            <button
              class="rounded-lg bg-green-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-green-700"
              @click="handleApprove(action.id)"
            >
              Freigeben
            </button>
            <button
              class="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
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
      <div v-if="store.loading" class="text-gray-500">Laden...</div>
      <div v-else-if="profileLoaded" class="max-w-2xl space-y-6">
        <!-- General -->
        <div class="rounded-lg border border-gray-200 bg-white p-5 space-y-4">
          <h3 class="text-lg font-medium text-gray-900">Allgemein</h3>
          <div class="flex items-center gap-3">
            <input id="active" v-model="profileForm.active" type="checkbox" class="h-4 w-4 rounded border-gray-300" />
            <label for="active" class="text-sm text-gray-700">Assistant aktiv</label>
          </div>
          <div class="flex items-center gap-3">
            <input id="briefing" v-model="profileForm.briefing_enabled" type="checkbox" class="h-4 w-4 rounded border-gray-300" />
            <label for="briefing" class="text-sm text-gray-700">Briefing aktiviert</label>
          </div>
          <div class="flex items-center gap-3">
            <input id="voice" v-model="profileForm.voice_enabled" type="checkbox" class="h-4 w-4 rounded border-gray-300" />
            <label for="voice" class="text-sm text-gray-700">Voice aktiviert</label>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700">Zeitzone</label>
              <input v-model="profileForm.timezone" type="text" class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm" />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700">Briefing-Zeit</label>
              <input v-model="profileForm.delivery_time" type="text" class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm" placeholder="07:00" />
            </div>
          </div>
        </div>

        <!-- LLM -->
        <div class="rounded-lg border border-gray-200 bg-white p-5 space-y-4">
          <h3 class="text-lg font-medium text-gray-900">LLM</h3>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700">Provider</label>
              <select v-model="profileForm.llm_provider" class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm">
                <option value="ollama">Ollama (lokal)</option>
                <option value="anthropic">Anthropic</option>
                <option value="openai">OpenAI</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700">Modell</label>
              <input v-model="profileForm.llm_model" type="text" class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm" placeholder="z.B. llama3" />
            </div>
          </div>
        </div>

        <!-- TTS / STT -->
        <div class="rounded-lg border border-gray-200 bg-white p-5 space-y-4">
          <h3 class="text-lg font-medium text-gray-900">Audio</h3>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700">TTS Provider</label>
              <select v-model="profileForm.tts_provider" class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm">
                <option value="piper">Piper</option>
                <option value="xtts">XTTS</option>
                <option value="disabled">Deaktiviert</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700">STT Provider</label>
              <select v-model="profileForm.stt_provider" class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm">
                <option value="faster-whisper">faster-whisper (lokal)</option>
                <option value="openai">OpenAI Whisper</option>
                <option value="disabled">Deaktiviert</option>
              </select>
            </div>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700">Max Items pro Briefing</label>
            <input v-model.number="profileForm.max_items_per_run" type="number" min="1" max="200" class="mt-1 block w-32 rounded-md border border-gray-300 px-3 py-2 text-sm" />
          </div>
        </div>

        <button
          class="rounded-lg bg-go4-primary px-6 py-2.5 text-sm font-medium text-white hover:bg-go4-primary/90"
          @click="saveProfile"
        >
          Einstellungen speichern
        </button>
      </div>
    </div>
  </div>
</template>
