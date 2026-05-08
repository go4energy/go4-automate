<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useEngagementStore } from '@/stores/engagement'
import PageHeader from '@/components/ui/PageHeader.vue'

const props = defineProps({
  id: { type: [String, Number], default: null }
})

const router = useRouter()
const route = useRoute()
const store = useEngagementStore()

const loading = ref(false)
const saving = ref(false)
const error = ref(null)

const isEdit = computed(() => !!props.id || !!route.params.id)
const testId = computed(() => props.id || route.params.id)

const form = ref({
  name: '',
  description: '',
  pipeline_id: null,
  test_type: 'message',
  channel: 'linkedin',
  action_type: 'first_contact',
  sample_size: 100,
  variants: [
    { name: 'A (Control)', description: '', content: '', subject: '', weight: 50, is_control: true },
    { name: 'B', description: '', content: '', subject: '', weight: 50, is_control: false }
  ]
})

const testTypes = [
  { value: 'message', label: 'Nachricht' },
  { value: 'subject', label: 'Betreffzeile' },
  { value: 'timing', label: 'Timing' },
  { value: 'channel', label: 'Kanal' }
]

const channels = [
  { value: 'linkedin', label: 'LinkedIn' },
  { value: 'email', label: 'Email' },
  { value: 'whatsapp', label: 'WhatsApp' }
]

const actionTypes = [
  { value: 'first_contact', label: 'Erstkontakt' },
  { value: 'follow_up_1', label: 'Follow-up 1' },
  { value: 'follow_up_2', label: 'Follow-up 2' },
  { value: 'reactivation', label: 'Reaktivierung' }
]

onMounted(async () => {
  await store.fetchPipelines()

  if (isEdit.value) {
    loading.value = true
    try {
      const test = await store.fetchABTest(testId.value)
      form.value = {
        name: test.name,
        description: test.description || '',
        pipeline_id: test.pipeline_id,
        test_type: test.test_type,
        channel: test.channel || 'linkedin',
        action_type: test.action_type || 'first_contact',
        sample_size: test.sample_size || 100,
        variants: test.variants?.length
          ? test.variants.map((v) => ({
              name: v.name,
              description: v.description || '',
              content: v.content || '',
              subject: v.subject || '',
              weight: v.weight,
              is_control: v.is_control
            }))
          : form.value.variants
      }
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }
})

function addVariant() {
  const nextLetter = String.fromCharCode(65 + form.value.variants.length)
  form.value.variants.push({
    name: nextLetter,
    description: '',
    content: '',
    subject: '',
    weight: 0,
    is_control: false
  })
  balanceWeights()
}

function removeVariant(index) {
  if (form.value.variants.length <= 2) return
  form.value.variants.splice(index, 1)
  balanceWeights()
}

function balanceWeights() {
  const count = form.value.variants.length
  const weight = Math.floor(100 / count)
  const remainder = 100 - weight * count

  form.value.variants.forEach((v, i) => {
    v.weight = weight + (i < remainder ? 1 : 0)
  })
}

async function save() {
  saving.value = true
  error.value = null

  try {
    const data = {
      name: form.value.name,
      description: form.value.description || null,
      pipeline_id: form.value.pipeline_id,
      test_type: form.value.test_type,
      channel: form.value.channel,
      action_type: form.value.action_type,
      sample_size: form.value.sample_size,
      variants: form.value.variants.map((v) => ({
        name: v.name,
        description: v.description || null,
        content: v.content || null,
        subject: v.subject || null,
        weight: v.weight,
        is_control: v.is_control
      }))
    }

    if (isEdit.value) {
      await store.editABTest(testId.value, data)
    } else {
      await store.addABTest(data)
    }

    router.push({ name: 'engagement-ab-tests' })
  } catch (err) {
    error.value = err.message
  } finally {
    saving.value = false
  }
}

function cancel() {
  router.push({ name: 'engagement-ab-tests' })
}
</script>

<template>
  <div class="bg-go4-bg dark:bg-gray-900">
    <PageHeader
      :title="isEdit ? 'A/B Test bearbeiten' : 'Neuer A/B Test'"
    >
      <template #actions>
        <button
          type="button"
          class="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
          @click="cancel"
        >
          Abbrechen
        </button>
        <button
          type="button"
          :disabled="saving"
          class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark disabled:opacity-50"
          @click="save"
        >
          {{ saving ? 'Speichern…' : isEdit ? 'Speichern' : 'Erstellen' }}
        </button>
      </template>
    </PageHeader>

    <div class="sm: lg:">
      <div
        v-if="loading"
        class="flex items-center justify-center py-12"
      >
        <span class="text-go4-muted dark:text-gray-400">Laden...</span>
      </div>

      <div
        v-else-if="error"
        class="rounded-lg bg-red-50 p-4 text-red-700 dark:bg-red-900/30 dark:text-red-300"
      >
        {{ error }}
      </div>

      <form
        v-else
        class="space-y-6"
        @submit.prevent="save"
      >
        <!-- Basic Info -->
        <div class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
          <h3 class="mb-4 font-semibold text-go4-secondary dark:text-white">
            Grundeinstellungen
          </h3>

          <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div class="md:col-span-2">
              <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                Name *
              </label>
              <input
                v-model="form.name"
                type="text"
                required
                class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                placeholder="z.B. LinkedIn Erstansprache A/B Test"
              >
            </div>

            <div class="md:col-span-2">
              <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                Beschreibung
              </label>
              <textarea
                v-model="form.description"
                rows="2"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                placeholder="Was wird getestet?"
              />
            </div>

            <div>
              <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                Pipeline *
              </label>
              <select
                v-model="form.pipeline_id"
                required
                class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
                <option :value="null">
                  Pipeline waehlen...
                </option>
                <option
                  v-for="pipeline in store.pipelines"
                  :key="pipeline.id"
                  :value="pipeline.id"
                >
                  {{ pipeline.name }}
                </option>
              </select>
            </div>

            <div>
              <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                Test-Typ *
              </label>
              <select
                v-model="form.test_type"
                required
                class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
                <option
                  v-for="type in testTypes"
                  :key="type.value"
                  :value="type.value"
                >
                  {{ type.label }}
                </option>
              </select>
            </div>

            <div>
              <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                Kanal
              </label>
              <select
                v-model="form.channel"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
                <option
                  v-for="channel in channels"
                  :key="channel.value"
                  :value="channel.value"
                >
                  {{ channel.label }}
                </option>
              </select>
            </div>

            <div>
              <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                Aktionstyp
              </label>
              <select
                v-model="form.action_type"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
                <option
                  v-for="action in actionTypes"
                  :key="action.value"
                  :value="action.value"
                >
                  {{ action.label }}
                </option>
              </select>
            </div>

            <div>
              <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                Ziel-Stichprobe
              </label>
              <input
                v-model.number="form.sample_size"
                type="number"
                min="10"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
            </div>
          </div>
        </div>

        <!-- Variants -->
        <div class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
          <div class="mb-4 flex items-center justify-between">
            <h3 class="font-semibold text-go4-secondary dark:text-white">
              Varianten
            </h3>
            <button
              type="button"
              class="flex items-center gap-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
              @click="addVariant"
            >
              <svg
                class="h-4 w-4"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fill-rule="evenodd"
                  d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
                  clip-rule="evenodd"
                />
              </svg>
              Variante hinzufuegen
            </button>
          </div>

          <div class="space-y-4">
            <div
              v-for="(variant, index) in form.variants"
              :key="index"
              class="rounded-lg border border-gray-100 p-4 dark:border-gray-700"
              :class="variant.is_control ? 'bg-blue-50/50 dark:bg-blue-900/10' : 'bg-gray-50 dark:bg-gray-700/30'"
            >
              <div class="mb-3 flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <span class="font-medium text-go4-secondary dark:text-white">
                    {{ variant.name }}
                  </span>
                  <span
                    v-if="variant.is_control"
                    class="rounded bg-blue-100 px-2 py-0.5 text-xs text-blue-700 dark:bg-blue-900/50 dark:text-blue-300"
                  >
                    Control
                  </span>
                </div>
                <div class="flex items-center gap-3">
                  <div class="flex items-center gap-2">
                    <label class="text-xs text-go4-muted dark:text-gray-400">Gewichtung:</label>
                    <input
                      v-model.number="variant.weight"
                      type="number"
                      min="0"
                      max="100"
                      class="w-16 rounded border border-gray-300 px-2 py-1 text-center text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                    >
                    <span class="text-xs text-go4-muted dark:text-gray-400">%</span>
                  </div>
                  <button
                    v-if="form.variants.length > 2"
                    type="button"
                    class="rounded p-1 text-gray-400 hover:bg-red-100 hover:text-red-600 dark:hover:bg-red-900/30 dark:hover:text-red-400"
                    @click="removeVariant(index)"
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
                        d="M6 18L18 6M6 6l12 12"
                      />
                    </svg>
                  </button>
                </div>
              </div>

              <div class="grid grid-cols-1 gap-3 md:grid-cols-2">
                <div class="md:col-span-2">
                  <label class="mb-1 block text-xs text-go4-muted dark:text-gray-400">
                    Beschreibung
                  </label>
                  <input
                    v-model="variant.description"
                    type="text"
                    class="w-full rounded border border-gray-200 px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                    placeholder="Kurze Beschreibung der Variante"
                  >
                </div>

                <div
                  v-if="form.test_type === 'subject'"
                  class="md:col-span-2"
                >
                  <label class="mb-1 block text-xs text-go4-muted dark:text-gray-400">
                    Betreffzeile
                  </label>
                  <input
                    v-model="variant.subject"
                    type="text"
                    class="w-full rounded border border-gray-200 px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                    placeholder="Betreff der Email"
                  >
                </div>

                <div
                  v-if="form.test_type === 'message'"
                  class="md:col-span-2"
                >
                  <label class="mb-1 block text-xs text-go4-muted dark:text-gray-400">
                    Nachricht
                  </label>
                  <textarea
                    v-model="variant.content"
                    rows="3"
                    class="w-full rounded border border-gray-200 px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                    placeholder="Nachrichteninhalt..."
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

      </form>
    </div>
  </div>
</template>
