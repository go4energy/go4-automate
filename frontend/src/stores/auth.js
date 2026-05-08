import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { login as apiLogin, getMe as apiGetMe } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const token = ref(localStorage.getItem('token') || null)
  const loading = ref(false)
  const error = ref(null)

  const isAuthenticated = computed(() => !!token.value && !!user.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const permissions = computed(() => user.value?.resolved_permissions || {})

  function hasPermission(module, action) {
    if (isAdmin.value) return true
    return permissions.value[module]?.[action] === true
  }

  function canViewModule(module) {
    if (isAdmin.value) return true
    return permissions.value[module]?.view === true
  }

  async function login(email, password) {
    loading.value = true
    error.value = null
    try {
      const { data } = await apiLogin(email, password)
      token.value = data.access_token
      localStorage.setItem('token', data.access_token)
      // Use login payload immediately so a flaky /me call does not block login.
      user.value = data.user || null
      // Best effort: hydrate resolved permissions and groups.
      await fetchMe()
      return true
    } catch (err) {
      error.value = err.message
      return false
    } finally {
      loading.value = false
    }
  }

  async function fetchMe() {
    if (!token.value) return false
    try {
      const { data } = await apiGetMe()
      user.value = data
      return true
    } catch {
      // Keep the login payload user if available; only clear a truly empty auth state.
      if (!user.value) {
        logout()
      }
      return false
    }
  }

  function logout() {
    user.value = null
    token.value = null
    localStorage.removeItem('token')
  }

  return {
    user,
    token,
    loading,
    error,
    isAuthenticated,
    isAdmin,
    permissions,
    hasPermission,
    canViewModule,
    login,
    fetchMe,
    logout
  }
})
