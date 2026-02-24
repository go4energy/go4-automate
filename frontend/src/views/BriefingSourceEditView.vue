<script setup>
import { ref, onMounted, computed, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useBriefingStore } from '@/stores/briefing'
import { useAuthStore } from '@/stores/auth'
import { getOAuthAuthUrl } from '@/api/briefing'
import PageHeader from '@/components/ui/PageHeader.vue'
import TagSelector from '@/components/ui/TagSelector.vue'
import StreamSelector from '@/components/ui/StreamSelector.vue'

const route = useRoute()
const router = useRouter()
const store = useBriefingStore()
const authStore = useAuthStore()

const isEdit = computed(() => !!route.params.id)
const saving = ref(false)
const orgWide = ref(false)

const form = ref({
  name: '',
  source_type: 'rss',
  url: '',
  keywords: [],
  active: true,
  fetch_interval_hours: 24,
  config: {},
  tags: [],
  streams: []
})

// OAuth state from API response (not from form.config which is sanitized)
const oauthConnected = ref(false)
const oauthEmail = ref('')
const oauthProvider = ref('')

const keywordsText = ref('')

const sourceTypes = [
  { value: 'rss', label: 'RSS Feed' },
  { value: 'website', label: 'Website' },
  { value: 'websearch', label: 'Websuche' },
  { value: 'calendar', label: 'Kalender' },
  { value: 'email', label: 'E-Mail' },
  { value: 'kpi', label: 'KPI Endpoint' }
]

const needsUrl = computed(() => ['rss', 'website', 'kpi'].includes(form.value.source_type))
const needsKeywords = computed(() =>
  ['rss', 'website', 'websearch', 'email'].includes(form.value.source_type)
)
const needsSelector = computed(() => form.value.source_type === 'website')
const isOAuthType = computed(() => ['calendar', 'email'].includes(form.value.source_type))

const oauthProviderLabel = computed(() => {
  if (oauthProvider.value === 'microsoft') return 'Microsoft 365'
  if (oauthProvider.value === 'google') return 'Google'
  return ''
})

async function loadSourceData() {
  const data = await store.fetchSource(route.params.id)
  Object.keys(form.value).forEach((key) => {
    if (data[key] !== undefined && data[key] !== null) {
      form.value[key] = data[key]
    }
  })
  form.value.tags = data.tags || []
  form.value.streams = data.streams || []
  keywordsText.value = (data.keywords || []).join(', ')
  // OAuth state from response
  oauthConnected.value = data.oauth_connected || false
  oauthEmail.value = data.oauth_email || ''
  oauthProvider.value = data.config?.oauth_provider || ''
}

onMounted(async () => {
  if (isEdit.value) {
    await loadSourceData()
  }
})

// OAuth popup message handler
function onOAuthMessage(e) {
  if (e.data?.type === 'oauth_success') {
    loadSourceData()
  }
}

onMounted(() => {
  window.addEventListener('message', onOAuthMessage)
})

onBeforeUnmount(() => {
  window.removeEventListener('message', onOAuthMessage)
})

async function connectOAuth(provider) {
  try {
    const { data } = await getOAuthAuthUrl(route.params.id, provider)
    window.open(data.auth_url, 'oauth', 'width=600,height=700')
  } catch {
    store.error = 'OAuth-URL konnte nicht geladen werden'
  }
}

async function handleDisconnect() {
  if (!confirm('OAuth-Verbindung wirklich trennen?')) return
  try {
    const data = await store.disconnectSourceOAuth(Number(route.params.id))
    oauthConnected.value = false
    oauthEmail.value = ''
    oauthProvider.value = ''
    if (data) {
      Object.keys(form.value).forEach((key) => {
        if (data[key] !== undefined && data[key] !== null) {
          form.value[key] = data[key]
        }
      })
    }
  } catch {
    // error handled by store
  }
}

async function handleSubmit() {
  saving.value = true
  try {
    const data = { ...form.value }

    // Parse keywords from comma-separated text
    if (keywordsText.value.trim()) {
      data.keywords = keywordsText.value
        .split(',')
        .map((k) => k.trim())
        .filter(Boolean)
    } else {
      data.keywords = []
    }

    // Ensure config is an object
    if (!data.config || typeof data.config !== 'object') {
      data.config = {}
    }

    if (isEdit.value) {
      await store.editSource(route.params.id, data)
    } else {
      const params = orgWide.value ? { org_wide: true } : undefined
      const created = await store.addSource(data, params)
      // Redirect to edit view so user can connect OAuth
      if (isOAuthType.value && created?.id) {
        router.push(`/briefing/sources/${created.id}/edit`)
        return
      }
    }
    router.push('/briefing')
  } catch {
    // error handled by store
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div>
    <PageHeader
      :title="isEdit ? 'Quelle bearbeiten' : 'Neue Quelle'"
      :subtitle="isEdit ? form.name : 'Briefing-Quelle erstellen'"
    />

    <!-- Error -->
    <div
      v-if="store.error"
      class="mt-4 rounded-lg bg-red-50 p-4 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-400"
    >
      {{ store.error }}
    </div>

    <form
      class="mt-6 max-w-2xl space-y-6"
      @submit.prevent="handleSubmit"
    >
      <!-- Name + Type -->
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div>
          <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">Name *</label>
          <input
            v-model="form.name"
            required
            class="mt-1 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-800 focus:border-go4-primary focus:ring-1 focus:ring-go4-primary dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
            placeholder="Heise RSS Feed"
          >
        </div>
        <div>
          <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">Typ *</label>
          <select
            v-model="form.source_type"
            :disabled="isEdit"
            class="mt-1 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-800 focus:border-go4-primary focus:ring-1 focus:ring-go4-primary disabled:bg-gray-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 dark:disabled:bg-gray-800/50"
          >
            <option
              v-for="t in sourceTypes"
              :key="t.value"
              :value="t.value"
            >
              {{ t.label }}
            </option>
          </select>
        </div>
      </div>

      <!-- URL (conditional) -->
      <div v-if="needsUrl">
        <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">
          URL {{ form.source_type === 'kpi' ? '(Endpoint)' : '' }} *
        </label>
        <input
          v-model="form.url"
          :required="needsUrl"
          type="url"
          class="mt-1 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-800 focus:border-go4-primary focus:ring-1 focus:ring-go4-primary dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
          placeholder="https://www.heise.de/rss/heise.rdf"
        >
      </div>

      <!-- Keywords (conditional) -->
      <div v-if="needsKeywords">
        <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">
          Keywords (kommagetrennt)
        </label>
        <input
          v-model="keywordsText"
          class="mt-1 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-800 focus:border-go4-primary focus:ring-1 focus:ring-go4-primary dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
          :placeholder="
            form.source_type === 'email'
              ? 'projekt, meeting, bericht'
              : 'solar, energie, photovoltaik'
          "
        >
        <p class="mt-1 text-xs text-go4-muted dark:text-gray-400">
          {{
            form.source_type === 'email'
              ? 'Nur E-Mails mit diesen Begriffen werden gespeichert. Leer = alle E-Mails.'
              : 'Nur Ergebnisse mit diesen Begriffen werden gespeichert. Leer = alle Ergebnisse.'
          }}
        </p>
      </div>

      <!-- CSS Selector (website only) -->
      <div v-if="needsSelector">
        <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">
          CSS-Selector
        </label>
        <input
          v-model="form.config.selector"
          class="mt-1 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-800 focus:border-go4-primary focus:ring-1 focus:ring-go4-primary dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
          placeholder="article, .post, .entry"
        >
        <p class="mt-1 text-xs text-go4-muted dark:text-gray-400">
          CSS-Selector fuer Artikel-Elemente. Standard: article, .post, .entry
        </p>
      </div>

      <!-- OAuth: Connected state -->
      <div
        v-if="isOAuthType && isEdit && oauthConnected"
        class="rounded-lg bg-green-50 p-4 dark:bg-green-900/20"
      >
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm font-medium text-green-700 dark:text-green-400">
              Verbunden
            </p>
            <p class="mt-0.5 text-xs text-green-600 dark:text-green-500">
              {{ oauthEmail }} ({{ oauthProviderLabel }})
            </p>
          </div>
          <button
            type="button"
            class="text-xs font-medium text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300"
            @click="handleDisconnect"
          >
            Trennen
          </button>
        </div>
      </div>

      <!-- OAuth: Not connected, edit mode — connect buttons -->
      <div
        v-else-if="isOAuthType && isEdit && !oauthConnected"
        class="rounded-lg bg-sky-50 p-4 dark:bg-sky-900/20"
      >
        <p class="text-sm font-medium text-sky-700 dark:text-sky-400">
          Konto verbinden
        </p>
        <p class="mt-1 text-xs text-sky-600 dark:text-sky-500">
          Verbinden Sie Ihr Konto um
          {{ form.source_type === 'calendar' ? 'Kalender-Termine' : 'E-Mails' }} abzurufen.
        </p>
        <div class="mt-3 flex gap-2">
          <button
            type="button"
            class="rounded-lg bg-[#0078d4] px-4 py-2 text-sm font-medium text-white transition hover:bg-[#0078d4]/90"
            @click="connectOAuth('microsoft')"
          >
            Microsoft 365
          </button>
          <button
            type="button"
            class="rounded-lg bg-[#4285f4] px-4 py-2 text-sm font-medium text-white transition hover:bg-[#4285f4]/90"
            @click="connectOAuth('google')"
          >
            Google
          </button>
        </div>
      </div>

      <!-- OAuth: Create mode — save first hint -->
      <div
        v-else-if="isOAuthType && !isEdit"
        class="rounded-lg bg-amber-50 p-4 text-sm text-amber-700 dark:bg-amber-900/20 dark:text-amber-400"
      >
        Speichern Sie die Quelle zuerst, dann koennen Sie Ihr Konto verbinden.
      </div>

      <!-- Calendar/Email specific config -->
      <div v-if="isOAuthType">
        <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">
          Tage zurueck
        </label>
        <input
          v-model.number="form.config.days_back"
          type="number"
          min="1"
          max="30"
          class="mt-1 block w-32 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-800 focus:border-go4-primary focus:ring-1 focus:ring-go4-primary dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
          placeholder="7"
        >
        <p class="mt-1 text-xs text-go4-muted dark:text-gray-400">
          {{
            form.source_type === 'calendar'
              ? 'Kalender-Termine der letzten N Tage abrufen (Standard: 7)'
              : 'E-Mails der letzten N Tage abrufen (Standard: 7)'
          }}
        </p>
      </div>

      <!-- Fetch Interval + Active -->
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div>
          <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">
            Fetch-Intervall (Stunden)
          </label>
          <input
            v-model.number="form.fetch_interval_hours"
            type="number"
            min="1"
            max="720"
            class="mt-1 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-800 focus:border-go4-primary focus:ring-1 focus:ring-go4-primary dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
          >
        </div>
        <div class="flex items-end pb-2">
          <label class="flex items-center gap-2">
            <input
              v-model="form.active"
              type="checkbox"
              class="h-4 w-4 rounded border-gray-300 text-go4-primary focus:ring-go4-primary dark:border-gray-600"
            >
            <span class="text-sm text-go4-secondary dark:text-gray-100">Aktiv</span>
          </label>
        </div>
      </div>

      <!-- Tags + Streams -->
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div>
          <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">
            Tags
          </label>
          <div class="mt-1">
            <TagSelector
              v-model="form.tags"
              placeholder="Tags auswaehlen..."
            />
          </div>
        </div>
        <div>
          <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">
            Streams
          </label>
          <div class="mt-1">
            <StreamSelector
              v-model="form.streams"
              placeholder="Streams auswaehlen..."
            />
          </div>
        </div>
      </div>

      <!-- Org-Wide Toggle (Admin only, create mode) -->
      <div
        v-if="authStore.isAdmin && !isEdit"
        class="flex items-center gap-3 rounded-lg bg-sky-50 dark:bg-sky-900/20 p-4"
      >
        <label class="flex items-center gap-2">
          <input
            v-model="orgWide"
            type="checkbox"
            class="h-4 w-4 rounded border-gray-300 text-go4-primary focus:ring-go4-primary dark:border-gray-600"
          >
          <span class="text-sm font-medium text-sky-700 dark:text-sky-400">Org-weite Quelle (fuer alle Mitarbeiter sichtbar)</span>
        </label>
      </div>

      <!-- Actions -->
      <div class="flex items-center gap-3 border-t border-gray-200 pt-6 dark:border-gray-700">
        <button
          type="submit"
          :disabled="saving"
          class="rounded-lg bg-go4-primary px-5 py-2 text-sm font-medium text-white transition hover:bg-go4-primary/90 disabled:opacity-50"
        >
          {{ saving ? 'Speichern...' : isEdit ? 'Speichern' : 'Quelle erstellen' }}
        </button>
        <router-link
          to="/briefing"
          class="rounded-lg border border-gray-300 px-5 py-2 text-sm font-medium text-go4-secondary hover:bg-gray-50 dark:border-gray-600 dark:text-gray-100 dark:hover:bg-gray-700"
        >
          Abbrechen
        </router-link>
      </div>
    </form>
  </div>
</template>
