<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCollectorStore } from '@/stores/collector'
import PageHeader from '@/components/ui/PageHeader.vue'
import TagSelector from '@/components/ui/TagSelector.vue'
import StreamSelector from '@/components/ui/StreamSelector.vue'

const route = useRoute()
const router = useRouter()
const store = useCollectorStore()

const loading = ref(false)
const error = ref(null)
const saving = ref(false)
const deleting = ref(false)
const savedSnapshot = ref('')

const isEdit = computed(() => !!route.params.id)
const needsUrl = computed(() => ['rss', 'website'].includes(form.value.source_type))

const form = ref({
  name: '',
  url: '',
  source_type: 'rss',
  keywords: [],
  fetch_interval_hours: 24,
  config: null,
  tags: [],
  streams: [],
  group_id: store.activeGroupId
})

const keywordInput = ref('')
const configInput = ref('')

const isDirty = computed(() => {
  if (!isEdit.value) return true
  return JSON.stringify({ ...form.value, _cfg: configInput.value }) !== savedSnapshot.value
})

function takeSnapshot() {
  savedSnapshot.value = JSON.stringify({ ...form.value, _cfg: configInput.value })
}

// --- Source Navigation ---

const currentIndex = computed(() => {
  if (!isEdit.value) return -1
  const id = Number(route.params.id)
  return store.sources.findIndex((s) => s.id === id)
})

const prevSource = computed(() => {
  if (currentIndex.value <= 0) return null
  return store.sources[currentIndex.value - 1]
})

const nextSource = computed(() => {
  if (currentIndex.value < 0 || currentIndex.value >= store.sources.length - 1) return null
  return store.sources[currentIndex.value + 1]
})

// --- Load Source ---

async function loadSource(id) {
  loading.value = true
  error.value = null
  configInput.value = ''
  try {
    const data = await store.fetchSource(id)
    form.value = {
      name: data.name,
      url: data.url || '',
      source_type: data.source_type,
      keywords: data.keywords || [],
      fetch_interval_hours: data.fetch_interval_hours,
      config: data.config,
      tags: data.tags || [],
      streams: data.streams || [],
      group_id: data.group_id
    }
    if (data.config) {
      configInput.value = JSON.stringify(data.config, null, 2)
    }
    takeSnapshot()
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  if (store.groups.length === 0) {
    await store.fetchGroups()
  }
  if (store.sources.length === 0) {
    await store.fetchSources()
  }
  if (isEdit.value) {
    await loadSource(Number(route.params.id))
  }
})

watch(
  () => route.params.id,
  async (newId) => {
    if (newId) {
      await loadSource(Number(newId))
    }
  }
)

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
    error.value = 'Ungueltiges JSON in Config'
    saving.value = false
    return
  }

  try {
    if (isEdit.value) {
      await store.editSource(Number(route.params.id), form.value)
      takeSnapshot()
    } else {
      const created = await store.addSource(form.value)
      router.push(`/collector/sources/${created.id}`)
    }
  } catch (err) {
    error.value = err.message
  } finally {
    saving.value = false
  }
}

function resetForm() {
  if (!savedSnapshot.value) return
  const saved = JSON.parse(savedSnapshot.value)
  const { _cfg, ...formData } = saved
  form.value = formData
  configInput.value = _cfg || ''
}

async function handleDelete() {
  if (!confirm('Quelle wirklich loeschen?')) return
  deleting.value = true
  try {
    await store.removeSource(Number(route.params.id))
    router.push('/collector')
  } catch (err) {
    error.value = err.message
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <div>
    <PageHeader :title="isEdit ? 'Quelle bearbeiten' : 'Neue Quelle'">
      <template
        v-if="isEdit && store.sources.length > 1"
        #actions
      >
        <div class="flex items-center gap-1">
          <button
            :disabled="!prevSource"
            class="rounded-lg border border-gray-300 dark:border-gray-600 p-2 text-go4-secondary dark:text-gray-100 transition hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-30 disabled:cursor-not-allowed"
            title="Vorherige Quelle"
            @click="router.push(`/collector/sources/${prevSource.id}`)"
          >
            <svg
              class="h-4 w-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M15 19l-7-7 7-7"
              />
            </svg>
          </button>
          <span class="px-2 text-xs text-go4-muted dark:text-gray-400">
            {{ currentIndex + 1 }} / {{ store.sources.length }}
          </span>
          <button
            :disabled="!nextSource"
            class="rounded-lg border border-gray-300 dark:border-gray-600 p-2 text-go4-secondary dark:text-gray-100 transition hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-30 disabled:cursor-not-allowed"
            title="Naechste Quelle"
            @click="router.push(`/collector/sources/${nextSource.id}`)"
          >
            <svg
              class="h-4 w-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M9 5l7 7-7 7"
              />
            </svg>
          </button>
        </div>
      </template>
    </PageHeader>

    <div
      v-if="loading"
      class="mt-8 text-center text-go4-muted dark:text-gray-400"
    >
      Laden...
    </div>

    <div
      v-else-if="error"
      class="mt-4 rounded-lg bg-red-50 dark:bg-red-900/20 p-4 text-sm text-red-700 dark:text-red-400"
    >
      {{ error }}
    </div>

    <form
      v-if="!loading"
      class="mt-6 space-y-6"
      @submit.prevent="handleSubmit"
    >
      <div>
        <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">Name</label>
        <input
          v-model="form.name"
          type="text"
          required
          class="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm dark:bg-gray-700 dark:text-gray-100 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
          placeholder="z.B. PV Magazine RSS"
        >
      </div>

      <div>
        <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">Typ</label>
        <select
          v-model="form.source_type"
          class="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm dark:bg-gray-700 dark:text-gray-100 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
        >
          <option value="rss">
            RSS Feed
          </option>
          <option value="website">
            Website
          </option>
          <option value="websearch">
            Websuche
          </option>
          <option value="inbox">
            Inbox
          </option>
        </select>
      </div>

      <div v-if="needsUrl">
        <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">URL</label>
        <input
          v-model="form.url"
          type="url"
          required
          class="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm dark:bg-gray-700 dark:text-gray-100 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
          placeholder="https://www.pv-magazine.de/feed/"
        >
      </div>

      <div>
        <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">
          Keywords
        </label>
        <p
          v-if="form.source_type === 'websearch'"
          class="mt-0.5 text-xs text-go4-muted dark:text-gray-400"
        >
          Suchbegriffe fuer die Google-Websuche. Mindestens ein Keyword angeben.
        </p>
        <div class="mt-1 flex gap-2">
          <input
            v-model="keywordInput"
            type="text"
            class="block flex-1 rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm dark:bg-gray-700 dark:text-gray-100 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
            placeholder="Keyword eingeben..."
            @keydown.enter.prevent="addKeyword"
          >
          <button
            type="button"
            class="rounded-lg bg-gray-100 dark:bg-gray-700 px-4 py-2 text-sm font-medium text-go4-secondary dark:text-gray-100 hover:bg-gray-200 dark:hover:bg-gray-600"
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

      <div>
        <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">
          Abruf-Intervall (Stunden)
        </label>
        <input
          v-model.number="form.fetch_interval_hours"
          type="number"
          min="1"
          max="168"
          class="mt-1 block w-32 rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm dark:bg-gray-700 dark:text-gray-100 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
        >
      </div>

      <div>
        <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">Tags</label>
        <div class="mt-1">
          <TagSelector
            v-model="form.tags"
            placeholder="Tags auswaehlen..."
          />
        </div>
      </div>

      <div>
        <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">Streams</label>
        <div class="mt-1">
          <StreamSelector
            v-model="form.streams"
            placeholder="Streams auswaehlen..."
          />
        </div>
      </div>

      <div>
        <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">Gruppe</label>
        <select
          v-model="form.group_id"
          class="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm dark:bg-gray-700 dark:text-gray-100 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
        >
          <option
            v-for="g in store.groups"
            :key="g.id"
            :value="g.id"
          >
            {{ g.name }}
          </option>
        </select>
      </div>

      <div>
        <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">
          Config (optional, JSON)
        </label>
        <textarea
          v-model="configInput"
          rows="4"
          class="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 font-mono text-sm dark:bg-gray-700 dark:text-gray-100 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
          placeholder="{&quot;selector&quot;: &quot;.article-list article&quot;}"
        />
      </div>

      <div class="flex items-center gap-3">
        <button
          v-if="isDirty"
          type="submit"
          :disabled="saving"
          class="rounded-lg bg-go4-primary px-6 py-2 text-sm font-medium text-white transition hover:bg-go4-primary/90 disabled:opacity-50"
        >
          {{ saving ? 'Speichern...' : 'Speichern' }}
        </button>
        <button
          v-if="isDirty && isEdit"
          type="button"
          class="rounded-lg border border-gray-300 dark:border-gray-600 px-6 py-2 text-sm font-medium text-go4-secondary dark:text-gray-100 hover:bg-gray-50 dark:hover:bg-gray-700"
          @click="resetForm"
        >
          Abbrechen
        </button>
        <router-link
          v-if="isDirty && !isEdit"
          to="/collector"
          class="rounded-lg border border-gray-300 dark:border-gray-600 px-6 py-2 text-sm font-medium text-go4-secondary dark:text-gray-100 hover:bg-gray-50 dark:hover:bg-gray-700"
        >
          Abbrechen
        </router-link>
        <button
          v-if="isEdit"
          type="button"
          :disabled="deleting"
          class="ml-auto rounded-lg bg-red-100 dark:bg-red-900/20 px-6 py-2 text-sm font-medium text-red-700 dark:text-red-400 transition hover:bg-red-200 dark:hover:bg-red-900/40 disabled:opacity-50"
          @click="handleDelete"
        >
          {{ deleting ? 'Loeschen...' : 'Loeschen' }}
        </button>
      </div>
    </form>
  </div>
</template>
