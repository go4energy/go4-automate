<script setup>
import { ref, watch, computed } from 'vue'
import SettingsField from './SettingsField.vue'

const props = defineProps({
  moduleName: { type: String, required: true },
  schema: { type: Array, default: () => [] },
  config: { type: Object, default: () => ({}) },
  status: { type: Object, default: () => ({}) },
  saving: { type: Boolean, default: false }
})

const emit = defineEmits(['save'])

const localConfig = ref({})

watch(
  () => props.config,
  (val) => {
    localConfig.value = { ...val }
  },
  { immediate: true, deep: true }
)

function updateField(key, value) {
  localConfig.value[key] = value
}

function reset() {
  localConfig.value = { ...props.config }
}

function save() {
  emit('save', localConfig.value)
}

const isHealthy = computed(() => props.status?.healthy === true)

const categories = computed(() => {
  const map = {}
  for (const param of props.schema) {
    const cat = param.category || 'allgemein'
    if (!map[cat]) map[cat] = []
    map[cat].push(param)
  }
  return Object.entries(map).map(([key, params]) => ({ key, params }))
})

const hasChanges = computed(() => {
  return JSON.stringify(localConfig.value) !== JSON.stringify(props.config)
})
</script>

<template>
  <div class="space-y-6">
    <!-- Status Badge -->
    <div
      v-if="status && status.module"
      class="flex items-center gap-4"
    >
      <div class="flex items-center gap-2">
        <span
          :class="[
            'inline-flex h-2.5 w-2.5 rounded-full',
            isHealthy ? 'bg-green-500' : 'bg-red-500'
          ]"
        />
        <span class="text-sm font-medium text-go4-secondary dark:text-gray-200">
          {{ isHealthy ? 'Gesund' : 'Problem' }}
        </span>
      </div>
      <!-- Component details -->
      <div
        v-if="status.components"
        class="flex flex-wrap gap-2"
      >
        <span
          v-for="(value, key) in status.components"
          :key="key"
          :class="[
            'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
            value === 'ok'
              ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
              : value === 'not_configured'
                ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400'
                : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
          ]"
        >
          {{ key }}: {{ value }}
        </span>
      </div>
    </div>

    <!-- Params grouped by category -->
    <div
      v-for="cat in categories"
      :key="cat.key"
      class="space-y-4"
    >
      <h3 class="text-sm font-semibold uppercase tracking-wider text-gray-400">
        {{ cat.key }}
      </h3>
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
        <SettingsField
          v-for="param in cat.params"
          :key="param.key"
          :param="param"
          :model-value="localConfig[param.key] ?? param.default"
          @update:model-value="updateField(param.key, $event)"
        />
      </div>
    </div>

    <!-- Actions -->
    <div class="flex items-center gap-3 border-t border-gray-200 pt-4 dark:border-gray-700">
      <button
        :disabled="saving || !hasChanges"
        class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white transition hover:bg-go4-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
        @click="save"
      >
        {{ saving ? 'Speichern...' : 'Speichern' }}
      </button>
      <button
        :disabled="saving || !hasChanges"
        class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
        @click="reset"
      >
        Zuruecksetzen
      </button>
    </div>
  </div>
</template>
