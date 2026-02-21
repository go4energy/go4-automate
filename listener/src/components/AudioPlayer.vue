<script setup>
import { usePlayerStore } from '@/stores/player'

const player = usePlayerStore()

function formatTime(seconds) {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}
</script>

<template>
  <div v-if="player.currentEpisode" class="rounded-xl bg-white p-4 shadow-sm">
    <div class="flex items-center gap-3">
      <button
        class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-go4-primary text-white"
        @click="player.togglePlay()"
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
        <div class="mt-1 flex items-center gap-2">
          <div class="h-1 flex-1 overflow-hidden rounded-full bg-gray-200">
            <div
              class="h-full rounded-full bg-go4-primary transition-all"
              :style="{ width: player.progress + '%' }"
            />
          </div>
          <span class="shrink-0 text-xs text-gray-500">{{ formatTime(player.timeLeft) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
