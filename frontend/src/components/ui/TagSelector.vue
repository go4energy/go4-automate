<script setup>
import { ref, computed, watch } from 'vue'
import api from '@/api'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  placeholder: { type: String, default: 'Tag auswaehlen...' }
})

const emit = defineEmits(['update:modelValue'])

const availableTags = ref([])
const loading = ref(false)
const creating = ref(false)
const dropdownOpen = ref(false)
const search = ref('')
let debounceTimer = null

const selectedSlugs = computed(() => props.modelValue || [])

const filteredTags = computed(() => {
  return availableTags.value.filter((t) => !selectedSlugs.value.includes(t.slug))
})

const selectedTags = computed(() =>
  selectedSlugs.value
    .map((slug) => availableTags.value.find((t) => t.slug === slug))
    .filter(Boolean)
)

const showCreateOption = computed(() => {
  if (!search.value.trim()) return false
  const q = search.value.toLowerCase().trim()
  return !availableTags.value.some((t) => t.label.toLowerCase() === q)
})

async function fetchTags(q) {
  loading.value = true
  try {
    const params = q ? { q } : {}
    const { data } = await api.get('/v1/tags/', { params })
    availableTags.value = data
  } catch {
    // silently fail
  } finally {
    loading.value = false
  }
}

watch(search, (val) => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    fetchTags(val.trim() || undefined)
  }, 300)
})

function addTag(tag) {
  emit('update:modelValue', [...selectedSlugs.value, tag.slug])
  search.value = ''
  dropdownOpen.value = false
}

function removeTag(slug) {
  emit(
    'update:modelValue',
    selectedSlugs.value.filter((s) => s !== slug)
  )
}

async function createAndAdd() {
  if (!search.value.trim() || creating.value) return
  creating.value = true
  try {
    const { data } = await api.post('/v1/tags/', { label: search.value.trim() })
    availableTags.value.push(data)
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
  if (availableTags.value.length === 0) {
    fetchTags()
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
    <!-- Selected tags -->
    <div
      class="flex min-h-[38px] flex-wrap items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-1.5 dark:border-gray-600 dark:bg-gray-800"
    >
      <span
        v-for="tag in selectedTags"
        :key="tag.slug"
        class="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium text-white"
        :style="{ backgroundColor: tag.color }"
      >
        {{ tag.label }}
        <button
          type="button"
          class="ml-0.5 text-white/70 hover:text-white"
          @click.stop="removeTag(tag.slug)"
        >
          &times;
        </button>
      </span>
      <!-- Slugs without matching tag object (e.g. tag deleted) -->
      <span
        v-for="slug in selectedSlugs.filter((s) => !selectedTags.find((t) => t.slug === s))"
        :key="slug"
        class="inline-flex items-center gap-1 rounded-full bg-gray-200 px-2.5 py-0.5 text-xs font-medium text-gray-700 dark:bg-gray-700 dark:text-gray-300"
      >
        {{ slug }}
        <button
          type="button"
          class="ml-0.5 text-gray-400 hover:text-gray-600"
          @click.stop="removeTag(slug)"
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
      />
    </div>

    <!-- Dropdown -->
    <div
      v-if="dropdownOpen && (filteredTags.length > 0 || showCreateOption)"
      class="absolute z-20 mt-1 max-h-48 w-full overflow-y-auto rounded-lg border border-gray-200 bg-white shadow-lg dark:border-gray-600 dark:bg-gray-800"
    >
      <button
        v-for="tag in filteredTags"
        :key="tag.slug"
        type="button"
        class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-gray-50 dark:hover:bg-gray-700"
        @mousedown.prevent="addTag(tag)"
      >
        <span class="inline-block h-3 w-3 rounded-full" :style="{ backgroundColor: tag.color }" />
        <span class="text-gray-800 dark:text-gray-200">{{ tag.label }}</span>
        <span class="text-xs text-gray-400 dark:text-gray-500">{{ tag.slug }}</span>
      </button>
      <!-- Create option -->
      <button
        v-if="showCreateOption"
        type="button"
        class="flex w-full items-center gap-2 border-t border-gray-100 px-3 py-2 text-left text-sm text-green-600 hover:bg-green-50 dark:border-gray-700 dark:text-green-400 dark:hover:bg-green-900/20"
        @mousedown.prevent="createAndAdd"
      >
        <span class="text-green-500">+</span>
        <span
          >Tag erstellen: <strong>{{ search.trim() }}</strong></span
        >
      </button>
    </div>

    <!-- Empty state -->
    <div
      v-if="dropdownOpen && filteredTags.length === 0 && !showCreateOption && search && !loading"
      class="absolute z-20 mt-1 w-full rounded-lg border border-gray-200 bg-white p-3 text-sm text-gray-500 shadow-lg dark:border-gray-600 dark:bg-gray-800 dark:text-gray-400"
    >
      Kein Tag gefunden.
    </div>
  </div>
</template>
