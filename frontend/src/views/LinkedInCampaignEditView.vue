<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useLinkedInStore } from '@/stores/linkedin'
import PageHeader from '@/components/ui/PageHeader.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'

const router = useRouter()
const route = useRoute()
const store = useLinkedInStore()

const props = defineProps({
  id: { type: [String, Number], default: null }
})

const isEdit = computed(() => !!props.id)

const form = ref({
  name: '',
  description: '',
  account_id: null,
  daily_limit: 50,
  stop_on_reply: true
})

const steps = ref([])
const saving = ref(false)
const error = ref(null)
const showDeleteStepConfirm = ref(false)
const stepToDelete = ref(null)

const stepTypes = [
  {
    value: 'connect',
    label: 'Kontaktanfrage',
    icon: 'M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z'
  },
  {
    value: 'message',
    label: 'Nachricht senden',
    icon: 'M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z'
  },
  { value: 'wait', label: 'Warten', icon: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z' },
  {
    value: 'condition',
    label: 'Bedingung',
    icon: 'M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z'
  }
]

const conditionTypes = [
  { value: 'connected', label: 'Verbunden' },
  { value: 'not_connected', label: 'Nicht verbunden' },
  { value: 'replied', label: 'Hat geantwortet' },
  { value: 'not_replied', label: 'Keine Antwort' }
]

onMounted(async () => {
  await store.fetchAccounts()
  await store.fetchTemplates()

  if (isEdit.value) {
    try {
      const campaign = await store.fetchCampaign(props.id)
      form.value = {
        name: campaign.name,
        description: campaign.description || '',
        account_id: campaign.account_id,
        daily_limit: campaign.daily_limit || 50,
        stop_on_reply: campaign.stop_on_reply !== false
      }
      steps.value =
        campaign.steps?.map((s) => ({
          id: s.id,
          type: s.action_type,
          delay_hours: s.delay_hours || 0,
          template_id: s.template_ids?.[0] || null,
          note: s.note || '',
          condition_type: s.condition_type || null,
          wait_hours: s.action_type === 'wait' ? s.delay_hours : 24
        })) || []
    } catch {
      error.value = 'Kampagne konnte nicht geladen werden'
    }
  }
})

const connectionTemplates = computed(() =>
  store.templates.filter((t) => t.type === 'connection_note')
)

const messageTemplates = computed(() =>
  store.templates.filter((t) => t.type === 'message' || t.type === 'follow_up')
)

function addStep(type) {
  const newStep = {
    id: null,
    type,
    delay_hours: steps.value.length > 0 ? 24 : 0,
    template_id: null,
    note: '',
    condition_type: null,
    wait_hours: 24
  }
  steps.value.push(newStep)
}

function removeStep(index) {
  stepToDelete.value = index
  showDeleteStepConfirm.value = true
}

function confirmRemoveStep() {
  if (stepToDelete.value !== null) {
    steps.value.splice(stepToDelete.value, 1)
  }
  showDeleteStepConfirm.value = false
  stepToDelete.value = null
}

function moveStep(index, direction) {
  const newIndex = index + direction
  if (newIndex < 0 || newIndex >= steps.value.length) return
  const temp = steps.value[index]
  steps.value[index] = steps.value[newIndex]
  steps.value[newIndex] = temp
}

async function save() {
  if (!form.value.name) {
    error.value = 'Name ist erforderlich'
    return
  }

  if (!form.value.account_id) {
    error.value = 'Bitte waehle einen Account aus'
    return
  }

  if (steps.value.length === 0) {
    error.value = 'Fuege mindestens einen Schritt hinzu'
    return
  }

  saving.value = true
  error.value = null

  try {
    const campaignData = {
      name: form.value.name,
      description: form.value.description || null,
      account_id: form.value.account_id,
      daily_limit: form.value.daily_limit,
      stop_on_reply: form.value.stop_on_reply,
      steps: steps.value.map((s, index) => ({
        order: index + 1,
        action_type: s.type,
        delay_hours: s.type === 'wait' ? s.wait_hours : s.delay_hours,
        template_ids: s.template_id ? [s.template_id] : [],
        note: s.note || null,
        condition_type: s.type === 'condition' ? s.condition_type : null
      }))
    }

    if (isEdit.value) {
      await store.editCampaign(props.id, campaignData)
      router.push(`/linkedin/campaigns/${props.id}`)
    } else {
      const newCampaign = await store.addCampaign(campaignData)
      router.push(`/linkedin/campaigns/${newCampaign.id}`)
    }
  } catch (err) {
    error.value = err.response?.data?.detail || err.message
  } finally {
    saving.value = false
  }
}

function cancel() {
  if (isEdit.value) {
    router.push(`/linkedin/campaigns/${props.id}`)
  } else {
    router.push('/linkedin/campaigns')
  }
}

function getStepIcon(type) {
  return stepTypes.find((t) => t.value === type)?.icon || ''
}

function getStepLabel(type) {
  return stepTypes.find((t) => t.value === type)?.label || type
}
</script>

<template>
  <div class="bg-go4-bg dark:bg-gray-900">
    <PageHeader
      :title="isEdit ? 'Kampagne bearbeiten' : 'Neue Kampagne'"
    />

    <div class="sm: lg:">
      <div
        v-if="error"
        class="mb-6 rounded-lg bg-red-50 p-4 text-red-700 dark:bg-red-900/30 dark:text-red-300"
      >
        {{ error }}
      </div>

      <div class="space-y-6">
        <!-- Basic Info -->
        <div
          class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800"
        >
          <h2 class="mb-4 text-lg font-medium text-go4-secondary dark:text-white">
            Grundeinstellungen
          </h2>

          <div class="grid gap-4 md:grid-cols-2">
            <div>
              <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-300">
                Name *
              </label>
              <input
                v-model="form.name"
                type="text"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                placeholder="z.B. Sales Outreach Q1"
              >
            </div>

            <div>
              <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-300">
                Account *
              </label>
              <select
                v-model="form.account_id"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
                <option :value="null">
                  Account waehlen...
                </option>
                <option
                  v-for="account in store.activeAccounts"
                  :key="account.id"
                  :value="account.id"
                >
                  {{ account.name }} ({{ account.email }})
                </option>
              </select>
            </div>

            <div class="md:col-span-2">
              <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-300">
                Beschreibung
              </label>
              <textarea
                v-model="form.description"
                rows="2"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                placeholder="Optional: Beschreibung der Kampagne"
              />
            </div>

            <div>
              <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-300">
                Taegliches Limit
              </label>
              <input
                v-model.number="form.daily_limit"
                type="number"
                min="1"
                max="100"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
              <p class="mt-1 text-xs text-go4-muted">
                Max. Aktionen pro Tag (empfohlen: 20-50)
              </p>
            </div>

            <div class="flex items-center">
              <label class="flex cursor-pointer items-center gap-3">
                <input
                  v-model="form.stop_on_reply"
                  type="checkbox"
                  class="h-4 w-4 rounded border-gray-300 text-go4-primary focus:ring-go4-primary"
                >
                <span class="text-sm text-go4-secondary dark:text-gray-300">
                  Bei Antwort automatisch stoppen
                </span>
              </label>
            </div>
          </div>
        </div>

        <!-- Campaign Steps -->
        <div
          class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800"
        >
          <div class="mb-4 flex items-center justify-between">
            <h2 class="text-lg font-medium text-go4-secondary dark:text-white">
              Kampagnen-Schritte
            </h2>
            <span class="text-sm text-go4-muted"> {{ steps.length }} Schritte </span>
          </div>

          <!-- Steps List -->
          <div
            v-if="steps.length > 0"
            class="mb-4 space-y-3"
          >
            <div
              v-for="(step, index) in steps"
              :key="index"
              class="rounded-lg border border-gray-200 bg-gray-50 p-4 dark:border-gray-600 dark:bg-gray-700"
            >
              <div class="mb-3 flex items-center justify-between">
                <div class="flex items-center gap-3">
                  <span
                    class="flex h-6 w-6 items-center justify-center rounded-full bg-go4-primary text-xs font-medium text-white"
                  >
                    {{ index + 1 }}
                  </span>
                  <svg
                    class="h-5 w-5 text-go4-muted"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      :d="getStepIcon(step.type)"
                    />
                  </svg>
                  <span class="font-medium text-go4-secondary dark:text-white">
                    {{ getStepLabel(step.type) }}
                  </span>
                </div>
                <div class="flex items-center gap-1">
                  <button
                    v-if="index > 0"
                    class="rounded p-1 text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600"
                    title="Nach oben"
                    @click="moveStep(index, -1)"
                  >
                    <svg
                      class="h-4 w-4"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M5 15l7-7 7 7"
                      />
                    </svg>
                  </button>
                  <button
                    v-if="index < steps.length - 1"
                    class="rounded p-1 text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600"
                    title="Nach unten"
                    @click="moveStep(index, 1)"
                  >
                    <svg
                      class="h-4 w-4"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M19 9l-7 7-7-7"
                      />
                    </svg>
                  </button>
                  <button
                    class="rounded p-1 text-gray-400 hover:bg-red-100 hover:text-red-600 dark:hover:bg-red-900/30"
                    title="Loeschen"
                    @click="removeStep(index)"
                  >
                    <svg
                      class="h-4 w-4"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
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

              <!-- Step Config -->
              <div class="grid gap-3 md:grid-cols-2">
                <!-- Delay -->
                <div v-if="index > 0 && step.type !== 'wait'">
                  <label class="mb-1 block text-xs text-go4-muted"> Verzoegerung (Stunden) </label>
                  <input
                    v-model.number="step.delay_hours"
                    type="number"
                    min="0"
                    class="w-full rounded border border-gray-300 px-2 py-1 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
                  >
                </div>

                <!-- Wait Hours -->
                <div v-if="step.type === 'wait'">
                  <label class="mb-1 block text-xs text-go4-muted"> Wartezeit (Stunden) </label>
                  <input
                    v-model.number="step.wait_hours"
                    type="number"
                    min="1"
                    class="w-full rounded border border-gray-300 px-2 py-1 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
                  >
                </div>

                <!-- Template for Connect -->
                <div v-if="step.type === 'connect'">
                  <label class="mb-1 block text-xs text-go4-muted"> Kontaktanfrage-Vorlage </label>
                  <select
                    v-model="step.template_id"
                    class="w-full rounded border border-gray-300 px-2 py-1 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
                  >
                    <option :value="null">
                      Ohne Notiz
                    </option>
                    <option
                      v-for="template in connectionTemplates"
                      :key="template.id"
                      :value="template.id"
                    >
                      {{ template.name }}
                    </option>
                  </select>
                </div>

                <!-- Note for Connect -->
                <div
                  v-if="step.type === 'connect' && !step.template_id"
                  class="md:col-span-2"
                >
                  <label class="mb-1 block text-xs text-go4-muted">
                    Individuelle Notiz (max. 300 Zeichen)
                  </label>
                  <textarea
                    v-model="step.note"
                    rows="2"
                    maxlength="300"
                    class="w-full rounded border border-gray-300 px-2 py-1 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
                    placeholder="Optional: {first_name}, ich wuerde mich gerne vernetzen..."
                  />
                </div>

                <!-- Template for Message -->
                <div
                  v-if="step.type === 'message'"
                  class="md:col-span-2"
                >
                  <label class="mb-1 block text-xs text-go4-muted"> Nachrichtenvorlage * </label>
                  <select
                    v-model="step.template_id"
                    class="w-full rounded border border-gray-300 px-2 py-1 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
                  >
                    <option :value="null">
                      Vorlage waehlen...
                    </option>
                    <option
                      v-for="template in messageTemplates"
                      :key="template.id"
                      :value="template.id"
                    >
                      {{ template.name }}
                    </option>
                  </select>
                </div>

                <!-- Condition -->
                <div
                  v-if="step.type === 'condition'"
                  class="md:col-span-2"
                >
                  <label class="mb-1 block text-xs text-go4-muted"> Bedingung </label>
                  <select
                    v-model="step.condition_type"
                    class="w-full rounded border border-gray-300 px-2 py-1 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
                  >
                    <option :value="null">
                      Bedingung waehlen...
                    </option>
                    <option
                      v-for="condition in conditionTypes"
                      :key="condition.value"
                      :value="condition.value"
                    >
                      {{ condition.label }}
                    </option>
                  </select>
                </div>
              </div>
            </div>
          </div>

          <!-- Empty State -->
          <div
            v-else
            class="mb-4 rounded-lg border-2 border-dashed border-gray-200 p-8 text-center dark:border-gray-600"
          >
            <p class="text-go4-muted">
              Fuege Schritte hinzu um deinen Workflow zu definieren
            </p>
          </div>

          <!-- Add Step Buttons -->
          <div class="flex flex-wrap gap-2">
            <button
              v-for="type in stepTypes"
              :key="type.value"
              class="flex items-center gap-2 rounded-lg border border-gray-300 px-3 py-2 text-sm text-go4-secondary hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
              @click="addStep(type.value)"
            >
              <svg
                class="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  :d="type.icon"
                />
              </svg>
              {{ type.label }}
            </button>
          </div>
        </div>

        <!-- Actions -->
        <div class="flex gap-3">
          <button
            class="flex-1 rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark disabled:opacity-50"
            :disabled="saving"
            @click="save"
          >
            {{ saving ? 'Speichern...' : isEdit ? 'Aktualisieren' : 'Kampagne erstellen' }}
          </button>
          <button
            class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
            @click="cancel"
          >
            Abbrechen
          </button>
        </div>
      </div>
    </div>

    <!-- Delete Step Confirmation -->
    <ConfirmDialog
      :open="showDeleteStepConfirm"
      title="Schritt loeschen?"
      message="Moechtest du diesen Schritt wirklich loeschen?"
      confirm-text="Loeschen"
      variant="danger"
      @confirm="confirmRemoveStep"
      @cancel="showDeleteStepConfirm = false"
    />
  </div>
</template>
