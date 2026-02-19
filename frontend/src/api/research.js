import api from '@/api'

// --- Sources ---
export const getSources = (params) => api.get('/v1/research/sources', { params })
export const getSource = (id) => api.get(`/v1/research/sources/${id}`)
export const createSource = (data) => api.post('/v1/research/sources', data)
export const updateSource = (id, data) => api.put(`/v1/research/sources/${id}`, data)
export const deleteSource = (id) => api.delete(`/v1/research/sources/${id}`)

// --- Research Run ---
export const runResearch = (data = {}) => api.post('/v1/research/run', data)

// --- Findings ---
export const getFindings = (params) => api.get('/v1/research/findings', { params })
export const updateFinding = (id, data) => api.patch(`/v1/research/findings/${id}`, data)

// --- Topics ---
export const getTopics = (params) => api.get('/v1/research/topics', { params })
export const createTopic = (data) => api.post('/v1/research/topics', data)
export const updateTopic = (id, data) => api.put(`/v1/research/topics/${id}`, data)
export const deleteTopic = (id) => api.delete(`/v1/research/topics/${id}`)
export const generateFromTopic = (id, data) => api.post(`/v1/research/topics/${id}/generate`, data)

// --- Upload ---
export const uploadImage = (file) => {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/v1/research/upload/image', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}
