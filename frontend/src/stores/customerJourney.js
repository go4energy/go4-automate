import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import {
  getDashboardStats,
  getDashboardFeed,
  getDashboardFeedByLead,
  getFeedSources,
  getLeads,
  getLeadTimeline,
  getRefCodes,
  createRefCode,
  bulkCreateRefCodes,
  updateRefCode,
  deleteRefCode,
  getCampaigns,
  createCampaign,
  updateCampaign,
  deleteCampaign,
} from '@/api/customerJourney'

export const useCustomerJourneyStore = defineStore('customerJourney', () => {
  // State
  const stats = ref(null)
  const feed = ref([])
  const feedByLead = ref([])
  const activityMode = ref('time') // 'time' | 'lead'
  const expandedLeads = ref(new Set())
  const feedSources = ref([])
  const feedSourceFilter = ref(null)
  const leads = ref([])
  const timeline = ref([])
  const refCodes = ref([])
  const campaigns = ref([])
  const loading = ref(false)
  const feedLoading = ref(true)
  const error = ref(null)

  // Computed
  const totalLeads = computed(() => stats.value?.leads_total || 0)
  const totalRefCodes = computed(() => stats.value?.ref_codes_total || 0)
  const totalCampaigns = computed(() => stats.value?.campaigns_active || 0)

  // Dashboard
  async function fetchStats() {
    try {
      const { data } = await getDashboardStats()
      stats.value = data
    } catch (err) {
      error.value = err.message
    }
  }

  async function fetchFeed(limit = 50) {
    feedLoading.value = true
    try {
      const params = { limit }
      if (feedSourceFilter.value) params.source_site = feedSourceFilter.value
      const { data } = await getDashboardFeed(params)
      feed.value = data
    } catch (err) {
      error.value = err.message
    } finally {
      feedLoading.value = false
    }
  }

  async function fetchFeedSources() {
    try {
      const { data } = await getFeedSources()
      feedSources.value = data
    } catch (err) {
      error.value = err.message
    }
  }

  function setFeedSourceFilter(value) {
    feedSourceFilter.value = value || null
  }

  async function fetchFeedByLead(params = {}) {
    feedLoading.value = true
    try {
      const merged = { ...params }
      if (feedSourceFilter.value && !merged.source_site) {
        merged.source_site = feedSourceFilter.value
      }
      const { data } = await getDashboardFeedByLead(merged)
      feedByLead.value = data
    } catch (err) {
      error.value = err.message
    } finally {
      feedLoading.value = false
    }
  }

  function setActivityMode(mode) {
    activityMode.value = mode === 'lead' ? 'lead' : 'time'
  }

  function toggleLead(id) {
    const next = new Set(expandedLeads.value)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    expandedLeads.value = next
  }

  function expandAllLeads() {
    expandedLeads.value = new Set(feedByLead.value.map((l) => l.id))
  }

  function collapseAllLeads() {
    expandedLeads.value = new Set()
  }

  function isLeadExpanded(id) {
    return expandedLeads.value.has(id)
  }

  // Leads
  async function fetchLeads(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getLeads(params)
      leads.value = data
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function fetchTimeline(contactId) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getLeadTimeline(contactId)
      timeline.value = data
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  // Ref-Codes
  async function fetchRefCodes(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getRefCodes(params)
      refCodes.value = data
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function addRefCode(refData) {
    error.value = null
    try {
      const { data } = await createRefCode(refData)
      refCodes.value.unshift(data)
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function addBulkRefCodes(bulkData) {
    error.value = null
    try {
      const { data } = await bulkCreateRefCodes(bulkData)
      refCodes.value.unshift(...data)
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function editRefCode(id, refData) {
    error.value = null
    try {
      const { data } = await updateRefCode(id, refData)
      const idx = refCodes.value.findIndex((r) => r.id === id)
      if (idx !== -1) refCodes.value[idx] = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function removeRefCode(id) {
    error.value = null
    try {
      await deleteRefCode(id)
      refCodes.value = refCodes.value.filter((r) => r.id !== id)
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // Campaigns
  async function fetchCampaigns(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getCampaigns(params)
      campaigns.value = data
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function addCampaign(campaignData) {
    error.value = null
    try {
      const { data } = await createCampaign(campaignData)
      campaigns.value.unshift(data)
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function editCampaign(id, campaignData) {
    error.value = null
    try {
      const { data } = await updateCampaign(id, campaignData)
      const idx = campaigns.value.findIndex((c) => c.id === id)
      if (idx !== -1) campaigns.value[idx] = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function removeCampaign(id) {
    error.value = null
    try {
      await deleteCampaign(id)
      campaigns.value = campaigns.value.filter((c) => c.id !== id)
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  return {
    // State
    stats,
    feed,
    feedByLead,
    activityMode,
    expandedLeads,
    feedSources,
    feedSourceFilter,
    feedLoading,
    leads,
    timeline,
    refCodes,
    campaigns,
    loading,
    error,
    // Computed
    totalLeads,
    totalRefCodes,
    totalCampaigns,
    // Dashboard
    fetchStats,
    fetchFeed,
    fetchFeedByLead,
    fetchFeedSources,
    setFeedSourceFilter,
    setActivityMode,
    toggleLead,
    expandAllLeads,
    collapseAllLeads,
    isLeadExpanded,
    // Leads
    fetchLeads,
    fetchTimeline,
    // Ref-Codes
    fetchRefCodes,
    addRefCode,
    addBulkRefCodes,
    editRefCode,
    removeRefCode,
    // Campaigns
    fetchCampaigns,
    addCampaign,
    editCampaign,
    removeCampaign,
  }
})
