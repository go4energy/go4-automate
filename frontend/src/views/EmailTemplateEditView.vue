<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useEmailMarketingStore } from '@/stores/emailmarketing'
import { previewTemplate } from '@/api/emailmarketing'
import PageHeader from '@/components/ui/PageHeader.vue'

const route = useRoute()
const router = useRouter()
const store = useEmailMarketingStore()

const isNew = computed(() => !route.params.id)
const loading = ref(true)
const saving = ref(false)
const previewHtml = ref('')
const showPreview = ref(false)

const form = ref({
  name: '',
  slug: '',
  description: '',
  subject: '',
  html_content:
    '<p>Hallo {{name}},</p>\n\n<p>Hier ist Ihr E-Mail-Inhalt.</p>\n\n<p>Mit freundlichen Grüßen</p>\n\n<p><a href="{{unsubscribe_url}}">Abmelden</a></p>',
  text_content: '',
  variables: ['name', 'email', 'unsubscribe_url'],
  category: '',
  tags: [],
  is_active: true
})

function generateSlug(name) {
  return name
    .toLowerCase()
    .replace(/[äöüß]/g, (c) => ({ ä: 'ae', ö: 'oe', ü: 'ue', ß: 'ss' })[c])
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
}

async function loadData() {
  loading.value = true
  if (!isNew.value) {
    try {
      await store.fetchTemplate(route.params.id)
      if (store.currentTemplate) {
        form.value = {
          name: store.currentTemplate.name,
          slug: store.currentTemplate.slug,
          description: store.currentTemplate.description || '',
          subject: store.currentTemplate.subject,
          html_content: store.currentTemplate.html_content,
          text_content: store.currentTemplate.text_content || '',
          variables: store.currentTemplate.variables || [],
          category: store.currentTemplate.category || '',
          tags: store.currentTemplate.tags || [],
          is_active: store.currentTemplate.is_active
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
      await store.addTemplate(form.value)
    } else {
      await store.editTemplate(route.params.id, form.value)
    }
    router.push({ name: 'emailmarketing' })
  } catch (err) {
    // Error handled by store
  } finally {
    saving.value = false
  }
}

async function preview() {
  try {
    const { data } = await previewTemplate({
      html_content: form.value.html_content,
      merge_data: { name: 'Max Mustermann', email: 'max@example.com', unsubscribe_url: '#' }
    })
    previewHtml.value = data.html
    showPreview.value = true
  } catch (err) {
    alert('Vorschau-Fehler')
  }
}

onMounted(() => {
  loadData()
})
</script>

<template>
  <div class="p-6">
    <PageHeader
      :title="isNew ? 'Neue Vorlage' : 'Vorlage bearbeiten'"
    >
      <template #actions>
        <button
          class="btn btn-secondary mr-2"
          @click="preview"
        >
          Vorschau
        </button>
        <button
          :disabled="saving || !form.name || !form.slug || !form.subject"
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

    <form
      v-else
      class="space-y-6"
      @submit.prevent="save"
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
              placeholder="z.B. Welcome Email"
              @input="isNew && (form.slug = generateSlug(form.name))"
            >
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Slug *</label>
            <input
              v-model="form.slug"
              type="text"
              required
              :disabled="!isNew"
              class="input"
              placeholder="z.B. welcome-email"
            >
          </div>
          <div class="md:col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Beschreibung</label>
            <input
              v-model="form.description"
              type="text"
              class="input"
              placeholder="Kurze Beschreibung..."
            >
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Kategorie</label>
            <input
              v-model="form.category"
              type="text"
              class="input"
              placeholder="z.B. onboarding"
            >
          </div>
          <div class="flex items-center">
            <input
              id="is_active"
              v-model="form.is_active"
              type="checkbox"
              class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
            >
            <label
              for="is_active"
              class="ml-2 block text-sm text-gray-900"
            >Aktiv</label>
          </div>
        </div>
      </div>

      <!-- Content -->
      <div class="bg-white rounded-lg shadow p-6">
        <h3 class="text-lg font-medium text-gray-900 mb-4">
          E-Mail-Inhalt
        </h3>
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Betreff *</label>
            <input
              v-model="form.subject"
              type="text"
              required
              class="input"
              placeholder="Betreffzeile"
            >
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">HTML-Inhalt *</label>
            <textarea
              v-model="form.html_content"
              rows="15"
              required
              class="input font-mono text-sm"
              placeholder="HTML-E-Mail-Inhalt..."
            />
            <p class="text-xs text-gray-500 mt-1">
              Merge-Tags:
              <code class="bg-gray-100 px-1 rounded">&#123;&#123;name&#125;&#125;</code>,
              <code class="bg-gray-100 px-1 rounded">&#123;&#123;email&#125;&#125;</code>,
              <code class="bg-gray-100 px-1 rounded">&#123;&#123;company&#125;&#125;</code>,
              <code class="bg-gray-100 px-1 rounded">&#123;&#123;unsubscribe_url&#125;&#125;</code>
            </p>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Plain-Text (optional)</label>
            <textarea
              v-model="form.text_content"
              rows="5"
              class="input font-mono text-sm"
              placeholder="Nur-Text-Version..."
            />
          </div>
        </div>
      </div>
    </form>

    <!-- Preview Modal -->
    <div
      v-if="showPreview"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click.self="showPreview = false"
    >
      <div class="bg-white rounded-lg shadow-xl p-6 w-full max-w-3xl max-h-[80vh] overflow-auto">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-medium text-gray-900">
            Vorschau
          </h3>
          <button
            class="text-gray-400 hover:text-gray-600"
            @click="showPreview = false"
          >
            <svg
              class="w-6 h-6"
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
        <div class="border rounded-lg p-4 bg-gray-50">
          <div
            class="prose max-w-none"
            v-html="previewHtml"
          />
        </div>
      </div>
    </div>
  </div>
</template>
