<script setup>
defineProps({
  title: { type: String, required: true },
  description: { type: String, default: null }
})
</script>

<template>
  <div class="rounded-lg bg-white p-12 text-center shadow-sm">
    <svg
      class="mx-auto h-12 w-12 text-gray-300"
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
    <h3 class="mt-4 text-sm font-medium text-go4-secondary">
      {{ title }}
    </h3>
    <p v-if="description" class="mt-1 text-sm text-go4-muted">
      {{ description }}
    </p>
    <div class="mt-4">
      <slot name="action" />
    </div>
  </div>
</template>
