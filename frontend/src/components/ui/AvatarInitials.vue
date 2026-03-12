<script setup>
import { computed } from 'vue'

const props = defineProps({
  name: { type: String, default: '' },
  imageUrl: { type: String, default: null },
  size: {
    type: String,
    default: 'md',
    validator: (v) => ['xs', 'sm', 'md', 'lg', 'xl'].includes(v)
  },
  color: { type: String, default: null }
})

const initials = computed(() => {
  if (!props.name) return '?'
  const parts = props.name.trim().split(/\s+/)
  if (parts.length === 1) {
    return parts[0].substring(0, 2).toUpperCase()
  }
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
})

const sizeClasses = {
  xs: 'h-6 w-6 text-xs',
  sm: 'h-8 w-8 text-sm',
  md: 'h-10 w-10 text-sm',
  lg: 'h-12 w-12 text-base',
  xl: 'h-16 w-16 text-lg'
}

const colors = [
  'bg-blue-500',
  'bg-green-500',
  'bg-yellow-500',
  'bg-red-500',
  'bg-purple-500',
  'bg-pink-500',
  'bg-indigo-500',
  'bg-teal-500'
]

const bgColor = computed(() => {
  if (props.color) return props.color
  if (!props.name) return colors[0]
  const hash = props.name.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)
  return colors[hash % colors.length]
})
</script>

<template>
  <div
    class="inline-flex flex-shrink-0 items-center justify-center rounded-full font-medium text-white"
    :class="[sizeClasses[size], !imageUrl ? bgColor : '']"
  >
    <img
      v-if="imageUrl"
      :src="imageUrl"
      :alt="name"
      class="h-full w-full rounded-full object-cover"
    >
    <span v-else>{{ initials }}</span>
  </div>
</template>
