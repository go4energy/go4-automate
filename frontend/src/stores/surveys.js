import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import {
  getSurveys,
  getSurvey,
  createSurvey,
  updateSurvey,
  deleteSurvey,
  updateSurveyStatus,
  duplicateSurvey,
  addQuestion as addQuestionApi,
  updateQuestion as updateQuestionApi,
  deleteQuestion as deleteQuestionApi,
  reorderQuestions,
  getResponses,
  getResponse,
  deleteResponse,
  getSurveyStats,
  getShareLink,
  sendInvites
} from '@/api/surveys'

export const useSurveysStore = defineStore('surveys', () => {
  // State
  const surveys = ref([])
  const currentSurvey = ref(null)
  const responses = ref([])
  const currentResponse = ref(null)
  const stats = ref(null)
  const shareLink = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // Computed
  const activeSurveys = computed(() => surveys.value.filter((s) => s.status === 'active'))
  const draftSurveys = computed(() => surveys.value.filter((s) => s.status === 'draft'))
  const questions = computed(() => currentSurvey.value?.questions || [])
  const totalResponses = computed(() =>
    surveys.value.reduce((sum, s) => sum + (s.response_count || 0), 0)
  )

  // ============== Surveys ==============

  async function fetchSurveys(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getSurveys(params)
      surveys.value = data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
    } finally {
      loading.value = false
    }
  }

  async function fetchSurvey(id) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getSurvey(id)
      currentSurvey.value = data
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function addSurvey(data) {
    loading.value = true
    error.value = null
    try {
      const response = await createSurvey(data)
      surveys.value.unshift(response.data)
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function editSurvey(id, data) {
    loading.value = true
    error.value = null
    try {
      const response = await updateSurvey(id, data)
      const index = surveys.value.findIndex((s) => s.id === id)
      if (index !== -1) {
        surveys.value[index] = response.data
      }
      if (currentSurvey.value?.id === id) {
        currentSurvey.value = { ...currentSurvey.value, ...response.data }
      }
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function removeSurvey(id) {
    loading.value = true
    error.value = null
    try {
      await deleteSurvey(id)
      surveys.value = surveys.value.filter((s) => s.id !== id)
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function setStatus(id, status) {
    loading.value = true
    error.value = null
    try {
      const response = await updateSurveyStatus(id, status)
      const index = surveys.value.findIndex((s) => s.id === id)
      if (index !== -1) {
        surveys.value[index] = response.data
      }
      if (currentSurvey.value?.id === id) {
        currentSurvey.value.status = status
      }
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function duplicate(id) {
    loading.value = true
    error.value = null
    try {
      const response = await duplicateSurvey(id)
      surveys.value.unshift(response.data)
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  // ============== Questions ==============

  async function addQuestion(surveyId, data) {
    loading.value = true
    error.value = null
    try {
      const response = await addQuestionApi(surveyId, data)
      if (currentSurvey.value?.id === surveyId) {
        currentSurvey.value.questions = currentSurvey.value.questions || []
        currentSurvey.value.questions.push(response.data)
      }
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function editQuestion(questionId, data) {
    loading.value = true
    error.value = null
    try {
      const response = await updateQuestionApi(questionId, data)
      if (currentSurvey.value) {
        const index = currentSurvey.value.questions?.findIndex((q) => q.id === questionId)
        if (index !== -1) {
          currentSurvey.value.questions[index] = response.data
        }
      }
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function removeQuestion(questionId) {
    loading.value = true
    error.value = null
    try {
      await deleteQuestionApi(questionId)
      if (currentSurvey.value) {
        currentSurvey.value.questions = currentSurvey.value.questions?.filter(
          (q) => q.id !== questionId
        )
      }
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function reorder(surveyId, questionIds) {
    loading.value = true
    error.value = null
    try {
      const response = await reorderQuestions(surveyId, questionIds)
      if (currentSurvey.value?.id === surveyId) {
        currentSurvey.value.questions = response.data
      }
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  // ============== Responses ==============

  async function fetchResponses(surveyId, params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getResponses(surveyId, params)
      responses.value = data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
    } finally {
      loading.value = false
    }
  }

  async function fetchResponse(responseId) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getResponse(responseId)
      currentResponse.value = data
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function removeResponse(responseId) {
    loading.value = true
    error.value = null
    try {
      await deleteResponse(responseId)
      responses.value = responses.value.filter((r) => r.id !== responseId)
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  // ============== Stats ==============

  async function fetchStats(surveyId) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getSurveyStats(surveyId)
      stats.value = data
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  // ============== Share ==============

  async function fetchShareLink(surveyId) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getShareLink(surveyId)
      shareLink.value = data
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function invite(surveyId, data) {
    loading.value = true
    error.value = null
    try {
      const response = await sendInvites(surveyId, data)
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  // Reset
  function reset() {
    currentSurvey.value = null
    responses.value = []
    currentResponse.value = null
    stats.value = null
    shareLink.value = null
    error.value = null
  }

  return {
    // State
    surveys,
    currentSurvey,
    responses,
    currentResponse,
    stats,
    shareLink,
    loading,
    error,
    // Computed
    activeSurveys,
    draftSurveys,
    questions,
    totalResponses,
    // Survey actions
    fetchSurveys,
    fetchSurvey,
    addSurvey,
    editSurvey,
    removeSurvey,
    setStatus,
    duplicate,
    // Question actions
    addQuestion,
    editQuestion,
    removeQuestion,
    reorder,
    // Response actions
    fetchResponses,
    fetchResponse,
    removeResponse,
    // Stats
    fetchStats,
    // Share
    fetchShareLink,
    invite,
    // Reset
    reset
  }
})
