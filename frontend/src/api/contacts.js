import api from '@/api'

// ============== Contacts ==============

export function getContacts(params = {}) {
  return api.get('/v1/contacts/', { params })
}

export function getContact(id) {
  return api.get(`/v1/contacts/${id}`)
}

export function getContactContext(id) {
  return api.get(`/v1/contacts/${id}/context`)
}

export function createContact(data) {
  return api.post('/v1/contacts/', data)
}

export function updateContact(id, data) {
  return api.put(`/v1/contacts/${id}`, data)
}

export function deleteContact(id) {
  return api.delete(`/v1/contacts/${id}`)
}

export function bulkDeleteContacts(ids) {
  return api.post('/v1/contacts/bulk-delete', { ids })
}

export function bulkTagContacts(ids, tags, action = 'add') {
  return api.post('/v1/contacts/bulk-tag', { ids, tags, action })
}

export function getContactFilters() {
  return api.get('/v1/contacts/filters')
}

// ============== Companies ==============

export function getCompanies(params = {}) {
  return api.get('/v1/contacts/companies', { params })
}

export function getCompany(id) {
  return api.get(`/v1/contacts/companies/${id}`)
}

export function createCompany(data) {
  return api.post('/v1/contacts/companies', data)
}

export function updateCompany(id, data) {
  return api.put(`/v1/contacts/companies/${id}`, data)
}

export function deleteCompany(id) {
  return api.delete(`/v1/contacts/companies/${id}`)
}
