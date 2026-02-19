import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request Interceptor – Tenant Header
api.interceptors.request.use((config) => {
  const tenantId = localStorage.getItem('tenant_id') || 'go4energy'
  config.headers['X-Tenant-ID'] = tenantId
  return config
})

// Response Interceptor – Error Handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.detail || error.message || 'Unbekannter Fehler'

    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }

    return Promise.reject(new Error(message))
  }
)

export default api
