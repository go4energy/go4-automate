import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request Interceptor – Tenant Header + Auth Token
api.interceptors.request.use((config) => {
  const tenantId = localStorage.getItem('tenant_id') || 'go4energy'
  const token = localStorage.getItem('token')

  config.headers['X-Tenant-ID'] = tenantId
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
})

// Response Interceptor – Error Handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    let message = 'Unbekannter Fehler'
    const detail = error.response?.data?.detail

    if (typeof detail === 'string') {
      message = detail
    } else if (Array.isArray(detail)) {
      // Validation errors from FastAPI
      message = detail.map((e) => e.msg || e.message || JSON.stringify(e)).join(', ')
    } else if (detail && typeof detail === 'object') {
      message = detail.msg || detail.message || JSON.stringify(detail)
    } else if (error.message) {
      message = error.message
    }

    if (error.response?.status === 401 && !error.config?.url?.includes('/auth/login')) {
      localStorage.removeItem('token')
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }

    return Promise.reject(new Error(message))
  }
)

export default api
