import api from '@/api'

export const getModules = () => api.get('/v1/modules')
export const getModule = (name) => api.get(`/v1/modules/${name}`)
export const getDesktopModules = () => api.get('/v1/modules/desktop')
export const getModuleDocumentation = (name) =>
  api.get(`/v1/modules/documentation/${name}`)
