import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import {
  getContentPieces,
  getContentPiece,
  generateContent,
  updateContentPiece,
  approveContent,
  publishContent,
  deleteContentPiece
} from '@/api/content'

export const useContentStore = defineStore('content', () => {
  const pieces = ref([])
  const currentPiece = ref(null)
  const loading = ref(false)
  const error = ref(null)

  const stats = computed(() => {
    const draft = pieces.value.filter((p) => p.status === 'draft').length
    const scheduled = pieces.value.filter((p) => p.status === 'scheduled').length
    const published = pieces.value.filter((p) => p.status === 'published').length
    const failed = pieces.value.filter((p) => p.status === 'failed').length
    const totalReach = pieces.value.reduce((sum, p) => sum + (p.reach || 0), 0)
    return { draft, scheduled, published, failed, totalReach }
  })

  async function fetchPieces(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getContentPieces(params)
      pieces.value = data
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function fetchPiece(pieceId) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getContentPiece(pieceId)
      currentPiece.value = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function generate(data) {
    loading.value = true
    error.value = null
    try {
      const { data: piece } = await generateContent(data)
      pieces.value.unshift(piece)
      return piece
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function approve(pieceId, data) {
    error.value = null
    try {
      const { data: piece } = await approveContent(pieceId, data)
      const index = pieces.value.findIndex((p) => p.id === pieceId)
      if (index !== -1) pieces.value[index] = piece
      if (currentPiece.value?.id === pieceId) currentPiece.value = piece
      return piece
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function publish(pieceId) {
    error.value = null
    try {
      const { data: result } = await publishContent(pieceId)
      const index = pieces.value.findIndex((p) => p.id === pieceId)
      if (index !== -1) {
        pieces.value[index] = { ...pieces.value[index], ...result }
      }
      return result
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function update(pieceId, data) {
    error.value = null
    try {
      const { data: piece } = await updateContentPiece(pieceId, data)
      const index = pieces.value.findIndex((p) => p.id === pieceId)
      if (index !== -1) pieces.value[index] = piece
      if (currentPiece.value?.id === pieceId) currentPiece.value = piece
      return piece
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function remove(pieceId) {
    error.value = null
    try {
      await deleteContentPiece(pieceId)
      pieces.value = pieces.value.filter((p) => p.id !== pieceId)
      if (currentPiece.value?.id === pieceId) currentPiece.value = null
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  return {
    pieces,
    currentPiece,
    loading,
    error,
    stats,
    fetchPieces,
    fetchPiece,
    generate,
    approve,
    publish,
    update,
    remove
  }
})
