<script setup>
/**
 * MetaSetupTab - Meta Conversions API Setup and Monitoring
 *
 * Provides UI for:
 * - Setting up Meta integration (Pixel ID, Access Token)
 * - Testing the connection
 * - Viewing event logs and statistics
 * - Setup guide with step-by-step instructions
 */

import { ref, computed, onMounted } from 'vue'
import {
  getMetaStatus,
  getMetaIntegration,
  createMetaIntegration,
  updateMetaIntegration,
  deleteMetaIntegration,
  sendTestEvent,
  getConversionEvents,
  getMetaStats,
  getSetupGuide
} from '@/api/meta'

// ============== State ==============

const loading = ref(false)
const error = ref(null)
const success = ref(null)

// Integration state
const status = ref(null)
const integration = ref(null)
const setupGuide = ref(null)

// Form state
const showForm = ref(false)
const form = ref({
  pixel_id: '',
  access_token: '',
  ad_account_id: '',
  test_mode: false
})
const showToken = ref(false)

// Events state
const events = ref([])
const eventsLoading = ref(false)
const eventsPage = ref(1)
const eventsTotal = ref(0)

// Stats state
const stats = ref(null)
const statsDays = ref(7)

// Test event state
const testLoading = ref(false)
const testResult = ref(null)

// ============== Computed ==============

const isConfigured = computed(() => status.value?.is_configured || false)
const isActive = computed(() => status.value?.is_active || false)

const statusBadge = computed(() => {
  if (!isConfigured.value) return { text: 'Nicht konfiguriert', class: 'bg-gray-100 text-gray-700' }
  if (!isActive.value) return { text: 'Deaktiviert', class: 'bg-yellow-100 text-yellow-700' }
  if (status.value?.test_mode) return { text: 'Test-Modus', class: 'bg-blue-100 text-blue-700' }
  return { text: 'Aktiv', class: 'bg-green-100 text-green-700' }
})

const eventStatusClass = (eventStatus) => {
  switch (eventStatus) {
    case 'sent':
      return 'text-green-600'
    case 'test':
      return 'text-blue-600'
    case 'failed':
      return 'text-red-600'
    default:
      return 'text-gray-600'
  }
}

// ============== Methods ==============

async function loadStatus() {
  try {
    const { data } = await getMetaStatus()
    status.value = data
  } catch (err) {
    console.error('Failed to load Meta status:', err)
  }
}

async function loadIntegration() {
  try {
    const { data } = await getMetaIntegration()
    integration.value = data
    if (data) {
      form.value.pixel_id = data.pixel_id
      form.value.ad_account_id = data.ad_account_id || ''
      form.value.test_mode = data.test_mode
      // Don't populate access_token - it's masked
    }
  } catch (err) {
    console.error('Failed to load integration:', err)
  }
}

async function loadSetupGuide() {
  try {
    const { data } = await getSetupGuide()
    setupGuide.value = data
  } catch (err) {
    console.error('Failed to load setup guide:', err)
  }
}

async function loadEvents() {
  eventsLoading.value = true
  try {
    const { data } = await getConversionEvents({
      page: eventsPage.value,
      page_size: 20,
      days: statsDays.value
    })
    events.value = data.items
    eventsTotal.value = data.total
  } catch (err) {
    console.error('Failed to load events:', err)
  } finally {
    eventsLoading.value = false
  }
}

async function loadStats() {
  try {
    const { data } = await getMetaStats(statsDays.value)
    stats.value = data
  } catch (err) {
    console.error('Failed to load stats:', err)
  }
}

async function saveIntegration() {
  loading.value = true
  error.value = null
  success.value = null

  try {
    const payload = {
      pixel_id: form.value.pixel_id,
      test_mode: form.value.test_mode
    }

    // Only include access_token if provided (new or updated)
    if (form.value.access_token) {
      payload.access_token = form.value.access_token
    }

    // Only include ad_account_id if provided
    if (form.value.ad_account_id) {
      payload.ad_account_id = form.value.ad_account_id
    }

    if (integration.value) {
      // Update existing
      await updateMetaIntegration(payload)
    } else {
      // Create new - access_token is required
      if (!form.value.access_token) {
        error.value = 'Access Token ist erforderlich'
        return
      }
      await createMetaIntegration(payload)
    }

    success.value = 'Integration erfolgreich gespeichert'
    showForm.value = false
    form.value.access_token = '' // Clear token after save

    // Reload data
    await Promise.all([loadStatus(), loadIntegration()])
  } catch (err) {
    error.value = err.response?.data?.detail || err.message
  } finally {
    loading.value = false
  }
}

async function deactivateIntegration() {
  if (!confirm('Meta-Integration wirklich deaktivieren?')) return

  loading.value = true
  error.value = null

  try {
    await deleteMetaIntegration()
    success.value = 'Integration deaktiviert'
    await Promise.all([loadStatus(), loadIntegration()])
  } catch (err) {
    error.value = err.response?.data?.detail || err.message
  } finally {
    loading.value = false
  }
}

async function runTestEvent() {
  testLoading.value = true
  testResult.value = null

  try {
    const { data } = await sendTestEvent({
      event_name: 'PageView',
      url: window.location.href
    })
    testResult.value = data
    if (data.success) {
      // Reload events to show the test event
      await loadEvents()
    }
  } catch (err) {
    testResult.value = {
      success: false,
      message: err.response?.data?.detail || err.message
    }
  } finally {
    testLoading.value = false
  }
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// ============== Lifecycle ==============

onMounted(async () => {
  loading.value = true
  try {
    await Promise.all([loadStatus(), loadIntegration(), loadSetupGuide()])
    if (isConfigured.value) {
      await Promise.all([loadEvents(), loadStats()])
    }
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h3 class="text-lg font-medium">
          Meta Conversions API
        </h3>
        <p class="text-sm text-gray-500">
          Server-side Event-Tracking für bessere Attribution und Ad-Optimierung
        </p>
      </div>
      <span :class="['rounded-full px-3 py-1 text-sm font-medium', statusBadge.class]">
        {{ statusBadge.text }}
      </span>
    </div>

    <!-- Alerts -->
    <div
      v-if="error"
      class="rounded-lg bg-red-50 p-4 text-red-700"
    >
      {{ error }}
      <button
        class="ml-2 underline"
        @click="error = null"
      >
        Schließen
      </button>
    </div>
    <div
      v-if="success"
      class="rounded-lg bg-green-50 p-4 text-green-700"
    >
      {{ success }}
      <button
        class="ml-2 underline"
        @click="success = null"
      >
        Schließen
      </button>
    </div>

    <!-- Not Configured State -->
    <div
      v-if="!isConfigured && !showForm"
      class="rounded-lg border-2 border-dashed border-gray-300 p-8 text-center"
    >
      <svg
        class="mx-auto h-12 w-12 text-gray-400"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M13 10V3L4 14h7v7l9-11h-7z"
        />
      </svg>
      <h3 class="mt-4 text-lg font-medium text-gray-900">
        Meta-Integration einrichten
      </h3>
      <p class="mt-2 text-sm text-gray-500">
        Verbinden Sie Ihr Meta-Pixel für server-seitiges Conversion-Tracking.
      </p>
      <button
        class="mt-4 rounded-lg bg-go4-primary px-4 py-2 text-white hover:bg-go4-primary/90"
        @click="showForm = true"
      >
        Integration starten
      </button>
    </div>

    <!-- Setup Form -->
    <div
      v-if="showForm"
      class="rounded-lg border bg-white p-6"
    >
      <h4 class="mb-4 text-lg font-medium">
        Integration konfigurieren
      </h4>

      <div class="space-y-4">
        <!-- Pixel ID -->
        <div>
          <label class="mb-1 block text-sm font-medium text-gray-700">
            Pixel ID *
          </label>
          <input
            v-model="form.pixel_id"
            type="text"
            placeholder="1234567890123456"
            class="w-full rounded-lg border px-3 py-2 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
            pattern="\d{15,16}"
          >
          <p class="mt-1 text-xs text-gray-500">
            15-16-stellige ID aus dem Meta Events Manager
          </p>
        </div>

        <!-- Access Token -->
        <div>
          <label class="mb-1 block text-sm font-medium text-gray-700">
            Access Token {{ integration ? '(leer lassen um beizubehalten)' : '*' }}
          </label>
          <div class="relative">
            <input
              v-model="form.access_token"
              :type="showToken ? 'text' : 'password'"
              placeholder="EAAxxxxxxx..."
              class="w-full rounded-lg border px-3 py-2 pr-10 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
            >
            <button
              type="button"
              class="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              @click="showToken = !showToken"
            >
              <svg
                v-if="showToken"
                class="h-5 w-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"
                />
              </svg>
              <svg
                v-else
                class="h-5 w-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                />
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                />
              </svg>
            </button>
          </div>
          <p class="mt-1 text-xs text-gray-500">
            System User Token mit ads_management Berechtigung
          </p>
        </div>

        <!-- Ad Account ID (optional) -->
        <div>
          <label class="mb-1 block text-sm font-medium text-gray-700">
            Ad Account ID (optional)
          </label>
          <input
            v-model="form.ad_account_id"
            type="text"
            placeholder="act_1234567890"
            class="w-full rounded-lg border px-3 py-2 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
          >
          <p class="mt-1 text-xs text-gray-500">
            Für Custom Audiences (wird in Phase 9b benötigt)
          </p>
        </div>

        <!-- Test Mode -->
        <div class="flex items-center gap-2">
          <input
            id="test_mode"
            v-model="form.test_mode"
            type="checkbox"
            class="h-4 w-4 rounded border-gray-300 text-go4-primary focus:ring-go4-primary"
          >
          <label
            for="test_mode"
            class="text-sm text-gray-700"
          >
            Test-Modus (Events erscheinen unter "Test Events" im Events Manager)
          </label>
        </div>

        <!-- Actions -->
        <div class="flex gap-3 pt-2">
          <button
            :disabled="loading || !form.pixel_id"
            class="rounded-lg bg-go4-primary px-4 py-2 text-white hover:bg-go4-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
            @click="saveIntegration"
          >
            {{ loading ? 'Speichern...' : 'Speichern' }}
          </button>
          <button
            class="rounded-lg border px-4 py-2 text-gray-700 hover:bg-gray-50"
            @click="showForm = false"
          >
            Abbrechen
          </button>
        </div>
      </div>
    </div>

    <!-- Configured State -->
    <template v-if="isConfigured && !showForm">
      <!-- Configuration Summary -->
      <div class="rounded-lg border bg-white p-4">
        <div class="flex items-center justify-between">
          <div class="space-y-1">
            <div class="flex items-center gap-2">
              <span class="font-medium">Pixel ID:</span>
              <code class="rounded bg-gray-100 px-2 py-0.5 text-sm">{{ integration?.pixel_id }}</code>
            </div>
            <div class="flex items-center gap-2 text-sm text-gray-500">
              <span>Token:</span>
              <code>{{ integration?.access_token_masked }}</code>
            </div>
            <div
              v-if="status?.last_event_at"
              class="text-sm text-gray-500"
            >
              Letztes Event: {{ formatDate(status.last_event_at) }}
            </div>
          </div>
          <div class="flex gap-2">
            <button
              class="rounded-lg border px-3 py-1.5 text-sm hover:bg-gray-50"
              @click="showForm = true"
            >
              Bearbeiten
            </button>
            <button
              class="rounded-lg border border-red-200 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50"
              @click="deactivateIntegration"
            >
              Deaktivieren
            </button>
          </div>
        </div>
      </div>

      <!-- Test Event -->
      <div class="rounded-lg border bg-white p-4">
        <div class="flex items-center justify-between">
          <div>
            <h4 class="font-medium">
              Verbindung testen
            </h4>
            <p class="text-sm text-gray-500">
              Sende ein Test-Event an Meta um die Integration zu verifizieren
            </p>
          </div>
          <button
            :disabled="testLoading"
            class="rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
            @click="runTestEvent"
          >
            {{ testLoading ? 'Sende...' : 'Test-Event senden' }}
          </button>
        </div>

        <!-- Test Result -->
        <div
          v-if="testResult"
          :class="[
            'mt-4 rounded-lg p-3',
            testResult.success ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
          ]"
        >
          <div class="flex items-center gap-2">
            <svg
              v-if="testResult.success"
              class="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M5 13l4 4L19 7"
              />
            </svg>
            <svg
              v-else
              class="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
            <span>{{ testResult.message }}</span>
          </div>
          <div
            v-if="testResult.event_id"
            class="mt-1 text-sm opacity-75"
          >
            Event ID: {{ testResult.event_id }}
          </div>
        </div>
      </div>

      <!-- Statistics -->
      <div
        v-if="stats"
        class="rounded-lg border bg-white p-4"
      >
        <div class="mb-4 flex items-center justify-between">
          <h4 class="font-medium">
            Statistiken
          </h4>
          <select
            v-model="statsDays"
            class="rounded border px-2 py-1 text-sm"
            @change="loadStats(); loadEvents()"
          >
            <option :value="7">
              Letzte 7 Tage
            </option>
            <option :value="30">
              Letzte 30 Tage
            </option>
            <option :value="90">
              Letzte 90 Tage
            </option>
          </select>
        </div>

        <div class="grid grid-cols-4 gap-4">
          <div class="rounded-lg bg-gray-50 p-3 text-center">
            <div class="text-2xl font-bold text-gray-900">
              {{ stats.total_events }}
            </div>
            <div class="text-sm text-gray-500">
              Events gesamt
            </div>
          </div>
          <div class="rounded-lg bg-green-50 p-3 text-center">
            <div class="text-2xl font-bold text-green-600">
              {{ stats.events_sent }}
            </div>
            <div class="text-sm text-gray-500">
              Gesendet
            </div>
          </div>
          <div class="rounded-lg bg-red-50 p-3 text-center">
            <div class="text-2xl font-bold text-red-600">
              {{ stats.events_failed }}
            </div>
            <div class="text-sm text-gray-500">
              Fehlgeschlagen
            </div>
          </div>
          <div class="rounded-lg bg-blue-50 p-3 text-center">
            <div class="text-2xl font-bold text-blue-600">
              {{ stats.success_rate.toFixed(1) }}%
            </div>
            <div class="text-sm text-gray-500">
              Erfolgsrate
            </div>
          </div>
        </div>

        <!-- Events by Type -->
        <div
          v-if="Object.keys(stats.events_by_type).length > 0"
          class="mt-4"
        >
          <h5 class="mb-2 text-sm font-medium text-gray-700">
            Nach Event-Typ
          </h5>
          <div class="flex flex-wrap gap-2">
            <span
              v-for="(count, eventType) in stats.events_by_type"
              :key="eventType"
              class="rounded-full bg-gray-100 px-3 py-1 text-sm"
            >
              {{ eventType }}: {{ count }}
            </span>
          </div>
        </div>
      </div>

      <!-- Recent Events -->
      <div class="rounded-lg border bg-white">
        <div class="border-b px-4 py-3">
          <h4 class="font-medium">
            Letzte Events
          </h4>
        </div>

        <div
          v-if="eventsLoading"
          class="p-8 text-center text-gray-500"
        >
          Lade Events...
        </div>

        <div
          v-else-if="events.length === 0"
          class="p-8 text-center text-gray-500"
        >
          Noch keine Events gesendet
        </div>

        <table
          v-else
          class="w-full"
        >
          <thead class="bg-gray-50 text-left text-sm text-gray-500">
            <tr>
              <th class="px-4 py-2">
                Zeit
              </th>
              <th class="px-4 py-2">
                Event
              </th>
              <th class="px-4 py-2">
                Contact
              </th>
              <th class="px-4 py-2">
                Status
              </th>
              <th class="px-4 py-2">
                Event ID
              </th>
            </tr>
          </thead>
          <tbody class="divide-y text-sm">
            <tr
              v-for="event in events"
              :key="event.id"
              class="hover:bg-gray-50"
            >
              <td class="px-4 py-2 text-gray-500">
                {{ formatDate(event.event_time) }}
              </td>
              <td class="px-4 py-2 font-medium">
                {{ event.event_name }}
              </td>
              <td class="px-4 py-2">
                {{ event.contact_name || '-' }}
              </td>
              <td class="px-4 py-2">
                <span :class="eventStatusClass(event.status)">
                  {{ event.status === 'sent' ? '✓' : event.status === 'test' ? '🧪' : '✗' }}
                  {{ event.status }}
                </span>
              </td>
              <td class="px-4 py-2 font-mono text-xs text-gray-400">
                {{ event.event_id.substring(0, 20) }}...
              </td>
            </tr>
          </tbody>
        </table>

        <!-- Pagination -->
        <div
          v-if="eventsTotal > 20"
          class="flex items-center justify-between border-t px-4 py-3"
        >
          <span class="text-sm text-gray-500">
            {{ eventsTotal }} Events gesamt
          </span>
          <div class="flex gap-2">
            <button
              :disabled="eventsPage === 1"
              class="rounded border px-3 py-1 text-sm disabled:opacity-50"
              @click="eventsPage--; loadEvents()"
            >
              Zurück
            </button>
            <button
              :disabled="eventsPage * 20 >= eventsTotal"
              class="rounded border px-3 py-1 text-sm disabled:opacity-50"
              @click="eventsPage++; loadEvents()"
            >
              Weiter
            </button>
          </div>
        </div>
      </div>
    </template>

    <!-- Setup Guide (collapsed) -->
    <details
      v-if="setupGuide"
      class="rounded-lg border bg-white"
    >
      <summary class="cursor-pointer px-4 py-3 font-medium">
        Setup-Anleitung
      </summary>
      <div class="border-t px-4 py-4">
        <ol class="space-y-4">
          <li
            v-for="step in setupGuide.steps"
            :key="step.step"
            class="flex gap-3"
          >
            <span class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-go4-primary text-sm text-white">
              {{ step.step }}
            </span>
            <div>
              <div class="font-medium">
                {{ step.title }}
              </div>
              <div class="text-sm text-gray-500">
                {{ step.description }}
              </div>
              <a
                v-if="step.link"
                :href="step.link"
                target="_blank"
                class="text-sm text-go4-primary hover:underline"
              >
                Öffnen →
              </a>
            </div>
          </li>
        </ol>
      </div>
    </details>
  </div>
</template>
