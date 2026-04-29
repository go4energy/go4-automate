<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useEmailMarketingStore } from '@/stores/emailmarketing'
import PageHeader from '@/components/ui/PageHeader.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import PipelineCampaignsList from '@/components/engagement/PipelineCampaignsList.vue'

const router = useRouter()
const route = useRoute()
const store = useEmailMarketingStore()

// Tab state from route
const activeTab = computed(() => route.meta?.tab || 'campaigns')

const loading = ref(true)

// Tab definitions
const tabs = [
  {
    id: 'campaigns',
    label: 'Kampagnen',
    icon: 'paper-airplane',
    route: '/emailmarketing/campaigns'
  },
  { id: 'templates', label: 'Vorlagen', icon: 'document-text', route: '/emailmarketing/templates' },
  { id: 'sequences', label: 'Sequenzen', icon: 'queue-list', route: '/emailmarketing/sequences' },
  { id: 'providers', label: 'Provider', icon: 'server', route: '/emailmarketing/providers' },
  { id: 'freigabe', label: 'Freigabe', icon: 'check-circle', route: '/emailmarketing/freigabe' }
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

// Status badges
function getStatusClass(status) {
  const classes = {
    draft: 'bg-gray-100 text-gray-700',
    scheduled: 'bg-blue-100 text-blue-700',
    sending: 'bg-yellow-100 text-yellow-700',
    sent: 'bg-green-100 text-green-700',
    active: 'bg-green-100 text-green-700',
    paused: 'bg-gray-100 text-gray-700',
    inactive: 'bg-gray-100 text-gray-700',
    error: 'bg-red-100 text-red-700'
  }
  return classes[status] || 'bg-gray-100 text-gray-700'
}

function getStatusLabel(status) {
  const labels = {
    draft: 'Entwurf',
    scheduled: 'Geplant',
    sending: 'Wird gesendet',
    sent: 'Gesendet',
    active: 'Aktiv',
    paused: 'Pausiert',
    inactive: 'Inaktiv',
    error: 'Fehler'
  }
  return labels[status] || status
}

// Actions
function createCampaign() {
  router.push({ name: 'emailmarketing-campaign-new' })
}

function createTemplate() {
  router.push({ name: 'emailmarketing-template-new' })
}

function createSequence() {
  router.push({ name: 'emailmarketing-sequence-new' })
}

function createProvider() {
  router.push({ name: 'emailmarketing-provider-new' })
}

function viewCampaign(id) {
  router.push({ name: 'emailmarketing-campaign-detail', params: { id } })
}

function editCampaign(id) {
  router.push({ name: 'emailmarketing-campaign-edit', params: { id } })
}

function editTemplate(id) {
  router.push({ name: 'emailmarketing-template-edit', params: { id } })
}

function viewSequence(id) {
  router.push({ name: 'emailmarketing-sequence-detail', params: { id } })
}

function editSequence(id) {
  router.push({ name: 'emailmarketing-sequence-edit', params: { id } })
}

function editProvider(id) {
  router.push({ name: 'emailmarketing-provider-edit', params: { id } })
}

async function deleteCampaign(campaign) {
  if (!confirm(`Kampagne "${campaign.name}" wirklich löschen?`)) return
  await store.removeCampaign(campaign.id)
}

async function deleteTemplate(template) {
  if (!confirm(`Vorlage "${template.name}" wirklich löschen?`)) return
  await store.removeTemplate(template.id)
}

async function deleteSequence(sequence) {
  if (!confirm(`Sequenz "${sequence.name}" wirklich löschen?`)) return
  await store.removeSequence(sequence.id)
}

async function deleteProvider(provider) {
  if (!confirm(`Provider "${provider.sender_email}" wirklich löschen?`)) return
  await store.removeProvider(provider.id)
}

async function verifyProvider(provider) {
  try {
    await store.checkProvider(provider.id)
    await store.fetchProviders()
  } catch (err) {
    // Error handled by store
  }
}

// Load data
async function loadData() {
  loading.value = true
  await Promise.all([
    store.fetchCampaigns(),
    store.fetchTemplates(),
    store.fetchSequences(),
    store.fetchProviders(),
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

onMounted(() => {
  loadData()
})
</script>

<template>
  <div class="p-6">
    <PageHeader
      title="E-Mail Marketing"
      description="Kampagnen, Sequenzen und Vorlagen verwalten"
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
          v-if="activeTab === 'templates'"
          class="btn btn-primary"
          @click="createTemplate"
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
          Neue Vorlage
        </button>
        <button
          v-if="activeTab === 'sequences'"
          class="btn btn-primary"
          @click="createSequence"
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
          Neue Sequenz
        </button>
        <button
          v-if="activeTab === 'providers'"
          class="btn btn-primary"
          @click="createProvider"
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
          Neuer Provider
        </button>
      </template>
    </PageHeader>

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
              ? 'border-primary-500 text-primary-600'
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
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
    </div>

    <!-- Campaigns Tab -->
    <div v-else-if="activeTab === 'campaigns'">
      <!-- Central engagement pipelines (channel=email) -->
      <PipelineCampaignsList
        channel-filter="email"
        class="mb-8"
      />

      <div class="mb-4 mt-8 border-t border-gray-200 pt-6 dark:border-gray-700">
        <h3 class="mb-3 text-base font-semibold text-gray-700 dark:text-gray-300">
          E-Mail-eigene Sequenzen
        </h3>
        <p class="mb-3 text-xs text-gray-500 dark:text-gray-400">
          Veraltete E-Mail-spezifische Campaigns. Werden langfristig in zentrale Engagement-Pipelines migriert.
        </p>
      </div>
      <EmptyState
        v-if="store.campaigns.length === 0"
        title="Keine Kampagnen"
        description="Erstellen Sie Ihre erste E-Mail-Kampagne."
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
                Betreff
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Status
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Gesendet
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Geöffnet
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
              <td class="px-6 py-4 whitespace-nowrap text-gray-500 max-w-xs truncate">
                {{ campaign.subject }}
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
                {{ campaign.opened_count }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-gray-500">
                {{ formatDate(campaign.created_at) }}
              </td>
              <td
                class="px-6 py-4 whitespace-nowrap text-right"
                @click.stop
              >
                <button
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
      <EmptyState
        v-if="store.templates.length === 0"
        title="Keine Vorlagen"
        description="Erstellen Sie wiederverwendbare E-Mail-Vorlagen."
        action-text="Vorlage erstellen"
        @action="createTemplate"
      />
      <div
        v-else
        class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
      >
        <div
          v-for="template in store.templates"
          :key="template.id"
          class="bg-white rounded-lg shadow p-4 hover:shadow-md transition-shadow cursor-pointer"
          @click="editTemplate(template.id)"
        >
          <div class="flex items-start justify-between">
            <div>
              <h3 class="font-medium text-gray-900">
                {{ template.name }}
              </h3>
              <p class="text-sm text-gray-500 mt-1">
                {{ template.subject }}
              </p>
            </div>
            <span
              :class="[
                'px-2 py-1 text-xs font-medium rounded-full',
                template.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'
              ]"
            >
              {{ template.is_active ? 'Aktiv' : 'Inaktiv' }}
            </span>
          </div>
          <div class="mt-4 flex items-center justify-between">
            <span class="text-xs text-gray-400">{{ formatDate(template.created_at) }}</span>
            <button
              class="text-gray-400 hover:text-red-600"
              title="Löschen"
              @click.stop="deleteTemplate(template)"
            >
              <svg
                class="w-4 h-4"
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

    <!-- Sequences Tab -->
    <div v-else-if="activeTab === 'sequences'">
      <EmptyState
        v-if="store.sequences.length === 0"
        title="Keine Sequenzen"
        description="Erstellen Sie automatisierte E-Mail-Sequenzen."
        action-text="Sequenz erstellen"
        @action="createSequence"
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
                Trigger
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Status
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Schritte
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Eingeschrieben
              </th>
              <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                Aktionen
              </th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr
              v-for="sequence in store.sequences"
              :key="sequence.id"
              class="hover:bg-gray-50 cursor-pointer"
              @click="viewSequence(sequence.id)"
            >
              <td class="px-6 py-4 whitespace-nowrap font-medium text-gray-900">
                {{ sequence.name }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-gray-500">
                {{ sequence.trigger_type }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span
                  :class="[
                    'px-2 py-1 text-xs font-medium rounded-full',
                    getStatusClass(sequence.status)
                  ]"
                >
                  {{ getStatusLabel(sequence.status) }}
                </span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-gray-500">
                {{ sequence.step_count }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-gray-500">
                {{ sequence.total_enrolled }}
              </td>
              <td
                class="px-6 py-4 whitespace-nowrap text-right"
                @click.stop
              >
                <button
                  class="text-gray-400 hover:text-gray-600 mr-2"
                  title="Bearbeiten"
                  @click="editSequence(sequence.id)"
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
                  @click="deleteSequence(sequence)"
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

    <!-- Providers Tab -->
    <div v-else-if="activeTab === 'providers'">
      <EmptyState
        v-if="store.providers.length === 0"
        title="Keine Provider"
        description="Fügen Sie einen E-Mail-Provider hinzu (SendGrid, Mailgun, Office 365)."
        action-text="Provider hinzufügen"
        @action="createProvider"
      />
      <div
        v-else
        class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
      >
        <div
          v-for="provider in store.providers"
          :key="provider.id"
          class="bg-white rounded-lg shadow p-4"
        >
          <div class="flex items-start justify-between">
            <div>
              <div class="flex items-center space-x-2">
                <span
                  class="px-2 py-1 text-xs font-medium rounded bg-gray-100 text-gray-700 uppercase"
                >
                  {{ provider.provider_type }}
                </span>
                <span
                  :class="[
                    'px-2 py-1 text-xs font-medium rounded-full',
                    getStatusClass(provider.status)
                  ]"
                >
                  {{ getStatusLabel(provider.status) }}
                </span>
              </div>
              <p class="font-medium text-gray-900 mt-2">
                {{ provider.sender_name }}
              </p>
              <p class="text-sm text-gray-500">
                {{ provider.sender_email }}
              </p>
            </div>
          </div>
          <div class="mt-4 pt-4 border-t border-gray-100 flex items-center justify-between">
            <span class="text-sm text-gray-500">
              Heute: {{ provider.emails_sent_today }} E-Mails
            </span>
            <div class="flex space-x-2">
              <button
                class="text-gray-400 hover:text-blue-600"
                title="Verifizieren"
                @click="verifyProvider(provider)"
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
                @click="editProvider(provider.id)"
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
                @click="deleteProvider(provider)"
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
            Vom Engagement Brain generierte E-Mail-Aktionen zur Freigabe
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
        description="Es gibt keine ausstehenden E-Mail-Aktionen vom Engagement Brain."
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
                <div class="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-100 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400">
                  <svg
                    class="h-5 w-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                    />
                  </svg>
                </div>
                <div>
                  <h4 class="font-medium text-go4-secondary dark:text-white">
                    {{ action.context?.contact_name || 'Unbekannter Kontakt' }}
                  </h4>
                  <p class="text-sm text-go4-muted dark:text-gray-400">
                    {{ action.context?.contact_email }}
                  </p>
                </div>
              </div>

              <!-- Action Type & Pipeline -->
              <div class="mb-3 flex flex-wrap items-center gap-2">
                <span class="rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-300">
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

              <!-- Subject -->
              <div
                v-if="action.context?.subject"
                class="mb-2"
              >
                <p class="text-xs font-medium text-go4-muted dark:text-gray-400">
                  Betreff
                </p>
                <p class="text-sm font-medium text-go4-secondary dark:text-white">
                  {{ action.context.subject }}
                </p>
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
  </div>
</template>
