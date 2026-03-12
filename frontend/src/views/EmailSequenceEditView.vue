<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useEmailMarketingStore } from '@/stores/emailmarketing'
import PageHeader from '@/components/ui/PageHeader.vue'

const route = useRoute()
const router = useRouter()
const store = useEmailMarketingStore()

const isNew = computed(() => !route.params.id)
const loading = ref(true)
const saving = ref(false)
const showStepModal = ref(false)
const editingStep = ref(null)

const form = ref({
  name: '',
  description: '',
  provider_id: null,
  trigger_type: 'manual',
  trigger_filters: null,
  send_window_start: '09:00',
  send_window_end: '18:00',
  skip_weekends: true,
  timezone: 'Europe/Berlin'
})

const stepForm = ref({
  position: 0,
  delay_days: 1,
  delay_hours: 0,
  subject: '',
  html_content: '<p>Hallo {{name}},</p>\n\n<p>Hier ist Ihre E-Mail.</p>',
  text_content: '',
  send_if_opened_previous: null,
  send_if_clicked_previous: null
})

const triggerTypes = [
  { value: 'manual', label: 'Manuell' },
  { value: 'tag_added', label: 'Tag hinzugefügt' },
  { value: 'contact_created', label: 'Kontakt erstellt' }
]

async function loadData() {
  loading.value = true
  await store.fetchProviders()

  if (!isNew.value) {
    try {
      await store.fetchSequence(route.params.id)
      if (store.currentSequence) {
        form.value = {
          name: store.currentSequence.name,
          description: store.currentSequence.description || '',
          provider_id: store.currentSequence.provider_id,
          trigger_type: store.currentSequence.trigger_type,
          trigger_filters: store.currentSequence.trigger_filters,
          send_window_start: store.currentSequence.send_window_start || '09:00',
          send_window_end: store.currentSequence.send_window_end || '18:00',
          skip_weekends: store.currentSequence.skip_weekends,
          timezone: store.currentSequence.timezone
        }
      }
    } catch (err) {
      router.push({ name: 'emailmarketing' })
    }
  }
  loading.value = false
}

async function save() {
  saving.value = true
  try {
    if (isNew.value) {
      const sequence = await store.addSequence(form.value)
      router.push({ name: 'emailmarketing-sequence-edit', params: { id: sequence.id } })
    } else {
      await store.editSequence(route.params.id, form.value)
    }
  } catch (err) {
    // Error handled by store
  } finally {
    saving.value = false
  }
}

function openAddStep() {
  editingStep.value = null
  stepForm.value = {
    position: store.currentSequence?.steps?.length || 0,
    delay_days: 1,
    delay_hours: 0,
    subject: '',
    html_content: '<p>Hallo {{name}},</p>\n\n<p>Hier ist Ihre E-Mail.</p>',
    text_content: '',
    send_if_opened_previous: null,
    send_if_clicked_previous: null
  }
  showStepModal.value = true
}

function openEditStep(step) {
  editingStep.value = step
  stepForm.value = {
    position: step.position,
    delay_days: step.delay_days,
    delay_hours: step.delay_hours,
    subject: step.subject,
    html_content: step.html_content,
    text_content: step.text_content || '',
    send_if_opened_previous: step.send_if_opened_previous,
    send_if_clicked_previous: step.send_if_clicked_previous
  }
  showStepModal.value = true
}

async function saveStep() {
  try {
    if (editingStep.value) {
      await store.editStep(route.params.id, editingStep.value.id, stepForm.value)
    } else {
      await store.addStep(route.params.id, stepForm.value)
    }
    showStepModal.value = false
    await store.fetchSequence(route.params.id)
  } catch (err) {
    alert(store.error)
  }
}

async function removeStep(step) {
  if (!confirm('Schritt wirklich löschen?')) return
  await store.removeStep(route.params.id, step.id)
  await store.fetchSequence(route.params.id)
}

onMounted(() => {
  loadData()
})
</script>

<template>
  <div class="p-6">
    <PageHeader
      :title="isNew ? 'Neue Sequenz' : 'Sequenz bearbeiten'"
      description="E-Mail-Sequenz konfigurieren"
    >
      <template #actions>
        <button
          :disabled="saving || !form.name"
          class="btn btn-primary"
          @click="save"
        >
          {{ saving ? 'Speichern...' : 'Speichern' }}
        </button>
      </template>
    </PageHeader>

    <div
      v-if="loading"
      class="flex items-center justify-center py-12"
    >
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
    </div>

    <div
      v-else
      class="space-y-6"
    >
      <!-- Basic Info -->
      <div class="bg-white rounded-lg shadow p-6">
        <h3 class="text-lg font-medium text-gray-900 mb-4">
          Grundeinstellungen
        </h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Name *</label>
            <input
              v-model="form.name"
              type="text"
              required
              class="input"
              placeholder="z.B. Onboarding-Sequenz"
            >
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Provider</label>
            <select
              v-model="form.provider_id"
              class="input"
            >
              <option :value="null">
                -- Wählen --
              </option>
              <option
                v-for="provider in store.activeProviders"
                :key="provider.id"
                :value="provider.id"
              >
                {{ provider.sender_name }} ({{ provider.provider_type }})
              </option>
            </select>
          </div>
          <div class="md:col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Beschreibung</label>
            <textarea
              v-model="form.description"
              rows="2"
              class="input"
              placeholder="Kurze Beschreibung..."
            />
          </div>
        </div>
      </div>

      <!-- Trigger -->
      <div class="bg-white rounded-lg shadow p-6">
        <h3 class="text-lg font-medium text-gray-900 mb-4">
          Trigger
        </h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Auslöser</label>
            <select
              v-model="form.trigger_type"
              class="input"
            >
              <option
                v-for="type in triggerTypes"
                :key="type.value"
                :value="type.value"
              >
                {{ type.label }}
              </option>
            </select>
          </div>
        </div>
      </div>

      <!-- Send Window -->
      <div class="bg-white rounded-lg shadow p-6">
        <h3 class="text-lg font-medium text-gray-900 mb-4">
          Sendefenster
        </h3>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Start</label>
            <input
              v-model="form.send_window_start"
              type="time"
              class="input"
            >
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Ende</label>
            <input
              v-model="form.send_window_end"
              type="time"
              class="input"
            >
          </div>
          <div class="flex items-center pt-6">
            <input
              id="skip_weekends"
              v-model="form.skip_weekends"
              type="checkbox"
              class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
            >
            <label
              for="skip_weekends"
              class="ml-2 block text-sm text-gray-900"
            >
              Wochenenden überspringen
            </label>
          </div>
        </div>
      </div>

      <!-- Steps (only for existing sequences) -->
      <div
        v-if="!isNew"
        class="bg-white rounded-lg shadow p-6"
      >
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-medium text-gray-900">
            Schritte
          </h3>
          <button
            class="btn btn-primary btn-sm"
            @click="openAddStep"
          >
            Schritt hinzufügen
          </button>
        </div>

        <div
          v-if="!store.currentSequence?.steps?.length"
          class="text-center py-8 text-gray-500"
        >
          Keine Schritte vorhanden.
        </div>
        <div
          v-else
          class="space-y-3"
        >
          <div
            v-for="(step, index) in store.currentSequence.steps"
            :key="step.id"
            class="border rounded-lg p-4 flex items-center justify-between"
          >
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
            <div class="flex space-x-2">
              <button
                class="text-gray-400 hover:text-gray-600"
                @click="openEditStep(step)"
              >
                <svg
                  class="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                  />
                </svg>
              </button>
              <button
                class="text-gray-400 hover:text-red-600"
                @click="removeStep(step)"
              >
                <svg
                  class="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                  />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Step Modal -->
    <div
      v-if="showStepModal"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click.self="showStepModal = false"
    >
      <div class="bg-white rounded-lg shadow-xl p-6 w-full max-w-2xl max-h-[80vh] overflow-auto">
        <h3 class="text-lg font-medium text-gray-900 mb-4">
          {{ editingStep ? 'Schritt bearbeiten' : 'Neuer Schritt' }}
        </h3>

        <div class="space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Verzögerung (Tage)</label>
              <input
                v-model.number="stepForm.delay_days"
                type="number"
                min="0"
                class="input"
              >
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Verzögerung (Stunden)</label>
              <input
                v-model.number="stepForm.delay_hours"
                type="number"
                min="0"
                max="23"
                class="input"
              >
            </div>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Betreff *</label>
            <input
              v-model="stepForm.subject"
              type="text"
              required
              class="input"
            >
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">HTML-Inhalt *</label>
            <textarea
              v-model="stepForm.html_content"
              rows="10"
              required
              class="input font-mono text-sm"
            />
          </div>
        </div>

        <div class="mt-6 flex justify-end space-x-2">
          <button
            class="btn btn-secondary"
            @click="showStepModal = false"
          >
            Abbrechen
          </button>
          <button
            :disabled="!stepForm.subject"
            class="btn btn-primary"
            @click="saveStep"
          >
            Speichern
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
