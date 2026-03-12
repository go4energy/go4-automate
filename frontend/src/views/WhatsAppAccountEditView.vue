<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useWhatsAppStore } from '@/stores/whatsapp'
import PageHeader from '@/components/ui/PageHeader.vue'
import Breadcrumb from '@/components/ui/Breadcrumb.vue'

const props = defineProps({
  id: { type: [String, Number], default: null }
})

const router = useRouter()
const store = useWhatsAppStore()

const loading = ref(true)
const saving = ref(false)
const verifying = ref(false)

const form = ref({
  name: '',
  phone_number: '',
  phone_number_id: '',
  waba_id: '',
  access_token: '',
  daily_limit: 1000
})

const isEdit = computed(() => !!props.id)
const account = computed(() => store.currentAccount)

// Save account
async function saveAccount() {
  if (!form.value.name || !form.value.phone_number_id || !form.value.waba_id) {
    alert('Bitte füllen Sie alle Pflichtfelder aus.')
    return
  }

  if (!isEdit.value && !form.value.access_token) {
    alert('Bitte geben Sie den Access Token ein.')
    return
  }

  saving.value = true
  try {
    if (isEdit.value) {
      await store.editAccount(props.id, form.value)
      router.push({ name: 'whatsapp-accounts' })
    } else {
      await store.addAccount(form.value)
      router.push({ name: 'whatsapp-accounts' })
    }
  } catch (err) {
    // Error handled by store
  } finally {
    saving.value = false
  }
}

// Verify credentials
async function verifyCredentials() {
  if (!props.id) return

  verifying.value = true
  try {
    await store.checkAccount(props.id)
    alert('Credentials erfolgreich verifiziert!')
  } catch (err) {
    alert('Verifizierung fehlgeschlagen: ' + (store.error || 'Unbekannter Fehler'))
  } finally {
    verifying.value = false
  }
}

// Load data
async function loadData() {
  loading.value = true
  try {
    if (isEdit.value) {
      await store.fetchAccount(props.id)
      form.value = {
        name: account.value.name,
        phone_number: account.value.phone_number,
        phone_number_id: account.value.phone_number_id,
        waba_id: account.value.waba_id,
        access_token: '',
        daily_limit: account.value.daily_limit
      }
    }
  } catch (err) {
    router.push({ name: 'whatsapp-accounts' })
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

    <PageHeader :title="isEdit ? 'Account bearbeiten' : 'Neuer Account'" />

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
            placeholder="z.B. Hauptnummer"
          >
        </div>

        <!-- Phone Number -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Telefonnummer</label>
          <input
            v-model="form.phone_number"
            type="text"
            class="input w-full"
            placeholder="+49 123 456789"
          >
        </div>

        <!-- Phone Number ID -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Phone Number ID *</label>
          <input
            v-model="form.phone_number_id"
            type="text"
            class="input w-full"
            placeholder="Meta Phone Number ID"
          >
          <p class="text-sm text-gray-500 mt-1">
            Finden Sie diese ID im Meta Business Manager unter WhatsApp &gt; Phone Numbers.
          </p>
        </div>

        <!-- WABA ID -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">WhatsApp Business Account ID *</label>
          <input
            v-model="form.waba_id"
            type="text"
            class="input w-full"
            placeholder="Meta WABA ID"
          >
        </div>

        <!-- Access Token -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            Access Token {{ isEdit ? '(leer lassen um beizubehalten)' : '*' }}
          </label>
          <input
            v-model="form.access_token"
            type="password"
            class="input w-full"
            placeholder="Permanent Access Token"
          >
          <p class="text-sm text-gray-500 mt-1">
            System User Token mit whatsapp_business_messaging Permission.
          </p>
        </div>

        <!-- Daily Limit -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Tägliches Limit</label>
          <input
            v-model.number="form.daily_limit"
            type="number"
            class="input w-full"
            min="1"
            max="100000"
          >
        </div>

        <!-- Status (Edit only) -->
        <div
          v-if="isEdit && account"
          class="pt-4 border-t"
        >
          <div class="flex items-center justify-between">
            <div>
              <span class="text-sm font-medium text-gray-700">Status: </span>
              <span
                :class="[
                  'px-2 py-1 text-xs font-medium rounded-full',
                  account.status === 'active'
                    ? 'bg-green-100 text-green-700'
                    : 'bg-red-100 text-red-700'
                ]"
              >
                {{ account.status === 'active' ? 'Aktiv' : account.status }}
              </span>
            </div>
            <button
              class="btn btn-secondary"
              :disabled="verifying"
              @click="verifyCredentials"
            >
              <svg
                v-if="verifying"
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
              Credentials verifizieren
            </button>
          </div>
          <p
            v-if="account.last_error"
            class="mt-2 text-sm text-red-600"
          >
            {{ account.last_error }}
          </p>
        </div>

        <!-- Actions -->
        <div class="pt-4 flex justify-end">
          <button
            class="btn btn-secondary mr-2"
            @click="router.push({ name: 'whatsapp-accounts' })"
          >
            Abbrechen
          </button>
          <button
            class="btn btn-primary"
            :disabled="saving"
            @click="saveAccount"
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
