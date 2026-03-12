<script setup>
import { ref } from 'vue'

const props = defineProps({
  filters: {
    type: Array,
    required: true
    // Each filter: { key: string, label: string, options: [{ value: string, label: string, count?: number }], multiple?: boolean }
  },
  modelValue: {
    type: Object,
    default: () => ({})
    // { filterKey: value | [values] }
  }
})

const emit = defineEmits(['update:modelValue'])

const collapsedSections = ref({})

function toggleSection(key) {
  collapsedSections.value[key] = !collapsedSections.value[key]
}

function isSelected(filterKey, value) {
  const current = props.modelValue[filterKey]
  if (Array.isArray(current)) {
    return current.includes(value)
  }
  return current === value
}

function toggleOption(filterKey, value, multiple) {
  const current = props.modelValue[filterKey]
  let newValue

  if (multiple) {
    const arr = Array.isArray(current) ? [...current] : []
    const idx = arr.indexOf(value)
    if (idx >= 0) {
      arr.splice(idx, 1)
    } else {
      arr.push(value)
    }
    newValue = arr.length > 0 ? arr : undefined
  } else {
    newValue = current === value ? undefined : value
  }

  const updated = { ...props.modelValue }
  if (newValue === undefined) {
    delete updated[filterKey]
  } else {
    updated[filterKey] = newValue
  }
  emit('update:modelValue', updated)
}

function clearAll() {
  emit('update:modelValue', {})
}

function hasActiveFilters() {
  return Object.keys(props.modelValue).length > 0
}
</script>

<template>
  <aside class="w-56 flex-shrink-0">
    <div class="sticky top-4">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
          Filter
        </h3>
        <button
          v-if="hasActiveFilters()"
          type="button"
          class="text-xs text-go4-primary hover:text-go4-primary-dark"
          @click="clearAll"
        >
          Zurücksetzen
        </button>
      </div>

      <div class="space-y-4">
        <div
          v-for="filter in filters"
          :key="filter.key"
          class="border-b border-gray-200 dark:border-gray-700 pb-4"
        >
          <button
            type="button"
            class="flex w-full items-center justify-between text-sm font-medium text-gray-700 dark:text-gray-300"
            @click="toggleSection(filter.key)"
          >
            <span>{{ filter.label }}</span>
            <svg
              class="h-4 w-4 transition-transform"
              :class="{ 'rotate-180': collapsedSections[filter.key] }"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </button>

          <div
            v-show="!collapsedSections[filter.key]"
            class="mt-2 space-y-1"
          >
            <label
              v-for="option in filter.options"
              :key="option.value"
              class="flex cursor-pointer items-center gap-2 rounded px-2 py-1 text-sm hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              <input
                type="checkbox"
                :checked="isSelected(filter.key, option.value)"
                class="h-4 w-4 rounded border-gray-300 text-go4-primary focus:ring-go4-primary"
                @change="toggleOption(filter.key, option.value, filter.multiple)"
              >
              <span class="flex-1 text-gray-600 dark:text-gray-400">{{ option.label }}</span>
              <span
                v-if="option.count !== undefined"
                class="text-xs text-gray-400 dark:text-gray-500"
              >
                {{ option.count }}
              </span>
            </label>
          </div>
        </div>
      </div>
    </div>
  </aside>
</template>
