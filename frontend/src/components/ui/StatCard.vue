<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], required: true },
  trend: { type: String, default: null },
  color: { type: String, default: 'text-go4-secondary dark:text-gray-100' }
})
</script>

<template>
  <div class="rounded-lg bg-white p-4 shadow-sm dark:bg-gray-800">
    <p class="text-xs font-medium text-go4-muted dark:text-gray-400">
      {{ label }}
    </p>
    <p :class="['mt-1 text-2xl font-semibold', color]">
      {{ value }}
    </p>
    <p
      v-if="trend"
      class="mt-1 text-xs"
      :class="
        trend.startsWith('+')
          ? 'text-green-600 dark:text-green-400'
          : trend.startsWith('-')
            ? 'text-red-600 dark:text-red-400'
            : 'text-go4-muted dark:text-gray-400'
      "
    >
      {{ trend }}
    </p>
  </div>
</template>
