<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useLetterStore } from '@/stores/letter'
import PageHeader from '@/components/ui/PageHeader.vue'

const props = defineProps({
  id: {
    type: [String, Number],
    default: null,
  },
})

const route = useRoute()
const router = useRouter()
const store = useLetterStore()

const templateId = computed(() => props.id || route.params.id)
const isNew = computed(() => !templateId.value || templateId.value === 'new')

const loading = ref(false)
const saving = ref(false)
const error = ref(null)

const form = ref({
  name: '',
  description: '',
  format: 'a4',
  content_html: '<p>Sehr geehrte/r {{contact.name}},</p>\n\n<p></p>\n\n<p>Mit freundlichen Grüßen</p>',
  header_html: '',
  footer_html: '',
  is_active: true,
})

// Preview
const showPreview = ref(false)
const previewHtml = ref('')

// Placeholder helpers
const placeholders = [
  { label: 'Name', value: '{{contact.name}}' },
  { label: 'Vorname', value: '{{contact.first_name}}' },
  { label: 'Nachname', value: '{{contact.last_name}}' },
  { label: 'Firma', value: '{{contact.company}}' },
  { label: 'Position', value: '{{contact.position}}' },
  { label: 'Datum', value: '{{date}}' },
]

async function loadTemplate() {
  if (isNew.value) return

  loading.value = true
  error.value = null
  try {
    const template = await store.fetchTemplate(templateId.value)
    form.value = {
      name: template.name,
      description: template.description || '',
      format: template.format,
      content_html: template.content_html,
      header_html: template.header_html || '',
      footer_html: template.footer_html || '',
      is_active: template.is_active,
    }
  } catch (err) {
    error.value = err.response?.data?.detail || err.message
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  error.value = null
  try {
    if (isNew.value) {
      await store.createTemplate(form.value)
    } else {
      await store.updateTemplate(templateId.value, form.value)
    }
    router.push('/letter/templates')
  } catch (err) {
    error.value = err.response?.data?.detail || err.message
  } finally {
    saving.value = false
  }
}

function cancel() {
  router.push('/letter/templates')
}

function insertPlaceholder(placeholder) {
  // Insert at cursor position in content_html textarea
  const textarea = document.getElementById('content-editor')
  if (textarea) {
    const start = textarea.selectionStart
    const end = textarea.selectionEnd
    const text = form.value.content_html
    form.value.content_html =
      text.substring(0, start) + placeholder + text.substring(end)
    // Reset cursor position
    setTimeout(() => {
      textarea.focus()
      textarea.setSelectionRange(
        start + placeholder.length,
        start + placeholder.length
      )
    }, 0)
  }
}

async function generatePreview() {
  if (!templateId.value || isNew.value) {
    // For new templates, just show the raw HTML
    previewHtml.value = form.value.content_html
    showPreview.value = true
    return
  }

  try {
    // Save first to have current content
    await store.updateTemplate(templateId.value, form.value)
    const result = await store.previewTemplate({ template_id: parseInt(templateId.value) })
    previewHtml.value = result.html
    showPreview.value = true
  } catch (err) {
    error.value = err.response?.data?.detail || err.message
  }
}

onMounted(() => {
  loadTemplate()
})
</script>

<template>
  <div class="space-y-6">
    <PageHeader
      :title="isNew ? 'Neues Template' : 'Template bearbeiten'"
    >
      <template #actions>
        <button
          class="btn btn-secondary"
          @click="generatePreview"
        >
          Vorschau
        </button>
      </template>
    </PageHeader>

    <div
      v-if="loading"
      class="py-8 text-center text-gray-500"
    >
      Laden...
    </div>

    <div
      v-else-if="error"
      class="rounded-lg bg-red-50 p-4 text-red-700"
    >
      {{ error }}
    </div>

    <div
      v-else
      class="grid gap-6 lg:grid-cols-3"
    >
      <!-- Main Form -->
      <div class="lg:col-span-2">
        <form
          class="space-y-6"
          @submit.prevent="save"
        >
          <!-- Basic Info -->
          <div class="rounded-lg bg-white p-6 shadow-sm">
            <h3 class="mb-4 font-medium text-gray-900">
              Grundinformationen
            </h3>
            <div class="grid gap-4 sm:grid-cols-2">
              <div>
                <label class="block text-sm font-medium text-gray-700">Name</label>
                <input
                  v-model="form.name"
                  type="text"
                  class="input mt-1 w-full"
                  placeholder="z.B. Erstkontakt Solar"
                  required
                >
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700">Format</label>
                <select
                  v-model="form.format"
                  class="input mt-1 w-full"
                >
                  <option value="a4">
                    A4
                  </option>
                  <option value="us_letter">
                    US Letter
                  </option>
                  <option value="din_lang">
                    DIN Lang
                  </option>
                </select>
              </div>
              <div class="sm:col-span-2">
                <label class="block text-sm font-medium text-gray-700">Beschreibung</label>
                <input
                  v-model="form.description"
                  type="text"
                  class="input mt-1 w-full"
                  placeholder="Kurze Beschreibung des Templates"
                >
              </div>
              <div class="flex items-center gap-2">
                <input
                  id="is-active"
                  v-model="form.is_active"
                  type="checkbox"
                  class="h-4 w-4 rounded border-gray-300"
                >
                <label
                  for="is-active"
                  class="text-sm text-gray-700"
                >
                  Template ist aktiv
                </label>
              </div>
            </div>
          </div>

          <!-- Header -->
          <div class="rounded-lg bg-white p-6 shadow-sm">
            <h3 class="mb-4 font-medium text-gray-900">
              Briefkopf (optional)
            </h3>
            <textarea
              v-model="form.header_html"
              rows="4"
              class="input w-full font-mono text-sm"
              placeholder="<div>Firmenlogo und Adresse...</div>"
            />
          </div>

          <!-- Content -->
          <div class="rounded-lg bg-white p-6 shadow-sm">
            <div class="mb-4 flex items-center justify-between">
              <h3 class="font-medium text-gray-900">
                Briefinhalt
              </h3>
              <div class="flex flex-wrap gap-2">
                <button
                  v-for="p in placeholders"
                  :key="p.value"
                  type="button"
                  class="rounded bg-gray-100 px-2 py-1 text-xs text-gray-600 hover:bg-gray-200"
                  @click="insertPlaceholder(p.value)"
                >
                  {{ p.label }}
                </button>
              </div>
            </div>
            <textarea
              id="content-editor"
              v-model="form.content_html"
              rows="15"
              class="input w-full font-mono text-sm"
              required
            />
          </div>

          <!-- Footer -->
          <div class="rounded-lg bg-white p-6 shadow-sm">
            <h3 class="mb-4 font-medium text-gray-900">
              Fußzeile (optional)
            </h3>
            <textarea
              v-model="form.footer_html"
              rows="4"
              class="input w-full font-mono text-sm"
              placeholder="<div>Kontaktinformationen, Bankverbindung...</div>"
            />
          </div>

          <!-- Actions -->
          <div class="flex justify-end gap-3">
            <button
              type="button"
              class="btn btn-secondary"
              @click="cancel"
            >
              Abbrechen
            </button>
            <button
              type="submit"
              class="btn btn-primary"
              :disabled="saving"
            >
              {{ saving ? 'Speichern...' : 'Speichern' }}
            </button>
          </div>
        </form>
      </div>

      <!-- Sidebar -->
      <div class="space-y-6">
        <!-- Placeholder Reference -->
        <div class="rounded-lg bg-white p-6 shadow-sm">
          <h3 class="mb-4 font-medium text-gray-900">
            Verfügbare Platzhalter
          </h3>
          <div class="space-y-2 text-sm">
            <div
              v-for="p in placeholders"
              :key="p.value"
              class="flex items-center justify-between rounded bg-gray-50 px-3 py-2"
            >
              <span class="text-gray-600">{{ p.label }}</span>
              <code class="text-xs text-gray-500">{{ p.value }}</code>
            </div>
          </div>
        </div>

        <!-- Tips -->
        <div class="rounded-lg bg-blue-50 p-6">
          <h3 class="mb-2 font-medium text-blue-900">
            Tipps
          </h3>
          <ul class="space-y-2 text-sm text-blue-700">
            <li>Verwenden Sie HTML-Tags für die Formatierung</li>
            <li>Platzhalter werden beim Versand durch echte Daten ersetzt</li>
            <li>Der Briefkopf erscheint auf jeder Seite oben</li>
            <li>Die Fußzeile erscheint auf jeder Seite unten</li>
          </ul>
        </div>
      </div>
    </div>

    <!-- Preview Modal -->
    <div
      v-if="showPreview"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      @click.self="showPreview = false"
    >
      <div class="h-[85vh] w-full max-w-4xl overflow-auto rounded-lg bg-white shadow-xl">
        <div class="sticky top-0 z-10 flex items-center justify-between border-b bg-white px-6 py-4">
          <h2 class="text-lg font-semibold">
            Vorschau
          </h2>
          <button
            class="text-gray-400 hover:text-gray-600"
            @click="showPreview = false"
          >
            <svg
              class="h-6 w-6"
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
        <div class="p-8">
          <!-- Paper simulation -->
          <div
            class="mx-auto bg-white shadow-lg"
            :class="{
              'max-w-[210mm] min-h-[297mm]': form.format === 'a4',
              'max-w-[8.5in] min-h-[11in]': form.format === 'us_letter',
              'max-w-[220mm] min-h-[110mm]': form.format === 'din_lang',
            }"
            style="padding: 2cm; border: 1px solid #e5e7eb;"
          >
            <!-- Header -->
            <div
              v-if="form.header_html"
              class="mb-8"
              v-html="form.header_html"
            />

            <!-- Content -->
            <div
              class="prose max-w-none"
              v-html="previewHtml"
            />

            <!-- Footer -->
            <div
              v-if="form.footer_html"
              class="mt-auto pt-8 text-sm text-gray-500"
              v-html="form.footer_html"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
