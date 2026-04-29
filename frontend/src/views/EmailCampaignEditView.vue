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
const testEmail = ref('')
const showTestModal = ref(false)

const form = ref({
  name: '',
  subject: '',
  html_content:
    '<p>Hallo {{name}},</p>\n\n<p>Hier ist Ihr E-Mail-Inhalt.</p>\n\n<p>Mit freundlichen Grüßen</p>\n\n<p><a href="{{unsubscribe_url}}">Abmelden</a></p>',
  text_content: '',
  provider_id: null,
  template_id: null,
  segment_filters: null,
  contact_ids: null
})

async function loadData() {
  loading.value = true
  await store.fetchProviders()
  await store.fetchTemplates()

  if (!isNew.value) {
    try {
      await store.fetchCampaign(route.params.id)
      if (store.currentCampaign) {
        form.value = {
          name: store.currentCampaign.name,
          subject: store.currentCampaign.subject,
          html_content: store.currentCampaign.html_content,
          text_content: store.currentCampaign.text_content || '',
          provider_id: store.currentCampaign.provider_id,
          template_id: store.currentCampaign.template_id,
          segment_filters: store.currentCampaign.segment_filters,
          contact_ids: store.currentCampaign.contact_ids
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
      const campaign = await store.addCampaign(form.value)
      router.push({ name: 'emailmarketing-campaign-detail', params: { id: campaign.id } })
    } else {
      await store.editCampaign(route.params.id, form.value)
      router.push({ name: 'emailmarketing-campaign-detail', params: { id: route.params.id } })
    }
  } catch (err) {
    // Error handled by store
  } finally {
    saving.value = false
  }
}

async function sendTest() {
  if (!testEmail.value) return
  try {
    await store.sendTestEmail(route.params.id, testEmail.value, { name: 'Test User' })
    showTestModal.value = false
    testEmail.value = ''
    alert('Test-E-Mail gesendet!')
  } catch (err) {
    alert('Fehler beim Senden: ' + store.error)
  }
}

function applyTemplate(templateId) {
  const template = store.templates.find((t) => t.id === templateId)
  if (template) {
    form.value.subject = template.subject
    form.value.html_content = template.html_content
    form.value.text_content = template.text_content || ''
  }
}

onMounted(() => {
  loadData()
})
</script>

<template>
  <div>
    <PageHeader
      :title="isNew ? 'Neue Kampagne' : 'Kampagne bearbeiten'"
    >
      <template #actions>
        <button
          v-if="!isNew"
          class="btn btn-secondary mr-2"
          @click="showTestModal = true"
        >
          Test senden
        </button>
        <button
          :disabled="saving || !form.name || !form.subject"
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
              placeholder="z.B. Newsletter März 2024"
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
        </div>
      </div>

      <!-- Template -->
      <div class="bg-white rounded-lg shadow p-6">
        <h3 class="text-lg font-medium text-gray-900 mb-4">
          Vorlage (optional)
        </h3>
        <select
          class="input"
          @change="applyTemplate($event.target.value)"
        >
          <option value="">
            -- Vorlage wählen --
          </option>
          <option
            v-for="template in store.activeTemplates"
            :key="template.id"
            :value="template.id"
          >
            {{ template.name }}
          </option>
        </select>
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
              placeholder="Betreffzeile der E-Mail"
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

      <!-- Segment Filters -->
      <div class="bg-white rounded-lg shadow p-6">
        <h3 class="text-lg font-medium text-gray-900 mb-4">
          Empfänger
        </h3>
        <p class="text-gray-500 text-sm mb-4">
          Empfänger werden beim Senden aus den Contacts generiert. Filter können in der
          Detail-Ansicht konfiguriert werden.
        </p>
      </div>
    </form>

    <!-- Test Modal -->
    <div
      v-if="showTestModal"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click.self="showTestModal = false"
    >
      <div class="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
        <h3 class="text-lg font-medium text-gray-900 mb-4">
          Test-E-Mail senden
        </h3>
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-1">E-Mail-Adresse</label>
          <input
            v-model="testEmail"
            type="email"
            class="input"
            placeholder="test@example.com"
          >
        </div>
        <div class="flex justify-end space-x-2">
          <button
            class="btn btn-secondary"
            @click="showTestModal = false"
          >
            Abbrechen
          </button>
          <button
            :disabled="!testEmail"
            class="btn btn-primary"
            @click="sendTest"
          >
            Senden
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
