import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import {
  getContacts,
  getContact,
  createContact,
  updateContact,
  deleteContact,
  bulkDeleteContacts,
  bulkTagContacts,
  getContactFilters,
  getCompanies,
  getCompany,
  createCompany,
  updateCompany,
  deleteCompany
} from '@/api/contacts'

export const useContactsStore = defineStore('contacts', () => {
  // State
  const contacts = ref([])
  const companies = ref([])
  const currentContact = ref(null)
  const currentCompany = ref(null)
  const filterOptions = ref({ sources: [], tags: [] })
  const loading = ref(false)
  const error = ref(null)

  // Computed
  const totalContacts = computed(() => contacts.value.length)
  const totalCompanies = computed(() => companies.value.length)

  // ============== Contacts ==============

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

  async function fetchContact(id) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getContact(id)
      currentContact.value = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
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

  async function editContact(id, contactData) {
    error.value = null
    try {
      const { data } = await updateContact(id, contactData)
      const index = contacts.value.findIndex((c) => c.id === id)
      if (index !== -1) {
        contacts.value[index] = data
      }
      if (currentContact.value?.id === id) {
        currentContact.value = data
      }
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function removeContact(id) {
    error.value = null
    try {
      await deleteContact(id)
      contacts.value = contacts.value.filter((c) => c.id !== id)
      if (currentContact.value?.id === id) {
        currentContact.value = null
      }
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function bulkDelete(ids) {
    error.value = null
    try {
      await bulkDeleteContacts(ids)
      contacts.value = contacts.value.filter((c) => !ids.includes(c.id))
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function bulkTag(ids, tags, action = 'add') {
    error.value = null
    try {
      await bulkTagContacts(ids, tags, action)
      // Refresh contacts to get updated tags
      await fetchContacts()
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function fetchFilters() {
    try {
      const { data } = await getContactFilters()
      filterOptions.value = data
    } catch (err) {
      // Silent fail for filter options
    }
  }

  // ============== Companies ==============

  async function fetchCompanies(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getCompanies(params)
      companies.value = data
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function fetchCompanyDetail(id) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getCompany(id)
      currentCompany.value = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function addCompany(companyData) {
    loading.value = true
    error.value = null
    try {
      const { data } = await createCompany(companyData)
      companies.value.unshift(data)
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function editCompany(id, companyData) {
    error.value = null
    try {
      const { data } = await updateCompany(id, companyData)
      const index = companies.value.findIndex((c) => c.id === id)
      if (index !== -1) {
        companies.value[index] = data
      }
      if (currentCompany.value?.id === id) {
        currentCompany.value = data
      }
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function removeCompany(id) {
    error.value = null
    try {
      await deleteCompany(id)
      companies.value = companies.value.filter((c) => c.id !== id)
      if (currentCompany.value?.id === id) {
        currentCompany.value = null
      }
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  function clearCurrent() {
    currentContact.value = null
    currentCompany.value = null
  }

  return {
    // State
    contacts,
    companies,
    currentContact,
    currentCompany,
    filterOptions,
    loading,
    error,
    // Computed
    totalContacts,
    totalCompanies,
    // Contact Actions
    fetchContacts,
    fetchContact,
    addContact,
    editContact,
    removeContact,
    bulkDelete,
    bulkTag,
    fetchFilters,
    // Company Actions
    fetchCompanies,
    fetchCompanyDetail,
    addCompany,
    editCompany,
    removeCompany,
    // Utils
    clearCurrent
  }
})
