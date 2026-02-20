import api from '@/api'

// --- Categories ---
export const getCategories = () => api.get('/v1/collector/categories')

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

// --- Topics ---
export const getTopics = (params) => api.get('/v1/collector/topics', { params })
export const createTopic = (data) => api.post('/v1/collector/topics', data)
export const updateTopic = (id, data) => api.put(`/v1/collector/topics/${id}`, data)
export const deleteTopic = (id) => api.delete(`/v1/collector/topics/${id}`)
export const generateFromTopic = (id, data) => api.post(`/v1/collector/topics/${id}/generate`, data)

// --- Upload ---
export const uploadImage = (file) => {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/v1/collector/upload/image', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}
