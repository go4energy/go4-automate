<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCrmStore } from '@/stores/crm'
import PageHeader from '@/components/ui/PageHeader.vue'
import SearchInput from '@/components/ui/SearchInput.vue'

const router = useRouter()
const store = useCrmStore()

const searchQuery = ref('')
const filterStatus = ref('all')
const filterPriority = ref('all')

const filteredTasks = computed(() => {
  let tasks = [...store.tasks]

  // Filter by status
  if (filterStatus.value === 'open') {
    tasks = tasks.filter((t) => t.status === 'open')
  } else if (filterStatus.value === 'completed') {
    tasks = tasks.filter((t) => t.status === 'completed')
  } else if (filterStatus.value === 'overdue') {
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    tasks = tasks.filter((t) => t.status === 'open' && t.due_date && new Date(t.due_date) < today)
  }

  // Filter by priority
  if (filterPriority.value !== 'all') {
    tasks = tasks.filter((t) => t.priority === filterPriority.value)
  }

  // Search
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    tasks = tasks.filter(
      (t) =>
        t.subject?.toLowerCase().includes(query) || t.description?.toLowerCase().includes(query)
    )
  }

  // Sort: open first, then by due date
  return tasks.sort((a, b) => {
    if (a.status !== b.status) {
      return a.status === 'open' ? -1 : 1
    }
    if (a.due_date && b.due_date) {
      return new Date(a.due_date) - new Date(b.due_date)
    }
    if (a.due_date) return -1
    if (b.due_date) return 1
    return new Date(b.created_at) - new Date(a.created_at)
  })
})

const openCount = computed(() => store.tasks.filter((t) => t.status === 'open').length)

const overdueCount = computed(() => {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return store.tasks.filter(
    (t) => t.status === 'open' && t.due_date && new Date(t.due_date) < today
  ).length
})

const priorityConfig = {
  low: {
    label: 'Niedrig',
    class: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300'
  },
  medium: {
    label: 'Normal',
    class: 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-300'
  },
  high: {
    label: 'Hoch',
    class: 'bg-orange-100 text-orange-600 dark:bg-orange-900/30 dark:text-orange-300'
  }
}

onMounted(async () => {
  await store.fetchTasks()
})

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

function goToDeal(dealId) {
  router.push({ name: 'crm-deal-detail', params: { id: dealId } })
}
</script>

<template>
  <div>
    <PageHeader
      title="Aufgaben"
      :subtitle="`${openCount} offen · ${overdueCount} überfällig`"
    />

    <!-- Filters -->
    <div class="mt-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div class="flex items-center gap-3">
        <select
          v-model="filterStatus"
          class="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100"
        >
          <option value="all">
            Alle Status
          </option>
          <option value="open">
            Offen
          </option>
          <option value="completed">
            Erledigt
          </option>
          <option value="overdue">
            Überfällig
          </option>
        </select>

        <select
          v-model="filterPriority"
          class="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100"
        >
          <option value="all">
            Alle Prioritäten
          </option>
          <option value="high">
            Hoch
          </option>
          <option value="medium">
            Normal
          </option>
          <option value="low">
            Niedrig
          </option>
        </select>
      </div>

      <SearchInput
        v-model="searchQuery"
        placeholder="Aufgaben suchen..."
        class="w-64"
      />
    </div>

    <!-- Loading -->
    <div
      v-if="store.loading"
      class="mt-6 flex items-center justify-center p-12"
    >
      <span class="text-go4-muted dark:text-gray-400">Laden...</span>
    </div>

    <!-- Error -->
    <div
      v-else-if="store.error"
      class="mt-6 rounded-lg bg-red-50 dark:bg-red-900/20 p-4 text-red-700 dark:text-red-400"
    >
      {{ store.error }}
    </div>

    <!-- Empty State -->
    <div
      v-else-if="filteredTasks.length === 0"
      class="mt-6 flex flex-col items-center justify-center rounded-lg border border-dashed border-gray-300 dark:border-gray-600 p-12"
    >
      <svg
        class="h-12 w-12 text-gray-300 dark:text-gray-600 mb-4"
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
      <h3 class="text-lg font-medium text-gray-900 dark:text-gray-100 mb-1">
        Keine Aufgaben
      </h3>
      <p class="text-sm text-gray-500 dark:text-gray-400">
        Aufgaben werden in Deals erstellt.
      </p>
    </div>

    <!-- Task List -->
    <div
      v-else
      class="mt-6 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 divide-y divide-gray-100 dark:divide-gray-700"
    >
      <div
        v-for="task in filteredTasks"
        :key="task.id"
        class="flex items-start gap-4 p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
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
          <div class="flex items-start justify-between gap-4">
            <div>
              <p
                class="font-medium"
                :class="
                  task.status === 'completed'
                    ? 'text-gray-400 dark:text-gray-500 line-through'
                    : 'text-gray-900 dark:text-gray-100'
                "
              >
                {{ task.subject }}
              </p>
              <p
                v-if="task.description"
                class="mt-1 text-sm text-gray-500 dark:text-gray-400 line-clamp-2"
              >
                {{ task.description }}
              </p>
            </div>

            <div class="flex items-center gap-2 flex-shrink-0">
              <span
                v-if="task.due_date"
                class="flex items-center gap-1 text-sm"
                :class="isOverdue(task) ? 'text-red-500' : 'text-gray-400 dark:text-gray-500'"
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
                    d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
                  />
                </svg>
                {{ formatDate(task.due_date) }}
              </span>
              <span
                class="rounded-full px-2 py-0.5 text-xs"
                :class="priorityConfig[task.priority]?.class"
              >
                {{ priorityConfig[task.priority]?.label }}
              </span>
            </div>
          </div>

          <!-- Related Deal -->
          <div
            v-if="task.deal_id"
            class="mt-2"
          >
            <button
              type="button"
              class="text-sm text-go4-primary hover:underline"
              @click="goToDeal(task.deal_id)"
            >
              Zum Deal
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
