import api from '@/api'

// --- Groups ---
export const getGroups = () => api.get('/v1/collector/groups')
export const getGroup = (id) => api.get(`/v1/collector/groups/${id}`)
export const createGroup = (data) => api.post('/v1/collector/groups', data)
export const updateGroup = (id, data) => api.put(`/v1/collector/groups/${id}`, data)
export const deleteGroup = (id) => api.delete(`/v1/collector/groups/${id}`)

// --- Sources ---
export const getSources = (params) => api.get('/v1/collector/sources', { params })
export const getSource = (id) => api.get(`/v1/collector/sources/${id}`)
export const createSource = (data) => api.post('/v1/collector/sources', data)
export const updateSource = (id, data) => api.put(`/v1/collector/sources/${id}`, data)
export const deleteSource = (id) => api.delete(`/v1/collector/sources/${id}`)

// --- Collector Run ---
export const runCollector = (data = {}) => api.post('/v1/collector/run', data)

// --- Inbox ---
export const createInboxItem = (data) => api.post('/v1/collector/inbox', data)

// --- Change Detection ---
export const detectChanges = (sourceId) =>
  api.post(`/v1/collector/sources/${sourceId}/detect-changes`)
export const getSnapshots = (sourceId) => api.get(`/v1/collector/sources/${sourceId}/snapshots`)

// --- Findings ---
export const getFindings = (params) => api.get('/v1/collector/findings', { params })
export const updateFinding = (id, data) => api.patch(`/v1/collector/findings/${id}`, data)
export const analyzeFinding = (id) => api.post(`/v1/collector/findings/${id}/analyze`)
export const bulkDeleteFindings = (ids) => api.post('/v1/collector/findings/bulk-delete', { ids })

// --- Topics ---
export const getTopics = (params) => api.get('/v1/collector/topics', { params })
export const getTopic = (id) => api.get(`/v1/collector/topics/${id}`)
export const createTopic = (data) => api.post('/v1/collector/topics', data)
export const updateTopic = (id, data) => api.put(`/v1/collector/topics/${id}`, data)
export const deleteTopic = (id) => api.delete(`/v1/collector/topics/${id}`)
export const generateFromTopic = (id, data) => api.post(`/v1/collector/topics/${id}/generate`, data)
export const reanalyzeTopic = (id) => api.post(`/v1/collector/topics/${id}/reanalyze`)
export const bulkDeleteTopics = (ids) => api.post('/v1/collector/topics/bulk-delete', { ids })

// --- Group Prompts ---
export const addGroupPrompt = (groupId, data) =>
  api.post(`/v1/collector/groups/${groupId}/prompts`, data)
export const removeGroupPrompt = (groupId, slug) =>
  api.delete(`/v1/collector/groups/${groupId}/prompts/${slug}`)
export const runGroupPrompt = (groupId, slug) =>
  api.post(`/v1/collector/groups/${groupId}/prompts/${slug}/run`)

// --- Upload ---
export const uploadImage = (file) => {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/v1/collector/upload/image', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}
