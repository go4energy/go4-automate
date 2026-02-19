import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import {
  createSetupConversation as apiCreate,
  listSetupConversations as apiList,
  getSetupConversation as apiGet,
  deleteSetupConversation as apiDelete,
  sendSetupMessage as apiSend,
  getSetupStatus as apiStatus
} from '@/api/setup'

export const useSetupStore = defineStore('setup', () => {
  const conversations = ref([])
  const activeConversation = ref(null)
  const streamingMessage = ref('')
  const isStreaming = ref(false)
  const toolCalls = ref([])
  const loading = ref(false)
  const error = ref(null)
  const setupStatus = ref(null)

  const completedSteps = computed(() => {
    if (!setupStatus.value?.modules) return 0
    return Object.values(setupStatus.value.modules).filter((m) => m.configured).length
  })

  const totalSteps = computed(() => {
    if (!setupStatus.value?.modules) return 5
    return Object.keys(setupStatus.value.modules).length
  })

  async function fetchStatus() {
    try {
      const { data } = await apiStatus()
      setupStatus.value = data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
    }
  }

  async function fetchConversations() {
    loading.value = true
    error.value = null
    try {
      const { data } = await apiList()
      conversations.value = data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
    } finally {
      loading.value = false
    }
  }

  async function startSetup() {
    error.value = null
    try {
      const { data } = await apiCreate()
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
      const { data } = await apiGet(convId)
      activeConversation.value = data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
    } finally {
      loading.value = false
    }
  }

  async function removeConversation(convId) {
    error.value = null
    try {
      await apiDelete(convId)
      conversations.value = conversations.value.filter((c) => c.id !== convId)
      if (activeConversation.value?.id === convId) {
        activeConversation.value = null
      }
    } catch (err) {
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

    // Auto-title
    if (!activeConversation.value.title) {
      activeConversation.value.title =
        content.length > 80 ? content.substring(0, 80) + '...' : content
    }

    // Start streaming
    isStreaming.value = true
    streamingMessage.value = ''
    toolCalls.value = []
    error.value = null

    try {
      const response = await apiSend(convId, content)
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
            } else if (data.tool_call) {
              toolCalls.value.push({
                name: data.tool_call.name,
                input: data.tool_call.input,
                status: 'executing',
                result: null
              })
            } else if (data.tool_result) {
              const tc = toolCalls.value.find(
                (t) => t.name === data.tool_result.name && t.status === 'executing'
              )
              if (tc) {
                tc.status = data.tool_result.result?.error ? 'error' : 'success'
                tc.result = data.tool_result.result
              }
            } else if (data.done) {
              activeConversation.value.messages.push({
                id: data.message_id,
                role: 'assistant',
                content: streamingMessage.value,
                metadata_: { toolCalls: [...toolCalls.value] },
                created_at: new Date().toISOString()
              })
              streamingMessage.value = ''
              toolCalls.value = []
              // Refresh status after setup actions
              fetchStatus()
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
        activeConversation.value.messages.push({
          id: Date.now(),
          role: 'assistant',
          content: streamingMessage.value,
          metadata_: { toolCalls: [...toolCalls.value] },
          created_at: new Date().toISOString()
        })
        streamingMessage.value = ''
        toolCalls.value = []
      }
    }
  }

  return {
    conversations,
    activeConversation,
    streamingMessage,
    isStreaming,
    toolCalls,
    loading,
    error,
    setupStatus,
    completedSteps,
    totalSteps,
    fetchStatus,
    fetchConversations,
    startSetup,
    openConversation,
    removeConversation,
    sendMessage
  }
})
