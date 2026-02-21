<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useBroadcasterStore } from '@/stores/broadcaster'
import PageHeader from '@/components/ui/PageHeader.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import EmptyState from '@/components/ui/EmptyState.vue'

const route = useRoute()
const router = useRouter()
const store = useBroadcasterStore()

const activeTab = ref('episodes')
const tabs = [
  { key: 'episodes', label: 'Episoden' },
  { key: 'users', label: 'Listener' }
]

onMounted(async () => {
  await store.fetchChannel(route.params.id)
  await store.fetchEpisodes(route.params.id)
  await store.fetchUsers()
})

async function handleGenerate() {
  await store.triggerGenerate(route.params.id)
  await store.fetchChannel(route.params.id)
}

async function handleDeleteEpisode(id) {
  if (confirm('Episode wirklich loeschen?')) {
    await store.removeEpisode(id)
  }
}

async function handleDeleteUser(id) {
  if (confirm('Listener wirklich loeschen?')) {
    await store.removeUser(id)
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
  return `${base}/api/v1/broadcaster/feed/${store.currentChannel.tenant_id}/${store.currentChannel.slug}/feed.xml`
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
        <router-link
          :to="`/broadcaster/channels/${route.params.id}/edit`"
          class="rounded-lg border border-go4-primary px-4 py-2 text-sm font-medium text-go4-primary transition hover:bg-go4-primary/5"
        >
          Bearbeiten
        </router-link>
      </template>
    </PageHeader>

    <!-- Error -->
    <div v-if="store.error" class="mt-4 rounded-lg bg-red-50 p-4 text-sm text-red-700">
      {{ store.error }}
    </div>

    <!-- Channel Info -->
    <div v-if="store.currentChannel" class="mt-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
      <div class="rounded-lg bg-white p-4 shadow-sm">
        <p class="text-xs font-medium uppercase text-go4-muted">Episoden</p>
        <p class="mt-1 text-2xl font-semibold text-go4-secondary">
          {{ store.currentChannel.episode_count || 0 }}
        </p>
      </div>
      <div class="rounded-lg bg-white p-4 shadow-sm">
        <p class="text-xs font-medium uppercase text-go4-muted">Abonnenten</p>
        <p class="mt-1 text-2xl font-semibold text-go4-secondary">
          {{ store.currentChannel.subscriber_count || 0 }}
        </p>
      </div>
      <div class="rounded-lg bg-white p-4 shadow-sm">
        <p class="text-xs font-medium uppercase text-go4-muted">Stimme</p>
        <p class="mt-1 text-sm font-medium text-go4-secondary">
          {{ store.currentChannel.voice }}
        </p>
      </div>
      <div class="rounded-lg bg-white p-4 shadow-sm">
        <p class="text-xs font-medium uppercase text-go4-muted">Schedule</p>
        <p class="mt-1 text-sm font-medium text-go4-secondary">
          {{ store.currentChannel.schedule || 'Manuell' }}
        </p>
      </div>
    </div>

    <!-- RSS Feed URL -->
    <div v-if="store.currentChannel" class="mt-4 rounded-lg bg-sky-50 p-3">
      <p class="text-xs font-medium text-sky-700">Podcast RSS-Feed:</p>
      <code class="mt-1 block break-all text-xs text-sky-900">{{ feedUrl() }}</code>
    </div>

    <!-- Tabs -->
    <div class="mt-6 border-b border-gray-200">
      <nav class="-mb-px flex space-x-8">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          class="border-b-2 px-1 pb-3 text-sm font-medium transition"
          :class="
            activeTab === tab.key
              ? 'border-go4-primary text-go4-primary'
              : 'border-transparent text-go4-muted hover:border-gray-300 hover:text-go4-secondary'
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
            v-if="tab.key === 'users'"
            class="ml-1.5 rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600"
          >
            {{ store.users.length }}
          </span>
        </button>
      </nav>
    </div>

    <!-- Loading -->
    <div v-if="store.loading" class="mt-8 flex items-center justify-center py-12">
      <span class="text-go4-muted">Laden...</span>
    </div>

    <!-- Episodes Tab -->
    <div v-else-if="activeTab === 'episodes'" class="mt-6">
      <EmptyState
        v-if="store.episodes.length === 0"
        title="Noch keine Episoden"
        description="Generieren Sie die erste Episode fuer diesen Channel."
      />
      <div v-else class="overflow-hidden rounded-lg bg-white shadow-sm">
        <table class="w-full text-left text-sm">
          <thead
            class="border-b border-gray-100 bg-gray-50 text-xs uppercase tracking-wider text-go4-muted"
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
          <tbody class="divide-y divide-gray-50">
            <tr v-for="ep in store.episodes" :key="ep.id" class="transition hover:bg-gray-50/50">
              <td class="px-4 py-3 text-go4-muted">
                {{ ep.episode_number }}
              </td>
              <td class="px-4 py-3">
                <p class="font-medium text-go4-secondary">
                  {{ ep.title }}
                </p>
                <p v-if="ep.summary" class="mt-0.5 line-clamp-1 text-xs text-go4-muted">
                  {{ ep.summary }}
                </p>
              </td>
              <td class="hidden px-4 py-3 text-xs text-go4-muted md:table-cell">
                {{ formatDuration(ep.audio_duration_seconds) }}
              </td>
              <td class="px-4 py-3">
                <StatusBadge :status="ep.status" />
              </td>
              <td class="hidden px-4 py-3 text-xs text-gray-400 lg:table-cell">
                {{ formatDate(ep.created_at) }}
              </td>
              <td class="px-4 py-3">
                <div class="flex items-center justify-end gap-1.5">
                  <a
                    v-if="ep.audio_url"
                    :href="`/uploads/${ep.audio_url}`"
                    target="_blank"
                    class="rounded bg-sky-100 px-2.5 py-1 text-xs font-medium text-sky-700 hover:bg-sky-200"
                  >
                    Audio
                  </a>
                  <button
                    class="rounded bg-red-100 px-2.5 py-1 text-xs font-medium text-red-700 hover:bg-red-200"
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

    <!-- Users Tab -->
    <div v-else-if="activeTab === 'users'" class="mt-6">
      <EmptyState
        v-if="store.users.length === 0"
        title="Noch keine Listener"
        description="Listener registrieren sich ueber die PWA oder werden hier angelegt."
      />
      <div v-else class="overflow-hidden rounded-lg bg-white shadow-sm">
        <table class="w-full text-left text-sm">
          <thead
            class="border-b border-gray-100 bg-gray-50 text-xs uppercase tracking-wider text-go4-muted"
          >
            <tr>
              <th class="px-4 py-3 font-medium">E-Mail</th>
              <th class="hidden px-4 py-3 font-medium md:table-cell">Name</th>
              <th class="hidden px-4 py-3 font-medium md:table-cell">Rolle</th>
              <th class="px-4 py-3 font-medium">Abos</th>
              <th class="hidden px-4 py-3 font-medium lg:table-cell">Letzter Login</th>
              <th class="px-4 py-3 text-right font-medium">Aktionen</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50">
            <tr v-for="user in store.users" :key="user.id" class="transition hover:bg-gray-50/50">
              <td class="px-4 py-3 font-medium text-go4-secondary">
                {{ user.email }}
              </td>
              <td class="hidden px-4 py-3 text-go4-muted md:table-cell">
                {{ user.display_name || '-' }}
              </td>
              <td class="hidden px-4 py-3 md:table-cell">
                <span
                  v-if="user.role"
                  class="rounded-full bg-purple-100 px-2 py-0.5 text-xs text-purple-700"
                >
                  {{ user.role }}
                </span>
              </td>
              <td class="px-4 py-3 text-xs text-go4-muted">
                {{ user.subscription_count || 0 }}
              </td>
              <td class="hidden px-4 py-3 text-xs text-gray-400 lg:table-cell">
                {{ formatDate(user.last_login_at) }}
              </td>
              <td class="px-4 py-3">
                <div class="flex items-center justify-end gap-1.5">
                  <button
                    class="rounded bg-red-100 px-2.5 py-1 text-xs font-medium text-red-700 hover:bg-red-200"
                    @click="handleDeleteUser(user.id)"
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
  </div>
</template>
