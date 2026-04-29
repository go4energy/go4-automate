<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useLinkedInStore } from '@/stores/linkedin'
import PageHeader from '@/components/ui/PageHeader.vue'

const router = useRouter()
const route = useRoute()
const store = useLinkedInStore()

const props = defineProps({
  id: { type: [String, Number], default: null }
})

const isEdit = computed(() => !!props.id)

const form = ref({
  name: '',
  type: 'message',
  content: '',
  subject: ''
})

const saving = ref(false)
const error = ref(null)

const templateTypes = [
  { value: 'connection_note', label: 'Kontaktanfrage-Notiz', maxLength: 300 },
  { value: 'message', label: 'Direktnachricht', maxLength: 8000 },
  { value: 'follow_up', label: 'Follow-up Nachricht', maxLength: 8000 },
  { value: 'inmail', label: 'InMail', maxLength: 1900 }
]

const currentTypeConfig = computed(() => {
  return templateTypes.find((t) => t.value === form.value.type) || templateTypes[1]
})

const availableVariables = [
  { key: '{first_name}', label: 'Vorname' },
  { key: '{last_name}', label: 'Nachname' },
  { key: '{full_name}', label: 'Vollstaendiger Name' },
  { key: '{company}', label: 'Unternehmen' },
  { key: '{position}', label: 'Position' },
  { key: '{industry}', label: 'Branche' },
  { key: '{location}', label: 'Standort' },
  { key: '{headline}', label: 'Headline' }
]

const previewContent = computed(() => {
  let content = form.value.content
  const sampleData = {
    '{first_name}': 'Max',
    '{last_name}': 'Mustermann',
    '{full_name}': 'Max Mustermann',
    '{company}': 'Muster GmbH',
    '{position}': 'CEO',
    '{industry}': 'Software',
    '{location}': 'Berlin',
    '{headline}': 'CEO at Muster GmbH'
  }
  for (const [key, value] of Object.entries(sampleData)) {
    content = content.replace(new RegExp(key.replace(/[{}]/g, '\\$&'), 'g'), value)
  }
  return content
})

const characterCount = computed(() => form.value.content.length)

const isOverLimit = computed(() => characterCount.value > currentTypeConfig.value.maxLength)

onMounted(async () => {
  if (isEdit.value) {
    try {
      const template = await store.fetchTemplate(props.id)
      form.value = {
        name: template.name,
        type: template.type,
        content: template.content,
        subject: template.subject || ''
      }
    } catch {
      error.value = 'Vorlage konnte nicht geladen werden'
    }
  }
})

function insertVariable(variable) {
  const textarea = document.getElementById('content-textarea')
  if (textarea) {
    const start = textarea.selectionStart
    const end = textarea.selectionEnd
    const text = form.value.content
    form.value.content = text.substring(0, start) + variable + text.substring(end)
    // Set cursor position after inserted variable
    setTimeout(() => {
      textarea.selectionStart = textarea.selectionEnd = start + variable.length
      textarea.focus()
    }, 0)
  } else {
    form.value.content += variable
  }
}

async function save() {
  if (!form.value.name || !form.value.content) {
    error.value = 'Name und Inhalt sind erforderlich'
    return
  }

  if (isOverLimit.value) {
    error.value = `Der Inhalt ueberschreitet das Limit von ${currentTypeConfig.value.maxLength} Zeichen`
    return
  }

  saving.value = true
  error.value = null

  try {
    const data = {
      name: form.value.name,
      type: form.value.type,
      content: form.value.content
    }
    if (form.value.type === 'inmail' && form.value.subject) {
      data.subject = form.value.subject
    }

    if (isEdit.value) {
      await store.editTemplate(props.id, data)
    } else {
      await store.addTemplate(data)
    }
    router.push('/linkedin/templates')
  } catch (err) {
    error.value = err.response?.data?.detail || err.message
  } finally {
    saving.value = false
  }
}

function cancel() {
  router.push('/linkedin/templates')
}
</script>

<template>
  <div class="bg-go4-bg dark:bg-gray-900">
    <PageHeader
      :title="isEdit ? 'Vorlage bearbeiten' : 'Neue Vorlage'"
    />

    <div class="sm: lg:">
      <div
        v-if="error"
        class="mb-6 rounded-lg bg-red-50 p-4 text-red-700 dark:bg-red-900/30 dark:text-red-300"
      >
        {{ error }}
      </div>

      <div class="grid gap-6 lg:grid-cols-2">
        <!-- Form -->
        <div class="space-y-6">
          <div
            class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800"
          >
            <h2 class="mb-4 text-lg font-medium text-go4-secondary dark:text-white">
              Vorlage
            </h2>

            <div class="space-y-4">
              <div>
                <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-300">
                  Name *
                </label>
                <input
                  v-model="form.name"
                  type="text"
                  class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                  placeholder="z.B. Erstkontakt Sales"
                >
              </div>

              <div>
                <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-300">
                  Typ *
                </label>
                <select
                  v-model="form.type"
                  class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                >
                  <option
                    v-for="type in templateTypes"
                    :key="type.value"
                    :value="type.value"
                  >
                    {{ type.label }} (max. {{ type.maxLength }} Zeichen)
                  </option>
                </select>
              </div>

              <div v-if="form.type === 'inmail'">
                <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-300">
                  Betreff
                </label>
                <input
                  v-model="form.subject"
                  type="text"
                  class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                  placeholder="Betreff der InMail"
                >
              </div>

              <div>
                <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-300">
                  Inhalt *
                </label>
                <textarea
                  id="content-textarea"
                  v-model="form.content"
                  rows="10"
                  class="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                  :class="{ 'border-red-500': isOverLimit }"
                  placeholder="Hallo {first_name},&#10;&#10;ich habe gesehen, dass du bei {company} als {position} arbeitest..."
                />
                <div class="mt-1 flex items-center justify-between text-xs">
                  <span :class="isOverLimit ? 'text-red-500' : 'text-go4-muted'">
                    {{ characterCount }} / {{ currentTypeConfig.maxLength }} Zeichen
                  </span>
                </div>
              </div>

              <!-- Variables -->
              <div>
                <label class="mb-2 block text-sm font-medium text-go4-secondary dark:text-gray-300">
                  Variablen einfuegen
                </label>
                <div class="flex flex-wrap gap-2">
                  <button
                    v-for="variable in availableVariables"
                    :key="variable.key"
                    type="button"
                    class="rounded-full bg-gray-100 px-3 py-1 text-xs text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
                    @click="insertVariable(variable.key)"
                  >
                    {{ variable.key }}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex gap-3">
            <button
              class="flex-1 rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark disabled:opacity-50"
              :disabled="saving || isOverLimit"
              @click="save"
            >
              {{ saving ? 'Speichern...' : isEdit ? 'Aktualisieren' : 'Erstellen' }}
            </button>
            <button
              class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
              @click="cancel"
            >
              Abbrechen
            </button>
          </div>
        </div>

        <!-- Preview -->
        <div
          class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800"
        >
          <h2 class="mb-4 text-lg font-medium text-go4-secondary dark:text-white">
            Vorschau
          </h2>
          <p class="mb-4 text-xs text-go4-muted">
            So sieht die Nachricht mit Beispieldaten aus:
          </p>

          <div class="rounded-lg bg-gray-50 p-4 dark:bg-gray-700">
            <div
              v-if="form.type === 'inmail' && form.subject"
              class="mb-3 border-b border-gray-200 pb-2 dark:border-gray-600"
            >
              <span class="text-xs text-go4-muted">Betreff:</span>
              <p class="font-medium text-go4-secondary dark:text-white">
                {{ form.subject }}
              </p>
            </div>
            <pre
              class="whitespace-pre-wrap font-sans text-sm text-go4-secondary dark:text-gray-200"
            >{{ previewContent || 'Gib oben einen Text ein...' }}</pre>
          </div>

          <div
            class="mt-4 rounded-lg border border-blue-100 bg-blue-50 p-3 dark:border-blue-900 dark:bg-blue-900/20"
          >
            <h3 class="mb-2 text-sm font-medium text-blue-800 dark:text-blue-300">
              Tipps fuer bessere Antworten
            </h3>
            <ul class="space-y-1 text-xs text-blue-700 dark:text-blue-400">
              <li>- Personalisiere mit dem Vornamen</li>
              <li>- Erwaehne das Unternehmen oder die Position</li>
              <li>- Halte dich kurz und praegnant</li>
              <li>- Stelle eine klare Frage oder CTA</li>
              <li>- Vermeide zu werbliche Sprache</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
