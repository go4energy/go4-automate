<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const displayName = ref('')
const saving = ref(false)
const saved = ref(false)

onMounted(async () => {
  await auth.fetchProfile()
  if (auth.user) {
    displayName.value = auth.user.display_name || ''
  }
})

async function saveProfile() {
  saving.value = true
  saved.value = false
  try {
    await auth.updateProfile({ display_name: displayName.value })
    saved.value = true
    setTimeout(() => {
      saved.value = false
    }, 2000)
  } finally {
    saving.value = false
  }
}

function handleLogout() {
  auth.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <div class="px-4 pb-4 pt-6">
    <h1 class="mb-6 text-2xl font-bold text-gray-900">Profil</h1>

    <div v-if="auth.loading" class="py-12 text-center text-gray-500">Laden...</div>

    <div v-else-if="auth.user" class="space-y-6">
      <div class="rounded-xl bg-white p-4 shadow-sm">
        <div class="mb-4 flex items-center gap-3">
          <div
            class="flex h-12 w-12 items-center justify-center rounded-full bg-go4-primary text-lg font-bold text-white"
          >
            {{ (auth.user.display_name || auth.user.email).charAt(0).toUpperCase() }}
          </div>
          <div>
            <p class="font-medium text-gray-900">{{ auth.user.display_name || 'Listener' }}</p>
            <p class="text-sm text-gray-500">{{ auth.user.email }}</p>
          </div>
        </div>

        <div class="space-y-3">
          <div>
            <label class="mb-1 block text-sm font-medium text-gray-700">Anzeigename</label>
            <input
              v-model="displayName"
              type="text"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
            />
          </div>

          <div class="flex items-center gap-3">
            <button
              :disabled="saving"
              class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-go4-primary-dark disabled:opacity-50"
              @click="saveProfile"
            >
              {{ saving ? 'Speichern...' : 'Speichern' }}
            </button>
            <span v-if="saved" class="text-sm text-green-600">Gespeichert</span>
          </div>
        </div>
      </div>

      <div class="rounded-xl bg-white p-4 shadow-sm">
        <h2 class="mb-2 text-sm font-semibold text-gray-900">Konto</h2>
        <div class="space-y-2 text-sm text-gray-600">
          <div class="flex justify-between">
            <span>Rolle</span>
            <span class="font-medium">{{ auth.user.role }}</span>
          </div>
          <div class="flex justify-between">
            <span>Mitglied seit</span>
            <span class="font-medium">
              {{ new Date(auth.user.created_at).toLocaleDateString('de-DE') }}
            </span>
          </div>
        </div>
      </div>

      <button
        class="w-full rounded-lg border border-red-200 bg-red-50 px-4 py-2.5 text-sm font-medium text-red-700 transition-colors hover:bg-red-100"
        @click="handleLogout"
      >
        Abmelden
      </button>
    </div>
  </div>
</template>
