<script setup>
/**
 * KI-Designer-Chat for email templates.
 * Persistent per template — history is loaded on mount, each user message
 * is sent to /templates/:id/ai-chat which returns:
 *   - assistant_message (text)
 *   - tool_calls (what Claude did: set_full_html, apply_diff, …)
 *   - new_html (if any tool changed the HTML)
 *
 * When new_html is returned, we emit it so the parent can update the
 * CodeMirror editor.
 */
import { ref, onMounted, nextTick, computed, watch } from 'vue'
import api from '@/api'

const props = defineProps({
  templateId: { type: [Number, String], default: null },
  currentHtml: { type: String, default: '' },
  // Optional callback returning a Promise<id> — invoked when the user wants
  // to chat but the template hasn't been saved yet. Auto-save happens
  // transparently and we continue with the resulting id.
  autoSave: { type: Function, default: null },
})
const emit = defineEmits(['update-html'])

const messages = ref([])
const loading = ref(false)
const sending = ref(false)
const error = ref(null)
const input = ref('')
const messagesContainer = ref(null)

const ready = computed(() => Boolean(props.templateId))
// We can chat as long as we have either an existing id or an auto-save callback
const canStartChat = computed(() => Boolean(props.templateId || props.autoSave))
const apiBase = computed(() => `/v1/emailmarketing/templates/${props.templateId}/ai-chat`)

async function loadHistory() {
  if (!ready.value) return
  loading.value = true
  try {
    const { data } = await api.get(apiBase.value)
    messages.value = data
    await scrollToBottom()
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    loading.value = false
  }
}

async function send() {
  const text = input.value.trim()
  if (!text || !canStartChat.value || sending.value) return
  sending.value = true
  error.value = null

  // If the template hasn't been saved yet, auto-save it first so we get an id.
  if (!props.templateId && props.autoSave) {
    try {
      const newId = await props.autoSave()
      if (!newId) {
        sending.value = false
        error.value = 'Bitte erst Name + Slug + Betreff ausfüllen, dann KI-Chat nutzen.'
        return
      }
      // Wait one tick for the parent to propagate the new template id via prop
      await nextTick()
    } catch (e) {
      sending.value = false
      error.value = 'Auto-Speichern fehlgeschlagen: ' + (e.message || 'unbekannt')
      return
    }
  }

  // Optimistic user message
  messages.value.push({
    id: -Date.now(),
    role: 'user',
    content: text,
    created_at: new Date().toISOString(),
    _optimistic: true,
  })
  await scrollToBottom()
  input.value = ''

  try {
    const { data } = await api.post(apiBase.value, {
      message: text,
      current_html: props.currentHtml,
    })

    // Reload full history so we have the canonical thread (incl. tool rows)
    await loadHistory()

    if (data.new_html) {
      emit('update-html', data.new_html)
    }
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
    // Remove the optimistic message on failure
    messages.value = messages.value.filter((m) => !m._optimistic)
  } finally {
    sending.value = false
  }
}

async function clearHistory() {
  if (!confirm('Chat-Verlauf wirklich löschen?')) return
  try {
    await api.delete(apiBase.value)
    messages.value = []
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  }
}

function scrollToBottom() {
  return nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

function onEnter(e) {
  if (e.shiftKey) return // Shift+Enter = newline
  e.preventDefault()
  send()
}

function fmtTime(iso) {
  const d = new Date(iso.endsWith('Z') ? iso : iso + 'Z')
  return d.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })
}

const visibleMessages = computed(() =>
  // Don't show 'tool' role messages directly — they're internal plumbing
  messages.value.filter((m) => m.role !== 'tool'),
)

// When templateId becomes available (e.g. after auto-save), load history.
watch(() => props.templateId, (newId, oldId) => {
  if (newId && newId !== oldId) loadHistory()
})

onMounted(loadHistory)
</script>

<template>
  <div class="rounded-lg border border-go4-primary/30 bg-blue-50/30 dark:bg-blue-900/10 dark:border-blue-800/40 overflow-hidden flex flex-col">
    <!-- Header -->
    <div class="flex items-center justify-between border-b border-go4-primary/20 dark:border-blue-800/40 px-4 py-2">
      <div class="flex items-center gap-2">
        <span class="text-lg">🤖</span>
        <span class="font-medium text-sm text-gray-900 dark:text-gray-100">
          KI-Designer-Assistant
        </span>
      </div>
      <button
        v-if="messages.length > 0"
        type="button"
        class="text-xs text-gray-500 hover:text-red-600"
        @click="clearHistory"
      >
        Verlauf löschen
      </button>
    </div>

    <!-- Not ready AND no autoSave fallback — minimal guard -->
    <div
      v-if="!canStartChat"
      class="p-4 text-sm text-gray-600 dark:text-gray-300"
    >
      Bitte zuerst die Vorlage speichern (Name + Slug + Betreff). Dann steht dir der KI-Designer
      mit Chat-Verlauf zur Verfügung.
    </div>

    <template v-else>
      <!-- Hint when not yet saved but auto-save is available -->
      <div
        v-if="!ready"
        class="px-4 pt-3 text-xs text-blue-700 dark:text-blue-200"
      >
        💡 Beim ersten Senden wird die Vorlage automatisch gespeichert (Name + Slug + Betreff erforderlich).
      </div>
      <!-- Messages -->
      <div
        ref="messagesContainer"
        class="overflow-y-auto p-4 space-y-3"
        style="max-height: 400px; min-height: 200px;"
      >
        <div
          v-if="loading"
          class="text-sm text-gray-500"
        >
          Verlauf laden…
        </div>
        <div
          v-else-if="visibleMessages.length === 0"
          class="text-sm text-gray-500 dark:text-gray-400 leading-relaxed"
        >
          <p class="mb-2">
            👋 Hallo! Ich helfe dir beim Bauen von E-Mail-Templates.
          </p>
          <p class="mb-2">Beispiel-Anfragen:</p>
          <ul class="list-disc list-inside text-xs space-y-1">
            <li>„Erstelle ein Cold-Outreach-Template für Stadtwerke, modern, blau-weiß"</li>
            <li>„Füge mein Logo oben ein" (lädt Bilder aus der Asset-Library)</li>
            <li>„Mach den CTA-Button grün"</li>
            <li>„Schreibe den Footer noch professioneller"</li>
          </ul>
        </div>

        <div
          v-for="msg in visibleMessages"
          :key="msg.id"
          class="flex"
          :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
        >
          <div
            class="max-w-[80%] rounded-lg px-3 py-2 text-sm"
            :class="msg.role === 'user'
              ? 'bg-go4-primary text-white'
              : 'bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 border border-gray-200 dark:border-gray-700'"
          >
            <div
              v-if="msg.content"
              class="whitespace-pre-wrap"
            >
              {{ msg.content }}
            </div>
            <!-- Tool-call indicators on assistant messages -->
            <div
              v-if="msg.tool_calls && msg.tool_calls.length"
              class="mt-2 space-y-1"
            >
              <div
                v-for="(tc, idx) in msg.tool_calls"
                :key="idx"
                class="text-xs px-2 py-1 rounded bg-emerald-50 dark:bg-emerald-900/20 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/40"
              >
                <span v-if="tc.name === 'set_full_html'">✓ HTML komplett ersetzt</span>
                <span v-else-if="tc.name === 'apply_diff'">✓ {{ tc.input?.summary || 'Änderung angewandt' }}</span>
                <span v-else-if="tc.name === 'insert_image'">✓ Bild eingefügt</span>
                <span v-else-if="tc.name === 'list_assets'">📋 Asset-Library angesehen</span>
                <span v-else>🔧 {{ tc.name }}</span>
              </div>
            </div>
            <div
              class="text-[10px] mt-1 opacity-60"
              :class="msg.role === 'user' ? 'text-right' : ''"
            >
              {{ fmtTime(msg.created_at) }}
            </div>
          </div>
        </div>

        <div
          v-if="sending"
          class="flex justify-start"
        >
          <div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-500">
            Claude denkt nach…
          </div>
        </div>
      </div>

      <!-- Error -->
      <div
        v-if="error"
        class="px-4 py-2 bg-red-50 dark:bg-red-900/20 border-t border-red-200 dark:border-red-800/40 text-xs text-red-700 dark:text-red-300"
      >
        {{ error }}
      </div>

      <!-- Input -->
      <div class="border-t border-go4-primary/20 dark:border-blue-800/40 p-3">
        <div class="flex gap-2">
          <textarea
            v-model="input"
            rows="2"
            class="flex-1 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary resize-none"
            placeholder="Was soll der Editor tun? (Enter = senden, Shift+Enter = neue Zeile)"
            :disabled="sending"
            @keydown.enter="onEnter"
          />
          <button
            type="button"
            class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="sending || !input.trim()"
            @click="send"
          >
            {{ sending ? '…' : 'Senden' }}
          </button>
        </div>
      </div>
    </template>
  </div>
</template>
