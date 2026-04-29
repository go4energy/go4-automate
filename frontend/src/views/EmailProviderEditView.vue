<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useEmailMarketingStore } from '@/stores/emailmarketing'
import PageHeader from '@/components/ui/PageHeader.vue'

const route = useRoute()
const router = useRouter()
const store = useEmailMarketingStore()

const isNew = computed(() => !route.params.id)
const loading = ref(true)
const saving = ref(false)
const verifying = ref(false)

const form = ref({
  provider_type: 'sendgrid',
  api_key: '',
  sender_email: '',
  sender_name: '',
  reply_to_email: '',
  tracking_domain: '',
  hourly_limit: 500,
  daily_limit: 10000,
  status: 'active'
})

const providerTypes = [
  { value: 'sendgrid', label: 'SendGrid' },
  { value: 'mailgun', label: 'Mailgun' },
  { value: 'o365', label: 'Office 365' }
]

async function loadData() {
  loading.value = true
  if (!isNew.value) {
    try {
      await store.fetchProvider(route.params.id)
      if (store.currentProvider) {
        form.value = {
          provider_type: store.currentProvider.provider_type,
          api_key: '', // Don't show existing key
          sender_email: store.currentProvider.sender_email,
          sender_name: store.currentProvider.sender_name,
          reply_to_email: store.currentProvider.reply_to_email || '',
          tracking_domain: store.currentProvider.tracking_domain || '',
          hourly_limit: store.currentProvider.hourly_limit,
          daily_limit: store.currentProvider.daily_limit,
          status: store.currentProvider.status
        }
      }
    } catch (err) {
      router.push({ name: 'emailmarketing' })
    }
  }
  loading.value = false
}

async function save() {
  saving.value = true
  try {
    const data = { ...form.value }
    if (!isNew.value && !data.api_key) {
      delete data.api_key // Don't update if not provided
    }

    if (isNew.value) {
      await store.addProvider(data)
    } else {
      await store.editProvider(route.params.id, data)
    }
    router.push({ name: 'emailmarketing' })
  } catch (err) {
    alert(store.error)
  } finally {
    saving.value = false
  }
}

async function verify() {
  if (isNew.value) return
  verifying.value = true
  try {
    const valid = await store.checkProvider(route.params.id)
    if (valid) {
      alert('Verifizierung erfolgreich!')
    } else {
      alert('Verifizierung fehlgeschlagen.')
    }
  } catch (err) {
    alert('Fehler: ' + store.error)
  } finally {
    verifying.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>

<template>
  <div class="p-6">
    <PageHeader
      :title="isNew ? 'Neuer Provider' : 'Provider bearbeiten'"
    >
      <template #actions>
        <button
          v-if="!isNew"
          :disabled="verifying"
          class="btn btn-secondary mr-2"
          @click="verify"
        >
          {{ verifying ? 'Verifizieren...' : 'Verifizieren' }}
        </button>
        <button
          :disabled="saving || !form.sender_email || !form.sender_name || (isNew && !form.api_key)"
          class="btn btn-primary"
          @click="save"
        >
          {{ saving ? 'Speichern...' : 'Speichern' }}
        </button>
      </template>
    </PageHeader>

    <div
      v-if="loading"
      class="flex items-center justify-center py-12"
    >
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
    </div>

    <form
      v-else
      class="space-y-6"
      @submit.prevent="save"
    >
      <!-- Provider Type -->
      <div class="bg-white rounded-lg shadow p-6">
        <h3 class="text-lg font-medium text-gray-900 mb-4">
          Provider
        </h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Typ *</label>
            <select
              v-model="form.provider_type"
              :disabled="!isNew"
              class="input"
            >
              <option
                v-for="type in providerTypes"
                :key="type.value"
                :value="type.value"
              >
                {{ type.label }}
              </option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              API-Key {{ isNew ? '*' : '(nur ändern wenn nötig)' }}
            </label>
            <input
              v-model="form.api_key"
              type="password"
              :required="isNew"
              class="input"
              placeholder="API-Schlüssel"
            >
          </div>
        </div>
      </div>

      <!-- Sender Settings -->
      <div class="bg-white rounded-lg shadow p-6">
        <h3 class="text-lg font-medium text-gray-900 mb-4">
          Absender
        </h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">E-Mail-Adresse *</label>
            <input
              v-model="form.sender_email"
              type="email"
              required
              class="input"
              placeholder="noreply@example.com"
            >
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Name *</label>
            <input
              v-model="form.sender_name"
              type="text"
              required
              class="input"
              placeholder="Mein Unternehmen"
            >
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Antwort-Adresse</label>
            <input
              v-model="form.reply_to_email"
              type="email"
              class="input"
              placeholder="support@example.com"
            >
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Tracking-Domain</label>
            <input
              v-model="form.tracking_domain"
              type="text"
              class="input"
              placeholder="mail.example.com"
            >
          </div>
        </div>
      </div>

      <!-- Rate Limits -->
      <div class="bg-white rounded-lg shadow p-6">
        <h3 class="text-lg font-medium text-gray-900 mb-4">
          Rate-Limits
        </h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Pro Stunde</label>
            <input
              v-model.number="form.hourly_limit"
              type="number"
              min="1"
              class="input"
            >
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Pro Tag</label>
            <input
              v-model.number="form.daily_limit"
              type="number"
              min="1"
              class="input"
            >
          </div>
        </div>
      </div>

      <!-- Status (Edit only) -->
      <div
        v-if="!isNew"
        class="bg-white rounded-lg shadow p-6"
      >
        <h3 class="text-lg font-medium text-gray-900 mb-4">
          Status
        </h3>
        <select
          v-model="form.status"
          class="input w-auto"
        >
          <option value="active">
            Aktiv
          </option>
          <option value="inactive">
            Inaktiv
          </option>
        </select>
      </div>
    </form>
  </div>
</template>
