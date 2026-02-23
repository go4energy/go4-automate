<script setup>
import { ref, computed } from 'vue'
import { createGroup, updateGroup } from '@/api/auth'
import PermissionMatrix from './PermissionMatrix.vue'

const props = defineProps({
  group: { type: Object, default: null }
})

const emit = defineEmits(['close', 'saved'])

const isEdit = computed(() => !!props.group)

const form = ref({
  name: props.group?.name || '',
  description: props.group?.description || '',
  permissions: props.group?.permissions || {}
})

const loading = ref(false)
const error = ref(null)

async function handleSubmit() {
  loading.value = true
  error.value = null
  try {
    const data = {
      name: form.value.name,
      description: form.value.description || null,
      permissions: form.value.permissions
    }
    if (isEdit.value) {
      await updateGroup(props.group.id, data)
    } else {
      await createGroup(data)
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
        {{ isEdit ? 'Gruppe bearbeiten' : 'Neue Gruppe' }}
      </h2>

      <form class="space-y-4" @submit.prevent="handleSubmit">
        <div
          v-if="error"
          class="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600 dark:bg-red-900/30 dark:text-red-400"
        >
          {{ error }}
        </div>

        <div>
          <label class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300"
            >Name</label
          >
          <input
            v-model="form.name"
            type="text"
            required
            class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
          />
        </div>

        <div>
          <label class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
            Beschreibung (optional)
          </label>
          <textarea
            v-model="form.description"
            rows="2"
            class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
          />
        </div>

        <div>
          <label class="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300"
            >Berechtigungen</label
          >
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
