<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useModuleStore } from '@/stores/modules'
import { registerModuleRoutes } from '@/router'

const router = useRouter()
const authStore = useAuthStore()
const moduleStore = useModuleStore()

const email = ref('')
const password = ref('')
const loading = ref(false)
const error = ref(null)

async function handleLogin() {
  loading.value = true
  error.value = null
  try {
    const success = await authStore.login(email.value, password.value)
    if (success) {
      // Load modules and register routes after login
      await moduleStore.fetchModules()
      registerModuleRoutes(moduleStore.modules)
      router.push('/')
    } else {
      error.value = authStore.error || 'Login fehlgeschlagen'
    }
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="flex items-center justify-center bg-gradient-to-br from-[#E8EDFF] via-[#DED8FF] to-[#FFE8D8] px-4 dark:from-[#0A0015] dark:via-[#000A1A] dark:to-[#050510]"
  >
    <div class="w-full max-w-sm">
      <!-- Logo -->
      <div class="mb-8 flex flex-col items-center">
        <div
          class="mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-go4-primary text-lg font-bold text-white shadow-lg"
        >
          g4
        </div>
        <h1 class="text-xl font-semibold text-go4-secondary dark:text-white">
          go4-automate
        </h1>
        <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Melden Sie sich an, um fortzufahren
        </p>
      </div>

      <!-- Login Card -->
      <div class="rounded-2xl bg-white/80 p-8 shadow-xl backdrop-blur dark:bg-gray-800/80">
        <form
          class="space-y-5"
          @submit.prevent="handleLogin"
        >
          <!-- Error -->
          <div
            v-if="error"
            class="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600 dark:bg-red-900/30 dark:text-red-400"
          >
            {{ error }}
          </div>

          <!-- Email -->
          <div>
            <label
              for="email"
              class="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300"
            >
              E-Mail
            </label>
            <input
              id="email"
              v-model="email"
              type="email"
              required
              autocomplete="email"
              class="w-full rounded-lg border border-gray-300 bg-white px-3.5 py-2.5 text-sm text-gray-900 transition placeholder:text-gray-400 focus:border-go4-primary focus:outline-none focus:ring-2 focus:ring-go4-primary/20 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 dark:placeholder:text-gray-500 dark:focus:border-go4-primary"
              placeholder="admin@go4.energy"
            >
          </div>

          <!-- Password -->
          <div>
            <label
              for="password"
              class="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300"
            >
              Passwort
            </label>
            <input
              id="password"
              v-model="password"
              type="password"
              required
              autocomplete="current-password"
              class="w-full rounded-lg border border-gray-300 bg-white px-3.5 py-2.5 text-sm text-gray-900 transition placeholder:text-gray-400 focus:border-go4-primary focus:outline-none focus:ring-2 focus:ring-go4-primary/20 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 dark:placeholder:text-gray-500 dark:focus:border-go4-primary"
              placeholder="••••••••"
            >
          </div>

          <!-- Submit -->
          <button
            type="submit"
            :disabled="loading"
            class="w-full rounded-lg bg-go4-primary px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-go4-primary/90 focus:outline-none focus:ring-2 focus:ring-go4-primary/50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <span v-if="loading">Anmelden...</span>
            <span v-else>Anmelden</span>
          </button>
        </form>
      </div>
    </div>
  </div>
</template>
