import api from '@/api'

// Module discovery
export const getModules = () => api.get('/v1/settings/modules')

// Module config
export const getModuleSchema = (name) => api.get(`/v1/settings/modules/${name}/schema`)
export const getModuleConfig = (name) => api.get(`/v1/settings/modules/${name}/config`)
export const updateModuleConfig = (name, updates) =>
  api.put(`/v1/settings/modules/${name}/config`, updates)
export const getModuleStatus = (name) => api.get(`/v1/settings/modules/${name}/status`)

// Global config
export const getGlobalSchema = () => api.get('/v1/settings/global/schema')
export const getGlobalConfig = () => api.get('/v1/settings/global/config')
export const updateGlobalConfig = (updates) => api.put('/v1/settings/global/config', updates)
