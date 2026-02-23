<script setup>
import { ref, onMounted } from 'vue'
import { useDistributorStore } from '@/stores/distributor'
import PageHeader from '@/components/ui/PageHeader.vue'
import KpiCard from '@/components/ads/KpiCard.vue'
import PerformanceChart from '@/components/ads/PerformanceChart.vue'
import WeatherWidget from '@/components/ads/WeatherWidget.vue'

const store = useDistributorStore()
const optimizing = ref(false)

onMounted(() => {
  store.fetchDashboard()
  store.fetchPerformance()
  store.fetchCampaigns()
  store.fetchWeather()
})

async function runOptimizer() {
  optimizing.value = true
  try {
    await store.optimize()
    await store.fetchDashboard()
  } finally {
    optimizing.value = false
  }
}
</script>

<template>
  <div>
    <PageHeader title="Distributor" subtitle="Kampagnen verteilen und optimieren">
      <template #actions>
        <button
          class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white transition hover:bg-go4-primary/90 disabled:opacity-50"
          :disabled="optimizing"
          @click="runOptimizer"
        >
          {{ optimizing ? 'Optimiert...' : 'Jetzt optimieren' }}
        </button>
      </template>
    </PageHeader>

    <div v-if="store.loading" class="mt-8 flex items-center justify-center p-12">
      <span class="text-go4-muted dark:text-gray-400">Laden...</span>
    </div>

    <div
      v-else-if="store.error"
      class="mt-8 rounded-lg bg-red-50 dark:bg-red-900/20 p-4 text-red-700 dark:text-red-400"
    >
      {{ store.error }}
    </div>

    <template v-else>
      <!-- KPI Cards -->
      <div class="mt-6 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          title="Ausgaben heute"
          :value="`${store.totalSpendToday} EUR`"
          :subtitle="`${store.dashboard?.this_week?.spend || '0.00'} EUR diese Woche`"
          :trend="store.dashboard?.trend || 'stable'"
        />
        <KpiCard
          title="Leads heute"
          :value="store.totalLeadsToday"
          :subtitle="`${store.dashboard?.this_week?.leads || 0} diese Woche`"
        />
        <KpiCard
          title="CPL heute"
          :value="`${Number(store.dashboard?.today?.cpl || 0).toFixed(2)} EUR`"
          :subtitle="`Ziel: ${Number(store.dashboard?.this_month?.cpl || 0).toFixed(2)} EUR (Monat)`"
          :trend="store.dashboard?.trend || 'stable'"
        />
        <KpiCard
          title="Impressions"
          :value="(store.dashboard?.today?.impressions || 0).toLocaleString()"
          :subtitle="`${(store.dashboard?.this_month?.impressions || 0).toLocaleString()} diesen Monat`"
        />
      </div>

      <!-- Performance Chart -->
      <div class="mt-8">
        <PerformanceChart :data="store.performance" />
      </div>

      <!-- Campaigns Table + Weather -->
      <div class="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <!-- Campaigns Table -->
        <div class="rounded-lg bg-white dark:bg-gray-800 p-6 shadow-sm lg:col-span-2">
          <h3 class="mb-4 text-sm font-medium text-go4-muted dark:text-gray-400">Kampagnen</h3>
          <div
            v-if="store.campaigns.length === 0"
            class="py-8 text-center text-go4-muted dark:text-gray-400"
          >
            Keine Kampagnen konfiguriert
          </div>
          <div v-else class="overflow-x-auto">
            <table class="min-w-full text-sm text-go4-secondary dark:text-gray-300">
              <thead>
                <tr
                  class="border-b dark:border-gray-700 text-left text-xs font-medium uppercase text-go4-muted dark:text-gray-400"
                >
                  <th class="py-3 pr-4">Kampagne</th>
                  <th class="py-3 pr-4">Status</th>
                  <th class="py-3 pr-4 text-right">Ziel-CPL</th>
                  <th class="py-3 pr-4 text-right">Max-CPL</th>
                  <th class="py-3 pr-4">Boost</th>
                  <th class="py-3">Aktionen</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="campaign in store.campaigns"
                  :key="campaign.id"
                  class="border-b dark:border-gray-700 last:border-0"
                >
                  <td class="py-3 pr-4">
                    <router-link
                      :to="`/distributor/campaigns/${campaign.id}/config`"
                      class="font-medium text-go4-primary hover:underline"
                    >
                      {{ campaign.campaign_name || campaign.campaign_id }}
                    </router-link>
                  </td>
                  <td class="py-3 pr-4">
                    <span
                      :class="[
                        'rounded-full px-2 py-0.5 text-xs font-medium',
                        campaign.status === 'active'
                          ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400'
                          : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300'
                      ]"
                    >
                      {{ campaign.status }}
                    </span>
                  </td>
                  <td class="py-3 pr-4 text-right">
                    {{
                      campaign.target_cpl ? `${Number(campaign.target_cpl).toFixed(2)} EUR` : '-'
                    }}
                  </td>
                  <td class="py-3 pr-4 text-right">
                    {{ campaign.max_cpl ? `${Number(campaign.max_cpl).toFixed(2)} EUR` : '-' }}
                  </td>
                  <td class="py-3 pr-4">
                    <span
                      :class="
                        campaign.weather_boost_enabled
                          ? 'text-yellow-600'
                          : 'text-gray-400 dark:text-gray-500'
                      "
                    >
                      {{ campaign.weather_boost_enabled ? 'Aktiv' : 'Aus' }}
                    </span>
                  </td>
                  <td class="py-3">
                    <button
                      v-if="campaign.status === 'active'"
                      class="text-xs text-red-600 hover:underline"
                      @click="store.pause(campaign.id)"
                    >
                      Pausieren
                    </button>
                    <button
                      v-else
                      class="text-xs text-green-600 hover:underline"
                      @click="store.resume(campaign.id)"
                    >
                      Fortsetzen
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Weather Widget -->
        <WeatherWidget :weather="store.weather" :loading="store.loading" />
      </div>

      <!-- Optimizer Log -->
      <div
        v-if="store.optimizerLog.length > 0"
        class="mt-8 rounded-lg bg-white dark:bg-gray-800 p-6 shadow-sm"
      >
        <h3 class="mb-4 text-sm font-medium text-go4-muted dark:text-gray-400">
          Letzte Optimierung
        </h3>
        <div class="space-y-2">
          <div
            v-for="(entry, idx) in store.optimizerLog"
            :key="idx"
            class="flex items-center gap-4 rounded-lg border dark:border-gray-700 p-3 text-sm"
          >
            <span
              :class="[
                'rounded-full px-2 py-0.5 text-xs font-medium',
                entry.action === 'scaled'
                  ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400'
                  : entry.action === 'reduced'
                    ? 'bg-orange-100 dark:bg-orange-900/30 text-orange-800 dark:text-orange-400'
                    : entry.action === 'stopped'
                      ? 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-400'
                      : entry.action === 'weather_boosted'
                        ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-400'
                        : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300'
              ]"
            >
              {{ entry.action }}
            </span>
            <span class="font-medium text-go4-secondary dark:text-gray-100">{{
              entry.campaign_name || entry.campaign_id
            }}</span>
            <span class="text-go4-muted dark:text-gray-400">{{ entry.reason }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
