import { createApp } from 'vue'
import { createPinia } from 'pinia'
import VueApexCharts from 'vue3-apexcharts'

import App from './App.vue'
import router, { registerModuleRoutes } from './router'
import { useAuthStore } from '@/stores/auth'
import { useModuleStore } from '@/stores/modules'
import { useLayoutStore } from '@/stores/layout'
import './assets/main.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(VueApexCharts)

// Initialize layout store early (applies dark mode class)
useLayoutStore()

// Initialize auth, then load modules and mount
const authStore = useAuthStore()
const moduleStore = useModuleStore()

async function bootstrap() {
  // Try to restore session from token
  if (authStore.token) {
    await authStore.fetchMe()
  }

  // Load modules only if authenticated
  if (authStore.isAuthenticated) {
    try {
      await moduleStore.fetchModules()
      registerModuleRoutes(moduleStore.modules)
    } catch {
      // Continue without dynamic routes
    }
  }

  // Install router AFTER dynamic routes are registered
  // to avoid race condition on hard refresh
  app.use(router)
  app.mount('#app')
}

bootstrap()
