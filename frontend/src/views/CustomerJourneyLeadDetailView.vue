<script setup>
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCustomerJourneyStore } from '@/stores/customerJourney'
import PageHeader from '@/components/ui/PageHeader.vue'

const route = useRoute()
const router = useRouter()
const store = useCustomerJourneyStore()

const contactId = computed(() => parseInt(route.params.id))

// Find lead from store (loaded in list)
const lead = computed(() => store.leads.find((l) => l.id === contactId.value))

onMounted(async () => {
  if (!lead.value) {
    await store.fetchLeads()
  }
  await store.fetchTimeline(contactId.value)
})

function toLocal(dateStr) {
  if (!dateStr) return null
  return new Date(dateStr.endsWith('Z') ? dateStr : dateStr + 'Z')
}

function formatDate(dateStr) {
  const d = toLocal(dateStr)
  if (!d) return '-'
  return d.toLocaleDateString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatDay(dateStr) {
  const d = toLocal(dateStr)
  if (!d) return '-'
  return d.toLocaleDateString('de-DE', {
    weekday: 'long',
    day: '2-digit',
    month: 'long',
    year: 'numeric',
  })
}

function formatTime(dateStr) {
  const d = toLocal(dateStr)
  if (!d) return '-'
  return d.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })
}

function eventLabel(event) {
  const map = {
    page_visit: 'Seitenaufruf',
    ref_link_click: 'Ref-Link Klick',
    return_visit: 'Wiederkehr',
    konfigurator_start: 'Konfigurator gestartet',
    konfigurator_step: 'Konfigurator Schritt',
    konfigurator_complete: 'Anfrage abgeschickt',
    konfigurator_mode_sunfi: 'Konfigurator: Sunfi-Modus',
    konfigurator_mode_manual: 'Konfigurator: Manuell',
    config_link_visit: 'Config-Link besucht',
    quote_pdf_download: 'Angebot PDF',
    ems_simulation: 'EMS Simulation',
    ems_simulation_complete: 'EMS Simulation abgeschlossen',
    ems_step_pv: 'EMS: PV-Anlage',
    ems_step_battery: 'EMS: Batterie',
    ems_step_running: 'EMS: Simulation läuft',
    ems_tab_simulation: 'EMS: Tab Simulation',
    ems_tab_ergebnisse: 'EMS: Tab Ergebnisse',
    ems_tab_parameter: 'EMS: Tab Parameter',
    ems_tab_zeitreihen: 'EMS: Tab Zeitreihen',
    ems_tab_empfehlungen: 'EMS: Tab Empfehlungen',
    ems_save_config: 'EMS: Config gespeichert',
    ems_lead_verified: 'EMS: Lead verifiziert',
    ems_pdf_download: 'EMS PDF',
    contact_form: 'Kontaktformular',
    spot_simulation: 'Spotpreis-Simulator',
    spot_simulation_start: 'Spot: Simulation gestartet',
    spot_simulation_complete: 'Spot: Simulation fertig',
    chat_started: 'Chat gestartet',
    quote_viewed: 'Angebot eingesehen',
    identify: 'Identifiziert',
    interest_detected: 'Interesse erkannt',
  }
  return map[event] || event
}

function categoryColor(category) {
  const map = {
    awareness: 'bg-blue-500',
    engagement: 'bg-yellow-500',
    conversion: 'bg-green-500',
    retention: 'bg-purple-500',
  }
  return map[category] || 'bg-gray-400'
}

function categoryBadge(category) {
  const map = {
    awareness: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    engagement: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
    conversion: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    retention: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  }
  return map[category] || 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
}

// Group timeline by day
const groupedTimeline = computed(() => {
  const groups = {}
  for (const event of store.timeline) {
    const d = toLocal(event.created_at)
    if (!d) continue
    const day = d.toISOString().split('T')[0]
    if (!groups[day]) groups[day] = []
    groups[day].push(event)
  }
  return Object.entries(groups).sort((a, b) => b[0].localeCompare(a[0]))
})
</script>

<template>
  <div class="space-y-6">
    <!-- Loading -->
    <div
      v-if="store.loading && !lead"
      class="flex items-center justify-center p-12"
    >
      <span class="text-go4-muted dark:text-gray-400">Laden...</span>
    </div>

    <template v-else>
      <!-- Header -->
      <div class="flex items-start justify-between">
        <div>
          <button
            class="mb-2 text-sm text-gray-500 hover:text-go4-primary"
            @click="router.push('/customer-journey/leads')"
          >
            &larr; Zurück zur Liste
          </button>
          <h1 class="text-2xl font-bold text-gray-900 dark:text-white">
            {{ lead?.name || 'Lead' }}
          </h1>
          <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
            {{ lead?.email }}
          </p>
        </div>
        <div class="flex items-center gap-3">
          <span
            v-if="lead?.journey_status"
            class="inline-flex rounded-full px-3 py-1 text-sm font-medium"
            :class="{
              'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400': lead.journey_status === 'new',
              'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400': lead.journey_status === 'active',
              'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400': lead.journey_status === 'converted',
              'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400': lead.journey_status === 'lost',
            }"
          >
            {{ lead.journey_status }}
          </span>
        </div>
      </div>

      <!-- Info Cards -->
      <div
        v-if="lead"
        class="grid grid-cols-2 md:grid-cols-4 gap-4"
      >
        <div class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
          <div class="text-sm text-gray-500 dark:text-gray-400">
            Quelle
          </div>
          <div class="mt-1 font-medium text-gray-900 dark:text-white">
            {{ lead.source || '-' }}
          </div>
        </div>
        <div class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
          <div class="text-sm text-gray-500 dark:text-gray-400">
            Telefon
          </div>
          <div class="mt-1 font-medium text-gray-900 dark:text-white">
            {{ lead.phone || '-' }}
          </div>
        </div>
        <div class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
          <div class="text-sm text-gray-500 dark:text-gray-400">
            Events
          </div>
          <div class="mt-1 font-medium text-gray-900 dark:text-white">
            {{ lead.event_count }}
          </div>
        </div>
        <div class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
          <div class="text-sm text-gray-500 dark:text-gray-400">
            Tracking-Hash
          </div>
          <div class="mt-1 font-mono text-sm text-go4-primary">
            {{ lead.tracking_hash }}
          </div>
        </div>
      </div>

      <!-- Timeline -->
      <div class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
        <div class="border-b border-gray-200 dark:border-gray-700 px-4 py-3">
          <h3 class="text-sm font-medium text-gray-900 dark:text-white">
            Journey Timeline
          </h3>
        </div>

        <div
          v-if="store.timeline.length === 0 && !store.loading"
          class="p-8 text-center text-gray-500 dark:text-gray-400"
        >
          Noch keine Events für diesen Lead
        </div>

        <div
          v-else
          class="p-4 space-y-6"
        >
          <div
            v-for="[day, events] in groupedTimeline"
            :key="day"
          >
            <!-- Day header -->
            <div class="flex items-center gap-3 mb-3">
              <div class="h-px flex-1 bg-gray-200 dark:bg-gray-700" />
              <span class="text-xs font-medium text-gray-500 dark:text-gray-400">{{ formatDay(day) }}</span>
              <div class="h-px flex-1 bg-gray-200 dark:bg-gray-700" />
            </div>

            <!-- Events -->
            <div class="relative ml-4 border-l-2 border-gray-200 dark:border-gray-700 pl-6 space-y-4">
              <div
                v-for="event in events"
                :key="event.id"
                class="relative"
              >
                <!-- Dot -->
                <div
                  class="absolute -left-[31px] top-1 h-3 w-3 rounded-full border-2 border-white dark:border-gray-800"
                  :class="categoryColor(event.category)"
                />

                <div class="flex items-start gap-3">
                  <span class="text-xs text-gray-400 font-mono w-12 shrink-0">{{ formatTime(event.created_at) }}</span>
                  <div class="flex-1">
                    <div class="flex items-center gap-2">
                      <span class="text-sm font-medium text-gray-900 dark:text-white">{{ eventLabel(event.event) }}</span>
                      <span
                        v-if="event.metadata_ && event.metadata_.config_hash"
                        class="text-xs font-mono text-go4-primary"
                      >{{ event.metadata_.config_hash }}</span>
                      <span
                        class="inline-flex rounded-full px-2 py-0.5 text-xs"
                        :class="categoryBadge(event.category)"
                      >
                        {{ event.category }}
                      </span>
                    </div>
                    <div
                      v-if="event.page_path"
                      class="mt-0.5 text-xs text-gray-400"
                    >
                      {{ event.page_path }}
                    </div>
                    <div
                      v-if="event.utm_source"
                      class="mt-0.5 text-xs text-gray-400"
                    >
                      utm: {{ [event.utm_source, event.utm_medium, event.utm_campaign].filter(Boolean).join(' / ') }}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
