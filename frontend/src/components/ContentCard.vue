<script setup>
import { computed } from 'vue'

const props = defineProps({
  piece: { type: Object, required: true }
})

const emit = defineEmits(['edit', 'approve', 'publish', 'delete'])

const platformLabel = computed(() => {
  const map = { facebook: 'FB', instagram: 'IG', linkedin: 'LI', twitter: 'X' }
  return map[props.piece.platform] || props.piece.platform
})

const platformColor = computed(() => {
  const map = {
    facebook: 'bg-blue-100 text-blue-800',
    instagram: 'bg-pink-100 text-pink-800',
    linkedin: 'bg-sky-100 text-sky-800',
    twitter: 'bg-gray-100 text-gray-800'
  }
  return map[props.piece.platform] || 'bg-gray-100 text-gray-800'
})

const statusColor = computed(() => {
  const map = {
    draft: 'bg-yellow-100 text-yellow-800',
    scheduled: 'bg-blue-100 text-blue-800',
    published: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800'
  }
  return map[props.piece.status] || 'bg-gray-100 text-gray-800'
})

const statusLabel = computed(() => {
  const map = {
    draft: 'Entwurf',
    scheduled: 'Geplant',
    published: 'Veröffentlicht',
    failed: 'Fehlgeschlagen'
  }
  return map[props.piece.status] || props.piece.status
})

const truncatedCaption = computed(() => {
  const caption = props.piece.caption || ''
  if (caption.length <= 150) return caption
  return caption.substring(0, 150) + '...'
})
</script>

<template>
  <div class="rounded-lg bg-white p-5 shadow-sm transition hover:shadow-md">
    <div class="flex items-start justify-between">
      <div class="flex items-center gap-2">
        <span
          class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium"
          :class="platformColor"
        >
          {{ platformLabel }}
        </span>
        <span
          class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium"
          :class="statusColor"
        >
          {{ statusLabel }}
        </span>
      </div>
      <span
        v-if="piece.ai_model"
        class="text-xs text-go4-muted"
      >AI</span>
    </div>

    <h3 class="mt-3 text-sm font-semibold text-go4-secondary line-clamp-2">
      {{ piece.title }}
    </h3>

    <p
      v-if="truncatedCaption"
      class="mt-2 text-xs text-go4-muted line-clamp-3"
    >
      {{ truncatedCaption }}
    </p>

    <div
      v-if="piece.status === 'published'"
      class="mt-3 flex items-center gap-4 text-xs text-go4-muted"
    >
      <span>Reach: {{ piece.reach.toLocaleString() }}</span>
      <span>Engagement: {{ piece.engagement.toLocaleString() }}</span>
      <span v-if="piece.engagement_rate > 0">{{ piece.engagement_rate }}%</span>
    </div>

    <div class="mt-4 flex items-center gap-2">
      <button
        class="rounded bg-go4-surface px-2.5 py-1 text-xs font-medium text-go4-secondary hover:bg-gray-200"
        @click="emit('edit', piece)"
      >
        Bearbeiten
      </button>
      <button
        v-if="piece.status === 'draft'"
        class="rounded bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-700 hover:bg-blue-100"
        @click="emit('approve', piece)"
      >
        Genehmigen
      </button>
      <button
        v-if="piece.status === 'scheduled'"
        class="rounded bg-green-50 px-2.5 py-1 text-xs font-medium text-green-700 hover:bg-green-100"
        @click="emit('publish', piece)"
      >
        Veröffentlichen
      </button>
      <button
        class="rounded bg-red-50 px-2.5 py-1 text-xs font-medium text-red-700 hover:bg-red-100"
        @click="emit('delete', piece)"
      >
        Löschen
      </button>
    </div>
  </div>
</template>
