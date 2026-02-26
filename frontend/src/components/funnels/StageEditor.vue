<script setup>
import { ref } from 'vue'

const props = defineProps({
  stages: { type: Array, default: () => [] }
})

const emit = defineEmits(['add', 'update', 'delete', 'reorder'])

const editingStage = ref(null)
const newStageName = ref('')
const showAddForm = ref(false)

const colors = [
  '#6B7280', // Gray
  '#3B82F6', // Blue
  '#8B5CF6', // Purple
  '#EC4899', // Pink
  '#EF4444', // Red
  '#F59E0B', // Amber
  '#10B981', // Green
  '#14B8A6' // Teal
]

function startEdit(stage) {
  editingStage.value = { ...stage }
}

function saveEdit() {
  if (editingStage.value) {
    emit('update', editingStage.value.id, editingStage.value)
    editingStage.value = null
  }
}

function cancelEdit() {
  editingStage.value = null
}

function addStage() {
  if (newStageName.value.trim()) {
    emit('add', {
      name: newStageName.value.trim(),
      position: props.stages.length,
      color: colors[props.stages.length % colors.length]
    })
    newStageName.value = ''
    showAddForm.value = false
  }
}
</script>

<template>
  <div class="space-y-2">
    <!-- Stage List -->
    <div class="space-y-2">
      <div
        v-for="stage in stages"
        :key="stage.id"
        class="flex items-center gap-3 rounded-lg bg-gray-50 dark:bg-gray-800 p-3"
      >
        <!-- Drag Handle -->
        <div class="cursor-move text-gray-400">
          <svg
            class="h-5 w-5"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fill-rule="evenodd"
              d="M3 5a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 5a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 5a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z"
              clip-rule="evenodd"
            />
          </svg>
        </div>

        <!-- Color Indicator -->
        <div
          class="h-4 w-4 rounded-full flex-shrink-0"
          :style="{ backgroundColor: stage.color }"
        />

        <!-- Stage Info (View Mode) -->
        <template v-if="editingStage?.id !== stage.id">
          <div class="flex-1 min-w-0">
            <span class="font-medium text-go4-secondary dark:text-white">
              {{ stage.name }}
            </span>
            <div class="flex gap-2 mt-0.5">
              <span
                v-if="stage.is_handoff"
                class="text-xs text-green-600"
              > Handoff </span>
              <span
                v-if="stage.is_disqualified"
                class="text-xs text-red-600"
              >
                Disqualifiziert
              </span>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex items-center gap-1">
            <span class="text-xs text-go4-muted dark:text-gray-400 mr-2">
              {{ stage.prospect_count || 0 }} Prospects
            </span>
            <button
              class="rounded p-1 text-gray-400 hover:bg-gray-200 hover:text-gray-600 dark:hover:bg-gray-700"
              @click="startEdit(stage)"
            >
              <svg
                class="h-4 w-4"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  d="M17.414 2.586a2 2 0 00-2.828 0L7 10.172V13h2.828l7.586-7.586a2 2 0 000-2.828z"
                />
              </svg>
            </button>
            <button
              class="rounded p-1 text-gray-400 hover:bg-red-100 hover:text-red-600 dark:hover:bg-red-900"
              :disabled="stage.prospect_count > 0"
              @click="$emit('delete', stage.id)"
            >
              <svg
                class="h-4 w-4"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fill-rule="evenodd"
                  d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                  clip-rule="evenodd"
                />
              </svg>
            </button>
          </div>
        </template>

        <!-- Stage Info (Edit Mode) -->
        <template v-else>
          <div class="flex-1 flex items-center gap-2">
            <input
              v-model="editingStage.name"
              type="text"
              class="flex-1 rounded border border-gray-300 dark:border-gray-600 px-2 py-1 text-sm dark:bg-gray-700 dark:text-white"
              @keyup.enter="saveEdit"
              @keyup.escape="cancelEdit"
            >

            <!-- Color Picker -->
            <div class="flex gap-1">
              <button
                v-for="color in colors"
                :key="color"
                class="h-5 w-5 rounded-full border-2"
                :class="{
                  'border-gray-800 dark:border-white': editingStage.color === color,
                  'border-transparent': editingStage.color !== color
                }"
                :style="{ backgroundColor: color }"
                @click="editingStage.color = color"
              />
            </div>

            <!-- Flags -->
            <label class="flex items-center gap-1 text-xs">
              <input
                v-model="editingStage.is_handoff"
                type="checkbox"
                class="rounded border-gray-300"
              >
              Handoff
            </label>
            <label class="flex items-center gap-1 text-xs">
              <input
                v-model="editingStage.is_disqualified"
                type="checkbox"
                class="rounded border-gray-300"
              >
              Disq.
            </label>
          </div>

          <div class="flex gap-1">
            <button
              class="rounded bg-go4-primary px-2 py-1 text-xs text-white hover:bg-go4-primary-dark"
              @click="saveEdit"
            >
              Speichern
            </button>
            <button
              class="rounded px-2 py-1 text-xs text-gray-600 hover:bg-gray-200 dark:text-gray-300 dark:hover:bg-gray-700"
              @click="cancelEdit"
            >
              Abbrechen
            </button>
          </div>
        </template>
      </div>
    </div>

    <!-- Add Stage Form -->
    <div
      v-if="showAddForm"
      class="flex items-center gap-2 rounded-lg bg-gray-50 dark:bg-gray-800 p-3"
    >
      <input
        v-model="newStageName"
        type="text"
        placeholder="Stage-Name"
        class="flex-1 rounded border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm dark:bg-gray-700 dark:text-white"
        @keyup.enter="addStage"
        @keyup.escape="showAddForm = false"
      >
      <button
        class="rounded bg-go4-primary px-3 py-2 text-sm text-white hover:bg-go4-primary-dark"
        @click="addStage"
      >
        Hinzufuegen
      </button>
      <button
        class="rounded px-3 py-2 text-sm text-gray-600 hover:bg-gray-200 dark:text-gray-300 dark:hover:bg-gray-700"
        @click="showAddForm = false"
      >
        Abbrechen
      </button>
    </div>

    <!-- Add Button -->
    <button
      v-if="!showAddForm"
      class="flex w-full items-center justify-center gap-2 rounded-lg border-2 border-dashed border-gray-300 dark:border-gray-600 py-3 text-sm text-gray-500 hover:border-go4-primary hover:text-go4-primary"
      @click="showAddForm = true"
    >
      <svg
        class="h-4 w-4"
        viewBox="0 0 20 20"
        fill="currentColor"
      >
        <path
          fill-rule="evenodd"
          d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
          clip-rule="evenodd"
        />
      </svg>
      Stage hinzufuegen
    </button>
  </div>
</template>
