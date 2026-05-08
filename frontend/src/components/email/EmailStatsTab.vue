<script setup>
/**
 * Email-Marketing Statistik-Dashboard.
 *
 * Zeigt aggregierte SendGrid-Versandmetriken:
 *  - 6 Hero-KPIs (Gesendet, Zustellrate, Open-Rate, Click-Rate, Bounce-Rate, Spam-Rate)
 *  - Compliance-Health-Ampel (grün/gelb/rot)
 *  - Trend-Chart (delivered/opens/clicks pro Tag)
 *  - Bounce + Spam Bar-Chart pro Tag
 *  - Ausklappbare Tagesdetails-Tabelle
 *  - Time-Range Woche/Monat/Jahr
 *  - Auto-Refresh alle 30s solange Tab aktiv
 */
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { getProviders, getProviderStats } from '@/api/emailmarketing'

const providers = ref([])
const selectedProviderId = ref(null)
const stats = ref([])
const loading = ref(false)
const error = ref(null)
const lastFetched = ref(null)
const detailsOpen = ref(false)

// Time-Range: 'week' | 'month' | 'year'
const range = ref('week')
const ranges = [
  { key: 'week', label: 'Woche', days: 7 },
  { key: 'month', label: 'Monat', days: 30 },
  { key: 'year', label: 'Jahr', days: 365 }
]

let pollHandle = null

function isoDate(d) {
  return d.toISOString().slice(0, 10)
}

function rangeDates() {
  const r = ranges.find((x) => x.key === range.value)
  const end = new Date()
  const start = new Date()
  start.setDate(end.getDate() - (r.days - 1))
  return { start: isoDate(start), end: isoDate(end) }
}

async function loadProviders() {
  try {
    const { data } = await getProviders()
    providers.value = (data || []).filter(
      (p) => p.provider_type === 'sendgrid' && p.status === 'active'
    )
    if (!selectedProviderId.value && providers.value.length) {
      selectedProviderId.value = providers.value[0].id
    }
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  }
}

async function loadStats() {
  if (!selectedProviderId.value) return
  loading.value = true
  error.value = null
  try {
    const { start, end } = rangeDates()
    const { data } = await getProviderStats(selectedProviderId.value, {
      start_date: start,
      end_date: end,
      aggregated_by: 'day'
    })
    stats.value = data || []
    lastFetched.value = new Date()
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    loading.value = false
  }
}

function startPolling() {
  stopPolling()
  pollHandle = setInterval(loadStats, 30000)
}
function stopPolling() {
  if (pollHandle) {
    clearInterval(pollHandle)
    pollHandle = null
  }
}

onMounted(async () => {
  await loadProviders()
  await loadStats()
  startPolling()
})
onBeforeUnmount(stopPolling)

watch([range, selectedProviderId], loadStats)

// ---------- Aggregations ----------
const totals = computed(() => {
  return stats.value.reduce(
    (acc, row) => {
      for (const k of Object.keys(acc)) acc[k] += row[k] || 0
      return acc
    },
    {
      requests: 0,
      delivered: 0,
      opens: 0,
      unique_opens: 0,
      clicks: 0,
      unique_clicks: 0,
      bounces: 0,
      blocks: 0,
      spam_reports: 0,
      unsubscribes: 0,
      invalid_emails: 0
    }
  )
})

function pct(num, denom) {
  if (!denom) return 0
  return (num / denom) * 100
}
function fmtPct(v) {
  return `${v.toFixed(2)} %`
}
function fmtNum(v) {
  return (v || 0).toLocaleString('de-DE')
}

const deliveryRate = computed(() => pct(totals.value.delivered, totals.value.requests))
const openRate = computed(() => pct(totals.value.unique_opens, totals.value.delivered))
const clickRate = computed(() => pct(totals.value.unique_clicks, totals.value.delivered))
const bounceRate = computed(() => pct(totals.value.bounces, totals.value.requests))
const spamRate = computed(() => pct(totals.value.spam_reports, totals.value.requests))

// ---------- Compliance-Ampel ----------
const compliance = computed(() => {
  const b = bounceRate.value
  const s = spamRate.value
  if (b > 5 || s > 0.1) {
    return {
      level: 'kritisch',
      color: 'red',
      icon: '🔴',
      title: 'Kritisch — Account-Risk',
      detail:
        'Bounce-Quote oder Spam-Beschwerderate über kritischer Schwelle. Senden pausieren, Liste prüfen, Suppression durchgehen.'
    }
  }
  if (b > 2 || s > 0.05) {
    return {
      level: 'warnung',
      color: 'amber',
      icon: '🟡',
      title: 'Warnung',
      detail:
        'Bounce- oder Spam-Quote angehoben. Listen-Hygiene prüfen, ggf. Volume reduzieren.'
    }
  }
  return {
    level: 'gesund',
    color: 'emerald',
    icon: '🟢',
    title: 'Gesund',
    detail: 'Alle Metriken im normalen Bereich. Volume kann ggf. erhöht werden.'
  }
})

// ---------- ApexCharts ----------
const trendOptions = computed(() => ({
  chart: {
    type: 'line',
    height: 320,
    toolbar: { show: false },
    fontFamily: 'inherit',
    zoom: { enabled: false }
  },
  stroke: { curve: 'smooth', width: 2 },
  colors: ['#10b981', '#3b82f6', '#8b5cf6'],
  xaxis: {
    categories: stats.value.map((r) => r.date),
    labels: { style: { fontSize: '11px' } }
  },
  yaxis: { labels: { style: { fontSize: '11px' } } },
  grid: { borderColor: '#e5e7eb', strokeDashArray: 4 },
  legend: { position: 'top', horizontalAlign: 'left' },
  tooltip: { theme: 'light' }
}))

const trendSeries = computed(() => [
  { name: 'Zugestellt', data: stats.value.map((r) => r.delivered || 0) },
  { name: 'Opens (unique)', data: stats.value.map((r) => r.unique_opens || 0) },
  { name: 'Clicks (unique)', data: stats.value.map((r) => r.unique_clicks || 0) }
])

const bounceOptions = computed(() => ({
  chart: { type: 'bar', height: 240, toolbar: { show: false }, fontFamily: 'inherit', stacked: true },
  plotOptions: { bar: { columnWidth: '55%', borderRadius: 2 } },
  colors: ['#f59e0b', '#ef4444'],
  xaxis: { categories: stats.value.map((r) => r.date), labels: { style: { fontSize: '11px' } } },
  yaxis: { labels: { style: { fontSize: '11px' } } },
  grid: { borderColor: '#e5e7eb', strokeDashArray: 4 },
  legend: { position: 'top', horizontalAlign: 'left' }
}))

const bounceSeries = computed(() => [
  { name: 'Bounces', data: stats.value.map((r) => r.bounces || 0) },
  { name: 'Spam Reports', data: stats.value.map((r) => r.spam_reports || 0) }
])
</script>

<template>
  <div class="space-y-4">
    <!-- Header: Provider + Time-Range + Last-Fetched -->
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div class="flex items-center gap-3">
        <select
          v-if="providers.length > 1"
          v-model="selectedProviderId"
          class="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
        >
          <option v-for="p in providers" :key="p.id" :value="p.id">
            {{ p.sender_email }} ({{ p.provider_type }})
          </option>
        </select>
        <span v-else-if="providers.length === 1" class="text-sm text-gray-600 dark:text-gray-400">
          Provider: <strong>{{ providers[0].sender_email }}</strong>
        </span>
        <span v-else class="text-sm text-amber-700 dark:text-amber-300">
          Kein aktiver SendGrid-Provider gefunden.
        </span>
      </div>
      <div class="flex items-center gap-2">
        <div class="inline-flex rounded-md border border-gray-300 dark:border-gray-600">
          <button
            v-for="r in ranges"
            :key="r.key"
            type="button"
            class="px-3 py-1.5 text-sm font-medium transition first:rounded-l-md last:rounded-r-md"
            :class="
              range === r.key
                ? 'bg-go4-primary text-white'
                : 'bg-white text-gray-700 hover:bg-gray-50 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700'
            "
            @click="range = r.key"
          >
            {{ r.label }}
          </button>
        </div>
        <button
          type="button"
          class="rounded-md border border-gray-300 px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50 disabled:opacity-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700"
          :disabled="loading"
          @click="loadStats"
        >
          {{ loading ? 'Lädt…' : '↻ Aktualisieren' }}
        </button>
        <span v-if="lastFetched" class="text-[11px] text-gray-500 dark:text-gray-400">
          {{ lastFetched.toLocaleTimeString('de-DE') }}
        </span>
      </div>
    </div>

    <div v-if="error" class="rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-300">
      {{ error }}
    </div>

    <!-- Hero KPIs -->
    <div class="grid grid-cols-2 gap-3 lg:grid-cols-6">
      <div class="rounded-lg bg-white p-4 shadow-sm dark:bg-gray-800">
        <div class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">Gesendet</div>
        <div class="mt-1 text-2xl font-semibold text-gray-900 dark:text-gray-100">
          {{ fmtNum(totals.requests) }}
        </div>
        <div class="text-[11px] text-gray-500 dark:text-gray-400">{{ stats.length }} Tage</div>
      </div>
      <div class="rounded-lg bg-white p-4 shadow-sm dark:bg-gray-800">
        <div class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">Zustellrate</div>
        <div class="mt-1 text-2xl font-semibold text-emerald-600 dark:text-emerald-400">
          {{ fmtPct(deliveryRate) }}
        </div>
        <div class="text-[11px] text-gray-500 dark:text-gray-400">{{ fmtNum(totals.delivered) }} delivered</div>
      </div>
      <div class="rounded-lg bg-white p-4 shadow-sm dark:bg-gray-800">
        <div class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">Open-Rate</div>
        <div class="mt-1 text-2xl font-semibold text-blue-600 dark:text-blue-400">
          {{ fmtPct(openRate) }}
        </div>
        <div class="text-[11px] text-gray-500 dark:text-gray-400">{{ fmtNum(totals.unique_opens) }} unique</div>
      </div>
      <div class="rounded-lg bg-white p-4 shadow-sm dark:bg-gray-800">
        <div class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">Click-Rate</div>
        <div class="mt-1 text-2xl font-semibold text-purple-600 dark:text-purple-400">
          {{ fmtPct(clickRate) }}
        </div>
        <div class="text-[11px] text-gray-500 dark:text-gray-400">{{ fmtNum(totals.unique_clicks) }} unique</div>
      </div>
      <div class="rounded-lg bg-white p-4 shadow-sm dark:bg-gray-800">
        <div class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">Bounce-Rate</div>
        <div
          class="mt-1 text-2xl font-semibold"
          :class="bounceRate > 5 ? 'text-red-600 dark:text-red-400' : bounceRate > 2 ? 'text-amber-600 dark:text-amber-400' : 'text-gray-700 dark:text-gray-200'"
        >
          {{ fmtPct(bounceRate) }}
        </div>
        <div class="text-[11px] text-gray-500 dark:text-gray-400">{{ fmtNum(totals.bounces) }} Bounces</div>
      </div>
      <div class="rounded-lg bg-white p-4 shadow-sm dark:bg-gray-800">
        <div class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">Spam-Rate</div>
        <div
          class="mt-1 text-2xl font-semibold"
          :class="spamRate > 0.1 ? 'text-red-600 dark:text-red-400' : spamRate > 0.05 ? 'text-amber-600 dark:text-amber-400' : 'text-gray-700 dark:text-gray-200'"
        >
          {{ fmtPct(spamRate) }}
        </div>
        <div class="text-[11px] text-gray-500 dark:text-gray-400">{{ fmtNum(totals.spam_reports) }} Reports</div>
      </div>
    </div>

    <!-- Trend + Compliance -->
    <div class="grid grid-cols-1 gap-3 lg:grid-cols-3">
      <div class="rounded-lg bg-white p-4 shadow-sm lg:col-span-2 dark:bg-gray-800">
        <h3 class="mb-2 text-sm font-semibold text-gray-900 dark:text-gray-100">
          Trend (Zugestellt, Opens, Clicks)
        </h3>
        <apexchart
          v-if="stats.length"
          type="line"
          :options="trendOptions"
          :series="trendSeries"
          height="320"
        />
        <p v-else class="py-12 text-center text-sm text-gray-500 dark:text-gray-400">
          Keine Daten im Zeitraum
        </p>
      </div>
      <div
        class="rounded-lg p-4 shadow-sm"
        :class="
          compliance.color === 'red'
            ? 'bg-red-50 dark:bg-red-900/20'
            : compliance.color === 'amber'
              ? 'bg-amber-50 dark:bg-amber-900/20'
              : 'bg-emerald-50 dark:bg-emerald-900/20'
        "
      >
        <div class="flex items-center gap-2">
          <span class="text-2xl">{{ compliance.icon }}</span>
          <h3
            class="text-sm font-semibold"
            :class="
              compliance.color === 'red'
                ? 'text-red-900 dark:text-red-200'
                : compliance.color === 'amber'
                  ? 'text-amber-900 dark:text-amber-200'
                  : 'text-emerald-900 dark:text-emerald-200'
            "
          >
            {{ compliance.title }}
          </h3>
        </div>
        <dl class="mt-3 space-y-1.5 text-sm">
          <div class="flex justify-between">
            <dt class="text-gray-700 dark:text-gray-300">Bounce-Rate</dt>
            <dd class="font-medium text-gray-900 dark:text-gray-100">{{ fmtPct(bounceRate) }}</dd>
          </div>
          <div class="flex justify-between">
            <dt class="text-gray-700 dark:text-gray-300">Spam-Rate</dt>
            <dd class="font-medium text-gray-900 dark:text-gray-100">{{ fmtPct(spamRate) }}</dd>
          </div>
          <div class="flex justify-between">
            <dt class="text-gray-700 dark:text-gray-300">Unsubscribes</dt>
            <dd class="font-medium text-gray-900 dark:text-gray-100">{{ fmtNum(totals.unsubscribes) }}</dd>
          </div>
          <div class="flex justify-between">
            <dt class="text-gray-700 dark:text-gray-300">Invalid Emails</dt>
            <dd class="font-medium text-gray-900 dark:text-gray-100">{{ fmtNum(totals.invalid_emails) }}</dd>
          </div>
        </dl>
        <p class="mt-3 text-xs text-gray-700 dark:text-gray-300">
          {{ compliance.detail }}
        </p>
        <div class="mt-3 border-t border-current/10 pt-2 text-[11px] text-gray-600 dark:text-gray-400">
          Schwellen: Bounce &lt;2 % gesund, &gt;5 % kritisch · Spam &lt;0,05 % gesund, &gt;0,1 % kritisch
        </div>
      </div>
    </div>

    <!-- Bounce + Spam Bar -->
    <div class="rounded-lg bg-white p-4 shadow-sm dark:bg-gray-800">
      <h3 class="mb-2 text-sm font-semibold text-gray-900 dark:text-gray-100">
        Bounces &amp; Spam-Reports pro Tag
      </h3>
      <apexchart
        v-if="stats.length"
        type="bar"
        :options="bounceOptions"
        :series="bounceSeries"
        height="240"
      />
      <p v-else class="py-12 text-center text-sm text-gray-500 dark:text-gray-400">
        Keine Daten im Zeitraum
      </p>
    </div>

    <!-- Tagesdetails-Tabelle -->
    <div class="rounded-lg bg-white shadow-sm dark:bg-gray-800">
      <button
        type="button"
        class="flex w-full items-center justify-between px-4 py-3 text-left"
        @click="detailsOpen = !detailsOpen"
      >
        <span class="text-sm font-semibold text-gray-900 dark:text-gray-100">
          Tagesdetails ({{ stats.length }})
        </span>
        <span class="text-xs text-gray-500 dark:text-gray-400">
          {{ detailsOpen ? '▴ Einklappen' : '▾ Ausklappen' }}
        </span>
      </button>
      <div v-if="detailsOpen" class="overflow-x-auto border-t border-gray-200 dark:border-gray-700">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 text-left text-xs uppercase tracking-wide text-gray-500 dark:bg-gray-900/40 dark:text-gray-400">
            <tr>
              <th class="px-4 py-2">Datum</th>
              <th class="px-4 py-2 text-right">Gesendet</th>
              <th class="px-4 py-2 text-right">Zugestellt</th>
              <th class="px-4 py-2 text-right">Opens (unique)</th>
              <th class="px-4 py-2 text-right">Clicks (unique)</th>
              <th class="px-4 py-2 text-right">Bounces</th>
              <th class="px-4 py-2 text-right">Spam</th>
              <th class="px-4 py-2 text-right">Unsubscribes</th>
              <th class="px-4 py-2 text-right">Blocks</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100 dark:divide-gray-700">
            <tr v-for="row in stats" :key="row.date" class="hover:bg-gray-50 dark:hover:bg-gray-700/30">
              <td class="px-4 py-2 font-mono text-xs text-gray-700 dark:text-gray-300">{{ row.date }}</td>
              <td class="px-4 py-2 text-right">{{ fmtNum(row.requests) }}</td>
              <td class="px-4 py-2 text-right text-emerald-700 dark:text-emerald-400">{{ fmtNum(row.delivered) }}</td>
              <td class="px-4 py-2 text-right text-blue-700 dark:text-blue-400">{{ fmtNum(row.unique_opens) }}</td>
              <td class="px-4 py-2 text-right text-purple-700 dark:text-purple-400">{{ fmtNum(row.unique_clicks) }}</td>
              <td class="px-4 py-2 text-right" :class="row.bounces > 0 ? 'text-amber-700 dark:text-amber-400' : 'text-gray-400'">
                {{ fmtNum(row.bounces) }}
              </td>
              <td class="px-4 py-2 text-right" :class="row.spam_reports > 0 ? 'text-red-700 dark:text-red-400' : 'text-gray-400'">
                {{ fmtNum(row.spam_reports) }}
              </td>
              <td class="px-4 py-2 text-right text-gray-700 dark:text-gray-300">{{ fmtNum(row.unsubscribes) }}</td>
              <td class="px-4 py-2 text-right text-gray-500">{{ fmtNum(row.blocks) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
