<script setup>
defineProps({
  funnel: { type: Object, required: true }
})

defineEmits(['click', 'edit', 'delete'])

function getStatusColor(status) {
  switch (status) {
    case 'active':
      return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
    case 'paused':
      return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
    case 'archived':
      return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
    default:
      return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
  }
}

function getStatusLabel(status) {
  switch (status) {
    case 'active':
      return 'Aktiv'
    case 'paused':
      return 'Pausiert'
    case 'archived':
      return 'Archiviert'
    default:
      return status
  }
}
</script>

<template>
  <div
    class="group relative cursor-pointer rounded-lg bg-white dark:bg-gray-800 p-5 shadow-sm ring-1 ring-gray-200 dark:ring-gray-700 transition-all hover:shadow-md hover:ring-go4-primary"
    @click="$emit('click', funnel)"
  >
    <!-- Color indicator -->
    <div
      v-if="funnel.color"
      class="absolute left-0 top-0 h-full w-1 rounded-l-lg"
      :style="{ backgroundColor: funnel.color }"
    />

    <!-- Header -->
    <div class="flex items-start justify-between">
      <div class="flex-1 min-w-0 pl-2">
        <h3 class="text-lg font-semibold text-go4-secondary dark:text-white truncate">
          {{ funnel.name }}
        </h3>
        <p
          v-if="funnel.description"
          class="mt-1 text-sm text-go4-muted dark:text-gray-400 line-clamp-2"
        >
          {{ funnel.description }}
        </p>
      </div>

      <!-- Status Badge -->
      <span
        class="ml-2 flex-shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium"
        :class="getStatusColor(funnel.status)"
      >
        {{ getStatusLabel(funnel.status) }}
      </span>
    </div>

    <!-- Stats -->
    <div class="mt-4 grid grid-cols-3 gap-4 border-t border-gray-100 dark:border-gray-700 pt-4">
      <div class="text-center">
        <div class="text-2xl font-bold text-go4-secondary dark:text-white">
          {{ funnel.prospect_count || 0 }}
        </div>
        <div class="text-xs text-go4-muted dark:text-gray-400">
          Prospects
        </div>
      </div>
      <div class="text-center">
        <div class="text-2xl font-bold text-go4-secondary dark:text-white">
          {{ funnel.company_count || 0 }}
        </div>
        <div class="text-xs text-go4-muted dark:text-gray-400">
          Firmen
        </div>
      </div>
      <div class="text-center">
        <div class="text-2xl font-bold text-go4-secondary dark:text-white">
          {{ funnel.stage_count || 0 }}
        </div>
        <div class="text-xs text-go4-muted dark:text-gray-400">
          Stages
        </div>
      </div>
    </div>

    <!-- Tags -->
    <div
      v-if="funnel.tags?.length"
      class="mt-3 flex flex-wrap gap-1"
    >
      <span
        v-for="tag in funnel.tags.slice(0, 3)"
        :key="tag"
        class="inline-flex items-center rounded-full bg-gray-100 dark:bg-gray-700 px-2 py-0.5 text-xs text-gray-600 dark:text-gray-300"
      >
        {{ tag }}
      </span>
      <span
        v-if="funnel.tags.length > 3"
        class="text-xs text-go4-muted dark:text-gray-400"
      >
        +{{ funnel.tags.length - 3 }}
      </span>
    </div>

    <!-- Actions (on hover) -->
    <div
      class="absolute right-2 top-2 flex gap-1 opacity-0 transition-opacity group-hover:opacity-100"
    >
      <button
        class="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700"
        title="Bearbeiten"
        @click.stop="$emit('edit', funnel)"
      >
        <svg
          class="h-4 w-4"
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path d="M17.414 2.586a2 2 0 00-2.828 0L7 10.172V13h2.828l7.586-7.586a2 2 0 000-2.828z" />
          <path
            fill-rule="evenodd"
            d="M2 6a2 2 0 012-2h4a1 1 0 010 2H4v10h10v-4a1 1 0 112 0v4a2 2 0 01-2 2H4a2 2 0 01-2-2V6z"
            clip-rule="evenodd"
          />
        </svg>
      </button>
      <button
        class="rounded p-1 text-gray-400 hover:bg-red-100 hover:text-red-600 dark:hover:bg-red-900"
        title="Loeschen"
        @click.stop="$emit('delete', funnel)"
      >
        <svg
          class="h-4 w-4"
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path
            fill-rule="evenodd"
            d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"
            clip-rule="evenodd"
          />
        </svg>
      </button>
    </div>
  </div>
</template>
