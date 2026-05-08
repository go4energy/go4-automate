<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  suggestions: { type: Array, default: () => [] },
  placeholder: { type: String, default: 'Tag eingeben + Enter…' }
})

const emit = defineEmits(['update:modelValue', 'focus'])

const draft = ref('')
const dropdownOpen = ref(false)

const tags = computed(() => props.modelValue || [])

const filteredSuggestions = computed(() => {
  const q = draft.value.trim().toLowerCase()
  const existing = new Set(tags.value)
  return props.suggestions
    .filter((s) => !existing.has(s))
    .filter((s) => !q || s.toLowerCase().includes(q))
    .slice(0, 30)
})

function commitDraft() {
  const v = draft.value.trim()
  if (!v) return
  if (tags.value.includes(v)) {
    draft.value = ''
    return
  }
  emit('update:modelValue', [...tags.value, v])
  draft.value = ''
}

function addSuggestion(s) {
  if (tags.value.includes(s)) return
  emit('update:modelValue', [...tags.value, s])
  draft.value = ''
  dropdownOpen.value = false
}

function removeTag(t) {
  emit('update:modelValue', tags.value.filter((x) => x !== t))
}

function handleFocus() {
  dropdownOpen.value = true
  emit('focus')
}

function handleBlur() {
  setTimeout(() => (dropdownOpen.value = false), 200)
}

function handleKeydown(e) {
  if (e.key === 'Enter') {
    e.preventDefault()
    commitDraft()
  } else if (e.key === ',' || e.key === ' ') {
    if (draft.value.trim()) {
      e.preventDefault()
      commitDraft()
    }
  } else if (e.key === 'Backspace' && !draft.value && tags.value.length) {
    emit('update:modelValue', tags.value.slice(0, -1))
  }
}
</script>

<template>
  <div class="relative">
    <div
      class="flex min-h-[38px] flex-wrap items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-1.5 dark:border-gray-600 dark:bg-gray-800"
    >
      <span
        v-for="tag in tags"
        :key="tag"
        class="inline-flex items-center gap-1 rounded-full bg-go4-primary/10 px-2.5 py-0.5 text-xs font-medium text-go4-primary"
      >
        {{ tag }}
        <button
          type="button"
          class="ml-0.5 text-go4-primary/70 hover:text-go4-primary"
          @click.stop="removeTag(tag)"
        >
          &times;
        </button>
      </span>
      <input
        v-model="draft"
        type="text"
        class="min-w-[100px] flex-1 border-0 bg-transparent p-0 text-sm text-gray-800 outline-none placeholder:text-gray-400 focus:ring-0 dark:text-gray-200 dark:placeholder:text-gray-500"
        :placeholder="tags.length === 0 ? placeholder : ''"
        @focus="handleFocus"
        @blur="handleBlur"
        @keydown="handleKeydown"
      >
    </div>

    <div
      v-if="dropdownOpen && filteredSuggestions.length > 0"
      class="absolute z-20 mt-1 max-h-48 w-full overflow-y-auto rounded-lg border border-gray-200 bg-white shadow-lg dark:border-gray-600 dark:bg-gray-800"
    >
      <button
        v-for="s in filteredSuggestions"
        :key="s"
        type="button"
        class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-gray-50 dark:hover:bg-gray-700"
        @mousedown.prevent="addSuggestion(s)"
      >
        <span class="text-gray-800 dark:text-gray-200">{{ s }}</span>
      </button>
    </div>
  </div>
</template>
