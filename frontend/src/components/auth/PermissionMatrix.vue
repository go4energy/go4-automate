<script setup>
import { computed } from 'vue'

const props = defineProps({
  permissions: { type: Object, default: () => ({}) },
  readonly: { type: Boolean, default: false }
})

const emit = defineEmits(['update'])

const modules = ['collector', 'creator', 'briefing', 'campaigns', 'crm', 'contacts']
const actions = ['view', 'edit', 'delete', 'settings']
const actionLabels = {
  view: 'Ansehen',
  edit: 'Bearbeiten',
  delete: 'Loeschen',
  settings: 'Einstellungen'
}
const moduleLabels = {
  collector: 'Collector',
  creator: 'Creator',
  briefing: 'Briefing',
  campaigns: 'Campaigns',
  crm: 'CRM',
  contacts: 'Kontakte'
}

const matrix = computed(() => {
  const result = {}
  for (const mod of modules) {
    result[mod] = {}
    for (const action of actions) {
      result[mod][action] = props.permissions?.[mod]?.[action] === true
    }
  }
  return result
})

function toggle(mod, action) {
  if (props.readonly) return
  const updated = JSON.parse(JSON.stringify(props.permissions || {}))
  if (!updated[mod]) updated[mod] = {}
  updated[mod][action] = !matrix.value[mod][action]
  emit('update', updated)
}
</script>

<template>
  <div class="overflow-x-auto">
    <table class="w-full text-sm">
      <thead>
        <tr class="border-b border-gray-200 dark:border-gray-700">
          <th class="py-2 pr-4 text-left font-medium text-gray-600 dark:text-gray-400">
            Modul
          </th>
          <th
            v-for="action in actions"
            :key="action"
            class="px-3 py-2 text-center font-medium text-gray-600 dark:text-gray-400"
          >
            {{ actionLabels[action] }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="mod in modules"
          :key="mod"
          class="border-b border-gray-100 dark:border-gray-700/50"
        >
          <td class="py-2.5 pr-4 font-medium text-gray-900 dark:text-gray-200">
            {{ moduleLabels[mod] }}
          </td>
          <td
            v-for="action in actions"
            :key="action"
            class="px-3 py-2.5 text-center"
          >
            <button
              type="button"
              :class="[
                'inline-flex h-5 w-5 items-center justify-center rounded border transition',
                matrix[mod][action]
                  ? 'border-go4-primary bg-go4-primary text-white'
                  : 'border-gray-300 bg-white dark:border-gray-600 dark:bg-gray-700',
                readonly ? 'cursor-default' : 'cursor-pointer hover:border-go4-primary'
              ]"
              @click="toggle(mod, action)"
            >
              <svg
                v-if="matrix[mod][action]"
                class="h-3.5 w-3.5"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="3"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M4.5 12.75l6 6 9-13.5"
                />
              </svg>
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
