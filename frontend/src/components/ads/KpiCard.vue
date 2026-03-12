<script setup>
const props = defineProps({
  title: { type: String, required: true },
  value: { type: [String, Number], required: true },
  subtitle: { type: String, default: '' },
  trend: { type: String, default: '' },
  icon: { type: String, default: '' }
})
</script>

<template>
  <div class="rounded-lg bg-white p-6 shadow-sm">
    <div class="flex items-center justify-between">
      <h3 class="text-sm font-medium text-go4-muted">
        {{ props.title }}
      </h3>
      <span
        v-if="props.trend === 'improving'"
        class="text-xs font-medium text-green-600"
      >
        &#8593; Besser
      </span>
      <span
        v-else-if="props.trend === 'declining'"
        class="text-xs font-medium text-red-600"
      >
        &#8595; Schlechter
      </span>
      <span
        v-else-if="props.trend === 'stable'"
        class="text-xs font-medium text-gray-500"
      >
        &#8596; Stabil
      </span>
    </div>
    <p class="mt-2 text-3xl font-semibold text-go4-secondary">
      {{ props.value }}
    </p>
    <p
      v-if="props.subtitle"
      class="mt-1 text-xs text-go4-muted"
    >
      {{ props.subtitle }}
    </p>
  </div>
</template>
