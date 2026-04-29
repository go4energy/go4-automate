<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useWhatsAppStore } from '@/stores/whatsapp'
import PageHeader from '@/components/ui/PageHeader.vue'

const props = defineProps({
  id: { type: [String, Number], required: true }
})

const router = useRouter()
const store = useWhatsAppStore()

const loading = ref(true)
const sending = ref(false)
const messageText = ref('')
const messagesContainer = ref(null)

const conversation = computed(() => store.currentConversation)
const messages = computed(() => store.currentConversation?.messages || [])

// Check if 24h window is open
const windowOpen = computed(() => {
  if (!conversation.value?.window_expires_at) return false
  return new Date(conversation.value.window_expires_at) > new Date()
})

// Format time
function formatTime(date) {
  if (!date) return ''
  return new Date(date).toLocaleTimeString('de-DE', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

function formatDate(date) {
  if (!date) return ''
  return new Date(date).toLocaleDateString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric'
  })
}

// Get message status icon
function getStatusIcon(status) {
  switch (status) {
    case 'pending':
      return 'clock'
    case 'sent':
      return 'check'
    case 'delivered':
      return 'check-double'
    case 'read':
      return 'check-double-blue'
    case 'failed':
      return 'x'
    default:
      return 'clock'
  }
}

// Scroll to bottom of messages
function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

// Send message
async function sendMessage() {
  if (!messageText.value.trim() || sending.value) return

  sending.value = true
  try {
    await store.sendConversationMessage(props.id, {
      message_type: 'text',
      text: { body: messageText.value.trim() }
    })
    messageText.value = ''
    scrollToBottom()
  } catch (err) {
    // Error handled by store
  } finally {
    sending.value = false
  }
}

// Handle enter key
function handleKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

// Mark as read when viewing
async function markAsRead() {
  if (conversation.value?.unread_count > 0) {
    await store.markRead(props.id)
  }
}

// Load data
async function loadData() {
  loading.value = true
  try {
    await store.fetchConversation(props.id)
    await markAsRead()
    scrollToBottom()
  } catch (err) {
    router.push({ name: 'whatsapp-inbox' })
  } finally {
    loading.value = false
  }
}

// Watch for new messages
watch(
  messages,
  () => {
    scrollToBottom()
  },
  { deep: true }
)

onMounted(() => {
  loadData()
})

onUnmounted(() => {
  store.clearCurrent()
})
</script>

<template>
  <div class="h-full flex flex-col">
    <!-- Loading -->
    <div
      v-if="loading"
      class="flex-1 flex items-center justify-center"
    >
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600" />
    </div>

    <template v-else-if="conversation">
      <!-- Header -->
      <div class="px-6 py-4 bg-white border-b flex items-center justify-between">
        <div class="flex items-center space-x-4">
          <div class="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
            <span class="text-green-700 font-medium text-lg">
              {{ (conversation.contact_name || conversation.phone)?.[0]?.toUpperCase() || '?' }}
            </span>
          </div>
          <div>
            <h2 class="font-semibold text-gray-900">
              {{ conversation.contact_name || conversation.phone }}
            </h2>
            <p class="text-sm text-gray-500">
              {{ conversation.phone }}
            </p>
          </div>
        </div>
        <div class="flex items-center space-x-4">
          <div
            v-if="windowOpen"
            class="flex items-center text-sm text-green-600"
          >
            <svg
              class="w-4 h-4 mr-1"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            24h-Fenster offen
          </div>
          <div
            v-else
            class="flex items-center text-sm text-gray-500"
          >
            <svg
              class="w-4 h-4 mr-1"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M12 15v2m0 0v2m0-2h2m-2 0H10m5-6a3 3 0 11-6 0 3 3 0 016 0z"
              />
            </svg>
            Nur Templates
          </div>
        </div>
      </div>

      <!-- Messages -->
      <div
        ref="messagesContainer"
        class="flex-1 overflow-y-auto p-6 space-y-4 bg-gray-50"
      >
        <div
          v-if="messages.length === 0"
          class="text-center text-gray-500 py-12"
        >
          Keine Nachrichten
        </div>

        <div
          v-for="(message, index) in messages"
          :key="message.id"
        >
          <!-- Date separator -->
          <div
            v-if="
              index === 0 ||
                formatDate(message.created_at) !== formatDate(messages[index - 1].created_at)
            "
            class="flex justify-center my-4"
          >
            <span class="bg-white px-3 py-1 rounded-full text-xs text-gray-500 shadow-sm">
              {{ formatDate(message.created_at) }}
            </span>
          </div>

          <!-- Message bubble -->
          <div
            :class="['flex', message.direction === 'outbound' ? 'justify-end' : 'justify-start']"
          >
            <div
              :class="[
                'max-w-[70%] rounded-lg px-4 py-2 shadow-sm',
                message.direction === 'outbound'
                  ? 'bg-green-500 text-white'
                  : 'bg-white text-gray-900'
              ]"
            >
              <!-- Template message -->
              <div
                v-if="message.message_type === 'template'"
                class="text-sm opacity-75 mb-1"
              >
                [Template: {{ message.template_name }}]
              </div>

              <!-- Text content -->
              <p
                v-if="message.content?.text?.body || message.content?.text"
                class="whitespace-pre-wrap break-words"
              >
                {{ message.content?.text?.body || message.content?.text }}
              </p>

              <!-- Media placeholder -->
              <div
                v-else-if="['image', 'document', 'audio', 'video'].includes(message.message_type)"
                class="flex items-center space-x-2"
              >
                <svg
                  class="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"
                  />
                </svg>
                <span>{{ message.message_type }}</span>
              </div>

              <!-- Timestamp and status -->
              <div
                :class="[
                  'flex items-center justify-end space-x-1 mt-1',
                  message.direction === 'outbound' ? 'text-green-100' : 'text-gray-400'
                ]"
              >
                <span class="text-xs">{{ formatTime(message.created_at) }}</span>
                <template v-if="message.direction === 'outbound'">
                  <svg
                    v-if="message.status === 'pending'"
                    class="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  <svg
                    v-else-if="message.status === 'sent'"
                    class="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  <svg
                    v-else-if="message.status === 'delivered'"
                    class="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  <svg
                    v-else-if="message.status === 'read'"
                    class="w-4 h-4 text-blue-300"
                    fill="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z" />
                  </svg>
                  <svg
                    v-else-if="message.status === 'failed'"
                    class="w-4 h-4 text-red-300"
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
                </template>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Input area -->
      <div class="px-6 py-4 bg-white border-t">
        <div
          v-if="!windowOpen"
          class="mb-3 p-3 bg-yellow-50 rounded-lg text-sm text-yellow-700"
        >
          Das 24h-Fenster ist abgelaufen. Sie können nur noch Template-Nachrichten senden.
        </div>
        <div class="flex items-end space-x-4">
          <textarea
            v-model="messageText"
            rows="1"
            class="flex-1 input resize-none"
            placeholder="Nachricht schreiben..."
            :disabled="!windowOpen || sending"
            @keydown="handleKeydown"
          />
          <button
            class="btn btn-primary px-4 py-2"
            :disabled="!messageText.trim() || !windowOpen || sending"
            @click="sendMessage"
          >
            <svg
              v-if="sending"
              class="animate-spin w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <circle
                class="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                stroke-width="4"
              />
              <path
                class="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            <svg
              v-else
              class="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
              />
            </svg>
          </button>
        </div>
      </div>
    </template>
  </div>
</template>
