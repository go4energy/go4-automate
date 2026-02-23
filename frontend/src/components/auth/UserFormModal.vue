<script setup>
import { ref, computed } from 'vue'
import { createUser, updateUser } from '@/api/auth'
import PermissionMatrix from './PermissionMatrix.vue'

const props = defineProps({
  user: { type: Object, default: null }
})

const emit = defineEmits(['close', 'saved'])

const isEdit = computed(() => !!props.user)

const form = ref({
  email: props.user?.email || '',
  display_name: props.user?.display_name || '',
  role: props.user?.role || 'user',
  password: '',
  permissions: props.user?.permissions || {}
})

const loading = ref(false)
const error = ref(null)

async function handleSubmit() {
  loading.value = true
  error.value = null
  try {
    if (isEdit.value) {
      const data = {
        email: form.value.email,
        display_name: form.value.display_name,
        role: form.value.role,
        permissions: form.value.permissions
      }
      await updateUser(props.user.id, data)
    } else {
      await createUser({
        email: form.value.email,
        display_name: form.value.display_name,
        role: form.value.role,
        password: form.value.password,
        permissions: form.value.permissions
      })
    }
    emit('saved')
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
    <div
      class="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl bg-white p-6 shadow-2xl dark:bg-gray-800"
    >
      <h2 class="mb-4 text-lg font-semibold text-gray-900 dark:text-gray-100">
        {{ isEdit ? 'Benutzer bearbeiten' : 'Neuer Benutzer' }}
      </h2>

      <form class="space-y-4" @submit.prevent="handleSubmit">
        <div
          v-if="error"
          class="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600 dark:bg-red-900/30 dark:text-red-400"
        >
          {{ error }}
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300"
              >E-Mail</label
            >
            <input
              v-model="form.email"
              type="email"
              required
              class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
            />
          </div>
          <div>
            <label class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300"
              >Name</label
            >
            <input
              v-model="form.display_name"
              type="text"
              required
              class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
            />
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300"
              >Rolle</label
            >
            <select
              v-model="form.role"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
            >
              <option value="user">Benutzer</option>
              <option value="admin">Administrator</option>
            </select>
          </div>
          <div v-if="!isEdit">
            <label class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300"
              >Passwort</label
            >
            <input
              v-model="form.password"
              type="password"
              required
              minlength="6"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
            />
          </div>
        </div>

        <!-- Direct Permissions (optional, for non-admin users) -->
        <div v-if="form.role !== 'admin'">
          <label class="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
            Direkte Berechtigungen (optional)
          </label>
          <PermissionMatrix :permissions="form.permissions" @update="form.permissions = $event" />
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
