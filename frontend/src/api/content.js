import api from '@/api'

export function getContentPieces(params = {}) {
  return api.get('/v1/content/pieces', { params })
}

export function getContentPiece(pieceId) {
  return api.get(`/v1/content/pieces/${pieceId}`)
}

export function generateContent(data) {
  return api.post('/v1/content/pieces/generate', data)
}

export function updateContentPiece(pieceId, data) {
  return api.put(`/v1/content/pieces/${pieceId}`, data)
}

export function approveContent(pieceId, data) {
  return api.patch(`/v1/content/pieces/${pieceId}/approve`, data)
}

export function publishContent(pieceId) {
  return api.post(`/v1/content/pieces/${pieceId}/publish`)
}

export function deleteContentPiece(pieceId) {
  return api.delete(`/v1/content/pieces/${pieceId}`)
}
