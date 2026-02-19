<script setup>
import { computed } from 'vue'
import { useLayoutStore } from '@/stores/layout'
import AppSidebar from './AppSidebar.vue'
import AppHeader from './AppHeader.vue'
import ChatPanel from '@/components/chat/ChatPanel.vue'

const layout = useLayoutStore()

const mainMargin = computed(() => (layout.sidebarCollapsed ? 'ml-16' : 'ml-64'))
</script>

<template>
  <div class="min-h-screen bg-go4-surface">
    <AppSidebar />
    <div :class="['flex min-h-screen flex-col transition-all duration-200', mainMargin]">
      <AppHeader />
      <main class="flex-1 p-6">
        <RouterView />
      </main>
    </div>
    <ChatPanel />
  </div>
</template>
