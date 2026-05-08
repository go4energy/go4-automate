<script setup>
/**
 * Generic settings page for modules that don't have their own tab system.
 * Reads module-name from route.meta.moduleName and renders the
 * ModuleSettings wrapper.
 *
 * Usage in manifests:
 *   {
 *     "path": "einstellungen",
 *     "name": "{module}-einstellungen",
 *     "view": "ModuleSettingsPageView",
 *     "meta": {
 *       "title": "Einstellungen",
 *       "moduleName": "<module>",
 *       "breadcrumb": {"label": "Einstellungen", "parent": "<module>"},
 *     },
 *   },
 */
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import PageHeader from '@/components/ui/PageHeader.vue'
import ModuleSettings from '@/components/settings/ModuleSettings.vue'

const route = useRoute()
const moduleName = computed(() => route.meta?.moduleName || '')
const title = computed(() => route.meta?.title || 'Einstellungen')
</script>

<template>
  <div>
    <PageHeader :title="title" />
    <ModuleSettings
      v-if="moduleName"
      :module-name="moduleName"
    />
    <div
      v-else
      class="rounded-lg bg-amber-50 dark:bg-amber-900/20 p-4 text-sm text-amber-800 dark:text-amber-200"
    >
      Kein Modul-Name in der Route definiert (route.meta.moduleName).
    </div>
  </div>
</template>
