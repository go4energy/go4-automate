/**
 * Post-Mail Store
 *
 * Pinia store for managing postmail state
 */

import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import postmailApi from '@/api/postmail'

export const usePostmailStore = defineStore('postmail', () => {
  // ============== State ==============
  const templates = ref([])
  const letters = ref([])
  const batches = ref([])
  const stats = ref(null)

  const loading = ref(false)
  const error = ref(null)

  // Current selections
  const currentTemplate = ref(null)
  const currentLetter = ref(null)
  const currentBatch = ref(null)

  // ============== Computed ==============
  const activeTemplates = computed(() =>
    templates.value.filter((t) => t.is_active)
  )

  const draftLetters = computed(() =>
    letters.value.filter((l) => l.status === 'draft')
  )

  const approvedLetters = computed(() =>
    letters.value.filter((l) => l.status === 'approved')
  )

  const queuedLetters = computed(() =>
    letters.value.filter((l) => l.status === 'queued')
  )

  const pendingBatches = computed(() =>
    batches.value.filter((b) => b.status !== 'sent')
  )

  // ============== Template Actions ==============
  async function fetchTemplates(params = {}) {
    loading.value = true
    error.value = null
    try {
      const data = await postmailApi.getTemplates(params)
      templates.value = data.items
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchTemplate(id) {
    loading.value = true
    error.value = null
    try {
      const template = await postmailApi.getTemplate(id)
      currentTemplate.value = template
      return template
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createTemplate(data) {
    loading.value = true
    error.value = null
    try {
      const template = await postmailApi.createTemplate(data)
      templates.value.push(template)
      return template
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateTemplate(id, data) {
    loading.value = true
    error.value = null
    try {
      const template = await postmailApi.updateTemplate(id, data)
      const idx = templates.value.findIndex((t) => t.id === id)
      if (idx !== -1) templates.value[idx] = template
      if (currentTemplate.value?.id === id) currentTemplate.value = template
      return template
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteTemplate(id) {
    loading.value = true
    error.value = null
    try {
      await postmailApi.deleteTemplate(id)
      templates.value = templates.value.filter((t) => t.id !== id)
      if (currentTemplate.value?.id === id) currentTemplate.value = null
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function previewTemplate(params) {
    loading.value = true
    error.value = null
    try {
      return await postmailApi.previewTemplate(params)
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  // ============== Letter Actions ==============
  async function fetchLetters(params = {}) {
    loading.value = true
    error.value = null
    try {
      const data = await postmailApi.getLetters(params)
      letters.value = data.items
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchLetter(id) {
    loading.value = true
    error.value = null
    try {
      const letter = await postmailApi.getLetter(id)
      currentLetter.value = letter
      return letter
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createLetter(data) {
    loading.value = true
    error.value = null
    try {
      const letter = await postmailApi.createLetter(data)
      letters.value.push(letter)
      return letter
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createLetterFromAction(params) {
    loading.value = true
    error.value = null
    try {
      const letter = await postmailApi.createLetterFromAction(params)
      letters.value.push(letter)
      return letter
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateLetter(id, data) {
    loading.value = true
    error.value = null
    try {
      const letter = await postmailApi.updateLetter(id, data)
      const idx = letters.value.findIndex((l) => l.id === id)
      if (idx !== -1) letters.value[idx] = letter
      if (currentLetter.value?.id === id) currentLetter.value = letter
      return letter
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteLetter(id) {
    loading.value = true
    error.value = null
    try {
      await postmailApi.deleteLetter(id)
      letters.value = letters.value.filter((l) => l.id !== id)
      if (currentLetter.value?.id === id) currentLetter.value = null
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function approveLetter(id) {
    loading.value = true
    error.value = null
    try {
      const letter = await postmailApi.approveLetter(id)
      const idx = letters.value.findIndex((l) => l.id === id)
      if (idx !== -1) letters.value[idx] = letter
      if (currentLetter.value?.id === id) currentLetter.value = letter
      return letter
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function generateLetterPdf(id) {
    loading.value = true
    error.value = null
    try {
      const letter = await postmailApi.generateLetterPdf(id)
      const idx = letters.value.findIndex((l) => l.id === id)
      if (idx !== -1) letters.value[idx] = letter
      if (currentLetter.value?.id === id) currentLetter.value = letter
      return letter
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  // ============== Batch Actions ==============
  async function fetchBatches(params = {}) {
    loading.value = true
    error.value = null
    try {
      const data = await postmailApi.getBatches(params)
      batches.value = data.items
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchBatch(id) {
    loading.value = true
    error.value = null
    try {
      const batch = await postmailApi.getBatch(id)
      currentBatch.value = batch
      return batch
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createBatch(data) {
    loading.value = true
    error.value = null
    try {
      const batch = await postmailApi.createBatch(data)
      batches.value.push(batch)
      return batch
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateBatch(id, data) {
    loading.value = true
    error.value = null
    try {
      const batch = await postmailApi.updateBatch(id, data)
      const idx = batches.value.findIndex((b) => b.id === id)
      if (idx !== -1) batches.value[idx] = batch
      if (currentBatch.value?.id === id) currentBatch.value = batch
      return batch
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function exportBatch(id) {
    loading.value = true
    error.value = null
    try {
      const result = await postmailApi.exportBatch(id)
      // Update batch in list
      const idx = batches.value.findIndex((b) => b.id === id)
      if (idx !== -1) {
        batches.value[idx].status = 'exported'
        batches.value[idx].export_path = result.export_path
      }
      return result
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function markBatchSent(id) {
    loading.value = true
    error.value = null
    try {
      const batch = await postmailApi.markBatchSent(id)
      const idx = batches.value.findIndex((b) => b.id === id)
      if (idx !== -1) batches.value[idx] = batch
      if (currentBatch.value?.id === id) currentBatch.value = batch
      return batch
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  // ============== Stats ==============
  async function fetchStats() {
    loading.value = true
    error.value = null
    try {
      stats.value = await postmailApi.getStats()
      return stats.value
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  // ============== Reset ==============
  function $reset() {
    templates.value = []
    letters.value = []
    batches.value = []
    stats.value = null
    loading.value = false
    error.value = null
    currentTemplate.value = null
    currentLetter.value = null
    currentBatch.value = null
  }

  return {
    // State
    templates,
    letters,
    batches,
    stats,
    loading,
    error,
    currentTemplate,
    currentLetter,
    currentBatch,
    // Computed
    activeTemplates,
    draftLetters,
    approvedLetters,
    queuedLetters,
    pendingBatches,
    // Template Actions
    fetchTemplates,
    fetchTemplate,
    createTemplate,
    updateTemplate,
    deleteTemplate,
    previewTemplate,
    // Letter Actions
    fetchLetters,
    fetchLetter,
    createLetter,
    createLetterFromAction,
    updateLetter,
    deleteLetter,
    approveLetter,
    generateLetterPdf,
    // Batch Actions
    fetchBatches,
    fetchBatch,
    createBatch,
    updateBatch,
    exportBatch,
    markBatchSent,
    // Stats
    fetchStats,
    // Reset
    $reset,
  }
})
