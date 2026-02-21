<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { usePlayerStore } from '@/stores/player'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const player = usePlayerStore()

const showNav = computed(() => route.meta.auth && auth.isLoggedIn)
const showMiniPlayer = computed(() => player.currentEpisode && route.name !== 'player')

function formatTime(seconds) {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}
</script>

<template>
  <div class="flex min-h-screen flex-col bg-gray-50">
    <main class="flex-1" :class="{ 'pb-32': showNav }">
      <router-view />
    </main>

    <!-- Mini Player -->
    <div
      v-if="showMiniPlayer"
      class="fixed bottom-16 left-0 right-0 z-40 border-t border-gray-200 bg-white px-4 py-2 shadow-lg"
      @click="router.push({ name: 'player' })"
    >
      <div class="flex items-center gap-3">
        <button
          class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-go4-primary text-white"
          @click.stop="player.togglePlay()"
        >
          <svg v-if="player.playing" class="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
          </svg>
          <svg v-else class="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M8 5v14l11-7z" />
          </svg>
        </button>
        <div class="min-w-0 flex-1">
          <p class="truncate text-sm font-medium text-gray-900">
            {{ player.currentEpisode.title }}
          </p>
          <p class="text-xs text-gray-500">
            {{ formatTime(player.currentTime) }} /
            {{ formatTime(player.duration) }}
          </p>
        </div>
      </div>
      <div class="mt-1 h-1 overflow-hidden rounded-full bg-gray-200">
        <div
          class="h-full rounded-full bg-go4-primary transition-all"
          :style="{ width: player.progress + '%' }"
        />
      </div>
    </div>

    <!-- Bottom Navigation -->
    <nav
      v-if="showNav"
      class="fixed bottom-0 left-0 right-0 z-50 border-t border-gray-200 bg-white"
    >
      <div class="flex items-center justify-around py-2">
        <router-link
          :to="{ name: 'home' }"
          class="flex flex-col items-center gap-1 px-3 py-1"
          :class="route.name === 'home' ? 'text-go4-primary' : 'text-gray-500'"
        >
          <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-4 0a1 1 0 01-1-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 01-1 1"
            />
          </svg>
          <span class="text-xs">Home</span>
        </router-link>

        <router-link
          :to="{ name: 'channels' }"
          class="flex flex-col items-center gap-1 px-3 py-1"
          :class="
            route.name === 'channels' || route.name === 'channel-detail'
              ? 'text-go4-primary'
              : 'text-gray-500'
          "
        >
          <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
            />
          </svg>
          <span class="text-xs">Channels</span>
        </router-link>

        <router-link
          :to="{ name: 'player' }"
          class="flex flex-col items-center gap-1 px-3 py-1"
          :class="route.name === 'player' ? 'text-go4-primary' : 'text-gray-500'"
        >
          <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
            />
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <span class="text-xs">Player</span>
        </router-link>

        <router-link
          :to="{ name: 'profile' }"
          class="flex flex-col items-center gap-1 px-3 py-1"
          :class="route.name === 'profile' ? 'text-go4-primary' : 'text-gray-500'"
        >
          <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
            />
          </svg>
          <span class="text-xs">Profil</span>
        </router-link>
      </div>
    </nav>
  </div>
</template>
