import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import {
  getContacts,
  createContact,
  updateContactStatus,
  pauseFollowup,
  getPipelines,
  getPipeline,
  createPipeline,
  updatePipeline,
  deletePipeline,
  addStage,
  updateStage,
  deleteStage,
  getDeals,
  getDeal,
  getKanbanBoard,
  createDeal,
  updateDeal,
  moveDeal,
  deleteDeal,
  getTasks,
  createTask,
  updateTask,
  deleteTask,
  getCalls,
  getCallStats,
  generateCallScript,
  logCall
} from '@/api/crm'

export const useCrmStore = defineStore('crm', () => {
  // State
  const contacts = ref([])
  const pipelines = ref([])
  const currentPipeline = ref(null)
  const kanbanBoard = ref(null)
  const deals = ref([])
  const currentDeal = ref(null)
  const tasks = ref([])
  const calls = ref([])
  const callStats = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // Computed
  const totalContacts = computed(() => contacts.value.length)
  const activeContacts = computed(() => contacts.value.filter((c) => c.status !== 'lost'))
  const defaultPipeline = computed(
    () => pipelines.value.find((p) => p.is_default) || pipelines.value[0]
  )
  const openDeals = computed(() => deals.value.filter((d) => d.status === 'open'))
  const openTasks = computed(() => tasks.value.filter((t) => t.status === 'open'))

  // ============== Legacy Contacts ==============

  async function fetchContacts(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getContacts(params)
      contacts.value = data
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function addContact(contactData) {
    loading.value = true
    error.value = null
    try {
      const { data } = await createContact(contactData)
      contacts.value.unshift(data)
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function changeStatus(contactId, status) {
    error.value = null
    try {
      const { data } = await updateContactStatus(contactId, status)
      const index = contacts.value.findIndex((c) => c.id === contactId)
      if (index !== -1) {
        contacts.value[index] = data
      }
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function toggleFollowupPause(contactId, paused) {
    error.value = null
    try {
      const { data } = await pauseFollowup(contactId, paused)
      const index = contacts.value.findIndex((c) => c.id === contactId)
      if (index !== -1) {
        contacts.value[index] = data
      }
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // ============== Pipelines ==============

  async function fetchPipelines() {
    loading.value = true
    error.value = null
    try {
      const { data } = await getPipelines()
      pipelines.value = data
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function fetchPipeline(id) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getPipeline(id)
      currentPipeline.value = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function addPipeline(pipelineData) {
    error.value = null
    try {
      const { data } = await createPipeline(pipelineData)
      pipelines.value.push(data)
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function editPipeline(id, pipelineData) {
    error.value = null
    try {
      const { data } = await updatePipeline(id, pipelineData)
      const index = pipelines.value.findIndex((p) => p.id === id)
      if (index !== -1) {
        pipelines.value[index] = data
      }
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function removePipeline(id) {
    error.value = null
    try {
      await deletePipeline(id)
      pipelines.value = pipelines.value.filter((p) => p.id !== id)
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // Stages
  async function addPipelineStage(pipelineId, stageData) {
    error.value = null
    try {
      const { data } = await addStage(pipelineId, stageData)
      if (currentPipeline.value?.id === pipelineId) {
        currentPipeline.value.stages.push(data)
      }
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function editStage(stageId, stageData) {
    error.value = null
    try {
      const { data } = await updateStage(stageId, stageData)
      if (currentPipeline.value) {
        const index = currentPipeline.value.stages.findIndex((s) => s.id === stageId)
        if (index !== -1) {
          currentPipeline.value.stages[index] = data
        }
      }
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function removeStage(stageId) {
    error.value = null
    try {
      await deleteStage(stageId)
      if (currentPipeline.value) {
        currentPipeline.value.stages = currentPipeline.value.stages.filter((s) => s.id !== stageId)
      }
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // ============== Deals ==============

  async function fetchDeals(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getDeals(params)
      deals.value = data
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function fetchDeal(id) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getDeal(id)
      currentDeal.value = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchKanbanBoard(pipelineId) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getKanbanBoard(pipelineId)
      kanbanBoard.value = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function addDeal(dealData) {
    error.value = null
    try {
      const { data } = await createDeal(dealData)
      deals.value.unshift(data)
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function editDeal(id, dealData) {
    error.value = null
    try {
      const { data } = await updateDeal(id, dealData)
      const index = deals.value.findIndex((d) => d.id === id)
      if (index !== -1) {
        deals.value[index] = data
      }
      if (currentDeal.value?.id === id) {
        currentDeal.value = data
      }
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function moveDealToStage(dealId, stageId) {
    error.value = null
    try {
      const { data } = await moveDeal(dealId, stageId)
      // Update in deals array
      const index = deals.value.findIndex((d) => d.id === dealId)
      if (index !== -1) {
        deals.value[index] = data
      }
      // Refresh kanban board if open
      if (kanbanBoard.value) {
        await fetchKanbanBoard(kanbanBoard.value.pipeline.id)
      }
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function removeDeal(id) {
    error.value = null
    try {
      await deleteDeal(id)
      deals.value = deals.value.filter((d) => d.id !== id)
      if (currentDeal.value?.id === id) {
        currentDeal.value = null
      }
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // ============== Tasks ==============

  async function fetchTasks(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getTasks(params)
      tasks.value = data
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function addTask(taskData) {
    error.value = null
    try {
      const { data } = await createTask(taskData)
      tasks.value.unshift(data)
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function editTask(id, taskData) {
    error.value = null
    try {
      const { data } = await updateTask(id, taskData)
      const index = tasks.value.findIndex((t) => t.id === id)
      if (index !== -1) {
        tasks.value[index] = data
      }
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function removeTask(id) {
    error.value = null
    try {
      await deleteTask(id)
      tasks.value = tasks.value.filter((t) => t.id !== id)
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function completeTask(id) {
    return editTask(id, { status: 'completed' })
  }

  // ============== Call Queue ==============

  async function fetchCalls(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getCalls(params)
      calls.value = data
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function fetchCallStats() {
    try {
      const { data } = await getCallStats()
      callStats.value = data
    } catch (err) {
      error.value = err.message
    }
  }

  async function generateScript(actionId) {
    try {
      const { data } = await generateCallScript(actionId)
      // Update the call in the list
      const idx = calls.value.findIndex((c) => c.id === actionId)
      if (idx !== -1) {
        calls.value[idx].suggested_content = data.script
      }
      return data.script
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function submitCallLog(actionId, logData) {
    try {
      const { data } = await logCall(actionId, logData)
      // Remove completed call from list
      calls.value = calls.value.filter((c) => c.id !== actionId)
      // Refresh stats
      await fetchCallStats()
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  function clearCurrent() {
    currentPipeline.value = null
    currentDeal.value = null
    kanbanBoard.value = null
  }

  return {
    // State
    contacts,
    pipelines,
    currentPipeline,
    kanbanBoard,
    deals,
    currentDeal,
    tasks,
    calls,
    callStats,
    loading,
    error,
    // Computed
    totalContacts,
    activeContacts,
    defaultPipeline,
    openDeals,
    openTasks,
    // Legacy Contact Actions
    fetchContacts,
    addContact,
    changeStatus,
    toggleFollowupPause,
    // Pipeline Actions
    fetchPipelines,
    fetchPipeline,
    addPipeline,
    editPipeline,
    removePipeline,
    addPipelineStage,
    editStage,
    removeStage,
    // Deal Actions
    fetchDeals,
    fetchDeal,
    fetchKanbanBoard,
    addDeal,
    editDeal,
    moveDealToStage,
    removeDeal,
    // Task Actions
    fetchTasks,
    addTask,
    editTask,
    removeTask,
    completeTask,
    // Call Queue Actions
    fetchCalls,
    fetchCallStats,
    generateScript,
    submitCallLog,
    // Utils
    clearCurrent
  }
})
