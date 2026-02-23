<script setup>
import { computed } from 'vue'

const props = defineProps({
  activities: { type: Array, required: true },
  compact: { type: Boolean, default: false },
  maxItems: { type: Number, default: 10 }
})

const moduleIcons = {
  content: {
    icon: '📝',
    color: 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400'
  },
  research: {
    icon: '🔍',
    color: 'bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400'
  },
  ads: {
    icon: '📢',
    color: 'bg-orange-100 text-orange-600 dark:bg-orange-900/30 dark:text-orange-400'
  },
  leads: {
    icon: '👤',
    color: 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400'
  },
  chat: { icon: '💬', color: 'bg-teal-100 text-teal-600 dark:bg-teal-900/30 dark:text-teal-400' },
  system: { icon: '⚙️', color: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400' }
}

const severityColors = {
  info: 'text-gray-600 dark:text-gray-300',
  success: 'text-green-600 dark:text-green-400',
  warning: 'text-amber-600 dark:text-amber-400',
  error: 'text-red-600 dark:text-red-400'
}

function getModule(mod) {
  return moduleIcons[mod] || moduleIcons.system
}

function formatTime(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const now = new Date()
  const diff = now - d
  if (diff < 60000) return 'gerade eben'
  if (diff < 3600000) return `vor ${Math.floor(diff / 60000)} Min.`
  if (diff < 86400000) return `vor ${Math.floor(diff / 3600000)} Std.`
  return d.toLocaleDateString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const displayItems = computed(() => props.activities.slice(0, props.maxItems))
</script>

<template>
  <div class="space-y-0">
    <div
      v-for="activity in displayItems"
      :key="activity.id"
      class="flex items-start gap-3 border-b border-gray-50 py-2.5 last:border-0 dark:border-gray-700/50"
      :class="props.compact ? 'px-0' : 'px-2'"
    >
      <span
        class="mt-0.5 flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full text-xs"
        :class="getModule(activity.module).color"
      >
        {{ getModule(activity.module).icon }}
      </span>
      <div class="min-w-0 flex-1">
        <p
          class="truncate text-sm"
          :class="severityColors[activity.severity] || 'text-gray-600 dark:text-gray-300'"
        >
          {{ activity.title }}
        </p>
        <p
          v-if="!props.compact && activity.detail"
          class="mt-0.5 truncate text-xs text-gray-400 dark:text-gray-500"
        >
          {{ activity.detail }}
        </p>
      </div>
      <span class="flex-shrink-0 text-xs text-gray-400 dark:text-gray-500">
        {{ formatTime(activity.created_at) }}
      </span>
    </div>
    <div
      v-if="displayItems.length === 0"
      class="py-6 text-center text-sm text-gray-400 dark:text-gray-500"
    >
      Keine Aktivitaeten
    </div>
  </div>
</template>
