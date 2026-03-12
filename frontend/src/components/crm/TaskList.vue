<script setup>
import { ref, computed } from 'vue'
import { useCrmStore } from '@/stores/crm'

const props = defineProps({
  tasks: { type: Array, default: () => [] },
  dealId: { type: Number, default: null },
  contactId: { type: Number, default: null }
})

const store = useCrmStore()

const showForm = ref(false)
const formData = ref({
  subject: '',
  description: '',
  due_date: '',
  priority: 'medium'
})

const sortedTasks = computed(() => {
  return [...props.tasks].sort((a, b) => {
    // Open tasks first
    if (a.status !== b.status) {
      return a.status === 'open' ? -1 : 1
    }
    // Then by due date
    if (a.due_date && b.due_date) {
      return new Date(a.due_date) - new Date(b.due_date)
    }
    if (a.due_date) return -1
    if (b.due_date) return 1
    return new Date(b.created_at) - new Date(a.created_at)
  })
})

const openCount = computed(() => props.tasks.filter((t) => t.status === 'open').length)

const priorityConfig = {
  low: { label: 'Niedrig', class: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300' },
  medium: {
    label: 'Normal',
    class: 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-300'
  },
  high: {
    label: 'Hoch',
    class: 'bg-orange-100 text-orange-600 dark:bg-orange-900/30 dark:text-orange-300'
  }
}

function formatDate(dateString) {
  if (!dateString) return ''
  const date = new Date(dateString)
  const today = new Date()
  today.setHours(0, 0, 0, 0)

  const tomorrow = new Date(today)
  tomorrow.setDate(tomorrow.getDate() + 1)

  const dateOnly = new Date(date)
  dateOnly.setHours(0, 0, 0, 0)

  if (dateOnly.getTime() === today.getTime()) return 'Heute'
  if (dateOnly.getTime() === tomorrow.getTime()) return 'Morgen'
  if (dateOnly < today) return 'Überfällig'
  return date.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit' })
}

function isOverdue(task) {
  if (task.status !== 'open' || !task.due_date) return false
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return new Date(task.due_date) < today
}

function openForm() {
  showForm.value = true
  formData.value = {
    subject: '',
    description: '',
    due_date: '',
    priority: 'medium'
  }
}

function closeForm() {
  showForm.value = false
}

async function submitForm() {
  if (!formData.value.subject.trim()) return

  try {
    await store.addTask({
      ...formData.value,
      deal_id: props.dealId,
      contact_id: props.contactId
    })
    closeForm()
  } catch {
    // Error handled in store
  }
}

async function toggleComplete(task) {
  try {
    if (task.status === 'open') {
      await store.completeTask(task.id)
    } else {
      await store.editTask(task.id, { status: 'open' })
    }
  } catch {
    // Error handled in store
  }
}

async function deleteTask(task) {
  try {
    await store.removeTask(task.id)
  } catch {
    // Error handled in store
  }
}
</script>

<template>
  <div class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
    <!-- Header -->
    <div
      class="flex items-center justify-between border-b border-gray-200 dark:border-gray-700 px-4 py-3"
    >
      <div class="flex items-center gap-2">
        <h3 class="font-medium text-gray-900 dark:text-gray-100">
          Aufgaben
        </h3>
        <span
          v-if="openCount > 0"
          class="rounded-full bg-go4-primary/10 px-2 py-0.5 text-xs font-medium text-go4-primary"
        >
          {{ openCount }} offen
        </span>
      </div>
      <button
        type="button"
        class="rounded-lg bg-go4-primary px-3 py-1.5 text-sm font-medium text-white hover:bg-go4-primary-dark"
        @click="openForm"
      >
        + Aufgabe
      </button>
    </div>

    <!-- Add Form -->
    <div
      v-if="showForm"
      class="border-b border-gray-200 dark:border-gray-700 p-4 bg-gray-50 dark:bg-gray-900/50"
    >
      <div class="space-y-3">
        <input
          v-model="formData.subject"
          type="text"
          placeholder="Aufgabe beschreiben..."
          class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
        >

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">Fällig am</label>
            <input
              v-model="formData.due_date"
              type="date"
              class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
            >
          </div>
          <div>
            <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">Priorität</label>
            <select
              v-model="formData.priority"
              class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
            >
              <option value="low">
                Niedrig
              </option>
              <option value="medium">
                Normal
              </option>
              <option value="high">
                Hoch
              </option>
            </select>
          </div>
        </div>

        <textarea
          v-model="formData.description"
          rows="2"
          placeholder="Beschreibung (optional)"
          class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
        />

        <div class="flex justify-end gap-2">
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
            @click="submitForm"
          >
            Speichern
          </button>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div
      v-if="tasks.length === 0 && !showForm"
      class="flex flex-col items-center justify-center p-8 text-center"
    >
      <svg
        class="h-12 w-12 text-gray-300 dark:text-gray-600 mb-3"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
        />
      </svg>
      <p class="text-sm text-gray-500 dark:text-gray-400">
        Keine Aufgaben vorhanden
      </p>
    </div>

    <!-- Task List -->
    <div
      v-else
      class="divide-y divide-gray-100 dark:divide-gray-700"
    >
      <div
        v-for="task in sortedTasks"
        :key="task.id"
        class="flex items-start gap-3 p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
        :class="{ 'opacity-60': task.status === 'completed' }"
      >
        <!-- Checkbox -->
        <button
          type="button"
          class="flex-shrink-0 mt-0.5"
          @click="toggleComplete(task)"
        >
          <div
            class="h-5 w-5 rounded border-2 flex items-center justify-center transition-colors"
            :class="
              task.status === 'completed'
                ? 'border-go4-primary bg-go4-primary'
                : 'border-gray-300 dark:border-gray-600 hover:border-go4-primary'
            "
          >
            <svg
              v-if="task.status === 'completed'"
              class="h-3 w-3 text-white"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="3"
                d="M5 13l4 4L19 7"
              />
            </svg>
          </div>
        </button>

        <!-- Content -->
        <div class="flex-1 min-w-0">
          <div class="flex items-start justify-between gap-2">
            <p
              class="text-sm font-medium"
              :class="
                task.status === 'completed'
                  ? 'text-gray-400 dark:text-gray-500 line-through'
                  : 'text-gray-900 dark:text-gray-100'
              "
            >
              {{ task.subject }}
            </p>
            <button
              type="button"
              class="flex-shrink-0 rounded p-1 text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20"
              @click="deleteTask(task)"
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
          </div>

          <div class="mt-1 flex items-center gap-2 text-xs">
            <span
              v-if="task.due_date"
              class="flex items-center gap-1"
              :class="isOverdue(task) ? 'text-red-500' : 'text-gray-400 dark:text-gray-500'"
            >
              <svg
                class="h-3 w-3"
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
              {{ formatDate(task.due_date) }}
            </span>
            <span
              class="rounded-full px-1.5 py-0.5 text-xs"
              :class="priorityConfig[task.priority]?.class"
            >
              {{ priorityConfig[task.priority]?.label }}
            </span>
          </div>

          <p
            v-if="task.description"
            class="mt-1 text-xs text-gray-500 dark:text-gray-400 line-clamp-2"
          >
            {{ task.description }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
