import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import {
  getPrompts,
  getPrompt,
  createPrompt,
  updatePrompt,
  deletePrompt,
  createPromptVersion,
  executePrompt
} from '@/api/prompts'

export const usePromptStore = defineStore('prompts', () => {
  const prompts = ref([])
  const currentPrompt = ref(null)
  const loading = ref(false)
  const error = ref(null)

  const categories = computed(() => {
    const cats = new Set(prompts.value.map((p) => p.category))
    return [...cats].sort()
  })

  async function fetchPrompts(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getPrompts(params)
      prompts.value = data
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function fetchPrompt(promptId) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getPrompt(promptId)
      currentPrompt.value = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function addPrompt(promptData) {
    loading.value = true
    error.value = null
    try {
      const { data } = await createPrompt(promptData)
      prompts.value.unshift(data)
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function editPrompt(promptId, promptData) {
    error.value = null
    try {
      const { data } = await updatePrompt(promptId, promptData)
      const index = prompts.value.findIndex((p) => p.id === promptId)
      if (index !== -1) prompts.value[index] = data
      if (currentPrompt.value?.id === promptId) currentPrompt.value = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function removePrompt(promptId) {
    error.value = null
    try {
      await deletePrompt(promptId)
      prompts.value = prompts.value.filter((p) => p.id !== promptId)
      if (currentPrompt.value?.id === promptId) currentPrompt.value = null
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function newVersion(promptId) {
    error.value = null
    try {
      const { data } = await createPromptVersion(promptId)
      prompts.value.unshift(data)
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function testPrompt(slug, variables) {
    error.value = null
    try {
      const { data } = await executePrompt({ prompt_slug: slug, variables })
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  return {
    prompts,
    currentPrompt,
    loading,
    error,
    categories,
    fetchPrompts,
    fetchPrompt,
    addPrompt,
    editPrompt,
    removePrompt,
    newVersion,
    testPrompt
  }
})
