<script setup>
import { ref, onMounted } from 'vue'
import {
  getUsers,
  deleteUser,
  resetPassword,
  getGroups,
  deleteGroup,
  addUserToGroup,
  removeUserFromGroup
} from '@/api/auth'
import { useTabState } from '@/composables/useTabState'
import PageHeader from '@/components/ui/PageHeader.vue'
import UserFormModal from '@/components/auth/UserFormModal.vue'
import GroupFormModal from '@/components/auth/GroupFormModal.vue'

const activeTab = useTabState('user-management', 'users', ['users', 'groups'])
const loading = ref(false)
const error = ref(null)

// Users
const users = ref([])
const showUserModal = ref(false)
const editingUser = ref(null)

// Groups
const groups = ref([])
const showGroupModal = ref(false)
const editingGroup = ref(null)

// Group member management
const managingGroup = ref(null)
const availableUsers = ref([])

async function loadUsers() {
  loading.value = true
  error.value = null
  try {
    const { data } = await getUsers()
    users.value = data
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function loadGroups() {
  loading.value = true
  error.value = null
  try {
    const { data } = await getGroups()
    groups.value = data
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function handleDeleteUser(user) {
  if (!confirm(`Benutzer "${user.display_name}" deaktivieren?`)) return
  try {
    await deleteUser(user.id)
    await loadUsers()
  } catch (err) {
    error.value = err.message
  }
}

async function handleResetPassword(user) {
  const newPw = prompt(`Neues Passwort fuer "${user.display_name}":`)
  if (!newPw || newPw.length < 6) {
    if (newPw) alert('Passwort muss mindestens 6 Zeichen haben')
    return
  }
  try {
    await resetPassword(user.id, { new_password: newPw })
    alert('Passwort zurueckgesetzt')
  } catch (err) {
    error.value = err.message
  }
}

async function handleDeleteGroup(group) {
  if (!confirm(`Gruppe "${group.name}" loeschen?`)) return
  try {
    await deleteGroup(group.id)
    await loadGroups()
  } catch (err) {
    error.value = err.message
  }
}

function openUserModal(user = null) {
  editingUser.value = user
  showUserModal.value = true
}

function openGroupModal(group = null) {
  editingGroup.value = group
  showGroupModal.value = true
}

async function onUserSaved() {
  showUserModal.value = false
  editingUser.value = null
  await loadUsers()
}

async function onGroupSaved() {
  showGroupModal.value = false
  editingGroup.value = null
  await loadGroups()
}

function openGroupMembers(group) {
  managingGroup.value = group
  availableUsers.value = users.value.filter((u) => u.active)
}

async function handleAddToGroup(userId) {
  try {
    await addUserToGroup(managingGroup.value.id, userId)
    await loadGroups()
    await loadUsers()
  } catch (err) {
    error.value = err.message
  }
}

async function handleRemoveFromGroup(userId) {
  try {
    await removeUserFromGroup(managingGroup.value.id, userId)
    await loadGroups()
    await loadUsers()
  } catch (err) {
    error.value = err.message
  }
}

onMounted(async () => {
  await Promise.all([loadUsers(), loadGroups()])
})
</script>

<template>
  <div>
    <PageHeader
      title="Benutzerverwaltung"
      subtitle="Benutzer, Gruppen und Berechtigungen verwalten"
    >
      <template #actions>
        <button
          v-if="activeTab === 'users'"
          class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary/90"
          @click="openUserModal()"
        >
          Neuer Benutzer
        </button>
        <button
          v-else
          class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary/90"
          @click="openGroupModal()"
        >
          Neue Gruppe
        </button>
      </template>
    </PageHeader>

    <!-- Tabs -->
    <div class="mb-6 flex gap-1 rounded-lg bg-gray-100 p-1 dark:bg-gray-800">
      <button
        :class="[
          'flex-1 rounded-md px-4 py-2 text-sm font-medium transition',
          activeTab === 'users'
            ? 'bg-white text-go4-secondary shadow-sm dark:bg-gray-700 dark:text-gray-100'
            : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
        ]"
        @click="activeTab = 'users'"
      >
        Benutzer ({{ users.length }})
      </button>
      <button
        :class="[
          'flex-1 rounded-md px-4 py-2 text-sm font-medium transition',
          activeTab === 'groups'
            ? 'bg-white text-go4-secondary shadow-sm dark:bg-gray-700 dark:text-gray-100'
            : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
        ]"
        @click="activeTab = 'groups'"
      >
        Gruppen ({{ groups.length }})
      </button>
    </div>

    <!-- Loading / Error -->
    <div v-if="loading" class="flex items-center justify-center py-12">
      <span class="text-sm text-gray-500">Laden...</span>
    </div>
    <div
      v-else-if="error"
      class="rounded-lg bg-red-50 p-4 text-sm text-red-600 dark:bg-red-900/30 dark:text-red-400"
    >
      {{ error }}
    </div>

    <!-- Users Tab -->
    <div v-else-if="activeTab === 'users'">
      <div class="overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 dark:bg-gray-800">
            <tr>
              <th class="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-400">Name</th>
              <th class="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-400">
                E-Mail
              </th>
              <th class="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-400">
                Rolle
              </th>
              <th class="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-400">
                Status
              </th>
              <th class="px-4 py-3 text-right font-medium text-gray-600 dark:text-gray-400">
                Aktionen
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
            <tr v-for="u in users" :key="u.id" class="bg-white dark:bg-gray-900">
              <td class="px-4 py-3 font-medium text-gray-900 dark:text-gray-100">
                {{ u.display_name }}
              </td>
              <td class="px-4 py-3 text-gray-600 dark:text-gray-400">
                {{ u.email }}
              </td>
              <td class="px-4 py-3">
                <span
                  :class="[
                    'inline-flex rounded-full px-2 py-0.5 text-xs font-medium',
                    u.role === 'admin'
                      ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400'
                      : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
                  ]"
                >
                  {{ u.role === 'admin' ? 'Admin' : 'Benutzer' }}
                </span>
              </td>
              <td class="px-4 py-3">
                <span
                  :class="[
                    'inline-flex rounded-full px-2 py-0.5 text-xs font-medium',
                    u.active
                      ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                      : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                  ]"
                >
                  {{ u.active ? 'Aktiv' : 'Inaktiv' }}
                </span>
              </td>
              <td class="px-4 py-3 text-right">
                <div class="flex items-center justify-end gap-2">
                  <button
                    class="text-gray-400 hover:text-go4-primary"
                    title="Bearbeiten"
                    @click="openUserModal(u)"
                  >
                    <svg
                      class="h-4 w-4"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="1.5"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125"
                      />
                    </svg>
                  </button>
                  <button
                    class="text-gray-400 hover:text-amber-500"
                    title="Passwort zuruecksetzen"
                    @click="handleResetPassword(u)"
                  >
                    <svg
                      class="h-4 w-4"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="1.5"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121.75 8.25z"
                      />
                    </svg>
                  </button>
                  <button
                    v-if="u.active"
                    class="text-gray-400 hover:text-red-500"
                    title="Deaktivieren"
                    @click="handleDeleteUser(u)"
                  >
                    <svg
                      class="h-4 w-4"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="1.5"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"
                      />
                    </svg>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Groups Tab -->
    <div v-else-if="activeTab === 'groups'">
      <div class="grid gap-4 sm:grid-cols-2">
        <div
          v-for="g in groups"
          :key="g.id"
          class="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900"
        >
          <div class="flex items-start justify-between">
            <div>
              <h3 class="font-medium text-gray-900 dark:text-gray-100">
                {{ g.name }}
              </h3>
              <p v-if="g.description" class="mt-0.5 text-sm text-gray-500 dark:text-gray-400">
                {{ g.description }}
              </p>
              <p class="mt-1 text-xs text-gray-400 dark:text-gray-500">
                {{ g.user_count }} {{ g.user_count === 1 ? 'Mitglied' : 'Mitglieder' }}
              </p>
            </div>
            <div class="flex gap-1">
              <button
                class="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-go4-primary dark:hover:bg-gray-800"
                title="Mitglieder verwalten"
                @click="openGroupMembers(g)"
              >
                <svg
                  class="h-4 w-4"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.5"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z"
                  />
                </svg>
              </button>
              <button
                class="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-go4-primary dark:hover:bg-gray-800"
                title="Bearbeiten"
                @click="openGroupModal(g)"
              >
                <svg
                  class="h-4 w-4"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.5"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125"
                  />
                </svg>
              </button>
              <button
                class="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-red-500 dark:hover:bg-gray-800"
                title="Loeschen"
                @click="handleDeleteGroup(g)"
              >
                <svg
                  class="h-4 w-4"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.5"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0"
                  />
                </svg>
              </button>
            </div>
          </div>

          <!-- Permission preview -->
          <div v-if="g.permissions" class="mt-3 flex flex-wrap gap-1">
            <template v-for="(actions, mod) in g.permissions" :key="mod">
              <span
                v-if="Object.values(actions).some(Boolean)"
                class="inline-flex rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600 dark:bg-gray-800 dark:text-gray-400"
              >
                {{ mod }}
              </span>
            </template>
          </div>
        </div>
      </div>
    </div>

    <!-- Group Members Panel -->
    <div
      v-if="managingGroup"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      @click.self="managingGroup = null"
    >
      <div class="w-full max-w-md rounded-xl bg-white p-6 shadow-2xl dark:bg-gray-800">
        <h2 class="mb-4 text-lg font-semibold text-gray-900 dark:text-gray-100">
          Mitglieder: {{ managingGroup.name }}
        </h2>

        <div class="space-y-2">
          <div
            v-for="u in availableUsers"
            :key="u.id"
            class="flex items-center justify-between rounded-lg border border-gray-200 px-3 py-2 dark:border-gray-700"
          >
            <div>
              <p class="text-sm font-medium text-gray-900 dark:text-gray-100">
                {{ u.display_name }}
              </p>
              <p class="text-xs text-gray-500 dark:text-gray-400">
                {{ u.email }}
              </p>
            </div>
            <button
              class="rounded-lg px-3 py-1 text-xs font-medium transition"
              :class="
                users
                  .find((usr) => usr.id === u.id)
                  ?.groups?.some((g) => g?.id === managingGroup.id)
                  ? 'bg-red-100 text-red-600 hover:bg-red-200 dark:bg-red-900/30 dark:text-red-400'
                  : 'bg-green-100 text-green-600 hover:bg-green-200 dark:bg-green-900/30 dark:text-green-400'
              "
              @click="
                users
                  .find((usr) => usr.id === u.id)
                  ?.groups?.some((g) => g?.id === managingGroup.id)
                  ? handleRemoveFromGroup(u.id)
                  : handleAddToGroup(u.id)
              "
            >
              {{
                users
                  .find((usr) => usr.id === u.id)
                  ?.groups?.some((g) => g?.id === managingGroup.id)
                  ? 'Entfernen'
                  : 'Hinzufuegen'
              }}
            </button>
          </div>
        </div>

        <div class="mt-4 flex justify-end">
          <button
            class="rounded-lg px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700"
            @click="managingGroup = null"
          >
            Schliessen
          </button>
        </div>
      </div>
    </div>

    <!-- Modals -->
    <UserFormModal
      v-if="showUserModal"
      :user="editingUser"
      @close="showUserModal = false"
      @saved="onUserSaved"
    />
    <GroupFormModal
      v-if="showGroupModal"
      :group="editingGroup"
      @close="showGroupModal = false"
      @saved="onGroupSaved"
    />
  </div>
</template>
