<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useBriefingStore } from '@/stores/briefing'
import { useAuthStore } from '@/stores/auth'
import PageHeader from '@/components/ui/PageHeader.vue'
import TagSelector from '@/components/ui/TagSelector.vue'
import StreamSelector from '@/components/ui/StreamSelector.vue'

const route = useRoute()
const router = useRouter()
const store = useBriefingStore()
const authStore = useAuthStore()

const isEdit = computed(() => !!route.params.id)
const saving = ref(false)
const orgWide = ref(false)

const form = ref({
  name: '',
  slug: '',
  description: '',
  target_audience: '',
  tags: [],
  streams: [],
  schedule: '0 6 * * 1-5',
  voice: 'de_DE-thorsten-high',
  language: 'de',
  intro_text: '',
  outro_text: '',
  personal_context_enabled: false,
  max_items: 10,
  max_duration_minutes: 5,
  cover_image_url: '',
  output_format: 'audio',
  text_format: 'markdown',
  tts_engine: null,
  xtts_speaker_id: null
})

const effectiveEngine = computed(() => form.value.tts_engine || 'piper')

const availableVoices = [
  { value: 'de_DE-thorsten-high', label: 'Thorsten (DE, hoch)' },
  { value: 'de_DE-thorsten-medium', label: 'Thorsten (DE, mittel)' },
  { value: 'de_DE-thorsten-low', label: 'Thorsten (DE, niedrig)' },
  { value: 'en_US-amy-medium', label: 'Amy (EN, mittel)' },
  { value: 'en_US-ryan-medium', label: 'Ryan (EN, mittel)' }
]

onMounted(async () => {
  store.fetchSpeakers()
  if (isEdit.value) {
    const data = await store.fetchChannel(route.params.id)
    Object.keys(form.value).forEach((key) => {
      if (data[key] !== undefined && data[key] !== null) {
        form.value[key] = data[key]
      }
    })
    form.value.tags = data.tags || []
    form.value.streams = data.streams || []
    // Nullable fields that might come back as null
    form.value.tts_engine = data.tts_engine || null
    form.value.xtts_speaker_id = data.xtts_speaker_id || null
  }
})

function generateSlug() {
  form.value.slug = form.value.name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
}

async function handleSubmit() {
  saving.value = true
  try {
    const data = { ...form.value }

    if (isEdit.value) {
      await store.editChannel(route.params.id, data)
    } else {
      const params = orgWide.value ? { org_wide: true } : undefined
      await store.addChannel(data, params)
    }
    router.push('/briefing')
  } catch {
    // error handled by store
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div>
    <PageHeader
      :title="isEdit ? 'Channel bearbeiten' : 'Neuer Channel'"
    />

    <!-- Error -->
    <div
      v-if="store.error"
      class="mt-4 rounded-lg bg-red-50 dark:bg-red-900/20 p-4 text-sm text-red-700 dark:text-red-400"
    >
      {{ store.error }}
    </div>

    <form
      class="mt-6 max-w-2xl space-y-6"
      @submit.prevent="handleSubmit"
    >
      <!-- Name + Slug -->
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div>
          <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">Name *</label>
          <input
            v-model="form.name"
            required
            class="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-800 dark:text-gray-200 focus:border-go4-primary focus:ring-1 focus:ring-go4-primary"
            placeholder="Management Briefing"
            @blur="!isEdit && !form.slug && generateSlug()"
          >
        </div>
        <div>
          <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">Slug *</label>
          <input
            v-model="form.slug"
            required
            :disabled="isEdit"
            class="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-800 dark:text-gray-200 focus:border-go4-primary focus:ring-1 focus:ring-go4-primary disabled:bg-gray-50 dark:disabled:bg-gray-800/50"
            placeholder="management-briefing"
          >
        </div>
      </div>

      <!-- Description -->
      <div>
        <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">Beschreibung</label>
        <textarea
          v-model="form.description"
          rows="2"
          class="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-800 dark:text-gray-200 focus:border-go4-primary focus:ring-1 focus:ring-go4-primary"
          placeholder="Taegliches Briefing fuer die Geschaeftsfuehrung..."
        />
      </div>

      <!-- Target Audience + Categories -->
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div>
          <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">Zielgruppe</label>
          <input
            v-model="form.target_audience"
            class="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-800 dark:text-gray-200 focus:border-go4-primary focus:ring-1 focus:ring-go4-primary"
            placeholder="Geschaeftsfuehrung"
          >
        </div>
        <div>
          <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">
            Tags
          </label>
          <div class="mt-1">
            <TagSelector
              v-model="form.tags"
              placeholder="Tags auswaehlen..."
            />
          </div>
        </div>
      </div>

      <!-- Streams -->
      <div>
        <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">
          Streams
        </label>
        <div class="mt-1">
          <StreamSelector
            v-model="form.streams"
            placeholder="Streams auswaehlen..."
          />
        </div>
      </div>

      <!-- Schedule -->
      <div>
        <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">Schedule (Cron)</label>
        <input
          v-model="form.schedule"
          class="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-800 dark:text-gray-200 focus:border-go4-primary focus:ring-1 focus:ring-go4-primary"
          placeholder="0 6 * * 1-5"
        >
        <p class="mt-1 text-xs text-go4-muted dark:text-gray-400">
          z.B. "0 6 * * 1-5" = Mo-Fr um 06:00
        </p>
      </div>

      <!-- TTS Engine + Voice/Speaker -->
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div>
          <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">TTS-Engine</label>
          <select
            v-model="form.tts_engine"
            class="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-800 dark:text-gray-200 focus:border-go4-primary focus:ring-1 focus:ring-go4-primary"
          >
            <option :value="null">
              Standard (global)
            </option>
            <option value="piper">
              Piper
            </option>
            <option value="xtts">
              XTTS v2
            </option>
            <option value="disabled">
              Deaktiviert
            </option>
          </select>
        </div>
        <div v-if="effectiveEngine !== 'xtts'">
          <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">Piper-Stimme</label>
          <select
            v-model="form.voice"
            class="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-800 dark:text-gray-200 focus:border-go4-primary focus:ring-1 focus:ring-go4-primary"
          >
            <option
              v-for="v in availableVoices"
              :key="v.value"
              :value="v.value"
            >
              {{ v.label }}
            </option>
          </select>
        </div>
        <div v-else>
          <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">XTTS-Sprecher</label>
          <select
            v-model="form.xtts_speaker_id"
            class="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-800 dark:text-gray-200 focus:border-go4-primary focus:ring-1 focus:ring-go4-primary"
          >
            <option :value="null">
              Kein Sprecher
            </option>
            <option
              v-for="s in store.speakers"
              :key="s.id"
              :value="s.id"
            >
              {{ s.name }} ({{ s.language === 'de' ? 'DE' : 'EN' }})
            </option>
          </select>
          <p
            v-if="store.speakers.length === 0"
            class="mt-1 text-xs text-go4-muted dark:text-gray-400"
          >
            Noch keine Sprecher. Laden Sie einen im "Sprecher"-Tab hoch.
          </p>
        </div>
      </div>

      <!-- Max Items + Duration -->
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div>
          <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">
            Max. Themen pro Episode
          </label>
          <input
            v-model.number="form.max_items"
            type="number"
            min="1"
            max="50"
            class="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-800 dark:text-gray-200 focus:border-go4-primary focus:ring-1 focus:ring-go4-primary"
          >
        </div>
        <div>
          <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">
            Max. Dauer (Minuten)
          </label>
          <input
            v-model.number="form.max_duration_minutes"
            type="number"
            min="1"
            max="30"
            class="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-800 dark:text-gray-200 focus:border-go4-primary focus:ring-1 focus:ring-go4-primary"
          >
        </div>
      </div>

      <!-- Output Format -->
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div>
          <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">
            Ausgabeformat
          </label>
          <select
            v-model="form.output_format"
            class="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-800 dark:text-gray-200 focus:border-go4-primary focus:ring-1 focus:ring-go4-primary"
          >
            <option value="audio">
              Audio
            </option>
            <option value="text">
              Text
            </option>
            <option value="both">
              Audio + Text
            </option>
          </select>
        </div>
        <div v-if="form.output_format !== 'audio'">
          <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">
            Textformat
          </label>
          <select
            v-model="form.text_format"
            class="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-800 dark:text-gray-200 focus:border-go4-primary focus:ring-1 focus:ring-go4-primary"
          >
            <option value="markdown">
              Markdown
            </option>
            <option value="html">
              HTML
            </option>
          </select>
        </div>
      </div>

      <!-- Intro + Outro -->
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div>
          <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">Intro-Text</label>
          <textarea
            v-model="form.intro_text"
            rows="2"
            class="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-800 dark:text-gray-200 focus:border-go4-primary focus:ring-1 focus:ring-go4-primary"
            placeholder="Willkommen zum Management Briefing..."
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">Outro-Text</label>
          <textarea
            v-model="form.outro_text"
            rows="2"
            class="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-800 dark:text-gray-200 focus:border-go4-primary focus:ring-1 focus:ring-go4-primary"
            placeholder="Das war Ihr Briefing fuer heute..."
          />
        </div>
      </div>

      <!-- Org-Wide Toggle (Admin only, create mode) -->
      <div
        v-if="authStore.isAdmin && !isEdit"
        class="flex items-center gap-3 rounded-lg bg-sky-50 dark:bg-sky-900/20 p-4"
      >
        <label class="flex items-center gap-2">
          <input
            v-model="orgWide"
            type="checkbox"
            class="h-4 w-4 rounded border-gray-300 text-go4-primary focus:ring-go4-primary dark:border-gray-600"
          >
          <span class="text-sm font-medium text-sky-700 dark:text-sky-400">Org-weiter Channel (fuer alle Mitarbeiter sichtbar)</span>
        </label>
      </div>

      <!-- Actions -->
      <div class="flex items-center gap-3 border-t border-gray-200 dark:border-gray-700 pt-6">
        <button
          type="submit"
          :disabled="saving"
          class="rounded-lg bg-go4-primary px-5 py-2 text-sm font-medium text-white transition hover:bg-go4-primary/90 disabled:opacity-50"
        >
          {{ saving ? 'Speichern...' : isEdit ? 'Speichern' : 'Channel erstellen' }}
        </button>
        <router-link
          to="/briefing"
          class="rounded-lg border border-gray-300 dark:border-gray-600 px-5 py-2 text-sm font-medium text-go4-secondary dark:text-gray-100 hover:bg-gray-50 dark:hover:bg-gray-700"
        >
          Abbrechen
        </router-link>
      </div>
    </form>
  </div>
</template>
