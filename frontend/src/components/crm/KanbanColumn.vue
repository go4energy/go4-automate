<script setup>
import { computed } from 'vue'
import KanbanCard from './KanbanCard.vue'

const props = defineProps({
  stage: { type: Object, required: true }
})

const emit = defineEmits(['deal-click', 'add-deal', 'drop'])

const formattedTotal = computed(() => {
  return new Intl.NumberFormat('de-DE', {
    style: 'currency',
    currency: 'EUR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(props.stage.total_value || 0)
})

function onDragOver(event) {
  event.preventDefault()
}

function onDrop(event) {
  event.preventDefault()
  const dealId = event.dataTransfer.getData('dealId')
  if (dealId) {
    emit('drop', { dealId: parseInt(dealId), stageId: props.stage.id })
  }
}

function onDragStart(event, deal) {
  event.dataTransfer.setData('dealId', deal.id.toString())
  event.dataTransfer.effectAllowed = 'move'
}

function onDealClick(deal) {
  emit('deal-click', deal)
}

function onAddDeal() {
  emit('add-deal', props.stage)
}
</script>

<template>
  <div
    class="flex flex-col w-72 flex-shrink-0 rounded-lg bg-gray-50 dark:bg-gray-900/50"
    @dragover="onDragOver"
    @drop="onDrop"
  >
    <!-- Header -->
    <div
      class="flex items-center justify-between px-3 py-2 border-b-2"
      :style="{ borderColor: stage.color }"
    >
      <div>
        <h3 class="font-semibold text-gray-900 dark:text-gray-100 text-sm">
          {{ stage.name }}
        </h3>
        <div class="text-xs text-gray-500 dark:text-gray-400">
          {{ stage.deal_count }} Deals · {{ formattedTotal }}
        </div>
      </div>
      <button
        type="button"
        class="rounded p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700"
        @click="onAddDeal"
      >
        <svg
          class="h-5 w-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M12 4v16m8-8H4"
          />
        </svg>
      </button>
    </div>

    <!-- Cards -->
    <div class="flex-1 overflow-y-auto p-2 space-y-2 min-h-[200px]">
      <KanbanCard
        v-for="deal in stage.deals"
        :key="deal.id"
        :deal="deal"
        @click="onDealClick(deal)"
        @dragstart="onDragStart($event, deal)"
      />

      <!-- Empty state -->
      <div
        v-if="stage.deals.length === 0"
        class="flex items-center justify-center h-20 text-sm text-gray-400 dark:text-gray-500"
      >
        Keine Deals
      </div>
    </div>
  </div>
</template>
