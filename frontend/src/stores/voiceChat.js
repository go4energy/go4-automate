import { ref } from 'vue'
import { defineStore } from 'pinia'
import {
  cancelPendingIntent,
  discardDraft,
  executePendingIntent,
  getConversationTurns,
  getDraft,
  getPendingIntent,
  getUndoLogs,
  sendDraft,
  sendVoiceAudio,
  sendVoiceChat,
  undoLogAction,
  updateDraft,
} from '@/api/assistant'

export const useVoiceChatStore = defineStore('voiceChat', () => {
  const messages = ref([])
  const conversationId = ref(null)
  const currentContext = ref(null)
  const currentDraft = ref(null)
  const currentPendingIntent = ref(null)
  const conversationTurns = ref([])
  const undoLogs = ref([])
  const draftEditor = ref({ subject: '', body_text: '' })
  const ttsEnabled = ref(true)
  const loading = ref(false)
  const error = ref(null)
  let reviewRequestId = 0

  async function sendText(text) {
    loading.value = true
    error.value = null
    messages.value.push({ role: 'user', content: text, time: new Date() })

    try {
      const { data } = await sendVoiceChat({
        text,
        conversation_id: conversationId.value,
        tts_enabled: ttsEnabled.value,
      })
      conversationId.value = data.conversation_id
      currentContext.value = data.context
      messages.value.push({
        role: 'assistant',
        content: data.text,
        audio_base64: data.audio_base64,
        time: new Date(),
      })
      refreshReviewState().catch((err) => {
        error.value = err.response?.data?.detail || err.message || error.value
      })
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      messages.value.push({
        role: 'assistant',
        content: `Fehler: ${error.value}`,
        time: new Date(),
        isError: true,
      })
      return null
    } finally {
      loading.value = false
    }
  }

  async function sendAudio(blob) {
    loading.value = true
    error.value = null
    messages.value.push({ role: 'user', content: '🎙 Sprachnachricht...', time: new Date(), isAudio: true })

    try {
      const { data } = await sendVoiceAudio(blob, conversationId.value, ttsEnabled.value)
      conversationId.value = data.conversation_id
      currentContext.value = data.context

      // Update user message with transcribed text from backend
      if (data.transcribed_text) {
        const lastUserMsg = [...messages.value].reverse().find((m) => m.role === 'user' && m.isAudio)
        if (lastUserMsg) {
          lastUserMsg.content = data.transcribed_text
          lastUserMsg.isAudio = false
        }
      }

      messages.value.push({
        role: 'assistant',
        content: data.text,
        audio_base64: data.audio_base64,
        time: new Date(),
      })
      refreshReviewState().catch((err) => {
        error.value = err.response?.data?.detail || err.message || error.value
      })
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      messages.value.push({
        role: 'assistant',
        content: `Fehler: ${error.value}`,
        time: new Date(),
        isError: true,
      })
      return null
    } finally {
      loading.value = false
    }
  }

  function clearChat() {
    messages.value = []
    conversationId.value = null
    currentContext.value = null
    currentDraft.value = null
    currentPendingIntent.value = null
    conversationTurns.value = []
    undoLogs.value = []
    error.value = null
  }

  async function refreshReviewState() {
    const requestId = ++reviewRequestId
    const pendingDraftId = currentContext.value?.pending_draft_id
    const pendingIntentId = currentContext.value?.pending_intent_id

    currentDraft.value = null
    currentPendingIntent.value = null
    undoLogs.value = []
    draftEditor.value = { subject: '', body_text: '' }

    const [draftResult, intentResult, turnsResult, undoResult] = await Promise.allSettled([
      pendingDraftId ? getDraft(pendingDraftId) : Promise.resolve(null),
      pendingIntentId ? getPendingIntent(pendingIntentId) : Promise.resolve(null),
      conversationId.value
        ? getConversationTurns(conversationId.value, { limit: 50 })
        : Promise.resolve(null),
      getUndoLogs({ limit: 5, undoable_only: true }),
    ])

    if (requestId !== reviewRequestId) return

    if (draftResult.status === 'fulfilled' && draftResult.value?.data) {
      currentDraft.value = draftResult.value.data
      draftEditor.value = {
        subject: draftResult.value.data.subject || '',
        body_text: draftResult.value.data.body_text || '',
      }
    } else if (draftResult.status === 'rejected') {
      error.value = draftResult.reason?.response?.data?.detail || draftResult.reason?.message || error.value
    }

    if (intentResult.status === 'fulfilled' && intentResult.value?.data) {
      currentPendingIntent.value = intentResult.value.data
    } else if (intentResult.status === 'rejected') {
      error.value =
        intentResult.reason?.response?.data?.detail || intentResult.reason?.message || error.value
    }

    if (turnsResult.status === 'fulfilled') {
      conversationTurns.value = turnsResult.value?.data || []
    } else if (conversationId.value) {
      conversationTurns.value = []
    }

    if (undoResult.status === 'fulfilled') {
      undoLogs.value = undoResult.value?.data || []
    } else {
      undoLogs.value = []
      error.value = undoResult.reason?.response?.data?.detail || undoResult.reason?.message || error.value
    }
  }

  async function confirmCurrentIntent() {
    if (!currentPendingIntent.value) return null
    loading.value = true
    error.value = null
    try {
      const { data } = await executePendingIntent(currentPendingIntent.value.id)
      currentPendingIntent.value = data
      if (currentContext.value) currentContext.value.pending_intent_id = null
      messages.value.push({
        role: 'assistant',
        content: `Aktion ausgefuehrt: ${data.intent_type}`,
        time: new Date(),
      })
      await refreshReviewState()
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      return null
    } finally {
      loading.value = false
    }
  }

  async function cancelCurrentIntent() {
    if (!currentPendingIntent.value) return null
    loading.value = true
    error.value = null
    try {
      const { data } = await cancelPendingIntent(currentPendingIntent.value.id)
      currentPendingIntent.value = data
      if (currentContext.value) currentContext.value.pending_intent_id = null
      messages.value.push({
        role: 'assistant',
        content: `Aktion abgebrochen: ${data.intent_type}`,
        time: new Date(),
      })
      await refreshReviewState()
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      return null
    } finally {
      loading.value = false
    }
  }

  async function sendCurrentDraft() {
    if (!currentDraft.value) return null
    loading.value = true
    error.value = null
    try {
      const { data } = await sendDraft(currentDraft.value.id)
      currentDraft.value = data
      if (currentContext.value) currentContext.value.pending_draft_id = null
      messages.value.push({
        role: 'assistant',
        content: 'Entwurf gesendet.',
        time: new Date(),
      })
      await refreshReviewState()
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      return null
    } finally {
      loading.value = false
    }
  }

  async function discardCurrentDraft() {
    if (!currentDraft.value) return null
    loading.value = true
    error.value = null
    try {
      const { data } = await discardDraft(currentDraft.value.id)
      currentDraft.value = data
      if (currentContext.value) currentContext.value.pending_draft_id = null
      messages.value.push({
        role: 'assistant',
        content: 'Entwurf verworfen.',
        time: new Date(),
      })
      await refreshReviewState()
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      return null
    } finally {
      loading.value = false
    }
  }

  async function saveCurrentDraft() {
    if (!currentDraft.value) return null
    loading.value = true
    error.value = null
    try {
      const { data } = await updateDraft(currentDraft.value.id, {
        subject: draftEditor.value.subject,
        body_text: draftEditor.value.body_text,
      })
      currentDraft.value = data
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      return null
    } finally {
      loading.value = false
    }
  }

  async function undoLastAction(undoLogId) {
    loading.value = true
    error.value = null
    try {
      const { data } = await undoLogAction(undoLogId)
      messages.value.push({
        role: 'assistant',
        content: `Rueckgaengig gemacht: ${data.action_type}`,
        time: new Date(),
      })
      await refreshReviewState()
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      return null
    } finally {
      loading.value = false
    }
  }

  return {
    messages,
    conversationId,
    currentContext,
    currentDraft,
    currentPendingIntent,
    conversationTurns,
    undoLogs,
    draftEditor,
    ttsEnabled,
    loading,
    error,
    sendText,
    sendAudio,
    refreshReviewState,
    confirmCurrentIntent,
    cancelCurrentIntent,
    sendCurrentDraft,
    discardCurrentDraft,
    saveCurrentDraft,
    undoLastAction,
    clearChat,
  }
})
