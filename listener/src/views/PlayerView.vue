<script setup>
import { usePlayerStore } from '@/stores/player'
import FeedbackButtons from '@/components/FeedbackButtons.vue'

const player = usePlayerStore()

const rates = [0.75, 1, 1.25, 1.5, 2]

function formatTime(seconds) {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

function seekFromClick(event) {
  const bar = event.currentTarget
  const rect = bar.getBoundingClientRect()
  const ratio = (event.clientX - rect.left) / rect.width
  player.seek(ratio * player.duration)
}
</script>

<template>
  <div class="flex min-h-screen flex-col px-4 pb-4 pt-6">
    <div
      v-if="!player.currentEpisode"
      class="flex flex-1 flex-col items-center justify-center py-12"
    >
      <div class="mb-3 flex h-20 w-20 items-center justify-center rounded-full bg-gray-100">
        <svg class="h-10 w-10 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
      </div>
      <p class="text-sm font-medium text-gray-900">Kein Briefing gestartet</p>
      <p class="mt-1 text-sm text-gray-500">Waehlen Sie eine Episode auf der Startseite.</p>
    </div>

    <div v-else class="flex flex-1 flex-col">
      <div class="mb-8 mt-8 text-center">
        <div
          class="mx-auto mb-4 flex h-32 w-32 items-center justify-center rounded-2xl bg-gradient-to-br from-go4-primary to-go4-primary-dark shadow-lg"
        >
          <svg class="h-16 w-16 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="1.5"
              d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
            />
          </svg>
        </div>
        <h1 class="text-lg font-bold text-gray-900">{{ player.currentEpisode.title }}</h1>
        <p v-if="player.currentEpisode.summary" class="mt-2 text-sm text-gray-500">
          {{ player.currentEpisode.summary }}
        </p>
      </div>

      <div class="mb-2">
        <div
          class="h-2 cursor-pointer overflow-hidden rounded-full bg-gray-200"
          @click="seekFromClick"
        >
          <div
            class="h-full rounded-full bg-go4-primary transition-all"
            :style="{ width: player.progress + '%' }"
          />
        </div>
        <div class="mt-1 flex justify-between text-xs text-gray-500">
          <span>{{ formatTime(player.currentTime) }}</span>
          <span>-{{ formatTime(player.timeLeft) }}</span>
        </div>
      </div>

      <div class="mb-6 flex items-center justify-center gap-6">
        <button class="p-2 text-gray-600" @click="player.skip(-15)">
          <svg class="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M12.066 11.2a1 1 0 000 1.6l5.334 4A1 1 0 0019 16V8a1 1 0 00-1.6-.8l-5.333 4zM4.066 11.2a1 1 0 000 1.6l5.334 4A1 1 0 0011 16V8a1 1 0 00-1.6-.8l-5.334 4z"
            />
          </svg>
        </button>

        <button
          class="flex h-16 w-16 items-center justify-center rounded-full bg-go4-primary text-white shadow-lg"
          @click="player.togglePlay()"
        >
          <svg v-if="player.playing" class="h-8 w-8" fill="currentColor" viewBox="0 0 24 24">
            <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
          </svg>
          <svg v-else class="ml-1 h-8 w-8" fill="currentColor" viewBox="0 0 24 24">
            <path d="M8 5v14l11-7z" />
          </svg>
        </button>

        <button class="p-2 text-gray-600" @click="player.skip(30)">
          <svg class="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M11.933 12.8a1 1 0 000-1.6L6.6 7.2A1 1 0 005 8v8a1 1 0 001.6.8l5.333-4zM19.933 12.8a1 1 0 000-1.6l-5.333-4A1 1 0 0013 8v8a1 1 0 001.6.8l5.333-4z"
            />
          </svg>
        </button>
      </div>

      <div class="mb-8 flex items-center justify-center gap-2">
        <button
          v-for="rate in rates"
          :key="rate"
          class="rounded-full px-3 py-1 text-sm font-medium transition-colors"
          :class="
            player.playbackRate === rate
              ? 'bg-go4-primary text-white'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          "
          @click="player.setRate(rate)"
        >
          {{ rate }}x
        </button>
      </div>

      <div class="mt-auto">
        <FeedbackButtons :episode-id="player.currentEpisode.id" />
      </div>
    </div>
  </div>
</template>
