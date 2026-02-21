<script setup>
const props = defineProps({
  message: { type: Object, required: true },
  isStreaming: { type: Boolean, default: false }
})

function formatTime(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <div class="flex" :class="props.message.role === 'user' ? 'justify-end' : 'justify-start'">
    <!-- System message -->
    <div v-if="props.message.role === 'system'" class="w-full text-center">
      <span class="inline-block rounded-full bg-gray-100 px-3 py-1 text-xs text-gray-500">
        {{ props.message.content }}
      </span>
    </div>

    <!-- User message -->
    <div v-else-if="props.message.role === 'user'" class="max-w-[80%]">
      <div class="rounded-2xl rounded-br-md bg-[#00865a] px-4 py-2.5 text-white">
        <p class="whitespace-pre-wrap text-sm">
          {{ props.message.content }}
        </p>
      </div>
      <p class="mt-1 text-right text-xs text-gray-400">
        {{ formatTime(props.message.created_at) }}
      </p>
    </div>

    <!-- Assistant message -->
    <div v-else class="max-w-[80%]">
      <div class="rounded-2xl rounded-bl-md bg-white px-4 py-2.5 shadow-sm ring-1 ring-gray-100">
        <p class="whitespace-pre-wrap text-sm text-gray-800">
          {{ props.message.content }}
        </p>
        <span
          v-if="props.isStreaming"
          class="ml-1 inline-block h-2 w-2 animate-pulse rounded-full bg-[#00865a]"
        />
      </div>
      <p class="mt-1 text-xs text-gray-400">
        {{ formatTime(props.message.created_at) }}
      </p>
    </div>
  </div>
</template>
