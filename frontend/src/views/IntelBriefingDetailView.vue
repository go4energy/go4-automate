<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { intelApi } from '@/api/intel'
import PageHeader from '@/components/ui/PageHeader.vue'

const props = defineProps({ id: { type: [String, Number], default: null } })
const route = useRoute()

const briefingId = computed(() => Number(props.id || route.params.id))
const briefing = ref(null)
const error = ref(null)

onMounted(async () => {
  try {
    briefing.value = await intelApi.getBriefing(briefingId.value)
  } catch (err) {
    error.value = err.response?.data?.detail || err.message
  }
})

const sections = computed(() => briefing.value?.payload?.sections || [])
const stats = computed(() => briefing.value?.payload?.stats || {})

const typeLabel = {
  competitor_change: 'Wettbewerber-Bewegung',
  market_gap_hypothesis: 'Markt-Lücke',
  regulatory_alert: 'Regulatorisch'
}
const typeColor = {
  competitor_change: 'border-orange-200 bg-orange-50',
  market_gap_hypothesis: 'border-purple-200 bg-purple-50',
  regulatory_alert: 'border-blue-200 bg-blue-50'
}
</script>

<template>
  <div>
    <PageHeader
      :title="
        briefing
          ? `Briefing vom ${new Date(briefing.period_end).toLocaleDateString('de-DE')}`
          : 'Briefing'
      "
      info-module="intel"
    />

    <div v-if="error" class="rounded-lg bg-red-50 p-4 text-sm text-red-700">{{ error }}</div>
    <div v-else-if="!briefing" class="text-sm text-go4-muted dark:text-gray-400">
      Lade Briefing…
    </div>

    <template v-else>
      <div class="mb-6 rounded-lg border border-go4-primary/20 bg-go4-primary/5 p-6">
        <p class="mb-2 text-sm uppercase tracking-wide text-go4-primary">Zusammenfassung</p>
        <p class="text-base leading-relaxed text-go4-secondary dark:text-gray-100">
          {{ briefing.tts_summary }}
        </p>
      </div>

      <div class="mb-6 grid grid-cols-3 gap-3">
        <div class="rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800">
          <p class="text-xs text-go4-muted">Sources geprüft</p>
          <p class="text-xl font-bold">{{ stats.sources_checked || 0 }}</p>
        </div>
        <div class="rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800">
          <p class="text-xs text-go4-muted">Änderungen erkannt</p>
          <p class="text-xl font-bold">{{ stats.changes_detected || 0 }}</p>
        </div>
        <div class="rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800">
          <p class="text-xs text-go4-muted">Nach Triage</p>
          <p class="text-xl font-bold">{{ stats.after_triage || 0 }}</p>
        </div>
      </div>

      <div class="space-y-4">
        <article
          v-for="(sec, idx) in sections"
          :key="idx"
          class="rounded-lg border p-5"
          :class="typeColor[sec.type] || 'border-gray-200 bg-white'"
        >
          <div class="mb-3 flex items-center justify-between">
            <span class="text-xs font-medium uppercase tracking-wide">
              {{ typeLabel[sec.type] || sec.type }} · {{ sec.change_type }}
            </span>
            <span class="text-xs font-semibold">
              Bedeutung: {{ Math.round((sec.significance || 0) * 100) }}%
            </span>
          </div>
          <h3 class="mb-1 text-lg font-bold">{{ sec.headline }}</h3>
          <p class="mb-3 text-sm text-gray-700">
            Target: <strong>{{ sec.watch_target }}</strong>
          </p>
          <div class="mb-3">
            <p class="mb-1 text-xs uppercase text-go4-muted">Zusammenfassung</p>
            <p class="text-sm leading-relaxed">{{ sec.summary }}</p>
          </div>
          <div class="mb-3">
            <p class="mb-1 text-xs uppercase text-go4-muted">Auswirkung für uns</p>
            <p class="text-sm leading-relaxed">{{ sec.impact_for_us }}</p>
          </div>
          <div v-if="sec.suggested_action">
            <p class="mb-1 text-xs uppercase text-go4-muted">Empfohlene Aktion</p>
            <p class="text-sm leading-relaxed">{{ sec.suggested_action }}</p>
          </div>
          <div v-if="sec.evidence?.length" class="mt-3 border-t border-current/10 pt-3">
            <p class="mb-1 text-xs uppercase text-go4-muted">Quellen</p>
            <ul class="space-y-1">
              <li v-for="(ev, i) in sec.evidence" :key="i" class="text-xs">
                <a :href="ev.url" target="_blank" rel="noopener" class="underline hover:no-underline">
                  {{ ev.url }}
                </a>
              </li>
            </ul>
          </div>
        </article>
      </div>
    </template>
  </div>
</template>
