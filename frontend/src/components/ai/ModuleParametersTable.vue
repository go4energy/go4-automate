<script setup>
import { ref, computed, watch } from 'vue'
import draggable from 'vuedraggable'

const props = defineProps({
  parameters: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false }
})

const emit = defineEmits(['update', 'delete', 'add', 'reorder'])

// Local copy for dragging
const localParams = ref([])

// Sync with props
watch(
  () => props.parameters,
  (newParams) => {
    localParams.value = [...newParams]
  },
  { immediate: true, deep: true }
)

// Editing state
const editingVariable = ref(null)
const editValue = ref('')
const editDescription = ref('')

// Add new parameter state
const showAddForm = ref(false)
const newVariable = ref('')
const newDescription = ref('')
const newVarType = ref('string')

// Computed
const hasParams = computed(() => localParams.value.length > 0)

// Edit functions
function startEdit(param) {
  editingVariable.value = param.variable
  editValue.value = param.value || ''
  editDescription.value = param.description || ''
}

function cancelEdit() {
  editingVariable.value = null
  editValue.value = ''
  editDescription.value = ''
}

function saveEdit(param) {
  emit('update', param.variable, {
    value: editValue.value || null,
    description: editDescription.value
  })
  cancelEdit()
}

// Delete
function handleDelete(param) {
  if (confirm(`Parameter "${param.variable}" wirklich löschen?`)) {
    emit('delete', param.variable)
  }
}

// Add new
function openAddForm() {
  showAddForm.value = true
  newVariable.value = ''
  newDescription.value = ''
  newVarType.value = 'string'
}

function cancelAdd() {
  showAddForm.value = false
}

function saveAdd() {
  if (!newVariable.value.trim() || !newDescription.value.trim()) return

  emit('add', {
    variable: newVariable.value.trim(),
    description: newDescription.value.trim(),
    var_type: newVarType.value,
    required: true
  })
  cancelAdd()
}

// Drag end
function onDragEnd() {
  const order = localParams.value.map((p) => p.variable)
  emit('reorder', order)
}

// Type labels
const typeLabels = {
  string: 'Text',
  array: 'Liste',
  boolean: 'Ja/Nein',
  number: 'Zahl'
}
</script>

<template>
  <div class="rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
    <!-- Header -->
    <div class="flex items-center justify-between border-b border-gray-200 px-4 py-3 dark:border-gray-700">
      <h3 class="text-sm font-medium text-go4-secondary dark:text-white">
        Parameter
        <span class="ml-1 text-go4-muted">({{ localParams.length }})</span>
      </h3>
      <button
        class="rounded px-2 py-1 text-xs text-go4-primary hover:bg-go4-primary/10"
        @click="openAddForm"
      >
        + Neu
      </button>
    </div>

    <!-- Table -->
    <div class="overflow-x-auto">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 text-xs uppercase text-go4-muted dark:bg-gray-700/50">
          <tr>
            <th class="w-8 px-2 py-2" />
            <th class="px-3 py-2 text-left">
              Variable
            </th>
            <th class="px-3 py-2 text-left">
              Beschreibung
            </th>
            <th class="px-3 py-2 text-left">
              Wert
            </th>
            <th class="px-3 py-2 text-left">
              Typ
            </th>
            <th class="w-20 px-3 py-2" />
          </tr>
        </thead>
        <draggable
          :list="localParams"
          tag="tbody"
          item-key="variable"
          handle=".drag-handle"
          ghost-class="bg-go4-primary/10"
          @end="onDragEnd"
        >
          <template #item="{ element: param }">
            <tr
              class="border-b border-gray-100 hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-700/30"
            >
              <!-- Drag Handle -->
              <td class="px-2 py-2">
                <div class="drag-handle cursor-move text-gray-400 hover:text-gray-600">
                  <svg
                    class="h-4 w-4"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path d="M7 2a2 2 0 1 0 0 4 2 2 0 0 0 0-4zM7 8a2 2 0 1 0 0 4 2 2 0 0 0 0-4zM7 14a2 2 0 1 0 0 4 2 2 0 0 0 0-4zM13 2a2 2 0 1 0 0 4 2 2 0 0 0 0-4zM13 8a2 2 0 1 0 0 4 2 2 0 0 0 0-4zM13 14a2 2 0 1 0 0 4 2 2 0 0 0 0-4z" />
                  </svg>
                </div>
              </td>

              <!-- Variable -->
              <td class="px-3 py-2">
                <code class="rounded bg-gray-100 px-1.5 py-0.5 text-xs dark:bg-gray-700">
                  {{ param.variable }}
                </code>
              </td>

              <!-- Description -->
              <td class="px-3 py-2">
                <template v-if="editingVariable === param.variable">
                  <input
                    v-model="editDescription"
                    type="text"
                    class="w-full rounded border border-gray-300 px-2 py-1 text-sm dark:border-gray-600 dark:bg-gray-700"
                    @keyup.enter="saveEdit(param)"
                    @keyup.escape="cancelEdit"
                  >
                </template>
                <template v-else>
                  <span class="text-go4-secondary dark:text-gray-300">
                    {{ param.description }}
                  </span>
                </template>
              </td>

              <!-- Value -->
              <td class="px-3 py-2">
                <template v-if="editingVariable === param.variable">
                  <input
                    v-model="editValue"
                    type="text"
                    class="w-full rounded border border-gray-300 px-2 py-1 text-sm dark:border-gray-600 dark:bg-gray-700"
                    placeholder="(leer)"
                    @keyup.enter="saveEdit(param)"
                    @keyup.escape="cancelEdit"
                  >
                </template>
                <template v-else>
                  <span
                    v-if="param.value"
                    class="text-go4-secondary dark:text-gray-300"
                  >
                    {{ param.value }}
                  </span>
                  <span
                    v-else
                    class="text-go4-muted italic"
                  >
                    (leer)
                  </span>
                </template>
              </td>

              <!-- Type -->
              <td class="px-3 py-2">
                <span class="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-go4-muted dark:bg-gray-700">
                  {{ typeLabels[param.var_type] || param.var_type }}
                </span>
              </td>

              <!-- Actions -->
              <td class="px-3 py-2">
                <div class="flex items-center gap-1">
                  <template v-if="editingVariable === param.variable">
                    <button
                      class="rounded p-1 text-green-600 hover:bg-green-100"
                      title="Speichern"
                      @click="saveEdit(param)"
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
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                    </button>
                    <button
                      class="rounded p-1 text-gray-400 hover:bg-gray-100"
                      title="Abbrechen"
                      @click="cancelEdit"
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
                          d="M6 18L18 6M6 6l12 12"
                        />
                      </svg>
                    </button>
                  </template>
                  <template v-else>
                    <button
                      class="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-go4-primary"
                      title="Bearbeiten"
                      @click="startEdit(param)"
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
                          d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                        />
                      </svg>
                    </button>
                    <button
                      class="rounded p-1 text-gray-400 hover:bg-red-100 hover:text-red-600"
                      title="Löschen"
                      @click="handleDelete(param)"
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
                  </template>
                </div>
              </td>
            </tr>
          </template>
        </draggable>
      </table>

      <!-- Empty State -->
      <div
        v-if="!hasParams && !loading"
        class="py-8 text-center text-go4-muted"
      >
        <p>Keine Parameter definiert</p>
        <p class="mt-1 text-xs">
          Parameter definieren welche Informationen im Onboarding abgefragt werden
        </p>
      </div>

      <!-- Loading -->
      <div
        v-if="loading"
        class="py-8 text-center text-go4-muted"
      >
        Laden...
      </div>
    </div>

    <!-- Add Form -->
    <div
      v-if="showAddForm"
      class="border-t border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-700/30"
    >
      <div class="grid grid-cols-4 gap-3">
        <div>
          <label class="mb-1 block text-xs text-go4-muted">Variable</label>
          <input
            v-model="newVariable"
            type="text"
            placeholder="z.B. company_name"
            class="w-full rounded border border-gray-300 px-2 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-700"
          >
        </div>
        <div class="col-span-2">
          <label class="mb-1 block text-xs text-go4-muted">Beschreibung</label>
          <input
            v-model="newDescription"
            type="text"
            placeholder="z.B. Name des Unternehmens"
            class="w-full rounded border border-gray-300 px-2 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-700"
          >
        </div>
        <div>
          <label class="mb-1 block text-xs text-go4-muted">Typ</label>
          <select
            v-model="newVarType"
            class="w-full rounded border border-gray-300 px-2 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-700"
          >
            <option value="string">
              Text
            </option>
            <option value="array">
              Liste
            </option>
            <option value="boolean">
              Ja/Nein
            </option>
            <option value="number">
              Zahl
            </option>
          </select>
        </div>
      </div>
      <div class="mt-3 flex justify-end gap-2">
        <button
          class="rounded px-3 py-1.5 text-sm text-go4-muted hover:bg-gray-200 dark:hover:bg-gray-600"
          @click="cancelAdd"
        >
          Abbrechen
        </button>
        <button
          class="rounded bg-go4-primary px-3 py-1.5 text-sm text-white hover:bg-go4-primary-dark"
          :disabled="!newVariable.trim() || !newDescription.trim()"
          @click="saveAdd"
        >
          Hinzufügen
        </button>
      </div>
    </div>
  </div>
</template>
