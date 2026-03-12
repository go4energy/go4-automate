<script setup>
import { ref, watch, computed } from 'vue'
import SettingsField from './SettingsField.vue'

const props = defineProps({
  schema: { type: Object, default: () => ({}) },
  config: { type: Object, default: () => ({}) },
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
  // Filter out unchanged secrets
  const updates = {}
  for (const [key, value] of Object.entries(localConfig.value)) {
    if (value === '***configured***') continue
    updates[key] = value
  }
  emit('save', updates)
}

const sortedCategories = computed(() => {
  if (!props.schema?.categories || !props.schema?.params) return []
  const catMap = {}
  for (const param of props.schema.params) {
    const cat = param.category || 'other'
    if (!catMap[cat]) catMap[cat] = []
    catMap[cat].push(param)
  }
  return props.schema.categories
    .filter((c) => catMap[c.key]?.length > 0)
    .sort((a, b) => a.order - b.order)
    .map((c) => ({ ...c, params: catMap[c.key] }))
})

const hasChanges = computed(() => {
  return JSON.stringify(localConfig.value) !== JSON.stringify(props.config)
})
</script>

<template>
  <div class="space-y-6">
    <!-- Categories -->
    <div
      v-for="cat in sortedCategories"
      :key="cat.key"
      class="space-y-4"
    >
      <h3 class="text-sm font-semibold uppercase tracking-wider text-gray-400">
        {{ cat.label }}
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
