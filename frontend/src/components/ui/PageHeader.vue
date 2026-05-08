<script setup>
import { ref } from 'vue'

import { getModuleDocumentation } from '@/api/modules'
import MarkdownViewer from '@/components/ui/MarkdownViewer.vue'

const props = defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: null },
  infoModule: { type: String, default: null }
})

const showDocumentation = ref(false)
const documentationTitle = ref('Dokumentation')
const documentationContent = ref('')
const documentationLoading = ref(false)
const documentationError = ref(null)

async function openDocumentation() {
  if (!props.infoModule) return
  showDocumentation.value = true
  documentationLoading.value = true
  documentationError.value = null

  try {
    const { data } = await getModuleDocumentation(props.infoModule)
    documentationTitle.value = data.title || 'Dokumentation'
    documentationContent.value = data.content || ''
  } catch (err) {
    documentationError.value = err.message
    documentationContent.value = ''
  } finally {
    documentationLoading.value = false
  }
}
</script>

<template>
  <div class="mb-6 flex items-center justify-between">
    <div>
      <div class="flex items-center gap-3">
        <h1 class="text-2xl font-bold text-go4-secondary dark:text-gray-100">
          {{ title }}
        </h1>
        <button
          v-if="infoModule"
          class="rounded-full border border-gray-300 bg-white px-2.5 py-1 text-xs font-medium text-gray-700 transition hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
          @click="openDocumentation"
        >
          Info
        </button>
      </div>
      <p
        v-if="subtitle"
        class="mt-1 text-sm text-go4-muted dark:text-gray-400"
      >
        {{ subtitle }}
      </p>
    </div>
    <div class="flex items-center gap-3">
      <slot name="actions" />
    </div>
  </div>
  <MarkdownViewer
    :open="showDocumentation"
    :title="documentationTitle"
    :content="documentationContent"
    :loading="documentationLoading"
    :error="documentationError"
    @close="showDocumentation = false"
  />
</template>
