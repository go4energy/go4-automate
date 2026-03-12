<script setup>
defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: null }
})
</script>

<template>
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold text-go4-secondary dark:text-gray-100">
        {{ title }}
      </h1>
      <p
        v-if="subtitle"
        class="mt-1 text-sm text-go4-muted dark:text-gray-400"
      >
        {{ subtitle }}
      </p>
    </div>
    <div class="flex items-center gap-3">
      <slot name="actions" />
    </div>
  </div>
</template>
