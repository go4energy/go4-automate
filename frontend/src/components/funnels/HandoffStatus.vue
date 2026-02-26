<script setup>
defineProps({
  handoff: { type: Object, required: true }
})

defineEmits(['retry'])

function getStatusColor(status) {
  switch (status) {
    case 'pending':
      return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
    case 'processing':
      return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
    case 'completed':
      return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
    case 'failed':
      return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
    case 'skipped':
      return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
    default:
      return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
  }
}

function getStatusLabel(status) {
  switch (status) {
    case 'pending':
      return 'Ausstehend'
    case 'processing':
      return 'Verarbeitung'
    case 'completed':
      return 'Abgeschlossen'
    case 'failed':
      return 'Fehlgeschlagen'
    case 'skipped':
      return 'Uebersprungen'
    default:
      return status
  }
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleDateString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<template>
  <div
    class="rounded-lg bg-white dark:bg-gray-800 p-4 shadow-sm ring-1 ring-gray-200 dark:ring-gray-700"
  >
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <!-- Status Icon -->
        <div
          class="flex h-10 w-10 items-center justify-center rounded-full"
          :class="{
            'bg-yellow-100': handoff.status === 'pending',
            'bg-blue-100': handoff.status === 'processing',
            'bg-green-100': handoff.status === 'completed',
            'bg-red-100': handoff.status === 'failed',
            'bg-gray-100': handoff.status === 'skipped'
          }"
        >
          <!-- Pending -->
          <svg
            v-if="handoff.status === 'pending'"
            class="h-5 w-5 text-yellow-600"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fill-rule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z"
              clip-rule="evenodd"
            />
          </svg>
          <!-- Processing -->
          <svg
            v-else-if="handoff.status === 'processing'"
            class="h-5 w-5 text-blue-600 animate-spin"
            viewBox="0 0 24 24"
            fill="none"
          >
            <circle
              class="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              stroke-width="4"
            />
            <path
              class="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
          </svg>
          <!-- Completed -->
          <svg
            v-else-if="handoff.status === 'completed'"
            class="h-5 w-5 text-green-600"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fill-rule="evenodd"
              d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
              clip-rule="evenodd"
            />
          </svg>
          <!-- Failed -->
          <svg
            v-else-if="handoff.status === 'failed'"
            class="h-5 w-5 text-red-600"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fill-rule="evenodd"
              d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
              clip-rule="evenodd"
            />
          </svg>
        </div>

        <!-- Info -->
        <div>
          <div class="flex items-center gap-2">
            <span class="font-medium text-go4-secondary dark:text-white">
              {{ handoff.prospect_name || 'Prospect #' + handoff.prospect_id }}
            </span>
            <span
              class="rounded-full px-2 py-0.5 text-xs font-medium"
              :class="getStatusColor(handoff.status)"
            >
              {{ getStatusLabel(handoff.status) }}
            </span>
          </div>
          <p class="text-sm text-go4-muted dark:text-gray-400">
            {{ formatDate(handoff.triggered_at) }} - {{ handoff.triggered_by }}
          </p>
        </div>
      </div>

      <!-- Retry Button (for failed) -->
      <button
        v-if="handoff.status === 'failed'"
        class="flex items-center gap-1 rounded bg-red-100 px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-200 dark:bg-red-900 dark:text-red-200 dark:hover:bg-red-800"
        @click="$emit('retry', handoff)"
      >
        <svg
          class="h-4 w-4"
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path
            fill-rule="evenodd"
            d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z"
            clip-rule="evenodd"
          />
        </svg>
        Wiederholen
      </button>
    </div>

    <!-- Error Message -->
    <div
      v-if="handoff.status === 'failed' && handoff.error_message"
      class="mt-3 rounded bg-red-50 dark:bg-red-900/30 p-3 text-sm text-red-700 dark:text-red-300"
    >
      {{ handoff.error_message }}
    </div>

    <!-- CRM Links (for completed) -->
    <div
      v-if="handoff.status === 'completed'"
      class="mt-3 flex gap-4 text-sm"
    >
      <div v-if="handoff.crm_contact_id">
        <span class="text-go4-muted dark:text-gray-400">CRM Kontakt:</span>
        <router-link
          :to="`/contacts/${handoff.crm_contact_id}`"
          class="ml-1 text-go4-primary hover:underline"
        >
          #{{ handoff.crm_contact_id }}
        </router-link>
      </div>
      <div v-if="handoff.crm_deal_id">
        <span class="text-go4-muted dark:text-gray-400">CRM Deal:</span>
        <router-link
          :to="`/crm/deals/${handoff.crm_deal_id}`"
          class="ml-1 text-go4-primary hover:underline"
        >
          #{{ handoff.crm_deal_id }}
        </router-link>
      </div>
    </div>
  </div>
</template>
