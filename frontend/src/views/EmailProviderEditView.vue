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
  provider_type: 'brevo',
  api_key: '',
  // AWS SES specific (bundled into api_key as JSON on save)
  aws_access_key_id: '',
  aws_secret_access_key: '',
  aws_region: 'eu-central-1',
  aws_configuration_set: '',
  sender_email: '',
  sender_name: '',
  reply_to_email: '',
  tracking_domain: '',
  hourly_limit: 500,
  daily_limit: 10000,
  status: 'active',
})

const providerTypes = [
  { value: 'brevo', label: 'Brevo (EU, DSGVO) – Empfohlen für Cold-Outreach' },
  { value: 'o365', label: 'Office 365 / Microsoft 365 – Für Transactional & Replies' },
  { value: 'aws_ses', label: 'AWS SES (Frankfurt) – Nur für Transactional' },
  { value: 'sendgrid', label: 'SendGrid' },
  { value: 'mailgun', label: 'Mailgun' },
]

const isAwsSes = computed(() => form.value.provider_type === 'aws_ses')

const inputClass =
  'block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 ' +
  'placeholder-gray-400 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary ' +
  'disabled:bg-gray-100 disabled:text-gray-500 ' +
  'dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 dark:placeholder-gray-500 dark:disabled:bg-gray-800'

const labelClass = 'block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1'

const cardClass =
  'rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800'

const headingClass = 'text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4'

const primaryBtnClass =
  'rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark ' +
  'disabled:opacity-50 disabled:cursor-not-allowed'

const secondaryBtnClass =
  'rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 ' +
  'hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed ' +
  'dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600'

function buildApiKeyPayload() {
  if (!isAwsSes.value) return form.value.api_key
  // Bundle AWS credentials as JSON for the encrypted store
  const bundle = {
    aws_access_key_id: form.value.aws_access_key_id.trim(),
    aws_secret_access_key: form.value.aws_secret_access_key.trim(),
  }
  if (form.value.aws_region) bundle.region = form.value.aws_region.trim()
  if (form.value.aws_configuration_set) {
    bundle.configuration_set = form.value.aws_configuration_set.trim()
  }
  return JSON.stringify(bundle)
}

async function loadData() {
  loading.value = true
  if (!isNew.value) {
    try {
      await store.fetchProvider(route.params.id)
      if (store.currentProvider) {
        form.value = {
          ...form.value,
          provider_type: store.currentProvider.provider_type,
          api_key: '', // Don't show existing key
          aws_access_key_id: '',
          aws_secret_access_key: '',
          aws_region: 'eu-central-1',
          aws_configuration_set: '',
          sender_email: store.currentProvider.sender_email,
          sender_name: store.currentProvider.sender_name,
          reply_to_email: store.currentProvider.reply_to_email || '',
          tracking_domain: store.currentProvider.tracking_domain || '',
          hourly_limit: store.currentProvider.hourly_limit,
          daily_limit: store.currentProvider.daily_limit,
          status: store.currentProvider.status,
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
    // For AWS SES we bundle the credentials into api_key as JSON; on edit
    // we only send if the user actually entered new values.
    if (isAwsSes.value) {
      const hasNewCreds =
        form.value.aws_access_key_id && form.value.aws_secret_access_key
      if (isNew.value || hasNewCreds) {
        data.api_key = buildApiKeyPayload()
      } else {
        delete data.api_key
      }
    } else if (!isNew.value && !data.api_key) {
      delete data.api_key
    }
    delete data.aws_access_key_id
    delete data.aws_secret_access_key
    delete data.aws_region
    delete data.aws_configuration_set

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
    alert(valid ? 'Verifizierung erfolgreich!' : 'Verifizierung fehlgeschlagen.')
  } catch (err) {
    alert('Fehler: ' + store.error)
  } finally {
    verifying.value = false
  }
}

const canSubmit = computed(() => {
  if (!form.value.sender_email || !form.value.sender_name) return false
  if (isNew.value) {
    if (isAwsSes.value) {
      return Boolean(form.value.aws_access_key_id && form.value.aws_secret_access_key)
    }
    return Boolean(form.value.api_key)
  }
  return true
})

onMounted(loadData)
</script>

<template>
  <div>
    <PageHeader :title="isNew ? 'Neuer Provider' : 'Provider bearbeiten'">
      <template #actions>
        <button
          v-if="!isNew"
          :disabled="verifying"
          :class="secondaryBtnClass"
          @click="verify"
        >
          {{ verifying ? 'Verifizieren…' : 'Verifizieren' }}
        </button>
        <button
          :disabled="saving || !canSubmit"
          :class="primaryBtnClass"
          @click="save"
        >
          {{ saving ? 'Speichern…' : 'Speichern' }}
        </button>
      </template>
    </PageHeader>

    <div
      v-if="loading"
      class="flex items-center justify-center py-12"
    >
      <span class="text-gray-500 dark:text-gray-400">Laden…</span>
    </div>

    <form
      v-else
      class="space-y-6"
      @submit.prevent="save"
    >
      <!-- Provider Type -->
      <div :class="cardClass">
        <h3 :class="headingClass">
          Provider
        </h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label :class="labelClass">Typ <span class="text-red-500">*</span></label>
            <select
              v-model="form.provider_type"
              :disabled="!isNew"
              :class="inputClass"
            >
              <option
                v-for="type in providerTypes"
                :key="type.value"
                :value="type.value"
              >
                {{ type.label }}
              </option>
            </select>
            <p
              v-if="!isNew"
              class="mt-1 text-xs text-gray-500 dark:text-gray-400"
            >
              Provider-Typ kann nach Anlage nicht mehr geändert werden.
            </p>
          </div>
          <div v-if="!isAwsSes">
            <label :class="labelClass">
              API-Key
              <span
                v-if="isNew"
                class="text-red-500"
              >*</span>
              <span
                v-else
                class="text-gray-400 font-normal"
              >(nur ändern wenn nötig)</span>
            </label>
            <input
              v-model="form.api_key"
              type="password"
              :required="isNew && !isAwsSes"
              :class="inputClass"
              placeholder="API-Schlüssel"
              autocomplete="new-password"
            >
          </div>
        </div>

        <!-- AWS SES specific fields -->
        <div
          v-if="isAwsSes"
          class="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4 border-t border-gray-200 dark:border-gray-700 pt-6"
        >
          <div>
            <label :class="labelClass">
              AWS Access Key ID
              <span
                v-if="isNew"
                class="text-red-500"
              >*</span>
              <span
                v-else
                class="text-gray-400 font-normal"
              >(nur ändern wenn nötig)</span>
            </label>
            <input
              v-model="form.aws_access_key_id"
              type="text"
              :required="isNew"
              :class="inputClass"
              placeholder="AKIAXXXXXXXXXXXXXXXX"
              autocomplete="off"
            >
          </div>
          <div>
            <label :class="labelClass">
              AWS Secret Access Key
              <span
                v-if="isNew"
                class="text-red-500"
              >*</span>
              <span
                v-else
                class="text-gray-400 font-normal"
              >(nur ändern wenn nötig)</span>
            </label>
            <input
              v-model="form.aws_secret_access_key"
              type="password"
              :required="isNew"
              :class="inputClass"
              placeholder="••••••••••••••••••••"
              autocomplete="new-password"
            >
          </div>
          <div>
            <label :class="labelClass">Region</label>
            <select
              v-model="form.aws_region"
              :class="inputClass"
            >
              <option value="eu-central-1">
                eu-central-1 (Frankfurt) — Empfohlen für DSGVO
              </option>
              <option value="eu-west-1">
                eu-west-1 (Irland)
              </option>
              <option value="us-east-1">
                us-east-1 (N. Virginia)
              </option>
              <option value="us-west-2">
                us-west-2 (Oregon)
              </option>
            </select>
          </div>
          <div>
            <label :class="labelClass">
              Configuration Set
              <span class="font-normal text-gray-400">(optional)</span>
            </label>
            <input
              v-model="form.aws_configuration_set"
              type="text"
              :class="inputClass"
              placeholder="ses-bounces-smartladen"
            >
            <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
              SES Configuration Set für Bounce-/Complaint-Tracking via SNS-Webhook.
            </p>
          </div>
          <div class="md:col-span-2 rounded-md bg-blue-50 p-3 text-sm text-blue-800 dark:bg-blue-900/20 dark:text-blue-200">
            <strong>Setup-Reihenfolge AWS SES:</strong>
            <ol class="mt-1 list-decimal list-inside space-y-0.5 text-xs">
              <li>AWS-Account in Region <code>eu-central-1</code> anlegen</li>
              <li>Domain <code>smartladen.de</code> in SES verifizieren (DKIM-Records ins DNS)</li>
              <li>SPF + DMARC Records ins DNS</li>
              <li>Production-Access beantragen (Sandbox = nur an verifizierte Adressen)</li>
              <li>IAM-User mit <code>AmazonSESFullAccess</code> → Access Key + Secret hier eintragen</li>
            </ol>
          </div>
        </div>
      </div>

      <!-- Sender Settings -->
      <div :class="cardClass">
        <h3 :class="headingClass">
          Absender
        </h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label :class="labelClass">E-Mail-Adresse <span class="text-red-500">*</span></label>
            <input
              v-model="form.sender_email"
              type="email"
              required
              :class="inputClass"
              placeholder="info@smartladen.de"
            >
          </div>
          <div>
            <label :class="labelClass">Anzeige-Name <span class="text-red-500">*</span></label>
            <input
              v-model="form.sender_name"
              type="text"
              required
              :class="inputClass"
              placeholder="Smartladen"
            >
          </div>
          <div>
            <label :class="labelClass">Reply-To-Adresse</label>
            <input
              v-model="form.reply_to_email"
              type="email"
              :class="inputClass"
              placeholder="info@smartladen.de"
            >
            <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Empfangsadresse für Antworten. Standard = Sender-Adresse.
            </p>
          </div>
          <div>
            <label :class="labelClass">Tracking-Domain</label>
            <input
              v-model="form.tracking_domain"
              type="text"
              :class="inputClass"
              placeholder="mail.smartladen.de"
            >
            <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Optional, Sub-Domain für Click-Redirects (Branding).
            </p>
          </div>
        </div>
      </div>

      <!-- Rate Limits -->
      <div :class="cardClass">
        <h3 :class="headingClass">
          Rate-Limits
        </h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label :class="labelClass">Pro Stunde</label>
            <input
              v-model.number="form.hourly_limit"
              type="number"
              min="1"
              :class="inputClass"
            >
          </div>
          <div>
            <label :class="labelClass">Pro Tag</label>
            <input
              v-model.number="form.daily_limit"
              type="number"
              min="1"
              :class="inputClass"
            >
          </div>
        </div>
        <p class="mt-3 text-xs text-gray-500 dark:text-gray-400">
          Empfehlung beim Start einer neuen Domain: 50/Tag → langsam steigern auf 500/Tag in 2-3 Wochen,
          um die Sender-Reputation aufzubauen.
        </p>
      </div>

      <!-- Status (Edit only) -->
      <div
        v-if="!isNew"
        :class="cardClass"
      >
        <h3 :class="headingClass">
          Status
        </h3>
        <select
          v-model="form.status"
          :class="inputClass"
          class="md:w-auto"
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
