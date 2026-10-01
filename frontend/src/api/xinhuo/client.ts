import axios from 'axios'
import { clearAuthStorage, isSessionExpired } from '@/auth/session'

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'
const API_TIMEOUT = Number(import.meta.env.VITE_API_TIMEOUT_MS) || 60000

const api = axios.create({
  baseURL: API_BASE,
  timeout: API_TIMEOUT
})

function isAuthTokenRequest(config: { url?: string; baseURL?: string } | undefined) {
  if (!config) return false
  const joined = `${config.baseURL || ''}${config.url || ''}`
  return /\/auth\/token(?:\/|$|\?)/.test(joined)
}

api.interceptors.request.use((config) => {
  const authTokenReq = isAuthTokenRequest(config)
  if (isSessionExpired()) {
    clearAuthStorage()
    if (!authTokenReq) {
      return Promise.reject(new Error('SESSION_EXPIRED'))
    }
  }
  const access = localStorage.getItem('access_token')
  if (access && !authTokenReq) {
    config.headers.Authorization = `Bearer ${access}`
  }
  return config
})

let isRefreshing = false
const waiters: Array<{
  resolve: (v: any) => void
  reject: (e: any) => void
  config: any
}> = []

function flushWaitersSuccess(token: string) {
  const q = waiters.splice(0)
  q.forEach(({ resolve, config }) => {
    config.headers.Authorization = `Bearer ${token}`
    resolve(api(config))
  })
}

function flushWaitersFailure(err: any) {
  const q = waiters.splice(0)
  q.forEach(({ reject }) => reject(err))
}

api.interceptors.response.use(
  (resp) => resp,
  async (error) => {
    const original = error.config
    // 登录/刷新接口的 401 不要再走 refresh，否则会误报「连不上后端」
    if (
      error?.response?.status !== 401 ||
      original?._retry ||
      isAuthTokenRequest(original)
    ) {
      return Promise.reject(error)
    }

    const refresh = localStorage.getItem('refresh_token')
    if (!refresh) {
      return Promise.reject(error)
    }

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        waiters.push({ resolve, reject, config: original })
      })
    }

    original._retry = true
    isRefreshing = true
    try {
      const resp = await axios.post(
        `${API_BASE}/auth/token/refresh/`,
        { refresh },
        { timeout: API_TIMEOUT }
      )
      const access = resp.data.access
      localStorage.setItem('access_token', access)
      flushWaitersSuccess(access)
      original.headers.Authorization = `Bearer ${access}`
      return api(original)
    } catch (e) {
      clearAuthStorage()
      flushWaitersFailure(e)
      return Promise.reject(e)
    } finally {
      isRefreshing = false
    }
  }
)

/** 登录专用：绕过拦截器，避免旧 refresh_token 干扰 */
export async function requestAccessToken(username: string, password: string) {
  const { data } = await axios.post(
    `${API_BASE}/auth/token/`,
    { username, password },
    {
      timeout: API_TIMEOUT,
      headers: { 'Content-Type': 'application/json' }
    }
  )
  return data as { access: string; refresh: string }
}

export default api
