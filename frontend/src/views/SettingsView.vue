<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSettingsStore } from '@/stores/settings'
import { usePromptStore } from '@/stores/prompts'
import { useAuthStore } from '@/stores/auth'
import { changePassword } from '@/api/auth'
import PageHeader from '@/components/ui/PageHeader.vue'
import SettingsGlobalTab from '@/components/settings/SettingsGlobalTab.vue'
import SettingsModuleTab from '@/components/settings/SettingsModuleTab.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import api from '@/api'

const route = useRoute()
const router = useRouter()
const store = useSettingsStore()
const promptStore = usePromptStore()
const authStore = useAuthStore()

const isPromptsTab = computed(() => route.name === 'settings-prompts')

// --- Password Change ---
const passwordForm = ref({
  currentPassword: '',
  newPassword: '',
  confirmPassword: ''
})
const passwordSaving = ref(false)
const passwordError = ref(null)
const passwordSuccess = ref(false)

async function handlePasswordChange() {
  passwordError.value = null
  passwordSuccess.value = false

  if (passwordForm.value.newPassword !== passwordForm.value.confirmPassword) {
    passwordError.value = 'Passwoerter stimmen nicht ueberein'
    return
  }
  if (passwordForm.value.newPassword.length < 6) {
    passwordError.value = 'Passwort muss mindestens 6 Zeichen haben'
    return
  }

  passwordSaving.value = true
  try {
    await changePassword({
      current_password: passwordForm.value.currentPassword,
      new_password: passwordForm.value.newPassword
    })
    passwordSuccess.value = true
    passwordForm.value = { currentPassword: '', newPassword: '', confirmPassword: '' }
  } catch (err) {
    passwordError.value = err.response?.data?.detail || err.message
  } finally {
    passwordSaving.value = false
  }
}

// --- Tag Management ---
const tags = ref([])
const tagsLoading = ref(false)
const tagsError = ref(null)
const tagForm = ref({ label: '', color: '#6B7280', icon: '' })
const editingTagId = ref(null)
const tagSaving = ref(false)

// --- Stream Management ---
const streams = ref([])
const streamsLoading = ref(false)
const streamsError = ref(null)
const streamForm = ref({ label: '', description: '', color: '#3B82F6', icon: '', active: true })
const editingStreamId = ref(null)
const streamSaving = ref(false)

async function fetchTags() {
  tagsLoading.value = true
  tagsError.value = null
  try {
    const { data } = await api.get('/v1/tags/')
    tags.value = data
  } catch (err) {
    tagsError.value = err.message
  } finally {
    tagsLoading.value = false
  }
}

function startEditTag(tag) {
  editingTagId.value = tag.id
  tagForm.value = { label: tag.label, color: tag.color, icon: tag.icon || '' }
}

function cancelEditTag() {
  editingTagId.value = null
  tagForm.value = { label: '', color: '#6B7280', icon: '' }
}

async function saveTag() {
  tagSaving.value = true
  tagsError.value = null
  try {
    if (editingTagId.value) {
      await api.put(`/v1/tags/${editingTagId.value}`, {
        label: tagForm.value.label,
        color: tagForm.value.color,
        icon: tagForm.value.icon || null
      })
    } else {
      await api.post('/v1/tags/', {
        label: tagForm.value.label,
        color: tagForm.value.color,
        icon: tagForm.value.icon || null
      })
    }
    tagForm.value = { label: '', color: '#6B7280', icon: '' }
    editingTagId.value = null
    await fetchTags()
  } catch (err) {
    tagsError.value = err.message
  } finally {
    tagSaving.value = false
  }
}

async function deleteTag(tagId) {
  tagsError.value = null
  try {
    await api.delete(`/v1/tags/${tagId}`)
    await fetchTags()
  } catch (err) {
    tagsError.value = err.message
  }
}

// --- Stream CRUD ---

async function fetchStreams() {
  streamsLoading.value = true
  streamsError.value = null
  try {
    const { data } = await api.get('/v1/streams/')
    streams.value = data
  } catch (err) {
    streamsError.value = err.message
  } finally {
    streamsLoading.value = false
  }
}

function startEditStream(stream) {
  editingStreamId.value = stream.id
  streamForm.value = {
    label: stream.label,
    description: stream.description || '',
    color: stream.color,
    icon: stream.icon || '',
    active: stream.active
  }
}

function cancelEditStream() {
  editingStreamId.value = null
  streamForm.value = { label: '', description: '', color: '#3B82F6', icon: '', active: true }
}

async function saveStream() {
  streamSaving.value = true
  streamsError.value = null
  try {
    if (editingStreamId.value) {
      await api.put(`/v1/streams/${editingStreamId.value}`, {
        label: streamForm.value.label,
        description: streamForm.value.description || null,
        color: streamForm.value.color,
        icon: streamForm.value.icon || null,
        active: streamForm.value.active
      })
    } else {
      await api.post('/v1/streams/', {
        label: streamForm.value.label,
        description: streamForm.value.description || null,
        color: streamForm.value.color,
        icon: streamForm.value.icon || null,
        active: streamForm.value.active
      })
    }
    streamForm.value = { label: '', description: '', color: '#3B82F6', icon: '', active: true }
    editingStreamId.value = null
    await fetchStreams()
  } catch (err) {
    streamsError.value = err.message
  } finally {
    streamSaving.value = false
  }
}

async function deleteStream(streamId) {
  streamsError.value = null
  try {
    await api.delete(`/v1/streams/${streamId}`)
    await fetchStreams()
  } catch (err) {
    streamsError.value = err.message
  }
}

const categoryColors = {
  content: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  analysis: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  email: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  general: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
  chat: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400',
  research: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400'
}

function getCategoryColor(category) {
  return categoryColors[category] || categoryColors.general
}

const isTagsTab = computed(() => store.activeTab === 'tags')
const isStreamsTab = computed(() => store.activeTab === 'streams')

const activeTabKey = computed(() => {
  if (isPromptsTab.value) return 'prompts'
  return store.activeTab
})

const allTabs = computed(() => {
  const list = store.tabs
  return [
    { key: 'profil', label: 'Profil' },
    ...list,
    { key: 'tags', label: 'Tags' },
    { key: 'streams', label: 'Streams' },
    { key: 'prompts', label: 'Prompts' },
    { key: 'desktop-layout', label: 'Desktop Layout' }
  ]
})

onMounted(async () => {
  await store.fetchModules()
  if (isPromptsTab.value) {
    promptStore.fetchPrompts({})
  } else if (store.activeTab === 'tags') {
    fetchTags()
  } else if (store.activeTab === 'streams') {
    fetchStreams()
  } else {
    await store.fetchTabData(store.activeTab)
  }
})

watch(
  () => store.activeTab,
  (tab) => {
    if (tab !== 'prompts' && tab !== 'tags' && tab !== 'streams' && tab !== 'profil') {
      store.fetchTabData(tab)
    }
  }
)

function switchTab(key) {
  if (key === 'prompts') {
    router.push('/settings/prompts')
    promptStore.fetchPrompts({})
  } else if (key === 'desktop-layout') {
    router.push('/settings/desktop-layout')
  } else if (key === 'profil') {
    if (isPromptsTab.value) {
      router.push('/settings')
    }
    store.setActiveTab(key)
    // Reset password form when switching to profile
    passwordForm.value = { currentPassword: '', newPassword: '', confirmPassword: '' }
    passwordError.value = null
    passwordSuccess.value = false
  } else if (key === 'tags') {
    if (isPromptsTab.value) {
      router.push('/settings')
    }
    store.setActiveTab(key)
    fetchTags()
  } else if (key === 'streams') {
    if (isPromptsTab.value) {
      router.push('/settings')
    }
    store.setActiveTab(key)
    fetchStreams()
  } else {
    if (isPromptsTab.value) {
      router.push('/settings')
    }
    store.setActiveTab(key)
  }
}

function onSaveModule(updates) {
  store.saveModuleConfig(store.activeTab, updates)
}

function onSaveGlobal(updates) {
  store.saveGlobalSettings(updates)
}

function goToPromptEditor(promptId) {
  router.push(`/settings/prompts/${promptId}`)
}

function goToNewPrompt() {
  router.push('/settings/prompts/new')
}
</script>

<template>
  <div class="space-y-6">
    <PageHeader
      title="Einstellungen"
      subtitle="Plattform- und Modul-Konfiguration verwalten"
    />

    <!-- Success Toast -->
    <div
      v-if="store.saveSuccess"
      class="rounded-lg bg-green-50 p-3 text-sm font-medium text-green-800 dark:bg-green-900/20 dark:text-green-400"
    >
      Einstellungen gespeichert.
    </div>

    <!-- Error Toast -->
    <div
      v-if="store.error"
      class="rounded-lg bg-red-50 p-3 text-sm font-medium text-red-800 dark:bg-red-900/20 dark:text-red-400"
    >
      {{ store.error }}
    </div>

    <!-- Tab Bar -->
    <div class="border-b border-gray-200 dark:border-gray-700">
      <nav class="-mb-px flex space-x-6 overflow-x-auto">
        <button
          v-for="tab in allTabs"
          :key="tab.key"
          :class="[
            'whitespace-nowrap border-b-2 px-1 py-3 text-sm font-medium transition',
            activeTabKey === tab.key
              ? 'border-go4-primary text-go4-primary'
              : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 dark:text-gray-400 dark:hover:border-gray-600 dark:hover:text-gray-300'
          ]"
          @click="switchTab(tab.key)"
        >
          {{ tab.label }}
        </button>
      </nav>
    </div>

    <!-- Loading -->
    <div
      v-if="store.loading && !isPromptsTab && !isTagsTab && !isStreamsTab"
      class="flex items-center justify-center p-12"
    >
      <span class="text-sm text-gray-500 dark:text-gray-400">Laden...</span>
    </div>

    <!-- Tab Content -->
    <div v-else>
      <!-- Profil Tab -->
      <div
        v-if="activeTabKey === 'profil'"
        class="space-y-6"
      >
        <!-- User Info -->
        <div class="rounded-lg bg-white p-6 shadow-sm dark:bg-gray-800">
          <h3 class="mb-4 text-lg font-semibold text-go4-secondary dark:text-white">
            Mein Profil
          </h3>
          <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label class="block text-sm font-medium text-gray-500 dark:text-gray-400">Name</label>
              <p class="mt-1 text-sm text-go4-secondary dark:text-white">
                {{ authStore.user?.display_name || '-' }}
              </p>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-500 dark:text-gray-400">E-Mail</label>
              <p class="mt-1 text-sm text-go4-secondary dark:text-white">
                {{ authStore.user?.email || '-' }}
              </p>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-500 dark:text-gray-400">Rolle</label>
              <p class="mt-1 text-sm text-go4-secondary dark:text-white">
                {{ authStore.user?.role || '-' }}
              </p>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-500 dark:text-gray-400">Letzter Login</label>
              <p class="mt-1 text-sm text-go4-secondary dark:text-white">
                {{
                  authStore.user?.last_login_at
                    ? new Date(authStore.user.last_login_at).toLocaleString('de-DE')
                    : '-'
                }}
              </p>
            </div>
          </div>
        </div>

        <!-- Password Change -->
        <div class="rounded-lg bg-white p-6 shadow-sm dark:bg-gray-800">
          <h3 class="mb-4 text-lg font-semibold text-go4-secondary dark:text-white">
            Passwort aendern
          </h3>

          <div
            v-if="passwordSuccess"
            class="mb-4 rounded-lg bg-green-50 p-3 text-sm text-green-700 dark:bg-green-900/30 dark:text-green-400"
          >
            Passwort erfolgreich geaendert!
          </div>

          <div
            v-if="passwordError"
            class="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-400"
          >
            {{ passwordError }}
          </div>

          <form
            class="max-w-md space-y-4"
            @submit.prevent="handlePasswordChange"
          >
            <div>
              <label class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                Aktuelles Passwort
              </label>
              <input
                v-model="passwordForm.currentPassword"
                type="password"
                required
                autocomplete="current-password"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
            </div>

            <div>
              <label class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                Neues Passwort
              </label>
              <input
                v-model="passwordForm.newPassword"
                type="password"
                required
                minlength="6"
                autocomplete="new-password"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
            </div>

            <div>
              <label class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                Passwort bestaetigen
              </label>
              <input
                v-model="passwordForm.confirmPassword"
                type="password"
                required
                autocomplete="new-password"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
            </div>

            <div class="pt-2">
              <button
                type="submit"
                :disabled="passwordSaving"
                class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary/90 disabled:opacity-50"
              >
                {{ passwordSaving ? 'Speichern...' : 'Passwort aendern' }}
              </button>
            </div>
          </form>
        </div>
      </div>

      <!-- Global Tab -->
      <SettingsGlobalTab
        v-else-if="activeTabKey === 'global'"
        :schema="store.globalSchema"
        :config="store.globalConfig"
        :saving="store.saving"
        @save="onSaveGlobal"
      />

      <!-- Tags Tab -->
      <div
        v-else-if="activeTabKey === 'tags'"
        class="space-y-6"
      >
        <div class="flex items-center justify-between">
          <p class="text-sm text-gray-500 dark:text-gray-400">
            Tags definieren das Routing zwischen Quellen und Ausgabe-Kanaelen.
          </p>
        </div>

        <div
          v-if="tagsError"
          class="rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-400"
        >
          {{ tagsError }}
        </div>

        <!-- Tag Form -->
        <div class="rounded-lg bg-white p-4 shadow-sm dark:bg-gray-800">
          <h3 class="mb-3 text-sm font-semibold text-go4-secondary dark:text-gray-100">
            {{ editingTagId ? 'Tag bearbeiten' : 'Neuer Tag' }}
          </h3>
          <form
            class="flex flex-wrap items-end gap-3"
            @submit.prevent="saveTag"
          >
            <div class="flex-1">
              <label class="block text-xs font-medium text-gray-500 dark:text-gray-400">Label</label>
              <input
                v-model="tagForm.label"
                type="text"
                required
                class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"
                placeholder="z.B. Solar, Speicher, Wettbewerb"
              >
            </div>
            <div class="w-24">
              <label class="block text-xs font-medium text-gray-500 dark:text-gray-400">Farbe</label>
              <input
                v-model="tagForm.color"
                type="color"
                class="mt-1 block h-[38px] w-full cursor-pointer rounded-lg border border-gray-300 dark:border-gray-600"
              >
            </div>
            <div class="w-32">
              <label class="block text-xs font-medium text-gray-500 dark:text-gray-400">Icon</label>
              <input
                v-model="tagForm.icon"
                type="text"
                class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"
                placeholder="tag"
              >
            </div>
            <button
              type="submit"
              :disabled="tagSaving || !tagForm.label.trim()"
              class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white transition hover:bg-go4-primary/90 disabled:opacity-50"
            >
              {{ tagSaving ? 'Speichern...' : editingTagId ? 'Aktualisieren' : 'Erstellen' }}
            </button>
            <button
              v-if="editingTagId"
              type="button"
              class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-600 dark:border-gray-600 dark:text-gray-300"
              @click="cancelEditTag"
            >
              Abbrechen
            </button>
          </form>
        </div>

        <!-- Tags List -->
        <div
          v-if="tagsLoading"
          class="flex items-center justify-center p-8"
        >
          <span class="text-sm text-gray-500 dark:text-gray-400">Laden...</span>
        </div>

        <EmptyState
          v-else-if="tags.length === 0"
          title="Noch keine Tags erstellt"
        />

        <div
          v-else
          class="overflow-hidden rounded-lg bg-white shadow-sm dark:bg-gray-800"
        >
          <table class="w-full text-left text-sm">
            <thead
              class="border-b border-gray-100 bg-gray-50 text-xs uppercase tracking-wider text-go4-muted dark:border-gray-700 dark:bg-gray-800/50 dark:text-gray-400"
            >
              <tr>
                <th class="px-4 py-3 font-medium">
                  Tag
                </th>
                <th class="px-4 py-3 font-medium">
                  Slug
                </th>
                <th class="hidden px-4 py-3 font-medium md:table-cell">
                  Icon
                </th>
                <th class="px-4 py-3 text-right font-medium">
                  Aktionen
                </th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-50 dark:divide-gray-700">
              <tr
                v-for="tag in tags"
                :key="tag.id"
                class="hover:bg-gray-50/50 dark:hover:bg-gray-700/50"
              >
                <td class="px-4 py-3">
                  <span
                    class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium text-white"
                    :style="{ backgroundColor: tag.color }"
                  >
                    {{ tag.label }}
                  </span>
                </td>
                <td class="px-4 py-3 font-mono text-xs text-gray-500 dark:text-gray-400">
                  {{ tag.slug }}
                </td>
                <td class="hidden px-4 py-3 text-xs text-gray-400 dark:text-gray-500 md:table-cell">
                  {{ tag.icon || '-' }}
                </td>
                <td class="px-4 py-3">
                  <div class="flex items-center justify-end gap-1.5">
                    <button
                      class="rounded bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
                      @click="startEditTag(tag)"
                    >
                      Bearbeiten
                    </button>
                    <button
                      class="rounded bg-red-100 px-2.5 py-1 text-xs font-medium text-red-700 hover:bg-red-200 dark:bg-red-900/20 dark:text-red-400"
                      @click="deleteTag(tag.id)"
                    >
                      Loeschen
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Streams Tab -->
      <div
        v-else-if="activeTabKey === 'streams'"
        class="space-y-6"
      >
        <div class="flex items-center justify-between">
          <p class="text-sm text-gray-500 dark:text-gray-400">
            Streams definieren Informationsfluesse zwischen Modulen (z.B. Collector → Briefing).
          </p>
        </div>

        <div
          v-if="streamsError"
          class="rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-400"
        >
          {{ streamsError }}
        </div>

        <!-- Stream Form -->
        <div class="rounded-lg bg-white p-4 shadow-sm dark:bg-gray-800">
          <h3 class="mb-3 text-sm font-semibold text-go4-secondary dark:text-gray-100">
            {{ editingStreamId ? 'Stream bearbeiten' : 'Neuer Stream' }}
          </h3>
          <form
            class="flex flex-wrap items-end gap-3"
            @submit.prevent="saveStream"
          >
            <div class="flex-1">
              <label class="block text-xs font-medium text-gray-500 dark:text-gray-400">Label</label>
              <input
                v-model="streamForm.label"
                type="text"
                required
                class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"
                placeholder="z.B. Wettbewerber-Monitoring, Management-Briefing"
              >
            </div>
            <div class="flex-1">
              <label class="block text-xs font-medium text-gray-500 dark:text-gray-400">Beschreibung</label>
              <input
                v-model="streamForm.description"
                type="text"
                class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"
                placeholder="Wofuer wird dieser Stream verwendet?"
              >
            </div>
            <div class="w-24">
              <label class="block text-xs font-medium text-gray-500 dark:text-gray-400">Farbe</label>
              <input
                v-model="streamForm.color"
                type="color"
                class="mt-1 block h-[38px] w-full cursor-pointer rounded-lg border border-gray-300 dark:border-gray-600"
              >
            </div>
            <div class="w-32">
              <label class="block text-xs font-medium text-gray-500 dark:text-gray-400">Icon</label>
              <input
                v-model="streamForm.icon"
                type="text"
                class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"
                placeholder="stream"
              >
            </div>
            <label
              v-if="editingStreamId"
              class="flex items-center gap-2"
            >
              <input
                v-model="streamForm.active"
                type="checkbox"
                class="h-4 w-4 rounded border-gray-300 text-go4-primary focus:ring-go4-primary dark:border-gray-600"
              >
              <span class="text-xs text-gray-500 dark:text-gray-400">Aktiv</span>
            </label>
            <button
              type="submit"
              :disabled="streamSaving || !streamForm.label.trim()"
              class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white transition hover:bg-go4-primary/90 disabled:opacity-50"
            >
              {{ streamSaving ? 'Speichern...' : editingStreamId ? 'Aktualisieren' : 'Erstellen' }}
            </button>
            <button
              v-if="editingStreamId"
              type="button"
              class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-600 dark:border-gray-600 dark:text-gray-300"
              @click="cancelEditStream"
            >
              Abbrechen
            </button>
          </form>
        </div>

        <!-- Streams List -->
        <div
          v-if="streamsLoading"
          class="flex items-center justify-center p-8"
        >
          <span class="text-sm text-gray-500 dark:text-gray-400">Laden...</span>
        </div>

        <EmptyState
          v-else-if="streams.length === 0"
          title="Noch keine Streams erstellt"
        />

        <div
          v-else
          class="overflow-hidden rounded-lg bg-white shadow-sm dark:bg-gray-800"
        >
          <table class="w-full text-left text-sm">
            <thead
              class="border-b border-gray-100 bg-gray-50 text-xs uppercase tracking-wider text-go4-muted dark:border-gray-700 dark:bg-gray-800/50 dark:text-gray-400"
            >
              <tr>
                <th class="px-4 py-3 font-medium">
                  Stream
                </th>
                <th class="px-4 py-3 font-medium">
                  Slug
                </th>
                <th class="hidden px-4 py-3 font-medium md:table-cell">
                  Beschreibung
                </th>
                <th class="px-4 py-3 font-medium">
                  Aktiv
                </th>
                <th class="px-4 py-3 text-right font-medium">
                  Aktionen
                </th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-50 dark:divide-gray-700">
              <tr
                v-for="stream in streams"
                :key="stream.id"
                class="hover:bg-gray-50/50 dark:hover:bg-gray-700/50"
              >
                <td class="px-4 py-3">
                  <span
                    class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium text-white"
                    :style="{ backgroundColor: stream.color }"
                  >
                    {{ stream.label }}
                  </span>
                </td>
                <td class="px-4 py-3 font-mono text-xs text-gray-500 dark:text-gray-400">
                  {{ stream.slug }}
                </td>
                <td class="hidden px-4 py-3 text-xs text-gray-400 dark:text-gray-500 md:table-cell">
                  {{ stream.description || '-' }}
                </td>
                <td class="px-4 py-3">
                  <span
                    :class="[
                      'inline-block h-2 w-2 rounded-full',
                      stream.active ? 'bg-green-400' : 'bg-gray-300 dark:bg-gray-600'
                    ]"
                  />
                </td>
                <td class="px-4 py-3">
                  <div class="flex items-center justify-end gap-1.5">
                    <button
                      class="rounded bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
                      @click="startEditStream(stream)"
                    >
                      Bearbeiten
                    </button>
                    <button
                      class="rounded bg-red-100 px-2.5 py-1 text-xs font-medium text-red-700 hover:bg-red-200 dark:bg-red-900/20 dark:text-red-400"
                      @click="deleteStream(stream.id)"
                    >
                      Loeschen
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Prompts Tab -->
      <div v-else-if="activeTabKey === 'prompts'">
        <!-- Prompts Header -->
        <div class="mb-6 flex items-center justify-between">
          <p class="text-sm text-gray-500 dark:text-gray-400">
            KI-Prompts verwalten und testen
          </p>
          <button
            class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white transition hover:bg-go4-primary/90"
            @click="goToNewPrompt"
          >
            + Neuer Prompt
          </button>
        </div>

        <!-- Loading -->
        <div
          v-if="promptStore.loading"
          class="flex items-center justify-center p-8"
        >
          <span class="text-sm text-gray-500 dark:text-gray-400">Laden...</span>
        </div>

        <!-- Error -->
        <div
          v-else-if="promptStore.error"
          class="rounded-lg bg-red-50 p-4 text-red-700 dark:bg-red-900/20 dark:text-red-400"
        >
          {{ promptStore.error }}
        </div>

        <!-- Empty -->
        <EmptyState
          v-else-if="promptStore.prompts.length === 0"
          title="Keine Prompts gefunden"
        >
          <template #action>
            <button
              class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white transition hover:bg-go4-primary/90"
              @click="goToNewPrompt"
            >
              Ersten Prompt erstellen
            </button>
          </template>
        </EmptyState>

        <!-- Grid -->
        <div
          v-else
          class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3"
        >
          <div
            v-for="prompt in promptStore.prompts"
            :key="prompt.id"
            class="cursor-pointer rounded-lg bg-white p-5 shadow-sm transition hover:shadow-md dark:bg-gray-800 dark:hover:bg-gray-750"
            @click="goToPromptEditor(prompt.id)"
          >
            <div class="flex items-start justify-between">
              <div class="min-w-0 flex-1">
                <h3 class="truncate text-sm font-semibold text-go4-secondary dark:text-gray-100">
                  {{ prompt.name }}
                </h3>
                <p class="mt-0.5 font-mono text-xs text-go4-muted dark:text-gray-500">
                  {{ prompt.slug }}
                </p>
              </div>
              <span
                :class="[
                  'ml-2 inline-flex shrink-0 rounded-full px-2 py-0.5 text-xs font-medium',
                  getCategoryColor(prompt.category)
                ]"
              >
                {{ prompt.category }}
              </span>
            </div>
            <p
              v-if="prompt.description"
              class="mt-2 line-clamp-2 text-xs text-go4-muted dark:text-gray-400"
            >
              {{ prompt.description }}
            </p>
            <div
              class="mt-3 flex items-center justify-between text-xs text-go4-muted dark:text-gray-500"
            >
              <span>{{ prompt.provider }} / {{ prompt.model }}</span>
              <div class="flex items-center gap-2">
                <span>v{{ prompt.version }}</span>
                <span
                  :class="[
                    'inline-block h-2 w-2 rounded-full',
                    prompt.is_active ? 'bg-green-400' : 'bg-gray-300 dark:bg-gray-600'
                  ]"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Module Tab -->
      <SettingsModuleTab
        v-else
        :module-name="store.activeTab"
        :schema="store.schemas[store.activeTab] || []"
        :config="store.configs[store.activeTab] || {}"
        :status="store.statuses[store.activeTab] || {}"
        :saving="store.saving"
        @save="onSaveModule"
      />
    </div>
  </div>
</template>
