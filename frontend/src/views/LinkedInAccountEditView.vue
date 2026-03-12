<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useLinkedInStore } from '@/stores/linkedin'
import PageHeader from '@/components/ui/PageHeader.vue'

const props = defineProps({
  id: { type: [String, Number], default: null }
})

const route = useRoute()
const router = useRouter()
const store = useLinkedInStore()

const accountId = computed(() => props.id || route.params.id)
const isEdit = computed(() => !!accountId.value)

const loading = ref(false)
const saving = ref(false)
const importingSession = ref(false)
const loggingIn = ref(false)
const error = ref(null)
const successMessage = ref(null)
const showCookieImport = ref(false)

const formData = ref({
  name: '',
  email: '',
  password: '',
  is_sales_navigator: false
})

const liAtCookie = ref('')
const currentAccount = ref(null)

onMounted(async () => {
  if (isEdit.value) {
    loading.value = true
    try {
      const account = await store.fetchAccount(accountId.value)
      currentAccount.value = account
      formData.value = {
        name: account.name,
        email: account.email,
        password: '',
        is_sales_navigator: account.is_sales_navigator
      }
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }
})

async function save() {
  if (!formData.value.name.trim() || !formData.value.email.trim()) {
    error.value = 'Name und E-Mail sind erforderlich'
    return
  }

  saving.value = true
  error.value = null
  successMessage.value = null

  try {
    const data = { ...formData.value }
    if (!data.password) {
      delete data.password
    }

    if (isEdit.value) {
      await store.editAccount(accountId.value, data)
      successMessage.value = 'Account gespeichert'
      const account = await store.fetchAccount(accountId.value)
      currentAccount.value = account
    } else {
      const newAccount = await store.addAccount(data)
      router.push(`/linkedin/accounts/${newAccount.id}/edit`)
    }
  } catch (err) {
    error.value = err.response?.data?.detail || err.message
  } finally {
    saving.value = false
  }
}

async function startLogin() {
  loggingIn.value = true
  error.value = null
  successMessage.value = null

  try {
    const result = await store.startAutoLogin(accountId.value, null, 120)

    if (result.success) {
      successMessage.value =
        'Login erfolgreich! Session gueltig bis: ' +
        new Date(result.session_expires_at).toLocaleString('de-DE')
      const account = await store.fetchAccount(accountId.value)
      currentAccount.value = account
    } else {
      if (result.needs_manual_intervention) {
        error.value =
          '2FA/CAPTCHA erkannt! Bitte im VNC-Fenster (Port 5901) loesen. ' + result.message
      } else {
        error.value = result.message
      }
    }
  } catch (err) {
    error.value = 'Auto-Login fehlgeschlagen: ' + (err.response?.data?.detail || err.message)
  } finally {
    loggingIn.value = false
  }
}

async function importSession() {
  if (!liAtCookie.value.trim()) {
    error.value = 'Bitte li_at Cookie-Wert eingeben'
    return
  }

  importingSession.value = true
  error.value = null
  successMessage.value = null

  try {
    const result = await store.importAccountSession(accountId.value, liAtCookie.value.trim())
    successMessage.value =
      'Session erfolgreich importiert! Gueltig bis: ' +
      new Date(result.session_expires_at).toLocaleString('de-DE')
    liAtCookie.value = ''
    const account = await store.fetchAccount(accountId.value)
    currentAccount.value = account
  } catch (err) {
    error.value = 'Session-Import fehlgeschlagen: ' + (err.response?.data?.detail || err.message)
  } finally {
    importingSession.value = false
  }
}

function cancel() {
  router.push('/linkedin')
}
</script>

<template>
  <div class="min-h-screen bg-go4-bg dark:bg-gray-900">
    <PageHeader
      :title="isEdit ? 'Account bearbeiten' : 'Neuer Account'"
      subtitle="LinkedIn Sales Navigator Account"
    >
      <template #actions>
        <button
          class="rounded-lg px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
          @click="cancel"
        >
          Abbrechen
        </button>
        <button
          class="rounded-lg bg-go4-primary px-4 py-2 text-sm text-white hover:bg-go4-primary-dark disabled:opacity-50"
          :disabled="saving"
          @click="save"
        >
          {{ saving ? 'Speichern...' : 'Speichern' }}
        </button>
      </template>
    </PageHeader>

    <div class="mx-auto max-w-2xl px-4 py-6 sm:px-6 lg:px-8">
      <div
        v-if="loading"
        class="py-12 text-center text-go4-muted"
      >
        Laden...
      </div>

      <div
        v-if="successMessage"
        class="mb-4 rounded-lg bg-green-50 p-4 text-green-700 dark:bg-green-900/30 dark:text-green-300"
      >
        {{ successMessage }}
      </div>

      <div
        v-if="error"
        class="mb-4 rounded-lg bg-red-50 p-4 text-red-700 dark:bg-red-900/30 dark:text-red-300"
      >
        {{ error }}
      </div>

      <div
        v-if="!loading"
        class="space-y-6"
      >
        <!-- Account-Daten -->
        <div class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
          <h3 class="mb-4 text-lg font-medium text-go4-secondary dark:text-white">
            Account-Daten
          </h3>

          <form
            class="space-y-5"
            @submit.prevent="save"
          >
            <div>
              <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                Account-Name *
              </label>
              <input
                v-model="formData.name"
                type="text"
                required
                class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                placeholder="z.B. Harry Ketschik"
              >
            </div>

            <div>
              <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                LinkedIn E-Mail *
              </label>
              <input
                v-model="formData.email"
                type="email"
                required
                class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                placeholder="name@example.com"
              >
            </div>

            <div>
              <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                LinkedIn Passwort{{ isEdit ? '' : ' *' }}
              </label>
              <input
                v-model="formData.password"
                type="password"
                :required="!isEdit"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                placeholder="LinkedIn-Passwort"
              >
              <p
                v-if="isEdit"
                class="mt-1 text-xs text-go4-muted dark:text-gray-400"
              >
                Leer lassen um das Passwort nicht zu aendern
              </p>
            </div>

            <div class="flex items-center gap-3">
              <input
                id="sales_navigator"
                v-model="formData.is_sales_navigator"
                type="checkbox"
                class="h-4 w-4 rounded border-gray-300 text-go4-primary"
              >
              <label
                for="sales_navigator"
                class="text-sm text-go4-secondary dark:text-gray-200"
              >
                Sales Navigator Lizenz vorhanden
              </label>
            </div>
          </form>
        </div>

        <!-- Verbindung -->
        <div class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-lg font-medium text-go4-secondary dark:text-white">
              Verbindung
            </h3>
            <span
              v-if="currentAccount"
              :class="[
                'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
                currentAccount.has_valid_session
                  ? 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300'
                  : 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300'
              ]"
            >
              {{ currentAccount.has_valid_session ? 'Verbunden' : 'Nicht verbunden' }}
            </span>
          </div>

          <!-- Nicht gespeichert -->
          <div
            v-if="!isEdit"
            class="rounded-lg bg-gray-50 p-4 text-sm text-go4-muted dark:bg-gray-700/50 dark:text-gray-400"
          >
            Bitte zuerst den Account speichern, um die Verbindung herzustellen.
          </div>

          <!-- Gespeichert: Login-Optionen -->
          <div
            v-else
            class="space-y-4"
          >
            <!-- Auto-Login -->
            <div>
              <p class="mb-3 text-sm text-go4-muted dark:text-gray-400">
                Der Auto-Login nutzt das gespeicherte Passwort und oeffnet einen Browser auf dem Server.
                Bei 2FA/CAPTCHA kannst du per VNC zuschauen und es manuell loesen.
              </p>
              <div class="flex items-center gap-3">
                <button
                  type="button"
                  class="rounded-lg bg-go4-primary px-4 py-2 text-sm text-white hover:bg-go4-primary-dark disabled:opacity-50"
                  :disabled="loggingIn"
                  @click="startLogin"
                >
                  {{ loggingIn ? 'Login laeuft...' : 'Auto-Login starten' }}
                </button>
                <span
                  v-if="loggingIn"
                  class="text-sm text-go4-muted dark:text-gray-400"
                >
                  Warte auf Login... (VNC: 192.168.1.227:5901)
                </span>
              </div>
            </div>

            <!-- Trennlinie -->
            <div class="relative">
              <div class="absolute inset-0 flex items-center">
                <div class="w-full border-t border-gray-200 dark:border-gray-700" />
              </div>
              <div class="relative flex justify-center text-xs">
                <span class="bg-white px-2 text-go4-muted dark:bg-gray-800 dark:text-gray-500">oder</span>
              </div>
            </div>

            <!-- Cookie-Import -->
            <div>
              <button
                type="button"
                class="flex items-center gap-2 text-sm text-go4-muted hover:text-go4-secondary dark:text-gray-400 dark:hover:text-gray-200"
                @click="showCookieImport = !showCookieImport"
              >
                <svg
                  class="h-4 w-4 transition-transform"
                  :class="{ 'rotate-90': showCookieImport }"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M9 5l7 7-7 7"
                  />
                </svg>
                Manueller Cookie-Import (Alternative)
              </button>

              <div
                v-if="showCookieImport"
                class="mt-3 space-y-3"
              >
                <div class="rounded-lg bg-blue-50 p-3 dark:bg-blue-900/20">
                  <ol class="list-decimal list-inside space-y-1 text-xs text-blue-800 dark:text-blue-200">
                    <li>Oeffne <a href="https://www.linkedin.com" target="_blank" class="underline font-medium">linkedin.com</a> und logge dich ein</li>
                    <li>Druecke <kbd class="px-1 py-0.5 rounded bg-blue-100 dark:bg-blue-800 font-mono text-xs">F12</kbd> → Tab <strong>Application</strong> → <strong>Cookies</strong> → linkedin.com</li>
                    <li>Kopiere den Wert von <code class="px-1 py-0.5 rounded bg-blue-100 dark:bg-blue-800 font-mono text-xs">li_at</code></li>
                  </ol>
                </div>

                <div class="flex gap-2">
                  <input
                    v-model="liAtCookie"
                    type="password"
                    class="flex-1 rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                    placeholder="AQEDAQNvY1234..."
                  >
                  <button
                    type="button"
                    class="rounded-lg bg-go4-secondary px-4 py-2 text-sm text-white hover:bg-gray-700 disabled:opacity-50"
                    :disabled="importingSession || !liAtCookie.trim()"
                    @click="importSession"
                  >
                    {{ importingSession ? 'Importiere...' : 'Importieren' }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
