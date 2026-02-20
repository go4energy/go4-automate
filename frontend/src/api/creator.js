import api from '@/api'

export function getCreatorPieces(params = {}) {
  return api.get('/v1/creator/pieces', { params })
}

export function getCreatorPiece(pieceId) {
  return api.get(`/v1/creator/pieces/${pieceId}`)
}

export function generateContent(data) {
  return api.post('/v1/creator/pieces/generate', data)
}

export function generateFromTopic(data) {
  return api.post('/v1/creator/pieces/generate-from-topic', data)
}

export function updateCreatorPiece(pieceId, data) {
  return api.put(`/v1/creator/pieces/${pieceId}`, data)
}

export function approveContent(pieceId, data) {
  return api.patch(`/v1/creator/pieces/${pieceId}/approve`, data)
}

export function publishContent(pieceId) {
  return api.post(`/v1/creator/pieces/${pieceId}/publish`)
}

export function deleteCreatorPiece(pieceId) {
  return api.delete(`/v1/creator/pieces/${pieceId}`)
}
