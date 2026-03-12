<script setup>
import { ref, onMounted, computed } from 'vue'
import api from '@/api'

const props = defineProps({
  show: { type: Boolean, default: false },
})

const emit = defineEmits(['close'])

const loading = ref(false)
const error = ref(null)
const limits = ref({})

// Group limits by category
const groupedLimits = computed(() => {
  const groups = {
    general: { label: 'Allgemein', items: [] },
    profile: { label: 'Profilbesuche', items: [] },
    messages: { label: 'Nachrichten', items: [] },
    requests: { label: 'Anfragen', items: [] },
    companies: { label: 'Unternehmen', items: [] },
  }

  for (const [key, value] of Object.entries(limits.value)) {
    const item = { key, ...value }

    if (key.includes('profile') || key.includes('page_view')) {
      groups.profile.items.push(item)
    } else if (key.includes('message') || key.includes('opener') || key.includes('followup') || key.includes('congratulation')) {
      groups.messages.items.push(item)
    } else if (key.includes('withdraw') || key.includes('request')) {
      groups.requests.items.push(item)
    } else if (key.includes('company')) {
      groups.companies.items.push(item)
    } else {
      groups.general.items.push(item)
    }
  }

  // Filter out empty groups
  return Object.fromEntries(
    Object.entries(groups).filter(([, group]) => group.items.length > 0)
  )
})

async function loadLimits() {
  loading.value = true
  error.value = null

  try {
    const { data } = await api.get('/v1/linkedin/safety-limits')
    limits.value = data
  } catch (err) {
    error.value = err.response?.data?.detail || 'Fehler beim Laden'
  } finally {
    loading.value = false
  }
}

function formatRange(item) {
  if (item.min === item.max) {
    return `${item.min}${item.unit ? ' ' + item.unit : ''}`
  }
  return `${item.min} - ${item.max}${item.unit ? ' ' + item.unit : ''}`
}

onMounted(() => {
  if (props.show) {
    loadLimits()
  }
})

// Watch for show changes
import { watch } from 'vue'
watch(
  () => props.show,
  (visible) => {
    if (visible && Object.keys(limits.value).length === 0) {
      loadLimits()
    }
  }
)
</script>

<template>
  <div
    v-if="show"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
    @click.self="emit('close')"
  >
    <div class="w-full max-w-2xl max-h-[80vh] overflow-hidden rounded-lg bg-white shadow-xl dark:bg-gray-800">
      <!-- Header -->
      <div class="flex items-center justify-between border-b border-gray-200 px-6 py-4 dark:border-gray-700">
        <div class="flex items-center gap-3">
          <div class="flex h-10 w-10 items-center justify-center rounded-full bg-blue-100 text-blue-600 dark:bg-blue-900/30">
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
                d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
              />
            </svg>
          </div>
          <div>
            <h3 class="text-lg font-semibold text-go4-secondary dark:text-white">
              Safety Limits
            </h3>
            <p class="text-sm text-go4-muted">
              Automatisierungsgrenzen für menschenähnliches Verhalten
            </p>
          </div>
        </div>
        <button
          class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          @click="emit('close')"
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
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>

      <!-- Content -->
      <div
        class="overflow-y-auto p-6"
        style="max-height: calc(80vh - 140px)"
      >
        <!-- Loading -->
        <div
          v-if="loading"
          class="py-8 text-center text-go4-muted"
        >
          Laden...
        </div>

        <!-- Error -->
        <div
          v-else-if="error"
          class="rounded-lg bg-red-50 p-4 text-red-700 dark:bg-red-900/20"
        >
          {{ error }}
        </div>

        <!-- Limits -->
        <div
          v-else
          class="space-y-6"
        >
          <!-- Info Banner -->
          <div class="rounded-lg bg-blue-50 p-4 dark:bg-blue-900/20">
            <div class="flex gap-3">
              <svg
                class="h-5 w-5 flex-shrink-0 text-blue-600 dark:text-blue-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <div class="text-sm text-blue-700 dark:text-blue-300">
                <p class="font-medium">
                  Automatische Randomisierung
                </p>
                <p class="mt-1">
                  Bei jedem Start einer Routine wird ein zufälliger Wert innerhalb des angegebenen Bereichs gewählt.
                  Dies simuliert menschliches Verhalten und minimiert das Erkennungsrisiko.
                </p>
              </div>
            </div>
          </div>

          <!-- Grouped Limits -->
          <div
            v-for="(group, groupKey) in groupedLimits"
            :key="groupKey"
            class="rounded-lg border border-gray-200 dark:border-gray-700"
          >
            <div class="border-b border-gray-200 bg-gray-50 px-4 py-2 dark:border-gray-700 dark:bg-gray-700/50">
              <h4 class="font-medium text-go4-secondary dark:text-white">
                {{ group.label }}
              </h4>
            </div>
            <div class="divide-y divide-gray-200 dark:divide-gray-700">
              <div
                v-for="item in group.items"
                :key="item.key"
                class="flex items-center justify-between px-4 py-3"
              >
                <span class="text-sm text-go4-secondary dark:text-gray-300">
                  {{ item.label }}
                </span>
                <span class="font-mono text-sm font-medium text-go4-primary">
                  {{ formatRange(item) }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="border-t border-gray-200 px-6 py-4 dark:border-gray-700">
        <div class="flex items-center justify-between">
          <p class="text-xs text-go4-muted">
            Diese Einstellungen können nur von Admins geändert werden.
          </p>
          <button
            class="rounded-lg bg-gray-100 px-4 py-2 text-sm font-medium hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600"
            @click="emit('close')"
          >
            Schließen
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
