<script setup>
import { ref, watch, computed } from 'vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  deal: { type: Object, default: null },
  pipeline: { type: Object, default: null },
  defaultStageId: { type: Number, default: null },
  contacts: { type: Array, default: () => [] },
  companies: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false }
})

const emit = defineEmits(['close', 'save'])

const form = ref({
  title: '',
  pipeline_id: null,
  stage_id: null,
  contact_id: null,
  company_id: null,
  value: null,
  currency: 'EUR',
  expected_close: '',
  priority: 'medium',
  description: '',
  tags: []
})

const tagInput = ref('')

const isEdit = computed(() => !!props.deal)
const title = computed(() => (isEdit.value ? 'Deal bearbeiten' : 'Neuer Deal'))

watch(
  () => props.open,
  (open) => {
    if (open) {
      if (props.deal) {
        form.value = {
          title: props.deal.title || '',
          pipeline_id: props.deal.pipeline_id,
          stage_id: props.deal.stage_id,
          contact_id: props.deal.contact_id || null,
          company_id: props.deal.company_id || null,
          value: props.deal.value || null,
          currency: props.deal.currency || 'EUR',
          expected_close: props.deal.expected_close || '',
          priority: props.deal.priority || 'medium',
          description: props.deal.description || '',
          tags: [...(props.deal.tags || [])]
        }
      } else {
        form.value = {
          title: '',
          pipeline_id: props.pipeline?.id || null,
          stage_id: props.defaultStageId || props.pipeline?.stages?.[0]?.id || null,
          contact_id: null,
          company_id: null,
          value: null,
          currency: 'EUR',
          expected_close: '',
          priority: 'medium',
          description: '',
          tags: []
        }
      }
      tagInput.value = ''
    }
  }
)

function addTag() {
  const tag = tagInput.value.trim()
  if (tag && !form.value.tags.includes(tag)) {
    form.value.tags.push(tag)
  }
  tagInput.value = ''
}

function removeTag(tag) {
  form.value.tags = form.value.tags.filter((t) => t !== tag)
}

function onSubmit() {
  const data = { ...form.value }
  if (data.value) {
    data.value = parseFloat(data.value)
  }
  emit('save', data)
}

function onClose() {
  emit('close')
}
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="duration-200 ease-out"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="duration-150 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="open"
        class="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 p-4 pt-16"
        @click.self="onClose"
      >
        <div
          class="w-full max-w-lg transform rounded-lg bg-white dark:bg-gray-800 shadow-xl transition-all"
        >
          <!-- Header -->
          <div
            class="flex items-center justify-between border-b border-gray-200 dark:border-gray-700 px-6 py-4"
          >
            <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
              {{ title }}
            </h2>
            <button
              type="button"
              class="rounded-lg p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              @click="onClose"
            >
              <svg
                class="h-5 w-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
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

          <!-- Form -->
          <form
            class="p-6 space-y-4"
            @submit.prevent="onSubmit"
          >
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Titel *
              </label>
              <input
                v-model="form.title"
                type="text"
                required
                placeholder="z.B. Website Redesign Projekt"
                class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
              >
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Stage
                </label>
                <select
                  v-model="form.stage_id"
                  required
                  class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
                >
                  <option
                    v-for="stage in pipeline?.stages"
                    :key="stage.id"
                    :value="stage.id"
                  >
                    {{ stage.name }}
                  </option>
                </select>
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Priorität
                </label>
                <select
                  v-model="form.priority"
                  class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
                >
                  <option value="low">
                    Niedrig
                  </option>
                  <option value="medium">
                    Normal
                  </option>
                  <option value="high">
                    Hoch
                  </option>
                </select>
              </div>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Wert
                </label>
                <input
                  v-model="form.value"
                  type="number"
                  min="0"
                  step="0.01"
                  placeholder="0.00"
                  class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
                >
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Abschluss erwartet
                </label>
                <input
                  v-model="form.expected_close"
                  type="date"
                  class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
                >
              </div>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Kontakt
                </label>
                <select
                  v-model="form.contact_id"
                  class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
                >
                  <option :value="null">
                    Kein Kontakt
                  </option>
                  <option
                    v-for="contact in contacts"
                    :key="contact.id"
                    :value="contact.id"
                  >
                    {{ contact.name }}
                  </option>
                </select>
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Firma
                </label>
                <select
                  v-model="form.company_id"
                  class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
                >
                  <option :value="null">
                    Keine Firma
                  </option>
                  <option
                    v-for="company in companies"
                    :key="company.id"
                    :value="company.id"
                  >
                    {{ company.name }}
                  </option>
                </select>
              </div>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Tags
              </label>
              <div class="flex flex-wrap gap-1 mb-2">
                <span
                  v-for="tag in form.tags"
                  :key="tag"
                  class="inline-flex items-center gap-1 rounded-full bg-go4-primary/10 px-2 py-0.5 text-xs text-go4-primary"
                >
                  {{ tag }}
                  <button
                    type="button"
                    class="hover:text-go4-primary-dark"
                    @click="removeTag(tag)"
                  >
                    <svg
                      class="h-3 w-3"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M6 18L18 6M6 6l12 12"
                      />
                    </svg>
                  </button>
                </span>
              </div>
              <div class="flex gap-2">
                <input
                  v-model="tagInput"
                  type="text"
                  placeholder="Tag hinzufügen..."
                  class="flex-1 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
                  @keydown.enter.prevent="addTag"
                >
                <button
                  type="button"
                  class="rounded-lg bg-gray-100 dark:bg-gray-700 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
                  @click="addTag"
                >
                  +
                </button>
              </div>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Beschreibung
              </label>
              <textarea
                v-model="form.description"
                rows="3"
                class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
              />
            </div>

            <!-- Actions -->
            <div class="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
              <button
                type="button"
                :disabled="loading"
                class="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50"
                @click="onClose"
              >
                Abbrechen
              </button>
              <button
                type="submit"
                :disabled="loading"
                class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark disabled:opacity-50"
              >
                <span v-if="loading">Speichern...</span>
                <span v-else>{{ isEdit ? 'Speichern' : 'Erstellen' }}</span>
              </button>
            </div>
          </form>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
