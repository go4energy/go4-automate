<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useResearchStore } from '@/stores/research'

const route = useRoute()
const router = useRouter()
const store = useResearchStore()

const loading = ref(false)
const error = ref(null)
const saving = ref(false)

const isEdit = computed(() => !!route.params.id)

const form = ref({
  name: '',
  url: '',
  source_type: 'rss',
  keywords: [],
  fetch_interval_hours: 24,
  config: null
})

const keywordInput = ref('')
const configInput = ref('')

onMounted(async () => {
  if (isEdit.value) {
    loading.value = true
    try {
      const data = await store.fetchSource(Number(route.params.id))
      form.value = {
        name: data.name,
        url: data.url,
        source_type: data.source_type,
        keywords: data.keywords || [],
        fetch_interval_hours: data.fetch_interval_hours,
        config: data.config
      }
      if (data.config) {
        configInput.value = JSON.stringify(data.config, null, 2)
      }
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }
})

function addKeyword() {
  const kw = keywordInput.value.trim()
  if (kw && !form.value.keywords.includes(kw)) {
    form.value.keywords.push(kw)
  }
  keywordInput.value = ''
}

function removeKeyword(index) {
  form.value.keywords.splice(index, 1)
}

async function handleSubmit() {
  saving.value = true
  error.value = null
  try {
    if (configInput.value.trim()) {
      form.value.config = JSON.parse(configInput.value)
    } else {
      form.value.config = null
    }
  } catch {
    error.value = 'Ungültiges JSON in Config'
    saving.value = false
    return
  }

  try {
    if (isEdit.value) {
      await store.editSource(Number(route.params.id), form.value)
    } else {
      await store.addSource(form.value)
    }
    router.push('/research')
  } catch (err) {
    error.value = err.message
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="mx-auto max-w-2xl px-4 py-8 sm:px-6 lg:px-8">
    <h1 class="text-2xl font-bold text-go4-secondary">
      {{ isEdit ? 'Quelle bearbeiten' : 'Neue Quelle' }}
    </h1>

    <div v-if="loading" class="mt-8 text-center text-go4-muted">Laden...</div>

    <div v-else-if="error" class="mt-4 rounded-lg bg-red-50 p-4 text-sm text-red-700">
      {{ error }}
    </div>

    <form v-if="!loading" class="mt-6 space-y-6" @submit.prevent="handleSubmit">
      <!-- Name -->
      <div>
        <label class="block text-sm font-medium text-go4-secondary">Name</label>
        <input
          v-model="form.name"
          type="text"
          required
          class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
          placeholder="z.B. PV Magazine RSS"
        />
      </div>

      <!-- URL -->
      <div>
        <label class="block text-sm font-medium text-go4-secondary">URL</label>
        <input
          v-model="form.url"
          type="url"
          required
          class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
          placeholder="https://www.pv-magazine.de/feed/"
        />
      </div>

      <!-- Source Type -->
      <div>
        <label class="block text-sm font-medium text-go4-secondary">Typ</label>
        <select
          v-model="form.source_type"
          class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
        >
          <option value="rss">RSS Feed</option>
          <option value="website">Website</option>
          <option value="websearch">Websuche</option>
        </select>
      </div>

      <!-- Keywords -->
      <div>
        <label class="block text-sm font-medium text-go4-secondary">Keywords</label>
        <div class="mt-1 flex gap-2">
          <input
            v-model="keywordInput"
            type="text"
            class="block flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
            placeholder="Keyword eingeben..."
            @keydown.enter.prevent="addKeyword"
          />
          <button
            type="button"
            class="rounded-lg bg-gray-100 px-4 py-2 text-sm font-medium text-go4-secondary hover:bg-gray-200"
            @click="addKeyword"
          >
            +
          </button>
        </div>
        <div class="mt-2 flex flex-wrap gap-2">
          <span
            v-for="(kw, i) in form.keywords"
            :key="i"
            class="inline-flex items-center gap-1 rounded-full bg-go4-primary/10 px-3 py-1 text-sm text-go4-primary"
          >
            {{ kw }}
            <button
              type="button"
              class="text-go4-primary/60 hover:text-go4-primary"
              @click="removeKeyword(i)"
            >
              x
            </button>
          </span>
        </div>
      </div>

      <!-- Interval -->
      <div>
        <label class="block text-sm font-medium text-go4-secondary">
          Abruf-Intervall (Stunden)
        </label>
        <input
          v-model.number="form.fetch_interval_hours"
          type="number"
          min="1"
          max="168"
          class="mt-1 block w-32 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
        />
      </div>

      <!-- Config (optional) -->
      <div>
        <label class="block text-sm font-medium text-go4-secondary">
          Config (optional, JSON)
        </label>
        <textarea
          v-model="configInput"
          rows="4"
          class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
          placeholder='{"selector": ".article-list article"}'
        />
      </div>

      <!-- Actions -->
      <div class="flex gap-3">
        <button
          type="submit"
          :disabled="saving"
          class="rounded-lg bg-go4-primary px-6 py-2 text-sm font-medium text-white transition hover:bg-go4-primary/90 disabled:opacity-50"
        >
          {{ saving ? 'Speichern...' : 'Speichern' }}
        </button>
        <router-link
          to="/research"
          class="rounded-lg border border-gray-300 px-6 py-2 text-sm font-medium text-go4-secondary hover:bg-gray-50"
        >
          Abbrechen
        </router-link>
      </div>
    </form>
  </div>
</template>
