<script setup>
import { onMounted, watch } from 'vue'
import { useSettingsStore } from '@/stores/settings'
import PageHeader from '@/components/ui/PageHeader.vue'
import SettingsGlobalTab from '@/components/settings/SettingsGlobalTab.vue'
import SettingsModuleTab from '@/components/settings/SettingsModuleTab.vue'

const store = useSettingsStore()

onMounted(async () => {
  await store.fetchModules()
  await store.fetchTabData(store.activeTab)
})

watch(
  () => store.activeTab,
  (tab) => {
    store.fetchTabData(tab)
  }
)

function switchTab(key) {
  store.setActiveTab(key)
}

function onSaveModule(updates) {
  store.saveModuleConfig(store.activeTab, updates)
}

function onSaveGlobal(updates) {
  store.saveGlobalSettings(updates)
}
</script>

<template>
  <div class="space-y-6">
    <PageHeader title="Einstellungen" subtitle="Plattform- und Modul-Konfiguration verwalten" />

    <!-- Success Toast -->
    <div
      v-if="store.saveSuccess"
      class="rounded-lg bg-green-50 p-3 text-sm font-medium text-green-800"
    >
      Einstellungen gespeichert.
    </div>

    <!-- Error Toast -->
    <div v-if="store.error" class="rounded-lg bg-red-50 p-3 text-sm font-medium text-red-800">
      {{ store.error }}
    </div>

    <!-- Tab Bar -->
    <div class="border-b border-gray-200">
      <nav class="-mb-px flex space-x-6 overflow-x-auto">
        <button
          v-for="tab in store.tabs"
          :key="tab.key"
          :class="[
            'whitespace-nowrap border-b-2 px-1 py-3 text-sm font-medium transition',
            store.activeTab === tab.key
              ? 'border-go4-primary text-go4-primary'
              : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
          ]"
          @click="switchTab(tab.key)"
        >
          {{ tab.label }}
        </button>
      </nav>
    </div>

    <!-- Loading -->
    <div v-if="store.loading" class="flex items-center justify-center p-12">
      <span class="text-sm text-gray-500">Laden...</span>
    </div>

    <!-- Tab Content -->
    <div v-else>
      <!-- Global Tab -->
      <SettingsGlobalTab
        v-if="store.activeTab === 'global'"
        :schema="store.globalSchema"
        :config="store.globalConfig"
        :saving="store.saving"
        @save="onSaveGlobal"
      />

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
