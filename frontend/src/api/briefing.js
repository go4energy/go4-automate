import api from '@/api'

// --- Channels ---
export const getChannels = () => api.get('/v1/briefing/channels')
export const getChannel = (id) => api.get(`/v1/briefing/channels/${id}`)
export const createChannel = (data, params) => api.post('/v1/briefing/channels', data, { params })
export const updateChannel = (id, data) => api.put(`/v1/briefing/channels/${id}`, data)
export const deleteChannel = (id) => api.delete(`/v1/briefing/channels/${id}`)

// --- Episodes ---
export const getEpisodes = (channelId) => api.get(`/v1/briefing/channels/${channelId}/episodes`)
export const generateEpisode = (channelId) =>
  api.post(`/v1/briefing/channels/${channelId}/generate`)
export const getEpisode = (id) => api.get(`/v1/briefing/episodes/${id}`)
export const deleteEpisode = (id) => api.delete(`/v1/briefing/episodes/${id}`)

// --- Listener Users (Admin) ---
export const getUsers = () => api.get('/v1/briefing/users')
export const createUser = (data) => api.post('/v1/briefing/users', data)
export const deleteUser = (id) => api.delete(`/v1/briefing/users/${id}`)

// --- Sources ---
export const getSources = (params) => api.get('/v1/briefing/sources', { params })
export const getSource = (id) => api.get(`/v1/briefing/sources/${id}`)
export const createSource = (data, params) => api.post('/v1/briefing/sources', data, { params })
export const updateSource = (id, data) => api.put(`/v1/briefing/sources/${id}`, data)
export const deleteSource = (id) => api.delete(`/v1/briefing/sources/${id}`)
export const runSources = () => api.post('/v1/briefing/sources/run')
export const runSource = (id) => api.post(`/v1/briefing/sources/${id}/run`)

// --- Findings ---
export const getFindings = (params) => api.get('/v1/briefing/findings', { params })
export const updateFinding = (id, data) => api.put(`/v1/briefing/findings/${id}`, data)
export const bulkDeleteFindings = (ids) => api.post('/v1/briefing/findings/bulk-delete', { ids })

// --- Channel Clone ---
export const cloneChannel = (channelId, data = {}) =>
  api.post(`/v1/briefing/channels/${channelId}/clone`, data)

// --- Channel-Source Linking ---
export const getChannelSources = (channelId) =>
  api.get(`/v1/briefing/channels/${channelId}/sources`)
export const linkSource = (channelId, sourceId) =>
  api.post(`/v1/briefing/channels/${channelId}/sources/${sourceId}`)
export const unlinkSource = (channelId, sourceId) =>
  api.delete(`/v1/briefing/channels/${channelId}/sources/${sourceId}`)

// --- Speakers (XTTS Voice Cloning) ---
export const getSpeakers = () => api.get('/v1/briefing/speakers')
export const uploadSpeaker = (formData) =>
  api.post('/v1/briefing/speakers', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
export const deleteSpeaker = (id) => api.delete(`/v1/briefing/speakers/${id}`)
export const getSpeakerPreviewUrl = (id) => `/api/v1/briefing/speakers/${id}/preview`

// --- OAuth ---
export const getOAuthAuthUrl = (sourceId, provider = 'microsoft') =>
  api.get('/v1/briefing/oauth/authorize', { params: { source_id: sourceId, provider } })
export const disconnectOAuth = (sourceId) =>
  api.post(`/v1/briefing/sources/${sourceId}/oauth/disconnect`)

// --- Personal Briefing ---
export const getPersonalSettings = () => api.get('/v1/briefing/personal/settings')
export const updatePersonalSettings = (data) => api.put('/v1/briefing/personal/settings', data)
export const getPersonalConnections = () => api.get('/v1/briefing/personal/connections')
export const getAvailableOllamaModels = () => api.get('/v1/briefing/personal/admin/ollama-models')
export const getPersonalOAuthAuthUrl = (provider, integrationType) =>
  api.get('/v1/briefing/personal/oauth/authorize', {
    params: { provider, integration_type: integrationType }
  })
export const disconnectPersonalConnection = (connectionId) =>
  api.post(`/v1/briefing/personal/connections/${connectionId}/disconnect`)
export const runPersonalBriefing = () => api.post('/v1/briefing/personal/run')

// --- Module Interface ---
export const getStatus = () => api.get('/v1/briefing/status')
export const getMetrics = (days = 7) => api.get('/v1/briefing/metrics', { params: { days } })
