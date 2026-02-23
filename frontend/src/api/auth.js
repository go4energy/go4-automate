import api from '@/api'

export const login = (email, password) => api.post('/v1/auth/login', { email, password })
export const getMe = () => api.get('/v1/auth/me')
export const changePassword = (data) => api.put('/v1/auth/me/password', data)

// Admin: Users
export const getUsers = () => api.get('/v1/auth/users')
export const createUser = (data) => api.post('/v1/auth/users', data)
export const updateUser = (id, data) => api.put(`/v1/auth/users/${id}`, data)
export const deleteUser = (id) => api.delete(`/v1/auth/users/${id}`)
export const resetPassword = (id, data) => api.put(`/v1/auth/users/${id}/reset-password`, data)

// Admin: Groups
export const getGroups = () => api.get('/v1/auth/groups')
export const createGroup = (data) => api.post('/v1/auth/groups', data)
export const updateGroup = (id, data) => api.put(`/v1/auth/groups/${id}`, data)
export const deleteGroup = (id) => api.delete(`/v1/auth/groups/${id}`)
export const addUserToGroup = (groupId, userId) =>
  api.post(`/v1/auth/groups/${groupId}/users/${userId}`)
export const removeUserFromGroup = (groupId, userId) =>
  api.delete(`/v1/auth/groups/${groupId}/users/${userId}`)

// Permission schema
export const getPermissionSchema = () => api.get('/v1/auth/permissions/schema')
