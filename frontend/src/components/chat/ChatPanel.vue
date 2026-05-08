<script setup>
import { ref, watch, nextTick, onMounted, computed } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useLayoutStore } from '@/stores/layout'
import { usePageTopics } from '@/stores/pageTopics'
import ChatMessage from './ChatMessage.vue'
import ChatInput from './ChatInput.vue'

const chatStore = useChatStore()
const layoutStore = useLayoutStore()
const pageTopics = usePageTopics()
const messagesContainer = ref(null)
const showNewMenu = ref(false)

const contextTypes = [
  { value: 'general', label: 'Allgemein', icon: '💬' },
  { value: 'onboarding', label: 'Onboarding', icon: '🚀' },
  { value: 'research', label: 'Research', icon: '🔍' },
  { value: 'content', label: 'Content', icon: '📝' }
]

const showPageTopics = computed(
  () => !chatStore.activeConversation && pageTopics.topics.length > 0
)

onMounted(() => {
  chatStore.fetchConversations()
  chatStore.fetchTopics()
})

async function startTopic(t) {
  await chatStore.startTopicConversation(t.topic, {
    context: t.context,
    title: t.title ? `💡 ${t.title}` : null
  })
}

function confirmDelete(conv) {
  chatStore.removeConversation(conv.id)
}

function scrollToBottom() {
  nextTick(() => {
    const el = messagesContainer.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

watch(
  () => chatStore.activeConversation?.messages?.length,
  () => scrollToBottom()
)

watch(
  () => chatStore.streamingMessage,
  () => scrollToBottom()
)

async function startConversation(contextType) {
  showNewMenu.value = false
  await chatStore.createConversation(contextType)
}

async function handleSend(content) {
  await chatStore.sendMessage(content)
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const now = new Date()
  const diff = now - d
  if (diff < 60000) return 'Gerade eben'
  if (diff < 3600000) return `vor ${Math.floor(diff / 60000)} Min.`
  if (diff < 86400000) return `vor ${Math.floor(diff / 3600000)} Std.`
  return d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit' })
}
</script>

<template>
  <Transition name="slide">
    <div
      v-if="layoutStore.chatOpen"
      class="fixed right-0 top-0 z-50 flex h-full w-full flex-col border-l border-gray-200 bg-gray-50 shadow-xl sm:w-[400px] dark:border-gray-700 dark:bg-gray-900"
    >
      <!-- Header -->
      <div
        class="flex items-center justify-between border-b border-gray-200 bg-white px-4 py-3 dark:border-gray-700 dark:bg-gray-800"
      >
        <div class="flex items-center gap-2">
          <button
            v-if="chatStore.activeConversation"
            class="rounded-lg p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700 dark:hover:text-gray-300"
            @click="chatStore.goBack()"
          >
            <svg
              class="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="2"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M15 19l-7-7 7-7"
              />
            </svg>
          </button>
          <h2 class="text-sm font-semibold text-gray-800 dark:text-gray-200">
            {{
              chatStore.activeConversation
                ? chatStore.activeConversation.title || 'Neues Gespraech'
                : 'Chat'
            }}
          </h2>
        </div>
        <div class="flex items-center gap-1">
          <!-- Trash: delete the active conversation incl. history -->
          <button
            v-if="chatStore.activeConversation"
            class="rounded-lg p-1.5 text-gray-400 transition hover:bg-red-50 hover:text-red-500 dark:hover:bg-red-900/20 dark:hover:text-red-400"
            title="Chat löschen"
            @click="confirmDelete(chatStore.activeConversation)"
          >
            <svg
              class="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="1.5"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0"
              />
            </svg>
          </button>
          <div
            v-if="!chatStore.activeConversation"
            class="relative"
          >
            <button
              class="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700 dark:hover:text-gray-300"
              @click="showNewMenu = !showNewMenu"
            >
              <svg
                class="h-5 w-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M12 4v16m8-8H4"
                />
              </svg>
            </button>
            <!-- Context type menu -->
            <div
              v-if="showNewMenu"
              class="absolute right-0 top-full z-10 mt-1 w-48 rounded-lg border border-gray-200 bg-white py-1 shadow-lg dark:border-gray-600 dark:bg-gray-800"
            >
              <button
                v-for="ct in contextTypes"
                :key="ct.value"
                class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-700"
                @click="startConversation(ct.value)"
              >
                <span>{{ ct.icon }}</span>
                <span>{{ ct.label }}</span>
              </button>
            </div>
          </div>
          <button
            class="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700 dark:hover:text-gray-300"
            @click="layoutStore.toggleChat()"
          >
            <svg
              class="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="2"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>
      </div>

      <!-- Page-Help Topic Banner: shown when the active screen has registered topics -->
      <div
        v-if="showPageTopics"
        class="border-b border-emerald-200 bg-emerald-50/70 px-4 py-3 dark:border-emerald-800/40 dark:bg-emerald-900/10"
      >
        <p class="mb-2 text-xs font-semibold uppercase tracking-wide text-emerald-700 dark:text-emerald-300">
          💡 Hilfe verfügbar zu dieser Seite
        </p>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="t in pageTopics.topics"
            :key="t.topic"
            type="button"
            class="rounded-full border border-emerald-300 bg-white px-3 py-1 text-xs font-medium text-emerald-800 shadow-sm transition hover:bg-emerald-50 dark:border-emerald-700/60 dark:bg-gray-800 dark:text-emerald-200 dark:hover:bg-emerald-900/30"
            @click="startTopic(t)"
          >
            {{ t.title }}
          </button>
        </div>
      </div>

      <!-- Conversation List -->
      <div
        v-if="!chatStore.activeConversation"
        class="flex-1 overflow-y-auto"
      >
        <div
          v-if="chatStore.loading"
          class="flex items-center justify-center p-8"
        >
          <span class="text-sm text-gray-500 dark:text-gray-400">Laden...</span>
        </div>
        <div
          v-else-if="chatStore.conversations.length === 0"
          class="flex flex-col items-center justify-center p-8 text-center"
        >
          <svg
            class="mb-3 h-12 w-12 text-gray-300 dark:text-gray-600"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="1"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
            />
          </svg>
          <p class="mb-1 text-sm font-medium text-gray-600 dark:text-gray-300">
            Keine Gespraeche
          </p>
          <p class="mb-4 text-xs text-gray-400 dark:text-gray-500">
            Starte ein neues Gespraech
          </p>
          <button
            class="rounded-lg bg-[#00865a] px-4 py-2 text-sm font-medium text-white hover:bg-[#006d49]"
            @click="startConversation('general')"
          >
            Neues Gespraech
          </button>
        </div>
        <div v-else>
          <div
            v-for="conv in chatStore.conversations"
            :key="conv.id"
            class="group relative flex items-start gap-3 border-b border-gray-100 px-4 py-3 transition hover:bg-white dark:border-gray-700/50 dark:hover:bg-gray-800"
          >
            <button
              type="button"
              class="flex flex-1 min-w-0 flex-col text-left"
              @click="chatStore.openConversation(conv.id)"
            >
              <p class="truncate text-sm font-medium text-gray-800 dark:text-gray-200">
                {{ conv.title || 'Neues Gespraech' }}
              </p>
              <p
                v-if="conv.last_message_preview"
                class="mt-0.5 truncate text-xs text-gray-400 dark:text-gray-500"
              >
                {{ conv.last_message_preview }}
              </p>
            </button>
            <div class="flex flex-col items-end gap-1">
              <div class="flex items-center gap-1.5 text-xs text-gray-400 dark:text-gray-500">
                <span>{{ formatDate(conv.created_at) }}</span>
                <button
                  type="button"
                  class="relative z-10 -m-1 rounded p-1 text-gray-300 transition hover:text-red-500 dark:text-gray-600 dark:hover:text-red-400"
                  title="Chat löschen"
                  @click.stop.prevent="confirmDelete(conv)"
                >
                  <svg
                    class="h-3.5 w-3.5"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2.5"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              </div>
              <span
                class="rounded-full bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-500 dark:bg-gray-700 dark:text-gray-400"
              >
                {{ conv.topic ? '💡 Hilfe' : conv.context_type }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Active Conversation -->
      <template v-else>
        <div
          ref="messagesContainer"
          class="flex-1 overflow-y-auto px-4 py-4"
        >
          <div
            v-if="!chatStore.activeConversation.messages?.length && !chatStore.isStreaming"
            class="flex flex-col items-center justify-center py-12 text-center"
          >
            <p class="mb-1 text-sm text-gray-500 dark:text-gray-400">
              Wie kann ich dir helfen?
            </p>
            <p class="mb-4 text-xs text-gray-400 dark:text-gray-500">
              Schreibe eine Nachricht um zu starten
            </p>
            <!-- Suggestions: prefer topic-suggestions of the matching page-topic -->
            <div
              v-if="
                pageTopics.topics.find(
                  (t) => t.topic === chatStore.activeConversation.topic,
                )?.suggestions?.length
              "
              class="flex w-full max-w-sm flex-col gap-2"
            >
              <button
                v-for="s in pageTopics.topics.find(
                  (t) => t.topic === chatStore.activeConversation.topic,
                ).suggestions"
                :key="s"
                type="button"
                class="rounded-lg border border-gray-200 bg-white px-3 py-2 text-left text-xs text-gray-700 transition hover:border-emerald-300 hover:bg-emerald-50 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200 dark:hover:border-emerald-700/60 dark:hover:bg-emerald-900/20"
                :disabled="chatStore.isStreaming"
                @click="handleSend(s)"
              >
                {{ s }}
              </button>
            </div>
          </div>
          <div
            v-else
            class="space-y-3"
          >
            <ChatMessage
              v-for="msg in chatStore.activeConversation.messages"
              :key="msg.id"
              :message="msg"
            />
            <!-- Streaming message -->
            <ChatMessage
              v-if="chatStore.isStreaming && chatStore.streamingMessage"
              :message="{
                role: 'assistant',
                content: chatStore.streamingMessage,
                created_at: null
              }"
              :is-streaming="true"
            />
          </div>
        </div>

        <!-- Error -->
        <div
          v-if="chatStore.error"
          class="border-t border-red-100 bg-red-50 px-4 py-2 dark:border-red-900/50 dark:bg-red-900/20"
        >
          <p class="text-xs text-red-600 dark:text-red-400">
            {{ chatStore.error }}
          </p>
        </div>

        <!-- Input -->
        <ChatInput
          :disabled="chatStore.isStreaming"
          @send="handleSend"
        />
      </template>
    </div>
  </Transition>
</template>
