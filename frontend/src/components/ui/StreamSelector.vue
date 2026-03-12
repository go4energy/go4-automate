<script setup>
import { ref, computed, watch } from 'vue'
import api from '@/api'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  placeholder: { type: String, default: 'Stream auswaehlen...' }
})

const emit = defineEmits(['update:modelValue'])

const availableStreams = ref([])
const loading = ref(false)
const creating = ref(false)
const dropdownOpen = ref(false)
const search = ref('')
let debounceTimer = null

const selectedSlugs = computed(() => props.modelValue || [])

const filteredStreams = computed(() => {
  return availableStreams.value.filter((s) => !selectedSlugs.value.includes(s.slug))
})

const selectedStreams = computed(() =>
  selectedSlugs.value
    .map((slug) => availableStreams.value.find((s) => s.slug === slug))
    .filter(Boolean)
)

const showCreateOption = computed(() => {
  if (!search.value.trim()) return false
  const q = search.value.toLowerCase().trim()
  return !availableStreams.value.some((s) => s.label.toLowerCase() === q)
})

async function fetchStreams(q) {
  loading.value = true
  try {
    const params = q ? { q } : {}
    const { data } = await api.get('/v1/streams/', { params })
    availableStreams.value = data
  } catch {
    // silently fail
  } finally {
    loading.value = false
  }
}

watch(search, (val) => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    fetchStreams(val.trim() || undefined)
  }, 300)
})

function addStream(stream) {
  emit('update:modelValue', [...selectedSlugs.value, stream.slug])
  search.value = ''
  dropdownOpen.value = false
}

function removeStream(slug) {
  emit(
    'update:modelValue',
    selectedSlugs.value.filter((s) => s !== slug)
  )
}

async function createAndAdd() {
  if (!search.value.trim() || creating.value) return
  creating.value = true
  try {
    const { data } = await api.post('/v1/streams/', { label: search.value.trim() })
    availableStreams.value.push(data)
    emit('update:modelValue', [...selectedSlugs.value, data.slug])
    search.value = ''
    dropdownOpen.value = false
  } catch {
    // silently fail
  } finally {
    creating.value = false
  }
}

function handleFocus() {
  dropdownOpen.value = true
  if (availableStreams.value.length === 0) {
    fetchStreams()
  }
}

function handleBlur() {
  setTimeout(() => {
    dropdownOpen.value = false
  }, 200)
}
</script>

<template>
  <div class="relative">
    <!-- Selected streams -->
    <div
      class="flex min-h-[38px] flex-wrap items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-1.5 dark:border-gray-600 dark:bg-gray-800"
    >
      <span
        v-for="stream in selectedStreams"
        :key="stream.slug"
        class="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium text-white"
        :style="{ backgroundColor: stream.color }"
      >
        {{ stream.label }}
        <button
          type="button"
          class="ml-0.5 text-white/70 hover:text-white"
          @click.stop="removeStream(stream.slug)"
        >
          &times;
        </button>
      </span>
      <!-- Slugs without matching stream object -->
      <span
        v-for="slug in selectedSlugs.filter((s) => !selectedStreams.find((st) => st.slug === s))"
        :key="slug"
        class="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
      >
        {{ slug }}
        <button
          type="button"
          class="ml-0.5 text-blue-400 hover:text-blue-600"
          @click.stop="removeStream(slug)"
        >
          &times;
        </button>
      </span>
      <input
        v-model="search"
        type="text"
        class="min-w-[100px] flex-1 border-0 bg-transparent p-0 text-sm text-gray-800 outline-none placeholder:text-gray-400 focus:ring-0 dark:text-gray-200 dark:placeholder:text-gray-500"
        :placeholder="selectedSlugs.length === 0 ? placeholder : ''"
        @focus="handleFocus"
        @blur="handleBlur"
      >
    </div>

    <!-- Dropdown -->
    <div
      v-if="dropdownOpen && (filteredStreams.length > 0 || showCreateOption)"
      class="absolute z-20 mt-1 max-h-48 w-full overflow-y-auto rounded-lg border border-gray-200 bg-white shadow-lg dark:border-gray-600 dark:bg-gray-800"
    >
      <button
        v-for="stream in filteredStreams"
        :key="stream.slug"
        type="button"
        class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-gray-50 dark:hover:bg-gray-700"
        @mousedown.prevent="addStream(stream)"
      >
        <span
          class="inline-block h-3 w-3 rounded-full"
          :style="{ backgroundColor: stream.color }"
        />
        <span class="text-gray-800 dark:text-gray-200">{{ stream.label }}</span>
        <span class="text-xs text-gray-400 dark:text-gray-500">{{ stream.slug }}</span>
      </button>
      <!-- Create option -->
      <button
        v-if="showCreateOption"
        type="button"
        class="flex w-full items-center gap-2 border-t border-gray-100 px-3 py-2 text-left text-sm text-blue-600 hover:bg-blue-50 dark:border-gray-700 dark:text-blue-400 dark:hover:bg-blue-900/20"
        @mousedown.prevent="createAndAdd"
      >
        <span class="text-blue-500">+</span>
        <span>Stream erstellen: <strong>{{ search.trim() }}</strong></span>
      </button>
    </div>

    <!-- Empty state (no results, no create) -->
    <div
      v-if="dropdownOpen && filteredStreams.length === 0 && !showCreateOption && search && !loading"
      class="absolute z-20 mt-1 w-full rounded-lg border border-gray-200 bg-white p-3 text-sm text-gray-500 shadow-lg dark:border-gray-600 dark:bg-gray-800 dark:text-gray-400"
    >
      Kein Stream gefunden.
    </div>
  </div>
</template>
