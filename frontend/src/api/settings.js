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

// Desktop layout
export const getDesktopLayout = () => api.get('/v1/settings/desktop-layout')
export const updateDesktopLayout = (moduleName, updates) =>
  api.put(`/v1/settings/desktop-layout/${moduleName}`, updates)
export const bulkUpdateDesktopOrder = (orderMap) =>
  api.put('/v1/settings/desktop-layout/bulk-order', orderMap)
export const deleteDesktopOverride = (moduleName) =>
  api.delete(`/v1/settings/desktop-layout/${moduleName}`)
