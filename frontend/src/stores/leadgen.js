import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  advanceRunStage,
  createCampaign,
  deleteCampaign,
  downloadAccountsCsv,
  downloadApolloCsv,
  downloadLeadsCsv,
  executeHandoff,
  getCampaign,
  getCampaignStats,
  getPlace,
  getRun,
  intakeCampaignParameters,
  listCampaigns,
  listPlacesForCampaign,
  listRunsForCampaign,
  stopRun,
  previewExport,
  previewHandoff,
  rejectPlace,
  resumeRun,
  startEnrichRun,
  startRun,
  updateCampaign
} from '@/api/leadgen'

export const useLeadgenStore = defineStore('leadgen', () => {
  const campaigns = ref([])
  const currentCampaign = ref(null)
  const currentCampaignStats = ref(null)
  const runs = ref([])
  const currentRun = ref(null)
  const places = ref({ items: [], total: 0, page: 1, size: 50 })
  const currentPlace = ref(null)
  const loading = ref(false)
  const error = ref(null)

  function _reset() {
    error.value = null
    loading.value = true
  }
  function _finish(err) {
    loading.value = false
    if (err) {
      error.value = err.response?.data?.detail || err.message || 'Fehler'
      throw err
    }
  }

  async function fetchCampaigns(params = {}) {
    _reset()
    try {
      const { data } = await listCampaigns(params)
      campaigns.value = data
      _finish()
    } catch (e) {
      _finish(e)
    }
  }

  async function fetchCampaign(id) {
    _reset()
    try {
      const { data } = await getCampaign(id)
      currentCampaign.value = data
      _finish()
      return data
    } catch (e) {
      _finish(e)
    }
  }

  async function createNewCampaign(data) {
    _reset()
    try {
      const { data: created } = await createCampaign(data)
      campaigns.value = [created, ...campaigns.value]
      _finish()
      return created
    } catch (e) {
      _finish(e)
    }
  }

  async function saveCampaign(id, data) {
    _reset()
    try {
      const { data: updated } = await updateCampaign(id, data)
      currentCampaign.value = updated
      _finish()
      return updated
    } catch (e) {
      _finish(e)
    }
  }

  async function removeCampaign(id) {
    _reset()
    try {
      await deleteCampaign(id)
      campaigns.value = campaigns.value.filter((c) => c.id !== id)
      _finish()
    } catch (e) {
      _finish(e)
    }
  }

  async function fetchStats(id) {
    _reset()
    try {
      const { data } = await getCampaignStats(id)
      currentCampaignStats.value = data
      _finish()
    } catch (e) {
      _finish(e)
    }
  }

  async function fetchRuns(campaignId) {
    _reset()
    try {
      const { data } = await listRunsForCampaign(campaignId)
      runs.value = data
      _finish()
    } catch (e) {
      _finish(e)
    }
  }

  async function launchRun(campaignId) {
    _reset()
    try {
      const { data } = await startRun(campaignId)
      runs.value = [data, ...runs.value]
      _finish()
      return data
    } catch (e) {
      _finish(e)
    }
  }

  async function launchEnrichRun(
    campaignId,
    {
      limit,
      sampling = 'top_rated',
      stages,
      minMatchScore,
      enrichCompanies,
      apolloValidateExistingUrls,
      apolloRevealEmail,
      apolloRevealPhone
    } = {}
  ) {
    _reset()
    try {
      const { data } = await startEnrichRun(campaignId, {
        limit,
        sampling,
        stages,
        minMatchScore,
        enrichCompanies,
        apolloValidateExistingUrls,
        apolloRevealEmail,
        apolloRevealPhone
      })
      runs.value = [data, ...runs.value]
      _finish()
      return data
    } catch (e) {
      _finish(e)
    }
  }

  async function fetchRun(id) {
    _reset()
    try {
      const { data } = await getRun(id)
      currentRun.value = data
      _finish()
      return data
    } catch (e) {
      _finish(e)
    }
  }

  async function stopRunAction(id) {
    _reset()
    try {
      const { data } = await stopRun(id)
      _finish()
      return data
    } catch (e) {
      _finish(e)
    }
  }

  async function resumeRunAction(id, additionalBudget = null) {
    _reset()
    try {
      const { data } = await resumeRun(id, additionalBudget)
      _finish()
      return data
    } catch (e) {
      _finish(e)
    }
  }

  async function advanceRunStageAction(id) {
    _reset()
    try {
      const { data } = await advanceRunStage(id)
      _finish()
      return data
    } catch (e) {
      _finish(e)
    }
  }

  async function fetchPlaces(campaignId, params = {}) {
    _reset()
    try {
      const { data } = await listPlacesForCampaign(campaignId, params)
      places.value = data
      _finish()
    } catch (e) {
      _finish(e)
    }
  }

  async function fetchPlace(id) {
    _reset()
    try {
      const { data } = await getPlace(id)
      currentPlace.value = data
      _finish()
      return data
    } catch (e) {
      _finish(e)
    }
  }

  async function rejectPlaceAction(id, reason) {
    _reset()
    try {
      const { data } = await rejectPlace(id, reason)
      _finish()
      return data
    } catch (e) {
      _finish(e)
    }
  }

  async function handoffPreview(campaignId, body) {
    _reset()
    try {
      const { data } = await previewHandoff(campaignId, body)
      _finish()
      return data
    } catch (e) {
      _finish(e)
    }
  }

  async function handoffExecute(campaignId, body) {
    _reset()
    try {
      const { data } = await executeHandoff(campaignId, body)
      _finish()
      return data
    } catch (e) {
      _finish(e)
    }
  }

  async function exportPreview(campaignId, body) {
    _reset()
    try {
      const { data } = await previewExport(campaignId, body)
      _finish()
      return data
    } catch (e) {
      _finish(e)
    }
  }

  async function exportDownload(campaignId, kind, params) {
    // kind: 'accounts' | 'leads' | 'apollo'
    _reset()
    try {
      let fn
      let filename
      if (kind === 'apollo') {
        fn = downloadApolloCsv
        filename = `apollo_contacts_camp_${campaignId}.csv`
      } else if (kind === 'leads') {
        fn = downloadLeadsCsv
        filename = `sales_nav_leads_camp_${campaignId}.csv`
      } else {
        fn = downloadAccountsCsv
        filename = `sales_nav_accounts_camp_${campaignId}.csv`
      }
      const response = await fn(campaignId, params)
      const blob = new Blob([response.data], { type: 'text/csv;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      _finish()
    } catch (e) {
      _finish(e)
    }
  }

  async function suggestParameters(text) {
    _reset()
    try {
      const { data } = await intakeCampaignParameters(text)
      _finish()
      return data
    } catch (e) {
      _finish(e)
    }
  }

  return {
    campaigns,
    currentCampaign,
    currentCampaignStats,
    runs,
    currentRun,
    places,
    currentPlace,
    loading,
    error,
    fetchCampaigns,
    fetchCampaign,
    createNewCampaign,
    saveCampaign,
    removeCampaign,
    fetchStats,
    fetchRuns,
    launchRun,
    launchEnrichRun,
    fetchRun,
    stopRunAction,
    resumeRunAction,
    advanceRunStageAction,
    fetchPlaces,
    fetchPlace,
    rejectPlaceAction,
    handoffPreview,
    handoffExecute,
    exportPreview,
    exportDownload,
    suggestParameters
  }
})
