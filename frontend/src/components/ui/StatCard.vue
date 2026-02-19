<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], required: true },
  trend: { type: String, default: null },
  color: { type: String, default: 'text-go4-secondary' }
})
</script>

<template>
  <div class="rounded-lg bg-white p-4 shadow-sm">
    <p class="text-xs font-medium text-go4-muted">
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
          ? 'text-green-600'
          : trend.startsWith('-')
            ? 'text-red-600'
            : 'text-go4-muted'
      "
    >
      {{ trend }}
    </p>
  </div>
</template>
