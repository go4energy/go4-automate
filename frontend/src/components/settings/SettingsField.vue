<script setup>
import { computed } from 'vue'

const props = defineProps({
  param: { type: Object, required: true },
  modelValue: { type: [String, Number, Boolean], default: null }
})

const emit = defineEmits(['update:modelValue'])

const isReadOnly = computed(() => props.param.editable === false)

function onInput(event) {
  const type = props.param.type
  let value = event.target.value
  if (type === 'integer') value = parseInt(value, 10) || 0
  else if (type === 'number') value = parseFloat(value) || 0
  emit('update:modelValue', value)
}

function onToggle() {
  emit('update:modelValue', !props.modelValue)
}

function onSelect(event) {
  emit('update:modelValue', event.target.value)
}

const hint = computed(() => {
  const p = props.param
  if (p.min !== undefined && p.max !== undefined) {
    return `${p.min} – ${p.max}`
  }
  return null
})
</script>

<template>
  <div class="space-y-1">
    <label class="block text-sm font-medium text-go4-secondary dark:text-gray-200">
      {{ param.description }}
      <span
        v-if="isReadOnly"
        class="ml-1 text-xs text-gray-400"
      >(nur lesen)</span>
    </label>

    <!-- Boolean: Toggle -->
    <button
      v-if="param.type === 'boolean'"
      type="button"
      :disabled="isReadOnly"
      :class="[
        'relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200',
        modelValue ? 'bg-go4-primary' : 'bg-gray-200 dark:bg-gray-600',
        isReadOnly ? 'opacity-50 cursor-not-allowed' : ''
      ]"
      @click="onToggle"
    >
      <span
        :class="[
          'pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200',
          modelValue ? 'translate-x-5' : 'translate-x-0'
        ]"
      />
    </button>

    <!-- Enum: Select -->
    <select
      v-else-if="param.type === 'enum'"
      :value="modelValue"
      :disabled="isReadOnly"
      class="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-go4-secondary shadow-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
      @change="onSelect"
    >
      <option
        v-for="opt in param.options"
        :key="opt"
        :value="opt"
      >
        {{ opt }}
      </option>
    </select>

    <!-- Secret: Password input -->
    <input
      v-else-if="param.type === 'secret'"
      type="password"
      :value="modelValue"
      :disabled="isReadOnly"
      :placeholder="
        modelValue === '***configured***'
          ? 'Konfiguriert (unveraendert lassen)'
          : 'Nicht konfiguriert'
      "
      class="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-go4-secondary shadow-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
      @input="onInput"
    >

    <!-- Integer: Number input -->
    <input
      v-else-if="param.type === 'integer'"
      type="number"
      :value="modelValue"
      :disabled="isReadOnly"
      :min="param.min"
      :max="param.max"
      step="1"
      class="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-go4-secondary shadow-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
      @input="onInput"
    >

    <!-- Number: Float input -->
    <input
      v-else-if="param.type === 'number'"
      type="number"
      :value="modelValue"
      :disabled="isReadOnly"
      :min="param.min"
      :max="param.max"
      step="0.1"
      class="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-go4-secondary shadow-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
      @input="onInput"
    >

    <!-- String: Text input (default) -->
    <input
      v-else
      type="text"
      :value="modelValue"
      :disabled="isReadOnly"
      class="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-go4-secondary shadow-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
      @input="onInput"
    >

    <p
      v-if="hint"
      class="text-xs text-gray-400"
    >
      Bereich: {{ hint }}
    </p>
  </div>
</template>
