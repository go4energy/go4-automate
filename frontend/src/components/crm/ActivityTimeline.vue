<script setup>
import { ref } from 'vue'

defineProps({
  activities: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false }
})

const emit = defineEmits(['add'])

const showForm = ref(false)
const formData = ref({
  activity_type: 'note',
  subject: '',
  description: ''
})

const activityTypes = [
  { value: 'call', label: 'Anruf', icon: 'phone' },
  { value: 'meeting', label: 'Meeting', icon: 'users' },
  { value: 'email', label: 'E-Mail', icon: 'mail' },
  { value: 'note', label: 'Notiz', icon: 'note' }
]

const activityIcons = {
  call: {
    icon: 'M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z',
    color: 'text-blue-500 bg-blue-100 dark:bg-blue-900/30'
  },
  meeting: {
    icon: 'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z',
    color: 'text-purple-500 bg-purple-100 dark:bg-purple-900/30'
  },
  email: {
    icon: 'M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z',
    color: 'text-green-500 bg-green-100 dark:bg-green-900/30'
  },
  note: {
    icon: 'M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z',
    color: 'text-gray-500 bg-gray-100 dark:bg-gray-700'
  },
  task_completed: {
    icon: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
    color: 'text-green-500 bg-green-100 dark:bg-green-900/30'
  },
  stage_changed: {
    icon: 'M13 7h8m0 0v8m0-8l-8 8-4-4-6 6',
    color: 'text-orange-500 bg-orange-100 dark:bg-orange-900/30'
  }
}

function formatDate(dateString) {
  if (!dateString) return ''
  const date = new Date(dateString)
  const now = new Date()
  const diff = now - date
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))

  if (days === 0) {
    const hours = Math.floor(diff / (1000 * 60 * 60))
    if (hours === 0) {
      const minutes = Math.floor(diff / (1000 * 60))
      return minutes <= 1 ? 'Gerade eben' : `vor ${minutes} Minuten`
    }
    return hours === 1 ? 'vor 1 Stunde' : `vor ${hours} Stunden`
  }
  if (days === 1) return 'Gestern'
  if (days < 7) return `vor ${days} Tagen`
  return date.toLocaleDateString('de-DE')
}

function openForm() {
  showForm.value = true
  formData.value = {
    activity_type: 'note',
    subject: '',
    description: ''
  }
}

function closeForm() {
  showForm.value = false
}

function submitForm() {
  if (!formData.value.subject.trim()) return
  emit('add', { ...formData.value })
  closeForm()
}
</script>

<template>
  <div class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
    <!-- Header -->
    <div
      class="flex items-center justify-between border-b border-gray-200 dark:border-gray-700 px-4 py-3"
    >
      <h3 class="font-medium text-gray-900 dark:text-gray-100">
        Aktivitäten
      </h3>
      <button
        type="button"
        class="rounded-lg bg-go4-primary px-3 py-1.5 text-sm font-medium text-white hover:bg-go4-primary-dark"
        @click="openForm"
      >
        + Aktivität
      </button>
    </div>

    <!-- Add Form -->
    <div
      v-if="showForm"
      class="border-b border-gray-200 dark:border-gray-700 p-4 bg-gray-50 dark:bg-gray-900/50"
    >
      <div class="space-y-3">
        <div class="flex gap-2">
          <button
            v-for="type in activityTypes"
            :key="type.value"
            type="button"
            class="rounded-lg px-3 py-1.5 text-sm font-medium transition-colors"
            :class="
              formData.activity_type === type.value
                ? 'bg-go4-primary text-white'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
            "
            @click="formData.activity_type = type.value"
          >
            {{ type.label }}
          </button>
        </div>

        <input
          v-model="formData.subject"
          type="text"
          placeholder="Betreff"
          class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
        >

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

    <!-- Loading -->
    <div
      v-if="loading"
      class="flex items-center justify-center p-8"
    >
      <span class="text-gray-500 dark:text-gray-400">Laden...</span>
    </div>

    <!-- Empty State -->
    <div
      v-else-if="activities.length === 0"
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
          d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
      <p class="text-sm text-gray-500 dark:text-gray-400">
        Keine Aktivitäten vorhanden
      </p>
    </div>

    <!-- Timeline -->
    <div
      v-else
      class="p-4"
    >
      <div class="space-y-4">
        <div
          v-for="activity in activities"
          :key="activity.id"
          class="flex gap-3"
        >
          <div class="flex-shrink-0">
            <div
              class="flex h-8 w-8 items-center justify-center rounded-full"
              :class="activityIcons[activity.activity_type]?.color || activityIcons.note.color"
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
                  :d="activityIcons[activity.activity_type]?.icon || activityIcons.note.icon"
                />
              </svg>
            </div>
          </div>

          <div class="flex-1 min-w-0">
            <div class="flex items-start justify-between">
              <div>
                <p class="text-sm font-medium text-gray-900 dark:text-gray-100">
                  {{ activity.subject }}
                </p>
                <p
                  v-if="activity.description"
                  class="mt-0.5 text-sm text-gray-500 dark:text-gray-400"
                >
                  {{ activity.description }}
                </p>
              </div>
              <span class="flex-shrink-0 text-xs text-gray-400 dark:text-gray-500">
                {{ formatDate(activity.created_at) }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
