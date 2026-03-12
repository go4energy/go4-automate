<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useWhatsAppStore } from '@/stores/whatsapp'
import PageHeader from '@/components/ui/PageHeader.vue'
import Breadcrumb from '@/components/ui/Breadcrumb.vue'

const props = defineProps({
  id: { type: [String, Number], required: true }
})

const router = useRouter()
const store = useWhatsAppStore()

const loading = ref(true)
const previewVariables = ref({})
const previewResult = ref(null)

const template = computed(() => store.currentTemplate)

// Format date
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

// Status styling
function getStatusClass(status) {
  const classes = {
    APPROVED: 'bg-green-100 text-green-700',
    PENDING: 'bg-yellow-100 text-yellow-700',
    REJECTED: 'bg-red-100 text-red-700'
  }
  return classes[status] || 'bg-gray-100 text-gray-700'
}

function getStatusLabel(status) {
  const labels = {
    APPROVED: 'Genehmigt',
    PENDING: 'Ausstehend',
    REJECTED: 'Abgelehnt'
  }
  return labels[status] || status
}

// Get component text
function getComponentText(components, type) {
  const component = components.find((c) => c.type === type)
  return component?.text || ''
}

// Preview template
async function previewTemplate() {
  try {
    previewResult.value = await store.getTemplatePreview(props.id, previewVariables.value)
  } catch (err) {
    // Error handled by store
  }
}

// Load data
async function loadData() {
  loading.value = true
  try {
    await store.fetchTemplate(props.id)
    // Initialize preview variables
    if (template.value?.variables) {
      template.value.variables.forEach((v) => {
        previewVariables.value[v] = ''
      })
    }
  } catch (err) {
    router.push({ name: 'whatsapp-templates' })
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadData()
})

onUnmounted(() => {
  store.clearCurrent()
})
</script>

<template>
  <div class="p-6">
    <Breadcrumb class="mb-4" />

    <!-- Loading -->
    <div
      v-if="loading"
      class="flex items-center justify-center py-12"
    >
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600" />
    </div>

    <template v-else-if="template">
      <PageHeader :title="template.name">
        <template #description>
          <span
            :class="['px-2 py-1 text-xs font-medium rounded-full', getStatusClass(template.status)]"
          >
            {{ getStatusLabel(template.status) }}
          </span>
          <span class="ml-2 text-gray-500">{{ template.language }} - {{ template.category }}</span>
        </template>
      </PageHeader>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
        <!-- Template Info -->
        <div class="bg-white rounded-lg shadow p-6">
          <h3 class="font-semibold text-gray-900 mb-4">
            Template-Struktur
          </h3>

          <div class="space-y-4">
            <!-- Header -->
            <div v-if="getComponentText(template.components, 'HEADER')">
              <label class="block text-sm font-medium text-gray-500 mb-1">Header</label>
              <p class="text-gray-900 bg-gray-50 p-3 rounded">
                {{ getComponentText(template.components, 'HEADER') }}
              </p>
            </div>

            <!-- Body -->
            <div>
              <label class="block text-sm font-medium text-gray-500 mb-1">Body</label>
              <p class="text-gray-900 bg-gray-50 p-3 rounded whitespace-pre-wrap">
                {{ getComponentText(template.components, 'BODY') }}
              </p>
            </div>

            <!-- Footer -->
            <div v-if="getComponentText(template.components, 'FOOTER')">
              <label class="block text-sm font-medium text-gray-500 mb-1">Footer</label>
              <p class="text-gray-900 bg-gray-50 p-3 rounded text-sm">
                {{ getComponentText(template.components, 'FOOTER') }}
              </p>
            </div>

            <!-- Buttons -->
            <div
              v-for="(component, idx) in template.components.filter((c) => c.type === 'BUTTONS')"
              :key="idx"
            >
              <label class="block text-sm font-medium text-gray-500 mb-1">Buttons</label>
              <div class="space-y-2">
                <div
                  v-for="(button, bidx) in component.buttons || []"
                  :key="bidx"
                  class="bg-gray-50 p-2 rounded text-sm"
                >
                  {{ button.text }} ({{ button.type }})
                </div>
              </div>
            </div>
          </div>

          <!-- Meta Info -->
          <div class="mt-6 pt-6 border-t">
            <dl class="grid grid-cols-2 gap-4 text-sm">
              <div>
                <dt class="text-gray-500">
                  Account ID
                </dt>
                <dd class="text-gray-900">
                  {{ template.account_id }}
                </dd>
              </div>
              <div>
                <dt class="text-gray-500">
                  Zuletzt synchronisiert
                </dt>
                <dd class="text-gray-900">
                  {{ formatDate(template.last_synced_at) }}
                </dd>
              </div>
            </dl>
          </div>
        </div>

        <!-- Preview -->
        <div class="bg-white rounded-lg shadow p-6">
          <h3 class="font-semibold text-gray-900 mb-4">
            Vorschau
          </h3>

          <!-- Variables Input -->
          <div
            v-if="template.variables?.length > 0"
            class="space-y-4 mb-6"
          >
            <div
              v-for="variable in template.variables"
              :key="variable"
            >
              <label class="block text-sm font-medium text-gray-700 mb-1">
                {{ variable }}
              </label>
              <input
                v-model="previewVariables[variable]"
                type="text"
                class="input w-full"
                :placeholder="`Wert für ${variable}`"
              >
            </div>
            <button
              class="btn btn-secondary w-full"
              @click="previewTemplate"
            >
              Vorschau aktualisieren
            </button>
          </div>

          <!-- Preview Result -->
          <div class="bg-gray-100 rounded-lg p-4">
            <div class="max-w-xs mx-auto bg-green-500 rounded-lg p-4 text-white">
              <p class="whitespace-pre-wrap">
                {{ previewResult?.rendered_text || getComponentText(template.components, 'BODY') }}
              </p>
              <div class="text-right text-xs text-green-200 mt-2">
                {{ new Date().toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' }) }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
