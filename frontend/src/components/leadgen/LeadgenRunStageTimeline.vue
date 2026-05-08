<script setup>
import { computed } from 'vue'

const props = defineProps({
  run: { type: Object, required: true }
})

const STAGE_DEFS = [
  { key: 'places',    label: 'Discovery (Google Places)' },
  { key: 'impressum', label: 'Impressum-Scraping' },
  { key: 'verify',    label: 'Verify (Serper)' },
  { key: 'llm',       label: 'LLM-Analyse (Haiku)' },
  { key: 'linkedin',  label: 'LinkedIn-Anreicherung (Serper + Gender)' },
  { key: 'apollo',    label: 'Apollo-Anreicherung (LinkedIn-Match)' }
]

const STATUS_ICON = {
  pending:   { glyph: '○', cls: 'text-gray-400' },
  running:   { glyph: '▶', cls: 'text-green-600 animate-pulse' },
  completed: { glyph: '✓', cls: 'text-go4-primary' },
  skipped:   { glyph: '⏭', cls: 'text-gray-400' },
  failed:    { glyph: '✗', cls: 'text-red-600' }
}

function fmtCost(cents) {
  if (!cents) return '0,00 €'
  return (cents / 100).toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €'
}

function fmtDuration(start, end) {
  if (!start) return null
  const s = new Date(start)
  const e = end ? new Date(end) : new Date()
  const secs = Math.max(0, Math.round((e - s) / 1000))
  if (secs < 60) return `${secs}s`
  const mins = Math.floor(secs / 60)
  if (mins < 60) return `${mins} min`
  const hrs = Math.floor(mins / 60)
  return `${hrs}h ${mins % 60}m`
}

const stages = computed(() => {
  const block = props.run?.stage_state?.stages || {}
  const explicitStages = props.run?.stage_state?.explicit_stages || null
  const currentStage = props.run?.current_stage
  const isFinal = ['completed', 'failed'].includes(props.run?.status)
  const runState = props.run?.stage_state || {}

  // Dynamic timeline: only render stages that were actually executed.
  // The worker writes ``status: 'skipped'`` entries for unselected stages
  // (so the timeline knows about them) but we don't want to show those —
  // they clutter the list with greyed-out "übersprungen" rows. Show:
  //  1. Stages with a non-skipped status entry (running/completed/failed)
  //  2. The currently-running stage (even if its entry hasn't been written yet)
  //  3. Fallback for legacy runs without any `stages` block: show whichever
  //     ones were explicit_stages, otherwise the full pipeline.
  const hasStagesBlock = Object.keys(block).length > 0
  const filtered = STAGE_DEFS.filter((def) => {
    const entry = block[def.key]
    if (entry && entry.status && entry.status !== 'skipped') return true
    if (def.key === currentStage && !isFinal) return true
    if (!hasStagesBlock) {
      if (Array.isArray(explicitStages) && explicitStages.length > 0) {
        return explicitStages.includes(def.key)
      }
      return true
    }
    return false
  })

  return filtered.map((def) => {
    const entry = block[def.key] || {}
    let status = entry.status
    // Fallback for older runs without `stages`: derive a status from the
    // current_stage field so the timeline still tells a coherent story.
    if (!status) {
      if (def.key === currentStage && !isFinal) {
        status = 'running'
      } else {
        status = 'pending'
      }
    }
    return {
      ...def,
      status,
      reason: entry.reason,
      startedAt: entry.started_at,
      completedAt: entry.completed_at,
      duration: fmtDuration(entry.started_at, entry.completed_at),
      // Generic counters
      total:     Number(entry.total)     || 0,
      processed: Number(entry.processed) || 0,
      succeeded: Number(entry.succeeded) || 0,
      failed:    Number(entry.failed)    || 0,
      costCents: Number(entry.cost_cents) || 0,
      // Stage-specific extras
      apiCalls:        Number(entry.api_calls)        || 0,
      tilesProcessed:  Number(entry.tiles_processed)  || 0,
      tileQueueLen:    Number(entry.tile_queue_len)   || 0,
      saturations:     Number(entry.saturations)      || 0,
      checked:         Number(entry.checked)          || 0,
      homepagesFound:  Number(entry.homepages_found)  || 0,
      noHomepage:      Number(entry.no_homepage)      || 0,
      skippedNoSite:   Number(entry.skipped_no_site)  || 0,
      // LinkedIn-stage counters live both on stages.linkedin (basic) and on
      // the run-level state (richer breakdown). Pull the rich ones too so
      // the timeline can show "company via Serper / Impressum".
      serperCalls:        Number(entry.serper_calls)                              || 0,
      genderViaLlm:       Number(entry.gender_via_llm)                            || 0,
      contactsViaSerper:  Number(runState.contacts_via_serper)     || 0,
      contactsViaImpressum: Number(runState.contacts_via_impressum) || 0,
      companyViaSerper:   Number(runState.company_via_serper)      || 0,
      companyViaImpressum: Number(runState.company_via_impressum)  || 0,
      // Apollo-stage breakdown — counters live on the run-level state and
      // on the stage entry itself (cost, processed, succeeded).
      apolloBulkCalls:    Number(entry.bulk_calls || runState.apollo_bulk_calls)         || 0,
      apolloCredits:      Number(entry.credits_used || runState.apollo_credits_used)     || 0,
      apolloMatchHigh:    Number(runState.apollo_matched_high)   || 0,
      apolloMatchMedium:  Number(runState.apollo_matched_medium) || 0,
      apolloMatchLow:     Number(runState.apollo_matched_low)    || 0,
      apolloNoMatch:      Number(runState.apollo_no_match)       || 0,
      icon: STATUS_ICON[status] || STATUS_ICON.pending
    }
  })
})

function progressPercent(s) {
  if (!s.total || !s.processed) return null
  if (s.status !== 'running') return null
  return Math.min(100, Math.round((s.processed / s.total) * 100))
}

function metricsFor(s) {
  // Returns a list of "label: value" pairs to render under each stage.
  // Empty array → nothing extra to show beyond the duration/cost line.
  if (s.status === 'pending') return []
  if (s.status === 'skipped') return []

  if (s.key === 'places') {
    const out = []
    if (s.processed)       out.push({ label: 'Places',       value: s.processed.toLocaleString('de-DE') })
    if (s.apiCalls)        out.push({ label: 'API-Calls',    value: s.apiCalls.toLocaleString('de-DE') })
    if (s.tilesProcessed)  out.push({ label: 'Tiles fertig', value: s.tilesProcessed.toLocaleString('de-DE') })
    if (s.tileQueueLen)    out.push({ label: 'Queue',        value: s.tileQueueLen.toLocaleString('de-DE') })
    if (s.saturations)     out.push({ label: 'Subdivisions', value: s.saturations.toLocaleString('de-DE') })
    return out
  }
  if (s.key === 'impressum') {
    const out = []
    if (s.total)     out.push({ label: 'Verarbeitet', value: `${s.processed.toLocaleString('de-DE')} / ${s.total.toLocaleString('de-DE')}` })
    if (s.succeeded) out.push({ label: 'OK',          value: s.succeeded.toLocaleString('de-DE'), tone: 'success' })
    if (s.failed)    out.push({ label: 'Fehler',      value: s.failed.toLocaleString('de-DE'),    tone: 'danger' })
    return out
  }
  if (s.key === 'verify') {
    const out = []
    if (s.checked)         out.push({ label: 'Geprüft',                value: s.checked.toLocaleString('de-DE') })
    if (s.homepagesFound)  out.push({ label: 'Verborgene Homepages',   value: s.homepagesFound.toLocaleString('de-DE'), tone: 'success' })
    if (s.noHomepage)      out.push({ label: 'Bestätigt ohne',         value: s.noHomepage.toLocaleString('de-DE') })
    return out
  }
  if (s.key === 'llm') {
    const out = []
    if (s.total)         out.push({ label: 'Verarbeitet',  value: `${s.processed.toLocaleString('de-DE')} / ${s.total.toLocaleString('de-DE')}` })
    if (s.skippedNoSite) out.push({ label: 'Synth. (no-site)', value: s.skippedNoSite.toLocaleString('de-DE') })
    if (s.succeeded)     out.push({ label: 'OK',           value: s.succeeded.toLocaleString('de-DE'), tone: 'success' })
    if (s.failed)        out.push({ label: 'Fehler',       value: s.failed.toLocaleString('de-DE'),    tone: 'danger' })
    return out
  }
  if (s.key === 'linkedin') {
    const out = []
    if (s.total)               out.push({ label: 'Firmen verarbeitet', value: `${s.processed.toLocaleString('de-DE')} / ${s.total.toLocaleString('de-DE')}` })
    if (s.serperCalls)         out.push({ label: 'Serper-Calls',       value: s.serperCalls.toLocaleString('de-DE') })
    if (s.contactsViaSerper)   out.push({ label: 'Personen via Serper', value: s.contactsViaSerper.toLocaleString('de-DE'), tone: 'success' })
    if (s.contactsViaImpressum)out.push({ label: 'Personen via Impressum', value: s.contactsViaImpressum.toLocaleString('de-DE'), tone: 'success' })
    if (s.companyViaSerper)    out.push({ label: 'Firmen via Serper',  value: s.companyViaSerper.toLocaleString('de-DE'), tone: 'success' })
    if (s.companyViaImpressum) out.push({ label: 'Firmen via Impressum', value: s.companyViaImpressum.toLocaleString('de-DE'), tone: 'success' })
    if (s.genderViaLlm)        out.push({ label: 'Gender via LLM',     value: s.genderViaLlm.toLocaleString('de-DE') })
    return out
  }
  if (s.key === 'apollo') {
    const out = []
    if (s.total)              out.push({ label: 'Personen verarbeitet', value: `${s.processed.toLocaleString('de-DE')} / ${s.total.toLocaleString('de-DE')}` })
    if (s.apolloBulkCalls)    out.push({ label: 'Bulk-Calls',           value: s.apolloBulkCalls.toLocaleString('de-DE') })
    if (s.apolloCredits)      out.push({ label: 'Credits',              value: s.apolloCredits.toLocaleString('de-DE'), tone: 'danger' })
    if (s.apolloMatchHigh)    out.push({ label: 'High-Match',           value: s.apolloMatchHigh.toLocaleString('de-DE'), tone: 'success' })
    if (s.apolloMatchMedium)  out.push({ label: 'Medium',               value: s.apolloMatchMedium.toLocaleString('de-DE'), tone: 'success' })
    if (s.apolloMatchLow)     out.push({ label: 'Low',                  value: s.apolloMatchLow.toLocaleString('de-DE') })
    if (s.apolloNoMatch)      out.push({ label: 'No-Match',             value: s.apolloNoMatch.toLocaleString('de-DE') })
    return out
  }
  return []
}

function toneClass(tone) {
  if (tone === 'success') return 'text-green-700 dark:text-green-400'
  if (tone === 'danger') return 'text-red-700 dark:text-red-400'
  return 'text-gray-900 dark:text-gray-100'
}
</script>

<template>
  <ul class="space-y-1.5">
    <li
      v-for="(s, idx) in stages"
      :key="s.key"
      class="grid grid-cols-[1.25rem_1fr] gap-x-2 text-xs"
    >
      <!-- Status icon column with connector line -->
      <div class="relative flex flex-col items-center">
        <span :class="['leading-none', s.icon.cls]">{{ s.icon.glyph }}</span>
        <div
          v-if="idx < stages.length - 1"
          class="mt-0.5 w-px flex-1 bg-gray-200 dark:bg-gray-700"
          aria-hidden="true"
        />
      </div>

      <!-- Stage content -->
      <div class="pb-1.5">
        <div class="flex flex-wrap items-baseline justify-between gap-2">
          <span class="font-medium text-gray-800 dark:text-gray-200">{{ s.label }}</span>
          <span class="flex items-center gap-3 text-[11px] text-gray-500 dark:text-gray-400">
            <span v-if="s.duration">{{ s.duration }}</span>
            <span v-if="s.costCents">{{ fmtCost(s.costCents) }}</span>
            <span
              v-if="s.status === 'skipped' && s.reason"
              class="italic"
              :title="s.reason"
            >übersprungen</span>
          </span>
        </div>

        <!-- Metrics row -->
        <div
          v-if="metricsFor(s).length"
          class="mt-0.5 flex flex-wrap gap-x-3 gap-y-0.5 text-[11px]"
        >
          <span
            v-for="m in metricsFor(s)"
            :key="m.label"
            class="text-gray-500 dark:text-gray-400"
          >
            {{ m.label }}:
            <span :class="['font-medium', toneClass(m.tone)]">{{ m.value }}</span>
          </span>
        </div>

        <!-- Inline progress bar for running stages -->
        <div
          v-if="progressPercent(s) !== null"
          class="mt-1 h-1.5 w-full rounded-full bg-gray-200 dark:bg-gray-700"
        >
          <div
            class="h-1.5 rounded-full bg-go4-primary transition-all"
            :style="{ width: progressPercent(s) + '%' }"
          />
        </div>
      </div>
    </li>
  </ul>
</template>
