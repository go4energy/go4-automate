<script setup>
import AppHeader from './AppHeader.vue'
import ChatPanel from '@/components/chat/ChatPanel.vue'
import { useLayoutStore } from '@/stores/layout'

const layoutStore = useLayoutStore()
</script>

<template>
  <div class="min-h-screen bg-go4-surface transition-colors dark:bg-go4-dark-bg">
    <!-- Hauptbereich (Header + Main): wird beim ChatPanel-Open per
         margin-right schmaler. Auf <sm Breakpoint bleibt es overlay,
         weil 400px Panel den Content komplett verdecken würde. -->
    <div
      class="transition-[margin-right] duration-300 ease-out"
      :class="layoutStore.chatOpen ? 'sm:mr-[400px]' : 'mr-0'"
    >
      <AppHeader />
      <main class="flex-1 p-6">
        <RouterView />
      </main>
    </div>
    <ChatPanel />
  </div>
</template>
