import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { getContacts, createContact, updateContactStatus, pauseFollowup } from '@/api/crm'

export const useCrmStore = defineStore('crm', () => {
  const contacts = ref([])
  const loading = ref(false)
  const error = ref(null)

  const totalContacts = computed(() => contacts.value.length)
  const activeContacts = computed(() => contacts.value.filter((c) => c.status !== 'lost'))

  async function fetchContacts(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getContacts(params)
      contacts.value = data
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function addContact(contactData) {
    loading.value = true
    error.value = null
    try {
      const { data } = await createContact(contactData)
      contacts.value.unshift(data)
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function changeStatus(contactId, status) {
    error.value = null
    try {
      const { data } = await updateContactStatus(contactId, status)
      const index = contacts.value.findIndex((c) => c.id === contactId)
      if (index !== -1) {
        contacts.value[index] = data
      }
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function toggleFollowupPause(contactId, paused) {
    error.value = null
    try {
      const { data } = await pauseFollowup(contactId, paused)
      const index = contacts.value.findIndex((c) => c.id === contactId)
      if (index !== -1) {
        contacts.value[index] = data
      }
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  return {
    contacts,
    loading,
    error,
    totalContacts,
    activeContacts,
    fetchContacts,
    addContact,
    changeStatus,
    toggleFollowupPause
  }
})
