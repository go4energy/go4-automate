<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useWhatsAppStore } from '@/stores/whatsapp'
import { usePipelineContext } from '@/stores/pipelineContext'
import PageHeader from '@/components/ui/PageHeader.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ModuleSettings from '@/components/settings/ModuleSettings.vue'

const router = useRouter()
const route = useRoute()
const store = useWhatsAppStore()
const pipelineCtx = usePipelineContext()

// Tab state from route
const activeTab = computed(() => route.meta?.tab || 'inbox')

const loading = ref(true)

// Tab definitions
const tabs = [
  { id: 'inbox', label: 'Inbox', icon: 'inbox', route: '/whatsapp/inbox' },
  { id: 'campaigns', label: 'Kampagnen', icon: 'speakerphone', route: '/whatsapp/campaigns' },
  { id: 'templates', label: 'Templates', icon: 'template', route: '/whatsapp/templates' },
  { id: 'accounts', label: 'Accounts', icon: 'cog', route: '/whatsapp/accounts' },
  { id: 'freigabe', label: 'Freigabe', icon: 'check-circle', route: '/whatsapp/freigabe' },
  { id: 'einstellungen', label: 'Einstellungen', icon: 'cog', route: '/whatsapp/einstellungen' }
]

// Format date
function formatDate(date) {
  if (!date) return '-'
  return new Date(date).toLocaleDateString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function formatRelativeTime(date) {
  if (!date) return ''
  const now = new Date()
  const d = new Date(date)
  const diffMs = now - d
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'Jetzt'
  if (diffMins < 60) return `${diffMins}m`
  if (diffHours < 24) return `${diffHours}h`
  if (diffDays < 7) return `${diffDays}d`
  return d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit' })
}

// Status badges
function getStatusClass(status) {
  const classes = {
    open: 'bg-green-100 text-green-700',
    closed: 'bg-gray-100 text-gray-700',
    draft: 'bg-gray-100 text-gray-700',
    scheduled: 'bg-blue-100 text-blue-700',
    sending: 'bg-yellow-100 text-yellow-700',
    sent: 'bg-green-100 text-green-700',
    active: 'bg-green-100 text-green-700',
    inactive: 'bg-gray-100 text-gray-700',
    error: 'bg-red-100 text-red-700',
    APPROVED: 'bg-green-100 text-green-700',
    PENDING: 'bg-yellow-100 text-yellow-700',
    REJECTED: 'bg-red-100 text-red-700'
  }
  return classes[status] || 'bg-gray-100 text-gray-700'
}

function getStatusLabel(status) {
  const labels = {
    open: 'Offen',
    closed: 'Geschlossen',
    draft: 'Entwurf',
    scheduled: 'Geplant',
    sending: 'Wird gesendet',
    sent: 'Gesendet',
    active: 'Aktiv',
    inactive: 'Inaktiv',
    error: 'Fehler',
    APPROVED: 'Genehmigt',
    PENDING: 'Ausstehend',
    REJECTED: 'Abgelehnt'
  }
  return labels[status] || status
}

// Actions
function openConversation(id) {
  router.push({ name: 'whatsapp-conversation', params: { id } })
}

function createCampaign() {
  router.push({ name: 'whatsapp-campaign-new' })
}

function viewCampaign(id) {
  router.push({ name: 'whatsapp-campaign-detail', params: { id } })
}

function editCampaign(id) {
  router.push({ name: 'whatsapp-campaign-edit', params: { id } })
}

function viewTemplate(id) {
  router.push({ name: 'whatsapp-template-detail', params: { id } })
}

function createAccount() {
  router.push({ name: 'whatsapp-account-new' })
}

function editAccount(id) {
  router.push({ name: 'whatsapp-account-edit', params: { id } })
}

async function deleteCampaign(campaign) {
  if (!confirm(`Kampagne "${campaign.name}" wirklich löschen?`)) return
  await store.removeCampaign(campaign.id)
}

async function deleteAccount(account) {
  if (!confirm(`Account "${account.name}" wirklich löschen?`)) return
  await store.removeAccount(account.id)
}

async function verifyAccount(account) {
  try {
    await store.checkAccount(account.id)
    await store.fetchAccounts()
  } catch (err) {
    // Error handled by store
  }
}

async function syncTemplatesForAccount(accountId) {
  try {
    await store.syncAccountTemplates(accountId)
  } catch (err) {
    // Error handled by store
  }
}

// Load data — scoped to the globally selected pipeline.
async function loadData() {
  loading.value = true
  const pid = pipelineCtx.activePipelineId || undefined
  await Promise.all([
    store.fetchConversations(),
    store.fetchCampaigns({ pipeline_id: pid }),
    store.fetchTemplates(),
    store.fetchAccounts(),
    store.fetchDashboard(),
    store.fetchEngagementActions()
  ])
  loading.value = false
}

// Engagement Brain Functions
async function refreshEngagementActions() {
  await store.fetchEngagementActions()
}

async function generateActionContent(actionId) {
  await store.generateContent(actionId)
}

async function executeAction(actionId, content) {
  await store.executeAction(actionId, content)
}

onMounted(async () => {
  await pipelineCtx.ensurePipelines()
  loadData()
})

watch(
  () => pipelineCtx.activePipelineId,
  () => loadData(),
)
</script>

<template>
  <div>
    <PageHeader
      title="WhatsApp"
    >
      <template #actions>
        <button
          v-if="activeTab === 'campaigns'"
          class="btn btn-primary"
          @click="createCampaign"
        >
          <svg
            class="w-5 h-5 mr-2"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M12 4v16m8-8H4"
            />
          </svg>
          Neue Kampagne
        </button>
        <button
          v-if="activeTab === 'accounts'"
          class="btn btn-primary"
          @click="createAccount"
        >
          <svg
            class="w-5 h-5 mr-2"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M12 4v16m8-8H4"
            />
          </svg>
          Neuer Account
        </button>
      </template>
    </PageHeader>

    <!-- Dashboard Stats -->
    <div
      v-if="store.dashboard && activeTab === 'inbox'"
      class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6"
    >
      <div class="bg-white rounded-lg shadow p-4">
        <div class="text-sm text-gray-500">
          Offene Chats
        </div>
        <div class="text-2xl font-semibold text-gray-900">
          {{ store.dashboard.open_conversations }}
        </div>
      </div>
      <div class="bg-white rounded-lg shadow p-4">
        <div class="text-sm text-gray-500">
          Gesendet (24h)
        </div>
        <div class="text-2xl font-semibold text-gray-900">
          {{ store.dashboard.messages_sent_24h }}
        </div>
      </div>
      <div class="bg-white rounded-lg shadow p-4">
        <div class="text-sm text-gray-500">
          Empfangen (24h)
        </div>
        <div class="text-2xl font-semibold text-gray-900">
          {{ store.dashboard.messages_received_24h }}
        </div>
      </div>
      <div class="bg-white rounded-lg shadow p-4">
        <div class="text-sm text-gray-500">
          Leserate (7d)
        </div>
        <div class="text-2xl font-semibold text-gray-900">
          {{ store.dashboard.read_rate_7d }}%
        </div>
      </div>
    </div>

    <!-- Tabs -->
    <div class="border-b border-gray-200 mb-6">
      <nav class="-mb-px flex space-x-8">
        <router-link
          v-for="tab in tabs"
          :key="tab.id"
          :to="tab.route"
          :class="[
            'py-4 px-1 border-b-2 font-medium text-sm whitespace-nowrap',
            activeTab === tab.id
              ? 'border-green-500 text-green-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
          ]"
        >
          {{ tab.label }}
        </router-link>
      </nav>
    </div>

    <!-- Loading -->
    <div
      v-if="loading"
      class="flex items-center justify-center py-12"
    >
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600" />
    </div>

    <!-- Inbox Tab -->
    <div v-else-if="activeTab === 'inbox'">
      <EmptyState
        v-if="store.conversations.length === 0"
        title="Keine Conversations"
      />
      <div
        v-else
        class="bg-white rounded-lg shadow divide-y divide-gray-200"
      >
        <div
          v-for="conv in store.conversations"
          :key="conv.id"
          class="p-4 hover:bg-gray-50 cursor-pointer flex items-center space-x-4"
          @click="openConversation(conv.id)"
        >
          <div
            class="flex-shrink-0 w-12 h-12 bg-green-100 rounded-full flex items-center justify-center"
          >
            <span class="text-green-700 font-medium text-lg">
              {{ (conv.contact_name || conv.phone)?.[0]?.toUpperCase() || '?' }}
            </span>
          </div>
          <div class="flex-1 min-w-0">
            <div class="flex items-center justify-between">
              <p class="font-medium text-gray-900 truncate">
                {{ conv.contact_name || conv.phone }}
              </p>
              <span class="text-xs text-gray-500">
                {{ formatRelativeTime(conv.last_message_at) }}
              </span>
            </div>
            <p class="text-sm text-gray-500 truncate">
              {{ conv.last_message_preview || 'Keine Nachrichten' }}
            </p>
          </div>
          <div
            v-if="conv.unread_count > 0"
            class="flex-shrink-0"
          >
            <span
              class="inline-flex items-center justify-center w-6 h-6 bg-green-500 text-white text-xs font-medium rounded-full"
            >
              {{ conv.unread_count }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Campaigns Tab -->
    <div v-else-if="activeTab === 'campaigns'">
      <p class="mb-3 text-xs text-gray-500 dark:text-gray-400">
        WhatsApp-spezifische Campaigns. Pipeline-zentrierte Kampagnen verwaltest du im
        <router-link
          to="/engagement"
          class="text-go4-primary hover:text-go4-primary-dark"
        >
          Engagement-Modul
        </router-link>; die ausgewählte Pipeline kannst du oben im Header wechseln.
      </p>
      <EmptyState
        v-if="store.campaigns.length === 0"
        title="Keine Kampagnen"
        action-text="Kampagne erstellen"
        @action="createCampaign"
      />
      <div
        v-else
        class="bg-white rounded-lg shadow overflow-hidden"
      >
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Name
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Status
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Gesendet
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Zugestellt
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Gelesen
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Erstellt
              </th>
              <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                Aktionen
              </th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr
              v-for="campaign in store.campaigns"
              :key="campaign.id"
              class="hover:bg-gray-50 cursor-pointer"
              @click="viewCampaign(campaign.id)"
            >
              <td class="px-6 py-4 whitespace-nowrap font-medium text-gray-900">
                {{ campaign.name }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span
                  :class="[
                    'px-2 py-1 text-xs font-medium rounded-full',
                    getStatusClass(campaign.status)
                  ]"
                >
                  {{ getStatusLabel(campaign.status) }}
                </span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-gray-500">
                {{ campaign.sent_count }} / {{ campaign.total_recipients }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-gray-500">
                {{ campaign.delivered_count }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-gray-500">
                {{ campaign.read_count }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-gray-500">
                {{ formatDate(campaign.created_at) }}
              </td>
              <td
                class="px-6 py-4 whitespace-nowrap text-right"
                @click.stop
              >
                <button
                  v-if="campaign.status === 'draft'"
                  class="text-gray-400 hover:text-gray-600 mr-2"
                  title="Bearbeiten"
                  @click="editCampaign(campaign.id)"
                >
                  <svg
                    class="w-5 h-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                    />
                  </svg>
                </button>
                <button
                  v-if="campaign.status === 'draft'"
                  class="text-gray-400 hover:text-red-600"
                  title="Löschen"
                  @click="deleteCampaign(campaign)"
                >
                  <svg
                    class="w-5 h-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                    />
                  </svg>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Templates Tab -->
    <div v-else-if="activeTab === 'templates'">
      <div class="mb-4 flex justify-end">
        <select
          v-if="store.accounts.length > 0"
          class="input w-64"
          @change="syncTemplatesForAccount($event.target.value)"
        >
          <option value="">
            Templates synchronisieren...
          </option>
          <option
            v-for="account in store.accounts"
            :key="account.id"
            :value="account.id"
          >
            {{ account.name }}
          </option>
        </select>
      </div>
      <EmptyState
        v-if="store.templates.length === 0"
        title="Keine Templates"
      />
      <div
        v-else
        class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
      >
        <div
          v-for="template in store.templates"
          :key="template.id"
          class="bg-white rounded-lg shadow p-4 hover:shadow-md transition-shadow cursor-pointer"
          @click="viewTemplate(template.id)"
        >
          <div class="flex items-start justify-between">
            <div>
              <h3 class="font-medium text-gray-900">
                {{ template.name }}
              </h3>
              <p class="text-sm text-gray-500 mt-1">
                {{ template.language }} - {{ template.category }}
              </p>
            </div>
            <span
              :class="[
                'px-2 py-1 text-xs font-medium rounded-full',
                getStatusClass(template.status)
              ]"
            >
              {{ getStatusLabel(template.status) }}
            </span>
          </div>
          <div class="mt-4">
            <span class="text-xs text-gray-400">{{ formatDate(template.created_at) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Accounts Tab -->
    <div v-else-if="activeTab === 'accounts'">
      <EmptyState
        v-if="store.accounts.length === 0"
        title="Keine Accounts"
        action-text="Account hinzufügen"
        @action="createAccount"
      />
      <div
        v-else
        class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
      >
        <div
          v-for="account in store.accounts"
          :key="account.id"
          class="bg-white rounded-lg shadow p-4"
        >
          <div class="flex items-start justify-between">
            <div>
              <div class="flex items-center space-x-2">
                <span
                  :class="[
                    'px-2 py-1 text-xs font-medium rounded-full',
                    getStatusClass(account.status)
                  ]"
                >
                  {{ getStatusLabel(account.status) }}
                </span>
              </div>
              <p class="font-medium text-gray-900 mt-2">
                {{ account.name }}
              </p>
              <p class="text-sm text-gray-500">
                {{ account.phone_number }}
              </p>
            </div>
            <div class="w-10 h-10 bg-green-500 rounded-full flex items-center justify-center">
              <svg
                class="w-6 h-6 text-white"
                fill="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"
                />
              </svg>
            </div>
          </div>
          <div class="mt-4 pt-4 border-t border-gray-100 flex items-center justify-between">
            <span class="text-sm text-gray-500">
              Heute: {{ account.messages_sent_today }} / {{ account.daily_limit }}
            </span>
            <div class="flex space-x-2">
              <button
                class="text-gray-400 hover:text-blue-600"
                title="Verifizieren"
                @click="verifyAccount(account)"
              >
                <svg
                  class="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </button>
              <button
                class="text-gray-400 hover:text-gray-600"
                title="Bearbeiten"
                @click="editAccount(account.id)"
              >
                <svg
                  class="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                  />
                </svg>
              </button>
              <button
                class="text-gray-400 hover:text-red-600"
                title="Löschen"
                @click="deleteAccount(account)"
              >
                <svg
                  class="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                  />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Freigabe Tab (Engagement Brain Actions) -->
    <div v-else-if="activeTab === 'freigabe'">
      <div class="mb-6 flex items-center justify-between">
        <div>
          <h2 class="text-lg font-semibold text-go4-secondary dark:text-white">
            Freigabe-Queue
          </h2>
          <p class="text-sm text-go4-muted dark:text-gray-400">
            Vom Engagement Brain generierte WhatsApp-Aktionen zur Freigabe
          </p>
        </div>
        <button
          class="flex items-center gap-2 rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark"
          @click="refreshEngagementActions"
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
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
          Aktualisieren
        </button>
      </div>

      <!-- Loading State -->
      <div
        v-if="loading"
        class="flex items-center justify-center py-12"
      >
        <span class="text-go4-muted dark:text-gray-400">Laden...</span>
      </div>

      <!-- Empty State -->
      <EmptyState
        v-else-if="store.engagementActions.length === 0"
        title="Keine Aktionen"
        icon="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
      />

      <!-- Actions List -->
      <div
        v-else
        class="space-y-4"
      >
        <div
          v-for="action in store.engagementActions"
          :key="action.id"
          class="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
        >
          <div class="flex items-start justify-between">
            <div class="flex-1">
              <!-- Contact Info -->
              <div class="mb-2 flex items-center gap-3">
                <div class="flex h-10 w-10 items-center justify-center rounded-full bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400">
                  <svg
                    class="h-5 w-5"
                    fill="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z" />
                  </svg>
                </div>
                <div>
                  <h4 class="font-medium text-go4-secondary dark:text-white">
                    {{ action.context?.contact_name || 'Unbekannter Kontakt' }}
                  </h4>
                  <p class="text-sm text-go4-muted dark:text-gray-400">
                    {{ action.context?.contact_phone }}
                  </p>
                </div>
              </div>

              <!-- Action Type & Pipeline -->
              <div class="mb-3 flex flex-wrap items-center gap-2">
                <span class="rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-700 dark:bg-green-900/50 dark:text-green-300">
                  {{ action.action_type }}
                </span>
                <span
                  v-if="action.context?.pipeline_name"
                  class="rounded-full bg-purple-100 px-2.5 py-0.5 text-xs font-medium text-purple-700 dark:bg-purple-900/50 dark:text-purple-300"
                >
                  {{ action.context.pipeline_name }}
                </span>
                <span
                  :class="[
                    'rounded-full px-2.5 py-0.5 text-xs font-medium',
                    action.priority === 'urgent' ? 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300' :
                    action.priority === 'high' ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/50 dark:text-orange-300' :
                    'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                  ]"
                >
                  {{ action.priority }}
                </span>
              </div>

              <!-- Suggested Content -->
              <div
                v-if="action.suggested_content || action.generated_content"
                class="rounded-lg bg-gray-50 p-3 dark:bg-gray-700/50"
              >
                <p class="mb-1 text-xs font-medium text-go4-muted dark:text-gray-400">
                  {{ action.generated_content ? 'Generierter Inhalt' : 'Vorgeschlagener Inhalt' }}
                </p>
                <p class="whitespace-pre-wrap text-sm text-go4-secondary dark:text-gray-200">
                  {{ action.generated_content || action.suggested_content }}
                </p>
              </div>
            </div>

            <!-- Actions -->
            <div class="ml-4 flex flex-col gap-2">
              <button
                v-if="!action.generated_content"
                :disabled="store.actionLoading[action.id]"
                class="flex items-center gap-1.5 rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-100 disabled:opacity-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
                @click="generateActionContent(action.id)"
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
                Generieren
              </button>
              <button
                :disabled="store.actionLoading[action.id]"
                class="flex items-center gap-1.5 rounded-lg bg-go4-primary px-3 py-1.5 text-sm font-medium text-white hover:bg-go4-primary-dark disabled:opacity-50"
                @click="executeAction(action.id, action.generated_content)"
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
                    d="M5 13l4 4L19 7"
                  />
                </svg>
                Freigeben
              </button>
            </div>
          </div>

          <!-- Due Date -->
          <div
            v-if="action.due_at"
            class="mt-3 flex items-center gap-1 text-xs text-go4-muted dark:text-gray-400"
          >
            <svg
              class="h-3.5 w-3.5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            Faellig: {{ formatDate(action.due_at) }}
          </div>
        </div>
      </div>
    </div>

    <!-- Einstellungen Tab -->
    <div v-else-if="activeTab === 'einstellungen'">
      <ModuleSettings module-name="whatsapp" />
    </div>
  </div>
</template>
