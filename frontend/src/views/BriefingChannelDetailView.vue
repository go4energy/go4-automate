<script setup>
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useBriefingStore } from '@/stores/briefing'
import { useAuthStore } from '@/stores/auth'
import { useTabState } from '@/composables/useTabState'
import PageHeader from '@/components/ui/PageHeader.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import EmptyState from '@/components/ui/EmptyState.vue'

const route = useRoute()
const router = useRouter()
const store = useBriefingStore()
const authStore = useAuthStore()

const activeTab = useTabState('briefing-channel', 'episodes', ['episodes', 'sources'])
const tabs = [
  { key: 'episodes', label: 'Episoden' },
  { key: 'sources', label: 'Quellen' }
]

const isOrgChannel = () => store.currentChannel?.user_id === null
const canEdit = () => !isOrgChannel() || authStore.isAdmin

onMounted(async () => {
  await store.fetchChannel(route.params.id)
  await store.fetchEpisodes(route.params.id)
  await store.fetchSources()
  await store.fetchChannelSources(route.params.id)
  store.fetchSpeakers()
})

function speakerName() {
  if (!store.currentChannel?.xtts_speaker_id) return ''
  const speaker = store.speakers.find((s) => s.id === store.currentChannel.xtts_speaker_id)
  return speaker?.name || ''
}

async function handleGenerate() {
  await store.triggerGenerate(route.params.id)
  await store.fetchChannel(route.params.id)
}

async function handleDeleteEpisode(id) {
  if (confirm('Episode wirklich loeschen?')) {
    await store.removeEpisode(id)
  }
}

async function handleCloneChannel() {
  const cloned = await store.cloneOrgChannel(route.params.id)
  if (cloned) {
    router.push(`/briefing/channels/${cloned.id}/edit`)
  }
}

async function handleLinkSource() {
  const select = document.getElementById('link-source-select')
  const sourceId = parseInt(select.value)
  if (!sourceId) return
  await store.linkSourceToChannel(route.params.id, sourceId)
  select.value = ''
}

async function handleUnlinkSource(sourceId) {
  if (confirm('Quelle wirklich vom Channel entfernen?')) {
    await store.unlinkSourceFromChannel(route.params.id, sourceId)
  }
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

function formatDuration(seconds) {
  if (!seconds) return '-'
  const min = Math.floor(seconds / 60)
  const sec = seconds % 60
  return `${min}:${sec.toString().padStart(2, '0')}`
}

function feedUrl() {
  if (!store.currentChannel) return ''
  const base = window.location.origin
  return `${base}/api/v1/briefing/feed/${store.currentChannel.tenant_id}/${store.currentChannel.slug}/feed.xml`
}
</script>

<template>
  <div>
    <PageHeader
      :title="store.currentChannel?.name || 'Channel'"
      :subtitle="store.currentChannel?.target_audience || ''"
    >
      <template #actions>
        <button
          class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white transition hover:bg-go4-primary/90 disabled:opacity-50"
          :disabled="store.generating"
          @click="handleGenerate"
        >
          {{ store.generating ? 'Generiert...' : 'Episode generieren' }}
        </button>
        <template v-if="canEdit()">
          <router-link
            :to="`/briefing/channels/${route.params.id}/edit`"
            class="rounded-lg border border-go4-primary px-4 py-2 text-sm font-medium text-go4-primary transition hover:bg-go4-primary/5"
          >
            Bearbeiten
          </router-link>
        </template>
        <button
          v-else-if="isOrgChannel()"
          class="rounded-lg border border-sky-500 px-4 py-2 text-sm font-medium text-sky-600 transition hover:bg-sky-50 dark:text-sky-400 dark:hover:bg-sky-900/20"
          @click="handleCloneChannel"
        >
          Anpassen
        </button>
      </template>
    </PageHeader>

    <!-- Error -->
    <div
      v-if="store.error"
      class="mt-4 rounded-lg bg-red-50 dark:bg-red-900/20 p-4 text-sm text-red-700 dark:text-red-400"
    >
      {{ store.error }}
    </div>

    <!-- Channel Info -->
    <div v-if="store.currentChannel" class="mt-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
      <div class="rounded-lg bg-white dark:bg-gray-800 p-4 shadow-sm">
        <p class="text-xs font-medium uppercase text-go4-muted dark:text-gray-400">Episoden</p>
        <p class="mt-1 text-2xl font-semibold text-go4-secondary dark:text-gray-100">
          {{ store.currentChannel.episode_count || 0 }}
        </p>
      </div>
      <div class="rounded-lg bg-white dark:bg-gray-800 p-4 shadow-sm">
        <p class="text-xs font-medium uppercase text-go4-muted dark:text-gray-400">Typ</p>
        <p class="mt-1 text-sm font-medium text-go4-secondary dark:text-gray-100">
          {{ store.currentChannel.user_id === null ? 'Organisation' : 'Persoenlich' }}
        </p>
      </div>
      <div class="rounded-lg bg-white dark:bg-gray-800 p-4 shadow-sm">
        <p class="text-xs font-medium uppercase text-go4-muted dark:text-gray-400">Stimme</p>
        <p class="mt-1 text-sm font-medium text-go4-secondary dark:text-gray-100">
          <template v-if="store.currentChannel.tts_engine === 'xtts'">
            XTTS v2
            <span v-if="speakerName()" class="text-go4-muted dark:text-gray-400">
              ({{ speakerName() }})
            </span>
          </template>
          <template v-else-if="store.currentChannel.tts_engine === 'disabled'">
            Deaktiviert
          </template>
          <template v-else>
            {{ store.currentChannel.voice }}
          </template>
        </p>
      </div>
      <div class="rounded-lg bg-white dark:bg-gray-800 p-4 shadow-sm">
        <p class="text-xs font-medium uppercase text-go4-muted dark:text-gray-400">Schedule</p>
        <p class="mt-1 text-sm font-medium text-go4-secondary dark:text-gray-100">
          {{ store.currentChannel.schedule || 'Manuell' }}
        </p>
      </div>
    </div>

    <!-- RSS Feed URL -->
    <div v-if="store.currentChannel" class="mt-4 rounded-lg bg-sky-50 dark:bg-sky-900/20 p-3">
      <p class="text-xs font-medium text-sky-700 dark:text-sky-400">Podcast RSS-Feed:</p>
      <code class="mt-1 block break-all text-xs text-sky-900 dark:text-sky-300">{{
        feedUrl()
      }}</code>
    </div>

    <!-- Tabs -->
    <div class="mt-6 border-b border-gray-200 dark:border-gray-700">
      <nav class="-mb-px flex space-x-8">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          class="border-b-2 px-1 pb-3 text-sm font-medium transition"
          :class="
            activeTab === tab.key
              ? 'border-go4-primary text-go4-primary'
              : 'border-transparent text-go4-muted dark:text-gray-400 hover:border-gray-300 dark:hover:border-gray-600 hover:text-go4-secondary dark:hover:text-gray-100'
          "
          @click="activeTab = tab.key"
        >
          {{ tab.label }}
          <span
            v-if="tab.key === 'episodes'"
            class="ml-1.5 rounded-full bg-go4-primary/10 px-2 py-0.5 text-xs text-go4-primary"
          >
            {{ store.episodes.length }}
          </span>
          <span
            v-if="tab.key === 'sources'"
            class="ml-1.5 rounded-full bg-gray-100 dark:bg-gray-700 px-2 py-0.5 text-xs text-gray-600 dark:text-gray-300"
          >
            {{ store.channelSources.length }}
          </span>
        </button>
      </nav>
    </div>

    <!-- Loading -->
    <div v-if="store.loading" class="mt-8 flex items-center justify-center py-12">
      <span class="text-go4-muted dark:text-gray-400">Laden...</span>
    </div>

    <!-- Episodes Tab -->
    <div v-else-if="activeTab === 'episodes'" class="mt-6">
      <EmptyState
        v-if="store.episodes.length === 0"
        title="Noch keine Episoden"
        description="Generieren Sie die erste Episode fuer diesen Channel."
      />
      <div v-else class="overflow-hidden rounded-lg bg-white dark:bg-gray-800 shadow-sm">
        <table class="w-full text-left text-sm">
          <thead
            class="border-b border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 text-xs uppercase tracking-wider text-go4-muted dark:text-gray-400"
          >
            <tr>
              <th class="px-4 py-3 font-medium">#</th>
              <th class="px-4 py-3 font-medium">Titel</th>
              <th class="hidden px-4 py-3 font-medium md:table-cell">Dauer</th>
              <th class="px-4 py-3 font-medium">Status</th>
              <th class="hidden px-4 py-3 font-medium lg:table-cell">Erstellt</th>
              <th class="px-4 py-3 text-right font-medium">Aktionen</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50 dark:divide-gray-700">
            <tr
              v-for="ep in store.episodes"
              :key="ep.id"
              class="transition hover:bg-gray-50/50 dark:hover:bg-gray-700/50"
            >
              <td class="px-4 py-3 text-go4-muted dark:text-gray-400">
                {{ ep.episode_number }}
              </td>
              <td class="px-4 py-3">
                <p class="font-medium text-go4-secondary dark:text-gray-100">
                  {{ ep.title }}
                </p>
                <p
                  v-if="ep.summary"
                  class="mt-0.5 line-clamp-1 text-xs text-go4-muted dark:text-gray-400"
                >
                  {{ ep.summary }}
                </p>
              </td>
              <td class="hidden px-4 py-3 text-xs text-go4-muted dark:text-gray-400 md:table-cell">
                {{ formatDuration(ep.audio_duration_seconds) }}
              </td>
              <td class="px-4 py-3">
                <StatusBadge :status="ep.status" />
              </td>
              <td class="hidden px-4 py-3 text-xs text-gray-400 dark:text-gray-500 lg:table-cell">
                {{ formatDate(ep.created_at) }}
              </td>
              <td class="px-4 py-3">
                <div class="flex items-center justify-end gap-1.5">
                  <a
                    v-if="ep.audio_url"
                    :href="`/uploads/${ep.audio_url}`"
                    target="_blank"
                    class="rounded bg-sky-100 dark:bg-sky-900/30 px-2.5 py-1 text-xs font-medium text-sky-700 dark:text-sky-400 hover:bg-sky-200 dark:hover:bg-sky-800/40"
                  >
                    Audio
                  </a>
                  <button
                    class="rounded bg-red-100 dark:bg-red-900/30 px-2.5 py-1 text-xs font-medium text-red-700 dark:text-red-400 hover:bg-red-200 dark:hover:bg-red-800/40"
                    @click="handleDeleteEpisode(ep.id)"
                  >
                    Loeschen
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Sources Tab -->
    <div v-else-if="activeTab === 'sources'" class="mt-6">
      <!-- Link Source -->
      <div v-if="canEdit()" class="mb-4 flex items-center gap-3">
        <select
          id="link-source-select"
          class="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-800 dark:text-gray-200"
        >
          <option value="">Quelle auswaehlen...</option>
          <option
            v-for="s in store.sources.filter(
              (s) => !store.channelSources.find((cs) => cs.id === s.id)
            )"
            :key="s.id"
            :value="s.id"
          >
            {{ s.name }} ({{ s.source_type }})
          </option>
        </select>
        <button
          class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white transition hover:bg-go4-primary/90"
          @click="handleLinkSource"
        >
          Verlinken
        </button>
      </div>

      <EmptyState
        v-if="store.channelSources.length === 0"
        title="Keine Quellen verlinkt"
        description="Verlinken Sie Briefing-Quellen mit diesem Channel."
      />
      <div v-else class="overflow-hidden rounded-lg bg-white dark:bg-gray-800 shadow-sm">
        <table class="w-full text-left text-sm">
          <thead
            class="border-b border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 text-xs uppercase tracking-wider text-go4-muted dark:text-gray-400"
          >
            <tr>
              <th class="px-4 py-3 font-medium">Name</th>
              <th class="px-4 py-3 font-medium">Typ</th>
              <th class="hidden px-4 py-3 font-medium md:table-cell">Status</th>
              <th v-if="canEdit()" class="px-4 py-3 text-right font-medium">Aktionen</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50 dark:divide-gray-700">
            <tr
              v-for="source in store.channelSources"
              :key="source.id"
              class="transition hover:bg-gray-50/50 dark:hover:bg-gray-700/50"
            >
              <td class="px-4 py-3 font-medium text-go4-secondary dark:text-gray-100">
                {{ source.name }}
              </td>
              <td class="px-4 py-3 text-xs text-go4-muted dark:text-gray-400">
                {{ source.source_type }}
              </td>
              <td class="hidden px-4 py-3 md:table-cell">
                <span
                  class="rounded-full px-2 py-0.5 text-xs font-medium"
                  :class="
                    source.active
                      ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400'
                  "
                >
                  {{ source.active ? 'Aktiv' : 'Inaktiv' }}
                </span>
              </td>
              <td v-if="canEdit()" class="px-4 py-3">
                <div class="flex items-center justify-end gap-1.5">
                  <button
                    class="rounded bg-red-100 dark:bg-red-900/30 px-2.5 py-1 text-xs font-medium text-red-700 dark:text-red-400 hover:bg-red-200 dark:hover:bg-red-800/40"
                    @click="handleUnlinkSource(source.id)"
                  >
                    Entfernen
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
