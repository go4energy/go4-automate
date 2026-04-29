<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useEmailMarketingStore } from '@/stores/emailmarketing'
import PageHeader from '@/components/ui/PageHeader.vue'

const route = useRoute()
const router = useRouter()
const store = useEmailMarketingStore()

const loading = ref(true)
const sending = ref(false)
const activeTab = ref('overview')

const campaign = computed(() => store.currentCampaign)
const stats = computed(() => store.campaignStats)

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

function getStatusClass(status) {
  const classes = {
    draft: 'bg-gray-100 text-gray-700',
    scheduled: 'bg-blue-100 text-blue-700',
    sending: 'bg-yellow-100 text-yellow-700',
    sent: 'bg-green-100 text-green-700'
  }
  return classes[status] || 'bg-gray-100 text-gray-700'
}

function getStatusLabel(status) {
  const labels = {
    draft: 'Entwurf',
    scheduled: 'Geplant',
    sending: 'Wird gesendet',
    sent: 'Gesendet'
  }
  return labels[status] || status
}

async function sendNow() {
  if (!confirm('Kampagne jetzt an alle Empfänger senden?')) return
  sending.value = true
  try {
    await store.sendCampaignNow(campaign.value.id)
    await loadData()
  } catch (err) {
    // Error handled by store
  } finally {
    sending.value = false
  }
}

function editCampaign() {
  router.push({ name: 'emailmarketing-campaign-edit', params: { id: campaign.value.id } })
}

async function loadData() {
  loading.value = true
  try {
    await store.fetchCampaign(route.params.id)
    if (store.currentCampaign) {
      await store.fetchCampaignStats(route.params.id)
      await store.fetchCampaignRecipients(route.params.id)
    }
  } catch (err) {
    router.push({ name: 'emailmarketing' })
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>

<template>
  <div class="p-6">
    <div
      v-if="loading"
      class="flex items-center justify-center py-12"
    >
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
    </div>

    <template v-else-if="campaign">
      <PageHeader
        :title="campaign.name"
      >
        <template #actions>
          <span
            :class="[
              'px-3 py-1 text-sm font-medium rounded-full mr-4',
              getStatusClass(campaign.status)
            ]"
          >
            {{ getStatusLabel(campaign.status) }}
          </span>
          <button
            v-if="campaign.status === 'draft'"
            class="btn btn-secondary mr-2"
            @click="editCampaign"
          >
            Bearbeiten
          </button>
          <button
            v-if="campaign.status === 'draft'"
            :disabled="sending"
            class="btn btn-primary"
            @click="sendNow"
          >
            {{ sending ? 'Wird gesendet...' : 'Jetzt senden' }}
          </button>
        </template>
      </PageHeader>

      <!-- Tabs -->
      <div class="border-b border-gray-200 mb-6">
        <nav class="-mb-px flex space-x-8">
          <button
            :class="[
              'py-4 px-1 border-b-2 font-medium text-sm',
              activeTab === 'overview'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            ]"
            @click="activeTab = 'overview'"
          >
            Übersicht
          </button>
          <button
            :class="[
              'py-4 px-1 border-b-2 font-medium text-sm',
              activeTab === 'recipients'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            ]"
            @click="activeTab = 'recipients'"
          >
            Empfänger ({{ campaign.total_recipients }})
          </button>
          <button
            :class="[
              'py-4 px-1 border-b-2 font-medium text-sm',
              activeTab === 'content'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            ]"
            @click="activeTab = 'content'"
          >
            Inhalt
          </button>
        </nav>
      </div>

      <!-- Overview Tab -->
      <div
        v-if="activeTab === 'overview'"
        class="space-y-6"
      >
        <!-- Stats Cards -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div class="bg-white rounded-lg shadow p-4">
            <p class="text-sm text-gray-500">
              Gesendet
            </p>
            <p class="text-2xl font-bold text-gray-900">
              {{ campaign.sent_count }}
            </p>
          </div>
          <div class="bg-white rounded-lg shadow p-4">
            <p class="text-sm text-gray-500">
              Geöffnet
            </p>
            <p class="text-2xl font-bold text-green-600">
              {{ campaign.opened_count }}
            </p>
            <p
              v-if="stats"
              class="text-sm text-gray-400"
            >
              {{ stats.open_rate }}%
            </p>
          </div>
          <div class="bg-white rounded-lg shadow p-4">
            <p class="text-sm text-gray-500">
              Geklickt
            </p>
            <p class="text-2xl font-bold text-blue-600">
              {{ campaign.clicked_count }}
            </p>
            <p
              v-if="stats"
              class="text-sm text-gray-400"
            >
              {{ stats.click_rate }}%
            </p>
          </div>
          <div class="bg-white rounded-lg shadow p-4">
            <p class="text-sm text-gray-500">
              Bounces
            </p>
            <p class="text-2xl font-bold text-red-600">
              {{ campaign.bounced_count }}
            </p>
          </div>
        </div>

        <!-- Details -->
        <div class="bg-white rounded-lg shadow p-6">
          <h3 class="font-medium text-gray-900 mb-4">
            Details
          </h3>
          <dl class="grid grid-cols-2 gap-4">
            <div>
              <dt class="text-sm text-gray-500">
                Erstellt am
              </dt>
              <dd class="text-gray-900">
                {{ formatDate(campaign.created_at) }}
              </dd>
            </div>
            <div>
              <dt class="text-sm text-gray-500">
                Gesendet am
              </dt>
              <dd class="text-gray-900">
                {{ formatDate(campaign.sent_at) }}
              </dd>
            </div>
            <div>
              <dt class="text-sm text-gray-500">
                Empfänger
              </dt>
              <dd class="text-gray-900">
                {{ campaign.total_recipients }}
              </dd>
            </div>
            <div>
              <dt class="text-sm text-gray-500">
                Abmeldungen
              </dt>
              <dd class="text-gray-900">
                {{ campaign.unsubscribed_count }}
              </dd>
            </div>
          </dl>
        </div>
      </div>

      <!-- Recipients Tab -->
      <div v-if="activeTab === 'recipients'">
        <div class="bg-white rounded-lg shadow overflow-hidden">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  E-Mail
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Name
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Status
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Geöffnet
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Geklickt
                </th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <tr
                v-for="recipient in store.campaignRecipients"
                :key="recipient.id"
              >
                <td class="px-6 py-4 whitespace-nowrap text-gray-900">
                  {{ recipient.email }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-gray-500">
                  {{ recipient.name || '-' }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <span
                    :class="[
                      'px-2 py-1 text-xs font-medium rounded-full',
                      getStatusClass(recipient.status)
                    ]"
                  >
                    {{ recipient.status }}
                  </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-gray-500">
                  {{ formatDate(recipient.opened_at) }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-gray-500">
                  {{ formatDate(recipient.clicked_at) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Content Tab -->
      <div v-if="activeTab === 'content'">
        <div class="bg-white rounded-lg shadow p-6">
          <h3 class="font-medium text-gray-900 mb-2">
            Betreff
          </h3>
          <p class="text-gray-600 mb-6">
            {{ campaign.subject }}
          </p>

          <h3 class="font-medium text-gray-900 mb-2">
            E-Mail-Inhalt
          </h3>
          <div class="border rounded-lg p-4 bg-gray-50">
            <div
              class="prose max-w-none"
              v-html="campaign.html_content"
            />
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
