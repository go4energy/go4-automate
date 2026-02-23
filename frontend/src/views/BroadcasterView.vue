<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useBroadcasterStore } from '@/stores/broadcaster'
import PageHeader from '@/components/ui/PageHeader.vue'
import EmptyState from '@/components/ui/EmptyState.vue'

const router = useRouter()
const store = useBroadcasterStore()

onMounted(() => {
  store.fetchChannels()
})

async function handleDelete(id) {
  if (confirm('Channel und alle Episoden wirklich loeschen?')) {
    await store.removeChannel(id)
  }
}

async function handleToggle(channel) {
  await store.editChannel(channel.id, { active: !channel.active })
}
</script>

<template>
  <div>
    <PageHeader title="Broadcaster" subtitle="Audio-Briefings fuer Ihre Zielgruppen">
      <template #actions>
        <router-link
          to="/broadcaster/channels/new"
          class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white transition hover:bg-go4-primary/90"
        >
          Neuer Channel
        </router-link>
      </template>
    </PageHeader>

    <!-- Error -->
    <div
      v-if="store.error"
      class="mt-4 rounded-lg bg-red-50 dark:bg-red-900/20 p-4 text-sm text-red-700 dark:text-red-400"
    >
      {{ store.error }}
    </div>

    <!-- Loading -->
    <div v-if="store.loading" class="mt-8 flex items-center justify-center py-12">
      <span class="text-go4-muted dark:text-gray-400">Laden...</span>
    </div>

    <!-- Empty -->
    <EmptyState
      v-else-if="store.channels.length === 0"
      title="Noch keine Channels"
      description="Erstellen Sie einen Briefing-Channel fuer Ihre erste Zielgruppe."
    />

    <!-- Channel Cards -->
    <div v-else class="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
      <div
        v-for="channel in store.channels"
        :key="channel.id"
        class="rounded-lg bg-white dark:bg-gray-800 p-5 shadow-sm transition hover:shadow-md"
      >
        <div class="flex items-start justify-between">
          <div class="min-w-0 flex-1">
            <router-link
              :to="`/broadcaster/channels/${channel.id}`"
              class="text-base font-semibold text-go4-secondary dark:text-gray-100 hover:text-go4-primary"
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
                ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 hover:bg-green-200 dark:hover:bg-green-800/40'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600'
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

        <!-- Stats -->
        <div class="mt-4 flex items-center gap-4 text-xs text-go4-muted dark:text-gray-400">
          <span>{{ channel.episode_count || 0 }} Episoden</span>
          <span>{{ channel.subscriber_count || 0 }} Abonnenten</span>
          <span v-if="channel.schedule">{{ channel.schedule }}</span>
        </div>

        <!-- Categories -->
        <div v-if="channel.categories?.length" class="mt-3 flex flex-wrap gap-1">
          <span
            v-for="cat in channel.categories.slice(0, 4)"
            :key="cat"
            class="rounded-full bg-sky-100 dark:bg-sky-900/30 px-2 py-0.5 text-xs text-sky-700 dark:text-sky-400"
          >
            {{ cat }}
          </span>
          <span
            v-if="channel.categories.length > 4"
            class="text-xs text-gray-400 dark:text-gray-500"
          >
            +{{ channel.categories.length - 4 }}
          </span>
        </div>

        <!-- Actions -->
        <div
          class="mt-4 flex items-center gap-2 border-t border-gray-100 dark:border-gray-700 pt-3"
        >
          <router-link
            :to="`/broadcaster/channels/${channel.id}`"
            class="rounded bg-go4-primary/10 px-2.5 py-1 text-xs font-medium text-go4-primary hover:bg-go4-primary/20"
          >
            Details
          </router-link>
          <router-link
            :to="`/broadcaster/channels/${channel.id}/edit`"
            class="rounded bg-gray-100 dark:bg-gray-700 px-2.5 py-1 text-xs font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
          >
            Bearbeiten
          </router-link>
          <button
            class="rounded bg-red-100 dark:bg-red-900/30 px-2.5 py-1 text-xs font-medium text-red-700 dark:text-red-400 hover:bg-red-200 dark:hover:bg-red-800/40"
            @click="handleDelete(channel.id)"
          >
            Loeschen
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
