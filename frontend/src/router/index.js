import { createRouter, createWebHistory } from 'vue-router'

// Static base routes (always available)
const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    name: 'layout',
    component: () => import('@/components/layout/AppLayout.vue'),
    children: [
      {
        path: '',
        name: 'desktop',
        component: () => import('@/views/DesktopView.vue'),
        meta: { title: 'Desktop' }
      },
      {
        path: 'dashboard',
        name: 'dashboard',
        component: () => import('@/views/DashboardView.vue'),
        meta: { title: 'Dashboard' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Auth guard
router.beforeEach(async (to) => {
  const { useAuthStore } = await import('@/stores/auth')
  const authStore = useAuthStore()

  const requiresAuth = to.meta.requiresAuth !== false

  // Try to restore session from token
  if (!authStore.user && authStore.token) {
    await authStore.fetchMe()
  }

  if (requiresAuth && !authStore.isAuthenticated) {
    return '/login'
  }

  if (to.path === '/login' && authStore.isAuthenticated) {
    return '/'
  }
})

// View resolver: pre-scan all views for dynamic import
const viewModules = import.meta.glob('@/views/*.vue')

/**
 * Register module routes dynamically from API module manifests.
 * All module routes are added as children of the AppLayout route.
 */
export function registerModuleRoutes(modules) {
  for (const mod of modules) {
    if (!mod.frontend?.routes) continue

    for (const route of mod.frontend.routes) {
      const viewPath = `/src/views/${route.view}.vue`
      const component = viewModules[viewPath]
      if (!component) continue

      const basePath = mod.frontend.base_route.startsWith('/')
        ? mod.frontend.base_route.slice(1)
        : mod.frontend.base_route

      const fullPath = route.path ? `${basePath}/${route.path}` : basePath

      router.addRoute('layout', {
        path: fullPath,
        name: route.name,
        component,
        props: route.props || false,
        meta: route.meta || {}
      })
    }
  }
}

export default router
