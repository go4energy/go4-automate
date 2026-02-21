<script setup>
import { onMounted } from 'vue'
import { useChannelsStore } from '@/stores/channels'
import { usePlayerStore } from '@/stores/player'
import EpisodeCard from '@/components/EpisodeCard.vue'

const props = defineProps({
  id: { type: [String, Number], required: true }
})

const channels = useChannelsStore()
const player = usePlayerStore()

onMounted(async () => {
  await channels.fetchChannel(props.id)
  await channels.fetchSubscriptions()
})

const isSubscribed = () => channels.subscribedIds.includes(Number(props.id))

async function toggleSubscription() {
  if (isSubscribed()) {
    await channels.unsubscribe(Number(props.id))
  } else {
    await channels.subscribe(Number(props.id))
  }
}
</script>

<template>
  <div class="px-4 pb-4 pt-6">
    <div v-if="channels.loading" class="py-12 text-center text-gray-500">Laden...</div>

    <div v-else-if="channels.error" class="rounded-lg bg-red-50 p-4 text-sm text-red-700">
      {{ channels.error }}
    </div>

    <div v-else-if="channels.currentChannel">
      <div class="mb-6">
        <router-link
          :to="{ name: 'channels' }"
          class="mb-3 inline-flex items-center gap-1 text-sm text-gray-500"
        >
          <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M15 19l-7-7 7-7"
            />
          </svg>
          Zurueck
        </router-link>

        <h1 class="text-2xl font-bold text-gray-900">{{ channels.currentChannel.name }}</h1>
        <p v-if="channels.currentChannel.description" class="mt-1 text-sm text-gray-600">
          {{ channels.currentChannel.description }}
        </p>

        <div class="mt-3 flex flex-wrap gap-2">
          <span
            v-for="cat in channels.currentChannel.categories || []"
            :key="cat"
            class="rounded-full bg-go4-primary/10 px-2.5 py-0.5 text-xs font-medium text-go4-primary"
          >
            {{ cat }}
          </span>
        </div>

        <div class="mt-4 flex items-center gap-3">
          <button
            class="rounded-lg px-4 py-2 text-sm font-medium transition-colors"
            :class="
              isSubscribed()
                ? 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                : 'bg-go4-primary text-white hover:bg-go4-primary-dark'
            "
            @click="toggleSubscription"
          >
            {{ isSubscribed() ? 'Abonniert' : 'Abonnieren' }}
          </button>
          <span class="text-sm text-gray-500">
            {{ channels.currentChannel.schedule || 'Kein Zeitplan' }}
          </span>
        </div>
      </div>

      <div v-if="channels.currentChannel.episodes?.length > 0" class="space-y-3">
        <h2 class="text-sm font-semibold uppercase tracking-wide text-gray-500">Episoden</h2>
        <EpisodeCard
          v-for="episode in channels.currentChannel.episodes"
          :key="episode.id"
          :episode="episode"
          @play="player.play(episode)"
        />
      </div>
      <div v-else class="py-8 text-center text-sm text-gray-500">
        Noch keine Episoden in diesem Channel.
      </div>
    </div>
  </div>
</template>
