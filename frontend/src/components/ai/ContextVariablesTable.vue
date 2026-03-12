<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  variables: { type: Object, required: true },
  loading: { type: Boolean, default: false }
})

const emit = defineEmits(['update', 'delete', 'add'])

// Editing state
const editingKey = ref(null)
const editValue = ref(null)
const editType = ref('text')

// Add new variable
const showAddRow = ref(false)
const newKey = ref('')
const newValue = ref('')

// Convert object to sorted array for display
const variablesList = computed(() => {
  return Object.entries(props.variables || {}).sort((a, b) => a[0].localeCompare(b[0]))
})

// Detect type from value
function detectType(value) {
  if (typeof value === 'boolean') return 'boolean'
  if (typeof value === 'number') return 'number'
  if (Array.isArray(value)) return 'list'
  if (typeof value === 'object' && value !== null) return 'json'
  if (typeof value === 'string' && value.length > 100) return 'textarea'
  return 'text'
}

// Format value for display
function formatValue(value) {
  if (typeof value === 'boolean') {
    return value ? 'true' : 'false'
  }
  if (Array.isArray(value)) {
    return value.join(', ')
  }
  if (typeof value === 'object' && value !== null) {
    return JSON.stringify(value, null, 2)
  }
  const str = String(value)
  if (str.length > 80) {
    return str.slice(0, 80) + '...'
  }
  return str
}

// Start editing a variable
function startEdit(key, value) {
  editingKey.value = key
  editType.value = detectType(value)

  // Convert value for editing
  if (Array.isArray(value)) {
    editValue.value = value.join('\n')
  } else if (typeof value === 'object' && value !== null) {
    editValue.value = JSON.stringify(value, null, 2)
  } else {
    editValue.value = value
  }
}

// Save edited variable
function saveEdit() {
  let finalValue = editValue.value

  // Convert back based on type
  if (editType.value === 'boolean') {
    finalValue = editValue.value === true || editValue.value === 'true'
  } else if (editType.value === 'number') {
    finalValue = Number(editValue.value)
  } else if (editType.value === 'list') {
    finalValue = editValue.value
      .split('\n')
      .map((s) => s.trim())
      .filter(Boolean)
  } else if (editType.value === 'json') {
    try {
      finalValue = JSON.parse(editValue.value)
    } catch {
      // Keep as string if invalid JSON
    }
  }

  emit('update', editingKey.value, finalValue)
  cancelEdit()
}

// Cancel editing
function cancelEdit() {
  editingKey.value = null
  editValue.value = null
  editType.value = 'text'
}

// Add new variable
function addVariable() {
  if (!newKey.value.trim()) return

  // Validate key format (snake_case)
  const key = newKey.value.trim().replace(/\s+/g, '_').toLowerCase()
  emit('add', key, newValue.value || '')

  newKey.value = ''
  newValue.value = ''
  showAddRow.value = false
}

// Delete variable
function deleteVariable(key) {
  if (confirm(`Variable "${key}" wirklich löschen?`)) {
    emit('delete', key)
  }
}
</script>

<template>
  <div class="rounded-lg border border-gray-200 dark:border-gray-700">
    <!-- Table -->
    <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
      <thead class="bg-gray-50 dark:bg-gray-800">
        <tr>
          <th
            class="px-4 py-3 text-left text-xs font-medium uppercase text-go4-muted dark:text-gray-400"
          >
            Variable
          </th>
          <th
            class="px-4 py-3 text-left text-xs font-medium uppercase text-go4-muted dark:text-gray-400"
          >
            Wert
          </th>
          <th
            class="w-24 px-4 py-3 text-right text-xs font-medium uppercase text-go4-muted dark:text-gray-400"
          >
            Aktionen
          </th>
        </tr>
      </thead>
      <tbody class="divide-y divide-gray-200 bg-white dark:divide-gray-700 dark:bg-gray-800">
        <!-- Variable rows -->
        <tr
          v-for="[key, value] in variablesList"
          :key="key"
        >
          <td class="px-4 py-3 font-mono text-sm text-go4-secondary dark:text-white">
            {{ key }}
          </td>
          <td class="px-4 py-3">
            <!-- Edit mode -->
            <div
              v-if="editingKey === key"
              class="space-y-2"
            >
              <select
                v-model="editType"
                class="rounded border border-gray-300 px-2 py-1 text-sm dark:border-gray-600 dark:bg-gray-700"
              >
                <option value="text">
                  Text
                </option>
                <option value="textarea">
                  Langer Text
                </option>
                <option value="boolean">
                  Boolean
                </option>
                <option value="number">
                  Zahl
                </option>
                <option value="list">
                  Liste (eine pro Zeile)
                </option>
                <option value="json">
                  JSON
                </option>
              </select>

              <!-- Boolean -->
              <div
                v-if="editType === 'boolean'"
                class="flex items-center gap-2"
              >
                <input
                  type="checkbox"
                  :checked="editValue === true || editValue === 'true'"
                  class="h-4 w-4 rounded"
                  @change="editValue = $event.target.checked"
                >
                <span class="text-sm">{{ editValue ? 'true' : 'false' }}</span>
              </div>

              <!-- Number -->
              <input
                v-else-if="editType === 'number'"
                v-model="editValue"
                type="number"
                class="w-full rounded border border-gray-300 px-2 py-1 text-sm dark:border-gray-600 dark:bg-gray-700"
              >

              <!-- Textarea / List / JSON -->
              <textarea
                v-else-if="['textarea', 'list', 'json'].includes(editType)"
                v-model="editValue"
                rows="4"
                class="w-full rounded border border-gray-300 px-2 py-1 font-mono text-sm dark:border-gray-600 dark:bg-gray-700"
              />

              <!-- Text -->
              <input
                v-else
                v-model="editValue"
                type="text"
                class="w-full rounded border border-gray-300 px-2 py-1 text-sm dark:border-gray-600 dark:bg-gray-700"
              >

              <div class="flex gap-2">
                <button
                  class="rounded bg-go4-primary px-3 py-1 text-sm text-white hover:bg-go4-primary-dark"
                  @click="saveEdit"
                >
                  Speichern
                </button>
                <button
                  class="rounded border border-gray-300 px-3 py-1 text-sm hover:bg-gray-100 dark:border-gray-600 dark:hover:bg-gray-700"
                  @click="cancelEdit"
                >
                  Abbrechen
                </button>
              </div>
            </div>

            <!-- Display mode -->
            <div v-else>
              <!-- Boolean -->
              <span
                v-if="typeof value === 'boolean'"
                :class="value ? 'text-green-600' : 'text-gray-400'"
              >
                {{ value ? 'true' : 'false' }}
              </span>

              <!-- List -->
              <div
                v-else-if="Array.isArray(value)"
                class="flex flex-wrap gap-1"
              >
                <span
                  v-for="item in value"
                  :key="item"
                  class="rounded bg-gray-100 px-2 py-0.5 text-sm dark:bg-gray-700"
                >
                  {{ item }}
                </span>
              </div>

              <!-- Object -->
              <code
                v-else-if="typeof value === 'object' && value !== null"
                class="text-xs text-gray-600 dark:text-gray-400"
              >
                {{ formatValue(value) }}
              </code>

              <!-- Text -->
              <span
                v-else
                class="text-sm text-go4-secondary dark:text-white"
              >
                {{ formatValue(value) }}
              </span>
            </div>
          </td>
          <td class="px-4 py-3 text-right">
            <button
              class="text-gray-400 hover:text-go4-primary"
              title="Bearbeiten"
              :disabled="loading"
              @click="startEdit(key, value)"
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
              class="ml-2 text-gray-400 hover:text-red-500"
              title="Löschen"
              :disabled="loading"
              @click="deleteVariable(key)"
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
          </td>
        </tr>

        <!-- Empty state -->
        <tr v-if="variablesList.length === 0 && !showAddRow">
          <td
            colspan="3"
            class="px-4 py-8 text-center text-go4-muted"
          >
            Keine Variablen definiert. Starte das Onboarding oder füge manuell hinzu.
          </td>
        </tr>

        <!-- Add new row -->
        <tr v-if="showAddRow">
          <td class="px-4 py-3">
            <input
              v-model="newKey"
              placeholder="variable_name"
              class="w-full rounded border border-gray-300 px-2 py-1 font-mono text-sm dark:border-gray-600 dark:bg-gray-700"
              @keyup.enter="addVariable"
            >
          </td>
          <td class="px-4 py-3">
            <input
              v-model="newValue"
              placeholder="Wert"
              class="w-full rounded border border-gray-300 px-2 py-1 text-sm dark:border-gray-600 dark:bg-gray-700"
              @keyup.enter="addVariable"
            >
          </td>
          <td class="px-4 py-3 text-right">
            <button
              class="text-sm text-gray-500 hover:text-gray-700"
              @click="showAddRow = false"
            >
              Abbrechen
            </button>
            <button
              class="ml-2 text-sm text-go4-primary hover:underline"
              @click="addVariable"
            >
              Hinzufügen
            </button>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- Add button -->
    <div
      v-if="!showAddRow"
      class="border-t border-gray-200 p-2 dark:border-gray-700"
    >
      <button
        class="text-sm text-go4-primary hover:underline"
        :disabled="loading"
        @click="showAddRow = true"
      >
        + Neue Variable
      </button>
    </div>

    <!-- Hint -->
    <div
      class="border-t border-gray-200 bg-gray-50 px-4 py-2 text-xs text-go4-muted dark:border-gray-700 dark:bg-gray-900"
    >
      Diese Variablen werden in Prompts als <code v-pre>{{ variable }}</code> verwendet und
      automatisch ersetzt.
    </div>
  </div>
</template>
