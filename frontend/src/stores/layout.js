import { ref } from 'vue'
import { defineStore } from 'pinia'

export const useLayoutStore = defineStore('layout', () => {
  const sidebarCollapsed = ref(localStorage.getItem('sidebar-collapsed') === 'true')
  const chatOpen = ref(false)

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
    localStorage.setItem('sidebar-collapsed', sidebarCollapsed.value)
  }

  function toggleChat() {
    chatOpen.value = !chatOpen.value
  }

  return { sidebarCollapsed, chatOpen, toggleSidebar, toggleChat }
})
