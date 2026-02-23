<script setup>
import { ref } from 'vue'
import { changePassword } from '@/api/auth'

const emit = defineEmits(['close'])

const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const loading = ref(false)
const error = ref(null)
const success = ref(false)

async function handleSubmit() {
  error.value = null
  if (newPassword.value !== confirmPassword.value) {
    error.value = 'Passwoerter stimmen nicht ueberein'
    return
  }
  if (newPassword.value.length < 6) {
    error.value = 'Passwort muss mindestens 6 Zeichen haben'
    return
  }

  loading.value = true
  try {
    await changePassword({
      current_password: currentPassword.value,
      new_password: newPassword.value
    })
    success.value = true
    setTimeout(() => emit('close'), 1500)
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
    @click.self="emit('close')"
  >
    <div class="w-full max-w-md rounded-xl bg-white p-6 shadow-2xl dark:bg-gray-800">
      <h2 class="mb-4 text-lg font-semibold text-gray-900 dark:text-gray-100">Passwort aendern</h2>

      <div
        v-if="success"
        class="rounded-lg bg-green-50 p-4 text-sm text-green-700 dark:bg-green-900/30 dark:text-green-400"
      >
        Passwort erfolgreich geaendert!
      </div>

      <form v-else class="space-y-4" @submit.prevent="handleSubmit">
        <div
          v-if="error"
          class="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600 dark:bg-red-900/30 dark:text-red-400"
        >
          {{ error }}
        </div>

        <div>
          <label class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300"
            >Aktuelles Passwort</label
          >
          <input
            v-model="currentPassword"
            type="password"
            required
            class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
          />
        </div>

        <div>
          <label class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300"
            >Neues Passwort</label
          >
          <input
            v-model="newPassword"
            type="password"
            required
            minlength="6"
            class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
          />
        </div>

        <div>
          <label class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300"
            >Passwort bestaetigen</label
          >
          <input
            v-model="confirmPassword"
            type="password"
            required
            class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
          />
        </div>

        <div class="flex justify-end gap-3 pt-2">
          <button
            type="button"
            class="rounded-lg px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700"
            @click="emit('close')"
          >
            Abbrechen
          </button>
          <button
            type="submit"
            :disabled="loading"
            class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary/90 disabled:opacity-50"
          >
            {{ loading ? 'Speichern...' : 'Speichern' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>
