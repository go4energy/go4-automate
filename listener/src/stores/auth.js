import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import api from '@/api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const token = ref(localStorage.getItem('listener_token') || null)
  const loading = ref(false)
  const error = ref(null)

  const isLoggedIn = computed(() => !!token.value)

  async function login(email, password) {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.post('/auth/login', { email, password })
      token.value = data.access_token
      localStorage.setItem('listener_token', data.access_token)
      await fetchProfile()
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function register(email, password, displayName, role) {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.post('/auth/register', {
        email,
        password,
        display_name: displayName,
        role
      })
      token.value = data.access_token
      localStorage.setItem('listener_token', data.access_token)
      await fetchProfile()
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchProfile() {
    try {
      const { data } = await api.get('/profile')
      user.value = data
    } catch {
      user.value = null
    }
  }

  async function updateProfile(updates) {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.put('/profile', updates)
      user.value = data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('listener_token')
  }

  return {
    user,
    token,
    loading,
    error,
    isLoggedIn,
    login,
    register,
    fetchProfile,
    updateProfile,
    logout
  }
})
