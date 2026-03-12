<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  columns: {
    type: Array,
    required: true
    // { key: string, label: string, sortable?: boolean, class?: string, headerClass?: string }
  },
  data: { type: Array, required: true },
  sortKey: { type: String, default: null },
  sortDirection: { type: String, default: 'asc' },
  selectable: { type: Boolean, default: false },
  selectedIds: { type: Array, default: () => [] },
  idKey: { type: String, default: 'id' },
  loading: { type: Boolean, default: false },
  emptyMessage: { type: String, default: 'Keine Daten vorhanden' }
})

const emit = defineEmits(['sort', 'select', 'selectAll', 'rowClick'])

const allSelected = computed(() => {
  if (props.data.length === 0) return false
  return props.data.every((row) => props.selectedIds.includes(row[props.idKey]))
})

const someSelected = computed(() => {
  if (props.data.length === 0) return false
  const selected = props.data.filter((row) => props.selectedIds.includes(row[props.idKey]))
  return selected.length > 0 && selected.length < props.data.length
})

function toggleSort(column) {
  if (!column.sortable) return
  const newDirection =
    props.sortKey === column.key && props.sortDirection === 'asc' ? 'desc' : 'asc'
  emit('sort', { key: column.key, direction: newDirection })
}

function toggleSelectAll() {
  emit('selectAll', !allSelected.value)
}

function toggleSelect(row) {
  const id = row[props.idKey]
  const isSelected = props.selectedIds.includes(id)
  emit('select', { id, selected: !isSelected })
}

function onRowClick(row) {
  emit('rowClick', row)
}
</script>

<template>
  <div class="overflow-hidden rounded-lg bg-white dark:bg-gray-800 shadow-sm">
    <div class="overflow-x-auto">
      <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
        <thead class="bg-gray-50 dark:bg-gray-800/50">
          <tr>
            <th
              v-if="selectable"
              class="w-12 px-4 py-3"
            >
              <input
                type="checkbox"
                :checked="allSelected"
                :indeterminate="someSelected"
                class="h-4 w-4 rounded border-gray-300 text-go4-primary focus:ring-go4-primary"
                @change="toggleSelectAll"
              >
            </th>
            <th
              v-for="column in columns"
              :key="column.key"
              class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-go4-muted dark:text-gray-400"
              :class="[column.headerClass, { 'cursor-pointer select-none': column.sortable }]"
              @click="toggleSort(column)"
            >
              <div class="flex items-center gap-1">
                <span>{{ column.label }}</span>
                <template v-if="column.sortable">
                  <svg
                    v-if="sortKey === column.key"
                    class="h-4 w-4"
                    :class="{ 'rotate-180': sortDirection === 'desc' }"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M5 15l7-7 7 7"
                    />
                  </svg>
                  <svg
                    v-else
                    class="h-4 w-4 text-gray-300 dark:text-gray-600"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4"
                    />
                  </svg>
                </template>
              </div>
            </th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-200 dark:divide-gray-700 bg-white dark:bg-gray-800">
          <tr v-if="loading">
            <td
              :colspan="columns.length + (selectable ? 1 : 0)"
              class="px-6 py-8 text-center text-go4-muted dark:text-gray-400"
            >
              Laden...
            </td>
          </tr>
          <tr v-else-if="data.length === 0">
            <td
              :colspan="columns.length + (selectable ? 1 : 0)"
              class="px-6 py-8 text-center text-go4-muted dark:text-gray-400"
            >
              {{ emptyMessage }}
            </td>
          </tr>
          <tr
            v-for="row in data"
            v-else
            :key="row[idKey]"
            class="hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer"
            @click="onRowClick(row)"
          >
            <td
              v-if="selectable"
              class="w-12 px-4 py-4"
              @click.stop
            >
              <input
                type="checkbox"
                :checked="selectedIds.includes(row[idKey])"
                class="h-4 w-4 rounded border-gray-300 text-go4-primary focus:ring-go4-primary"
                @change="toggleSelect(row)"
              >
            </td>
            <td
              v-for="column in columns"
              :key="column.key"
              class="whitespace-nowrap px-6 py-4 text-sm text-gray-900 dark:text-gray-100"
              :class="column.class"
            >
              <slot
                :name="`cell-${column.key}`"
                :row="row"
                :value="row[column.key]"
              >
                {{ row[column.key] }}
              </slot>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
