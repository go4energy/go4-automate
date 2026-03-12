<script setup>
defineProps({
  loading: { type: Boolean, default: false },
  emptyTitle: { type: String, default: 'Keine Einträge' },
  emptyDescription: { type: String, default: null },
  columns: {
    type: Number,
    default: 3,
    validator: (v) => [1, 2, 3, 4, 5, 6].includes(v)
  }
})

const gridClasses = {
  1: 'grid-cols-1',
  2: 'grid-cols-1 sm:grid-cols-2',
  3: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3',
  4: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4',
  5: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5',
  6: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6'
}
</script>

<template>
  <div>
    <!-- Loading State -->
    <div
      v-if="loading"
      class="flex items-center justify-center p-12"
    >
      <span class="text-go4-muted dark:text-gray-400">Laden...</span>
    </div>

    <!-- Empty State -->
    <div
      v-else-if="!$slots.default"
      class="rounded-lg bg-white dark:bg-gray-800 p-12 text-center shadow-sm"
    >
      <svg
        class="mx-auto h-12 w-12 text-gray-300 dark:text-gray-600"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5m6 4.125l2.25 2.25m0 0l2.25 2.25M12 13.875l2.25-2.25M12 13.875l-2.25 2.25M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z"
        />
      </svg>
      <h3 class="mt-4 text-sm font-medium text-go4-secondary dark:text-gray-200">
        {{ emptyTitle }}
      </h3>
      <p
        v-if="emptyDescription"
        class="mt-1 text-sm text-go4-muted dark:text-gray-400"
      >
        {{ emptyDescription }}
      </p>
      <div class="mt-4">
        <slot name="empty-action" />
      </div>
    </div>

    <!-- Grid Content -->
    <div
      v-else
      class="grid gap-4"
      :class="gridClasses[columns]"
    >
      <slot />
    </div>
  </div>
</template>
