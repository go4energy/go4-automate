import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import {
  getDashboard,
  getPipelines,
  getPipeline,
  createPipeline,
  updatePipeline,
  deletePipeline,
  getPipelineStats,
  getPipelineFunnel,
  getEnrollments,
  getEnrollment,
  enrollContact,
  bulkEnrollContacts,
  updateEnrollment,
  unenrollContact,
  getActions,
  getApprovalQueue,
  getAction,
  approveAction,
  completeAction,
  cancelAction,
  getContactActivities,
  getEnrollmentActivities,
  getRecentActivities,
  logActivity,
  // Brain API
  getAvailableChannels,
  checkPrerequisites,
  brainSetupChat,
  createPipelineFromSetup,
  // Statistics API
  getStatistics,
  getChannelPerformance,
  getConversionFunnel,
  getResponseTimeAnalytics,
  getOptimizationInsights,
  // A/B Testing API
  getABTests,
  getABTest,
  createABTest,
  updateABTest,
  deleteABTest,
  startABTest,
  pauseABTest,
  completeABTest,
  getABTestResults,
  // Tracking API
  getTrackingLinks,
  createTrackingLink,
  createTrackingLinksBulk,
  deactivateTrackingLink,
  getTrackingEvents,
  getEventSummary,
  getPixelCode,
  recordConversion,
  getAttributionDashboard
} from '@/api/engagement'

export const useEngagementStore = defineStore('engagement', () => {
  // State
  const dashboard = ref(null)
  const pipelines = ref([])
  const currentPipeline = ref(null)
  const pipelineStats = ref(null)
  const pipelineFunnel = ref(null)
  const enrollments = ref([])
  const currentEnrollment = ref(null)
  const pendingActions = ref([])
  const approvalQueue = ref([])
  const currentAction = ref(null)
  const activities = ref([])
  const recentActivities = ref([])
  const availableChannels = ref([])
  const statistics = ref(null)
  const channelPerformance = ref(null)
  const conversionFunnel = ref(null)
  const responseAnalytics = ref(null)
  const optimizationInsights = ref(null)
  // A/B Testing state
  const abTests = ref([])
  const currentABTest = ref(null)
  const abTestResults = ref(null)
  // Tracking state
  const trackingLinks = ref([])
  const trackingEvents = ref([])
  const eventSummary = ref(null)
  const pixelCode = ref(null)
  const attributionDashboard = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // Computed
  const activePipelines = computed(() => pipelines.value.filter((p) => p.is_active))
  const activeEnrollments = computed(() => enrollments.value.filter((e) => e.status === 'active'))
  const pendingActionsCount = computed(() => approvalQueue.value.length)
  const runningABTests = computed(() => abTests.value.filter((t) => t.status === 'running'))
  const activeTrackingLinks = computed(() => trackingLinks.value.filter((l) => l.is_active))

  // ============== Dashboard ==============

  async function fetchDashboard() {
    loading.value = true
    error.value = null
    try {
      const { data } = await getDashboard()
      dashboard.value = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  // ============== Pipelines ==============

  async function fetchPipelines(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getPipelines(params)
      pipelines.value = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
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
      if (currentPipeline.value?.id === id) {
        currentPipeline.value = data
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
      if (currentPipeline.value?.id === id) {
        currentPipeline.value = null
      }
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function fetchPipelineStats(id) {
    error.value = null
    try {
      const { data } = await getPipelineStats(id)
      pipelineStats.value = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function fetchPipelineFunnel(id) {
    error.value = null
    try {
      const { data } = await getPipelineFunnel(id)
      pipelineFunnel.value = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // ============== Enrollments ==============

  async function fetchEnrollments(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getEnrollments(params)
      enrollments.value = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchEnrollment(id) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getEnrollment(id)
      currentEnrollment.value = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function enroll(enrollmentData) {
    error.value = null
    try {
      const { data } = await enrollContact(enrollmentData)
      enrollments.value.unshift(data)
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function bulkEnroll(bulkData) {
    error.value = null
    try {
      const { data } = await bulkEnrollContacts(bulkData)
      // Refresh enrollments after bulk operation
      await fetchEnrollments({ pipeline_id: bulkData.pipeline_id })
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function editEnrollment(id, enrollmentData) {
    error.value = null
    try {
      const { data } = await updateEnrollment(id, enrollmentData)
      const index = enrollments.value.findIndex((e) => e.id === id)
      if (index !== -1) {
        enrollments.value[index] = data
      }
      if (currentEnrollment.value?.id === id) {
        currentEnrollment.value = data
      }
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function unenroll(id) {
    error.value = null
    try {
      await unenrollContact(id)
      const index = enrollments.value.findIndex((e) => e.id === id)
      if (index !== -1) {
        enrollments.value[index].status = 'stopped'
      }
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // ============== Pending Actions ==============

  async function fetchActions(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getActions(params)
      pendingActions.value = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchApprovalQueue(module = null) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getApprovalQueue(module)
      approvalQueue.value = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchAction(id) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getAction(id)
      currentAction.value = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function approve(id, modifiedContent = null) {
    error.value = null
    try {
      const payload = modifiedContent ? { modified_content: modifiedContent } : {}
      const { data } = await approveAction(id, payload)
      // Update in approval queue
      approvalQueue.value = approvalQueue.value.filter((a) => a.id !== id)
      // Update in pending actions
      const index = pendingActions.value.findIndex((a) => a.id === id)
      if (index !== -1) {
        pendingActions.value[index] = data
      }
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function complete(id, result = null, errorMessage = null) {
    error.value = null
    try {
      const payload = {}
      if (result) payload.result = result
      if (errorMessage) payload.error_message = errorMessage
      const { data } = await completeAction(id, payload)
      // Update in pending actions
      const index = pendingActions.value.findIndex((a) => a.id === id)
      if (index !== -1) {
        pendingActions.value[index] = data
      }
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function cancel(id) {
    error.value = null
    try {
      const { data } = await cancelAction(id)
      // Remove from approval queue
      approvalQueue.value = approvalQueue.value.filter((a) => a.id !== id)
      // Update in pending actions
      const index = pendingActions.value.findIndex((a) => a.id === id)
      if (index !== -1) {
        pendingActions.value[index] = data
      }
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // ============== Activities ==============

  async function fetchContactActivities(contactId, limit = 50) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getContactActivities(contactId, limit)
      activities.value = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchEnrollmentActivities(enrollmentId) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getEnrollmentActivities(enrollmentId)
      activities.value = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchRecentActivities(limit = 20, channel = null) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getRecentActivities(limit, channel)
      recentActivities.value = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function addActivity(activityData) {
    error.value = null
    try {
      const { data } = await logActivity(activityData)
      activities.value.unshift(data)
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // ============== Brain API ==============

  async function fetchAvailableChannels() {
    error.value = null
    try {
      const { data } = await getAvailableChannels()
      availableChannels.value = data.channels
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function checkChannelPrerequisites(channels) {
    error.value = null
    try {
      const { data } = await checkPrerequisites(channels)
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function sendSetupMessage(message, conversationHistory = []) {
    error.value = null
    try {
      const { data } = await brainSetupChat(message, conversationHistory)
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function createFromSetup(config) {
    error.value = null
    try {
      const { data } = await createPipelineFromSetup(config)
      pipelines.value.push(data.pipeline)
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // ============== Statistics ==============

  async function fetchStatistics(pipelineId = null, days = 30) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getStatistics(pipelineId, days)
      statistics.value = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchChannelPerformance(pipelineId = null, days = 30) {
    error.value = null
    try {
      const { data } = await getChannelPerformance(pipelineId, days)
      channelPerformance.value = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function fetchConversionFunnel(pipelineId = null, days = 30) {
    error.value = null
    try {
      const { data } = await getConversionFunnel(pipelineId, days)
      conversionFunnel.value = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function fetchResponseAnalytics(pipelineId = null, days = 30) {
    error.value = null
    try {
      const { data } = await getResponseTimeAnalytics(pipelineId, days)
      responseAnalytics.value = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function fetchOptimizationInsights(pipelineId = null, days = 90) {
    error.value = null
    try {
      const { data } = await getOptimizationInsights(pipelineId, days)
      optimizationInsights.value = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // ============== A/B Testing ==============

  async function fetchABTests(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getABTests(params)
      abTests.value = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchABTest(id) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getABTest(id)
      currentABTest.value = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function addABTest(testData) {
    error.value = null
    try {
      const { data } = await createABTest(testData)
      abTests.value.push(data)
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function editABTest(id, testData) {
    error.value = null
    try {
      const { data } = await updateABTest(id, testData)
      const index = abTests.value.findIndex((t) => t.id === id)
      if (index !== -1) {
        abTests.value[index] = data
      }
      if (currentABTest.value?.id === id) {
        currentABTest.value = data
      }
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function removeABTest(id) {
    error.value = null
    try {
      await deleteABTest(id)
      abTests.value = abTests.value.filter((t) => t.id !== id)
      if (currentABTest.value?.id === id) {
        currentABTest.value = null
      }
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function startTest(id) {
    error.value = null
    try {
      const { data } = await startABTest(id)
      const index = abTests.value.findIndex((t) => t.id === id)
      if (index !== -1) {
        abTests.value[index] = data
      }
      if (currentABTest.value?.id === id) {
        currentABTest.value = data
      }
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function pauseTest(id) {
    error.value = null
    try {
      const { data } = await pauseABTest(id)
      const index = abTests.value.findIndex((t) => t.id === id)
      if (index !== -1) {
        abTests.value[index] = data
      }
      if (currentABTest.value?.id === id) {
        currentABTest.value = data
      }
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function completeTest(id, winnerVariantId = null) {
    error.value = null
    try {
      const { data } = await completeABTest(id, winnerVariantId)
      const index = abTests.value.findIndex((t) => t.id === id)
      if (index !== -1) {
        abTests.value[index] = data
      }
      if (currentABTest.value?.id === id) {
        currentABTest.value = data
      }
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function fetchABTestResults(id) {
    error.value = null
    try {
      const { data } = await getABTestResults(id)
      abTestResults.value = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // ============== Tracking Links ==============

  async function fetchTrackingLinks(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getTrackingLinks(params)
      trackingLinks.value = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function addTrackingLink(linkData) {
    error.value = null
    try {
      const { data } = await createTrackingLink(linkData)
      trackingLinks.value.unshift(data)
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function addTrackingLinksBulk(bulkData) {
    error.value = null
    try {
      const { data } = await createTrackingLinksBulk(bulkData)
      trackingLinks.value.unshift(...data)
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function deactivateLink(id) {
    error.value = null
    try {
      const { data } = await deactivateTrackingLink(id)
      const index = trackingLinks.value.findIndex((l) => l.id === id)
      if (index !== -1) {
        trackingLinks.value[index] = data
      }
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // ============== Tracking Events ==============

  async function fetchTrackingEvents(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getTrackingEvents(params)
      trackingEvents.value = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchEventSummary(params = {}) {
    error.value = null
    try {
      const { data } = await getEventSummary(params)
      eventSummary.value = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function fetchPixelCode() {
    error.value = null
    try {
      const { data } = await getPixelCode()
      pixelCode.value = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // ============== Attribution ==============

  async function addConversion(conversionData) {
    error.value = null
    try {
      const { data } = await recordConversion(conversionData)
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function fetchAttributionDashboard(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getAttributionDashboard(params)
      attributionDashboard.value = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  // ============== Utils ==============

  function clearCurrent() {
    currentPipeline.value = null
    currentEnrollment.value = null
    currentAction.value = null
    currentABTest.value = null
    pipelineStats.value = null
    pipelineFunnel.value = null
    abTestResults.value = null
  }

  function clearAll() {
    dashboard.value = null
    pipelines.value = []
    enrollments.value = []
    pendingActions.value = []
    approvalQueue.value = []
    activities.value = []
    recentActivities.value = []
    abTests.value = []
    trackingLinks.value = []
    trackingEvents.value = []
    eventSummary.value = null
    pixelCode.value = null
    attributionDashboard.value = null
    clearCurrent()
  }

  return {
    // State
    dashboard,
    pipelines,
    currentPipeline,
    pipelineStats,
    pipelineFunnel,
    enrollments,
    currentEnrollment,
    pendingActions,
    approvalQueue,
    currentAction,
    activities,
    recentActivities,
    loading,
    error,
    // A/B Testing State
    abTests,
    currentABTest,
    abTestResults,
    // Tracking State
    trackingLinks,
    trackingEvents,
    eventSummary,
    pixelCode,
    attributionDashboard,
    // Computed
    activePipelines,
    activeEnrollments,
    pendingActionsCount,
    runningABTests,
    activeTrackingLinks,
    // Dashboard
    fetchDashboard,
    // Pipeline Actions
    fetchPipelines,
    fetchPipeline,
    addPipeline,
    editPipeline,
    removePipeline,
    fetchPipelineStats,
    fetchPipelineFunnel,
    // Enrollment Actions
    fetchEnrollments,
    fetchEnrollment,
    enroll,
    bulkEnroll,
    editEnrollment,
    unenroll,
    // Action Actions
    fetchActions,
    fetchApprovalQueue,
    fetchAction,
    approve,
    complete,
    cancel,
    // Activity Actions
    fetchContactActivities,
    fetchEnrollmentActivities,
    fetchRecentActivities,
    addActivity,
    // Brain Actions
    availableChannels,
    fetchAvailableChannels,
    checkChannelPrerequisites,
    sendSetupMessage,
    createFromSetup,
    // Statistics Actions
    statistics,
    channelPerformance,
    conversionFunnel,
    responseAnalytics,
    optimizationInsights,
    fetchStatistics,
    fetchChannelPerformance,
    fetchConversionFunnel,
    fetchResponseAnalytics,
    fetchOptimizationInsights,
    // A/B Testing Actions
    fetchABTests,
    fetchABTest,
    addABTest,
    editABTest,
    removeABTest,
    startTest,
    pauseTest,
    completeTest,
    fetchABTestResults,
    // Tracking Link Actions
    fetchTrackingLinks,
    addTrackingLink,
    addTrackingLinksBulk,
    deactivateLink,
    // Tracking Event Actions
    fetchTrackingEvents,
    fetchEventSummary,
    fetchPixelCode,
    // Attribution Actions
    addConversion,
    fetchAttributionDashboard,
    // Utils
    clearCurrent,
    clearAll
  }
})
