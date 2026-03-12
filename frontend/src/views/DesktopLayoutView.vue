<script setup>
import { ref, computed, onMounted } from 'vue'
import { useModuleStore } from '@/stores/modules'
import { getDesktopLayout, updateDesktopLayout, deleteDesktopOverride } from '@/api/settings'
import PageHeader from '@/components/ui/PageHeader.vue'

const moduleStore = useModuleStore()

const loading = ref(false)
const saving = ref(false)
const error = ref(null)
const layoutOverrides = ref({})
const selectedModule = ref(null)
const editForm = ref({})

// Icon library - common Heroicons
const iconLibrary = [
  {
    name: 'Workflow',
    path: 'M3.75 4.5h16.5M3.75 9h16.5m-16.5 4.5h16.5m-16.5 4.5h16.5',
    category: 'workflow'
  },
  {
    name: 'Flow',
    path: 'M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5',
    category: 'workflow'
  },
  {
    name: 'Arrows Flow',
    path: 'M4.5 12h15m0 0l-6.75-6.75M19.5 12l-6.75 6.75',
    category: 'workflow'
  },
  {
    name: 'Code Bracket',
    path: 'M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5',
    category: 'workflow'
  },
  {
    name: 'Command Line',
    path: 'm6.75 7.5 3 2.25-3 2.25m4.5 0h3m-9 8.25h13.5A2.25 2.25 0 0 0 21 18V6a2.25 2.25 0 0 0-2.25-2.25H5.25A2.25 2.25 0 0 0 3 6v12a2.25 2.25 0 0 0 2.25 2.25Z',
    category: 'workflow'
  },
  {
    name: 'Puzzle',
    path: 'M14.25 6.087c0-.355.186-.676.401-.959.221-.29.349-.634.349-1.003 0-1.036-1.007-1.875-2.25-1.875s-2.25.84-2.25 1.875c0 .369.128.713.349 1.003.215.283.401.604.401.959v0a.64.64 0 01-.657.643 48.39 48.39 0 01-4.163-.3c.186 1.613.293 3.25.315 4.907a.656.656 0 01-.658.663v0c-.355 0-.676-.186-.959-.401a1.647 1.647 0 00-1.003-.349c-1.036 0-1.875 1.007-1.875 2.25s.84 2.25 1.875 2.25c.369 0 .713-.128 1.003-.349.283-.215.604-.401.959-.401v0c.31 0 .555.26.532.57a48.039 48.039 0 01-.642 5.056c1.518.19 3.058.309 4.616.354a.64.64 0 00.657-.643v0c0-.355-.186-.676-.401-.959a1.647 1.647 0 01-.349-1.003c0-1.035 1.008-1.875 2.25-1.875 1.243 0 2.25.84 2.25 1.875 0 .369-.128.713-.349 1.003-.215.283-.4.604-.4.959v0c0 .333.277.599.61.58a48.1 48.1 0 005.427-.63 48.05 48.05 0 00.582-4.717.532.532 0 00-.533-.57v0c-.355 0-.676.186-.959.401-.29.221-.634.349-1.003.349-1.035 0-1.875-1.007-1.875-2.25s.84-2.25 1.875-2.25c.37 0 .713.128 1.003.349.283.215.604.401.96.401v0a.656.656 0 00.658-.663 48.422 48.422 0 00-.37-5.36c-1.886.342-3.81.574-5.766.689a.578.578 0 01-.61-.58v0z',
    category: 'workflow'
  },
  {
    name: 'Cog',
    path: 'M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z M15 12a3 3 0 11-6 0 3 3 0 016 0z',
    category: 'system'
  },
  {
    name: 'Cube',
    path: 'm21 7.5-9-5.25L3 7.5m18 0-9 5.25m9-5.25v9l-9 5.25M3 7.5l9 5.25M3 7.5v9l9 5.25m0-9v9',
    category: 'system'
  },
  {
    name: 'Chart Bar',
    path: 'M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z',
    category: 'marketing'
  },
  {
    name: 'Users',
    path: 'M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z',
    category: 'crm'
  },
  {
    name: 'Funnel',
    path: 'M12 3c2.755 0 5.455.232 8.083.678.533.09.917.556.917 1.096v1.044a2.25 2.25 0 01-.659 1.591l-5.432 5.432a2.25 2.25 0 00-.659 1.591v2.927a2.25 2.25 0 01-1.244 2.013L9.75 21v-6.568a2.25 2.25 0 00-.659-1.591L3.659 7.409A2.25 2.25 0 013 5.818V4.774c0-.54.384-1.006.917-1.096A48.32 48.32 0 0112 3z',
    category: 'sales'
  },
  {
    name: 'Megaphone',
    path: 'M10.34 15.84c-.688-.06-1.386-.09-2.09-.09H7.5a4.5 4.5 0 110-9h.75c.704 0 1.402-.03 2.09-.09m0 9.18c.253.962.584 1.892.985 2.783.247.55.06 1.21-.463 1.511l-.657.38c-.551.318-1.26.117-1.527-.461a20.845 20.845 0 01-1.44-4.282m3.102.069a18.03 18.03 0 01-.59-4.59c0-1.586.205-3.124.59-4.59m0 9.18a23.848 23.848 0 018.835 2.535M10.34 6.66a23.847 23.847 0 008.835-2.535m0 0A23.74 23.74 0 0018.795 3m.38 1.125a23.91 23.91 0 011.014 5.395m-1.014 8.855c-.118.38-.245.754-.38 1.125m.38-1.125a23.91 23.91 0 001.014-5.395m0-3.46c.495.413.811 1.035.811 1.73 0 .695-.316 1.317-.811 1.73m0-3.46a24.347 24.347 0 010 3.46',
    category: 'marketing'
  },
  {
    name: 'Document',
    path: 'M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z',
    category: 'content'
  },
  {
    name: 'Clipboard Check',
    path: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4',
    category: 'sales'
  },
  {
    name: 'Lightning Bolt',
    path: 'M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z',
    category: 'workflow'
  },
  {
    name: 'Sparkles',
    path: 'M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z',
    category: 'marketing'
  },
  {
    name: 'Arrows Pointing Out',
    path: 'M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15',
    category: 'workflow'
  },
  {
    name: 'Queue List',
    path: 'M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 010 3.75H5.625a1.875 1.875 0 010-3.75z',
    category: 'workflow'
  },
  {
    name: 'Server Stack',
    path: 'M5.25 14.25h13.5m-13.5 0a3 3 0 01-3-3m3 3a3 3 0 100 6h13.5a3 3 0 100-6m-16.5-3a3 3 0 013-3h13.5a3 3 0 013 3m-19.5 0a4.5 4.5 0 01.9-2.7L5.737 5.1a3.375 3.375 0 012.7-1.35h7.126c1.062 0 2.062.5 2.7 1.35l2.587 3.45a4.5 4.5 0 01.9 2.7m0 0a3 3 0 01-3 3m0 3h.008v.008h-.008v-.008zm0-6h.008v.008h-.008v-.008zm-3 6h.008v.008h-.008v-.008zm0-6h.008v.008h-.008v-.008z',
    category: 'system'
  },
  {
    name: 'Circle Stack',
    path: 'M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125',
    category: 'system'
  },
  {
    name: 'Share',
    path: 'M7.217 10.907a2.25 2.25 0 100 2.186m0-2.186c.18.324.283.696.283 1.093s-.103.77-.283 1.093m0-2.186l9.566-5.314m-9.566 7.5l9.566 5.314m0 0a2.25 2.25 0 103.935 2.186 2.25 2.25 0 00-3.935-2.186zm0-12.814a2.25 2.25 0 103.933-2.185 2.25 2.25 0 00-3.933 2.185z',
    category: 'workflow'
  }
]

// Predefined colors
const colorPalette = [
  { name: 'Orange', value: '#FF6600' },
  { name: 'Blue', value: '#3B82F6' },
  { name: 'Purple', value: '#8B5CF6' },
  { name: 'Green', value: '#10B981' },
  { name: 'Red', value: '#EF4444' },
  { name: 'Yellow', value: '#F59E0B' },
  { name: 'Pink', value: '#EC4899' },
  { name: 'Cyan', value: '#06B6D4' },
  { name: 'Indigo', value: '#6366F1' },
  { name: 'Teal', value: '#14B8A6' },
  { name: 'Brown', value: '#D4A574' },
  { name: 'Gray', value: '#6B7280' }
]

// All modules for editing
const allModules = computed(() => {
  const modules = []

  // Add desktop modules from store
  for (const [category, mods] of Object.entries(moduleStore.desktopGrouped)) {
    for (const mod of mods) {
      modules.push({
        ...mod,
        category,
        hasOverride: !!layoutOverrides.value[mod.name]
      })
    }
  }

  return modules
})

onMounted(async () => {
  await Promise.all([moduleStore.fetchDesktop(), loadLayoutOverrides()])
})

async function loadLayoutOverrides() {
  loading.value = true
  error.value = null
  try {
    const { data } = await getDesktopLayout()
    layoutOverrides.value = data.modules || {}
  } catch (err) {
    error.value = err.response?.data?.detail || err.message
  } finally {
    loading.value = false
  }
}

function openEditor(mod) {
  selectedModule.value = mod
  const override = layoutOverrides.value[mod.name] || {}
  editForm.value = {
    label: override.label || mod.label,
    icon: override.icon || mod.icon,
    color: override.color || mod.color,
    order: override.order ?? mod.order ?? 99,
    visible: override.visible !== false,
    external_url: override.external_url || mod.external_url || ''
  }
}

function closeEditor() {
  selectedModule.value = null
  editForm.value = {}
}

function selectIcon(iconPath) {
  editForm.value.icon = iconPath
}

function selectColor(colorValue) {
  editForm.value.color = colorValue
}

async function saveModule() {
  if (!selectedModule.value) return

  saving.value = true
  error.value = null
  try {
    const updates = {}
    const mod = selectedModule.value
    const original = layoutOverrides.value[mod.name] || {}

    // Only save changed values
    if (editForm.value.label !== mod.label || original.label) {
      updates.label = editForm.value.label
    }
    if (editForm.value.icon !== mod.icon || original.icon) {
      updates.icon = editForm.value.icon
    }
    if (editForm.value.color !== mod.color || original.color) {
      updates.color = editForm.value.color
    }
    if (editForm.value.order !== (mod.order ?? 99) || original.order) {
      updates.order = editForm.value.order
    }
    if (!editForm.value.visible) {
      updates.visible = false
    }
    if (editForm.value.external_url) {
      updates.external_url = editForm.value.external_url
    }

    const { data } = await updateDesktopLayout(mod.name, updates)
    layoutOverrides.value = data.modules || {}

    // Refresh desktop modules
    await moduleStore.fetchDesktop()
    closeEditor()
  } catch (err) {
    error.value = err.response?.data?.detail || err.message
  } finally {
    saving.value = false
  }
}

async function resetModule() {
  if (!selectedModule.value) return

  saving.value = true
  error.value = null
  try {
    const { data } = await deleteDesktopOverride(selectedModule.value.name)
    layoutOverrides.value = data.modules || {}

    // Refresh desktop modules
    await moduleStore.fetchDesktop()
    closeEditor()
  } catch (err) {
    error.value = err.response?.data?.detail || err.message
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-go4-bg dark:bg-gray-900">
    <PageHeader
      title="Desktop Layout"
      subtitle="Module-Icons, Farben und Reihenfolge anpassen"
    />

    <div class="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:px-8">
      <!-- Loading -->
      <div
        v-if="loading"
        class="flex items-center justify-center py-12"
      >
        <span class="text-go4-muted dark:text-gray-400">Laden...</span>
      </div>

      <!-- Error -->
      <div
        v-else-if="error"
        class="mb-6 rounded-lg bg-red-50 p-4 text-red-700 dark:bg-red-900/20 dark:text-red-400"
      >
        {{ error }}
      </div>

      <!-- Module Grid -->
      <div
        v-else
        class="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5"
      >
        <button
          v-for="mod in allModules"
          :key="mod.name"
          class="group relative flex flex-col items-center gap-3 rounded-xl border border-gray-200 bg-white p-4 transition-all hover:border-go4-primary hover:shadow-lg dark:border-gray-700 dark:bg-gray-800"
          :class="{ 'ring-2 ring-go4-primary': mod.hasOverride }"
          @click="openEditor(mod)"
        >
          <!-- Override badge -->
          <span
            v-if="mod.hasOverride"
            class="absolute -right-1 -top-1 h-3 w-3 rounded-full bg-go4-primary"
          />

          <!-- Icon preview -->
          <div
            class="flex h-16 w-16 items-center justify-center rounded-2xl"
            :style="{ backgroundColor: `${mod.color}20` }"
          >
            <svg
              class="h-8 w-8"
              :style="{ color: mod.color }"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                :d="mod.icon"
              />
            </svg>
          </div>

          <!-- Label -->
          <span class="text-sm font-medium text-go4-secondary dark:text-white">
            {{ mod.label }}
          </span>

          <!-- Category badge -->
          <span class="text-xs text-go4-muted dark:text-gray-500">
            {{ mod.category }}
          </span>
        </button>
      </div>
    </div>

    <!-- Edit Modal -->
    <div
      v-if="selectedModule"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      @click.self="closeEditor"
    >
      <div
        class="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl bg-white p-6 shadow-xl dark:bg-gray-800"
      >
        <div class="mb-6 flex items-center justify-between">
          <h2 class="text-xl font-bold text-go4-secondary dark:text-white">
            {{ selectedModule.label }} bearbeiten
          </h2>
          <button
            class="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700"
            @click="closeEditor"
          >
            <svg
              class="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <!-- Preview -->
        <div class="mb-6 flex items-center justify-center">
          <div
            class="flex h-24 w-24 items-center justify-center rounded-3xl transition-all"
            :style="{ backgroundColor: `${editForm.color}20` }"
          >
            <svg
              class="h-12 w-12"
              :style="{ color: editForm.color }"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                :d="editForm.icon"
              />
            </svg>
          </div>
        </div>

        <!-- Label -->
        <div class="mb-4">
          <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-white">
            Label
          </label>
          <input
            v-model="editForm.label"
            type="text"
            class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary dark:border-gray-600 dark:bg-gray-700 dark:text-white"
          >
        </div>

        <!-- Color Picker -->
        <div class="mb-4">
          <label class="mb-2 block text-sm font-medium text-go4-secondary dark:text-white">
            Farbe
          </label>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="color in colorPalette"
              :key="color.value"
              class="h-8 w-8 rounded-lg border-2 transition-transform hover:scale-110"
              :class="
                editForm.color === color.value ? 'border-go4-secondary' : 'border-transparent'
              "
              :style="{ backgroundColor: color.value }"
              :title="color.name"
              @click="selectColor(color.value)"
            />
            <input
              v-model="editForm.color"
              type="color"
              class="h-8 w-8 cursor-pointer rounded-lg border border-gray-300"
              title="Custom"
            >
          </div>
        </div>

        <!-- Icon Picker -->
        <div class="mb-4">
          <label class="mb-2 block text-sm font-medium text-go4-secondary dark:text-white">
            Icon
          </label>
          <div
            class="grid max-h-48 grid-cols-6 gap-2 overflow-y-auto rounded-lg border border-gray-200 p-3 dark:border-gray-600"
          >
            <button
              v-for="icon in iconLibrary"
              :key="icon.name"
              class="flex h-10 w-10 items-center justify-center rounded-lg border-2 transition-colors hover:bg-gray-100 dark:hover:bg-gray-700"
              :class="
                editForm.icon === icon.path
                  ? 'border-go4-primary bg-go4-primary/10'
                  : 'border-transparent'
              "
              :title="icon.name"
              @click="selectIcon(icon.path)"
            >
              <svg
                class="h-6 w-6 text-go4-secondary dark:text-white"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="1.5"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  :d="icon.path"
                />
              </svg>
            </button>
          </div>
        </div>

        <!-- Custom Icon Path -->
        <div class="mb-4">
          <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-white">
            Eigener Icon-Pfad (SVG path)
          </label>
          <textarea
            v-model="editForm.icon"
            rows="2"
            class="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-xs focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary dark:border-gray-600 dark:bg-gray-700 dark:text-white"
          />
        </div>

        <!-- Order -->
        <div class="mb-4">
          <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-white">
            Reihenfolge (niedriger = weiter vorne)
          </label>
          <input
            v-model.number="editForm.order"
            type="number"
            min="0"
            max="999"
            class="w-32 rounded-lg border border-gray-300 px-3 py-2 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary dark:border-gray-600 dark:bg-gray-700 dark:text-white"
          >
        </div>

        <!-- External URL -->
        <div class="mb-4">
          <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-white">
            Externe URL (optional)
          </label>
          <input
            v-model="editForm.external_url"
            type="url"
            placeholder="https://..."
            class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary dark:border-gray-600 dark:bg-gray-700 dark:text-white"
          >
        </div>

        <!-- Visibility -->
        <div class="mb-6">
          <label class="flex cursor-pointer items-center gap-3">
            <input
              v-model="editForm.visible"
              type="checkbox"
              class="h-4 w-4 rounded border-gray-300 text-go4-primary focus:ring-go4-primary"
            >
            <span class="text-sm text-go4-secondary dark:text-white">Auf dem Desktop anzeigen</span>
          </label>
        </div>

        <!-- Actions -->
        <div
          class="flex items-center justify-between border-t border-gray-200 pt-4 dark:border-gray-700"
        >
          <button
            v-if="layoutOverrides[selectedModule?.name]"
            class="rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 dark:border-red-700 dark:text-red-400 dark:hover:bg-red-900/20"
            :disabled="saving"
            @click="resetModule"
          >
            Auf Standard zuruecksetzen
          </button>
          <div v-else />

          <div class="flex gap-3">
            <button
              class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
              @click="closeEditor"
            >
              Abbrechen
            </button>
            <button
              class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary/90 disabled:opacity-50"
              :disabled="saving"
              @click="saveModule"
            >
              {{ saving ? 'Speichern...' : 'Speichern' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
