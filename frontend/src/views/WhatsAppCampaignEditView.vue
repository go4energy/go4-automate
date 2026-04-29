<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useWhatsAppStore } from '@/stores/whatsapp'
import PageHeader from '@/components/ui/PageHeader.vue'

const props = defineProps({
  id: { type: [String, Number], default: null }
})

const router = useRouter()
const store = useWhatsAppStore()

const loading = ref(true)
const saving = ref(false)
const generating = ref(false)

const form = ref({
  name: '',
  account_id: null,
  template_id: null,
  segment_filters: {},
  contact_ids: []
})

const isEdit = computed(() => !!props.id)
const campaign = computed(() => store.currentCampaign)

// Format date
function formatDate(date) {
  if (!date) return '-'
  return new Date(date).toLocaleDateString('de-DE')
}

// Save campaign
async function saveCampaign() {
  if (!form.value.name || !form.value.account_id || !form.value.template_id) {
    alert('Bitte füllen Sie alle Pflichtfelder aus.')
    return
  }

  saving.value = true
  try {
    if (isEdit.value) {
      await store.editCampaign(props.id, form.value)
    } else {
      const campaign = await store.addCampaign(form.value)
      router.replace({ name: 'whatsapp-campaign-edit', params: { id: campaign.id } })
    }
  } catch (err) {
    // Error handled by store
  } finally {
    saving.value = false
  }
}

// Generate recipients
async function generateRecipients() {
  if (!props.id) {
    alert('Bitte speichern Sie die Kampagne zuerst.')
    return
  }

  generating.value = true
  try {
    const count = await store.generateRecipients(props.id)
    alert(`${count} Empfänger generiert.`)
  } catch (err) {
    // Error handled by store
  } finally {
    generating.value = false
  }
}

// Load data
async function loadData() {
  loading.value = true
  try {
    await Promise.all([store.fetchAccounts(), store.fetchTemplates()])

    if (isEdit.value) {
      await store.fetchCampaign(props.id)
      form.value = {
        name: campaign.value.name,
        account_id: campaign.value.account_id,
        template_id: campaign.value.template_id,
        segment_filters: campaign.value.segment_filters || {},
        contact_ids: campaign.value.contact_ids || []
      }
    }
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
  <div>
    <PageHeader :title="isEdit ? 'Kampagne bearbeiten' : 'Neue Kampagne'" />

    <!-- Loading -->
    <div
      v-if="loading"
      class="flex items-center justify-center py-12"
    >
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600" />
    </div>

    <div
      v-else
      class="max-w-2xl"
    >
      <!-- Form -->
      <div class="bg-white rounded-lg shadow p-6 space-y-6">
        <!-- Name -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Name *</label>
          <input
            v-model="form.name"
            type="text"
            class="input w-full"
            placeholder="Kampagnenname"
          >
        </div>

        <!-- Account -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">WhatsApp Account *</label>
          <select
            v-model="form.account_id"
            class="input w-full"
          >
            <option :value="null">
              Account auswählen...
            </option>
            <option
              v-for="account in store.accounts"
              :key="account.id"
              :value="account.id"
            >
              {{ account.name }} ({{ account.phone_number }})
            </option>
          </select>
        </div>

        <!-- Template -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Template *</label>
          <select
            v-model="form.template_id"
            class="input w-full"
          >
            <option :value="null">
              Template auswählen...
            </option>
            <option
              v-for="template in store.approvedTemplates"
              :key="template.id"
              :value="template.id"
            >
              {{ template.name }} ({{ template.language }})
            </option>
          </select>
          <p
            v-if="store.templates.length === 0"
            class="text-sm text-gray-500 mt-1"
          >
            Keine Templates vorhanden. Bitte synchronisieren Sie zuerst Templates von Meta.
          </p>
        </div>

        <!-- Segment Filters -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Segment-Filter (optional)</label>
          <p class="text-sm text-gray-500 mb-2">
            Filtern Sie Kontakte nach Tags. Mehrere Tags mit Komma trennen.
          </p>
          <input
            v-model="form.segment_filters.tags"
            type="text"
            class="input w-full"
            placeholder="z.B. lead, newsletter"
          >
        </div>

        <!-- Actions -->
        <div class="pt-4 flex items-center justify-between">
          <div>
            <button
              v-if="isEdit"
              class="btn btn-secondary"
              :disabled="generating"
              @click="generateRecipients"
            >
              <svg
                v-if="generating"
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
              Empfänger generieren
            </button>
            <span
              v-if="campaign?.total_recipients"
              class="ml-4 text-sm text-gray-500"
            >
              {{ campaign.total_recipients }} Empfänger
            </span>
          </div>
          <button
            class="btn btn-primary"
            :disabled="saving"
            @click="saveCampaign"
          >
            <svg
              v-if="saving"
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
            {{ isEdit ? 'Speichern' : 'Erstellen' }}
          </button>
        </div>
      </div>

      <!-- Error -->
      <div
        v-if="store.error"
        class="mt-4 p-4 bg-red-50 rounded-lg text-red-700"
      >
        {{ store.error }}
      </div>
    </div>
  </div>
</template>
