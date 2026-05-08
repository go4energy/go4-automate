import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { useEngagementStore } from '@/stores/engagement'

/**
 * Outreach-Module: rendern den Pipeline-Selector im Header und zeigen
 * nur Daten der aktuell ausgewählten Pipeline.
 *
 * Mapping: Route-Prefix → Channel-Key in pipeline.channels.
 * - 'engagement' hat keinen Channel-Filter (zeigt alle Pipelines).
 */
export const OUTREACH_MODULE_CHANNELS = {
  engagement: null,
  emailmarketing: 'email',
  linkedin: 'linkedin',
  letter: 'letter',
  whatsapp: 'whatsapp',
}

export function moduleKeyForPath(path) {
  if (!path) return null
  const seg = path.replace(/^\/+/, '').split('/')[0]
  return Object.prototype.hasOwnProperty.call(OUTREACH_MODULE_CHANNELS, seg)
    ? seg
    : null
}

export function isOutreachPath(path) {
  return moduleKeyForPath(path) !== null
}

export const usePipelineContext = defineStore('pipelineContext', () => {
  const engagementStore = useEngagementStore()

  const stored = parseInt(localStorage.getItem('activePipelineId'))
  const activePipelineId = ref(Number.isFinite(stored) ? stored : null)

  // Aktuelles Modul (aus Router gesetzt) — bestimmt den Channel-Filter im Selector.
  const currentModuleKey = ref(null)

  const activePipeline = computed(() => {
    if (!activePipelineId.value) return null
    return (
      engagementStore.pipelines.find((p) => p.id === activePipelineId.value) ||
      null
    )
  })

  const label = computed(() => activePipeline.value?.name || 'Pipeline wählen')

  const isActive = computed(() => !!activePipelineId.value)

  // Pipelines, die für das aktuelle Modul relevant sind.
  // Engagement zeigt alle, andere Module nur die mit dem entsprechenden Kanal.
  const pipelinesForCurrentModule = computed(() => {
    const all = engagementStore.pipelines || []
    const channel = OUTREACH_MODULE_CHANNELS[currentModuleKey.value]
    if (!channel) return all
    return all.filter((p) => (p.channels || []).includes(channel))
  })

  // Ist die globale Auswahl mit dem aktuellen Modul kompatibel?
  // Beispiel: globale Pipeline hat keinen LinkedIn-Kanal, User ist im LinkedIn-Modul.
  const activePipelineMatchesModule = computed(() => {
    if (!activePipeline.value) return false
    const channel = OUTREACH_MODULE_CHANNELS[currentModuleKey.value]
    if (!channel) return true
    return (activePipeline.value.channels || []).includes(channel)
  })

  function setActivePipeline(id) {
    const numeric = id ? parseInt(id) : null
    activePipelineId.value = Number.isFinite(numeric) ? numeric : null
    if (activePipelineId.value) {
      localStorage.setItem('activePipelineId', activePipelineId.value)
    } else {
      localStorage.removeItem('activePipelineId')
    }
  }

  function clearPipeline() {
    setActivePipeline(null)
  }

  function setCurrentModule(key) {
    currentModuleKey.value = key
  }

  async function ensurePipelines() {
    if (engagementStore.pipelines.length === 0) {
      await engagementStore.fetchPipelines()
    }
    // Self-heal: Auswahl zeigt auf gelöschte Pipeline → reset.
    if (
      activePipelineId.value &&
      !engagementStore.pipelines.find((p) => p.id === activePipelineId.value)
    ) {
      clearPipeline()
    }
  }

  return {
    activePipelineId,
    activePipeline,
    label,
    isActive,
    currentModuleKey,
    pipelinesForCurrentModule,
    activePipelineMatchesModule,
    setActivePipeline,
    clearPipeline,
    setCurrentModule,
    ensurePipelines,
  }
})
