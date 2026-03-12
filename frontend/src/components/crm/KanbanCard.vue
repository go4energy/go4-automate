<script setup>
import { computed } from 'vue'

const props = defineProps({
  deal: { type: Object, required: true }
})

const emit = defineEmits(['click', 'dragstart'])

const priorityColors = {
  low: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
  medium: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  high: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300'
}

const formattedValue = computed(() => {
  if (!props.deal.value) return null
  return new Intl.NumberFormat('de-DE', {
    style: 'currency',
    currency: props.deal.currency || 'EUR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(props.deal.value)
})

const formattedDate = computed(() => {
  if (!props.deal.expected_close) return null
  return new Date(props.deal.expected_close).toLocaleDateString('de-DE', {
    day: '2-digit',
    month: 'short'
  })
})

function onClick() {
  emit('click', props.deal)
}

function onDragStart(event) {
  event.dataTransfer.setData('dealId', props.deal.id.toString())
  event.dataTransfer.effectAllowed = 'move'
  emit('dragstart', event)
}
</script>

<template>
  <div
    class="cursor-pointer rounded-lg bg-white dark:bg-gray-800 p-3 shadow-sm border border-gray-200 dark:border-gray-700 hover:shadow-md transition-shadow"
    draggable="true"
    @click="onClick"
    @dragstart="onDragStart"
  >
    <h4 class="font-medium text-gray-900 dark:text-gray-100 text-sm leading-tight">
      {{ deal.title }}
    </h4>

    <div
      v-if="deal.company_name || deal.contact_name"
      class="mt-1 text-xs text-gray-500 dark:text-gray-400"
    >
      {{ deal.company_name || deal.contact_name }}
    </div>

    <div class="mt-2 flex items-center justify-between">
      <div
        v-if="formattedValue"
        class="text-sm font-semibold text-gray-900 dark:text-gray-100"
      >
        {{ formattedValue }}
      </div>
      <div
        v-else
        class="text-sm text-gray-400"
      >
        -
      </div>

      <div class="flex items-center gap-2">
        <span
          v-if="deal.priority !== 'medium'"
          class="rounded px-1.5 py-0.5 text-xs font-medium"
          :class="priorityColors[deal.priority]"
        >
          {{ deal.priority === 'high' ? 'Hoch' : 'Niedrig' }}
        </span>
      </div>
    </div>

    <div
      v-if="formattedDate || deal.tags.length > 0"
      class="mt-2 flex items-center justify-between"
    >
      <div
        v-if="deal.tags.length > 0"
        class="flex flex-wrap gap-1"
      >
        <span
          v-for="tag in deal.tags.slice(0, 2)"
          :key="tag"
          class="rounded-full bg-gray-100 dark:bg-gray-700 px-1.5 py-0.5 text-xs text-gray-600 dark:text-gray-400"
        >
          {{ tag }}
        </span>
      </div>
      <div v-else />

      <div
        v-if="formattedDate"
        class="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400"
      >
        <svg
          class="h-3.5 w-3.5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
          />
        </svg>
        {{ formattedDate }}
      </div>
    </div>
  </div>
</template>
