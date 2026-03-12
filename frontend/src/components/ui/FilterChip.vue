<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: String, default: null }
})

const emit = defineEmits(['remove'])

function remove() {
  emit('remove')
}
</script>

<template>
  <span
    class="inline-flex items-center gap-1 rounded-full bg-go4-primary/10 px-3 py-1 text-sm text-go4-primary"
  >
    <span class="font-medium">{{ label }}:</span>
    <span>{{ value }}</span>
    <button
      type="button"
      class="ml-1 rounded-full p-0.5 hover:bg-go4-primary/20"
      @click="remove"
    >
      <svg
        class="h-3.5 w-3.5"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M6 18L18 6M6 6l12 12"
        />
      </svg>
    </button>
  </span>
</template>
