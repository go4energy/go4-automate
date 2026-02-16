<script setup>
import { ref, onMounted } from 'vue'

const loading = ref(true)
const error = ref(null)

onMounted(() => {
  loading.value = false
})
</script>

<template>
  <div class="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
    <h1 class="text-3xl font-bold text-go4-secondary">
      go4-automate Dashboard
    </h1>
    <p class="mt-2 text-go4-muted">
      Marketing Automation Platform
    </p>

    <div v-if="loading" class="mt-8 flex items-center justify-center">
      <span class="text-go4-muted">Laden...</span>
    </div>

    <div v-else-if="error" class="mt-8 rounded-lg bg-red-50 p-4 text-red-700">
      {{ error }}
    </div>

    <div v-else class="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
      <div class="rounded-lg bg-white p-6 shadow-sm">
        <h2 class="text-sm font-medium text-go4-muted">Leads</h2>
        <p class="mt-2 text-3xl font-semibold text-go4-secondary">0</p>
      </div>
      <div class="rounded-lg bg-white p-6 shadow-sm">
        <h2 class="text-sm font-medium text-go4-muted">Campaigns</h2>
        <p class="mt-2 text-3xl font-semibold text-go4-secondary">0</p>
      </div>
      <div class="rounded-lg bg-white p-6 shadow-sm">
        <h2 class="text-sm font-medium text-go4-muted">Workflows</h2>
        <p class="mt-2 text-3xl font-semibold text-go4-secondary">0</p>
      </div>
    </div>
  </div>
</template>
