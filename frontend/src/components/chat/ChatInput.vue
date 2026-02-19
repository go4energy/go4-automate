<script setup>
import { ref, nextTick } from 'vue'

const props = defineProps({
  disabled: { type: Boolean, default: false },
  placeholder: { type: String, default: 'Nachricht eingeben...' }
})

const emit = defineEmits(['send'])

const message = ref('')
const textareaRef = ref(null)

function autoResize() {
  const el = textareaRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 150) + 'px'
}

function handleKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}

function send() {
  const text = message.value.trim()
  if (!text || props.disabled) return
  emit('send', text)
  message.value = ''
  nextTick(() => autoResize())
}
</script>

<template>
  <div class="flex items-end gap-2 border-t border-gray-200 bg-white p-3">
    <textarea
      ref="textareaRef"
      v-model="message"
      :placeholder="props.placeholder"
      :disabled="props.disabled"
      rows="1"
      class="flex-1 resize-none rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-800 placeholder-gray-400 outline-none transition focus:border-[#00865a] focus:bg-white focus:ring-1 focus:ring-[#00865a] disabled:opacity-50"
      @input="autoResize"
      @keydown="handleKeydown"
    />
    <button
      :disabled="!message.trim() || props.disabled"
      class="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-[#00865a] text-white transition hover:bg-[#006d49] disabled:opacity-40 disabled:hover:bg-[#00865a]"
      @click="send"
    >
      <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5"
        />
      </svg>
    </button>
  </div>
</template>
