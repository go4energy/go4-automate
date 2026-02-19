<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: { type: String, required: true },
  size: { type: String, default: 'sm' }
})

const statusColors = {
  draft: 'bg-yellow-100 text-yellow-800',
  scheduled: 'bg-blue-100 text-blue-800',
  published: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
  active: 'bg-green-100 text-green-800',
  paused: 'bg-gray-100 text-gray-600',
  inactive: 'bg-gray-100 text-gray-600',
  new: 'bg-gray-100 text-gray-800',
  contacted: 'bg-blue-100 text-blue-800',
  qualified: 'bg-indigo-100 text-indigo-800',
  converted: 'bg-green-100 text-green-800',
  lost: 'bg-red-100 text-red-800',
  suggested: 'bg-yellow-100 text-yellow-800',
  approved: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
  generating: 'bg-blue-100 text-blue-800',
  generated: 'bg-emerald-100 text-emerald-800',
  reviewed: 'bg-blue-100 text-blue-800',
  used: 'bg-green-100 text-green-800',
  dismissed: 'bg-red-100 text-red-800',
  info: 'bg-blue-100 text-blue-800',
  success: 'bg-green-100 text-green-800',
  warning: 'bg-yellow-100 text-yellow-800',
  error: 'bg-red-100 text-red-800'
}

const colorClass = computed(() => statusColors[props.status] || 'bg-gray-100 text-gray-800')
const sizeClass = computed(() =>
  props.size === 'xs' ? 'px-1.5 py-0.5 text-[10px]' : 'px-2.5 py-0.5 text-xs'
)
</script>

<template>
  <span :class="['inline-flex items-center rounded-full font-medium', colorClass, sizeClass]">
    {{ status }}
  </span>
</template>
