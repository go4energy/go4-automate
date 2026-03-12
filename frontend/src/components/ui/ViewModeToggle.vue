<script setup>
const props = defineProps({
  modelValue: { type: String, required: true },
  modes: {
    type: Array,
    default: () => [
      { value: 'cards', icon: 'cards', label: 'Karten' },
      { value: 'table', icon: 'table', label: 'Tabelle' }
    ]
  }
})

const emit = defineEmits(['update:modelValue'])

const iconPaths = {
  cards:
    'M4 5a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H5a1 1 0 01-1-1V5zm10 0a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1V5zM4 15a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H5a1 1 0 01-1-1v-4zm10 0a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z',
  table:
    'M3 4a1 1 0 011-1h16a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zm0 6a1 1 0 011-1h16a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1v-2zm0 6a1 1 0 011-1h16a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1v-2z',
  kanban: 'M9 4h6v16H9V4zM4 8h4v12H4V8zm12-2h4v14h-4V6z',
  list: 'M4 6h16M4 10h16M4 14h16M4 18h16'
}

function setMode(mode) {
  emit('update:modelValue', mode)
}
</script>

<template>
  <div
    class="inline-flex rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 p-1"
  >
    <button
      v-for="mode in modes"
      :key="mode.value"
      type="button"
      :title="mode.label"
      class="rounded-md p-1.5 transition-colors"
      :class="[
        modelValue === mode.value
          ? 'bg-go4-primary text-white'
          : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700'
      ]"
      @click="setMode(mode.value)"
    >
      <svg
        class="h-5 w-5"
        fill="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          v-if="mode.icon === 'list'"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          :d="iconPaths[mode.icon]"
        />
        <path
          v-else
          :d="iconPaths[mode.icon]"
        />
      </svg>
    </button>
  </div>
</template>
