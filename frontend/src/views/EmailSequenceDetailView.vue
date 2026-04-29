<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useEmailMarketingStore } from '@/stores/emailmarketing'
import PageHeader from '@/components/ui/PageHeader.vue'

const route = useRoute()
const router = useRouter()
const store = useEmailMarketingStore()

const loading = ref(true)
const activeTab = ref('steps')

const sequence = computed(() => store.currentSequence)

function formatDate(date) {
  if (!date) return '-'
  return new Date(date).toLocaleDateString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function getStatusClass(status) {
  const classes = {
    draft: 'bg-gray-100 text-gray-700',
    active: 'bg-green-100 text-green-700',
    paused: 'bg-yellow-100 text-yellow-700'
  }
  return classes[status] || 'bg-gray-100 text-gray-700'
}

function getStatusLabel(status) {
  const labels = {
    draft: 'Entwurf',
    active: 'Aktiv',
    paused: 'Pausiert'
  }
  return labels[status] || status
}

async function activate() {
  try {
    await store.activateSequenceById(sequence.value.id)
  } catch (err) {
    alert(store.error)
  }
}

async function pause() {
  await store.pauseSequenceById(sequence.value.id)
}

function editSequence() {
  router.push({ name: 'emailmarketing-sequence-edit', params: { id: sequence.value.id } })
}

async function loadData() {
  loading.value = true
  try {
    await store.fetchSequence(route.params.id)
    if (store.currentSequence) {
      await store.fetchEnrollments(route.params.id)
    }
  } catch (err) {
    router.push({ name: 'emailmarketing' })
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>

<template>
  <div class="p-6">
    <div
      v-if="loading"
      class="flex items-center justify-center py-12"
    >
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
    </div>

    <template v-else-if="sequence">
      <PageHeader
        :title="sequence.name"
      >
        <template #actions>
          <span
            :class="[
              'px-3 py-1 text-sm font-medium rounded-full mr-4',
              getStatusClass(sequence.status)
            ]"
          >
            {{ getStatusLabel(sequence.status) }}
          </span>
          <button
            class="btn btn-secondary mr-2"
            @click="editSequence"
          >
            Bearbeiten
          </button>
          <button
            v-if="sequence.status === 'draft' || sequence.status === 'paused'"
            class="btn btn-primary"
            @click="activate"
          >
            Aktivieren
          </button>
          <button
            v-if="sequence.status === 'active'"
            class="btn btn-secondary"
            @click="pause"
          >
            Pausieren
          </button>
        </template>
      </PageHeader>

      <!-- Tabs -->
      <div class="border-b border-gray-200 mb-6">
        <nav class="-mb-px flex space-x-8">
          <button
            :class="[
              'py-4 px-1 border-b-2 font-medium text-sm',
              activeTab === 'steps'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            ]"
            @click="activeTab = 'steps'"
          >
            Schritte ({{ sequence.steps?.length || 0 }})
          </button>
          <button
            :class="[
              'py-4 px-1 border-b-2 font-medium text-sm',
              activeTab === 'enrollments'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            ]"
            @click="activeTab = 'enrollments'"
          >
            Eingeschrieben ({{ sequence.total_enrolled }})
          </button>
          <button
            :class="[
              'py-4 px-1 border-b-2 font-medium text-sm',
              activeTab === 'settings'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            ]"
            @click="activeTab = 'settings'"
          >
            Einstellungen
          </button>
        </nav>
      </div>

      <!-- Steps Tab -->
      <div
        v-if="activeTab === 'steps'"
        class="space-y-4"
      >
        <div
          v-if="!sequence.steps?.length"
          class="text-center py-12 text-gray-500"
        >
          Keine Schritte vorhanden. Bearbeiten Sie die Sequenz, um Schritte hinzuzufügen.
        </div>
        <div
          v-for="(step, index) in sequence.steps"
          :key="step.id"
          class="bg-white rounded-lg shadow p-4"
        >
          <div class="flex items-start justify-between">
            <div class="flex items-center space-x-4">
              <div
                class="w-8 h-8 rounded-full bg-primary-100 text-primary-700 flex items-center justify-center font-medium"
              >
                {{ index + 1 }}
              </div>
              <div>
                <p class="font-medium text-gray-900">
                  {{ step.subject }}
                </p>
                <p class="text-sm text-gray-500">
                  Nach {{ step.delay_days }} Tag(en)
                  <span v-if="step.delay_hours"> und {{ step.delay_hours }} Stunde(n)</span>
                </p>
              </div>
            </div>
            <div class="flex items-center space-x-4 text-sm text-gray-500">
              <span>{{ step.sent_count }} gesendet</span>
              <span>{{ step.opened_count }} geöffnet</span>
              <span>{{ step.clicked_count }} geklickt</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Enrollments Tab -->
      <div v-if="activeTab === 'enrollments'">
        <div
          v-if="!store.enrollments?.length"
          class="text-center py-12 text-gray-500"
        >
          Keine Kontakte eingeschrieben.
        </div>
        <div
          v-else
          class="bg-white rounded-lg shadow overflow-hidden"
        >
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Kontakt
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Status
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Schritt
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Nächster Versand
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Eingeschrieben
                </th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <tr
                v-for="enrollment in store.enrollments"
                :key="enrollment.id"
              >
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="font-medium text-gray-900">
                    {{ enrollment.contact_name || '-' }}
                  </div>
                  <div class="text-sm text-gray-500">
                    {{ enrollment.contact_email }}
                  </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <span
                    :class="[
                      'px-2 py-1 text-xs font-medium rounded-full',
                      getStatusClass(enrollment.status)
                    ]"
                  >
                    {{ enrollment.status }}
                  </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-gray-500">
                  {{ enrollment.current_step }} / {{ sequence.steps?.length || 0 }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-gray-500">
                  {{ formatDate(enrollment.next_send_at) }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-gray-500">
                  {{ formatDate(enrollment.enrolled_at) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Settings Tab -->
      <div
        v-if="activeTab === 'settings'"
        class="bg-white rounded-lg shadow p-6"
      >
        <dl class="grid grid-cols-2 gap-4">
          <div>
            <dt class="text-sm text-gray-500">
              Trigger
            </dt>
            <dd class="text-gray-900">
              {{ sequence.trigger_type }}
            </dd>
          </div>
          <div>
            <dt class="text-sm text-gray-500">
              Zeitzone
            </dt>
            <dd class="text-gray-900">
              {{ sequence.timezone }}
            </dd>
          </div>
          <div>
            <dt class="text-sm text-gray-500">
              Sendefenster
            </dt>
            <dd class="text-gray-900">
              {{ sequence.send_window_start || '-' }} - {{ sequence.send_window_end || '-' }}
            </dd>
          </div>
          <div>
            <dt class="text-sm text-gray-500">
              Wochenenden überspringen
            </dt>
            <dd class="text-gray-900">
              {{ sequence.skip_weekends ? 'Ja' : 'Nein' }}
            </dd>
          </div>
          <div>
            <dt class="text-sm text-gray-500">
              Abgeschlossen
            </dt>
            <dd class="text-gray-900">
              {{ sequence.total_completed }}
            </dd>
          </div>
          <div>
            <dt class="text-sm text-gray-500">
              Abgemeldet
            </dt>
            <dd class="text-gray-900">
              {{ sequence.total_unsubscribed }}
            </dd>
          </div>
        </dl>
      </div>
    </template>
  </div>
</template>
