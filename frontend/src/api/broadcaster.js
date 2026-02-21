import api from '@/api'

// --- Channels ---
export const getChannels = () => api.get('/v1/broadcaster/channels')
export const getChannel = (id) => api.get(`/v1/broadcaster/channels/${id}`)
export const createChannel = (data) => api.post('/v1/broadcaster/channels', data)
export const updateChannel = (id, data) => api.put(`/v1/broadcaster/channels/${id}`, data)
export const deleteChannel = (id) => api.delete(`/v1/broadcaster/channels/${id}`)

// --- Episodes ---
export const getEpisodes = (channelId) => api.get(`/v1/broadcaster/channels/${channelId}/episodes`)
export const generateEpisode = (channelId) =>
  api.post(`/v1/broadcaster/channels/${channelId}/generate`)
export const getEpisode = (id) => api.get(`/v1/broadcaster/episodes/${id}`)
export const deleteEpisode = (id) => api.delete(`/v1/broadcaster/episodes/${id}`)

// --- Listener Users (Admin) ---
export const getUsers = () => api.get('/v1/broadcaster/users')
export const createUser = (data) => api.post('/v1/broadcaster/users', data)
export const deleteUser = (id) => api.delete(`/v1/broadcaster/users/${id}`)

// --- Module Interface ---
export const getStatus = () => api.get('/v1/broadcaster/status')
export const getMetrics = (days = 7) => api.get('/v1/broadcaster/metrics', { params: { days } })
