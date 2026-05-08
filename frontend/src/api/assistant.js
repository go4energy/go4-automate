import api from '@/api'

// Profile
export const getProfile = () => api.get('/v1/assistant/profile')
export const updateProfile = (data) => api.put('/v1/assistant/profile', data)

// Sources
export const getSources = () => api.get('/v1/assistant/sources')
export const addSource = (data) => api.post('/v1/assistant/sources', data)
export const updateSource = (id, data) => api.put(`/v1/assistant/sources/${id}`, data)
export const deleteSource = (id) => api.delete(`/v1/assistant/sources/${id}`)
export const getMailboxPolicy = (sourceId) =>
  api.get(`/v1/assistant/sources/${sourceId}/mailbox-policy`)
export const setupMailboxPolicy = (sourceId, data = {}) =>
  api.post(`/v1/assistant/sources/${sourceId}/mailbox-policy/setup`, data)

// Categories
export const getCategories = (params) => api.get('/v1/assistant/categories', { params })
export const createCategory = (data) => api.post('/v1/assistant/categories', data)
export const updateCategory = (id, data) => api.put(`/v1/assistant/categories/${id}`, data)
export const deleteCategory = (id) => api.delete(`/v1/assistant/categories/${id}`)

// TEMP review
export const getTempReview = (params) => api.get('/v1/assistant/temp/review', { params })
export const getWaitingReview = (params) => api.get('/v1/assistant/reviews/waiting', { params })
export const getTodoReview = (params) => api.get('/v1/assistant/reviews/todos', { params })
export const getTriageBatch = (params) => api.get('/v1/assistant/triage/batch', { params })

// Items
export const getItems = (params) => api.get('/v1/assistant/items', { params })
export const getItem = (id) => api.get(`/v1/assistant/items/${id}`)
export const getItemDecisions = (id) => api.get(`/v1/assistant/items/${id}/decisions`)

// Feedback
export const addFeedback = (itemId, data) =>
  api.post(`/v1/assistant/items/${itemId}/feedback`, data)

// Rules
export const getRules = () => api.get('/v1/assistant/rules')
export const createRule = (data) => api.post('/v1/assistant/rules', data)
export const updateRule = (id, data) => api.put(`/v1/assistant/rules/${id}`, data)
export const deleteRule = (id) => api.delete(`/v1/assistant/rules/${id}`)

// Actions / Approvals
export const getPendingActions = () => api.get('/v1/assistant/actions/pending')
export const approveAction = (id) => api.post(`/v1/assistant/actions/${id}/approve`)
export const rejectAction = (id) => api.post(`/v1/assistant/actions/${id}/reject`)

// Drafts
export const getDrafts = (params) => api.get('/v1/assistant/drafts', { params })
export const getDraft = (id) => api.get(`/v1/assistant/drafts/${id}`)
export const updateDraft = (id, data) => api.put(`/v1/assistant/drafts/${id}`, data)
export const sendDraft = (id) => api.post(`/v1/assistant/drafts/${id}/send`)
export const discardDraft = (id) => api.post(`/v1/assistant/drafts/${id}/discard`)

// Pending intents
export const getPendingIntents = (params) =>
  api.get('/v1/assistant/pending-intents', { params })
export const getPendingIntent = (id) => api.get(`/v1/assistant/pending-intents/${id}`)
export const executePendingIntent = (id) =>
  api.post(`/v1/assistant/pending-intents/${id}/execute`)
export const cancelPendingIntent = (id) =>
  api.post(`/v1/assistant/pending-intents/${id}/cancel`)

// Conversations
export const getConversationTurns = (conversationId, params) =>
  api.get(`/v1/assistant/conversations/${conversationId}/turns`, { params })

// Undo logs
export const getUndoLogs = (params) => api.get('/v1/assistant/undo-logs', { params })
export const undoLogAction = (id) => api.post(`/v1/assistant/undo-logs/${id}/undo`)

// Dashboard
export const getDashboard = () => api.get('/v1/assistant/dashboard')
export const getMailboxHealth = () => api.get('/v1/assistant/mailbox-health')

// OAuth
export const getOAuthUrl = (params) =>
  api.get('/v1/assistant/oauth/authorize', { params })

// Model / Voice Lists
export const getOllamaModels = () => api.get('/v1/assistant/ollama-models')
export const getPiperVoices = () => api.get('/v1/assistant/piper-voices')

// Speaker Voices (XTTS)
export const getSpeakerVoices = () => api.get('/v1/assistant/speaker-voices')
export const uploadSpeakerVoice = (name, wavBlob) => {
  const form = new FormData()
  form.append('name', name)
  form.append('audio', wavBlob, `${name}.wav`)
  return api.post('/v1/assistant/speaker-voices', form)
}
export const deleteSpeakerVoice = (name) =>
  api.delete(`/v1/assistant/speaker-voices/${name}`)

// Test / Manual Triggers
export const runIntake = () => api.post('/v1/assistant/intake/run')
export const runClassify = () => api.post('/v1/assistant/classify/run')
export const runRules = () => api.post('/v1/assistant/rules/apply')
export const runBriefing = (data) => api.post('/v1/assistant/briefing/run', data || {})
export const getRuleSuggestions = () => api.get('/v1/assistant/rule-suggestions')
export const applyRuleSuggestion = (data) =>
  api.post('/v1/assistant/rule-suggestions/apply', data)

// Voice Chat
export const sendVoiceChat = (data) => {
  const form = new FormData()
  form.append('text', data.text)
  if (data.conversation_id) form.append('conversation_id', data.conversation_id)
  form.append('tts_enabled', data.tts_enabled ?? true)
  return api.post('/v1/assistant/voice/chat', form)
}

export const sendVoiceAudio = (audioBlob, conversationId, ttsEnabled = true) => {
  const form = new FormData()
  form.append('audio', audioBlob, 'recording.webm')
  if (conversationId) form.append('conversation_id', conversationId)
  form.append('tts_enabled', ttsEnabled)
  return api.post('/v1/assistant/voice/chat', form)
}

export const transcribeAudio = (audioBlob) => {
  const form = new FormData()
  form.append('audio', audioBlob, 'recording.webm')
  return api.post('/v1/assistant/voice/transcribe', form)
}

export const synthesizeTTS = (text) =>
  api.post('/v1/assistant/voice/tts', { text }, { responseType: 'arraybuffer' })
