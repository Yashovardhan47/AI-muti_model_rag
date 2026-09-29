import axios from 'axios'
import { useAuth } from './auth'

export const api = axios.create({ baseURL: '/api', timeout: 180000 })
api.interceptors.request.use(config => { const token = useAuth.getState().access; if (token) config.headers.Authorization = `Bearer ${token}`; return config })
let refreshing: Promise<string> | null = null
api.interceptors.response.use(response => response, async error => {
  const original = error.config
  if (error.response?.status !== 401 || !original || original._retry || original.url?.startsWith('/auth/')) return Promise.reject(error)
  const refresh = useAuth.getState().refresh
  if (!refresh) { useAuth.getState().clear(); return Promise.reject(error) }
  original._retry = true
  try {
    refreshing ||= axios.post('/api/auth/refresh', { refresh_token: refresh }).then(({data}) => { useAuth.getState().setTokens(data.access_token, data.refresh_token, data.user); return data.access_token }).finally(() => { refreshing = null })
    original.headers.Authorization = `Bearer ${await refreshing}`
    return api(original)
  } catch (e) { useAuth.getState().clear(); return Promise.reject(e) }
})
export const errorText = (error: unknown) => axios.isAxiosError(error) ? (typeof error.response?.data?.detail === 'string' ? error.response.data.detail : error.message) : String(error)
export async function previewFile(id: string) {
  const response = await api.get(`/files/${id}/preview`, { responseType: 'blob' })
  const url = URL.createObjectURL(response.data)
  window.open(url, '_blank', 'noopener,noreferrer')
  setTimeout(() => URL.revokeObjectURL(url), 60_000)
}
