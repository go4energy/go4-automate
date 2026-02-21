<script setup>
import { onMounted } from 'vue'
import { useChannelsStore } from '@/stores/channels'
import { useAuthStore } from '@/stores/auth'
import { usePlayerStore } from '@/stores/player'
import EpisodeCard from '@/components/EpisodeCard.vue'

const channels = useChannelsStore()
const auth = useAuthStore()
const player = usePlayerStore()

onMounted(async () => {
  await auth.fetchProfile()
  await channels.fetchSubscriptions()
  await channels.fetchFeed()
})
</script>

<template>
  <div class="px-4 pb-4 pt-6">
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-gray-900">
        Hallo{{ auth.user?.display_name ? ', ' + auth.user.display_name : '' }}
      </h1>
      <p class="text-sm text-gray-500">Ihr persoenliches Briefing</p>
    </div>

    <div v-if="channels.loading" class="py-12 text-center text-gray-500">Laden...</div>

    <div v-else-if="channels.error" class="rounded-lg bg-red-50 p-4 text-sm text-red-700">
      {{ channels.error }}
    </div>

    <div v-else-if="channels.feed.length === 0" class="py-12 text-center">
      <div class="mx-auto mb-3 flex h-16 w-16 items-center justify-center rounded-full bg-gray-100">
        <svg class="h-8 w-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
          />
        </svg>
      </div>
      <p class="text-sm font-medium text-gray-900">Noch keine Episoden</p>
      <p class="mt-1 text-sm text-gray-500">Abonnieren Sie Channels, um Briefings zu erhalten.</p>
      <router-link
        :to="{ name: 'channels' }"
        class="mt-4 inline-block rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white"
      >
        Channels entdecken
      </router-link>
    </div>

    <div v-else class="space-y-3">
      <h2 class="text-sm font-semibold uppercase tracking-wide text-gray-500">Neueste Episoden</h2>
      <EpisodeCard
        v-for="episode in channels.feed"
        :key="episode.id"
        :episode="episode"
        @play="player.play(episode)"
      />
    </div>
  </div>
</template>
