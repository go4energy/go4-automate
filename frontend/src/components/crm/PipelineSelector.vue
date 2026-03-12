<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  pipelines: { type: Array, required: true },
  modelValue: { type: [Number, null], default: null }
})

const emit = defineEmits(['update:modelValue'])

const isOpen = ref(false)

const selectedPipeline = computed(() => {
  return props.pipelines.find((p) => p.id === props.modelValue)
})

function select(pipeline) {
  emit('update:modelValue', pipeline.id)
  isOpen.value = false
}

function toggle() {
  isOpen.value = !isOpen.value
}

function close() {
  isOpen.value = false
}
</script>

<template>
  <div class="relative">
    <button
      type="button"
      class="flex items-center gap-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-600"
      @click="toggle"
    >
      <span>{{ selectedPipeline?.name || 'Pipeline wählen' }}</span>
      <svg
        class="h-4 w-4 transition-transform"
        :class="{ 'rotate-180': isOpen }"
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

    <Transition
      enter-active-class="transition duration-100 ease-out"
      enter-from-class="transform scale-95 opacity-0"
      enter-to-class="transform scale-100 opacity-100"
      leave-active-class="transition duration-75 ease-in"
      leave-from-class="transform scale-100 opacity-100"
      leave-to-class="transform scale-95 opacity-0"
    >
      <div
        v-if="isOpen"
        class="absolute left-0 top-full mt-1 w-56 rounded-lg bg-white dark:bg-gray-800 shadow-lg border border-gray-200 dark:border-gray-700 z-10"
        @click.stop
      >
        <div class="py-1">
          <button
            v-for="pipeline in pipelines"
            :key="pipeline.id"
            type="button"
            class="flex w-full items-center justify-between px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700"
            :class="{ 'bg-go4-primary/10': pipeline.id === modelValue }"
            @click="select(pipeline)"
          >
            <span>{{ pipeline.name }}</span>
            <span class="text-xs text-gray-400">{{ pipeline.deal_count }} Deals</span>
          </button>
        </div>
      </div>
    </Transition>

    <!-- Click outside handler -->
    <div
      v-if="isOpen"
      class="fixed inset-0 z-0"
      @click="close"
    />
  </div>
</template>
