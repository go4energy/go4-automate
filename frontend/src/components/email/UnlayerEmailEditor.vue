<script setup>
/**
 * Drag-&-Drop Email-Editor (Unlayer / vue-email-editor) für Vue 3.
 *
 * Wichtig: Der Editor wird als iframe von editor.unlayer.com geladen.
 * Der Wrapper darf den iframe NICHT mit overflow:hidden oder fester
 * Höhe begrenzen, sonst zeigt sich nur die initial-leere Container-Div
 * (~50px) und der iframe wird abgeschnitten.
 *
 * Custom Merge-Tags + LLM-Slot werden als Drag-Drop-Tags exportiert.
 */

import { ref, watch, onMounted } from 'vue'
import { EmailEditor } from 'vue-email-editor'

const props = defineProps({
  design: { type: Object, default: null },
  // numeric height in px (component renders min-height in px)
  minHeight: { type: Number, default: 720 },
})

const emit = defineEmits(['change', 'ready'])

const editor = ref(null)
const isReady = ref(false)

const mergeTags = {
  first_name: { name: 'Vorname', value: '{{first_name}}', sample: 'Max' },
  last_name: { name: 'Nachname', value: '{{last_name}}', sample: 'Mustermann' },
  full_name: { name: 'Voller Name', value: '{{full_name}}', sample: 'Max Mustermann' },
  company_name: { name: 'Firma', value: '{{company_name}}', sample: 'Smartladen GmbH' },
  position: { name: 'Position', value: '{{position}}', sample: 'Geschäftsführer' },
  llm_body: {
    name: 'LLM-Body (personalisierter Text)',
    value: '{{llm_body}}',
    sample: 'Der Brain-LLM generiert hier den auf den Empfänger zugeschnittenen Hauptteil der Email.',
  },
  llm_subject: {
    name: 'LLM-Subject',
    value: '{{llm_subject}}',
    sample: 'Eine personalisierte Betreffzeile',
  },
  tracking_hash: {
    name: 'Tracking-Hash',
    value: '{{tracking_hash}}',
    sample: 'abc123XYZ',
  },
  unsubscribe_url: {
    name: 'Abmelde-Link',
    value: '{{unsubscribe_url}}',
    sample: 'https://example.com/unsubscribe',
  },
  impressum_block: {
    name: 'Impressum-Block',
    value: '{{impressum_block}}',
    sample: 'Impressum: Smartladen GmbH …',
  },
}

const editorOptions = {
  appearance: { theme: 'modern_light' },
  features: {
    preview: true,
    stockImages: false,
    textEditor: { tables: true, cleanPaste: true },
  },
  mergeTags,
  locale: 'de-DE',
  // Source-blob is helpful for support tickets
  source: { name: 'go4-automate', version: '1.0' },
}

function onEditorLoad() {
  if (props.design && editor.value) {
    try {
      editor.value.editor.loadDesign(props.design)
    } catch {
      /* design might be malformed; user starts with blank canvas */
    }
  }
}

function onEditorReady() {
  isReady.value = true
  emit('ready')
}

watch(
  () => props.design,
  (next) => {
    if (next && editor.value && isReady.value) {
      try {
        editor.value.editor.loadDesign(next)
      } catch {
        /* ignore */
      }
    }
  },
)

function exportContent() {
  return new Promise((resolve, reject) => {
    if (!editor.value || !isReady.value) {
      reject(new Error('Editor noch nicht bereit'))
      return
    }
    editor.value.editor.exportHtml((data) => {
      resolve({ design: data.design, html: data.html })
    })
  })
}

defineExpose({ exportContent })

onMounted(() => {
  /* Editor mounted; embed-script is loaded by the wrapper itself */
})
</script>

<template>
  <div
    class="unlayer-wrapper rounded-lg border border-gray-200 bg-white dark:border-gray-700"
    :style="{ minHeight: minHeight + 'px' }"
  >
    <EmailEditor
      ref="editor"
      :options="editorOptions"
      :min-height="minHeight + 'px'"
      @load="onEditorLoad"
      @ready="onEditorReady"
    />
    <!-- Status fallback while iframe loads (Unlayer takes 1-3s) -->
    <div
      v-if="!isReady"
      class="absolute inset-0 flex items-center justify-center pointer-events-none"
    >
      <div class="text-sm text-gray-500 dark:text-gray-400">
        Editor lädt…
      </div>
    </div>
  </div>
</template>

<style>
/* NOT scoped — Unlayer creates the .unlayer-editor div outside Vue's
   scoped-CSS attribute, and the iframe gets injected by their script. */
.unlayer-wrapper {
  position: relative;
  display: flex;
  flex-direction: column;
}
.unlayer-wrapper .unlayer-editor {
  flex: 1 1 auto;
  width: 100% !important;
  display: flex !important;
  flex-direction: column;
  border-radius: 0.5rem;
}
.unlayer-wrapper .unlayer-editor iframe {
  flex: 1 1 auto;
  width: 100% !important;
  height: 100% !important;
  min-height: 720px !important;
  border: 0 !important;
  display: block !important;
}
</style>
