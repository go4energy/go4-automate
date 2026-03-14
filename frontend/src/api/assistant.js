import api from '@/api'

// Profile
export const getProfile = () => api.get('/v1/assistant/profile')
export const updateProfile = (data) => api.put('/v1/assistant/profile', data)

// Sources
export const getSources = () => api.get('/v1/assistant/sources')
export const addSource = (data) => api.post('/v1/assistant/sources', data)
export const updateSource = (id, data) => api.put(`/v1/assistant/sources/${id}`, data)
export const deleteSource = (id) => api.delete(`/v1/assistant/sources/${id}`)

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

// Dashboard
export const getDashboard = () => api.get('/v1/assistant/dashboard')

// OAuth
export const getOAuthUrl = (params) =>
  api.get('/v1/assistant/oauth/authorize', { params })

// Test / Manual Triggers
export const runIntake = () => api.post('/v1/assistant/intake/run')
export const runClassify = () => api.post('/v1/assistant/classify/run')
export const runRules = () => api.post('/v1/assistant/rules/apply')
export const runBriefing = (data) => api.post('/v1/assistant/briefing/run', data || {})
export const getRuleSuggestions = () => api.get('/v1/assistant/rule-suggestions')
