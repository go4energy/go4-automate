<script setup>
/**
 * Standalone wrapper that loads schema + config + status for a single module
 * and renders the SettingsModuleTab UI. Drop into any module view as a
 * dedicated "Einstellungen" tab — no need to go through the global Settings
 * module any more.
 *
 * Example:
 *   <ModuleSettings module-name="emailmarketing" />
 */
import { ref, computed, onMounted, watch } from 'vue'
import {
  getModuleSchema,
  getModuleConfig,
  updateModuleConfig,
  getModuleStatus,
} from '@/api/settings'
import SettingsModuleTab from '@/components/settings/SettingsModuleTab.vue'

const props = defineProps({
  moduleName: { type: String, required: true },
})

const schema = ref(null)
const config = ref({})
const status = ref(null)
const loading = ref(true)
const saving = ref(false)
const error = ref(null)
const savedToast = ref(false)

async function load() {
  loading.value = true
  error.value = null
  try {
    const [s, c, st] = await Promise.all([
      getModuleSchema(props.moduleName),
      getModuleConfig(props.moduleName),
      getModuleStatus(props.moduleName),
    ])
    schema.value = s.data
    config.value = c.data.config || {}
    status.value = st.data
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    loading.value = false
  }
}

async function onSave(updates) {
  saving.value = true
  error.value = null
  try {
    const { data } = await updateModuleConfig(props.moduleName, updates)
    config.value = data.config || {}
    savedToast.value = true
    setTimeout(() => (savedToast.value = false), 2500)
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    saving.value = false
  }
}

onMounted(load)
watch(() => props.moduleName, load)

const hasParams = computed(() => Array.isArray(schema.value) && schema.value.length > 0)
</script>

<template>
  <div>
    <div
      v-if="loading"
      class="flex items-center justify-center py-12"
    >
      <span class="text-gray-500 dark:text-gray-400">Laden…</span>
    </div>

    <div
      v-else-if="error"
      class="rounded-lg bg-red-50 p-4 text-red-700 dark:bg-red-900/20 dark:text-red-400"
    >
      {{ error }}
    </div>

    <div
      v-else-if="!hasParams"
      class="rounded-lg border border-dashed border-gray-300 bg-white p-8 text-center text-sm text-gray-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-400"
    >
      Für dieses Modul gibt es keine konfigurierbaren Einstellungen.
    </div>

    <SettingsModuleTab
      v-else
      :module-name="moduleName"
      :schema="schema"
      :config="config"
      :status="status"
      :saving="saving"
      @save="onSave"
    />

    <transition
      enter-active-class="transition duration-200"
      enter-from-class="opacity-0 translate-y-2"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition duration-200"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="savedToast"
        class="fixed bottom-4 right-4 z-50 rounded-lg bg-emerald-600 text-white px-4 py-2 shadow-lg text-sm font-medium"
      >
        ✓ Gespeichert
      </div>
    </transition>
  </div>
</template>
