import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { getLeads, createLead, updateLeadStatus, pauseFollowup } from '@/api/leads'

export const useLeadStore = defineStore('leads', () => {
  const leads = ref([])
  const loading = ref(false)
  const error = ref(null)

  const totalLeads = computed(() => leads.value.length)
  const activeLeads = computed(() => leads.value.filter((l) => l.status !== 'lost'))

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

  async function addLead(leadData) {
    loading.value = true
    error.value = null
    try {
      const { data } = await createLead(leadData)
      leads.value.unshift(data)
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function changeStatus(leadId, status) {
    error.value = null
    try {
      const { data } = await updateLeadStatus(leadId, status)
      const index = leads.value.findIndex((l) => l.id === leadId)
      if (index !== -1) {
        leads.value[index] = data
      }
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function toggleFollowupPause(leadId, paused) {
    error.value = null
    try {
      const { data } = await pauseFollowup(leadId, paused)
      const index = leads.value.findIndex((l) => l.id === leadId)
      if (index !== -1) {
        leads.value[index] = data
      }
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  return {
    leads,
    loading,
    error,
    totalLeads,
    activeLeads,
    fetchLeads,
    addLead,
    changeStatus,
    toggleFollowupPause
  }
})
