<script setup>
defineProps({
  episode: { type: Object, required: true }
})

const emit = defineEmits(['play'])

function formatDuration(seconds) {
  if (!seconds) return ''
  const m = Math.floor(seconds / 60)
  return `${m} Min.`
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric'
  })
}
</script>

<template>
  <div class="rounded-xl bg-white p-4 shadow-sm">
    <div class="flex items-start gap-3">
      <button
        class="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-go4-primary/10 text-go4-primary transition-colors hover:bg-go4-primary hover:text-white"
        :disabled="!episode.audio_url"
        @click.stop="emit('play')"
      >
        <svg class="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
          <path d="M8 5v14l11-7z" />
        </svg>
      </button>
      <div class="min-w-0 flex-1">
        <h3 class="text-sm font-semibold text-gray-900">{{ episode.title }}</h3>
        <p v-if="episode.summary" class="mt-0.5 line-clamp-2 text-xs text-gray-500">
          {{ episode.summary }}
        </p>
        <div class="mt-2 flex items-center gap-3 text-xs text-gray-400">
          <span v-if="episode.published_at || episode.generated_at">
            {{ formatDate(episode.published_at || episode.generated_at) }}
          </span>
          <span v-if="episode.audio_duration_seconds">
            {{ formatDuration(episode.audio_duration_seconds) }}
          </span>
          <span
            v-if="episode.status === 'generating'"
            class="rounded-full bg-yellow-100 px-2 py-0.5 text-yellow-700"
          >
            Wird generiert...
          </span>
        </div>
      </div>
    </div>
  </div>
</template>
