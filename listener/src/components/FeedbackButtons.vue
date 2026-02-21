<script setup>
import { ref } from 'vue'
import { useFeedbackStore } from '@/stores/feedback'

const props = defineProps({
  episodeId: { type: Number, required: true },
  findingId: { type: Number, default: null }
})

const feedback = useFeedbackStore()
const submitted = ref(null)
const loading = ref(false)

async function rate(rating) {
  if (submitted.value !== null) return
  loading.value = true
  try {
    await feedback.submitFeedback(props.episodeId, rating, props.findingId)
    submitted.value = rating
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="flex items-center justify-center gap-4">
    <p class="text-sm text-gray-500">War dieses Briefing hilfreich?</p>
    <div class="flex gap-2">
      <button
        :disabled="loading || submitted !== null"
        class="rounded-full p-2 transition-colors"
        :class="
          submitted === 1
            ? 'bg-green-100 text-green-600'
            : 'bg-gray-100 text-gray-500 hover:bg-green-50 hover:text-green-600'
        "
        @click="rate(1)"
      >
        <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5"
          />
        </svg>
      </button>
      <button
        :disabled="loading || submitted !== null"
        class="rounded-full p-2 transition-colors"
        :class="
          submitted === -1
            ? 'bg-red-100 text-red-600'
            : 'bg-gray-100 text-gray-500 hover:bg-red-50 hover:text-red-600'
        "
        @click="rate(-1)"
      >
        <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018c.163 0 .326.02.485.06L17 4m-7 10v2a3.5 3.5 0 003.5 3.5h.792c.413 0 .747-.335.747-.747 0-.592.174-1.171.5-1.664L17 13V4m-7 10h2m5-6h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5"
          />
        </svg>
      </button>
    </div>
    <p v-if="submitted !== null" class="text-sm text-green-600">Danke!</p>
  </div>
</template>
