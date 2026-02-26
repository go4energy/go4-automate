import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import {
  getFunnels,
  getFunnel,
  createFunnel,
  updateFunnel,
  deleteFunnel,
  addStage as addStageApi,
  updateStage as updateStageApi,
  deleteStage as deleteStageApi,
  getCompanies,
  getCompany,
  createCompany,
  updateCompany,
  deleteCompany,
  getProspects,
  getProspect,
  getKanbanBoard,
  createProspect,
  updateProspect,
  moveProspect as moveProspectApi,
  deleteProspect,
  checkDuplicate,
  bulkImportProspects,
  createActivity,
  getProspectActivities,
  initiateHandoff,
  getHandoffs,
  retryHandoff as retryHandoffApi
} from '@/api/funnels'

export const useFunnelsStore = defineStore('funnels', () => {
  // State
  const funnels = ref([])
  const currentFunnel = ref(null)
  const companies = ref([])
  const currentCompany = ref(null)
  const prospects = ref([])
  const currentProspect = ref(null)
  const kanbanBoard = ref(null)
  const activities = ref([])
  const handoffs = ref([])
  const loading = ref(false)
  const error = ref(null)

  // Computed
  const activeFunnels = computed(() => funnels.value.filter((f) => f.status === 'active'))
  const totalProspects = computed(() =>
    funnels.value.reduce((sum, f) => sum + (f.prospect_count || 0), 0)
  )
  const qualifiedProspects = computed(() => prospects.value.filter((p) => p.status === 'qualified'))
  const stages = computed(() => currentFunnel.value?.stages || [])
  const kanbanData = computed(() => kanbanBoard.value?.stages || [])

  // ============== Funnels ==============

  async function fetchFunnels(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getFunnels(params)
      funnels.value = data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
    } finally {
      loading.value = false
    }
  }

  async function fetchFunnel(id) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getFunnel(id)
      currentFunnel.value = data
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function addFunnel(funnelData) {
    error.value = null
    try {
      const { data } = await createFunnel(funnelData)
      funnels.value.unshift(data)
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  async function editFunnel(id, funnelData) {
    error.value = null
    try {
      const { data } = await updateFunnel(id, funnelData)
      const index = funnels.value.findIndex((f) => f.id === id)
      if (index !== -1) {
        funnels.value[index] = data
      }
      if (currentFunnel.value?.id === id) {
        currentFunnel.value = data
      }
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  async function removeFunnel(id) {
    error.value = null
    try {
      await deleteFunnel(id)
      funnels.value = funnels.value.filter((f) => f.id !== id)
      if (currentFunnel.value?.id === id) {
        currentFunnel.value = null
      }
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  // ============== Stages ==============

  async function fetchStages(funnelId) {
    // Stages come from the funnel - ensure we have the current funnel loaded
    if (!currentFunnel.value || currentFunnel.value.id !== funnelId) {
      await fetchFunnel(funnelId)
    }
    return currentFunnel.value?.stages || []
  }

  async function addStageToFunnel(funnelId, stageData) {
    error.value = null
    try {
      const { data } = await addStageApi(funnelId, stageData)
      if (currentFunnel.value?.id === funnelId) {
        currentFunnel.value.stages.push(data)
      }
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  async function editStage(stageId, stageData) {
    error.value = null
    try {
      const { data } = await updateStageApi(stageId, stageData)
      if (currentFunnel.value) {
        const index = currentFunnel.value.stages.findIndex((s) => s.id === stageId)
        if (index !== -1) {
          currentFunnel.value.stages[index] = data
        }
      }
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  async function removeStage(stageId) {
    error.value = null
    try {
      await deleteStageApi(stageId)
      if (currentFunnel.value) {
        currentFunnel.value.stages = currentFunnel.value.stages.filter((s) => s.id !== stageId)
      }
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  // ============== Companies ==============

  async function fetchCompanies(funnelId, params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getCompanies(funnelId, params)
      companies.value = data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
    } finally {
      loading.value = false
    }
  }

  async function fetchCompany(companyId) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getCompany(companyId)
      currentCompany.value = data
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function addCompany(funnelId, companyData) {
    error.value = null
    try {
      const { data } = await createCompany(funnelId, companyData)
      companies.value.unshift(data)
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  async function editCompany(companyId, companyData) {
    error.value = null
    try {
      const { data } = await updateCompany(companyId, companyData)
      const index = companies.value.findIndex((c) => c.id === companyId)
      if (index !== -1) {
        companies.value[index] = data
      }
      if (currentCompany.value?.id === companyId) {
        currentCompany.value = data
      }
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  async function removeCompany(companyId) {
    error.value = null
    try {
      await deleteCompany(companyId)
      companies.value = companies.value.filter((c) => c.id !== companyId)
      if (currentCompany.value?.id === companyId) {
        currentCompany.value = null
      }
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  // ============== Prospects ==============

  async function fetchProspects(funnelId, params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getProspects(funnelId, params)
      prospects.value = data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
    } finally {
      loading.value = false
    }
  }

  async function fetchProspect(prospectId) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getProspect(prospectId)
      currentProspect.value = data
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchKanbanBoard(funnelId) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getKanbanBoard(funnelId)
      kanbanBoard.value = data
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function addProspect(funnelId, prospectData) {
    error.value = null
    try {
      const { data } = await createProspect(funnelId, prospectData)
      prospects.value.unshift(data)
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  async function editProspect(prospectId, prospectData) {
    error.value = null
    try {
      const { data } = await updateProspect(prospectId, prospectData)
      const index = prospects.value.findIndex((p) => p.id === prospectId)
      if (index !== -1) {
        prospects.value[index] = data
      }
      if (currentProspect.value?.id === prospectId) {
        currentProspect.value = data
      }
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  async function moveProspect(prospectId, stageId) {
    error.value = null
    try {
      const { data } = await moveProspectApi(prospectId, stageId)
      // Update in prospects array
      const index = prospects.value.findIndex((p) => p.id === prospectId)
      if (index !== -1) {
        prospects.value[index] = data
      }
      // Refresh kanban board if open
      if (kanbanBoard.value) {
        await fetchKanbanBoard(kanbanBoard.value.funnel.id)
      }
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  async function removeProspect(prospectId) {
    error.value = null
    try {
      await deleteProspect(prospectId)
      prospects.value = prospects.value.filter((p) => p.id !== prospectId)
      if (currentProspect.value?.id === prospectId) {
        currentProspect.value = null
      }
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  // ============== Duplicate Check ==============

  async function checkForDuplicate(data) {
    error.value = null
    try {
      const { data: result } = await checkDuplicate(data)
      return result
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  // ============== Bulk Import ==============

  async function importProspects(funnelId, importData) {
    loading.value = true
    error.value = null
    try {
      const { data } = await bulkImportProspects(funnelId, importData)
      // Refresh prospects list
      if (currentFunnel.value?.id === funnelId) {
        await fetchProspects(funnelId)
      }
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  // ============== Activities ==============

  async function fetchProspectActivities(prospectId) {
    error.value = null
    try {
      const { data } = await getProspectActivities(prospectId)
      activities.value = data
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  async function logActivity(prospectId, activityData) {
    error.value = null
    try {
      const { data } = await createActivity(prospectId, activityData)
      activities.value.unshift(data)
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  // ============== Handoffs ==============

  async function startHandoff(prospectId, handoffData) {
    error.value = null
    try {
      const { data } = await initiateHandoff(prospectId, handoffData)
      // Update prospect status
      const index = prospects.value.findIndex((p) => p.id === prospectId)
      if (index !== -1) {
        prospects.value[index].status = 'handed_off'
      }
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  async function fetchHandoffs(params = {}) {
    error.value = null
    try {
      const { data } = await getHandoffs(params)
      handoffs.value = data
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  async function retryHandoff(handoffId) {
    error.value = null
    try {
      const { data } = await retryHandoffApi(handoffId)
      const index = handoffs.value.findIndex((h) => h.id === handoffId)
      if (index !== -1) {
        handoffs.value[index] = data
      }
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  // ============== Utils ==============

  function clearCurrent() {
    currentFunnel.value = null
    currentCompany.value = null
    currentProspect.value = null
    kanbanBoard.value = null
    companies.value = []
    prospects.value = []
    activities.value = []
  }

  return {
    // State
    funnels,
    currentFunnel,
    companies,
    currentCompany,
    prospects,
    currentProspect,
    kanbanBoard,
    activities,
    handoffs,
    loading,
    error,
    // Computed
    activeFunnels,
    totalProspects,
    qualifiedProspects,
    stages,
    kanbanData,
    // Funnel Actions
    fetchFunnels,
    fetchFunnel,
    addFunnel,
    editFunnel,
    removeFunnel,
    // Stage Actions
    fetchStages,
    addStage: addStageToFunnel,
    editStage,
    removeStage,
    // Company Actions
    fetchCompanies,
    fetchCompany,
    addCompany,
    editCompany,
    removeCompany,
    // Prospect Actions
    fetchProspects,
    fetchProspect,
    fetchKanban: fetchKanbanBoard,
    addProspect,
    editProspect,
    moveProspect,
    removeProspect,
    // Duplicate Check
    checkForDuplicate,
    // Bulk Import
    importProspects,
    // Activity Actions
    fetchActivities: fetchProspectActivities,
    logActivity,
    // Handoff Actions
    triggerHandoff: startHandoff,
    fetchHandoffs,
    retryHandoff,
    // Utils
    clearCurrent
  }
})
