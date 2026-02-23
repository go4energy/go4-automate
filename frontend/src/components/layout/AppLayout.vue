<script setup>
import AppHeader from './AppHeader.vue'
import ChatPanel from '@/components/chat/ChatPanel.vue'
</script>

<template>
  <div class="min-h-screen bg-go4-surface transition-colors dark:bg-go4-dark-bg">
    <AppHeader />
    <main class="flex-1 p-6">
      <RouterView />
    </main>
    <ChatPanel />
  </div>
</template>
