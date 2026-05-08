<script setup>
/**
 * Clustered map view of all geocoded LeadgenPlaces of a campaign.
 *
 * Uses Leaflet + leaflet.markercluster (both MIT, OSM tiles free).
 * Bubble-clusters automatically resolve into smaller bubbles when the user
 * zooms in.
 */
import { ref, onMounted, onBeforeUnmount, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import 'leaflet.markercluster'
import 'leaflet.markercluster/dist/MarkerCluster.css'
import 'leaflet.markercluster/dist/MarkerCluster.Default.css'

import api from '@/api'

const props = defineProps({
  campaignId: { type: [Number, String], required: true },
})

const router = useRouter()
const mapEl = ref(null)
const points = ref([])
const loading = ref(false)
const error = ref(null)
const statusFilter = ref('')
const minScore = ref(null)  // null = no filter; 0..10

// Aligned with the Prospects-Tab dropdown so the user sees the same options.
const statusOptions = [
  { value: '', label: 'Alle Status' },
  { value: 'discovered', label: 'discovered' },
  { value: 'impressum_done', label: 'impressum_done' },
  { value: 'impressum_failed', label: 'impressum_failed' },
  { value: 'llm_done', label: 'llm_done' },
  { value: 'llm_failed', label: 'llm_failed' },
  { value: 'enrolled', label: 'enrolled' },
  { value: 'rejected', label: 'rejected' },
]

const filteredPoints = computed(() => {
  let list = points.value
  if (statusFilter.value) {
    list = list.filter((p) => p.status === statusFilter.value)
  }
  if (minScore.value != null && minScore.value !== '') {
    const min = Number(minScore.value)
    list = list.filter((p) => p.match_score != null && p.match_score >= min)
  }
  return list
})

let mapInstance = null
let clusterGroup = null

// Status -> marker dot color
const statusColors = {
  discovered: '#94a3b8',          // slate
  impressum_scraped: '#0ea5e9',   // sky
  llm_qualified: '#10b981',       // emerald
  llm_rejected: '#ef4444',        // red
  rejected: '#ef4444',
  approved: '#22c55e',            // green
  handed_off: '#a855f7',          // purple
  unbekannt: '#9ca3af',
}

function dotIcon(color) {
  const html = `<span style="
    display:block; width:14px; height:14px; border-radius:50%;
    background:${color}; border:2px solid white; box-shadow:0 0 0 1px rgba(0,0,0,0.2);
  "></span>`
  return L.divIcon({
    html,
    className: 'leadgen-dot-icon',
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  })
}

async function fetchPoints() {
  loading.value = true
  error.value = null
  try {
    const { data } = await api.get(
      `/v1/leadgen/campaigns/${props.campaignId}/places/map`,
    )
    points.value = data
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    loading.value = false
  }
}

function escapeHtml(s) {
  return String(s || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function renderMarkers() {
  if (!mapInstance) return
  if (clusterGroup) {
    mapInstance.removeLayer(clusterGroup)
    clusterGroup = null
  }
  clusterGroup = L.markerClusterGroup({
    showCoverageOnHover: false,
    chunkedLoading: true,
    spiderfyOnMaxZoom: true,
    maxClusterRadius: 60,
  })
  for (const p of filteredPoints.value) {
    const color = statusColors[p.status] || statusColors.unbekannt
    const marker = L.marker([p.lat, p.lng], { icon: dotIcon(color) })
    const label = escapeHtml(p.name)
    const city = p.city ? escapeHtml(p.city) : ''
    const status = escapeHtml(p.status || '')
    const score = p.match_score
    const scoreBadge =
      score == null
        ? ''
        : `<span style="display:inline-block;margin-left:6px;padding:1px 6px;border-radius:9999px;font-size:10px;font-weight:600;
              background:${score >= 7 ? '#dcfce7' : score >= 4 ? '#fef9c3' : '#fee2e2'};
              color:${score >= 7 ? '#166534' : score >= 4 ? '#854d0e' : '#991b1b'}">
              ${score}/10
           </span>`
    marker.bindPopup(
      `<div style="min-width:200px">
         <div style="font-weight:600;margin-bottom:2px">${label}</div>
         ${city ? `<div style="font-size:12px;color:#6b7280">${city}</div>` : ''}
         <div style="font-size:11px;margin-top:4px">
           <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${color};margin-right:4px"></span>${status}${scoreBadge}
         </div>
         <a href="#/leadgen/campaigns/${props.campaignId}/places/${p.id}"
            style="display:block;margin-top:6px;font-size:12px;color:#0ea5e9">
           Details öffnen →
         </a>
       </div>`,
    )
    marker.on('click', () => {
      // Single click also navigates after a short delay (popup also opens)
    })
    clusterGroup.addLayer(marker)
  }
  mapInstance.addLayer(clusterGroup)
  // Fit bounds to all visible markers
  if (filteredPoints.value.length > 0) {
    try {
      const bounds = clusterGroup.getBounds()
      if (bounds.isValid()) {
        mapInstance.fitBounds(bounds, { padding: [40, 40] })
      }
    } catch {}
  }
}

function initMap() {
  if (!mapEl.value || mapInstance) return
  mapInstance = L.map(mapEl.value, {
    center: [51.0, 10.4],   // Germany center
    zoom: 6,
    scrollWheelZoom: true,
  })
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap',
    maxZoom: 19,
  }).addTo(mapInstance)
}

onMounted(async () => {
  initMap()
  await fetchPoints()
  renderMarkers()
})

onBeforeUnmount(() => {
  if (mapInstance) {
    mapInstance.remove()
    mapInstance = null
    clusterGroup = null
  }
})

watch(filteredPoints, () => renderMarkers())
watch(() => props.campaignId, async () => {
  await fetchPoints()
  renderMarkers()
})

// Suppress eslint unused warnings
void router
</script>

<template>
  <div class="space-y-3">
    <!-- Filter bar — aligned with Prospects tab styling -->
    <div class="flex flex-wrap items-center gap-3 rounded-lg bg-white p-3 shadow-sm dark:bg-gray-800">
      <select
        v-model="statusFilter"
        class="w-56 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800"
      >
        <option
          v-for="o in statusOptions"
          :key="o.value"
          :value="o.value"
        >
          {{ o.label }}
        </option>
      </select>

      <label class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
        Match-Score ≥
        <input
          v-model.number="minScore"
          type="number"
          min="0"
          max="10"
          step="1"
          placeholder="0–10"
          class="w-20 rounded-lg border border-gray-300 bg-white px-2 py-2 text-sm dark:border-gray-600 dark:bg-gray-800"
        />
        <button
          v-if="minScore != null && minScore !== ''"
          type="button"
          class="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
          title="Score-Filter zurücksetzen"
          @click="minScore = null"
        >
          ✕
        </button>
      </label>

      <div class="ml-auto text-xs text-gray-500">
        {{ filteredPoints.length.toLocaleString('de-DE') }} Treffer
        <span v-if="filteredPoints.length !== points.length" class="text-gray-400">
          / {{ points.length.toLocaleString('de-DE') }}
        </span>
      </div>
    </div>

    <div
      v-if="error"
      class="rounded-md bg-red-50 p-2 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-300"
    >
      {{ error }}
    </div>

    <!-- Map container -->
    <div class="relative rounded-lg bg-white shadow dark:bg-gray-800">
      <div
        v-if="loading"
        class="absolute inset-0 z-10 flex items-center justify-center bg-white/70 dark:bg-gray-800/70"
      >
        <span class="text-sm text-gray-600 dark:text-gray-300">Lade Punkte…</span>
      </div>
      <div
        ref="mapEl"
        class="h-[calc(100vh-220px)] min-h-[600px] w-full rounded-lg"
      />
    </div>
  </div>
</template>
