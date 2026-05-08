import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import {
  createConversation as apiCreateConversation,
  listConversations as apiListConversations,
  getConversation as apiGetConversation,
  deleteConversation as apiDeleteConversation,
  sendMessage as apiSendMessage,
  listTopics as apiListTopics
} from '@/api/chat'
import { useLayoutStore } from '@/stores/layout'

export const useChatStore = defineStore('chat', () => {
  const conversations = ref([])
  const activeConversation = ref(null)
  const streamingMessage = ref('')
  const isStreaming = ref(false)
  const loading = ref(false)
  const error = ref(null)
  const topicRegistry = ref({}) // { topic_id: title }

  const unreadCount = computed(() => 0)

  async function fetchTopics() {
    try {
      const { data } = await apiListTopics()
      const map = {}
      for (const t of data) map[t.id] = t.title
      topicRegistry.value = map
    } catch {
      // non-critical — fallback uses page-supplied titles
    }
  }

  /** Open the chat for a help-topic. Reuses an existing topic-conversation
   * (backend dedups) and forces the panel open so the user lands directly
   * in the conversation. */
  async function startTopicConversation(topic, { context = null, title = null } = {}) {
    error.value = null
    try {
      const { data } = await apiCreateConversation({
        title,
        context_type: 'help',
        context_data: context,
        topic
      })
      // Replace-or-prepend in list
      const idx = conversations.value.findIndex((c) => c.id === data.id)
      if (idx >= 0) conversations.value.splice(idx, 1)
      conversations.value.unshift(data)
      // Reload full conversation (with messages) so prior history shows up.
      const { data: full } = await apiGetConversation(data.id)
      activeConversation.value = full
      const layout = useLayoutStore()
      if (!layout.chatOpen) layout.toggleChat()
      return full
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      return null
    }
  }

  async function fetchConversations() {
    loading.value = true
    error.value = null
    try {
      const { data } = await apiListConversations()
      conversations.value = data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
    } finally {
      loading.value = false
    }
  }

  async function createConversation(contextType = 'general') {
    error.value = null
    try {
      const { data } = await apiCreateConversation({ context_type: contextType })
      conversations.value.unshift(data)
      activeConversation.value = data
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      return null
    }
  }

  async function openConversation(convId) {
    loading.value = true
    error.value = null
    try {
      const { data } = await apiGetConversation(convId)
      activeConversation.value = data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
    } finally {
      loading.value = false
    }
  }

  async function removeConversation(convId) {
    error.value = null
    // Optimistic remove — drop from list immediately for snappy UI.
    const previous = conversations.value
    conversations.value = previous.filter((c) => c.id !== convId)
    if (activeConversation.value?.id === convId) {
      activeConversation.value = null
    }
    try {
      await apiDeleteConversation(convId)
    } catch (err) {
      const status = err.response?.status
      // 404 = already gone server-side (stale list) — keep it removed.
      if (status === 404) return
      // Real error: restore item + surface error.
      conversations.value = previous
      error.value = err.response?.data?.detail || err.message
    }
  }

  async function sendMessage(content) {
    if (!activeConversation.value || isStreaming.value) return

    const convId = activeConversation.value.id

    // Add user message locally
    const userMsg = {
      id: Date.now(),
      role: 'user',
      content,
      created_at: new Date().toISOString()
    }
    if (!activeConversation.value.messages) {
      activeConversation.value.messages = []
    }
    activeConversation.value.messages.push(userMsg)

    // Auto-title from first message
    if (!activeConversation.value.title) {
      activeConversation.value.title =
        content.length > 80 ? content.substring(0, 80) + '...' : content
    }

    // Start streaming
    isStreaming.value = true
    streamingMessage.value = ''
    error.value = null

    try {
      const response = await apiSendMessage(convId, content)
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const jsonStr = line.slice(6).trim()
          if (!jsonStr) continue

          try {
            const data = JSON.parse(jsonStr)
            if (data.delta) {
              streamingMessage.value += data.delta
            } else if (data.done) {
              // Push completed assistant message
              activeConversation.value.messages.push({
                id: data.message_id,
                role: 'assistant',
                content: streamingMessage.value,
                created_at: new Date().toISOString()
              })
              streamingMessage.value = ''
            } else if (data.error) {
              error.value = data.error
            }
          } catch {
            // Skip malformed JSON
          }
        }
      }
    } catch (err) {
      error.value = err.message || 'Verbindungsfehler'
    } finally {
      isStreaming.value = false
      if (streamingMessage.value) {
        // If stream ended without done event, push what we have
        activeConversation.value.messages.push({
          id: Date.now(),
          role: 'assistant',
          content: streamingMessage.value,
          created_at: new Date().toISOString()
        })
        streamingMessage.value = ''
      }
    }
  }

  function goBack() {
    activeConversation.value = null
  }

  return {
    conversations,
    activeConversation,
    streamingMessage,
    isStreaming,
    loading,
    error,
    unreadCount,
    topicRegistry,
    fetchConversations,
    fetchTopics,
    createConversation,
    openConversation,
    removeConversation,
    sendMessage,
    startTopicConversation,
    goBack
  }
})
