import api from '@/api'

export function getPrompts(params = {}) {
  return api.get('/v1/prompts/', { params })
}

export function getPrompt(promptId) {
  return api.get(`/v1/prompts/${promptId}`)
}

export function createPrompt(data) {
  return api.post('/v1/prompts/', data)
}

export function updatePrompt(promptId, data) {
  return api.put(`/v1/prompts/${promptId}`, data)
}

export function deletePrompt(promptId) {
  return api.delete(`/v1/prompts/${promptId}`)
}

export function createPromptVersion(promptId) {
  return api.post(`/v1/prompts/${promptId}/version`)
}

export function executePrompt(data) {
  return api.post('/v1/llm/execute', data)
}
