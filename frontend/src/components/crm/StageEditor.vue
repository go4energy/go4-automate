<script setup>
import { ref } from 'vue'
import { useCrmStore } from '@/stores/crm'

const props = defineProps({
  pipeline: { type: Object, required: true }
})

const store = useCrmStore()

const showForm = ref(false)
const editingStage = ref(null)
const stageForm = ref({
  name: '',
  color: '#6B7280',
  probability: 0,
  is_won: false,
  is_lost: false
})

const colorOptions = [
  '#6B7280', // Gray
  '#3B82F6', // Blue
  '#8B5CF6', // Purple
  '#EC4899', // Pink
  '#EF4444', // Red
  '#F59E0B', // Amber
  '#10B981', // Green
  '#14B8A6', // Teal
  '#06B6D4', // Cyan
  '#6366F1' // Indigo
]

function openAddForm() {
  editingStage.value = null
  stageForm.value = {
    name: '',
    color: '#6B7280',
    probability: 0,
    is_won: false,
    is_lost: false
  }
  showForm.value = true
}

function openEditForm(stage) {
  editingStage.value = stage
  stageForm.value = {
    name: stage.name,
    color: stage.color,
    probability: stage.probability,
    is_won: stage.is_won,
    is_lost: stage.is_lost
  }
  showForm.value = true
}

function closeForm() {
  showForm.value = false
  editingStage.value = null
}

async function saveStage() {
  if (!stageForm.value.name.trim()) return

  try {
    if (editingStage.value) {
      await store.editStage(editingStage.value.id, stageForm.value)
    } else {
      await store.addPipelineStage(props.pipeline.id, {
        ...stageForm.value,
        position: props.pipeline.stages?.length || 0
      })
    }
    closeForm()
    await store.fetchPipeline(props.pipeline.id)
  } catch {
    // Error handled in store
  }
}

async function deleteStage(stage) {
  if (!confirm(`Stage "${stage.name}" wirklich löschen?`)) return

  try {
    await store.removeStage(stage.id)
    await store.fetchPipeline(props.pipeline.id)
  } catch {
    // Error handled in store
  }
}

function handleWonLostChange(field) {
  if (field === 'is_won' && stageForm.value.is_won) {
    stageForm.value.is_lost = false
    stageForm.value.probability = 100
  } else if (field === 'is_lost' && stageForm.value.is_lost) {
    stageForm.value.is_won = false
    stageForm.value.probability = 0
  }
}
</script>

<template>
  <div>
    <!-- Header -->
    <div class="flex items-center justify-between mb-4">
      <h4 class="font-medium text-gray-900 dark:text-gray-100">
        Stages
      </h4>
      <button
        type="button"
        class="rounded-lg bg-go4-primary px-3 py-1.5 text-sm font-medium text-white hover:bg-go4-primary-dark"
        @click="openAddForm"
      >
        + Stage
      </button>
    </div>

    <!-- Add/Edit Form -->
    <div
      v-if="showForm"
      class="mb-4 rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 p-4"
    >
      <div class="space-y-3">
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">Name *</label>
            <input
              v-model="stageForm.name"
              type="text"
              placeholder="z.B. Qualified"
              class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
            >
          </div>
          <div>
            <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">Wahrscheinlichkeit %</label>
            <input
              v-model.number="stageForm.probability"
              type="number"
              min="0"
              max="100"
              class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
            >
          </div>
        </div>

        <div>
          <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">Farbe</label>
          <div class="flex gap-2">
            <button
              v-for="color in colorOptions"
              :key="color"
              type="button"
              class="h-6 w-6 rounded-full border-2 transition-all"
              :class="
                stageForm.color === color
                  ? 'border-gray-900 dark:border-white scale-110'
                  : 'border-transparent hover:scale-105'
              "
              :style="{ backgroundColor: color }"
              @click="stageForm.color = color"
            />
          </div>
        </div>

        <div class="flex gap-4">
          <label class="flex items-center gap-2">
            <input
              v-model="stageForm.is_won"
              type="checkbox"
              class="h-4 w-4 rounded border-gray-300 text-go4-primary focus:ring-go4-primary"
              @change="handleWonLostChange('is_won')"
            >
            <span class="text-sm text-gray-700 dark:text-gray-300">Gewonnen-Stage</span>
          </label>
          <label class="flex items-center gap-2">
            <input
              v-model="stageForm.is_lost"
              type="checkbox"
              class="h-4 w-4 rounded border-gray-300 text-go4-primary focus:ring-go4-primary"
              @change="handleWonLostChange('is_lost')"
            >
            <span class="text-sm text-gray-700 dark:text-gray-300">Verloren-Stage</span>
          </label>
        </div>

        <div class="flex justify-end gap-2 pt-2">
          <button
            type="button"
            class="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-600"
            @click="closeForm"
          >
            Abbrechen
          </button>
          <button
            type="button"
            class="rounded-lg bg-go4-primary px-3 py-1.5 text-sm font-medium text-white hover:bg-go4-primary-dark"
            @click="saveStage"
          >
            Speichern
          </button>
        </div>
      </div>
    </div>

    <!-- Stages List -->
    <div
      v-if="pipeline.stages?.length === 0"
      class="text-center py-6 text-sm text-gray-500 dark:text-gray-400"
    >
      Keine Stages vorhanden. Fügen Sie Ihre erste Stage hinzu.
    </div>

    <div
      v-else
      class="space-y-2"
    >
      <div
        v-for="(stage, index) in pipeline.stages"
        :key="stage.id"
        class="flex items-center gap-3 rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 px-4 py-3"
      >
        <!-- Position indicator -->
        <span
          class="flex-shrink-0 w-6 h-6 flex items-center justify-center rounded-full bg-gray-100 dark:bg-gray-700 text-xs font-medium text-gray-600 dark:text-gray-300"
        >
          {{ index + 1 }}
        </span>

        <!-- Color & Name -->
        <div class="flex items-center gap-2 flex-1 min-w-0">
          <span
            class="h-3 w-3 rounded-full flex-shrink-0"
            :style="{ backgroundColor: stage.color }"
          />
          <span class="font-medium text-gray-900 dark:text-gray-100 truncate">
            {{ stage.name }}
          </span>
          <span
            v-if="stage.is_won"
            class="flex-shrink-0 rounded-full bg-green-100 dark:bg-green-900/30 px-2 py-0.5 text-xs text-green-700 dark:text-green-300"
          >
            Gewonnen
          </span>
          <span
            v-if="stage.is_lost"
            class="flex-shrink-0 rounded-full bg-red-100 dark:bg-red-900/30 px-2 py-0.5 text-xs text-red-700 dark:text-red-300"
          >
            Verloren
          </span>
        </div>

        <!-- Probability -->
        <span class="flex-shrink-0 text-sm text-gray-500 dark:text-gray-400">
          {{ stage.probability }}%
        </span>

        <!-- Deal Count -->
        <span class="flex-shrink-0 text-sm text-gray-400 dark:text-gray-500">
          {{ stage.deal_count || 0 }} Deals
        </span>

        <!-- Actions -->
        <div class="flex items-center gap-1">
          <button
            type="button"
            class="rounded p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-600"
            @click="openEditForm(stage)"
          >
            <svg
              class="h-4 w-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"
              />
            </svg>
          </button>
          <button
            type="button"
            class="rounded p-1 text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20"
            @click="deleteStage(stage)"
          >
            <svg
              class="h-4 w-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
              />
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
