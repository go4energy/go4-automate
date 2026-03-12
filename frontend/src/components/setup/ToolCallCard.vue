<script setup>
import { ref } from 'vue'

const props = defineProps({
  toolCall: { type: Object, required: true }
})

const expanded = ref(false)

const toolLabels = {
  get_current_config: 'Konfiguration lesen',
  update_tenant_config: 'Konfiguration aktualisieren',
  list_research_sources: 'Quellen auflisten',
  create_research_source: 'Quelle anlegen',
  delete_research_source: 'Quelle loeschen',
  update_content_config: 'Content-Config aktualisieren',
  update_ads_config: 'Ads-Config aktualisieren',
  check_integration_status: 'Integrationen pruefen',
  list_prompts: 'Prompts auflisten',
  get_setup_progress: 'Fortschritt pruefen'
}

function summarizeInput(input) {
  if (!input) return ''
  if (input.updates) {
    const keys = Object.keys(input.updates)
    return keys.length <= 3 ? keys.join(', ') : `${keys.length} Parameter`
  }
  if (input.name) return input.name
  if (input.source_id) return `ID ${input.source_id}`
  return ''
}
</script>

<template>
  <div
    class="my-2 overflow-hidden rounded-lg border transition"
    :class="{
      'border-blue-200 bg-blue-50': props.toolCall.status === 'executing',
      'border-green-200 bg-green-50': props.toolCall.status === 'success',
      'border-red-200 bg-red-50': props.toolCall.status === 'error'
    }"
  >
    <button
      class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm"
      @click="expanded = !expanded"
    >
      <!-- Status icon -->
      <span
        v-if="props.toolCall.status === 'executing'"
        class="flex h-4 w-4 items-center justify-center"
      >
        <span
          class="h-3 w-3 animate-spin rounded-full border-2 border-blue-400 border-t-transparent"
        />
      </span>
      <svg
        v-else-if="props.toolCall.status === 'success'"
        class="h-4 w-4 text-green-600"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        stroke-width="2"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M5 13l4 4L19 7"
        />
      </svg>
      <svg
        v-else
        class="h-4 w-4 text-red-600"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        stroke-width="2"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M6 18L18 6M6 6l12 12"
        />
      </svg>

      <!-- Tool name -->
      <span class="font-medium text-gray-700">
        {{ toolLabels[props.toolCall.name] || props.toolCall.name }}
      </span>

      <!-- Summary -->
      <span
        v-if="summarizeInput(props.toolCall.input)"
        class="text-gray-500"
      >
        — {{ summarizeInput(props.toolCall.input) }}
      </span>

      <!-- Expand chevron -->
      <svg
        class="ml-auto h-4 w-4 text-gray-400 transition"
        :class="{ 'rotate-180': expanded }"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        stroke-width="2"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M19 9l-7 7-7-7"
        />
      </svg>
    </button>

    <!-- Expanded details -->
    <div
      v-if="expanded"
      class="border-t border-gray-200 px-3 py-2 text-xs"
    >
      <div
        v-if="props.toolCall.input && Object.keys(props.toolCall.input).length"
        class="mb-2"
      >
        <p class="mb-1 font-semibold text-gray-500">
          Input:
        </p>
        <pre class="overflow-auto rounded bg-white p-2 text-gray-600">{{
          JSON.stringify(props.toolCall.input, null, 2)
        }}</pre>
      </div>
      <div v-if="props.toolCall.result">
        <p class="mb-1 font-semibold text-gray-500">
          Ergebnis:
        </p>
        <pre class="overflow-auto rounded bg-white p-2 text-gray-600">{{
          JSON.stringify(props.toolCall.result, null, 2)
        }}</pre>
      </div>
    </div>
  </div>
</template>
