<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const isRegister = ref(false)
const email = ref('')
const password = ref('')
const displayName = ref('')
const role = ref('employee')
const error = ref(null)
const loading = ref(false)

async function handleSubmit() {
  loading.value = true
  error.value = null
  try {
    if (isRegister.value) {
      await auth.register(email.value, password.value, displayName.value, role.value)
    } else {
      await auth.login(email.value, password.value)
    }
    router.push({ name: 'home' })
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div
    class="flex min-h-screen items-center justify-center bg-gradient-to-br from-go4-primary to-go4-primary-dark p-4"
  >
    <div class="w-full max-w-sm rounded-2xl bg-white p-8 shadow-xl">
      <div class="mb-6 text-center">
        <div
          class="mx-auto mb-3 flex h-16 w-16 items-center justify-center rounded-full bg-go4-primary/10"
        >
          <svg
            class="h-8 w-8 text-go4-primary"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
            />
          </svg>
        </div>
        <h1 class="text-xl font-bold text-gray-900">go4 Briefing</h1>
        <p class="text-sm text-gray-500">Ihr Audio-Nachrichtensprecher</p>
      </div>

      <div v-if="error" class="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">
        {{ error }}
      </div>

      <form class="space-y-4" @submit.prevent="handleSubmit">
        <div v-if="isRegister">
          <label class="mb-1 block text-sm font-medium text-gray-700">Name</label>
          <input
            v-model="displayName"
            type="text"
            required
            class="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
            placeholder="Ihr Name"
          />
        </div>

        <div>
          <label class="mb-1 block text-sm font-medium text-gray-700">E-Mail</label>
          <input
            v-model="email"
            type="email"
            required
            class="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
            placeholder="name@firma.de"
          />
        </div>

        <div>
          <label class="mb-1 block text-sm font-medium text-gray-700">Passwort</label>
          <input
            v-model="password"
            type="password"
            required
            minlength="8"
            class="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
            placeholder="Mindestens 8 Zeichen"
          />
        </div>

        <div v-if="isRegister">
          <label class="mb-1 block text-sm font-medium text-gray-700">Rolle</label>
          <select
            v-model="role"
            class="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
          >
            <option value="employee">Mitarbeiter</option>
            <option value="manager">Manager</option>
            <option value="executive">Geschaeftsleitung</option>
          </select>
        </div>

        <button
          type="submit"
          :disabled="loading"
          class="w-full rounded-lg bg-go4-primary px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-go4-primary-dark disabled:opacity-50"
        >
          {{ loading ? 'Bitte warten...' : isRegister ? 'Registrieren' : 'Anmelden' }}
        </button>
      </form>

      <p class="mt-4 text-center text-sm text-gray-500">
        <button class="text-go4-primary hover:underline" @click="isRegister = !isRegister">
          {{ isRegister ? 'Bereits registriert? Anmelden' : 'Noch kein Konto? Registrieren' }}
        </button>
      </p>
    </div>
  </div>
</template>
