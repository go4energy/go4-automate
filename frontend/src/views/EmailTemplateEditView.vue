<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useEmailMarketingStore } from '@/stores/emailmarketing'
import { previewTemplate } from '@/api/emailmarketing'
import PageHeader from '@/components/ui/PageHeader.vue'
import UnlayerEmailEditor from '@/components/email/UnlayerEmailEditor.vue'
import HtmlCodeEditor from '@/components/email/HtmlCodeEditor.vue'
import AssetLibrary from '@/components/email/AssetLibrary.vue'
import EmailDesignerChat from '@/components/email/EmailDesignerChat.vue'

const route = useRoute()
const router = useRouter()
const store = useEmailMarketingStore()

const isNew = computed(() => !route.params.id)
const loading = ref(true)
const saving = ref(false)
const previewHtml = ref('')

const visualEditor = ref(null)

// HTML-mode sub-tabs: 'edit' | 'preview'
const htmlSubTab = ref('edit')

const form = ref({
  name: '',
  slug: '',
  description: '',
  subject: '',
  html_content: '',
  text_content: '',
  variables: ['first_name', 'llm_body', 'tracking_hash', 'unsubscribe_url'],
  category: '',
  tags: [],
  is_active: true,
  design_json: null,
  editor_mode: 'unlayer',
})

const inputClass =
  'block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 ' +
  'placeholder-gray-400 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary ' +
  'disabled:bg-gray-100 disabled:text-gray-500 ' +
  'dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 dark:placeholder-gray-500 dark:disabled:bg-gray-800'
const labelClass = 'block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1'
const cardClass =
  'rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800'
const headingClass = 'text-lg font-semibold text-gray-900 dark:text-gray-100'
const primaryBtnClass =
  'rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark ' +
  'disabled:opacity-50 disabled:cursor-not-allowed'
const secondaryBtnClass =
  'rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 ' +
  'hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed ' +
  'dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600'

const editorModes = [
  {
    value: 'unlayer',
    label: 'Editor',
    description: 'Drag-&-Drop visueller Editor (Unlayer). Empfohlen für Marketing-Mails.',
  },
  {
    value: 'plain',
    label: 'Reiner Text',
    description: 'Nur Text, keine Formatierung. Hohe Deliverability, einfach. Für persönliche 1-zu-1 Mails.',
  },
  {
    value: 'html',
    label: 'HTML (Code + KI)',
    description: 'Code-Editor mit KI-Assistenten (Claude). Für Power-User mit volle Kontrolle.',
  },
]

function generateSlug(name) {
  return name
    .toLowerCase()
    .replace(/[äöüß]/g, (c) => ({ ä: 'ae', ö: 'oe', ü: 'ue', ß: 'ss' })[c])
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
}

const defaultByMode = {
  unlayer: '',
  plain:
    'Hallo {{first_name}},\n\n{{llm_body}}\n\nMit freundlichen Grüßen\nIhr Smartladen-Team\n\n— —\n{{impressum_block}}\n\nAbmelden: {{unsubscribe_url}}',
  html:
    `<table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;font-family:Arial,sans-serif;">
  <tr><td align="center">
    <table width="600" cellpadding="0" cellspacing="0" style="background:#fff;padding:24px;">
      <tr><td>
        <p style="margin:0 0 16px;color:#333;">Hallo {{first_name}},</p>
        <p style="margin:0 0 16px;color:#333;">{{llm_body}}</p>
        <p style="margin:24px 0;text-align:center;">
          <a href="{{tracking_link "/termin"}}" style="background:#1e40af;color:#fff;padding:12px 24px;border-radius:6px;text-decoration:none;display:inline-block;">Termin buchen</a>
        </p>
        <p style="margin:0 0 16px;color:#333;">Mit freundlichen Grüßen<br>Ihr Smartladen-Team</p>
        <hr style="border:none;border-top:1px solid #eee;margin:24px 0;">
        <div style="font-size:11px;color:#888;">
          {{impressum_block}}<br><br>
          <a href="{{unsubscribe_url}}" style="color:#888;">Abmelden</a>
        </div>
      </td></tr>
    </table>
  </td></tr>
</table>`,
}

function applyDefaultIfEmpty() {
  // When user picks a mode and the relevant content field is empty,
  // seed it with the default starter for that mode.
  const m = form.value.editor_mode
  if (m === 'plain' && !form.value.text_content) {
    form.value.text_content = defaultByMode.plain
  }
  if (m === 'html' && !form.value.html_content) {
    form.value.html_content = defaultByMode.html
  }
  // 'unlayer' starts with empty editor (user drags blocks in)
}

function changeEditorMode(newMode) {
  if (newMode === form.value.editor_mode) return
  // Detect content that would be lost
  const hasUnlayer = !!form.value.design_json
  const hasHtml = (form.value.html_content || '').trim().length > 0
  const hasPlain = (form.value.text_content || '').trim().length > 0

  let warn = false
  if (form.value.editor_mode === 'unlayer' && hasUnlayer) warn = true
  if (form.value.editor_mode === 'html' && hasHtml && newMode !== 'html') warn = true
  if (form.value.editor_mode === 'plain' && hasPlain && newMode !== 'plain') warn = true

  if (warn) {
    const ok = confirm(
      `Modus-Wechsel: ${form.value.editor_mode} → ${newMode}\n\n` +
      'Inhalte aus dem aktuellen Modus bleiben gespeichert, sind aber im neuen Modus nicht direkt editierbar. ' +
      'Beim Speichern wird nur der Inhalt des aktiven Modus als versendebereit markiert.\n\n' +
      'Wirklich wechseln?',
    )
    if (!ok) return
  }
  form.value.editor_mode = newMode
  applyDefaultIfEmpty()
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
          html_content: store.currentTemplate.html_content || '',
          text_content: store.currentTemplate.text_content || '',
          variables: store.currentTemplate.variables || [],
          category: store.currentTemplate.category || '',
          tags: store.currentTemplate.tags || [],
          is_active: store.currentTemplate.is_active,
          design_json: store.currentTemplate.design_json || null,
          editor_mode: store.currentTemplate.editor_mode || 'unlayer',
        }
      }
    } catch (err) {
      router.push({ name: 'emailmarketing' })
    }
  } else {
    applyDefaultIfEmpty()
  }
  loading.value = false
}

async function save() {
  saving.value = true
  try {
    if (form.value.editor_mode === 'unlayer' && visualEditor.value) {
      try {
        const { design, html } = await visualEditor.value.exportContent()
        form.value.design_json = design
        form.value.html_content = html
      } catch {
        alert('Editor noch nicht bereit, bitte erneut versuchen.')
        saving.value = false
        return
      }
    } else if (form.value.editor_mode === 'plain') {
      // For plain mode, copy text into html_content as <pre>-wrapped fallback
      // so the send pipeline always has html_content available.
      form.value.html_content = `<pre style="font-family:Arial,sans-serif;white-space:pre-wrap;">${form.value.text_content}</pre>`
    }
    // 'html' mode: html_content is already maintained by the CodeMirror v-model

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

const sampleMergeData = {
  first_name: 'Max',
  last_name: 'Mustermann',
  full_name: 'Max Mustermann',
  company_name: 'Beispiel GmbH',
  position: 'Geschäftsführer',
  email: 'max@beispiel.de',
  unsubscribe_url: '#abmelden',
  llm_body: '[Hier würde der vom Brain-LLM personalisierte Body-Text stehen.]',
  llm_subject: 'Beispiel-Betreff',
  tracking_hash: 'abc123XYZ',
  impressum_block: 'Smartladen GmbH · Musterstr. 1 · 10115 Berlin · HRB 12345',
}

async function refreshPreview() {
  try {
    let html = form.value.html_content
    if (form.value.editor_mode === 'unlayer' && visualEditor.value) {
      try {
        const result = await visualEditor.value.exportContent()
        html = result.html
      } catch {
        /* editor not ready */
      }
    } else if (form.value.editor_mode === 'plain') {
      html = `<pre style="font-family:Arial,sans-serif;white-space:pre-wrap;">${form.value.text_content}</pre>`
    }
    const { data } = await previewTemplate({
      html_content: html,
      merge_data: sampleMergeData,
    })
    previewHtml.value = data.html
  } catch (err) {
    previewHtml.value = `<p style="color:red">Vorschau-Fehler: ${err.message || 'unbekannt'}</p>`
  }
}

// Auto-refresh preview when entering preview tab in HTML-mode
watch(
  () => htmlSubTab.value,
  (tab) => {
    if (tab === 'preview') refreshPreview()
  },
)

onMounted(loadData)
</script>

<template>
  <div>
    <PageHeader :title="isNew ? 'Neue Vorlage' : 'Vorlage bearbeiten'">
      <template #actions>
        <button
          type="button"
          :disabled="saving || !form.name || !form.slug || !form.subject"
          :class="primaryBtnClass"
          @click="save"
        >
          {{ saving ? 'Speichern…' : 'Speichern' }}
        </button>
      </template>
    </PageHeader>

    <div
      v-if="loading"
      class="flex items-center justify-center py-12"
    >
      <span class="text-gray-500 dark:text-gray-400">Laden…</span>
    </div>

    <form
      v-else
      class="space-y-6"
      @submit.prevent="save"
    >
      <!-- Basic Info -->
      <div :class="cardClass">
        <h3 :class="`${headingClass} mb-4`">
          Grundeinstellungen
        </h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label :class="labelClass">Name <span class="text-red-500">*</span></label>
            <input
              v-model="form.name"
              type="text"
              required
              :class="inputClass"
              placeholder="z.B. Cold-Outreach Lastmanagement"
              @input="isNew && (form.slug = generateSlug(form.name))"
            >
          </div>
          <div>
            <label :class="labelClass">Slug <span class="text-red-500">*</span></label>
            <input
              v-model="form.slug"
              type="text"
              required
              :disabled="!isNew"
              :class="inputClass"
              placeholder="cold-outreach-lastmanagement"
            >
          </div>
          <div class="md:col-span-2">
            <label :class="labelClass">Beschreibung</label>
            <input
              v-model="form.description"
              type="text"
              :class="inputClass"
              placeholder="Kurze Beschreibung des Verwendungszwecks…"
            >
          </div>
          <div>
            <label :class="labelClass">Kategorie</label>
            <input
              v-model="form.category"
              type="text"
              :class="inputClass"
              placeholder="z.B. cold-outreach"
            >
          </div>
          <div class="flex items-end pb-1">
            <label class="inline-flex items-center cursor-pointer">
              <input
                v-model="form.is_active"
                type="checkbox"
                class="h-4 w-4 rounded border-gray-300 text-go4-primary focus:ring-go4-primary dark:border-gray-600 dark:bg-gray-700"
              >
              <span class="ml-2 text-sm text-gray-700 dark:text-gray-300">Aktiv</span>
            </label>
          </div>

          <!-- Editor-Mode Selector -->
          <div class="md:col-span-2 mt-2 border-t border-gray-200 dark:border-gray-700 pt-4">
            <label :class="labelClass">Editor-Modus</label>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
              <button
                v-for="mode in editorModes"
                :key="mode.value"
                type="button"
                class="text-left rounded-lg border p-3 transition-colors"
                :class="form.editor_mode === mode.value
                  ? 'border-go4-primary bg-go4-primary/5 dark:bg-go4-primary/10'
                  : 'border-gray-200 hover:border-gray-300 dark:border-gray-700 dark:hover:border-gray-600'"
                @click="changeEditorMode(mode.value)"
              >
                <div class="flex items-center gap-2 mb-1">
                  <div
                    class="h-4 w-4 rounded-full border-2 flex items-center justify-center"
                    :class="form.editor_mode === mode.value
                      ? 'border-go4-primary'
                      : 'border-gray-300 dark:border-gray-600'"
                  >
                    <div
                      v-if="form.editor_mode === mode.value"
                      class="h-2 w-2 rounded-full bg-go4-primary"
                    />
                  </div>
                  <span class="font-medium text-sm text-gray-900 dark:text-gray-100">{{ mode.label }}</span>
                </div>
                <p class="text-xs text-gray-500 dark:text-gray-400 leading-snug">
                  {{ mode.description }}
                </p>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Subject (always visible) -->
      <div :class="cardClass">
        <h3 :class="`${headingClass} mb-4`">
          Betreff
        </h3>
        <input
          v-model="form.subject"
          type="text"
          required
          :class="inputClass"
          placeholder="Betreffzeile (kann auch {{llm_subject}} enthalten)"
        >
      </div>

      <!-- Mode: UNLAYER -->
      <div
        v-if="form.editor_mode === 'unlayer'"
        :class="cardClass"
      >
        <h3 :class="`${headingClass} mb-4`">
          Layout (Drag &amp; Drop)
        </h3>
        <UnlayerEmailEditor
          ref="visualEditor"
          :design="form.design_json"
          :min-height="720"
        />
        <p class="mt-3 text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
          Ziehe Blöcke aus der rechten Sidebar ins Layout. Im Editor-Tab
          <strong>„Merge Tags"</strong> findest du alle Platzhalter
          (<code class="rounded bg-gray-100 px-1 dark:bg-gray-700">&#123;&#123;first_name&#125;&#125;</code>,
          <code class="rounded bg-gray-100 px-1 dark:bg-gray-700">&#123;&#123;llm_body&#125;&#125;</code> usw.)
          zum Reinziehen.
        </p>
      </div>

      <!-- Mode: PLAIN TEXT -->
      <div
        v-else-if="form.editor_mode === 'plain'"
        :class="cardClass"
      >
        <h3 :class="`${headingClass} mb-4`">
          Text-Inhalt
        </h3>
        <textarea
          v-model="form.text_content"
          rows="20"
          required
          :class="`${inputClass} font-mono leading-relaxed`"
          placeholder="Hallo {{first_name}},..."
        />
        <p class="mt-2 text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
          Reiner Text, keine HTML-Formatierung. Beste Deliverability, wirkt persönlich. Merge-Tags
          (<code class="rounded bg-gray-100 px-1 dark:bg-gray-700">&#123;&#123;first_name&#125;&#125;</code>,
          <code class="rounded bg-gray-100 px-1 dark:bg-gray-700">&#123;&#123;llm_body&#125;&#125;</code>)
          funktionieren auch hier. Pflicht: Opt-Out-Link
          <code class="rounded bg-gray-100 px-1 dark:bg-gray-700">&#123;&#123;unsubscribe_url&#125;&#125;</code>
          und Impressum
          <code class="rounded bg-gray-100 px-1 dark:bg-gray-700">&#123;&#123;impressum_block&#125;&#125;</code>.
        </p>
      </div>

      <!-- Mode: HTML (Code + KI later) -->
      <div
        v-else-if="form.editor_mode === 'html'"
        :class="cardClass"
      >
        <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h3 :class="headingClass">
            HTML-Editor
          </h3>
          <div class="inline-flex rounded-md border border-gray-200 dark:border-gray-700 p-0.5">
            <button
              type="button"
              class="px-3 py-1 text-xs font-medium rounded transition-colors"
              :class="htmlSubTab === 'edit'
                ? 'bg-go4-primary text-white'
                : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'"
              @click="htmlSubTab = 'edit'"
            >
              Code
            </button>
            <button
              type="button"
              class="px-3 py-1 text-xs font-medium rounded transition-colors"
              :class="htmlSubTab === 'preview'
                ? 'bg-go4-primary text-white'
                : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'"
              @click="htmlSubTab = 'preview'"
            >
              Vorschau
            </button>
          </div>
        </div>

        <!-- KI-Designer-Chat -->
        <div class="mb-4">
          <EmailDesignerChat
            :template-id="route.params.id || null"
            :current-html="form.html_content"
            @update-html="(html) => { form.html_content = html }"
          />
        </div>

        <!-- Code Editor -->
        <div v-show="htmlSubTab === 'edit'">
          <HtmlCodeEditor
            v-model="form.html_content"
            :min-height="640"
          />
          <p class="mt-2 text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
            Verfügbare Merge-Tags:
            <code class="rounded bg-gray-100 px-1 dark:bg-gray-700">&#123;&#123;first_name&#125;&#125;</code>,
            <code class="rounded bg-gray-100 px-1 dark:bg-gray-700">&#123;&#123;company_name&#125;&#125;</code>,
            <code class="rounded bg-gray-100 px-1 dark:bg-gray-700">&#123;&#123;llm_body&#125;&#125;</code>,
            <code class="rounded bg-gray-100 px-1 dark:bg-gray-700">&#123;&#123;tracking_link "/produkte"&#125;&#125;</code>,
            <code class="rounded bg-gray-100 px-1 dark:bg-gray-700">&#123;&#123;unsubscribe_url&#125;&#125;</code>,
            <code class="rounded bg-gray-100 px-1 dark:bg-gray-700">&#123;&#123;impressum_block&#125;&#125;</code>.
          </p>
        </div>

        <!-- Preview Tab -->
        <div v-show="htmlSubTab === 'preview'">
          <div class="rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 p-4">
            <iframe
              :srcdoc="previewHtml"
              class="w-full rounded bg-white"
              :style="{ minHeight: '640px' }"
              sandbox="allow-same-origin"
            />
          </div>
          <button
            type="button"
            :class="`${secondaryBtnClass} mt-3`"
            @click="refreshPreview"
          >
            Vorschau aktualisieren
          </button>
        </div>
      </div>

      <!-- Asset Library — only relevant for unlayer + html modes -->
      <div
        v-if="form.editor_mode !== 'plain'"
        :class="cardClass"
      >
        <h3 :class="`${headingClass} mb-2`">
          Bilder &amp; Dateien
        </h3>
        <p class="text-xs text-gray-500 dark:text-gray-400 mb-4">
          Hochgeladene Bilder werden tenant-weit gespeichert und können in jeder Vorlage verwendet werden.
          Klick auf ein Bild kopiert die URL — diese ins HTML / in den Unlayer-Image-Block einfügen.
        </p>
        <AssetLibrary />
      </div>

      <!-- Plain-Text Fallback (only for unlayer/html modes — plain mode IS the text) -->
      <div
        v-if="form.editor_mode !== 'plain'"
        :class="cardClass"
      >
        <label :class="`${labelClass} mb-2`">
          Plain-Text-Version
          <span class="font-normal text-gray-400">(optional, empfohlen für bessere Deliverability)</span>
        </label>
        <textarea
          v-model="form.text_content"
          rows="6"
          :class="`${inputClass} font-mono`"
          placeholder="Reine Text-Version der Mail…"
        />
      </div>
    </form>
  </div>
</template>
