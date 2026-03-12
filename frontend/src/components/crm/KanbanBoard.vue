<script setup>
import KanbanColumn from './KanbanColumn.vue'

defineProps({
  stages: { type: Array, required: true }
})

const emit = defineEmits(['deal-click', 'add-deal', 'move-deal'])

function onDealClick(deal) {
  emit('deal-click', deal)
}

function onAddDeal(stage) {
  emit('add-deal', stage)
}

function onDrop({ dealId, stageId }) {
  emit('move-deal', { dealId, stageId })
}
</script>

<template>
  <div class="flex gap-4 overflow-x-auto pb-4">
    <KanbanColumn
      v-for="stage in stages"
      :key="stage.id"
      :stage="stage"
      @deal-click="onDealClick"
      @add-deal="onAddDeal"
      @drop="onDrop"
    />
  </div>
</template>
