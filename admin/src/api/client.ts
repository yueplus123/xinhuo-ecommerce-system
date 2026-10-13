import axios from 'axios'
import { clearAuth, getAccess, getRefresh, isSessionExpired, setAccess } from '@/utils/auth'

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'
const TIMEOUT = 60000

const api = axios.create({ baseURL: API_BASE, timeout: TIMEOUT })

const isTokenUrl = (c?: { url?: string }) => /\/auth\/token(?:\/|$|\?)/.test(c?.url || '')

api.interceptors.request.use((config) => {
  if (isSessionExpired()) {
    clearAuth()
    if (!isTokenUrl(config)) return Promise.reject(new Error('SESSION_EXPIRED'))
  }
  const token = getAccess()
  if (token && !isTokenUrl(config)) config.headers.Authorization = `Bearer ${token}`
  return config
})

// 401 时用 refresh 换新 access，并发请求只刷新一次
let refreshing: Promise<string> | null = null
api.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config
    if (error?.response?.status !== 401 || !original || original._retry || isTokenUrl(original)) {
      return Promise.reject(error)
    }
    const refresh = getRefresh()
    if (!refresh) return Promise.reject(error)
    original._retry = true
    try {
      refreshing ??= axios
        .post(`${API_BASE}/auth/token/refresh/`, { refresh }, { timeout: TIMEOUT })
        .then((r) => r.data.access as string)
        .finally(() => (refreshing = null))
      const access = await refreshing
      setAccess(access)
      original.headers.Authorization = `Bearer ${access}`
      return api(original)
    } catch (e) {
      clearAuth()
      return Promise.reject(e)
    }
  }
)

/** 登录：绕过拦截器 */
export async function requestToken(username: string, password: string) {
  const { data } = await axios.post(`${API_BASE}/auth/token/`, { username, password }, { timeout: TIMEOUT })
  return data as { access: string; refresh: string }
}

export default api
