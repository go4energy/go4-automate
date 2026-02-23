import { ref } from 'vue'
import { defineStore } from 'pinia'

export const useLayoutStore = defineStore('layout', () => {
  const chatOpen = ref(false)
  const sidebarCollapsed = ref(localStorage.getItem('sidebar-collapsed') === 'true')
  const darkMode = ref(localStorage.getItem('dark-mode') === 'true')

  // Apply or remove dark class on init
  if (darkMode.value) {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }

  function toggleDarkMode() {
    darkMode.value = !darkMode.value
    localStorage.setItem('dark-mode', darkMode.value)
    if (darkMode.value) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }

  function toggleChat() {
    chatOpen.value = !chatOpen.value
  }

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
    localStorage.setItem('sidebar-collapsed', sidebarCollapsed.value)
  }

  return { chatOpen, sidebarCollapsed, darkMode, toggleDarkMode, toggleChat, toggleSidebar }
})
