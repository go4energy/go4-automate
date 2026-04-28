<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useLetterStore } from '@/stores/letter'
import PageHeader from '@/components/ui/PageHeader.vue'
import Breadcrumb from '@/components/ui/Breadcrumb.vue'

const props = defineProps({
  id: {
    type: [String, Number],
    required: true,
  },
})

const route = useRoute()
const router = useRouter()
const store = useLetterStore()

const letterId = computed(() => props.id || route.params.id)

const loading = ref(false)
const error = ref(null)

const letter = computed(() => store.currentLetter)

// Status badge colors
const statusColors = {
  draft: 'bg-gray-100 text-gray-800',
  approved: 'bg-blue-100 text-blue-800',
  queued: 'bg-yellow-100 text-yellow-800',
  sent: 'bg-green-100 text-green-800',
  delivered: 'bg-green-200 text-green-900',
  returned: 'bg-red-100 text-red-800',
}

const statusLabels = {
  draft: 'Entwurf',
  approved: 'Genehmigt',
  queued: 'In Warteschlange',
  sent: 'Versendet',
  delivered: 'Zugestellt',
  returned: 'Rückläufer',
}

async function loadLetter() {
  loading.value = true
  error.value = null
  try {
    await store.fetchLetter(letterId.value)
  } catch (err) {
    error.value = err.response?.data?.detail || err.message
  } finally {
    loading.value = false
  }
}

async function approveLetter() {
  try {
    await store.approveLetter(letterId.value)
  } catch (err) {
    error.value = err.response?.data?.detail || err.message
  }
}

async function generatePdf() {
  try {
    await store.generateLetterPdf(letterId.value)
  } catch (err) {
    error.value = err.response?.data?.detail || err.message
  }
}

async function deleteLetter() {
  if (!confirm('Brief wirklich löschen?')) return
  try {
    await store.deleteLetter(letterId.value)
    router.push('/letter')
  } catch (err) {
    error.value = err.response?.data?.detail || err.message
  }
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function goBack() {
  router.push('/letter')
}

onMounted(() => {
  loadLetter()
})
</script>

<template>
  <div class="space-y-6">
    <Breadcrumb class="mb-4" />

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
      <button
        class="ml-4 underline"
        @click="goBack"
      >
        Zurück
      </button>
    </div>

    <template v-else-if="letter">
      <PageHeader
        :title="letter.recipient_name"
        :description="letter.recipient_company || 'Brief-Details'"
      >
        <template #actions>
          <button
            v-if="letter.status === 'draft'"
            class="btn btn-primary"
            @click="approveLetter"
          >
            Genehmigen
          </button>
          <button
            v-if="letter.status === 'approved' && !letter.pdf_path"
            class="btn btn-secondary"
            @click="generatePdf"
          >
            PDF generieren
          </button>
          <a
            v-if="letter.pdf_path"
            :href="`/uploads/${letter.pdf_path}`"
            target="_blank"
            class="btn btn-secondary"
          >
            PDF ansehen
          </a>
          <button
            v-if="letter.status === 'draft'"
            class="btn btn-danger"
            @click="deleteLetter"
          >
            Löschen
          </button>
        </template>
      </PageHeader>

      <div class="grid gap-6 lg:grid-cols-3">
        <!-- Main Content -->
        <div class="lg:col-span-2 space-y-6">
          <!-- Letter Preview -->
          <div class="rounded-lg bg-white p-6 shadow-sm">
            <h3 class="mb-4 font-medium text-gray-900">
              Briefinhalt
            </h3>
            <div
              class="prose max-w-none rounded border border-gray-200 bg-gray-50 p-6"
              v-html="letter.content_html || '<em class=&quot;text-gray-400&quot;>Kein Inhalt</em>'"
            />
          </div>

          <!-- Recipient Details -->
          <div class="rounded-lg bg-white p-6 shadow-sm">
            <h3 class="mb-4 font-medium text-gray-900">
              Empfänger
            </h3>
            <div class="grid gap-4 sm:grid-cols-2">
              <div>
                <label class="block text-sm text-gray-500">Name</label>
                <div class="font-medium">
                  {{ letter.recipient_name }}
                </div>
              </div>
              <div>
                <label class="block text-sm text-gray-500">Firma</label>
                <div class="font-medium">
                  {{ letter.recipient_company || '-' }}
                </div>
              </div>
              <div>
                <label class="block text-sm text-gray-500">Straße</label>
                <div class="font-medium">
                  {{ letter.recipient_street || '-' }}
                </div>
              </div>
              <div>
                <label class="block text-sm text-gray-500">PLZ / Stadt</label>
                <div class="font-medium">
                  {{ letter.recipient_zip || '' }} {{ letter.recipient_city || '-' }}
                </div>
              </div>
              <div>
                <label class="block text-sm text-gray-500">Land</label>
                <div class="font-medium">
                  {{ letter.recipient_country }}
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Sidebar -->
        <div class="space-y-6">
          <!-- Status Card -->
          <div class="rounded-lg bg-white p-6 shadow-sm">
            <h3 class="mb-4 font-medium text-gray-900">
              Status
            </h3>
            <div class="space-y-4">
              <div>
                <span
                  class="inline-flex rounded-full px-3 py-1 text-sm font-medium"
                  :class="statusColors[letter.status]"
                >
                  {{ statusLabels[letter.status] || letter.status }}
                </span>
              </div>

              <div v-if="letter.batch_id">
                <label class="block text-sm text-gray-500">Batch</label>
                <div class="font-medium">
                  #{{ letter.batch_id }}
                </div>
              </div>

              <div>
                <label class="block text-sm text-gray-500">Erstellt</label>
                <div class="font-medium">
                  {{ formatDate(letter.created_at) }}
                </div>
              </div>

              <div v-if="letter.queued_at">
                <label class="block text-sm text-gray-500">In Warteschlange</label>
                <div class="font-medium">
                  {{ formatDate(letter.queued_at) }}
                </div>
              </div>

              <div v-if="letter.sent_at">
                <label class="block text-sm text-gray-500">Versendet</label>
                <div class="font-medium">
                  {{ formatDate(letter.sent_at) }}
                </div>
              </div>

              <div v-if="letter.delivered_at">
                <label class="block text-sm text-gray-500">Zugestellt</label>
                <div class="font-medium">
                  {{ formatDate(letter.delivered_at) }}
                </div>
              </div>

              <div v-if="letter.returned_at">
                <label class="block text-sm text-gray-500">Rückläufer</label>
                <div class="font-medium text-red-600">
                  {{ formatDate(letter.returned_at) }}
                </div>
                <div
                  v-if="letter.return_reason"
                  class="mt-1 text-sm text-gray-500"
                >
                  Grund: {{ letter.return_reason }}
                </div>
              </div>
            </div>
          </div>

          <!-- References Card -->
          <div class="rounded-lg bg-white p-6 shadow-sm">
            <h3 class="mb-4 font-medium text-gray-900">
              Verknüpfungen
            </h3>
            <div class="space-y-3">
              <div>
                <label class="block text-sm text-gray-500">Template</label>
                <div class="font-medium">
                  {{ letter.template_name || `#${letter.template_id}` }}
                </div>
              </div>

              <div v-if="letter.contact_id">
                <label class="block text-sm text-gray-500">Kontakt</label>
                <router-link
                  :to="`/contacts/${letter.contact_id}`"
                  class="font-medium text-go4-primary hover:underline"
                >
                  Kontakt #{{ letter.contact_id }}
                </router-link>
              </div>

              <div v-if="letter.pipeline_id">
                <label class="block text-sm text-gray-500">Pipeline</label>
                <router-link
                  :to="`/engagement/pipelines/${letter.pipeline_id}`"
                  class="font-medium text-go4-primary hover:underline"
                >
                  Pipeline #{{ letter.pipeline_id }}
                </router-link>
              </div>

              <div v-if="letter.pdf_path">
                <label class="block text-sm text-gray-500">PDF</label>
                <a
                  :href="`/uploads/${letter.pdf_path}`"
                  target="_blank"
                  class="font-medium text-go4-primary hover:underline"
                >
                  {{ letter.pdf_path.split('/').pop() }}
                </a>
              </div>
            </div>
          </div>

          <!-- Back Button -->
          <button
            class="btn btn-secondary w-full"
            @click="goBack"
          >
            Zurück zur Übersicht
          </button>
        </div>
      </div>
    </template>
  </div>
</template>
