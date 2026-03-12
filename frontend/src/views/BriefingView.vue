<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useBriefingStore } from '@/stores/briefing'
import { useAuthStore } from '@/stores/auth'
import PageHeader from '@/components/ui/PageHeader.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'

const router = useRouter()
const route = useRoute()
const store = useBriefingStore()
const authStore = useAuthStore()

// Tab state from route
const activeTab = computed(() => route.meta?.tab || 'sources')

const tabs = [
  { key: 'sources', label: 'Quellen', route: '/briefing/sources' },
  { key: 'findings', label: 'Findings', route: '/briefing/findings' },
  { key: 'channels', label: 'Channels', route: '/briefing/channels' },
  { key: 'speakers', label: 'Sprecher', route: '/briefing/speakers' }
]

const statusFilter = ref('')
const sourceTypeFilter = ref('')

// Speaker upload form
const speakerName = ref('')
const speakerLanguage = ref('de')
const speakerDescription = ref('')
const speakerFile = ref(null)
const speakerUploading = ref(false)

onMounted(() => {
  store.fetchChannels()
  store.fetchSources()
  store.fetchFindings()
  store.fetchSpeakers()
})

async function handleDeleteChannel(id) {
  if (confirm('Channel und alle Episoden wirklich loeschen?')) {
    await store.removeChannel(id)
  }
}

async function handleToggle(channel) {
  await store.editChannel(channel.id, { active: !channel.active })
}

async function handleCloneChannel(channel) {
  const cloned = await store.cloneOrgChannel(channel.id)
  if (cloned) {
    router.push(`/briefing/channels/${cloned.id}/edit`)
  }
}

async function handleDeleteSource(id) {
  if (confirm('Quelle wirklich loeschen?')) {
    await store.removeSource(id)
  }
}

async function handleRunSource(id) {
  const result = await store.runSingleSource(id)
  if (result) {
    await store.fetchSources()
    await store.fetchFindings()
  }
}

async function handleRunAllSources() {
  const result = await store.runAllSources()
  if (result) {
    await store.fetchSources()
    await store.fetchFindings()
  }
}

async function handleDismissFinding(id) {
  await store.editFinding(id, { status: 'dismissed' })
}

function onSpeakerFileChange(event) {
  speakerFile.value = event.target.files[0] || null
}

async function handleUploadSpeaker() {
  if (!speakerName.value || !speakerFile.value) return
  speakerUploading.value = true
  try {
    const formData = new FormData()
    formData.append('name', speakerName.value)
    formData.append('language', speakerLanguage.value)
    if (speakerDescription.value) formData.append('description', speakerDescription.value)
    formData.append('file', speakerFile.value)
    await store.addSpeaker(formData)
    speakerName.value = ''
    speakerLanguage.value = 'de'
    speakerDescription.value = ''
    speakerFile.value = null
  } catch {
    // error handled by store
  } finally {
    speakerUploading.value = false
  }
}

async function handleDeleteSpeaker(id) {
  if (confirm('Sprecher wirklich loeschen?')) {
    await store.removeSpeaker(id)
  }
}

function formatFileSize(bytes) {
  if (!bytes) return '-'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDuration(seconds) {
  if (!seconds) return '-'
  const min = Math.floor(seconds / 60)
  const sec = seconds % 60
  return `${min}:${sec.toString().padStart(2, '0')}`
}

function speakerPreviewUrl(id) {
  return `/api/v1/briefing/speakers/${id}/preview`
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const sourceTypeLabels = {
  rss: 'RSS',
  website: 'Website',
  websearch: 'Websuche',
  calendar: 'Kalender',
  email: 'E-Mail',
  kpi: 'KPI'
}

const filteredFindings = () => {
  let items = store.findings
  if (statusFilter.value) {
    items = items.filter((f) => f.status === statusFilter.value)
  }
  if (sourceTypeFilter.value) {
    items = items.filter((f) => f.source_type === sourceTypeFilter.value)
  }
  return items
}
</script>

<template>
  <div>
    <PageHeader
      title="Briefing"
      subtitle="Internes Briefing fuer Ihre Zielgruppen"
    >
      <template #actions>
        <router-link
          v-if="activeTab === 'channels'"
          to="/briefing/channels/new"
          class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white transition hover:bg-go4-primary/90"
        >
          Neuer Channel
        </router-link>
        <router-link
          v-if="activeTab === 'sources'"
          to="/briefing/sources/new"
          class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white transition hover:bg-go4-primary/90"
        >
          Neue Quelle
        </router-link>
        <button
          v-if="activeTab === 'sources'"
          :disabled="store.runningSource"
          class="rounded-lg border border-go4-primary px-4 py-2 text-sm font-medium text-go4-primary transition hover:bg-go4-primary/5 disabled:opacity-50"
          @click="handleRunAllSources"
        >
          {{ store.runningSource ? 'Laeuft...' : 'Alle fetchen' }}
        </button>
      </template>
    </PageHeader>

    <!-- Error -->
    <div
      v-if="store.error"
      class="mt-4 rounded-lg bg-red-50 p-4 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-400"
    >
      {{ store.error }}
    </div>

    <!-- Tabs with arrow separators -->
    <div class="mt-4 border-b border-gray-200 dark:border-gray-700">
      <nav class="-mb-px flex items-center">
        <template
          v-for="(tab, index) in tabs"
          :key="tab.key"
        >
          <router-link
            :to="tab.route"
            class="border-b-2 px-1 pb-3 text-sm font-medium transition"
            :class="
              activeTab === tab.key
                ? 'border-go4-primary text-go4-primary'
                : 'border-transparent text-go4-muted dark:text-gray-400 hover:border-gray-300 dark:hover:border-gray-600 hover:text-go4-secondary dark:hover:text-gray-100'
            "
          >
            {{ tab.label }}
          </router-link>
          <span
            v-if="index < tabs.length - 1"
            class="mx-3 pb-3 text-go4-muted dark:text-gray-500 select-none"
          >
            &rarr;
          </span>
        </template>
      </nav>
    </div>

    <!-- Sources Tab -->
    <div
      v-if="activeTab === 'sources'"
      class="mt-6"
    >
      <div
        v-if="store.sourcesLoading"
        class="flex items-center justify-center py-12"
      >
        <span class="text-go4-muted dark:text-gray-400">Laden...</span>
      </div>

      <EmptyState
        v-else-if="store.sources.length === 0"
        title="Noch keine Quellen"
        description="Erstellen Sie eine Briefing-Quelle (RSS, Website, Kalender, etc.)."
      />

      <template v-else>
        <!-- Meine Quellen -->
        <div
          v-if="store.mySources.length > 0"
          class="mb-8"
        >
          <h3
            class="mb-3 text-sm font-semibold uppercase tracking-wider text-go4-muted dark:text-gray-400"
          >
            Meine Quellen
          </h3>
          <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            <div
              v-for="source in store.mySources"
              :key="source.id"
              class="rounded-lg bg-white p-5 shadow-sm transition hover:shadow-md dark:bg-gray-800"
            >
              <div class="flex items-start justify-between">
                <div class="min-w-0 flex-1">
                  <p class="text-base font-semibold text-go4-secondary dark:text-gray-100">
                    {{ source.name }}
                  </p>
                  <p class="mt-1 text-xs text-go4-muted dark:text-gray-400">
                    {{ sourceTypeLabels[source.source_type] || source.source_type }}
                  </p>
                </div>
                <span
                  class="ml-2 shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium"
                  :class="
                    source.active
                      ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                      : 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400'
                  "
                >
                  {{ source.active ? 'Aktiv' : 'Inaktiv' }}
                </span>
              </div>
              <!-- OAuth status for calendar/email -->
              <div
                v-if="['calendar', 'email'].includes(source.source_type)"
                class="mt-2"
              >
                <span
                  v-if="source.oauth_connected"
                  class="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700 dark:bg-green-900/30 dark:text-green-400"
                >
                  Verbunden
                  <span
                    v-if="source.oauth_email"
                    class="font-normal text-green-600 dark:text-green-500"
                  >
                    ({{ source.oauth_email }})
                  </span>
                </span>
                <span
                  v-else
                  class="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-500 dark:bg-gray-700 dark:text-gray-400"
                >
                  Nicht verbunden
                </span>
              </div>
              <p
                v-else-if="source.url"
                class="mt-2 truncate text-xs text-gray-400 dark:text-gray-500"
              >
                {{ source.url }}
              </p>
              <div class="mt-3 flex items-center gap-4 text-xs text-go4-muted dark:text-gray-400">
                <span>Alle {{ source.fetch_interval_hours }}h</span>
                <span v-if="source.last_fetched_at">
                  Letzter Fetch: {{ formatDate(source.last_fetched_at) }}
                </span>
                <span v-else>Noch nie gefetcht</span>
              </div>
              <div
                class="mt-4 flex items-center gap-2 border-t border-gray-100 pt-3 dark:border-gray-700"
              >
                <router-link
                  :to="`/briefing/sources/${source.id}/edit`"
                  class="rounded bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
                >
                  Bearbeiten
                </router-link>
                <button
                  :disabled="store.runningSource"
                  class="rounded bg-sky-100 px-2.5 py-1 text-xs font-medium text-sky-700 hover:bg-sky-200 disabled:opacity-50 dark:bg-sky-900/30 dark:text-sky-400 dark:hover:bg-sky-800/40"
                  @click="handleRunSource(source.id)"
                >
                  Jetzt fetchen
                </button>
                <button
                  class="rounded bg-red-100 px-2.5 py-1 text-xs font-medium text-red-700 hover:bg-red-200 dark:bg-red-900/30 dark:text-red-400 dark:hover:bg-red-800/40"
                  @click="handleDeleteSource(source.id)"
                >
                  Loeschen
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Organisation Quellen -->
        <div v-if="store.orgSources.length > 0">
          <h3
            class="mb-3 text-sm font-semibold uppercase tracking-wider text-go4-muted dark:text-gray-400"
          >
            Organisation
          </h3>
          <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            <div
              v-for="source in store.orgSources"
              :key="source.id"
              class="rounded-lg bg-white p-5 shadow-sm transition hover:shadow-md dark:bg-gray-800"
            >
              <div class="flex items-start justify-between">
                <div class="min-w-0 flex-1">
                  <p class="text-base font-semibold text-go4-secondary dark:text-gray-100">
                    {{ source.name }}
                  </p>
                  <p class="mt-1 text-xs text-go4-muted dark:text-gray-400">
                    {{ sourceTypeLabels[source.source_type] || source.source_type }}
                  </p>
                </div>
                <span
                  class="ml-2 shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium"
                  :class="
                    source.active
                      ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                      : 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400'
                  "
                >
                  {{ source.active ? 'Aktiv' : 'Inaktiv' }}
                </span>
              </div>
              <!-- OAuth status for calendar/email -->
              <div
                v-if="['calendar', 'email'].includes(source.source_type)"
                class="mt-2"
              >
                <span
                  v-if="source.oauth_connected"
                  class="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700 dark:bg-green-900/30 dark:text-green-400"
                >
                  Verbunden
                  <span
                    v-if="source.oauth_email"
                    class="font-normal text-green-600 dark:text-green-500"
                  >
                    ({{ source.oauth_email }})
                  </span>
                </span>
                <span
                  v-else
                  class="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-500 dark:bg-gray-700 dark:text-gray-400"
                >
                  Nicht verbunden
                </span>
              </div>
              <p
                v-else-if="source.url"
                class="mt-2 truncate text-xs text-gray-400 dark:text-gray-500"
              >
                {{ source.url }}
              </p>
              <div class="mt-3 flex items-center gap-4 text-xs text-go4-muted dark:text-gray-400">
                <span>Alle {{ source.fetch_interval_hours }}h</span>
                <span v-if="source.last_fetched_at">
                  Letzter Fetch: {{ formatDate(source.last_fetched_at) }}
                </span>
                <span v-else>Noch nie gefetcht</span>
              </div>
              <div
                class="mt-4 flex items-center gap-2 border-t border-gray-100 pt-3 dark:border-gray-700"
              >
                <template v-if="authStore.isAdmin">
                  <router-link
                    :to="`/briefing/sources/${source.id}/edit`"
                    class="rounded bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
                  >
                    Bearbeiten
                  </router-link>
                  <button
                    :disabled="store.runningSource"
                    class="rounded bg-sky-100 px-2.5 py-1 text-xs font-medium text-sky-700 hover:bg-sky-200 disabled:opacity-50 dark:bg-sky-900/30 dark:text-sky-400 dark:hover:bg-sky-800/40"
                    @click="handleRunSource(source.id)"
                  >
                    Jetzt fetchen
                  </button>
                  <button
                    class="rounded bg-red-100 px-2.5 py-1 text-xs font-medium text-red-700 hover:bg-red-200 dark:bg-red-900/30 dark:text-red-400 dark:hover:bg-red-800/40"
                    @click="handleDeleteSource(source.id)"
                  >
                    Loeschen
                  </button>
                </template>
                <button
                  v-else
                  :disabled="store.runningSource"
                  class="rounded bg-sky-100 px-2.5 py-1 text-xs font-medium text-sky-700 hover:bg-sky-200 disabled:opacity-50 dark:bg-sky-900/30 dark:text-sky-400 dark:hover:bg-sky-800/40"
                  @click="handleRunSource(source.id)"
                >
                  Jetzt fetchen
                </button>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- Findings Tab -->
    <div
      v-else-if="activeTab === 'findings'"
      class="mt-6"
    >
      <!-- Filters -->
      <div class="mb-4 flex flex-wrap items-center gap-3">
        <select
          v-model="statusFilter"
          class="rounded-lg border border-gray-300 px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
        >
          <option value="">
            Alle Status
          </option>
          <option value="new">
            Neu
          </option>
          <option value="used">
            Verwendet
          </option>
          <option value="dismissed">
            Verworfen
          </option>
        </select>
        <select
          v-model="sourceTypeFilter"
          class="rounded-lg border border-gray-300 px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
        >
          <option value="">
            Alle Typen
          </option>
          <option value="rss">
            RSS
          </option>
          <option value="website">
            Website
          </option>
          <option value="websearch">
            Websuche
          </option>
          <option value="calendar">
            Kalender
          </option>
          <option value="email">
            E-Mail
          </option>
          <option value="kpi">
            KPI
          </option>
        </select>
      </div>

      <div
        v-if="store.findingsLoading"
        class="flex items-center justify-center py-12"
      >
        <span class="text-go4-muted dark:text-gray-400">Laden...</span>
      </div>

      <EmptyState
        v-else-if="filteredFindings().length === 0"
        title="Keine Findings"
        description="Erstellen Sie Quellen und fetchen Sie diese, um Findings zu erhalten."
      />

      <div
        v-else
        class="overflow-hidden rounded-lg bg-white shadow-sm dark:bg-gray-800"
      >
        <table class="w-full text-left text-sm">
          <thead
            class="border-b border-gray-100 bg-gray-50 text-xs uppercase tracking-wider text-go4-muted dark:border-gray-700 dark:bg-gray-800/50 dark:text-gray-400"
          >
            <tr>
              <th class="px-4 py-3 font-medium">
                Titel
              </th>
              <th class="hidden px-4 py-3 font-medium md:table-cell">
                Typ
              </th>
              <th class="px-4 py-3 font-medium">
                Status
              </th>
              <th class="hidden px-4 py-3 font-medium lg:table-cell">
                Gefunden
              </th>
              <th class="px-4 py-3 text-right font-medium">
                Aktionen
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50 dark:divide-gray-700">
            <tr
              v-for="finding in filteredFindings()"
              :key="finding.id"
              class="transition hover:bg-gray-50/50 dark:hover:bg-gray-700/50"
            >
              <td class="max-w-xs px-4 py-3">
                <a
                  v-if="finding.url"
                  :href="finding.url"
                  target="_blank"
                  class="font-medium text-go4-secondary hover:text-go4-primary dark:text-gray-100"
                >
                  {{ finding.title }}
                </a>
                <p
                  v-else
                  class="font-medium text-go4-secondary dark:text-gray-100"
                >
                  {{ finding.title }}
                </p>
                <p
                  v-if="finding.summary"
                  class="mt-0.5 line-clamp-1 text-xs text-go4-muted dark:text-gray-400"
                >
                  {{ finding.summary }}
                </p>
              </td>
              <td class="hidden px-4 py-3 text-xs text-go4-muted dark:text-gray-400 md:table-cell">
                {{ sourceTypeLabels[finding.source_type] || finding.source_type || '-' }}
              </td>
              <td class="px-4 py-3">
                <StatusBadge :status="finding.status" />
              </td>
              <td class="hidden px-4 py-3 text-xs text-gray-400 dark:text-gray-500 lg:table-cell">
                {{ formatDate(finding.found_at) }}
              </td>
              <td class="px-4 py-3">
                <div class="flex items-center justify-end gap-1.5">
                  <button
                    v-if="finding.status === 'new'"
                    class="rounded bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
                    @click="handleDismissFinding(finding.id)"
                  >
                    Verwerfen
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Channels Tab -->
    <div
      v-else-if="activeTab === 'channels'"
      class="mt-6"
    >
      <div
        v-if="store.loading"
        class="flex items-center justify-center py-12"
      >
        <span class="text-go4-muted dark:text-gray-400">Laden...</span>
      </div>

      <EmptyState
        v-else-if="store.channels.length === 0"
        title="Noch keine Channels"
        description="Erstellen Sie einen Briefing-Channel fuer Ihre erste Zielgruppe."
      />

      <template v-else>
        <!-- Meine Briefings -->
        <div
          v-if="store.myChannels.length > 0"
          class="mb-8"
        >
          <h3
            class="mb-3 text-sm font-semibold uppercase tracking-wider text-go4-muted dark:text-gray-400"
          >
            Meine Briefings
          </h3>
          <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            <div
              v-for="channel in store.myChannels"
              :key="channel.id"
              class="rounded-lg bg-white p-5 shadow-sm transition hover:shadow-md dark:bg-gray-800"
            >
              <div class="flex items-start justify-between">
                <div class="min-w-0 flex-1">
                  <router-link
                    :to="`/briefing/channels/${channel.id}`"
                    class="text-base font-semibold text-go4-secondary hover:text-go4-primary dark:text-gray-100"
                  >
                    {{ channel.name }}
                  </router-link>
                  <p
                    v-if="channel.target_audience"
                    class="mt-1 text-xs text-go4-muted dark:text-gray-400"
                  >
                    Zielgruppe: {{ channel.target_audience }}
                  </p>
                </div>
                <button
                  class="ml-2 shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium transition"
                  :class="
                    channel.active
                      ? 'bg-green-100 text-green-700 hover:bg-green-200 dark:bg-green-900/30 dark:text-green-400 dark:hover:bg-green-800/40'
                      : 'bg-gray-100 text-gray-500 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-400 dark:hover:bg-gray-600'
                  "
                  @click="handleToggle(channel)"
                >
                  {{ channel.active ? 'Aktiv' : 'Inaktiv' }}
                </button>
              </div>
              <p
                v-if="channel.description"
                class="mt-2 line-clamp-2 text-sm text-gray-500 dark:text-gray-400"
              >
                {{ channel.description }}
              </p>
              <div class="mt-4 flex items-center gap-4 text-xs text-go4-muted dark:text-gray-400">
                <span>{{ channel.episode_count || 0 }} Episoden</span>
                <span v-if="channel.output_format && channel.output_format !== 'audio'">
                  {{ channel.output_format === 'both' ? 'Audio + Text' : 'Text' }}
                </span>
              </div>
              <div
                class="mt-4 flex items-center gap-2 border-t border-gray-100 pt-3 dark:border-gray-700"
              >
                <router-link
                  :to="`/briefing/channels/${channel.id}`"
                  class="rounded bg-go4-primary/10 px-2.5 py-1 text-xs font-medium text-go4-primary hover:bg-go4-primary/20"
                >
                  Details
                </router-link>
                <router-link
                  :to="`/briefing/channels/${channel.id}/edit`"
                  class="rounded bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
                >
                  Bearbeiten
                </router-link>
                <button
                  class="rounded bg-red-100 px-2.5 py-1 text-xs font-medium text-red-700 hover:bg-red-200 dark:bg-red-900/30 dark:text-red-400 dark:hover:bg-red-800/40"
                  @click="handleDeleteChannel(channel.id)"
                >
                  Loeschen
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Org-Vorlagen -->
        <div v-if="store.orgChannels.length > 0">
          <h3
            class="mb-3 text-sm font-semibold uppercase tracking-wider text-go4-muted dark:text-gray-400"
          >
            Org-Vorlagen
          </h3>
          <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            <div
              v-for="channel in store.orgChannels"
              :key="channel.id"
              class="rounded-lg bg-white p-5 shadow-sm transition hover:shadow-md dark:bg-gray-800"
            >
              <div class="flex items-start justify-between">
                <div class="min-w-0 flex-1">
                  <router-link
                    :to="`/briefing/channels/${channel.id}`"
                    class="text-base font-semibold text-go4-secondary hover:text-go4-primary dark:text-gray-100"
                  >
                    {{ channel.name }}
                  </router-link>
                  <p
                    v-if="channel.target_audience"
                    class="mt-1 text-xs text-go4-muted dark:text-gray-400"
                  >
                    Zielgruppe: {{ channel.target_audience }}
                  </p>
                </div>
                <button
                  class="ml-2 shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium transition"
                  :class="
                    channel.active
                      ? 'bg-green-100 text-green-700 hover:bg-green-200 dark:bg-green-900/30 dark:text-green-400 dark:hover:bg-green-800/40'
                      : 'bg-gray-100 text-gray-500 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-400 dark:hover:bg-gray-600'
                  "
                  @click="authStore.isAdmin && handleToggle(channel)"
                >
                  {{ channel.active ? 'Aktiv' : 'Inaktiv' }}
                </button>
              </div>
              <p
                v-if="channel.description"
                class="mt-2 line-clamp-2 text-sm text-gray-500 dark:text-gray-400"
              >
                {{ channel.description }}
              </p>
              <div class="mt-4 flex items-center gap-4 text-xs text-go4-muted dark:text-gray-400">
                <span>{{ channel.episode_count || 0 }} Episoden</span>
                <span>{{ channel.subscriber_count || 0 }} Abonnenten</span>
                <span v-if="channel.output_format && channel.output_format !== 'audio'">
                  {{ channel.output_format === 'both' ? 'Audio + Text' : 'Text' }}
                </span>
              </div>
              <div
                class="mt-4 flex items-center gap-2 border-t border-gray-100 pt-3 dark:border-gray-700"
              >
                <router-link
                  :to="`/briefing/channels/${channel.id}`"
                  class="rounded bg-go4-primary/10 px-2.5 py-1 text-xs font-medium text-go4-primary hover:bg-go4-primary/20"
                >
                  Details
                </router-link>
                <button
                  class="rounded bg-sky-100 px-2.5 py-1 text-xs font-medium text-sky-700 hover:bg-sky-200 dark:bg-sky-900/30 dark:text-sky-400 dark:hover:bg-sky-800/40"
                  @click="handleCloneChannel(channel)"
                >
                  Anpassen
                </button>
                <template v-if="authStore.isAdmin">
                  <router-link
                    :to="`/briefing/channels/${channel.id}/edit`"
                    class="rounded bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
                  >
                    Bearbeiten
                  </router-link>
                  <button
                    class="rounded bg-red-100 px-2.5 py-1 text-xs font-medium text-red-700 hover:bg-red-200 dark:bg-red-900/30 dark:text-red-400 dark:hover:bg-red-800/40"
                    @click="handleDeleteChannel(channel.id)"
                  >
                    Loeschen
                  </button>
                </template>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- Speakers Tab -->
    <div
      v-else-if="activeTab === 'speakers'"
      class="mt-6"
    >
      <div
        v-if="store.speakersLoading"
        class="flex items-center justify-center py-12"
      >
        <span class="text-go4-muted dark:text-gray-400">Laden...</span>
      </div>

      <template v-else>
        <!-- Upload Form (Admin only) -->
        <div
          v-if="authStore.isAdmin"
          class="mb-6 rounded-lg bg-white p-5 shadow-sm dark:bg-gray-800"
        >
          <h3 class="mb-4 text-sm font-semibold text-go4-secondary dark:text-gray-100">
            Neuen Sprecher hochladen
          </h3>
          <form
            class="space-y-4"
            @submit.prevent="handleUploadSpeaker"
          >
            <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
              <div>
                <label class="block text-xs font-medium text-go4-muted dark:text-gray-400">Name *</label>
                <input
                  v-model="speakerName"
                  required
                  class="mt-1 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-800 focus:border-go4-primary focus:ring-1 focus:ring-go4-primary dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
                  placeholder="Thomas"
                >
              </div>
              <div>
                <label class="block text-xs font-medium text-go4-muted dark:text-gray-400">Sprache</label>
                <select
                  v-model="speakerLanguage"
                  class="mt-1 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-800 focus:border-go4-primary focus:ring-1 focus:ring-go4-primary dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
                >
                  <option value="de">
                    Deutsch
                  </option>
                  <option value="en">
                    Englisch
                  </option>
                </select>
              </div>
              <div>
                <label class="block text-xs font-medium text-go4-muted dark:text-gray-400">WAV-Datei * (6-30s)</label>
                <input
                  type="file"
                  accept=".wav"
                  class="mt-1 block w-full text-sm text-gray-500 file:mr-3 file:rounded file:border-0 file:bg-go4-primary/10 file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-go4-primary dark:text-gray-400"
                  @change="onSpeakerFileChange"
                >
              </div>
            </div>
            <div>
              <label class="block text-xs font-medium text-go4-muted dark:text-gray-400">Beschreibung</label>
              <input
                v-model="speakerDescription"
                class="mt-1 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-800 focus:border-go4-primary focus:ring-1 focus:ring-go4-primary dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
                placeholder="Maennliche Stimme, ruhig und professionell"
              >
            </div>
            <button
              type="submit"
              :disabled="speakerUploading || !speakerName || !speakerFile"
              class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white transition hover:bg-go4-primary/90 disabled:opacity-50"
            >
              {{ speakerUploading ? 'Hochladen...' : 'Sprecher hochladen' }}
            </button>
          </form>
        </div>

        <!-- Speaker List -->
        <EmptyState
          v-if="store.speakers.length === 0"
          title="Noch keine Sprecher"
          description="Laden Sie eine WAV-Datei (6-30s) hoch, um XTTS Voice Cloning zu nutzen."
        />
        <div
          v-else
          class="overflow-hidden rounded-lg bg-white shadow-sm dark:bg-gray-800"
        >
          <table class="w-full text-left text-sm">
            <thead
              class="border-b border-gray-100 bg-gray-50 text-xs uppercase tracking-wider text-go4-muted dark:border-gray-700 dark:bg-gray-800/50 dark:text-gray-400"
            >
              <tr>
                <th class="px-4 py-3 font-medium">
                  Name
                </th>
                <th class="px-4 py-3 font-medium">
                  Sprache
                </th>
                <th class="hidden px-4 py-3 font-medium md:table-cell">
                  Dauer
                </th>
                <th class="hidden px-4 py-3 font-medium md:table-cell">
                  Groesse
                </th>
                <th class="px-4 py-3 text-right font-medium">
                  Aktionen
                </th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-50 dark:divide-gray-700">
              <tr
                v-for="speaker in store.speakers"
                :key="speaker.id"
                class="transition hover:bg-gray-50/50 dark:hover:bg-gray-700/50"
              >
                <td class="px-4 py-3">
                  <p class="font-medium text-go4-secondary dark:text-gray-100">
                    {{ speaker.name }}
                  </p>
                  <p
                    v-if="speaker.description"
                    class="mt-0.5 text-xs text-go4-muted dark:text-gray-400"
                  >
                    {{ speaker.description }}
                  </p>
                </td>
                <td class="px-4 py-3 text-xs text-go4-muted dark:text-gray-400">
                  {{ speaker.language === 'de' ? 'Deutsch' : 'Englisch' }}
                </td>
                <td
                  class="hidden px-4 py-3 text-xs text-go4-muted dark:text-gray-400 md:table-cell"
                >
                  {{ formatDuration(speaker.duration_seconds) }}
                </td>
                <td
                  class="hidden px-4 py-3 text-xs text-go4-muted dark:text-gray-400 md:table-cell"
                >
                  {{ formatFileSize(speaker.file_size_bytes) }}
                </td>
                <td class="px-4 py-3">
                  <div class="flex items-center justify-end gap-1.5">
                    <a
                      :href="speakerPreviewUrl(speaker.id)"
                      target="_blank"
                      class="rounded bg-sky-100 px-2.5 py-1 text-xs font-medium text-sky-700 hover:bg-sky-200 dark:bg-sky-900/30 dark:text-sky-400 dark:hover:bg-sky-800/40"
                    >
                      Vorhoeren
                    </a>
                    <button
                      v-if="authStore.isAdmin"
                      class="rounded bg-red-100 px-2.5 py-1 text-xs font-medium text-red-700 hover:bg-red-200 dark:bg-red-900/30 dark:text-red-400 dark:hover:bg-red-800/40"
                      @click="handleDeleteSpeaker(speaker.id)"
                    >
                      Loeschen
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </div>
  </div>
</template>
