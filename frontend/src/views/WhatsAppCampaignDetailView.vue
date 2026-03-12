<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useWhatsAppStore } from '@/stores/whatsapp'
import PageHeader from '@/components/ui/PageHeader.vue'
import Breadcrumb from '@/components/ui/Breadcrumb.vue'

const props = defineProps({
  id: { type: [String, Number], required: true }
})

const router = useRouter()
const store = useWhatsAppStore()

const loading = ref(true)
const sending = ref(false)
const recipientFilter = ref('')
const recipientStatus = ref('')

const campaign = computed(() => store.currentCampaign)
const stats = computed(() => store.campaignStats)
const recipients = computed(() => store.campaignRecipients)

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

// Status styling
function getStatusClass(status) {
  const classes = {
    draft: 'bg-gray-100 text-gray-700',
    scheduled: 'bg-blue-100 text-blue-700',
    sending: 'bg-yellow-100 text-yellow-700',
    sent: 'bg-green-100 text-green-700',
    pending: 'bg-gray-100 text-gray-700',
    delivered: 'bg-green-100 text-green-700',
    read: 'bg-blue-100 text-blue-700',
    failed: 'bg-red-100 text-red-700'
  }
  return classes[status] || 'bg-gray-100 text-gray-700'
}

function getStatusLabel(status) {
  const labels = {
    draft: 'Entwurf',
    scheduled: 'Geplant',
    sending: 'Wird gesendet',
    sent: 'Gesendet',
    pending: 'Ausstehend',
    delivered: 'Zugestellt',
    read: 'Gelesen',
    failed: 'Fehlgeschlagen'
  }
  return labels[status] || status
}

// Actions
function editCampaign() {
  router.push({ name: 'whatsapp-campaign-edit', params: { id: props.id } })
}

async function sendCampaign() {
  if (!confirm('Kampagne jetzt senden?')) return
  sending.value = true
  try {
    await store.sendCampaignNow(props.id)
    await loadData()
  } catch (err) {
    // Error handled by store
  } finally {
    sending.value = false
  }
}

async function loadRecipients() {
  await store.fetchCampaignRecipients(props.id, {
    status: recipientStatus.value || undefined,
    search: recipientFilter.value || undefined,
    limit: 100
  })
}

// Load data
async function loadData() {
  loading.value = true
  try {
    await store.fetchCampaign(props.id)
    await store.fetchCampaignStats(props.id)
    await loadRecipients()
  } catch (err) {
    router.push({ name: 'whatsapp-campaigns' })
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadData()
})

onUnmounted(() => {
  store.clearCurrent()
})
</script>

<template>
  <div class="p-6">
    <Breadcrumb class="mb-4" />

    <!-- Loading -->
    <div
      v-if="loading"
      class="flex items-center justify-center py-12"
    >
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600" />
    </div>

    <template v-else-if="campaign">
      <PageHeader :title="campaign.name">
        <template #actions>
          <button
            v-if="campaign.status === 'draft'"
            class="btn btn-secondary mr-2"
            @click="editCampaign"
          >
            Bearbeiten
          </button>
          <button
            v-if="campaign.status === 'draft' && campaign.total_recipients > 0"
            class="btn btn-primary"
            :disabled="sending"
            @click="sendCampaign"
          >
            <svg
              v-if="sending"
              class="animate-spin w-5 h-5 mr-2"
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
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
            Jetzt senden
          </button>
        </template>
      </PageHeader>

      <!-- Status -->
      <div class="mb-6">
        <span
          :class="['px-3 py-1 text-sm font-medium rounded-full', getStatusClass(campaign.status)]"
        >
          {{ getStatusLabel(campaign.status) }}
        </span>
      </div>

      <!-- Stats -->
      <div class="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
        <div class="bg-white rounded-lg shadow p-4">
          <div class="text-sm text-gray-500">
            Empfänger
          </div>
          <div class="text-2xl font-semibold text-gray-900">
            {{ campaign.total_recipients }}
          </div>
        </div>
        <div class="bg-white rounded-lg shadow p-4">
          <div class="text-sm text-gray-500">
            Gesendet
          </div>
          <div class="text-2xl font-semibold text-gray-900">
            {{ campaign.sent_count }}
          </div>
        </div>
        <div class="bg-white rounded-lg shadow p-4">
          <div class="text-sm text-gray-500">
            Zugestellt
          </div>
          <div class="text-2xl font-semibold text-green-600">
            {{ campaign.delivered_count }}
          </div>
          <div
            v-if="stats"
            class="text-xs text-gray-500"
          >
            {{ stats.delivery_rate }}%
          </div>
        </div>
        <div class="bg-white rounded-lg shadow p-4">
          <div class="text-sm text-gray-500">
            Gelesen
          </div>
          <div class="text-2xl font-semibold text-blue-600">
            {{ campaign.read_count }}
          </div>
          <div
            v-if="stats"
            class="text-xs text-gray-500"
          >
            {{ stats.read_rate }}%
          </div>
        </div>
        <div class="bg-white rounded-lg shadow p-4">
          <div class="text-sm text-gray-500">
            Fehlgeschlagen
          </div>
          <div class="text-2xl font-semibold text-red-600">
            {{ campaign.failed_count }}
          </div>
        </div>
      </div>

      <!-- Campaign Info -->
      <div class="bg-white rounded-lg shadow p-6 mb-6">
        <h3 class="font-semibold text-gray-900 mb-4">
          Kampagnen-Details
        </h3>
        <dl class="grid grid-cols-2 gap-4">
          <div>
            <dt class="text-sm text-gray-500">
              Erstellt
            </dt>
            <dd class="text-gray-900">
              {{ formatDate(campaign.created_at) }}
            </dd>
          </div>
          <div v-if="campaign.sent_at">
            <dt class="text-sm text-gray-500">
              Gesendet
            </dt>
            <dd class="text-gray-900">
              {{ formatDate(campaign.sent_at) }}
            </dd>
          </div>
          <div v-if="campaign.scheduled_at">
            <dt class="text-sm text-gray-500">
              Geplant für
            </dt>
            <dd class="text-gray-900">
              {{ formatDate(campaign.scheduled_at) }}
            </dd>
          </div>
          <div v-if="campaign.template_id">
            <dt class="text-sm text-gray-500">
              Template
            </dt>
            <dd class="text-gray-900">
              ID: {{ campaign.template_id }}
            </dd>
          </div>
        </dl>
      </div>

      <!-- Recipients -->
      <div class="bg-white rounded-lg shadow overflow-hidden">
        <div class="p-4 border-b flex items-center justify-between">
          <h3 class="font-semibold text-gray-900">
            Empfänger
          </h3>
          <div class="flex items-center space-x-4">
            <input
              v-model="recipientFilter"
              type="text"
              class="input w-48"
              placeholder="Suchen..."
              @input="loadRecipients"
            >
            <select
              v-model="recipientStatus"
              class="input w-40"
              @change="loadRecipients"
            >
              <option value="">
                Alle Status
              </option>
              <option value="pending">
                Ausstehend
              </option>
              <option value="sent">
                Gesendet
              </option>
              <option value="delivered">
                Zugestellt
              </option>
              <option value="read">
                Gelesen
              </option>
              <option value="failed">
                Fehlgeschlagen
              </option>
            </select>
          </div>
        </div>
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Kontakt
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Telefon
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
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr
              v-for="recipient in recipients"
              :key="recipient.id"
            >
              <td class="px-6 py-4 whitespace-nowrap font-medium text-gray-900">
                {{ recipient.contact_name || '-' }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-gray-500">
                {{ recipient.phone }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span
                  :class="[
                    'px-2 py-1 text-xs font-medium rounded-full',
                    getStatusClass(recipient.status)
                  ]"
                >
                  {{ getStatusLabel(recipient.status) }}
                </span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-gray-500">
                {{ formatDate(recipient.sent_at) }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-gray-500">
                {{ formatDate(recipient.delivered_at) }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-gray-500">
                {{ formatDate(recipient.read_at) }}
              </td>
            </tr>
            <tr v-if="recipients.length === 0">
              <td
                colspan="6"
                class="px-6 py-8 text-center text-gray-500"
              >
                Keine Empfänger gefunden
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>
