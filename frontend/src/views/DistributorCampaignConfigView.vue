<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDistributorStore } from '@/stores/distributor'
import PageHeader from '@/components/ui/PageHeader.vue'

const route = useRoute()
const router = useRouter()
const store = useDistributorStore()

const loading = ref(false)
const error = ref(null)
const saving = ref(false)

const form = ref({
  campaign_id: '',
  campaign_name: '',
  platform: 'meta',
  target_cpl: '',
  max_cpl: '',
  daily_budget_min: '',
  daily_budget_max: '',
  weather_boost_enabled: true,
  weather_boost_factor: '1.5',
  auto_optimize: true
})

const isEdit = ref(false)
const configId = ref(null)

onMounted(async () => {
  const id = route.params.id
  if (id && id !== 'new') {
    isEdit.value = true
    configId.value = Number(id)
    loading.value = true
    error.value = null
    try {
      await store.fetchCampaigns()
      const config = store.campaigns.find((c) => c.id === configId.value)
      if (config) {
        form.value = {
          campaign_id: config.campaign_id,
          campaign_name: config.campaign_name || '',
          platform: config.platform,
          target_cpl: config.target_cpl || '',
          max_cpl: config.max_cpl || '',
          daily_budget_min: config.daily_budget_min || '',
          daily_budget_max: config.daily_budget_max || '',
          weather_boost_enabled: config.weather_boost_enabled,
          weather_boost_factor: config.weather_boost_factor || '1.5',
          auto_optimize: config.auto_optimize
        }
      } else {
        error.value = 'Kampagne nicht gefunden'
      }
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }
})

async function save() {
  saving.value = true
  error.value = null
  try {
    const data = {
      ...form.value,
      target_cpl: form.value.target_cpl ? Number(form.value.target_cpl) : null,
      max_cpl: form.value.max_cpl ? Number(form.value.max_cpl) : null,
      daily_budget_min: form.value.daily_budget_min ? Number(form.value.daily_budget_min) : null,
      daily_budget_max: form.value.daily_budget_max ? Number(form.value.daily_budget_max) : null,
      weather_boost_factor: Number(form.value.weather_boost_factor)
    }
    if (isEdit.value) {
      await store.editCampaignConfig(configId.value, data)
    } else {
      await store.addCampaignConfig(data)
    }
    router.push('/distributor')
  } catch (err) {
    error.value = err.message
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="mx-auto max-w-3xl">
    <PageHeader :title="isEdit ? 'Kampagne bearbeiten' : 'Neue Kampagne konfigurieren'" />

    <div v-if="loading" class="mt-8 flex items-center justify-center p-12">
      <span class="text-go4-muted">Laden...</span>
    </div>

    <div v-else-if="error" class="mt-4 rounded-lg bg-red-50 p-4 text-red-700">
      {{ error }}
    </div>

    <form v-else class="mt-8 space-y-6" @submit.prevent="save">
      <div class="rounded-lg bg-white p-6 shadow-sm">
        <h2 class="mb-4 text-lg font-medium text-go4-secondary">Grunddaten</h2>
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label class="block text-sm font-medium text-go4-muted">Meta Campaign ID</label>
            <input
              v-model="form.campaign_id"
              type="text"
              required
              :disabled="isEdit"
              class="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary disabled:bg-gray-100"
              placeholder="z.B. 23456789012345"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-go4-muted">Kampagnenname</label>
            <input
              v-model="form.campaign_name"
              type="text"
              class="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
              placeholder="z.B. Solar-Leads Wien"
            />
          </div>
        </div>
      </div>

      <div class="rounded-lg bg-white p-6 shadow-sm">
        <h2 class="mb-4 text-lg font-medium text-go4-secondary">Budget & CPL</h2>
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label class="block text-sm font-medium text-go4-muted">Ziel-CPL (EUR)</label>
            <input
              v-model="form.target_cpl"
              type="number"
              step="0.01"
              min="0"
              class="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
              placeholder="z.B. 15.00"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-go4-muted">Max-CPL (EUR)</label>
            <input
              v-model="form.max_cpl"
              type="number"
              step="0.01"
              min="0"
              class="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
              placeholder="z.B. 30.00"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-go4-muted">Min. Tagesbudget (EUR)</label>
            <input
              v-model="form.daily_budget_min"
              type="number"
              step="0.01"
              min="0"
              class="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
              placeholder="z.B. 10.00"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-go4-muted">Max. Tagesbudget (EUR)</label>
            <input
              v-model="form.daily_budget_max"
              type="number"
              step="0.01"
              min="0"
              class="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
              placeholder="z.B. 100.00"
            />
          </div>
        </div>
      </div>

      <div class="rounded-lg bg-white p-6 shadow-sm">
        <h2 class="mb-4 text-lg font-medium text-go4-secondary">Optimierung</h2>
        <div class="space-y-4">
          <label class="flex items-center gap-3">
            <input
              v-model="form.auto_optimize"
              type="checkbox"
              class="h-4 w-4 rounded border-gray-300 text-go4-primary focus:ring-go4-primary"
            />
            <span class="text-sm text-go4-secondary">Automatische Budget-Optimierung</span>
          </label>
          <label class="flex items-center gap-3">
            <input
              v-model="form.weather_boost_enabled"
              type="checkbox"
              class="h-4 w-4 rounded border-gray-300 text-go4-primary focus:ring-go4-primary"
            />
            <span class="text-sm text-go4-secondary">Wetter-Boost aktivieren</span>
          </label>
          <div v-if="form.weather_boost_enabled" class="ml-7">
            <label class="block text-sm font-medium text-go4-muted">Boost-Faktor</label>
            <input
              v-model="form.weather_boost_factor"
              type="number"
              step="0.1"
              min="1"
              max="3"
              class="mt-1 w-32 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
            />
            <span class="ml-2 text-xs text-go4-muted"
              >z.B. 1.5 = 50% mehr Budget bei Sonnenschein</span
            >
          </div>
        </div>
      </div>

      <div class="flex items-center justify-end gap-4">
        <button
          type="button"
          class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-go4-secondary hover:bg-gray-50"
          @click="router.push('/distributor')"
        >
          Abbrechen
        </button>
        <button
          type="submit"
          :disabled="saving"
          class="rounded-lg bg-go4-primary px-6 py-2 text-sm font-medium text-white transition hover:bg-go4-primary/90 disabled:opacity-50"
        >
          {{ saving ? 'Speichert...' : 'Speichern' }}
        </button>
      </div>
    </form>
  </div>
</template>
