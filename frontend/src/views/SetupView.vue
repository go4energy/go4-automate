<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'
import { useSetupStore } from '@/stores/setup'
import ChatMessage from '@/components/chat/ChatMessage.vue'
import ChatInput from '@/components/chat/ChatInput.vue'
import ToolCallCard from '@/components/setup/ToolCallCard.vue'
import SetupProgress from '@/components/setup/SetupProgress.vue'

const store = useSetupStore()
const messagesContainer = ref(null)

const quickActions = [
  {
    label: 'Frisches Setup',
    message: 'Ich moechte ein frisches Setup starten. Bitte fuehre mich durch alle Module.'
  },
  { label: 'Research einrichten', message: 'Ich moechte meine Research-Quellen konfigurieren.' },
  { label: 'Content anpassen', message: 'Ich moechte meine Content-Strategie anpassen.' },
  {
    label: 'Integrationen pruefen',
    message: 'Bitte pruefe welche Integrationen konfiguriert sind.'
  }
]

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

watch(() => store.streamingMessage, scrollToBottom)
watch(() => store.activeConversation?.messages?.length, scrollToBottom)

async function handleStartSetup() {
  await store.startSetup()
}

async function handleSend(content) {
  if (!store.activeConversation) {
    await store.startSetup()
  }
  await store.sendMessage(content)
}

function handleQuickAction(action) {
  handleSend(action.message)
}

async function handleDeleteConversation(convId) {
  await store.removeConversation(convId)
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleDateString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

onMounted(() => {
  store.fetchConversations()
  store.fetchStatus()
})
</script>

<template>
  <div class="-m-6 flex h-[calc(100vh-4rem)]">
    <!-- Left Sidebar -->
    <div
      class="flex w-72 shrink-0 flex-col border-r border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50"
    >
      <!-- New session button -->
      <div class="border-b border-gray-200 dark:border-gray-700 p-4">
        <button
          class="flex w-full items-center justify-center gap-2 rounded-lg bg-[#00865a] px-4 py-2.5 text-sm font-medium text-white transition hover:bg-[#006d49]"
          @click="handleStartSetup"
        >
          <svg
            class="h-4 w-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          Neue Session
        </button>
      </div>

      <!-- Conversation list -->
      <div class="flex-1 overflow-y-auto p-2">
        <p
          v-if="store.conversations.length"
          class="mb-2 px-2 text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500"
        >
          Sessions
        </p>
        <div class="space-y-1">
          <div
            v-for="conv in store.conversations"
            :key="conv.id"
            class="group flex cursor-pointer items-center gap-2 rounded-lg px-3 py-2 text-sm transition"
            :class="
              store.activeConversation?.id === conv.id
                ? 'bg-[#00865a]/10 text-[#00865a]'
                : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
            "
            @click="store.openConversation(conv.id)"
          >
            <svg
              class="h-4 w-4 shrink-0"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="1.5"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z"
              />
            </svg>
            <span class="flex-1 truncate">{{ conv.title || 'Neue Session' }}</span>
            <button
              class="hidden shrink-0 rounded p-0.5 text-gray-400 dark:text-gray-500 hover:bg-gray-200 dark:hover:bg-gray-600 hover:text-red-500 group-hover:block"
              @click.stop="handleDeleteConversation(conv.id)"
            >
              <svg
                class="h-3.5 w-3.5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2"
              >
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      <!-- Setup Progress -->
      <div class="border-t border-gray-200 dark:border-gray-700 p-4">
        <SetupProgress :status="store.setupStatus" />
      </div>
    </div>

    <!-- Right: Chat Area -->
    <div class="flex flex-1 flex-col">
      <!-- Messages -->
      <div
        ref="messagesContainer"
        class="flex-1 overflow-y-auto bg-gray-50 dark:bg-gray-800/50 p-6"
      >
        <!-- Empty state -->
        <div
          v-if="!store.activeConversation || !store.activeConversation.messages?.length"
          class="flex h-full flex-col items-center justify-center"
        >
          <div class="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-[#00865a]/10">
            <svg
              class="h-8 w-8 text-[#00865a]"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="1.5"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 010 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 010-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28z"
              />
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
              />
            </svg>
          </div>
          <h2 class="mb-2 text-lg font-semibold text-gray-800 dark:text-gray-200">Setup Wizard</h2>
          <p class="mb-6 max-w-md text-center text-sm text-gray-500 dark:text-gray-400">
            Konfiguriere deine Marketing-Plattform Schritt fuer Schritt. Der Assistent fuehrt dich
            durch alle Module.
          </p>
          <!-- Quick action chips -->
          <div class="flex flex-wrap justify-center gap-2">
            <button
              v-for="action in quickActions"
              :key="action.label"
              class="rounded-full border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 py-2 text-sm text-gray-600 dark:text-gray-300 shadow-sm transition hover:border-[#00865a] hover:text-[#00865a]"
              @click="handleQuickAction(action)"
            >
              {{ action.label }}
            </button>
          </div>
        </div>

        <!-- Messages list -->
        <div v-else class="mx-auto max-w-3xl space-y-4">
          <template v-for="msg in store.activeConversation.messages" :key="msg.id">
            <ChatMessage :message="msg" />
            <!-- Tool calls from metadata -->
            <template v-if="msg.metadata_?.toolCalls?.length">
              <ToolCallCard
                v-for="(tc, i) in msg.metadata_.toolCalls"
                :key="`${msg.id}-tc-${i}`"
                :tool-call="tc"
              />
            </template>
          </template>

          <!-- Streaming message -->
          <template v-if="store.isStreaming">
            <!-- Active tool calls -->
            <ToolCallCard
              v-for="(tc, i) in store.toolCalls"
              :key="`stream-tc-${i}`"
              :tool-call="tc"
            />
            <!-- Streaming text -->
            <ChatMessage
              v-if="store.streamingMessage"
              :message="{ role: 'assistant', content: store.streamingMessage }"
              :is-streaming="true"
            />
          </template>
        </div>
      </div>

      <!-- Quick actions when conversation is active but no streaming -->
      <div
        v-if="
          store.activeConversation &&
          !store.isStreaming &&
          store.activeConversation.messages?.length
        "
        class="flex gap-2 border-t border-gray-100 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 py-2"
      >
        <button
          v-for="action in quickActions"
          :key="action.label"
          class="rounded-full border border-gray-200 dark:border-gray-700 px-3 py-1 text-xs text-gray-500 dark:text-gray-400 transition hover:border-[#00865a] hover:text-[#00865a]"
          @click="handleQuickAction(action)"
        >
          {{ action.label }}
        </button>
      </div>

      <!-- Error -->
      <div
        v-if="store.error"
        class="border-t border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 px-4 py-2 text-sm text-red-600 dark:text-red-400"
      >
        {{ store.error }}
      </div>

      <!-- Input -->
      <ChatInput
        :disabled="store.isStreaming"
        placeholder="Nachricht an den Setup-Assistenten..."
        @send="handleSend"
      />
    </div>
  </div>
</template>
