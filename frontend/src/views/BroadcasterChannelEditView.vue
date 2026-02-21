<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useBroadcasterStore } from '@/stores/broadcaster'
import PageHeader from '@/components/ui/PageHeader.vue'

const route = useRoute()
const router = useRouter()
const store = useBroadcasterStore()

const isEdit = computed(() => !!route.params.id)
const saving = ref(false)

const form = ref({
  name: '',
  slug: '',
  description: '',
  target_audience: '',
  categories: [],
  schedule: '0 6 * * 1-5',
  voice: 'de_DE-thorsten-high',
  language: 'de',
  intro_text: '',
  outro_text: '',
  personal_context_enabled: false,
  max_items: 10,
  max_duration_minutes: 5,
  cover_image_url: ''
})

const categoriesInput = ref('')

const availableVoices = [
  { value: 'de_DE-thorsten-high', label: 'Thorsten (DE, hoch)' },
  { value: 'de_DE-thorsten-medium', label: 'Thorsten (DE, mittel)' },
  { value: 'de_DE-thorsten-low', label: 'Thorsten (DE, niedrig)' },
  { value: 'en_US-amy-medium', label: 'Amy (EN, mittel)' },
  { value: 'en_US-ryan-medium', label: 'Ryan (EN, mittel)' }
]

onMounted(async () => {
  if (isEdit.value) {
    const data = await store.fetchChannel(route.params.id)
    Object.keys(form.value).forEach((key) => {
      if (data[key] !== undefined && data[key] !== null) {
        form.value[key] = data[key]
      }
    })
    categoriesInput.value = (data.categories || []).join(', ')
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
    data.categories = categoriesInput.value
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)

    if (isEdit.value) {
      await store.editChannel(route.params.id, data)
    } else {
      await store.addChannel(data)
    }
    router.push('/broadcaster')
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
      :subtitle="isEdit ? form.name : 'Briefing-Channel erstellen'"
    />

    <!-- Error -->
    <div v-if="store.error" class="mt-4 rounded-lg bg-red-50 p-4 text-sm text-red-700">
      {{ store.error }}
    </div>

    <form class="mt-6 max-w-2xl space-y-6" @submit.prevent="handleSubmit">
      <!-- Name + Slug -->
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div>
          <label class="block text-sm font-medium text-go4-secondary">Name *</label>
          <input
            v-model="form.name"
            required
            class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:ring-1 focus:ring-go4-primary"
            placeholder="Management Briefing"
            @blur="!isEdit && !form.slug && generateSlug()"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-go4-secondary">Slug *</label>
          <input
            v-model="form.slug"
            required
            :disabled="isEdit"
            class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:ring-1 focus:ring-go4-primary disabled:bg-gray-50"
            placeholder="management-briefing"
          />
        </div>
      </div>

      <!-- Description -->
      <div>
        <label class="block text-sm font-medium text-go4-secondary">Beschreibung</label>
        <textarea
          v-model="form.description"
          rows="2"
          class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:ring-1 focus:ring-go4-primary"
          placeholder="Taegliches Briefing fuer die Geschaeftsfuehrung..."
        />
      </div>

      <!-- Target Audience + Categories -->
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div>
          <label class="block text-sm font-medium text-go4-secondary">Zielgruppe</label>
          <input
            v-model="form.target_audience"
            class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:ring-1 focus:ring-go4-primary"
            placeholder="Geschaeftsfuehrung"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-go4-secondary">
            Kategorien (komma-getrennt)
          </label>
          <input
            v-model="categoriesInput"
            class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:ring-1 focus:ring-go4-primary"
            placeholder="social_media, competitor, podcast"
          />
        </div>
      </div>

      <!-- Schedule + Voice -->
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div>
          <label class="block text-sm font-medium text-go4-secondary">Schedule (Cron)</label>
          <input
            v-model="form.schedule"
            class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:ring-1 focus:ring-go4-primary"
            placeholder="0 6 * * 1-5"
          />
          <p class="mt-1 text-xs text-go4-muted">z.B. "0 6 * * 1-5" = Mo-Fr um 06:00</p>
        </div>
        <div>
          <label class="block text-sm font-medium text-go4-secondary">Stimme</label>
          <select
            v-model="form.voice"
            class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:ring-1 focus:ring-go4-primary"
          >
            <option v-for="v in availableVoices" :key="v.value" :value="v.value">
              {{ v.label }}
            </option>
          </select>
        </div>
      </div>

      <!-- Max Items + Duration -->
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div>
          <label class="block text-sm font-medium text-go4-secondary">
            Max. Themen pro Episode
          </label>
          <input
            v-model.number="form.max_items"
            type="number"
            min="1"
            max="50"
            class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:ring-1 focus:ring-go4-primary"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-go4-secondary"> Max. Dauer (Minuten) </label>
          <input
            v-model.number="form.max_duration_minutes"
            type="number"
            min="1"
            max="30"
            class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:ring-1 focus:ring-go4-primary"
          />
        </div>
      </div>

      <!-- Intro + Outro -->
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div>
          <label class="block text-sm font-medium text-go4-secondary">Intro-Text</label>
          <textarea
            v-model="form.intro_text"
            rows="2"
            class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:ring-1 focus:ring-go4-primary"
            placeholder="Willkommen zum Management Briefing..."
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-go4-secondary">Outro-Text</label>
          <textarea
            v-model="form.outro_text"
            rows="2"
            class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:ring-1 focus:ring-go4-primary"
            placeholder="Das war Ihr Briefing fuer heute..."
          />
        </div>
      </div>

      <!-- Actions -->
      <div class="flex items-center gap-3 border-t border-gray-200 pt-6">
        <button
          type="submit"
          :disabled="saving"
          class="rounded-lg bg-go4-primary px-5 py-2 text-sm font-medium text-white transition hover:bg-go4-primary/90 disabled:opacity-50"
        >
          {{ saving ? 'Speichern...' : isEdit ? 'Speichern' : 'Channel erstellen' }}
        </button>
        <router-link
          to="/broadcaster"
          class="rounded-lg border border-gray-300 px-5 py-2 text-sm font-medium text-go4-secondary hover:bg-gray-50"
        >
          Abbrechen
        </router-link>
      </div>
    </form>
  </div>
</template>
